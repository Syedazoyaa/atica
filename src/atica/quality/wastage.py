"""Material wastage and recovery.

* **wastage** is material that does not end up in the good output:
  ``gross_wastage = material_input - material_in_output`` (it includes the material of scrapped units).
* **recovery** is the part of that waste that is reclaimed and reusable (regrind, offcuts back to stock).
* ``net_wastage = gross_wastage - recovered`` is what is truly lost.

Denominators: ``gross_wastage_percent`` and ``net_wastage_percent`` are percentages of
``material_input``; ``recovery_percent`` is a percentage of ``gross_wastage``.
All quantities must be expressed in the same unit (``unit`` is only a label).
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
class RecoveryResult(Result):
    """Result of :func:`calculate_material_recovery` (denominator of ``recovery_percent``: the waste)."""

    waste_quantity: Decimal
    recovered_quantity: Decimal
    unrecovered_quantity: Decimal
    recovery_percent: Decimal
    unit: str = ""
    formula: str = "recovered = waste x recovery% / 100"
    warnings: Tuple[str, ...] = ()


def calculate_material_recovery(
    waste_quantity: Any, recovery_percent: Any, *, unit: str = ""
) -> RecoveryResult:
    """Material reclaimed from ``waste_quantity``: ``waste x recovery% / 100``.

    >>> str(calculate_material_recovery(200, 40).recovered_quantity)
    '80'
    """
    w = non_negative(waste_quantity, "waste_quantity")
    p = percentage(recovery_percent, "recovery_percent")
    rec = w * p / _HUNDRED
    return RecoveryResult(dec(w), dec(rec), dec(w - rec), dec(p), unit)


@dataclass(frozen=True)
class WastageResult(Result):
    """Result of :func:`calculate_wastage` (see the module docstring for the definitions)."""

    material_input: Decimal
    material_in_output: Decimal
    gross_wastage: Decimal
    recovered: Decimal
    net_wastage: Decimal
    gross_wastage_percent: Decimal
    net_wastage_percent: Decimal
    utilisation_percent: Decimal
    recovery_percent: Optional[Decimal]
    unit: str = ""
    formula: str = "gross = input - in_output; net = gross - recovered; percentages are of input"
    warnings: Tuple[str, ...] = ()


def calculate_wastage(
    material_input: Any,
    material_in_output: Any,
    *,
    recovered_quantity: Any = None,
    recovery_percent: Any = None,
    unit: str = "",
) -> WastageResult:
    """Material wastage of a process, optionally net of recovered material.

    :param material_input: material consumed (``> 0``).
    :param material_in_output: material contained in the good output (``<= material_input``).
    :param recovered_quantity: material reclaimed from the waste (absolute), **or**
    :param recovery_percent: % of the gross wastage that is reclaimed - give at most one.
    :raises ZeroDenominatorError: ``material_input`` is 0.
    :raises InvalidConfigurationError: both recovery arguments given.
    :raises ValidationError: output exceeds input, or recovery exceeds the waste.

    >>> r = calculate_wastage(1000, 920, recovery_percent=25)
    >>> (str(r.gross_wastage), str(r.net_wastage), str(r.net_wastage_percent))
    ('80', '60', '6')
    """
    total = non_negative(material_input, "material_input")
    if total == 0:
        raise ZeroDenominatorError(
            "Wastage percentages are undefined when the material input is 0.", parameter="material_input"
        )
    used = non_negative(material_in_output, "material_in_output")
    if used > total:
        raise ValidationError(
            "material_in_output (%s) cannot exceed material_input (%s)."
            % (material_in_output, material_input),
            parameter="material_in_output",
            hint="Material cannot be created by the process.",
        )
    if recovered_quantity is not None and recovery_percent is not None:
        raise InvalidConfigurationError(
            "Give recovered_quantity or recovery_percent, not both.", parameter="recovery_percent"
        )
    gross = total - used
    if recovery_percent is not None:
        recovered = gross * percentage(recovery_percent, "recovery_percent") / _HUNDRED
    elif recovered_quantity is not None:
        recovered = non_negative(recovered_quantity, "recovered_quantity")
        if recovered > gross:
            raise ValidationError(
                "recovered_quantity (%s) exceeds the gross wastage (%s)." % (recovered_quantity, dec(gross)),
                parameter="recovered_quantity",
            )
    else:
        recovered = Fraction(0)
    net = gross - recovered
    return WastageResult(
        material_input=dec(total),
        material_in_output=dec(used),
        gross_wastage=dec(gross),
        recovered=dec(recovered),
        net_wastage=dec(net),
        gross_wastage_percent=dec(gross / total * _HUNDRED),
        net_wastage_percent=dec(net / total * _HUNDRED),
        utilisation_percent=dec(used / total * _HUNDRED),
        recovery_percent=dec(recovered / gross * _HUNDRED) if gross else None,
        unit=unit,
        warnings=() if gross else ("There is no wastage; recovery_percent is not applicable.",),
    )
