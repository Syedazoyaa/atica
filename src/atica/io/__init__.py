"""File input / output and bulk processing (M08)."""
from ._common import Table
from .bulk import (
    BulkResult,
    RowResult,
    export_errors,
    export_results,
    map_columns,
    process_file,
    process_rows,
)
from .csv_handler import read_csv, write_csv
from .excel_handler import read_xlsx, write_xlsx

__all__ = [
    "BulkResult",
    "RowResult",
    "Table",
    "export_errors",
    "export_results",
    "map_columns",
    "process_file",
    "process_rows",
    "read_csv",
    "read_xlsx",
    "write_csv",
    "write_xlsx",
]
