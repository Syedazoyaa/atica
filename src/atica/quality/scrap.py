"""Scrap quantity/percentage, expected output and required input.

Terminology (used consistently by the whole ``quality`` package)
----------------------------------------------------------------
* **scrap**    - units that are rejected and *not* recovered.
* **rework**   - units that fail first inspection but are reprocessed (see :mod:`atica.quality.yields`).
* **recovery** - material reclaimed from waste (see :mod:`atica.quality.wastage`).
* **wastage**  - material that does not end up in good output (see :mod:`atica.quality.wastage`).

``scrap_percent`` always means **scrap / input x 100**, where *input* is the quantity
started.  All percentages use the 0-100 scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Tuple

from ..core.exceptions import ConstraintError, ValidationError, ZeroDenominatorError
from ..core.precision import dec, display_decimal
from ..core.results import Result
from ..core.rounding import Rounding, resolve_rounding, round_fraction
from ..core.validation import non_negative, percentage

_ONE = Fraction(1)
_HUNDRED = Fraction(100)


@dataclass(frozen=True)
class QualityQuantity(Result):
    """A calculated quantity (``quantity``) with its unrounded value and formula."""

    quantity: Decimal
    exact_quantity: Decimal
    unit: str
    scrap_percent: Decimal
    rounding: Rounding
    places: int
    formula: str
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        text = display_decimal(self.quantity)
        return "%s %s" % (text, self.unit) if self.unit else text


@dataclass(frozen=True)
class PercentageResult(Result):
    """A percentage together with the numbers and the **denominator** it was computed from."""

    percent: Decimal
    numerator: Decimal
    denominator: Decimal
    denominator_meaning: str
    formula: str
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return "%s%%" % display_decimal(self.percent)


def _out(exact: Fraction, rounding: Any, places: int) -> tuple[Decimal, Rounding, int]:
    policy, places = resolve_rounding(rounding, places)
    value = round_fraction(exact, policy, places) if policy is not Rounding.NONE else dec(exact)
    return value, policy, places


def calculate_scrap_quantity(
    input_quantity: Any, scrap_percent: Any, *, rounding: Any = Rounding.NONE, places: int = 0, unit: str = ""
) -> QualityQuantity:
    """Scrap expected from ``input_quantity`` started: ``input x scrap% / 100``.

    >>> str(calculate_scrap_quantity(1000, 5))
    '50'
    """
    q = non_negative(input_quantity, "input_quantity")
    s = percentage(scrap_percent, "scrap_percent")
    exact = q * s / _HUNDRED
    value, policy, places = _out(exact, rounding, places)
    return QualityQuantity(value, dec(exact), unit, dec(s), policy, places, "scrap = input x scrap% / 100")


def calculate_expected_output(
    input_quantity: Any, scrap_percent: Any, *, rounding: Any = Rounding.NONE, places: int = 0, unit: str = ""
) -> QualityQuantity:
    """Expected good output from ``input_quantity`` started: ``input x (1 - scrap%/100)``.

    A 100 % scrap rate is valid and gives zero good output.

    >>> str(calculate_expected_output(1000, 5))
    '950'
    """
    q = non_negative(input_quantity, "input_quantity")
    s = percentage(scrap_percent, "scrap_percent")
    exact = q * (_ONE - s / _HUNDRED)
    value, policy, places = _out(exact, rounding, places)
    return QualityQuantity(value, dec(exact), unit, dec(s), policy, places, "good = input x (1 - scrap%/100)")


def calculate_required_input(
    good_output: Any, scrap_percent: Any, *, rounding: Any = Rounding.NONE, places: int = 0, unit: str = ""
) -> QualityQuantity:
    """Quantity to start to obtain ``good_output`` good units: ``good / (1 - scrap%/100)``.

    Use ``rounding='ceiling'`` for whole units that still guarantee the target.

    :raises ConstraintError: ``scrap_percent`` is 100 and ``good_output`` is positive (impossible).

    >>> str(calculate_required_input(950, 5))
    '1000'
    """
    g = non_negative(good_output, "good_output")
    s = percentage(scrap_percent, "scrap_percent")
    if s == _HUNDRED:
        if g > 0:
            raise ConstraintError(
                "With 100%% scrap no amount of input yields %s good units." % good_output,
                parameter="scrap_percent",
                hint="Scrap must be below 100% to produce good output.",
            )
        exact = Fraction(0)
    else:
        exact = g / (_ONE - s / _HUNDRED)
    value, policy, places = _out(exact, rounding, places)
    return QualityQuantity(value, dec(exact), unit, dec(s), policy, places, "input = good / (1 - scrap%/100)")


def calculate_scrap_percentage(input_quantity: Any, scrap_quantity: Any) -> PercentageResult:
    """Scrap as a percentage of the quantity started: ``scrap / input x 100``.

    :raises ZeroDenominatorError: ``input_quantity`` is 0 (the percentage is undefined).
    :raises ValidationError: ``scrap_quantity`` exceeds ``input_quantity``.

    >>> str(calculate_scrap_percentage(1000, 50))
    '5%'
    """
    q = non_negative(input_quantity, "input_quantity")
    s = non_negative(scrap_quantity, "scrap_quantity")
    if q == 0:
        raise ZeroDenominatorError(
            "Scrap percentage is undefined when the input quantity is 0.",
            parameter="input_quantity",
            hint="Provide a positive input quantity.",
        )
    if s > q:
        raise ValidationError(
            "scrap_quantity (%s) cannot exceed input_quantity (%s)." % (scrap_quantity, input_quantity),
            parameter="scrap_quantity",
        )
    return PercentageResult(
        dec(s / q * _HUNDRED), dec(s), dec(q), "input quantity (units started)", "scrap / input x 100"
    )
