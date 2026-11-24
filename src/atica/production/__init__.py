"""Production calculations (Module 04): batches, constraints, time and capacity.

>>> from atica.production import calculate_batches
>>> plan = calculate_batches(250, 100)
>>> (int(plan.full_batches), int(plan.partial_batch_quantity), int(plan.batches_required))
(2, 50, 3)
"""

from .batches import (
    BatchMaterial,
    BatchMaterialPlan,
    BatchPlan,
    ConstrainedQuantity,
    calculate_batch_materials,
    calculate_batches,
    constrain_production_quantity,
)
from .capacity import BatchCapacity, calculate_batch_capacity
from .time import CapacityResult, ProductionTime, production_capacity, production_time

__all__ = [
    "BatchCapacity",
    "BatchMaterial",
    "BatchMaterialPlan",
    "BatchPlan",
    "CapacityResult",
    "ConstrainedQuantity",
    "ProductionTime",
    "calculate_batch_capacity",
    "calculate_batch_materials",
    "calculate_batches",
    "constrain_production_quantity",
    "production_capacity",
    "production_time",
]
