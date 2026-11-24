"""Yield, scrap, rework, recovery and wastage (Module 05).

>>> from atica.quality import calculate_required_input
>>> str(calculate_required_input(950, 5))
'1000'
"""

from .scrap import (
    PercentageResult,
    QualityQuantity,
    calculate_expected_output,
    calculate_required_input,
    calculate_scrap_percentage,
    calculate_scrap_quantity,
)
from .wastage import RecoveryResult, WastageResult, calculate_material_recovery, calculate_wastage
from .yields import (
    ReworkProjection,
    YieldResult,
    calculate_rework,
    calculate_yield,
    required_input_with_rework,
)

__all__ = [
    "PercentageResult",
    "QualityQuantity",
    "RecoveryResult",
    "ReworkProjection",
    "WastageResult",
    "YieldResult",
    "calculate_expected_output",
    "calculate_material_recovery",
    "calculate_required_input",
    "calculate_rework",
    "calculate_scrap_percentage",
    "calculate_scrap_quantity",
    "calculate_wastage",
    "calculate_yield",
    "required_input_with_rework",
]
