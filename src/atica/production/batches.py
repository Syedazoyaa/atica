"""Batch calculations, material needs per batch and production-quantity constraints."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, List, Mapping, Optional, Tuple

from ..core.exceptions import ConstraintError, InvalidConfigurationError
from ..core.precision import dec
from ..core.results import Result
from ..core.rounding import PackageRounding, Rounding, resolve_rounding
from ..core.validation import non_negative, percentage, positive
from ..materials import Bom, BomRequirements, MaterialRequirement
from ..materials.bom import _check_overrides, _compute
from ..units import UnitRegistry, default_registry


@dataclass(frozen=True)
class BatchPlan(Result):
    """Result of :func:`calculate_batches`.

    * ``full_batches``           - batches that run at full ``batch_size`` (``floor``);
    * ``partial_batch_quantity`` - size of the last, partly filled batch (0 if none);
    * ``batches_required``       - ``full_batches`` plus one if there is a partial batch (``ceil``);
    * ``total_capacity``         - ``batches_required x batch_size``;
    * ``unused_capacity``        - ``total_capacity - quantity``.
    """

    quantity: Decimal
    batch_size: Decimal
    full_batches: Decimal
    partial_batch_quantity: Decimal
    batches_required: Decimal
    total_capacity: Decimal
    unused_capacity: Decimal
    formula: str = "full = floor(quantity / batch_size); partial = quantity - full x batch_size; required = ceil(quantity / batch_size)"
    warnings: Tuple[str, ...] = ()

    @property
    def has_partial_batch(self) -> bool:
        return self.partial_batch_quantity > 0


def calculate_batches(quantity: Any, batch_size: Any) -> BatchPlan:
    """Split ``quantity`` into batches of ``batch_size``, keeping the partial batch explicit.

    :param quantity: units to make (``>= 0``; fractions allowed).
    :param batch_size: capacity of one batch (``> 0``).

    >>> plan = calculate_batches(250, 100)
    >>> (int(plan.full_batches), int(plan.partial_batch_quantity), int(plan.batches_required))
    (2, 50, 3)
    """
    q = non_negative(quantity, "quantity")
    size = positive(batch_size, "batch_size")
    full = math.floor(q / size)
    partial = q - full * size
    required = full + (1 if partial > 0 else 0)
    return BatchPlan(
        quantity=dec(q),
        batch_size=dec(size),
        full_batches=Decimal(full),
        partial_batch_quantity=dec(partial),
        batches_required=Decimal(required),
        total_capacity=dec(required * size),
        unused_capacity=dec(required * size - q),
    )


@dataclass(frozen=True)
class BatchMaterial(Result):
    """One material across a batch plan: per full batch, in the partial batch, and in total.

    ``total = full_batches x per_full_batch + partial_batch`` using the *rounded* per-batch
    quantities (what is actually issued); ``exact_total`` uses the unrounded figures.
    """

    material_id: str
    unit: str
    per_full_batch: Decimal
    partial_batch: Decimal
    total: Decimal
    exact_total: Decimal


@dataclass(frozen=True)
class BatchMaterialPlan(Result):
    """Result of :func:`calculate_batch_materials`."""

    batches: BatchPlan
    per_full_batch: BomRequirements
    partial_batch: Optional[BomRequirements]
    materials: Tuple[BatchMaterial, ...]


def calculate_batch_materials(
    bom: Bom,
    quantity: Any,
    batch_size: Any,
    *,
    scrap_percent: Any = 0,
    rounding: Any = Rounding.NONE,
    places: int = 0,
    report_units: Optional[Mapping[str, str]] = None,
    registry: Optional[UnitRegistry] = None,
) -> BatchMaterialPlan:
    """Material needed per batch and in total for ``quantity`` units made in batches of ``batch_size``.

    Each batch is costed like a small production run (:func:`~atica.materials.calculate_bom_requirements`),
    so scrap and wastage apply per batch.  With ``rounding='none'`` the totals equal a single
    calculation for the whole quantity; with rounding they can differ by the per-batch rounding,
    which is exactly what would be issued.

    >>> from atica.materials import Bom, BomItem
    >>> bom = Bom([BomItem("resin", "2", "kg")])
    >>> plan = calculate_batch_materials(bom, 250, 100)
    >>> str(plan.materials[0].total)
    '500'
    """
    reg = registry or default_registry()
    q = non_negative(quantity, "quantity")
    size = positive(batch_size, "batch_size")
    scrap = percentage(scrap_percent, "scrap_percent", allow_100=False)
    policy, places = resolve_rounding(rounding, places)
    overrides = _check_overrides(bom, report_units)
    batches = calculate_batches(q, size)
    full_n = Fraction(math.floor(q / size))
    partial_q = q - full_n * size

    def one_batch(good: Fraction) -> Tuple[BomRequirements, List[Fraction]]:
        lines, totals, exact = _compute(bom, good, scrap, policy, places, overrides, reg)
        result = BomRequirements(bom.product_id, dec(good), dec(scrap), tuple(lines), tuple(totals))
        return result, exact

    per_full, exact_full = one_batch(size)
    partial, exact_partial = (
        one_batch(partial_q) if partial_q > 0 else (None, [Fraction(0)] * len(exact_full))
    )

    def issued(requirement: MaterialRequirement, exact: Fraction) -> Fraction:
        # what is actually issued: the rounded figure (an exact decimal), or the exact fraction if unrounded
        return exact if policy is Rounding.NONE else Fraction(requirement.quantity)

    rows: List[BatchMaterial] = []
    for i, full_line in enumerate(per_full.totals):
        issued_full = issued(full_line, exact_full[i])
        issued_partial = issued(partial.totals[i], exact_partial[i]) if partial else Fraction(0)
        rows.append(
            BatchMaterial(
                material_id=full_line.material_id,
                unit=full_line.unit,
                per_full_batch=full_line.quantity,
                partial_batch=dec(issued_partial),
                total=dec(full_n * issued_full + issued_partial),
                exact_total=dec(full_n * exact_full[i] + exact_partial[i]),
            )
        )
    return BatchMaterialPlan(
        batches=batches, per_full_batch=per_full, partial_batch=partial, materials=tuple(rows)
    )


@dataclass(frozen=True)
class ConstrainedQuantity(Result):
    """Result of :func:`constrain_production_quantity`; ``adjustments`` names the rules that changed it."""

    requested: Decimal
    quantity: Decimal
    increase: Decimal
    adjustments: Tuple[str, ...]
    warnings: Tuple[str, ...] = ()


def constrain_production_quantity(
    requested: Any,
    *,
    minimum: Any = None,
    maximum: Any = None,
    multiple: Any = None,
    multiple_rounding: Any = PackageRounding.CEILING,
) -> ConstrainedQuantity:
    """Adjust a required quantity to production constraints.

    Order of rules: (1) a **zero** request stays zero; (2) raise to ``minimum`` run size;
    (3) snap to a ``multiple`` (package ceiling by default, or ``'floor'``);
    (4) the result must not exceed ``maximum``.

    :raises ConstraintError: the adjusted quantity exceeds ``maximum`` or (with package floor)
        falls below ``minimum``.
    :raises InvalidConfigurationError: ``minimum`` is larger than ``maximum``.

    >>> str(constrain_production_quantity(950, minimum=500, multiple=100).quantity)
    '1000'
    """
    req = non_negative(requested, "requested")
    lo = non_negative(minimum, "minimum") if minimum is not None else None
    hi = positive(maximum, "maximum") if maximum is not None else None
    mult = positive(multiple, "multiple") if multiple is not None else None
    mode = PackageRounding.parse(multiple_rounding)
    if lo is not None and hi is not None and lo > hi:
        raise InvalidConfigurationError(
            "minimum (%s) exceeds maximum (%s)." % (minimum, maximum), parameter="minimum"
        )
    q = req
    notes: List[str] = []
    if q > 0:
        if lo is not None and q < lo:
            q = lo
            notes.append("minimum")
        if mult is not None:
            snapped = (
                math.ceil(q / mult) if mode is PackageRounding.CEILING else math.floor(q / mult)
            ) * mult
            if snapped != q:
                q = snapped
                notes.append("multiple")
        if lo is not None and q < lo:
            raise ConstraintError(
                "After rounding down to multiples of %s the quantity %s is below the minimum %s."
                % (multiple, dec(q), minimum),
                parameter="minimum",
                hint="Use multiple_rounding='ceiling' or lower the minimum.",
            )
        if hi is not None and q > hi:
            raise ConstraintError(
                "Required quantity %s exceeds the maximum %s." % (dec(q), maximum),
                parameter="maximum",
                hint="Split the order or raise the maximum.",
            )
    return ConstrainedQuantity(
        requested=dec(req), quantity=dec(q), increase=dec(q - req), adjustments=tuple(notes)
    )
