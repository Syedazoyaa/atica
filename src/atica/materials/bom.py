"""Multi-material BOM requirements and available-material capacity."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..core.exceptions import (
    InvalidConfigurationError,
    MissingInputError,
    ValidationError,
)
from ..core.precision import dec
from ..core.results import Result
from ..core.rounding import Rounding, resolve_rounding, round_fraction
from ..core.validation import non_negative, percentage
from ..units import UnitRegistry, default_registry
from .material import (
    _HUNDRED,
    _ONE,
    Bom,
    MaterialRequirement,
    _requirement,
    _unit_factor,
)


@dataclass(frozen=True)
class BomRequirements(Result):
    """Requirements of every material in a BOM for one production quantity.

    ``lines`` has one entry per BOM line (in BOM order).  ``totals`` has one entry per
    distinct material - identical to ``lines`` unless the BOM allows duplicate
    identifiers, in which case lines of one material are summed (units converted to
    the first line's report unit) and rounded once.
    """

    product_id: str
    production_quantity: Decimal
    scrap_percent: Decimal
    lines: Tuple[MaterialRequirement, ...]
    totals: Tuple[MaterialRequirement, ...]
    warnings: Tuple[str, ...] = ()

    def by_material(self) -> Dict[str, MaterialRequirement]:
        """``{material_id: total requirement}``."""
        return {t.material_id: t for t in self.totals}

    def __getitem__(self, material_id: str) -> MaterialRequirement:
        for t in self.totals:
            if t.material_id.casefold() == str(material_id).casefold():
                return t
        raise KeyError(material_id)


def calculate_bom_requirements(
    bom: Bom,
    production_quantity: Any,
    *,
    scrap_percent: Any = 0,
    rounding: Any = Rounding.NONE,
    places: int = 0,
    report_units: Optional[Mapping[str, str]] = None,
    registry: Optional[UnitRegistry] = None,
) -> BomRequirements:
    """Material requirements of every BOM line for ``production_quantity`` good units.

    Each line follows :func:`~atica.materials.calculate_material_requirement` (with the
    line's own ``wastage_percent``); ``scrap_percent`` applies to the whole product.

    :param report_units: optional ``{material_id: unit}`` to report selected materials in
        another compatible unit (e.g. ``{"steel": "kg"}`` for a BOM written in grams).
    :raises IncompatibleUnitError: a report unit measures a different quantity.
    :raises InvalidConfigurationError: ``report_units`` names a material that is not in the BOM.

    >>> from atica.materials import Bom, BomItem
    >>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("paint", "40", "mL")])
    >>> r = calculate_bom_requirements(bom, 1000)
    >>> str(r["steel"]), str(r["paint"])
    ('250 kg', '40000 mL')
    """
    reg = registry or default_registry()
    good = non_negative(production_quantity, "production_quantity")
    scrap = percentage(scrap_percent, "scrap_percent", allow_100=False)
    policy, places = resolve_rounding(rounding, places)
    overrides = _check_overrides(bom, report_units)
    lines: List[MaterialRequirement] = []
    for item in bom.items:
        lines.append(
            _requirement(
                item.material_id,
                Fraction(item.quantity_per_unit),
                item.unit,
                good,
                scrap,
                Fraction(item.wastage_percent),
                policy,
                places,
                overrides.get(item.material_id.casefold()),
                reg,
            )
        )
    totals = _merge(lines, policy, places, reg) if bom.allow_duplicates else tuple(lines)
    return BomRequirements(
        product_id=bom.product_id,
        production_quantity=dec(good),
        scrap_percent=dec(scrap),
        lines=tuple(lines),
        totals=totals,
    )


def _check_overrides(bom: Bom, report_units: Optional[Mapping[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    known = {m.casefold() for m in bom.material_ids}
    for material, unit in (report_units or {}).items():
        if str(material).casefold() not in known:
            raise InvalidConfigurationError(
                "report_units names %r, which is not a material of this BOM." % (material,),
                parameter="report_units",
                hint="BOM materials: %s." % ", ".join(bom.material_ids),
            )
        out[str(material).casefold()] = unit
    return out


def _total(group: List[MaterialRequirement], factors: List[Fraction], attr: str) -> Fraction:
    """Sum of ``attr`` over ``group``, each line converted with its unit factor (exact)."""
    return sum((Fraction(getattr(g, attr)) * k for g, k in zip(group, factors)), Fraction(0))


def _merge(
    lines: List[MaterialRequirement], policy: Rounding, places: int, reg: UnitRegistry
) -> Tuple[MaterialRequirement, ...]:
    groups: Dict[str, List[MaterialRequirement]] = {}
    for line in lines:
        groups.setdefault(line.material_id.casefold(), []).append(line)
    merged: List[MaterialRequirement] = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        first = group[0]
        factors = [reg.factor(g.unit, first.unit) for g in group]  # IncompatibleUnitError if mixed dimensions

        exact = _total(group, factors, "exact_quantity")
        merged.append(
            MaterialRequirement(
                material_id=first.material_id,
                unit=first.unit,
                production_quantity=first.production_quantity,
                units_started=first.units_started,
                base_quantity=dec(_total(group, factors, "base_quantity")),
                scrap_allowance=dec(_total(group, factors, "scrap_allowance")),
                wastage_allowance=dec(_total(group, factors, "wastage_allowance")),
                exact_quantity=dec(exact),
                quantity=round_fraction(exact, policy, places) if policy is not Rounding.NONE else dec(exact),
                quantity_per_unit=dec(_total(group, factors, "quantity_per_unit")),
                per_unit_unit=first.unit,
                scrap_percent=first.scrap_percent,
                wastage_percent=Decimal(0),
                rounding=policy,
                places=places,
                warnings=("Combined %d BOM lines for this material." % len(group),),
            )
        )
    return tuple(merged)


# ------------------------------------------------------------------- capacity
@dataclass(frozen=True)
class MaterialCapacity(Result):
    """How many good units one material alone could support."""

    material_id: str
    available: Decimal
    unit: str
    required_per_unit: Decimal  # gross material consumed per good unit, in ``unit``
    producible_units: Decimal


@dataclass(frozen=True)
class ProductionCapacity(Result):
    """Result of :func:`calculate_producible_quantity`.

    ``producible_quantity`` is limited by the scarcest material (``limiting_material``).
    ``exact_quantity`` is the unrounded figure.
    """

    producible_quantity: Decimal
    exact_quantity: Decimal
    limiting_material: str
    materials: Tuple[MaterialCapacity, ...]
    scrap_percent: Decimal
    rounding: Rounding = Rounding.FLOOR
    places: int = 0
    formula: str = "min over materials of available x (1 - scrap%) / (sum of per_unit / (1 - wastage%))"
    warnings: Tuple[str, ...] = ()


def calculate_producible_quantity(
    bom: Bom,
    available: Mapping[str, Any],
    *,
    scrap_percent: Any = 0,
    rounding: Any = Rounding.FLOOR,
    places: int = 0,
    registry: Optional[UnitRegistry] = None,
) -> ProductionCapacity:
    """How many good units can be made from the available materials.

    :param available: ``{material_id: quantity}`` (in the BOM line's unit) or
        ``{material_id: (quantity, unit)}`` for any compatible unit.  **Every** BOM
        material must be listed: a missing one is an error, never assumed zero or unlimited.
    :param rounding: default ``'floor'`` (whole units you can really finish); use ``'none'`` for the exact figure.

    Formula per material: ``producible = available x (1 - scrap/100) / sum(q_i / (1 - wastage_i/100))``
    over that material's BOM lines; the answer is the minimum over materials.

    >>> from atica.materials import Bom, BomItem
    >>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("screws", 4, "piece")])
    >>> cap = calculate_producible_quantity(bom, {"steel": (100, "kg"), "screws": 1000})
    >>> int(cap.producible_quantity), cap.limiting_material
    (250, 'screws')
    """
    reg = registry or default_registry()
    scrap = percentage(scrap_percent, "scrap_percent", allow_100=False)
    policy, places = resolve_rounding(rounding, places)
    avail_by_key = {str(k).casefold(): v for k, v in available.items()}
    unknown = [k for k in avail_by_key if k not in {m.casefold() for m in bom.material_ids}]
    if unknown:
        raise InvalidConfigurationError(
            "available lists materials that are not in the BOM: %s." % ", ".join(unknown),
            parameter="available",
            hint="BOM materials: %s." % ", ".join(bom.material_ids),
        )
    caps: List[MaterialCapacity] = []
    exact_values: List[Fraction] = []
    for material in bom.material_ids:
        lines = [i for i in bom.items if i.material_id.casefold() == material.casefold()]
        unit = lines[0].unit
        if material.casefold() not in avail_by_key:
            raise MissingInputError(
                "No available quantity given for material %r." % material,
                parameter="available",
                hint="List every BOM material (use 0 if there is none).",
            )
        raw = avail_by_key[material.casefold()]
        if isinstance(raw, (tuple, list)):
            if len(raw) != 2:
                raise ValidationError(
                    "%r: use a number or (quantity, unit)." % material, parameter="available"
                )
            qty = non_negative(raw[0], "available[%s]" % material)
            stock_unit = raw[1]
        else:
            qty, stock_unit = non_negative(raw, "available[%s]" % material), unit
        _, to_line_unit = _unit_factor(reg, stock_unit, unit)
        in_line_unit = qty * to_line_unit
        gross_per_unit = Fraction(0)
        for line in lines:
            _, k = _unit_factor(reg, line.unit, unit)
            gross_per_unit += (
                Fraction(line.quantity_per_unit) * k / (_ONE - Fraction(line.wastage_percent) / _HUNDRED)
            )
        producible = in_line_unit * (_ONE - scrap / _HUNDRED) / gross_per_unit
        exact_values.append(producible)
        caps.append(
            MaterialCapacity(
                material_id=material,
                available=dec(in_line_unit),
                unit=reg.get(unit).symbol,
                required_per_unit=dec(gross_per_unit),
                producible_units=dec(producible),
            )
        )
    limiting = min(range(len(caps)), key=lambda i: exact_values[i])
    exact = exact_values[limiting]
    return ProductionCapacity(
        producible_quantity=round_fraction(exact, policy, places)
        if policy is not Rounding.NONE
        else dec(exact),
        exact_quantity=dec(exact),
        limiting_material=caps[limiting].material_id,
        materials=tuple(caps),
        scrap_percent=dec(scrap),
        rounding=policy,
        places=places,
    )


__all__ = [
    "BomRequirements",
    "MaterialCapacity",
    "ProductionCapacity",
    "calculate_bom_requirements",
    "calculate_producible_quantity",
]
