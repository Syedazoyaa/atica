"""Production screen: calls :mod:`atica.production`."""

from __future__ import annotations

from typing import Any, Mapping

from atica import production
from atica.core import format_duration, use_precision

from ..models import Outcome, ResultTable
from ..services import AppState, fmt, with_unit
from ..services.parsing import build_bom
from ._common import checked, optional, rounding_args, val


def batches(values: Mapping[str, Any], state: AppState) -> Outcome:
    with use_precision(state.precision):
        plan = production.calculate_batches(val(values, "quantity"), val(values, "batch_size"))
    outcome = Outcome(
        title="Batch plan",
        headline="%s batch(es) required" % fmt(plan.batches_required, state),
        rows=[
            ("Full batches", fmt(plan.full_batches, state)),
            ("Partial batch quantity", fmt(plan.partial_batch_quantity, state)),
            ("Total capacity of required batches", fmt(plan.total_capacity, state)),
            ("Unused capacity", fmt(plan.unused_capacity, state)),
        ],
        formula=plan.formula,
        summary="%s units in batches of %s: %s required"
        % (fmt(plan.quantity, state), fmt(plan.batch_size, state), fmt(plan.batches_required, state)),
    )
    if checked(values, "include_materials"):
        bom = build_bom(state.bom_rows)
        rounding, places = rounding_args(values)
        with use_precision(state.precision):
            mp = production.calculate_batch_materials(
                bom,
                val(values, "quantity"),
                val(values, "batch_size"),
                scrap_percent=optional(values, "scrap_percent", 0),
                rounding=rounding,
                places=places,
                registry=state.registry,
            )
        outcome.tables.append(
            ResultTable(
                "Materials per batch",
                ["Material", "Per full batch", "Partial batch", "Total", "Unit"],
                [
                    [
                        m.material_id,
                        fmt(m.per_full_batch, state),
                        fmt(m.partial_batch, state),
                        fmt(m.total, state),
                        m.unit,
                    ]
                    for m in mp.materials
                ],
            )
        )
    return outcome


def _human(value, unit, state):
    """``1.5 h`` as ``1 hour 30 minutes``; the exact number stays available in the result rows."""
    return format_duration(value, unit, state.registry)


def time(values: Mapping[str, Any], state: AppState) -> Outcome:
    setup = optional(values, "setup_time")
    with use_precision(state.precision):
        r = production.production_time(
            val(values, "quantity"),
            val(values, "rate"),
            per=val(values, "per") or "h",
            unit=val(values, "unit") or "h",
            efficiency_percent=optional(values, "efficiency_percent", 100),
            setup_time=(setup, val(values, "setup_unit") or "h") if setup else 0,
            registry=state.registry,
        )
    return Outcome(
        title="Production time",
        headline=_human(r.total_time, r.unit, state),
        rows=[
            ("Exact total", with_unit(r.total_time, r.unit, state)),
            ("Run time", _human(r.run_time, r.unit, state)),
            ("Setup time", _human(r.setup_time, r.unit, state)),
            ("Effective rate", "%s per %s" % (fmt(r.effective_rate, state), r.rate_per)),
        ],
        formula=r.formula,
        assumptions=list(r.assumptions),
        summary="%s units take %s" % (fmt(r.quantity, state), _human(r.total_time, r.unit, state)),
    )


def capacity(values: Mapping[str, Any], state: AppState) -> Outcome:
    unit = val(values, "time_unit") or "h"
    setup = optional(values, "setup_time")
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        r = production.production_capacity(
            val(values, "rate"),
            (val(values, "available_time"), unit),
            per=val(values, "per") or "h",
            time_unit=unit,
            efficiency_percent=optional(values, "efficiency_percent", 100),
            setup_time=(setup, unit) if setup else 0,
            rounding=rounding,
            places=places,
            registry=state.registry,
        )
    return Outcome(
        title="Production capacity",
        headline="%s units" % fmt(r.quantity, state),
        rows=[
            ("Productive time", _human(r.productive_time, r.time_unit, state)),
            ("Exact figure", fmt(r.exact_quantity, state)),
        ],
        formula=r.formula,
        assumptions=list(r.assumptions),
        warnings=list(r.warnings),
        summary="Capacity %s units in %s"
        % (fmt(r.quantity, state), with_unit(r.available_time, r.time_unit, state)),
    )


def batch_capacity(values: Mapping[str, Any], state: AppState) -> Outcome:
    unit = val(values, "time_unit") or "h"
    with use_precision(state.precision):
        r = production.calculate_batch_capacity(
            (val(values, "available_time"), unit),
            (val(values, "time_per_batch"), unit),
            time_unit=unit,
            batch_size=optional(values, "batch_size"),
            registry=state.registry,
        )
    rows = [
        ("Leftover time", _human(r.leftover_time, r.time_unit, state)),
        ("Share of the next batch", fmt(r.next_batch_fraction, state)),
    ]
    if r.quantity is not None:
        rows.append(("Quantity from full batches", fmt(r.quantity, state)))
    return Outcome(
        title="Batch capacity",
        headline="%s full batch(es)" % fmt(r.full_batches, state),
        rows=rows,
        formula=r.formula,
        summary="%s full batches fit" % fmt(r.full_batches, state),
    )


def constraints(values: Mapping[str, Any], state: AppState) -> Outcome:
    with use_precision(state.precision):
        r = production.constrain_production_quantity(
            val(values, "requested"),
            minimum=optional(values, "minimum"),
            maximum=optional(values, "maximum"),
            multiple=optional(values, "multiple"),
            multiple_rounding=val(values, "multiple_rounding") or "ceiling",
        )
    return Outcome(
        title="Production quantity",
        headline=fmt(r.quantity, state),
        rows=[
            ("Requested", fmt(r.requested, state)),
            ("Increase", fmt(r.increase, state)),
            ("Rules applied", ", ".join(r.adjustments) or "none"),
        ],
        summary="Requested %s -> %s" % (fmt(r.requested, state), fmt(r.quantity, state)),
    )
