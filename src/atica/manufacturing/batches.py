"""Batch calculations (M05)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any, Dict, Optional

from ..calculations.numeric import calc_context, clean, plain_number
from ..results import CalculationResult
from ._common import number, resolve_rate


@dataclass(frozen=True)
class BatchResult:
    total_quantity: Decimal
    batch_size: Decimal
    full_batches: Decimal
    remainder: Decimal  # quantity left over after the full batches
    batches_required: Decimal  # including a final partial batch
    last_batch_quantity: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {k: plain_number(v) for k, v in self.__dict__.items()}


def calculate_batches(total_quantity: Any, batch_size: Any) -> BatchResult:
    """Split ``total_quantity`` into batches of ``batch_size``; the remainder is reported."""
    total = number(total_quantity, "total_quantity", code="INVALID_PRODUCTION_QUANTITY")
    size = number(batch_size, "batch_size", positive=True, code="INVALID_BATCH_SIZE")
    with calc_context():
        exact = total / size
        full = exact.to_integral_value(rounding=ROUND_FLOOR)
        required = exact.to_integral_value(rounding=ROUND_CEILING)
        remainder = total - full * size
        last = remainder if remainder else (size if required else Decimal(0))
        return BatchResult(
            total, size, clean(full), clean(remainder), clean(required), clean(last)
        )


def calculate_batch_material(
    material_per_unit: Any, batch_size: Any, material_unit: Optional[str] = None, *, scrap_rate: Any = None
) -> CalculationResult:
    """Material consumed by one batch of ``batch_size`` good units."""
    from .materials import calculate_material_requirement

    return calculate_material_requirement(
        material_per_unit, batch_size, material_unit, scrap_rate=scrap_rate
    )


def calculate_production_time(total_quantity: Any, units_per_hour: Any) -> CalculationResult:
    """Hours needed to make ``total_quantity`` at ``units_per_hour``."""
    total = number(total_quantity, "total_quantity", code="INVALID_PRODUCTION_QUANTITY")
    rate = number(units_per_hour, "units_per_hour", positive=True, code="INVALID_PRODUCTION_RATE")
    with calc_context():
        hours = clean(total / rate)
    return CalculationResult(hours, "hour", total, None, "total_quantity / units_per_hour")
