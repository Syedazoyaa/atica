"""First-pass yield, final yield and rework.

Every unit started has exactly one first-pass outcome::

    input = good_first_pass + sent_to_rework + first_pass_scrap

Units sent to rework are then either *recovered* (become good) or scrapped::

    sent_to_rework = recovered_from_rework + rework_scrap

so a reworked unit is counted **once**: it is never in ``good_first_pass`` and,
once recovered, it is in ``final_good`` but not in ``final_scrap``::

    final_good  = good_first_pass + recovered_from_rework
    final_scrap = first_pass_scrap + rework_scrap

Denominators
------------
``first_pass_yield_percent`` = good_first_pass / input; ``final_yield_percent`` =
final_good / input; ``rework_percent`` = sent_to_rework / input; ``scrap_percent`` =
final_scrap / input; ``rework_recovery_percent`` = recovered / **sent_to_rework**
(``None`` when nothing was reworked).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Optional, Tuple

from ..core.exceptions import InvalidConfigurationError, ValidationError, ZeroDenominatorError
from ..core.precision import dec
from ..core.results import Result
from ..core.validation import non_negative, percentage

_HUNDRED = Fraction(100)


@dataclass(frozen=True)
class YieldResult(Result):
    """Outcome of a production run (see the module docstring for definitions)."""

    input_quantity: Decimal
    good_first_pass: Decimal
    sent_to_rework: Decimal
    recovered_from_rework: Decimal
    first_pass_scrap: Decimal
    rework_scrap: Decimal
    final_good: Decimal
    final_scrap: Decimal
    first_pass_yield_percent: Decimal
    final_yield_percent: Decimal
    rework_percent: Decimal
    scrap_percent: Decimal
    rework_recovery_percent: Optional[Decimal]
    unit: str = ""
    formula: str = "first-pass yield = good_first_pass / input x 100; final yield = (good_first_pass + recovered) / input x 100"
    warnings: Tuple[str, ...] = ()


def calculate_yield(
    input_quantity: Any,
    good_first_pass: Any,
    *,
    sent_to_rework: Any = 0,
    recovered_from_rework: Any = 0,
    first_pass_scrap: Any = None,
    unit: str = "",
) -> YieldResult:
    """First-pass and final yield of a run.

    :param input_quantity: units started (``> 0``; zero would make every percentage undefined).
    :param good_first_pass: units that passed inspection the first time.
    :param sent_to_rework: units that failed but were sent to rework.
    :param recovered_from_rework: of those, units that became good after rework.
    :param first_pass_scrap: optional; units scrapped at first inspection.  If given it must equal
        ``input - good_first_pass - sent_to_rework`` (a consistency check); if omitted it is derived.
    :raises ZeroDenominatorError: ``input_quantity`` is 0.
    :raises ValidationError: the quantities contradict each other.

    >>> r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
    >>> (str(r.first_pass_yield_percent), str(r.final_yield_percent), str(r.scrap_percent))
    ('90', '94.5', '5.5')
    """
    total = non_negative(input_quantity, "input_quantity")
    if total == 0:
        raise ZeroDenominatorError(
            "Yield is undefined when the input quantity is 0.",
            parameter="input_quantity",
            hint="Provide a positive input quantity.",
        )
    good = non_negative(good_first_pass, "good_first_pass")
    rework = non_negative(sent_to_rework, "sent_to_rework")
    recovered = non_negative(recovered_from_rework, "recovered_from_rework")
    if good + rework > total:
        raise ValidationError(
            "good_first_pass (%s) + sent_to_rework (%s) exceeds input_quantity (%s)."
            % (good_first_pass, sent_to_rework, input_quantity),
            parameter="good_first_pass",
            hint="Each unit has one first-pass outcome: good, rework or scrap.",
        )
    if recovered > rework:
        raise ValidationError(
            "recovered_from_rework (%s) exceeds sent_to_rework (%s)."
            % (recovered_from_rework, sent_to_rework),
            parameter="recovered_from_rework",
            hint="You cannot recover more units than were reworked.",
        )
    direct_scrap = total - good - rework
    if first_pass_scrap is not None and non_negative(first_pass_scrap, "first_pass_scrap") != direct_scrap:
        raise ValidationError(
            "first_pass_scrap (%s) does not match input - good_first_pass - sent_to_rework (%s)."
            % (first_pass_scrap, dec(direct_scrap)),
            parameter="first_pass_scrap",
        )
    rework_scrap = rework - recovered
    final_good = good + recovered
    final_scrap = direct_scrap + rework_scrap
    return YieldResult(
        input_quantity=dec(total),
        good_first_pass=dec(good),
        sent_to_rework=dec(rework),
        recovered_from_rework=dec(recovered),
        first_pass_scrap=dec(direct_scrap),
        rework_scrap=dec(rework_scrap),
        final_good=dec(final_good),
        final_scrap=dec(final_scrap),
        first_pass_yield_percent=dec(good / total * _HUNDRED),
        final_yield_percent=dec(final_good / total * _HUNDRED),
        rework_percent=dec(rework / total * _HUNDRED),
        scrap_percent=dec(final_scrap / total * _HUNDRED),
        rework_recovery_percent=dec(recovered / rework * _HUNDRED) if rework else None,
        unit=unit,
        warnings=()
        if rework
        else ("Nothing was sent to rework; rework_recovery_percent is not applicable.",),
    )


@dataclass(frozen=True)
class ReworkProjection(Result):
    """Expected outcome of ``input_quantity`` given first-pass yield, rework and recovery rates.

    Values are *expected* (statistical) quantities and may be fractional; they are not rounded
    so that ``final_good + final_scrap == input_quantity`` holds exactly.
    """

    input_quantity: Decimal
    good_first_pass: Decimal
    sent_to_rework: Decimal
    first_pass_scrap: Decimal
    recovered_from_rework: Decimal
    rework_scrap: Decimal
    final_good: Decimal
    final_scrap: Decimal
    first_pass_yield_percent: Decimal
    final_yield_percent: Decimal
    scrap_percent: Decimal
    unit: str = ""
    formula: str = "final yield = first-pass yield + rework% x recovery%/100"
    warnings: Tuple[str, ...] = ()


def calculate_rework(
    input_quantity: Any,
    *,
    first_pass_yield_percent: Any,
    rework_percent: Any = 0,
    rework_recovery_percent: Any = 100,
    unit: str = "",
) -> ReworkProjection:
    """Project good output and scrap when part of the failures are reworked.

    :param first_pass_yield_percent: % of input that is good first time (denominator: input).
    :param rework_percent: % of input sent to rework (denominator: input).
    :param rework_recovery_percent: % of the *reworked* units that become good (denominator: reworked units).
    :raises InvalidConfigurationError: ``first_pass_yield_percent + rework_percent`` exceeds 100.

    Formula: ``final yield = FPY + rework% x recovery% / 100``; scrap is the rest.

    >>> p = calculate_rework(1000, first_pass_yield_percent=90, rework_percent=6, rework_recovery_percent=75)
    >>> (str(p.final_good), str(p.final_scrap))
    ('945', '55')
    """
    total = non_negative(input_quantity, "input_quantity")
    fpy = percentage(first_pass_yield_percent, "first_pass_yield_percent")
    rw = percentage(rework_percent, "rework_percent")
    rec = percentage(rework_recovery_percent, "rework_recovery_percent")
    if fpy + rw > _HUNDRED:
        raise InvalidConfigurationError(
            "first_pass_yield_percent (%s) + rework_percent (%s) exceeds 100."
            % (first_pass_yield_percent, rework_percent),
            parameter="rework_percent",
            hint="Every unit is good, reworked or scrapped on first inspection.",
        )
    good = total * fpy / _HUNDRED
    sent = total * rw / _HUNDRED
    direct = total - good - sent
    recovered = sent * rec / _HUNDRED
    rework_scrap = sent - recovered
    final_good = good + recovered
    final_scrap = direct + rework_scrap
    return ReworkProjection(
        input_quantity=dec(total),
        good_first_pass=dec(good),
        sent_to_rework=dec(sent),
        first_pass_scrap=dec(direct),
        recovered_from_rework=dec(recovered),
        rework_scrap=dec(rework_scrap),
        final_good=dec(final_good),
        final_scrap=dec(final_scrap),
        first_pass_yield_percent=dec(fpy),
        final_yield_percent=dec(fpy + rw * rec / _HUNDRED),
        scrap_percent=dec(_HUNDRED - fpy - rw * rec / _HUNDRED),
        unit=unit,
    )


def required_input_with_rework(
    good_output: Any,
    *,
    first_pass_yield_percent: Any,
    rework_percent: Any = 0,
    rework_recovery_percent: Any = 100,
) -> Decimal:
    """Units to start to obtain ``good_output`` final good units: ``good / final_yield``.

    :raises ZeroDenominatorError: the final yield is 0 and ``good_output`` is positive.
    """
    g = non_negative(good_output, "good_output")
    probe = calculate_rework(
        1,
        first_pass_yield_percent=first_pass_yield_percent,
        rework_percent=rework_percent,
        rework_recovery_percent=rework_recovery_percent,
    )
    final = Fraction(probe.final_yield_percent) / _HUNDRED
    if g == 0:
        return Decimal(0)
    if final == 0:
        raise ZeroDenominatorError(
            "The final yield is 0%, so no input produces good output.", parameter="first_pass_yield_percent"
        )
    return dec(g / final)
