"""Common result model returned by ATICA calculations."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from .calculations.numeric import format_quantity
from .calculations.rounding import RoundingPolicy


@dataclass(frozen=True)
class CalculationResult:
    """Structured result of a single-output calculation.

    ``str(result)`` gives ``"<quantity> <unit>"`` e.g. ``"2500 g"``.
    """

    output_quantity: Decimal
    output_unit: Optional[str] = None
    input_quantity: Optional[Decimal] = None
    input_unit: Optional[str] = None
    formula: str = ""
    rounding_policy: RoundingPolicy = RoundingPolicy.NONE
    warnings: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def quantity(self) -> Decimal:
        return self.output_quantity

    @property
    def unit(self) -> Optional[str]:
        return self.output_unit

    def display(self, places: Optional[int] = None) -> str:
        """Format with *display* precision (does not change the stored value)."""
        text = format_quantity(self.output_quantity, places)
        return "%s %s" % (text, self.output_unit) if self.output_unit else text

    def __str__(self) -> str:
        return self.display()

    def to_dict(self) -> Dict[str, Any]:
        def fmt(v):
            return format_quantity(v) if isinstance(v, Decimal) else v

        return {
            "input_quantity": fmt(self.input_quantity),
            "input_unit": self.input_unit,
            "output_quantity": fmt(self.output_quantity),
            "output_unit": self.output_unit,
            "formula": self.formula,
            "rounding_policy": self.rounding_policy.value,
            "warnings": list(self.warnings),
            "metadata": {k: fmt(v) for k, v in self.metadata.items()},
        }
