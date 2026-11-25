"""Human-readable durations, e.g. ``1.5 h`` -> ``1 hour 30 minutes``.

Presentation only: the numeric results of the calculations are never changed.  The conversion to
seconds is exact (``Fraction``); only the final whole-second rounding (half up) is a display choice.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, List, Optional

from .validation import non_negative

_PARTS = (("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1))


def format_duration(value: Any, unit: str = "h", registry: Optional[Any] = None) -> str:
    """Write ``value`` (a non-negative number of ``unit``) as days, hours, minutes and seconds.

    Zero-valued units are left out, labels are singular/plural, and the value is rounded to the
    nearest whole second.  A positive duration under half a second reads ``less than 1 second``.

    >>> format_duration("1.5", "h")
    '1 hour 30 minutes'
    >>> format_duration(90, "min")
    '1 hour 30 minutes'
    >>> format_duration(0)
    '0 seconds'
    """
    from ..units import default_registry

    reg = registry or default_registry()
    amount = non_negative(value, "duration")
    seconds = amount * reg.factor(unit, "s")
    whole = int(seconds + Fraction(1, 2)) if seconds >= 0 else 0  # half up (seconds >= 0)
    if whole == 0:
        return "0 seconds" if amount == 0 else "less than 1 second"
    out: List[str] = []
    for name, size in _PARTS:
        count, whole = divmod(whole, size)
        if count:
            out.append("%d %s%s" % (count, name, "" if count == 1 else "s"))
    return " ".join(out)
