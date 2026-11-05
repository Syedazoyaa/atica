"""Safe file handling shared by the CSV and Excel handlers."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from ..exceptions import BulkProcessingError

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ROWS = 100_000

_NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


@dataclass
class Table:
    """Rows read from a file. ``row_numbers`` are the line/row numbers in the source file."""

    fieldnames: List[str]
    rows: List[Dict[str, str]] = field(default_factory=list)
    row_numbers: List[int] = field(default_factory=list)


def check_input_path(path: Any, suffixes: Sequence[str], max_bytes: int = MAX_FILE_BYTES) -> str:
    p = os.fspath(path)
    if not os.path.isfile(p):
        raise BulkProcessingError("File not found: %s" % p, code="FILE_NOT_FOUND")
    if os.path.splitext(p)[1].lower() not in suffixes:
        raise BulkProcessingError(
            "Unsupported file type %r (expected %s)." % (os.path.splitext(p)[1], ", ".join(suffixes)),
            code="UNSUPPORTED_FILE_TYPE",
        )
    if os.path.getsize(p) > max_bytes:
        raise BulkProcessingError(
            "File is larger than the %d MB limit." % (max_bytes // (1024 * 1024)), code="FILE_TOO_LARGE"
        )
    return p


def check_output_path(path: Any, suffixes: Sequence[str], overwrite: bool) -> str:
    p = os.fspath(path)
    if os.path.splitext(p)[1].lower() not in suffixes:
        raise BulkProcessingError("Output file must end with %s." % " or ".join(suffixes), code="UNSUPPORTED_FILE_TYPE")
    folder = os.path.dirname(os.path.abspath(p))
    if not os.path.isdir(folder):
        raise BulkProcessingError("Output folder does not exist: %s" % folder, code="OUTPUT_FOLDER_MISSING")
    if os.path.exists(p) and not overwrite:
        raise BulkProcessingError(
            "%s already exists; pass overwrite=True to replace it." % p, code="FILE_EXISTS"
        )
    return p


def sanitize_cell(value: Any) -> Any:
    """Neutralise spreadsheet formula injection in text cells (leading = + - @)."""
    if isinstance(value, str) and value and value[0] in "=+-@\t\r" and not _NUMBER.match(value.strip()):
        return "'" + value
    return value


def check_headers(headers: List[str]) -> None:
    seen = set()
    for h in headers:
        key = h.strip().casefold()
        if key and key in seen:
            raise BulkProcessingError("Duplicate column %r in file header." % h, code="DUPLICATE_COLUMN")
        seen.add(key)
