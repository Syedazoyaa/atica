"""Numeric precision handling shared by every ATICA module.

Design
------
* Public numbers are :class:`~decimal.Decimal` - never binary ``float`` results.
* Inside calculations ATICA uses exact rational arithmetic
  (:class:`fractions.Fraction`) so that repeating decimals (``1/3``, ``5/9``)
  never accumulate error, and floor/ceiling decisions are made on the *exact*
  value.  A result is converted back to ``Decimal`` once, at the end.
* Only that final division can be inexact.  It is rounded half-even to
  ``get_precision()`` significant digits (default :data:`DEFAULT_PRECISION`).
  Precision is configurable per call-tree with :func:`use_precision` and is
  stored in a :class:`contextvars.ContextVar`, so it is thread- and
  task-safe and there is no process-wide mutable state.
"""

from __future__ import annotations

import contextlib
import decimal
from contextvars import ContextVar
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterator, Union

from .exceptions import InvalidQuantityError, NumericRangeError

#: Significant digits for results that cannot be represented exactly.
#: 50 digits is far beyond any physical meaning, yet cheap.
DEFAULT_PRECISION = 50
MIN_PRECISION = 5
MAX_PRECISION = 1000

#: Inputs whose decimal exponent is larger than this are rejected (about 1e300).
MAX_MAGNITUDE = 300

_precision: ContextVar[int] = ContextVar("atica_precision", default=DEFAULT_PRECISION)

Number = Union[int, float, str, Decimal, Fraction]


def get_precision() -> int:
    """Return the number of significant digits used for inexact results."""
    return _precision.get()


@contextlib.contextmanager
def use_precision(digits: int) -> Iterator[int]:
    """Temporarily set the precision (significant digits) for ATICA calculations.

    >>> from atica.core import use_precision
    >>> with use_precision(10):
    ...     pass
    """
    if (
        not isinstance(digits, int)
        or isinstance(digits, bool)
        or not (MIN_PRECISION <= digits <= MAX_PRECISION)
    ):
        raise InvalidQuantityError(
            "precision must be an integer between %d and %d (got %r)."
            % (MIN_PRECISION, MAX_PRECISION, digits),
            parameter="digits",
        )
    token = _precision.set(digits)
    try:
        yield digits
    finally:
        _precision.reset(token)


def _context() -> decimal.Context:
    return decimal.Context(
        prec=get_precision(),
        rounding=decimal.ROUND_HALF_EVEN,
        Emin=-999_999,
        Emax=999_999,
        traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow],
    )


def to_decimal(value: Any, name: str = "value") -> Decimal:
    """Convert ``value`` to a finite :class:`~decimal.Decimal`, or raise.

    Accepts ``int``, ``Decimal``, ``Fraction``, numeric ``str`` and ``float``.
    A float is converted through ``repr`` (so ``0.1`` is ``Decimal('0.1')``, not
    its binary expansion) - pass strings or Decimals when you need exactness
    beyond what a float carries.  ``bool``, ``None``, NaN and infinities are
    rejected, as are magnitudes beyond about ``1e300``.
    """
    if isinstance(value, bool) or value is None:
        raise InvalidQuantityError(
            "%r is not a valid number." % (value,),
            parameter=name,
            hint="Pass an int, Decimal, float or numeric string.",
        )
    try:
        if isinstance(value, Decimal):
            result = value
        elif isinstance(value, int):
            result = Decimal(value)
        elif isinstance(value, float):
            result = Decimal(repr(value))
        elif isinstance(value, Fraction):
            result = fraction_to_decimal(check_fraction_magnitude(value, name))
        elif isinstance(value, str):
            result = Decimal(value.strip())
        else:
            raise TypeError
    except (decimal.InvalidOperation, ValueError, TypeError):
        raise InvalidQuantityError(
            "%r is not a valid number." % (value,),
            parameter=name,
            hint="Pass an int, Decimal, float or numeric string such as '12.5'.",
        ) from None
    if not result.is_finite():
        raise InvalidQuantityError(
            "%r is not a finite number." % (value,), parameter=name, hint="NaN and infinity are not allowed."
        )
    if not result.is_zero() and abs(result.adjusted()) > MAX_MAGNITUDE:
        raise NumericRangeError(
            "%s is outside the supported range (about 1e-%d to 1e%d)." % (name, MAX_MAGNITUDE, MAX_MAGNITUDE),
            parameter=name,
        )
    return result


