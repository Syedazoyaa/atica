"""Unit conversion (Module 01).

>>> from atica.units import convert
>>> str(convert(25, "kg", "g"))
'25000 g'
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from ..core.rounding import Rounding
from .definitions import BASE_UNITS, Unit
from .registry import Conversion, UnitRegistry

_DEFAULT = UnitRegistry().freeze()


def default_registry() -> UnitRegistry:
    """The shared, **read-only** registry holding the standard units.

    Use ``UnitRegistry()`` for your own writable registry with custom units.
    """
    return _DEFAULT


def convert(
    value: Any,
    from_unit: str,
    to_unit: str,
    *,
    rounding: Any = Rounding.NONE,
    places: int = 0,
    interval: bool = False,
    registry: Optional[UnitRegistry] = None,
) -> Conversion:
    """Convert ``value`` from ``from_unit`` to ``to_unit``.

    :param value: the amount (int, Decimal, numeric string or float; see
        :func:`atica.core.precision.to_decimal`).
    :param from_unit: source unit symbol or alias (case-sensitive), e.g. ``"kg"``.
    :param to_unit: target unit; must measure the same kind of quantity.
    :param rounding: ``'none'`` (default; exact up to the library precision),
        ``'half_up'``, ``'half_even'``, ``'floor'`` or ``'ceiling'``.
    :param places: decimal places for the rounding (requires a rounding policy).
    :param interval: treat a temperature as a *difference* (no offsets), e.g. +-5 C in F.
    :param registry: a :class:`UnitRegistry` with custom units (default: standard units).
    :returns: :class:`Conversion` (``.value``, ``.unit``, ``.exact_value`` ...).
    :raises UnknownUnitError: a unit is not defined.
    :raises IncompatibleUnitError: the units measure different things.
    :raises InvalidQuantityError: invalid number, or a temperature below absolute zero.

    Formula: ``target = ((value + offset_src) * factor_src) / factor_dst - offset_dst``
    (offsets are zero except for Celsius/Fahrenheit).  Computed exactly, rounded once.

    >>> str(convert("212", "F", "C"))
    '100 C'
    """
    return (registry or _DEFAULT).convert(
        value, from_unit, to_unit, rounding=rounding, places=places, interval=interval
    )


def are_compatible(unit_a: str, unit_b: str, *, registry: Optional[UnitRegistry] = None) -> bool:
    """True if the two units can be converted into each other."""
    return (registry or _DEFAULT).are_compatible(unit_a, unit_b)


def get_unit(name: str, *, registry: Optional[UnitRegistry] = None) -> Unit:
    """Look up a unit by symbol or alias."""
    return (registry or _DEFAULT).get(name)


def list_units(
    category: Optional[str] = None, *, registry: Optional[UnitRegistry] = None
) -> Tuple[Unit, ...]:
    """All units (optionally of one category)."""
    return (registry or _DEFAULT).units(category)


def list_categories(*, registry: Optional[UnitRegistry] = None) -> Tuple[str, ...]:
    """All measurement categories."""
    return (registry or _DEFAULT).categories()


__all__ = [
    "BASE_UNITS",
    "Conversion",
    "Unit",
    "UnitRegistry",
    "are_compatible",
    "convert",
    "default_registry",
    "get_unit",
    "list_categories",
    "list_units",
]
