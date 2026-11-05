"""Yield, scrap and wastage calculations (M06).

**Rates are fractions**, not percentages: ``scrap_rate="0.05"`` means 5 %.
Every function that takes ``scrap_rate`` also accepts ``scrap_percent`` (``5``)
- pass only one of the two.

Terminology
-----------
* *scrap*   - finished/semi-finished units rejected and not recoverable;
* *rework*  - units that failed first-pass inspection but are recovered;
* *wastage* - material lost in the process (``input - material in good output``),
  of which scrap is one part and unavoidable process loss the other.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from ..calculations.numeric import calc_context, clean, format_quantity, plain_number
from ..calculations.rounding import RoundingPolicy, round_value
from ..exceptions import ManufacturingError
from ..results import CalculationResult
from ._common import number, resolve_rate


def calculate_required_input(
    good_output: Any,
    scrap_rate: Any = None,
    *,
    scrap_percent: Any = None,
    rounding: Any = RoundingPolicy.NONE,
    places: int = 0,
    multiple: Any = 1,
    unit: Optional[str] = None,
) -> CalculationResult:
    """Input needed to obtain ``good_output`` good units: ``good / (1 - scrap_rate)``.

    >>> str(calculate_required_input(1000, "0.05", rounding="up"))
    '1053'
    """
    good = number(good_output, "good_output", code="INVALID_PRODUCTION_QUANTITY")
    rate = resolve_rate(scrap_rate, scrap_percent)
    policy = RoundingPolicy.parse(rounding)
    with calc_context():
        exact = clean(good / (Decimal(1) - rate))
    value = round_value(exact, policy, places=places, multiple=multiple)
    return CalculationResult(
        output_quantity=value,
        output_unit=unit,
        input_quantity=good,
        input_unit=unit,
        formula="good_output / (1 - scrap_rate)",
        rounding_policy=policy,
        metadata={"scrap_rate": rate, "exact_quantity": exact},
    )


def calculate_expected_output(
    input_quantity: Any,
    scrap_rate: Any = None,
    *,
    scrap_percent: Any = None,
    rounding: Any = RoundingPolicy.NONE,
    places: int = 0,
    multiple: Any = 1,
    unit: Optional[str] = None,
) -> CalculationResult:
    """Expected usable output from ``input_quantity``: ``input * (1 - scrap_rate)``."""
    qty = number(input_quantity, "input_quantity", code="INVALID_PRODUCTION_QUANTITY")
    rate = resolve_rate(scrap_rate, scrap_percent)
    policy = RoundingPolicy.parse(rounding)
    with calc_context():
        exact = clean(qty * (Decimal(1) - rate))
    return CalculationResult(
        output_quantity=round_value(exact, policy, places=places, multiple=multiple),
        output_unit=unit,
        input_quantity=qty,
        input_unit=unit,
        formula="input_quantity x (1 - scrap_rate)",
        rounding_policy=policy,
        metadata={"scrap_rate": rate, "exact_quantity": exact},
    )


def calculate_scrap_quantity(
    total_input: Any,
    scrap_rate: Any = None,
    *,
    scrap_percent: Any = None,
    rounding: Any = RoundingPolicy.NONE,
    places: int = 0,
    unit: Optional[str] = None,
) -> CalculationResult:
    """Scrap expected from ``total_input`` at the given rate."""
    qty = number(total_input, "total_input", code="INVALID_PRODUCTION_QUANTITY")
    rate = resolve_rate(scrap_rate, scrap_percent)
    policy = RoundingPolicy.parse(rounding)
    with calc_context():
        exact = clean(qty * rate)
    return CalculationResult(
        output_quantity=round_value(exact, policy, places=places),
        output_unit=unit,
        input_quantity=qty,
        input_unit=unit,
        formula="total_input x scrap_rate",
        rounding_policy=policy,
        metadata={"scrap_rate": rate, "exact_quantity": exact},
    )


def calculate_scrap_percentage(total_input: Any, scrap_quantity: Any) -> Decimal:
    """Scrap as a percentage of input (``50`` of ``1000`` -> ``5``)."""
    total = number(total_input, "total_input", positive=True, code="INVALID_PRODUCTION_QUANTITY")
    scrap = number(scrap_quantity, "scrap_quantity", code="INVALID_SCRAP_QUANTITY")
    if scrap > total:
        raise ManufacturingError(
            "Scrap quantity (%s) cannot exceed total input (%s)." % (scrap, total), code="INVALID_SCRAP_QUANTITY", field="scrap_quantity"
        )
    with calc_context():
        return clean(scrap / total * 100)


@dataclass(frozen=True)
class YieldResult:
    total_input: Decimal
    good_output: Decimal
    rework_quantity: Decimal
    scrap_quantity: Decimal
    yield_rate: Decimal  # first-pass good / input (fraction)
    scrap_rate: Decimal
    rework_rate: Decimal

    @property
    def yield_percent(self) -> Decimal:
        with calc_context():
            return clean(self.yield_rate * 100)

    @property
    def scrap_percent(self) -> Decimal:
        with calc_context():
            return clean(self.scrap_rate * 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_input": plain_number(self.total_input),
            "good_output": plain_number(self.good_output),
            "rework_quantity": plain_number(self.rework_quantity),
            "scrap_quantity": plain_number(self.scrap_quantity),
            "yield_rate": format_quantity(self.yield_rate),
            "yield_percent": format_quantity(self.yield_percent),
            "scrap_rate": format_quantity(self.scrap_rate),
            "rework_rate": format_quantity(self.rework_rate),
        }


def calculate_yield(total_input: Any, good_output: Any, rework_quantity: Any = 0) -> YieldResult:
    """Production yield. ``scrap = input - good - rework``."""
    total = number(total_input, "total_input", positive=True, code="INVALID_PRODUCTION_QUANTITY")
    good = number(good_output, "good_output", code="INVALID_PRODUCTION_QUANTITY")
    rework = number(rework_quantity, "rework_quantity", code="INVALID_REWORK_QUANTITY")
    if good + rework > total:
        raise ManufacturingError(
            "Good output (%s) plus rework (%s) cannot exceed total input (%s)." % (good, rework, total),
            code="OUTPUT_EXCEEDS_INPUT",
            field="good_output",
        )
    with calc_context():
        scrap = total - good - rework
        return YieldResult(
            total_input=total,
            good_output=good,
            rework_quantity=rework,
            scrap_quantity=clean(scrap),
            yield_rate=clean(good / total),
            scrap_rate=clean(scrap / total),
            rework_rate=clean(rework / total),
        )


@dataclass(frozen=True)
class WastageResult:
    material_input: Decimal
    material_in_output: Decimal
    scrap_quantity: Decimal
    wastage_quantity: Decimal  # total loss
    process_wastage: Decimal  # loss that is not scrap
    wastage_rate: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_input": plain_number(self.material_input),
            "material_in_output": plain_number(self.material_in_output),
            "scrap_quantity": plain_number(self.scrap_quantity),
            "wastage_quantity": plain_number(self.wastage_quantity),
            "process_wastage": plain_number(self.process_wastage),
            "wastage_rate": format_quantity(self.wastage_rate),
        }


def calculate_wastage(material_input: Any, material_in_output: Any, scrap_quantity: Any = 0) -> WastageResult:
    """Material wastage = input - material that ended up in good output.

    ``scrap_quantity`` (material scrapped) is reported separately from the remaining
    ``process_wastage`` (trimmings, spillage, ...).
    """
    total = number(material_input, "material_input", positive=True, code="INVALID_QUANTITY")
    used = number(material_in_output, "material_in_output", code="INVALID_QUANTITY")
    scrap = number(scrap_quantity, "scrap_quantity", code="INVALID_SCRAP_QUANTITY")
    if used > total:
        raise ManufacturingError(
            "Material in output (%s) cannot exceed material input (%s)." % (used, total), code="OUTPUT_EXCEEDS_INPUT", field="material_in_output"
        )
    with calc_context():
        waste = total - used
        if scrap > waste:
            raise ManufacturingError(
                "Scrap (%s) cannot exceed total wastage (%s)." % (scrap, waste), code="INVALID_SCRAP_QUANTITY", field="scrap_quantity"
            )
        return WastageResult(
            material_input=total,
            material_in_output=used,
            scrap_quantity=scrap,
            wastage_quantity=clean(waste),
            process_wastage=clean(waste - scrap),
            wastage_rate=clean(waste / total),
        )