def to_fraction(value: Any, name: str = "value") -> Fraction:
    """Exact rational value of a number; also accepts ``'a/b'`` strings.

    >>> to_fraction("5/9")
    Fraction(5, 9)
    """
    if isinstance(value, Fraction):
        return check_fraction_magnitude(value, name)
    if isinstance(value, str) and "/" in value:
        left, _, right = value.partition("/")
        num, den = to_fraction(left, name), to_fraction(right, name)
        if den == 0:
            raise InvalidQuantityError("%r has a zero denominator." % value, parameter=name)
        return check_fraction_magnitude(num / den, name)
    return Fraction(to_decimal(value, name))


_FRACTION_LOW = Fraction(1, 10**MAX_MAGNITUDE)
_FRACTION_HIGH = Fraction(10 ** (MAX_MAGNITUDE + 1))


def check_fraction_magnitude(value: Fraction, name: str = "value") -> Fraction:
    """Apply the same magnitude limits to an exact fraction as to Decimal/int/float input.

    Non-zero values must satisfy ``1e-300 <= |value| < 1e301`` (the same as ``|Decimal.adjusted()| <= 300``).
    The check is exact; the fraction itself is returned unchanged.
    """
    if value != 0 and not (_FRACTION_LOW <= abs(value) < _FRACTION_HIGH):
        raise NumericRangeError(
            "%s is outside the supported range (about 1e-%d to 1e%d)." % (name, MAX_MAGNITUDE, MAX_MAGNITUDE),
            parameter=name,
        )
    return value


def fraction_to_decimal(value: Fraction) -> Decimal:
    """Convert an exact fraction to Decimal (one rounding, at ``get_precision()`` digits)."""
    if value.denominator == 1:
        return Decimal(value.numerator)
    ctx = _context()
    try:
        return ctx.divide(Decimal(value.numerator), Decimal(value.denominator))
    except decimal.DecimalException as exc:
        raise NumericRangeError("Result is outside the representable range.") from exc


def normalize(value: Decimal) -> Decimal:
    """Strip trailing zeros without switching to exponent notation for integers.

    ``Decimal('2500.00')`` -> ``Decimal('2500')``; ``Decimal('0.50')`` -> ``Decimal('0.5')``.
    """
    if value.is_zero():
        return Decimal(0)
    n = value.normalize(decimal.Context(prec=max(get_precision(), len(value.as_tuple().digits)) + 2))
    if n.as_tuple().exponent > 0:  # type: ignore[operator]
        return Decimal(int(n))
    return n


def dec(value: Fraction) -> Decimal:
    """Fraction -> normalised Decimal. The standard way results leave a calculation."""
    return normalize(fraction_to_decimal(value))


def display_decimal(value: Decimal, max_places: int = 10) -> str:
    """Human-friendly text of ``value``: at most ``max_places`` decimals, trailing zeros removed.

    Display only - the stored value keeps its full precision.
    """
    quantum = Decimal(1).scaleb(-max_places)
    ctx = decimal.Context(prec=max(get_precision(), len(value.as_tuple().digits)) + max_places + 2)
    exponent = value.as_tuple().exponent
    shorten = isinstance(exponent, int) and exponent < -max_places
    text = format(value.quantize(quantum, context=ctx) if shorten else value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_decimal(value: Decimal, places: Union[int, None] = None) -> str:
    """Plain (never scientific) text of a Decimal; ``places`` pads/rounds for display only."""
    if places is not None:
        from .rounding import round_value

        return format(round_value(value, "half_up", places), "f")
    return format(normalize(value), "f")
