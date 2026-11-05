"""Material requirement calculations (M05)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..calculations.numeric import calc_context, clean, format_quantity, plain_number
from ..calculations.rounding import RoundingPolicy, round_value
from ..exceptions import ManufacturingError
from ..results import CalculationResult
from ..units.registry import UnitRegistry
from ..validation.manufacturing_rules import validate_material
from ._common import number, resolve_rate


def calculate_material_requirement(
    material_per_unit: Any = None,
    production_quantity: Any = None,
    material_unit: Optional[str] = None,
    *,
    target_output: Any = None,
    scrap_rate: Any = None,
    scrap_percent: Any = None,
    wastage_rate: Any = None,
    rounding: Any = RoundingPolicy.NONE,
    places: int = 0,
    multiple: Any = 1,
    units_rounding: Any = RoundingPolicy.NONE,
    units_places: int = 0,
    output_unit: Optional[str] = None,
    registry: Optional[UnitRegistry] = None,
) -> CalculationResult:
    """Material needed for production, optionally allowing for scrap and wastage.

    ``production_quantity`` and ``target_output`` are synonyms (good units wanted).

    * With ``material_per_unit``: returns the total material (in ``material_unit``,
      or ``output_unit`` when given - converted through the unit registry).
    * Without it: returns the number of units that must be *started* to obtain
      ``target_output`` good units given ``scrap_rate``.

    Scrap rate and wastage rate are fractions (``0.05`` = 5 %). *Scrap* reduces good
    units per unit started; *wastage* increases material consumed per unit.

    ``units_rounding`` rounds the units started (e.g. whole units); ``rounding``
    rounds the returned figure.

    >>> str(calculate_material_requirement(material_per_unit="0.5", production_quantity=1000, material_unit="kg"))
    '500 kg'
    >>> str(calculate_material_requirement(target_output=1000, scrap_rate="0.05", rounding="up"))
    '1053'
    """
    if production_quantity is not None and target_output is not None:
        if number(production_quantity, "production_quantity") != number(target_output, "target_output"):
            raise ManufacturingError(
                "production_quantity and target_output are synonyms but have different values.",
                code="AMBIGUOUS_INPUT",
                field="target_output",
            )
    raw_qty = production_quantity if production_quantity is not None else target_output
    if raw_qty is None:
        raise ManufacturingError("A production quantity / target output is required.", code="MISSING_INPUT", field="production_quantity")
    qty = number(raw_qty, "production_quantity", code="INVALID_PRODUCTION_QUANTITY", label="Production quantity")
    scrap = resolve_rate(scrap_rate, scrap_percent)
    wastage = resolve_rate(wastage_rate, None, field="wastage_rate", code="INVALID_WASTAGE_RATE")
    if material_per_unit is None and scrap_rate is None and scrap_percent is None:
        raise ManufacturingError(
            "Provide material_per_unit (material total) and/or a scrap rate (required input).",
            code="MISSING_INPUT",
            field="material_per_unit",
        )
    per_unit = number(material_per_unit, "material_per_unit", code="INVALID_MATERIAL_CONSUMPTION") if material_per_unit is not None else None
    policy = RoundingPolicy.parse(rounding)
    units_policy = RoundingPolicy.parse(units_rounding)

    with calc_context():
        started_exact = clean(qty / (Decimal(1) - scrap))
        meta: Dict[str, Any] = {
            "production_quantity": qty,
            "scrap_rate": scrap,
            "wastage_rate": wastage,
        }
        warnings: List[str] = []
        if per_unit is None:
            value = round_value(started_exact, policy, places=places, multiple=multiple)
            meta["exact_quantity"] = started_exact
            return CalculationResult(
                output_quantity=value,
                output_unit=material_unit,
                input_quantity=qty,
                input_unit=material_unit,
                formula="target_output / (1 - scrap_rate)",
                rounding_policy=policy,
                metadata=meta,
            )
        started = round_value(started_exact, units_policy, places=units_places)
        effective = per_unit / (Decimal(1) - wastage)
        total = clean(started * effective)
    meta.update(units_to_process=started, material_per_unit=per_unit, effective_material_per_unit=clean(effective))
    unit = material_unit
    if output_unit and material_unit and output_unit != material_unit:
        reg = registry
        if reg is None:
            from ..units.converter import get_default_registry

            reg = get_default_registry()
        converted = reg.convert(total, material_unit, output_unit)
        total = converted.output_quantity
        warnings.extend(converted.warnings)
        unit = converted.output_unit
    elif output_unit and not material_unit:
        unit = output_unit
    meta["exact_quantity"] = total
    value = round_value(total, policy, places=places, multiple=multiple)
    return CalculationResult(
        output_quantity=value,
        output_unit=unit,
        input_quantity=qty,
        input_unit=None,
        formula="units_started x material_per_unit / (1 - wastage_rate), units_started = output / (1 - scrap_rate)",
        rounding_policy=policy,
        warnings=tuple(warnings),
        metadata=meta,
    )


def calculate_producible_quantity(
    available_material: Any,
    material_per_unit: Any,
    *,
    scrap_rate: Any = None,
    wastage_rate: Any = None,
    rounding: Any = RoundingPolicy.DOWN,
) -> CalculationResult:
    """How many good units can be made from ``available_material`` (default: whole units, rounded down)."""
    available = number(available_material, "available_material", code="INVALID_QUANTITY")
    per_unit = number(material_per_unit, "material_per_unit", positive=True, code="INVALID_MATERIAL_CONSUMPTION")
    scrap = resolve_rate(scrap_rate)
    wastage = resolve_rate(wastage_rate, field="wastage_rate", code="INVALID_WASTAGE_RATE")
    policy = RoundingPolicy.parse(rounding)
    with calc_context():
        started = available / (per_unit / (Decimal(1) - wastage))
        exact = clean(started * (Decimal(1) - scrap))
    return CalculationResult(
        output_quantity=round_value(exact, policy),
        output_unit="units",
        input_quantity=available,
        formula="available / (material_per_unit / (1 - wastage)) x (1 - scrap)",
        rounding_policy=policy,
        metadata={"exact_quantity": exact},
    )


class Material:
    """A manufacturing material (data model 7.4)."""

    def __init__(
        self,
        material_id: str,
        name: str,
        unit: str,
        consumption_per_unit: Any,
        wastage_rate: Any = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        validate_material(material_id, unit, consumption_per_unit, wastage_rate).raise_if_invalid(ManufacturingError)
        self.material_id = material_id.strip()
        self.name = name
        self.unit = unit.strip()
        self.consumption_per_unit = number(consumption_per_unit, "consumption_per_unit")
        self.wastage_rate = resolve_rate(wastage_rate, field="wastage_rate", code="INVALID_WASTAGE_RATE")
        self.metadata = dict(metadata or {})

    def requirement(self, production_quantity: Any, *, scrap_rate: Any = None, **kwargs: Any) -> CalculationResult:
        return calculate_material_requirement(
            self.consumption_per_unit,
            production_quantity,
            self.unit,
            scrap_rate=scrap_rate,
            wastage_rate=self.wastage_rate,
            **kwargs,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "unit": self.unit,
            "consumption_per_unit": format_quantity(self.consumption_per_unit),
            "wastage_rate": format_quantity(self.wastage_rate),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Material":
        try:
            return cls(
                data["material_id"],
                data.get("name", data["material_id"]),
                data["unit"],
                data["consumption_per_unit"],
                data.get("wastage_rate", 0),
                data.get("metadata"),
            )
        except (KeyError, TypeError) as exc:
            raise ManufacturingError("Invalid material definition: %s" % exc, code="INVALID_MATERIAL") from None


def calculate_bom_requirements(
    materials: List[Material], production_quantity: Any, *, scrap_rate: Any = None, **kwargs: Any
) -> Dict[str, CalculationResult]:
    """Requirement for several materials at once, keyed by ``material_id``."""
    return {m.material_id: m.requirement(production_quantity, scrap_rate=scrap_rate, **kwargs) for m in materials}
