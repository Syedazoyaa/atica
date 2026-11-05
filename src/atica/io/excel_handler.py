"""Optional Excel (.xlsx) import / export. Requires ``pip install atica[excel]``."""
from __future__ import annotations

import datetime
from typing import Any, Dict, Optional, Sequence

from ..exceptions import BulkProcessingError
from ._common import MAX_ROWS, Table, check_headers, check_input_path, check_output_path, sanitize_cell


def _openpyxl():
    try:
        import openpyxl  # noqa: WPS433
    except ImportError:
        raise BulkProcessingError(
            "Excel support needs the optional 'openpyxl' package: pip install atica[excel]",
            code="EXCEL_SUPPORT_MISSING",
        ) from None
    return openpyxl


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value).strip()


def read_xlsx(path: Any, *, sheet: Optional[str] = None, max_rows: int = MAX_ROWS) -> Table:
    """Read the first (or named) worksheet; the first non-empty row is the header."""
    p = check_input_path(path, (".xlsx", ".xlsm"))
    openpyxl = _openpyxl()
    try:
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many types for corrupt files
        raise BulkProcessingError("Cannot open Excel file: %s" % exc, code="MALFORMED_FILE") from None
    try:
        if sheet is not None and sheet not in wb.sheetnames:
            raise BulkProcessingError("Worksheet %r not found (available: %s)." % (sheet, ", ".join(wb.sheetnames)), code="SHEET_NOT_FOUND")
        ws = wb[sheet] if sheet else wb.worksheets[0]
        table = None
        for number, values in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [_cell_text(v) for v in values]
            if not any(cells):
                continue
            if table is None:
                header = [c.strip() for c in cells]
                while header and not header[-1]:
                    header.pop()
                check_headers(header)
                table = Table(fieldnames=header)
                continue
            if len(table.rows) >= max_rows:
                raise BulkProcessingError("Sheet has more than %d data rows." % max_rows, code="TOO_MANY_ROWS")
            row = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(table.fieldnames)}
            table.rows.append(row)
            table.row_numbers.append(number)
    finally:
        wb.close()
    if table is None:
        raise BulkProcessingError("The worksheet is empty.", code="EMPTY_FILE")
    return table


def write_xlsx(
    path: Any,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, Any]],
    *,
    overwrite: bool = False,
    sanitize: bool = True,
    sheet_name: str = "Results",
) -> str:
    p = check_output_path(path, (".xlsx",), overwrite)
    openpyxl = _openpyxl()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    ws.append(list(fieldnames))
    for row in rows:
        ws.append([sanitize_cell(row.get(f, "")) if sanitize else row.get(f, "") for f in fieldnames])
    try:
        wb.save(p)
    except OSError as exc:
        raise BulkProcessingError("Cannot write file: %s" % exc, code="FILE_WRITE_ERROR") from None
    return p
