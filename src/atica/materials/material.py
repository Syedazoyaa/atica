"""Single-material requirement calculation and the BOM data model.

Percentages (all on the 0-100 scale) and their denominators
-----------------------------------------------------------
* ``scrap_percent``   - share of the **units started** that are rejected, so
  ``units_started = good_units / (1 - scrap/100)``.
* ``wastage_percent`` - share of the **material issued** (gross) that is lost
  in processing, so ``gross_material = material_used / (1 - wastage/100)``.

Scrap and wastage describe different losses and are both applied: a scrapped
unit consumes its full material *and* the process loses wastage on all material
issued.  To convert a "markup on net" figure ``m`` % to this convention use
``wastage_percent = 100 * m / (100 + m)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, Mapping, NamedTuple, Optional, Tuple

from ..core.exceptions import (
    DuplicateMaterialError,
    MaterialError,
    MissingInputError,
    UnsupportedOperationError,
    ValidationError,
)
from ..core.precision import dec, display_decimal
from ..core.results import Result
from ..core.rounding import Rounding, resolve_rounding, round_fraction
from ..core.validation import non_negative, percentage, positive, text
from ..units import UnitRegistry, default_registry

_ONE = Fraction(1)
_HUNDRED = Fraction(100)


@dataclass(frozen=True)
class MaterialRequirement(Result):
    """Material needed to make ``production_quantity`` good units.

    ``exact_quantity == base_quantity + scrap_allowance + wastage_allowance`` (all in ``unit``);
    ``quantity`` is ``exact_quantity`` after the requested rounding.
    """

    material_id: str
    unit: str
    production_quantity: Decimal
    units_started: Decimal
    base_quantity: Decimal
    scrap_allowance: Decimal
    wastage_allowance: Decimal
    exact_quantity: Decimal
    quantity: Decimal
    quantity_per_unit: Decimal
    per_unit_unit: str
    scrap_percent: Decimal
    wastage_percent: Decimal
    rounding: Rounding = Rounding.NONE
    places: int = 0
    formula: str = "units_started = good / (1 - scrap%); gross = per_unit x units_started / (1 - wastage%)"
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return "%s %s" % (display_decimal(self.quantity), self.unit)


@dataclass(frozen=True)
class BomItem:
    """One material line of a bill of materials.

    ``quantity_per_unit`` is the **net** amount of material in one finished unit,
    expressed in ``unit``; ``wastage_percent`` is the extra process loss (see module docs).
    """

    material_id: str
    quantity_per_unit: Decimal
    unit: str
    wastage_percent: Decimal = Decimal(0)
    name: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", text(self.material_id, "material_id", max_length=64))
        object.__setattr__(self, "unit", text(self.unit, "unit", max_length=64))
        object.__setattr__(self, "name", (self.name or "").strip())
        qty = positive(self.quantity_per_unit, "quantity_per_unit")
        object.__setattr__(self, "quantity_per_unit", dec(qty))
        wastage = percentage(self.wastage_percent, "wastage_percent", allow_100=False)
        object.__setattr__(self, "wastage_percent", dec(wastage))


@dataclass(frozen=True)
class Bom:
    """An immutable bill of materials: the materials needed for **one** finished unit.

    Material identifiers must be unique (compared ignoring case) unless
    ``allow_duplicates=True``; in that case lines with the same identifier are
    kept as separate lines and also reported combined in ``totals``.
    """

    items: Tuple[BomItem, ...]
    product_id: str = ""
    allow_duplicates: bool = False

    def __post_init__(self) -> None:
        items = tuple(self.items)
        if not items:
            raise MissingInputError("A BOM needs at least one material.", parameter="items")
        seen: Dict[str, str] = {}
        for item in items:
            if not isinstance(item, BomItem):
                raise ValidationError(
                    "BOM items must be BomItem objects (got %s)." % type(item).__name__, parameter="items"
                )
            key = item.material_id.casefold()
            if key in seen and not self.allow_duplicates:
                raise DuplicateMaterialError(
                    "Material %r appears more than once in the BOM." % item.material_id,
                    parameter="items",
                    hint="Merge the lines, use distinct ids, or create the Bom with allow_duplicates=True.",
                )
            seen[key] = item.material_id
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "product_id", (self.product_id or "").strip())

    @property
    def material_ids(self) -> Tuple[str, ...]:
        """Distinct material identifiers, in first-seen order."""
        out: Dict[str, str] = {}
        for item in self.items:
            out.setdefault(item.material_id.casefold(), item.material_id)
        return tuple(out.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "allow_duplicates": self.allow_duplicates,
            "items": [
                {
                    "material_id": i.material_id,
                    "quantity_per_unit": str(i.quantity_per_unit),
                    "unit": i.unit,
                    "wastage_percent": str(i.wastage_percent),
                    "name": i.name,
                }
                for i in self.items
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Bom:
        try:
            items = tuple(
                BomItem(
                    d["material_id"],
                    d["quantity_per_unit"],
                    d["unit"],
                    d.get("wastage_percent", 0),
                    d.get("name", ""),
                )
                for d in data["items"]
            )
        except (KeyError, TypeError) as exc:
            raise MaterialError("Malformed BOM description: %s." % exc, parameter="data") from None
        return cls(items, data.get("product_id", ""), bool(data.get("allow_duplicates", False)))


def _unit_factor(registry: UnitRegistry, unit: str, report_unit: Optional[str]) -> tuple[str, Fraction]:
    u = registry.get(text(unit, "unit", max_length=64))
    if u.is_offset:
        raise UnsupportedOperationError(
            "%s is an offset temperature scale and cannot measure a material quantity." % u.symbol,
            parameter="unit",
        )
    if report_unit is None or report_unit == unit:
        return u.symbol, _ONE
    return registry.get(report_unit).symbol, registry.factor(unit, report_unit)


class Parts(NamedTuple):
    """The exact (unrounded) components of a requirement, in the report unit.

    Kept alongside the Decimal result so that later steps (merging duplicate lines, summing batches)
    work from the exact fractions and never from an already-rounded Decimal.
    """

    base: Fraction
    scrap: Fraction
    wastage: Fraction
    exact: Fraction
    per_unit: Fraction


def _requirement(
    material_id: str,
    q: Fraction,
    unit: str,
    good: Fraction,
    scrap: Fraction,
    wastage: Fraction,
    policy: Rounding,
    places: int,
    report_unit: Optional[str],
    registry: UnitRegistry,
) -> MaterialRequirement:
    return _requirement_parts(
        material_id, q, unit, good, scrap, wastage, policy, places, report_unit, registry
    )[0]


def _requirement_parts(
    material_id: str,
    q: Fraction,
    unit: str,
    good: Fraction,
    scrap: Fraction,
    wastage: Fraction,
    policy: Rounding,
    places: int,
    report_unit: Optional[str],
    registry: UnitRegistry,
) -> Tuple[MaterialRequirement, Parts]:
    out_unit, k = _unit_factor(registry, unit, report_unit)
    started = good / (_ONE - scrap / _HUNDRED)
    used = q * started
    gross = used / (_ONE - wastage / _HUNDRED)
    base = q * good * k
    scrap_part = q * (started - good) * k
    wastage_part = (gross - used) * k
    exact = gross * k
    parts = Parts(base, scrap_part, wastage_part, exact, q * k)
    requirement = MaterialRequirement(
        material_id=material_id,
        unit=out_unit,
        production_quantity=dec(good),
        units_started=dec(started),
        base_quantity=dec(base),
        scrap_allowance=dec(scrap_part),
        wastage_allowance=dec(wastage_part),
        exact_quantity=dec(exact),
        quantity=round_fraction(exact, policy, places) if policy is not Rounding.NONE else dec(exact),
        quantity_per_unit=dec(q),
        per_unit_unit=registry.get(unit).symbol,
        scrap_percent=dec(scrap),
        wastage_percent=dec(wastage),
        rounding=policy,
        places=places,
    )
    return requirement, parts


def calculate_material_requirement(
    quantity_per_unit: Any,
    production_quantity: Any,
    unit: str,
    *,
    wastage_percent: Any = 0,
    scrap_percent: Any = 0,
    rounding: Any = Rounding.NONE,
    places: int = 0,
    report_unit: Optional[str] = None,
    material_id: str = "",
    registry: Optional[UnitRegistry] = None,
) -> MaterialRequirement:
    """Total quantity of one material needed for ``production_quantity`` good units.

    :param quantity_per_unit: net material in one finished unit (``> 0``), measured in ``unit``.
    :param production_quantity: good units wanted (``>= 0``).
    :param unit: unit of ``quantity_per_unit`` (a registry unit, e.g. ``"kg"``).
    :param wastage_percent: 0-100 (<100); share of *issued material* lost in processing.
    :param scrap_percent: 0-100 (<100); share of *units started* that are rejected.
    :param rounding: rounding of the final figure (default ``'none'``); ``places`` = decimal places.
    :param report_unit: express the result in this (compatible) unit instead of ``unit``.
    :param registry: registry holding custom units (default: standard units).
    :raises IncompatibleUnitError: ``report_unit`` measures a different quantity.

    Formula: ``started = good / (1 - scrap/100)``;
    ``total = quantity_per_unit x started / (1 - wastage/100)``.

    >>> str(calculate_material_requirement("0.5", 1000, "kg"))
    '500 kg'
    >>> str(calculate_material_requirement("0.5", 1000, "kg", report_unit="g"))
    '500000 g'
    """
    reg = registry or default_registry()
    q = positive(quantity_per_unit, "quantity_per_unit")
    good = non_negative(production_quantity, "production_quantity")
    scrap = percentage(scrap_percent, "scrap_percent", allow_100=False)
    wastage = percentage(wastage_percent, "wastage_percent", allow_100=False)
    policy, places = resolve_rounding(rounding, places)
    return _requirement(material_id, q, unit, good, scrap, wastage, policy, places, report_unit, reg)


__all__ = ["Bom", "BomItem", "MaterialRequirement", "calculate_material_requirement"]
