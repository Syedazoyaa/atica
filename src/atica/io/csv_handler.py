"""CSV import / export using only the standard library."""
from __future__ import annotations

import csv
from typing import Any, Dict, Sequence

from ..exceptions import BulkProcessingError
from ._common import MAX_ROWS, Table, check_headers, check_input_path, check_output_path, sanitize_cell

EXTRA = "__extra__"


def read_csv(path: Any, *, encoding: str = "utf-8-sig", max_rows: int = MAX_ROWS) -> Table:
    """Read a CSV file. Blank lines are skipped; ``row_numbers`` are source line numbers.

    Rows with more cells than headers keep the overflow under ``'__extra__'`` so the
    bulk engine can reject them instead of silently dropping data.
    """
    p = check_input_path(path, (".csv",))
    try:
        with open(p, "r", encoding=encoding, newline="") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                raise BulkProcessingError("The CSV file is empty.", code="EMPTY_FILE") from None
            header = [h.strip() for h in header]
            if not any(header):
                raise BulkProcessingError("The CSV file has no header row.", code="EMPTY_FILE")
            check_headers(header)
            table = Table(fieldnames=header)
            for cells in reader:
                if not any(c.strip() for c in cells):
                    continue
                if len(table.rows) >= max_rows:
                    raise BulkProcessingError(
                        "File has more than %d data rows; split it or raise max_rows." % max_rows,
                        code="TOO_MANY_ROWS",
                    )
                row: Dict[str, str] = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(header)}
                if len(cells) > len(header):
                    row[EXTRA] = ",".join(cells[len(header):])
                table.rows.append(row)
                table.row_numbers.append(reader.line_num)
    except UnicodeDecodeError as exc:
        raise BulkProcessingError("File is not valid %s text: %s" % (encoding, exc), code="ENCODING_ERROR") from None
    except csv.Error as exc:
        raise BulkProcessingError("Malformed CSV: %s" % exc, code="MALFORMED_FILE") from None
    except OSError as exc:
        raise BulkProcessingError("Cannot read file: %s" % exc, code="FILE_READ_ERROR") from None
    return table


def write_csv(
    path: Any,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, Any]],
    *,
    overwrite: bool = False,
    sanitize: bool = True,
    encoding: str = "utf-8-sig",
) -> str:
    """Write rows to ``path`` (never overwrites unless ``overwrite=True``)."""
    p = check_output_path(path, (".csv",), overwrite)
    try:
        with open(p, "w", encoding=encoding, newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: (sanitize_cell(v) if sanitize else v) for k, v in row.items()})
    except OSError as exc:
        raise BulkProcessingError("Cannot write file: %s" % exc, code="FILE_WRITE_ERROR") from None
    return p
