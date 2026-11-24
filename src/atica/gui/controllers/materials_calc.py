"""Materials & BOM screen: calls :mod:`atica.materials`."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from atica import materials
from atica.core import MissingInputError, use_precision

from ..models import Outcome, ResultTable
from ..services import AppState, fmt
from ..services.parsing import build_bom
from ._common import checked, optional, rounding_args, val


def requirements(values: Mapping[str, Any], state: AppState) -> Outcome:
    bom = build_bom(state.bom_rows, allow_duplicates=checked(values, "allow_duplicates"))
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        result = materials.calculate_bom_requirements(
            bom,
            val(values, "production_quantity"),
            scrap_percent=optional(values, "scrap_percent", 0),
            rounding=rounding,
            places=places,
            registry=state.registry,
        )
    table = ResultTable(
        "Material requirements",
        ["Material", "Required", "Unit", "Net need", "Scrap allowance", "Wastage allowance"],
        [
            [
                t.material_id,
                fmt(t.quantity, state),
                t.unit,
                fmt(t.base_quantity, state),
                fmt(t.scrap_allowance, state),
                fmt(t.wastage_allowance, state),
            ]
            for t in result.totals
        ],
    )
    outcome = Outcome(
        title="BOM requirements",
        headline="%d material(s) for %s units" % (len(result.totals), fmt(result.production_quantity, state)),
        tables=[table],
        formula="started = good / (1 - scrap%); required = per_unit x started / (1 - wastage%)",
        assumptions=[
            "Scrap % is a share of units started; wastage % is a share of material issued.",
            "Rounding: %s." % (rounding.replace("_", " ") if rounding != "none" else "none (exact values)"),
        ],
        summary="BOM for %s units: %d material(s)"
        % (fmt(result.production_quantity, state), len(result.totals)),
    )
    for t in result.totals:
        outcome.warnings.extend("%s: %s" % (t.material_id, w) for w in t.warnings)
    return outcome


def capacity(values: Mapping[str, Any], available_rows: Sequence[Sequence[str]], state: AppState) -> Outcome:
    bom = build_bom(state.bom_rows, allow_duplicates=checked(values, "allow_duplicates"))
    available: Dict[str, Any] = {}
    for row in available_rows:
        cells = [(c or "").strip() for c in ([*list(row), "", "", ""])[:3]]
        if cells[0] and cells[1] == "":
            raise MissingInputError(
                "No quantity entered for %r." % cells[0],
                parameter="available",
                hint="Enter the stock on hand (0 if none).",
            )
        if cells[0]:
            available[cells[0]] = (cells[1], cells[2]) if cells[2] else cells[1]
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        result = materials.calculate_producible_quantity(
            bom,
            available,
            scrap_percent=optional(values, "scrap_percent", 0),
            rounding=rounding,
            places=places,
            registry=state.registry,
        )
    table = ResultTable(
        "Capacity by material",
        ["Material", "Available", "Per unit (gross)", "Units supported"],
        [
            [
                m.material_id,
                "%s %s" % (fmt(m.available, state), m.unit),
                "%s %s" % (fmt(m.required_per_unit, state), m.unit),
                fmt(m.producible_units, state),
            ]
            for m in result.materials
        ],
    )
    return Outcome(
        title="Production capacity from materials",
        headline="%s units can be made" % fmt(result.producible_quantity, state),
        rows=[
            ("Limiting material", result.limiting_material),
            ("Exact figure", fmt(result.exact_quantity, state)),
        ],
        tables=[table],
        formula=result.formula,
        summary="Capacity %s units (limited by %s)"
        % (fmt(result.producible_quantity, state), result.limiting_material),
    )
