"""Argument validation shared by all modules.

Every function raises a specific :class:`~atica.core.exceptions.ValidationError`
subclass naming the offending parameter, and returns the cleaned value:
``Fraction`` for numbers (exact; see :mod:`atica.core.precision`), ``str`` for text.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Optional

from .exceptions import (
    InvalidPercentageError,
    InvalidQuantityError,
    MissingInputError,
    ValidationError,
)
from .precision import to_fraction

_HUNDRED = Fraction(100)


def require(value: Any, name: str, hint: Optional[str] = None) -> Any:
    """Return ``value`` unless it is ``None``."""
    if value is None:
        raise MissingInputError("%s is required." % name, parameter=name, hint=hint)
    return value


def number(
    value: Any,
    name: str,
    *,
    minimum: Optional[Any] = None,
    inclusive: bool = True,
    maximum: Optional[Any] = None,
) -> Fraction:
    """Validate a finite number and optionally a lower/upper bound.

    ``inclusive`` applies to ``minimum`` only (``maximum`` is always inclusive).
    """
    require(value, name)
    n = to_fraction(value, name)
    if minimum is not None:
        low = Fraction(minimum)
        if n < low or (not inclusive and n == low):
            relation = "at least" if inclusive else "greater than"
            raise InvalidQuantityError(
                "%s must be %s %s (got %s)." % (name, relation, _show(low), _show(n)),
                parameter=name,
            )
    if maximum is not None and n > Fraction(maximum):
        raise InvalidQuantityError(
            "%s must be at most %s (got %s)." % (name, _show(Fraction(maximum)), _show(n)), parameter=name
        )
    return n


def non_negative(value: Any, name: str) -> Fraction:
    """A number ``>= 0``."""
    n = number(value, name)
    if n < 0:
        raise InvalidQuantityError(
            "%s must not be negative (got %s)." % (name, _show(n)),
            parameter=name,
            hint="Quantities cannot be negative.",
        )
    return n


def positive(value: Any, name: str) -> Fraction:
    """A number ``> 0``."""
    n = number(value, name)
    if n <= 0:
        raise InvalidQuantityError(
            "%s must be greater than zero (got %s)." % (name, _show(n)), parameter=name
        )
    return n


def whole_number(value: Any, name: str, *, minimum: int = 0) -> int:
    """An integer-valued number ``>= minimum`` (``3`` and ``Decimal('3.0')`` both give ``3``)."""
    n = number(value, name)
    if n.denominator != 1:
        raise InvalidQuantityError("%s must be a whole number (got %s)." % (name, _show(n)), parameter=name)
    if n < minimum:
        raise InvalidQuantityError(
            "%s must be at least %d (got %s)." % (name, minimum, _show(n)), parameter=name
        )
    return int(n)


def percentage(value: Any, name: str, *, allow_100: bool = True, default: Optional[Any] = None) -> Fraction:
    """A percentage in ``[0, 100]`` (or ``[0, 100)`` when ``allow_100`` is false).

    Percentages are always on the 0-100 scale: ``5`` means 5 %, not 500 %.
    Returns the percentage itself (not a fraction of 1).
    """
    if value is None:
        if default is None:
            require(value, name)
        value = default
    p = to_fraction(value, name)
    if p < 0 or p > _HUNDRED or (not allow_100 and p == _HUNDRED):
        upper = "100" if allow_100 else "below 100"
        raise InvalidPercentageError(
            "%s must be between 0 and %s percent (got %s)." % (name, upper, _show(p)),
            parameter=name,
            hint="Percentages use the 0-100 scale: write 5 for 5%%, not 0.05.",
        )
    return p


def text(value: Any, name: str, *, max_length: int = 200) -> str:
    """A non-empty string without leading/trailing whitespace."""
    require(value, name)
    if not isinstance(value, str):
        raise ValidationError("%s must be text (got %s)." % (name, type(value).__name__), parameter=name)
    cleaned = value.strip()
    if not cleaned:
        raise MissingInputError("%s must not be empty." % name, parameter=name)
    if len(cleaned) > max_length:
        raise ValidationError("%s is longer than %d characters." % (name, max_length), parameter=name)
    return cleaned


def _show(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    from .precision import fraction_to_decimal

    return format(fraction_to_decimal(value).normalize(), "f")
