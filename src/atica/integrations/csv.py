"""CSV import/export (standard library only).

Files are read as UTF-8 (a BOM is accepted).  Nothing is overwritten unless ``overwrite=True``;
text cells that could be interpreted as spreadsheet formulas are neutralised on export.
"""

from __future__ import annotations

import csv as _csv
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..core.exceptions import IntegrationError
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


def read_csv(path: Any, *, max_rows: int = MAX_ROWS) -> Tuple[List[str], List[Row], List[int]]:
    """Read a CSV file -> ``(fieldnames, rows, row_numbers)``; blank lines are skipped.

    :raises IntegrationError: missing/oversized/unsupported file, no header, duplicate or ragged columns.
    """
    p = check_input_path(path, (".csv",))
    try:
        with open(p, encoding="utf-8-sig", newline="") as handle:
            reader = _csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise IntegrationError("The CSV file is empty.", parameter="path") from None
            fieldnames = check_headers(header)
            if not any(fieldnames):
                raise IntegrationError("The CSV file has no header row.", parameter="path")
            rows: List[Row] = []
            numbers: List[int] = []
            for cells in reader:
                if not any(c.strip() for c in cells):
                    continue
                if len(rows) >= max_rows:
                    raise IntegrationError(
                        "More than %d data rows." % max_rows, parameter="path", hint="Split the file."
                    )
                if len(cells) > len(fieldnames):
                    raise IntegrationError(
                        "Row %d has more cells (%d) than the header has columns (%d)."
                        % (reader.line_num, len(cells), len(fieldnames)),
                        parameter="path",
                    )
                check_cells_have_headers([c.strip() for c in cells], fieldnames, reader.line_num)
                rows.append(
                    {h: (cells[i].strip() if i < len(cells) else "") for i, h in enumerate(fieldnames) if h}
                )
                numbers.append(reader.line_num)
    except UnicodeDecodeError as exc:
        raise IntegrationError("The file is not valid UTF-8 text: %s" % exc, parameter="path") from None
    except _csv.Error as exc:
        raise IntegrationError("Malformed CSV: %s" % exc, parameter="path") from None
    except OSError as exc:
        raise IntegrationError("Cannot read the file: %s" % exc, parameter="path") from None
    return fieldnames, rows, numbers


def write_csv(
    path: Any, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]], *, overwrite: bool = False
) -> str:
    """Write ``rows`` to ``path`` and return the path."""
    p = check_output_path(path, (".csv",), overwrite)
    try:
        with open(p, "w", encoding="utf-8-sig", newline="") as handle:
            writer = _csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: sanitize_cell(v) for k, v in row.items()})
    except OSError as exc:
        raise IntegrationError("Cannot write the file: %s" % exc, parameter="path") from None
    return p


def convert_csv(
    path: Any,
    *,
    output_path: Optional[Any] = None,
    overwrite: bool = False,
    registry: Optional[UnitRegistry] = None,
    **options: Any,
) -> ConversionReport:
    """Convert every row of a CSV (columns ``value``, ``from_unit``, ``to_unit``) with :func:`atica.units.convert`.

    ``options`` are ``value_column``, ``from_column``, ``to_column``, ``rounding`` and ``places``.
    If ``output_path`` is given the converted rows are written there.
    """
    _, rows, numbers = read_csv(path)
    report = convert_rows(rows, registry=registry, row_numbers=numbers, **options)
    if output_path is not None:
        write_csv(output_path, report.fieldnames, list(report.rows), overwrite=overwrite)
    return report


def read_bom_csv(path: Any, *, product_id: str = "", allow_duplicates: bool = False) -> Bom:
    """Load a BOM from a CSV with columns ``material_id, quantity_per_unit, unit`` (+ optional ``wastage_percent``, ``name``)."""
    _, rows, numbers = read_csv(path)
    return bom_from_rows(rows, product_id=product_id, allow_duplicates=allow_duplicates, row_numbers=numbers)
