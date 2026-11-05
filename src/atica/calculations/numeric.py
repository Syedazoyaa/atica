"""Decimal helpers shared by every ATICA module.

Three precisions are kept apart:

* **calculation precision** - ``CALC_PRECISION`` digits used inside arithmetic;
* **result precision**     - results are cleaned to ``RESULT_DIGITS`` significant
  digits to remove representation noise (e.g. ``5/9``);
* **display precision**    - applied only when formatting (``format_quantity``).
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Any

from ..exceptions import InvalidQuantityError

CALC_PRECISION = 60
RESULT_DIGITS = 28
MAX_EXPONENT = 300

_FRACTION_RE = re.compile(r"^\s*([+-]?[0-9.]+(?:[eE][+-]?\d+)?)\s*/\s*([+-]?[0-9.]+(?:[eE][+-]?\d+)?)\s*$")


@contextmanager
def calc_context(prec: int = CALC_PRECISION):
    """Context manager giving a high-precision Decimal context."""
    with localcontext() as ctx:
        ctx.prec = prec
        yield ctx


def to_decimal(value: Any, *, field: str = "value", allow_fraction: bool = False) -> Decimal:
    """Convert ``value`` to a finite :class:`~decimal.Decimal`.

    Accepts ``int``, ``float`` (through ``repr`` so ``0.1`` stays ``0.1``),
    ``Decimal``, ``Fraction`` and numeric strings. Booleans, NaN, infinities and
    absurdly large exponents are rejected with :class:`InvalidQuantityError`.
    """
    try:
        if isinstance(value, bool) or value is None:
            raise InvalidOperation
        if isinstance(value, Decimal):
            result = value
        elif isinstance(value, int):
            result = Decimal(value)
        elif isinstance(value, float):
            result = Decimal(repr(value))
        elif isinstance(value, Fraction):
            with calc_context():
                result = Decimal(value.numerator) / Decimal(value.denominator)
        elif isinstance(value, str):
            text = value.strip()
            match = _FRACTION_RE.match(text) if allow_fraction else None
            if match:
                with calc_context():
                    result = Decimal(match.group(1)) / Decimal(match.group(2))
            else:
                result = Decimal(text)
        else:
            raise InvalidOperation
    except (InvalidOperation, ValueError, ZeroDivisionError):
        raise InvalidQuantityError(
            "%r is not a valid number." % (value,), code="INVALID_NUMBER", field=field
        ) from None
    if not result.is_finite():
        raise InvalidQuantityError(
            "%r is not a finite number." % (value,), code="INVALID_NUMBER", field=field
        )
    if result != 0 and abs(result.adjusted()) > MAX_EXPONENT:
        raise InvalidQuantityError(
            "%r is outside the supported numeric range." % (value,),
            code="NUMBER_OUT_OF_RANGE",
            field=field,
        )
    return result


def normalize(value: Decimal) -> Decimal:
    """Strip trailing zeros and exponents: ``Decimal('2500.00')`` -> ``Decimal('2500')``."""
    if value == 0:
        return Decimal(0)
    with calc_context():
        n = value.normalize()
        if n.as_tuple().exponent > 0:
            n = n.quantize(Decimal(1))
    return n


def clean(value: Decimal) -> Decimal:
    """Round to ``RESULT_DIGITS`` significant digits and normalise."""
    with calc_context(RESULT_DIGITS):
        value = +value
    return normalize(value)


def format_quantity(value: Decimal, places: "int | None" = None) -> str:
    """Format a Decimal as plain text (never scientific notation).

    ``places`` is *display* precision only; the value itself is untouched.
    """
    from decimal import ROUND_HALF_UP

    if places is not None:
        with calc_context():
            value = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        return format(value, "f")
    return format(normalize(value), "f")


def plain_number(value: Decimal):
    """Return ``int`` for integral values and the normalised Decimal otherwise."""
    n = normalize(value)
    if n == n.to_integral_value():
        return int(n)
    return n
