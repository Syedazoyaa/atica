"""Packaging screen: calls :mod:`atica.packaging`."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from atica import packaging
from atica.core import use_precision

from ..models import Outcome, ResultTable
from ..services import AppState, fmt
from ..services.parsing import build_product
from ._common import checked, need, val

_NEED_PRODUCT = "No packaging hierarchy is defined yet."
_NEED_PRODUCT_HINT = "Enter the levels (smallest first) and press 'Validate and apply levels'."


def apply_levels(values: Mapping[str, Any], rows: Sequence[Sequence[str]], state: AppState) -> Outcome:
    product = build_product(val(values, "product_id") or "PRODUCT", val(values, "name") or "", rows)
    state.product = product
    state.changed()
    table = ResultTable(
        "Packaging levels",
        ["Level", "Contains", "Base units per level"],
        [
            [
                level.name,
                "-" if level.of is None else "%s x %s" % (fmt(level.contains, state), level.of),
                fmt(product.size_of(level.name), state),
            ]
            for level in product.levels
        ],
    )
    return Outcome(
        title="Packaging hierarchy",
        headline="%d level(s): %s" % (len(product.levels), " < ".join(product.level_names)),
        tables=[table],
        summary="Applied hierarchy " + " < ".join(product.level_names),
    )


def breakdown(values: Mapping[str, Any], state: AppState) -> Outcome:
    product = need(state.product, _NEED_PRODUCT, _NEED_PRODUCT_HINT)
    with use_precision(state.precision):
        r = packaging.breakdown(
            product,
            val(values, "quantity"),
            val(values, "from_level"),  # type: ignore[arg-type]
            val(values, "to_level"),  # type: ignore[arg-type]
            require_whole=checked(values, "require_whole"),
        )
    rows = [
        ("Quantity", "%s %s" % (fmt(r.quantity, state), r.from_level)),
        ("Full %s packages" % r.to_level, fmt(r.full_packages, state)),
        ("Remaining quantity", "%s %s" % (fmt(r.remainder, state), r.remainder_unit)),
        ("Minimum whole %s needed" % r.to_level, fmt(r.packages_required, state)),
        ("Exact equivalent", "%s %s" % (fmt(r.exact_packages, state), r.to_level)),
        ("Quantity covered by those packages", "%s %s" % (fmt(r.packaged_quantity, state), r.from_level)),
        ("Surplus", "%s %s" % (fmt(r.surplus, state), r.from_level)),
        ("%s per %s" % (r.from_level, r.to_level), fmt(r.units_per_package, state)),
    ]
    return Outcome(
        title="Packaging breakdown",
        headline=str(r),
        rows=rows,
        formula=r.formula,
        summary=str(r),
    )


def decompose(values: Mapping[str, Any], state: AppState) -> Outcome:
    product = need(state.product, _NEED_PRODUCT, _NEED_PRODUCT_HINT)
    with use_precision(state.precision):
        plan = packaging.decompose(product, val(values, "quantity"), val(values, "from_level") or "")
    parts = [(name, count) for name, count in plan.counts] + [(plan.base_unit, plan.remainder)]
    table = ResultTable(
        "Whole packages per level", ["Level", "Count"], [[n, fmt(c, state)] for n, c in parts]
    )
    text = " + ".join("%s %s" % (fmt(c, state), n) for n, c in parts if c)
    return Outcome(
        title="Packaging plan",
        headline=text or "0",
        tables=[table],
        summary="%s %s = %s" % (fmt(plan.quantity, state), plan.from_level, text or "0"),
    )
