"""Excel (.xlsx) import/export.  Requires the optional extra: ``pip install "atica[excel]"``."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..core.exceptions import IntegrationError, MissingDependencyError
from ..materials import Bom
from ..units import UnitRegistry
from ._rows import (
    MAX_ROWS,
    ConversionReport,
    Row,
    bom_from_rows,
    check_cells_have_headers,
    check_headers,
    check_input_path,
    check_output_path,
    convert_rows,
    sanitize_cell,
)


def _openpyxl() -> Any:
    try:
        import openpyxl
    except ImportError:
        raise MissingDependencyError(
            "Excel support needs the optional 'openpyxl' package.",
            parameter="openpyxl",
            hint='Install it with: pip install "atica[excel]"',
        ) from None
    return openpyxl


def _illegal_character_error() -> Any:
    """openpyxl's ``IllegalCharacterError`` (it is not a ``ValueError`` subclass)."""
    from openpyxl.utils.exceptions import IllegalCharacterError

    return IllegalCharacterError


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value).strip()


_BAD_SHEET_CHARS = set("[]:*?/\\")


def _check_sheet_name(name: Any) -> None:
    """Excel sheet names: 1-31 characters, none of the characters ``[ ] : * ? /`` or backslash, not starting/ending with an apostrophe."""
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 31
        or _BAD_SHEET_CHARS & set(name)
        or name.startswith("'")
        or name.endswith("'")
    ):
        raise IntegrationError(
            "%r is not a valid Excel worksheet name." % (name,),
            parameter="sheet_name",
            hint="Use 1-31 characters without any of [ ] : * ? / or backslash (and no leading/trailing apostrophe).",
        )


def read_xlsx(
    path: Any, *, sheet: Optional[str] = None, max_rows: int = MAX_ROWS
) -> Tuple[List[str], List[Row], List[int]]:
    """Read the first (or named) sheet -> ``(fieldnames, rows, row_numbers)``; the first non-empty row is the header."""
    p = check_input_path(path, (".xlsx", ".xlsm"))
    openpyxl = _openpyxl()
    try:
        book = openpyxl.load_workbook(p, read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many types for damaged files
        raise IntegrationError("Cannot open the Excel file: %s" % exc, parameter="path") from None
    try:
        if sheet is not None and sheet not in book.sheetnames:
            raise IntegrationError(
                "Worksheet %r not found." % sheet,
                parameter="sheet",
                hint="Available: %s." % ", ".join(book.sheetnames),
            )
        worksheet = book[sheet] if sheet else book.worksheets[0]
        fieldnames: Optional[List[str]] = None
        rows: List[Row] = []
        numbers: List[int] = []
        for number, values in enumerate(worksheet.iter_rows(values_only=True), start=1):
            cells = [_text(v) for v in values]
            if not any(cells):
                continue
            if fieldnames is None:
                header = list(cells)
                while header and not header[-1]:
                    header.pop()
                fieldnames = check_headers(header)
                continue
            if len(rows) >= max_rows:
                raise IntegrationError("More than %d data rows." % max_rows, parameter="path")
            check_cells_have_headers(cells, fieldnames, number)
            rows.append({h: (cells[i] if i < len(cells) else "") for i, h in enumerate(fieldnames) if h})
            numbers.append(number)
    finally:
        book.close()
    if fieldnames is None:
        raise IntegrationError("The worksheet is empty.", parameter="path")
    return fieldnames, rows, numbers


def write_xlsx(
    path: Any,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, Any]],
    *,
    overwrite: bool = False,
    sheet_name: str = "Results",
) -> str:
    """Write ``rows`` to an .xlsx file and return the path."""
    p = check_output_path(path, (".xlsx",), overwrite)
    _check_sheet_name(sheet_name)
    openpyxl = _openpyxl()
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = sheet_name
    try:
        sheet.append(list(fieldnames))
        for row in rows:
            sheet.append([sanitize_cell(row.get(f, "")) for f in fieldnames])
    except (ValueError, _illegal_character_error()) as exc:  # e.g. control characters Excel cannot store
        raise IntegrationError(
            "A value cannot be stored in an Excel sheet: %s" % exc,
            parameter="rows",
            hint="Remove control characters from the data or export to CSV instead.",
        ) from None
    try:
        book.save(p)
    except OSError as exc:
        raise IntegrationError(
            "Cannot write the file: %s" % exc,
            parameter="path",
            hint="Check that the folder is writable and that the file is not open in Excel.",
        ) from None
    return p


def convert_xlsx(
    path: Any,
    *,
    sheet: Optional[str] = None,
    output_path: Optional[Any] = None,
    overwrite: bool = False,
    registry: Optional[UnitRegistry] = None,
    **options: Any,
) -> ConversionReport:
    """Like :func:`atica.integrations.csv.convert_csv` for an Excel sheet."""
    _, rows, numbers = read_xlsx(path, sheet=sheet)
    report = convert_rows(rows, registry=registry, row_numbers=numbers, **options)
    if output_path is not None:
        write_xlsx(output_path, report.fieldnames, list(report.rows), overwrite=overwrite)
    return report


def read_bom_xlsx(
    path: Any, *, sheet: Optional[str] = None, product_id: str = "", allow_duplicates: bool = False
) -> Bom:
    """Load a BOM from a sheet (see :func:`atica.integrations.csv.read_bom_csv` for the columns)."""
    _, rows, numbers = read_xlsx(path, sheet=sheet)
    return bom_from_rows(rows, product_id=product_id, allow_duplicates=allow_duplicates, row_numbers=numbers)
