"""Batch capacity: how many batches fit into available time."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Tuple

from ..core.precision import dec
from ..core.results import Result
from ..core.validation import positive
from ..units import UnitRegistry, default_registry
from .time import _require_time, duration


@dataclass(frozen=True)
class BatchCapacity(Result):
    """Result of :func:`calculate_batch_capacity`.

    ``full_batches`` complete batches fit; ``leftover_time`` is what remains (shorter than one
    batch) and ``next_batch_fraction`` how much of another batch it covers.  ``quantity`` is
    the output of the full batches when a ``batch_size`` was given.
    """

    full_batches: Decimal
    leftover_time: Decimal
    time_unit: str
    next_batch_fraction: Decimal
    time_per_batch: Decimal
    batch_size: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    formula: str = (
        "full = floor(available_time / time_per_batch); leftover = available - full x time_per_batch"
    )
    warnings: Tuple[str, ...] = ()


def calculate_batch_capacity(
    available_time: Any,
    time_per_batch: Any,
    *,
    time_unit: str = "h",
    batch_size: Any = None,
    registry: Optional[UnitRegistry] = None,
) -> BatchCapacity:
    """Number of complete batches that fit into ``available_time``.

    Times are numbers in ``time_unit`` or ``(number, unit)`` pairs (so 8 hours against 45-minute
    batches is ``calculate_batch_capacity(8, (45, "min"))``).  ``time_per_batch`` must be > 0.

    >>> r = calculate_batch_capacity(8, (45, "min"), batch_size=100)
    >>> (int(r.full_batches), int(r.quantity))
    (10, 1000)
    """
    reg = registry or default_registry()
    _require_time(reg, time_unit, "time_unit")
    avail = duration(available_time, "available_time", time_unit, time_unit, reg)
    per_batch = duration(time_per_batch, "time_per_batch", time_unit, time_unit, reg)
    positive(per_batch, "time_per_batch")
    full = math.floor(avail / per_batch)
    leftover = avail - full * per_batch
    size = positive(batch_size, "batch_size") if batch_size is not None else None
    return BatchCapacity(
        full_batches=Decimal(full),
        leftover_time=dec(leftover),
        time_unit=reg.get(time_unit).symbol,
        next_batch_fraction=dec(leftover / per_batch),
        time_per_batch=dec(per_batch),
        batch_size=dec(size) if size is not None else None,
        quantity=dec(full * size) if size is not None else None,
    )
