"""Quality & Yield screen: calls :mod:`atica.quality`."""

from __future__ import annotations

from typing import Any, Mapping

from atica import quality
from atica.core import use_precision

from ..models import Outcome
from ..services import AppState, fmt, percent, with_unit
from ._common import optional, rounding_args, val


def scrap(values: Mapping[str, Any], state: AppState) -> Outcome:
    mode = val(values, "mode") or "required_input"
    unit = optional(values, "unit", "")
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        if mode == "scrap_percentage":
            r = quality.calculate_scrap_percentage(
                val(values, "input_quantity"), val(values, "scrap_quantity")
            )
            return Outcome(
                title="Scrap percentage",
                headline=percent(r.percent, state),
                rows=[
                    ("Scrap", fmt(r.numerator, state)),
                    ("Denominator", "%s (%s)" % (fmt(r.denominator, state), r.denominator_meaning)),
                ],
                formula=r.formula,
                summary="Scrap %s of %s = %s"
                % (fmt(r.numerator, state), fmt(r.denominator, state), percent(r.percent, state)),
            )
        if mode == "required_input":
            q = quality.calculate_required_input(
                val(values, "good_output"),
                val(values, "scrap_percent"),
                rounding=rounding,
                places=places,
                unit=unit,
            )
            label = "Input to start"
        elif mode == "expected_output":
            q = quality.calculate_expected_output(
                val(values, "input_quantity"),
                val(values, "scrap_percent"),
                rounding=rounding,
                places=places,
                unit=unit,
            )
            label = "Expected good output"
        else:
            q = quality.calculate_scrap_quantity(
                val(values, "input_quantity"),
                val(values, "scrap_percent"),
                rounding=rounding,
                places=places,
                unit=unit,
            )
            label = "Expected scrap"
    rows = [("Scrap rate", percent(q.scrap_percent, state))]
    if q.rounding.value != "none":
        rows.append(("Exact value", with_unit(q.exact_quantity, q.unit, state)))
    return Outcome(
        title=label,
        headline=with_unit(q.quantity, q.unit, state),
        rows=rows,
        formula=q.formula,
        assumptions=["Scrap % is measured against the quantity started (the input)."],
        summary="%s: %s" % (label, with_unit(q.quantity, q.unit, state)),
    )


def yield_(values: Mapping[str, Any], state: AppState) -> Outcome:
    with use_precision(state.precision):
        r = quality.calculate_yield(
            val(values, "input_quantity"),
            val(values, "good_first_pass"),
            sent_to_rework=optional(values, "sent_to_rework", 0),
            recovered_from_rework=optional(values, "recovered_from_rework", 0),
            first_pass_scrap=optional(values, "first_pass_scrap"),
        )
    return Outcome(
        title="Yield",
        headline="Final yield %s" % percent(r.final_yield_percent, state),
        rows=[
            ("First-pass yield", percent(r.first_pass_yield_percent, state)),
            ("Final yield", percent(r.final_yield_percent, state)),
            ("Rework rate (of input)", percent(r.rework_percent, state)),
            ("Rework recovery (of reworked units)", percent(r.rework_recovery_percent, state)),
            ("Scrap rate (of input)", percent(r.scrap_percent, state)),
            ("Final good units", fmt(r.final_good, state)),
            ("Final scrapped units", fmt(r.final_scrap, state)),
            ("  of which scrapped at first inspection", fmt(r.first_pass_scrap, state)),
            ("  of which scrapped after rework", fmt(r.rework_scrap, state)),
        ],
        formula=r.formula,
        warnings=list(r.warnings),
        assumptions=[
            "Every unit has one first-pass outcome (good, rework or scrap); reworked units are counted once."
        ],
        summary="First-pass %s, final %s"
        % (percent(r.first_pass_yield_percent, state), percent(r.final_yield_percent, state)),
    )


def rework(values: Mapping[str, Any], state: AppState) -> Outcome:
    with use_precision(state.precision):
        p = quality.calculate_rework(
            val(values, "input_quantity"),
            first_pass_yield_percent=val(values, "first_pass_yield_percent"),
            rework_percent=optional(values, "rework_percent", 0),
            rework_recovery_percent=optional(values, "rework_recovery_percent", 100),
        )
        need = None
        if optional(values, "good_target"):
            need = quality.required_input_with_rework(
                val(values, "good_target"),
                first_pass_yield_percent=val(values, "first_pass_yield_percent"),
                rework_percent=optional(values, "rework_percent", 0),
                rework_recovery_percent=optional(values, "rework_recovery_percent", 100),
            )
    rows = [
        ("Good at first pass", fmt(p.good_first_pass, state)),
        ("Sent to rework", fmt(p.sent_to_rework, state)),
        ("Scrapped at first inspection", fmt(p.first_pass_scrap, state)),
        ("Recovered by rework", fmt(p.recovered_from_rework, state)),
        ("Scrapped after rework", fmt(p.rework_scrap, state)),
        ("Final good units", fmt(p.final_good, state)),
        ("Final scrapped units", fmt(p.final_scrap, state)),
        ("Final scrap rate", percent(p.scrap_percent, state)),
    ]
    if need is not None:
        rows.append(("Input needed for the good-unit target", fmt(need, state)))
    return Outcome(
        title="Rework projection",
        headline="Final yield %s" % percent(p.final_yield_percent, state),
        rows=rows,
        formula=p.formula,
        assumptions=["Values are expected (statistical) quantities and may be fractional."],
        summary="Final yield %s with rework" % percent(p.final_yield_percent, state),
    )


def wastage(values: Mapping[str, Any], state: AppState) -> Outcome:
    unit = optional(values, "unit", "")
    with use_precision(state.precision):
        r = quality.calculate_wastage(
            val(values, "material_input"),
            val(values, "material_in_output"),
            recovered_quantity=optional(values, "recovered_quantity"),
            recovery_percent=optional(values, "recovery_percent"),
            unit=unit,
        )
    return Outcome(
        title="Material wastage",
        headline="Net wastage %s" % with_unit(r.net_wastage, unit, state),
        rows=[
            ("Gross wastage", with_unit(r.gross_wastage, unit, state)),
            ("Recovered", with_unit(r.recovered, unit, state)),
            ("Net wastage", with_unit(r.net_wastage, unit, state)),
            ("Gross wastage (of input)", percent(r.gross_wastage_percent, state)),
            ("Net wastage (of input)", percent(r.net_wastage_percent, state)),
            ("Material utilisation (of input)", percent(r.utilisation_percent, state)),
            ("Recovery (of gross wastage)", percent(r.recovery_percent, state)),
        ],
        formula=r.formula,
        warnings=list(r.warnings),
        assumptions=["All quantities must be in the same unit."],
        summary="Wastage %s of input" % percent(r.net_wastage_percent, state),
    )


def recovery(values: Mapping[str, Any], state: AppState) -> Outcome:
    unit = optional(values, "unit", "")
    with use_precision(state.precision):
        r = quality.calculate_material_recovery(
            val(values, "waste_quantity"), val(values, "recovery_percent"), unit=unit
        )
    return Outcome(
        title="Material recovery",
        headline="%s recovered" % with_unit(r.recovered_quantity, unit, state),
        rows=[
            ("Waste", with_unit(r.waste_quantity, unit, state)),
            ("Not recovered", with_unit(r.unrecovered_quantity, unit, state)),
        ],
        formula=r.formula,
        summary="Recovered %s" % with_unit(r.recovered_quantity, unit, state),
    )
