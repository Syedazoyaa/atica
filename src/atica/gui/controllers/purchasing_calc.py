"""Purchasing screen: calls :mod:`atica.purchasing`."""

from __future__ import annotations

from typing import Any, Mapping

from atica import purchasing
from atica.core import use_precision

from ..models import Outcome
from ..services import AppState, with_unit
from ._common import optional, val


def purchase(values: Mapping[str, Any], state: AppState) -> Outcome:
    purchase_unit = optional(values, "purchase_unit")
    with use_precision(state.precision):
        r = purchasing.calculate_purchase_quantity(
            val(values, "required_quantity"),
            unit=optional(values, "unit", ""),
            stock_on_hand=optional(values, "stock_on_hand", 0),
            minimum_order_quantity=optional(values, "minimum_order_quantity", 0),
            order_multiple=optional(values, "order_multiple"),
            purchase_unit=purchase_unit,
            registry=state.registry,
        )
    rows = [
        ("Required", with_unit(r.required_quantity, r.unit, state)),
        ("Deducted from stock", with_unit(r.stock_deducted, r.unit, state)),
        ("Net requirement", with_unit(r.net_requirement, r.unit, state)),
        ("Surplus after ordering", with_unit(r.surplus, r.unit, state)),
        ("Rules that raised the order", ", ".join(c.replace("_", " ") for c in r.constraints) or "none"),
    ]
    if purchase_unit:
        rows.append(("You will receive", with_unit(r.received_quantity, r.stock_unit, state)))
    return Outcome(
        title="Recommended order",
        headline=with_unit(r.order_quantity, r.unit, state),
        rows=rows,
        formula=r.formula,
        warnings=list(r.warnings),
        assumptions=["Minimum order quantity and order multiple are in the purchase unit."],
        summary="Order %s" % with_unit(r.order_quantity, r.unit, state),
    )
