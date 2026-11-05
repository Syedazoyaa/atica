"""Operation-level rounding policies (M10).

ATICA never applies one global rounding rule. Every operation takes its own
policy. Policies that work on decimal places (``HALF_UP``, ``HALF_EVEN``,
``DOWN``, ``UP``) use ``places``; package policies (``CEILING_PACKAGE``,
``FLOOR_PACKAGE``, ``PRESERVE_REMAINDER``) use ``multiple`` - the package size.

``DOWN`` rounds towards negative infinity and ``UP`` towards positive infinity;
for the non-negative quantities used in manufacturing these are floor/ceiling.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
)
from enum import Enum
from typing import Any, Union

from ..exceptions import ValidationError
from .numeric import calc_context, to_decimal


class RoundingPolicy(str, Enum):
    NONE = "none"
    HALF_UP = "half_up"
    HALF_EVEN = "half_even"
    DOWN = "down"
    UP = "up"
    CEILING_PACKAGE = "ceiling_package"
    FLOOR_PACKAGE = "floor_package"
    PRESERVE_REMAINDER = "preserve_remainder"

    @classmethod
    def parse(cls, value: Union["RoundingPolicy", str, None]) -> "RoundingPolicy":
        if value is None:
            return cls.NONE
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower().replace("-", "_").replace(" ", "_"))
        except ValueError:
            raise ValidationError(
                "Unknown rounding policy %r. Valid: %s."
                % (value, ", ".join(p.value for p in cls)),
                code="INVALID_ROUNDING_POLICY",
                field="rounding",
            ) from None


_DECIMAL_MODES = {
    RoundingPolicy.HALF_UP: ROUND_HALF_UP,
    RoundingPolicy.HALF_EVEN: ROUND_HALF_EVEN,
    RoundingPolicy.DOWN: ROUND_FLOOR,
    RoundingPolicy.UP: ROUND_CEILING,
}


@dataclass(frozen=True)
class RoundedValue:
    """A rounded value together with the original and the difference."""

    original: Decimal
    rounded: Decimal
    remainder: Decimal  # original - rounded
    policy: RoundingPolicy


def round_value(
    value: Any,
    policy: Union[RoundingPolicy, str, None] = RoundingPolicy.NONE,
    *,
    places: int = 0,
    multiple: Any = 1,
) -> Decimal:
    """Apply ``policy`` to ``value`` and return the rounded Decimal."""
    policy = RoundingPolicy.parse(policy)
    d = to_decimal(value)
    if policy is RoundingPolicy.NONE:
        return d
    if policy in (
        RoundingPolicy.CEILING_PACKAGE,
        RoundingPolicy.FLOOR_PACKAGE,
        RoundingPolicy.PRESERVE_REMAINDER,
    ):
        m = to_decimal(multiple, field="multiple")
        if m <= 0:
            raise ValidationError(
                "Package size (multiple) must be greater than zero.",
                code="INVALID_PACKAGE_SIZE",
                field="multiple",
            )
        with calc_context():
            q = d / m
            mode = ROUND_CEILING if policy is RoundingPolicy.CEILING_PACKAGE else ROUND_FLOOR
            return q.to_integral_value(rounding=mode) * m
    if not isinstance(places, int) or isinstance(places, bool) or places < 0:
        raise ValidationError(
            "places must be a non-negative integer.", code="INVALID_PLACES", field="places"
        )
    with calc_context():
        return d.quantize(Decimal(1).scaleb(-places), rounding=_DECIMAL_MODES[policy])


def round_with_remainder(
    value: Any,
    policy: Union[RoundingPolicy, str, None],
    *,
    places: int = 0,
    multiple: Any = 1,
) -> RoundedValue:
    """Like :func:`round_value` but also report what was rounded away.

    With ``PRESERVE_REMAINDER`` the value is split into whole packages and the
    leftover is kept in ``remainder`` instead of being discarded.
    """
    policy = RoundingPolicy.parse(policy)
    original = to_decimal(value)
    rounded = round_value(original, policy, places=places, multiple=multiple)
    with calc_context():
        remainder = original - rounded
    return RoundedValue(original, rounded, remainder, policy)
