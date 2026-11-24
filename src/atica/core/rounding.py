"""Rounding policies.

Two different ideas are kept apart on purpose:

**Mathematical rounding** (:class:`Rounding`) rounds a number to a number of
decimal places: ``NONE``, ``HALF_UP``, ``HALF_EVEN``, ``FLOOR``, ``CEILING``.

**Packaging constraints** (:class:`PackageRounding`, :func:`round_to_multiple`,
:func:`split_by_multiple`) snap a quantity to a multiple of a package size:
*package ceiling* (buy/make whole packages), *package floor* (only complete
packages) and *remainder preservation* (whole packages **plus** the leftover).

All rounding is performed on the exact rational value, never on an
already-rounded Decimal, so ``ceil(1/3 * 3)`` is exactly ``1`` and a repeating
decimal can never push a value over a package boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Any, Union

from .exceptions import InvalidRoundingError, ValidationError
from .precision import fraction_to_decimal, to_fraction

MAX_PLACES = 100


class Rounding(str, Enum):
    """Mathematical rounding policy."""

    NONE = "none"
    HALF_UP = "half_up"  # ties away from zero (2.5 -> 3, -2.5 -> -3)
    HALF_EVEN = "half_even"  # banker's rounding (2.5 -> 2, 3.5 -> 4)
    FLOOR = "floor"  # towards -infinity
    CEILING = "ceiling"  # towards +infinity

    @classmethod
    def parse(cls, value: Union[Rounding, str, None]) -> Rounding:
        """Accept an enum member or its (case-insensitive) name/value; ``None`` means ``NONE``."""
        if value is None:
            return cls.NONE
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            key = value.strip().lower().replace("-", "_").replace(" ", "_")
            for member in cls:
                if key in (member.value, member.name.lower()):
                    return member
        raise InvalidRoundingError(
            "Unknown rounding policy %r." % (value,),
            parameter="rounding",
            hint="Use one of: %s." % ", ".join(m.value for m in cls),
        )


class PackageRounding(str, Enum):
    """Direction for snapping a quantity to a multiple of a package size."""

    CEILING = "package_ceiling"  # whole packages needed to cover the quantity
    FLOOR = "package_floor"  # only the complete packages that fit

    @classmethod
    def parse(cls, value: Union[PackageRounding, str]) -> PackageRounding:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            key = value.strip().lower().replace("-", "_").replace(" ", "_")
            for member in cls:
                if key in (member.value, member.name.lower(), member.value.replace("package_", "")):
                    return member
        raise InvalidRoundingError(
            "Unknown package rounding %r." % (value,),
            parameter="mode",
            hint="Use 'ceiling' (package ceiling) or 'floor' (package floor).",
        )


def check_places(places: Any) -> int:
    """Validate a ``places`` argument (an integer; negative means tens, hundreds ...)."""
    if not isinstance(places, int) or isinstance(places, bool) or abs(places) > MAX_PLACES:
        raise InvalidRoundingError(
            "places must be an integer between -%d and %d (got %r)." % (MAX_PLACES, MAX_PLACES, places),
            parameter="places",
        )
    return places


def resolve_rounding(rounding: Union[Rounding, str, None], places: Any) -> tuple[Rounding, int]:
    """Validate a ``(rounding, places)`` pair.

    ``places`` other than 0 together with ``rounding='none'`` is contradictory and rejected
    rather than silently ignored.
    """
    policy = Rounding.parse(rounding)
    places = check_places(places)
    if policy is Rounding.NONE and places != 0:
        raise InvalidRoundingError(
            "places=%d has no effect with rounding='none'." % places,
            parameter="places",
            hint="Choose a rounding policy such as 'half_up', or remove places.",
        )
    return policy, places


def round_fraction(value: Fraction, rounding: Rounding, places: int = 0) -> Decimal:
    """Round an exact fraction to ``places`` decimal places. ``NONE`` converts without rounding."""
    if rounding is Rounding.NONE:
        return fraction_to_decimal(value)
    scaled = value * Fraction(10) ** places
    if rounding is Rounding.FLOOR:
        whole = math.floor(scaled)
    elif rounding is Rounding.CEILING:
        whole = math.ceil(scaled)
    else:
        floor = math.floor(scaled)
        diff = scaled - floor
        if diff > Fraction(1, 2):
            whole = floor + 1
        elif diff < Fraction(1, 2):
            whole = floor
        elif rounding is Rounding.HALF_EVEN:
            whole = floor if floor % 2 == 0 else floor + 1
        else:  # HALF_UP: ties away from zero
            whole = floor + 1 if scaled > 0 else floor
    return Decimal("%de%d" % (whole, -places))


def round_value(
    value: Any, rounding: Union[Rounding, str, None] = Rounding.HALF_UP, places: int = 0
) -> Decimal:
    """Round ``value`` to ``places`` decimal places using ``rounding``.

    >>> from atica.core import round_value
    >>> str(round_value("2.675", "half_up", 2))
    '2.68'
    >>> str(round_value("2.5", "half_even"))
    '2'
    """
    policy, places = resolve_rounding(rounding, places)
    return round_fraction(to_fraction(value, "value"), policy, places)


# ------------------------------------------------------------- packaging constraints
def _multiple(multiple: Any) -> Fraction:
    m = to_fraction(multiple, "multiple")
    if m <= 0:
        raise ValidationError(
            "The package size / multiple must be greater than zero (got %s)." % multiple,
            parameter="multiple",
        )
    return m


def round_to_multiple(
    value: Any, multiple: Any, mode: Union[PackageRounding, str] = PackageRounding.CEILING
) -> Decimal:
    """Snap ``value`` to a multiple of ``multiple`` (package ceiling or package floor).

    >>> str(round_to_multiple(250, 240))   # package ceiling: 2 packages of 240
    '480'
    >>> str(round_to_multiple(250, 240, "floor"))
    '240'
    """
    m = _multiple(multiple)
    v = to_fraction(value, "value")
    q = v / m
    n = math.ceil(q) if PackageRounding.parse(mode) is PackageRounding.CEILING else math.floor(q)
    return fraction_to_decimal(n * m)


@dataclass(frozen=True)
class MultipleSplit:
    """``value == packages * multiple + remainder`` with ``0 <= remainder < multiple``."""

    value: Decimal
    multiple: Decimal
    packages: Decimal
    remainder: Decimal


def split_by_multiple(value: Any, multiple: Any) -> MultipleSplit:
    """Remainder preservation: whole packages *and* what is left over (nothing is discarded).

    >>> s = split_by_multiple(250, 240)
    >>> (str(s.packages), str(s.remainder))
    ('1', '10')
    """
    m = _multiple(multiple)
    v = to_fraction(value, "value")
    if v < 0:
        raise ValidationError("value must not be negative (got %s)." % value, parameter="value")
    n = math.floor(v / m)
    return MultipleSplit(
        value=fraction_to_decimal(v),
        multiple=fraction_to_decimal(m),
        packages=Decimal(n),
        remainder=fraction_to_decimal(v - n * m),
    )
