"""Result base class and conventions.

ATICA does **not** use one universal result object.  Each calculation returns a
small, frozen dataclass with fields specific to it.  They share these
conventions:

* numbers are ``Decimal``;
* a ``unit`` field names the unit of the main value where one exists;
* ``exact_*`` fields hold the unrounded value when rounding was requested;
* ``warnings`` is a tuple of human-readable strings (empty when all is well);
* ``formula`` is a short text of the formula used;
* :meth:`Result.to_dict` gives plain data and :meth:`Result.explain` a readable summary.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from enum import Enum
from typing import Any, Dict

from .precision import format_decimal


def _plain(value: Any, numbers: str) -> Any:
    if isinstance(value, Result):
        return value.to_dict(numbers=numbers)
    if isinstance(value, Decimal):
        if numbers == "str":
            return format_decimal(value)
        if numbers == "float":
            return float(value)
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_plain(v, numbers) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v, numbers) for k, v in value.items()}
    return value


@dataclasses.dataclass(frozen=True)
class Result:
    """Base class for all calculation results."""

    def to_dict(self, *, numbers: str = "decimal") -> Dict[str, Any]:
        """Plain-data form.

        ``numbers`` is ``'decimal'`` (default, lossless), ``'str'`` (JSON-safe, lossless)
        or ``'float'`` (convenient, may lose precision).
        """
        if numbers not in ("decimal", "str", "float"):
            raise ValueError("numbers must be 'decimal', 'str' or 'float'.")
        return {f.name: _plain(getattr(self, f.name), numbers) for f in dataclasses.fields(self)}

    def explain(self) -> str:
        """Readable multi-line summary of every field."""
        lines = [type(self).__name__]
        for name, value in self.to_dict(numbers="str").items():
            if value in (None, [], ""):
                continue
            lines.append("  %s: %s" % (name.replace("_", " "), value))
        return "\n".join(lines)
