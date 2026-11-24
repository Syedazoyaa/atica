"""Helpers shared by the controllers: reading form values and common option handling."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple

from atica.core import MissingInputError
from atica.core.validation import whole_number


def val(values: Mapping[str, Any], key: str) -> Optional[str]:
    """Stripped text of a form value, or ``None`` when blank (so the core reports 'x is required')."""
    raw = values.get(key)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def optional(values: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Like :func:`val` for optional inputs: blank gives ``default``."""
    text = val(values, key)
    return default if text is None else text


def rounding_args(values: Mapping[str, Any]) -> Tuple[str, int]:
    """``(rounding, places)`` from the standard rounding controls."""
    rounding = val(values, "rounding") or "none"
    if rounding == "none":
        return "none", 0
    places = val(values, "places")
    return rounding, whole_number(places if places is not None else 0, "places", minimum=0)


def checked(values: Mapping[str, Any], key: str) -> bool:
    return bool(values.get(key))


def need(value: Any, what: str, hint: str = "") -> Any:
    """Fail clearly when a shared object (product, BOM ...) has not been set up yet."""
    if value is None:
        raise MissingInputError(what, hint=hint or None)
    return value


ROUNDING_CHOICES = (
    ("No rounding (exact)", "none"),
    ("Half up", "half_up"),
    ("Half even (banker's)", "half_even"),
    ("Floor (down)", "floor"),
    ("Ceiling (up)", "ceiling"),
)
