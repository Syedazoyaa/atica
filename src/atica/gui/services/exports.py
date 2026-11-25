"""Export file naming: ``ATICA_<MODULE>_<OPERATION>_<YYYYMMDD_HHMMSS>.<ext>`` (Qt-free).

One implementation serves every export in the GUI, so the convention cannot drift between screens.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Optional

#: Tool names used by the calculator panels -> the module name used in filenames.
_MODULES = {
    "BOM": "MATERIALS",
    "UNIT CONVERTER": "UNITS",
    "CUSTOM UNITS": "UNITS",
}


def sanitize(text: str, fallback: str = "EXPORT") -> str:
    """Upper-case ``A-Z0-9`` words joined by single underscores (safe on every file system)."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_").upper()
    return cleaned or fallback


def suggest_filename(
    module: str, operation: str, extension: str = "csv", now: Optional[datetime.datetime] = None
) -> str:
    """e.g. ``ATICA_PRODUCTION_CAPACITY_20261125_183000.csv`` (local time)."""
    module = _MODULES.get(str(module).strip().upper(), module)
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d_%H%M%S")
    ext = sanitize(extension, "CSV").lower()
    return "ATICA_%s_%s_%s.%s" % (sanitize(module, "MODULE"), sanitize(operation, "RESULT"), stamp, ext)


def with_extension(path: str, chosen_filter: str = "", default: str = "csv") -> str:
    """Add the extension implied by the selected file-dialog filter when the user typed none."""
    if os.path.splitext(path)[1]:
        return path
    return path + (".xlsx" if "xlsx" in chosen_filter.lower() else "." + default)


def unique_path(path: str) -> str:
    """``path`` if it is free, otherwise ``name (2).ext``, ``name (3).ext`` ... - never overwrites."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s (%d)%s" % (stem, n, ext)):
        n += 1
    return "%s (%d)%s" % (stem, n, ext)
