"""Internal helpers shared by manufacturing calculations."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ..calculations.numeric import calc_context
from ..exceptions import ManufacturingError
from ..validation.manufacturing_rules import check_rate
from ..validation.result import ValidationResult, parse_number


def number(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    code: str = "INVALID_QUANTITY",
    label: Optional[str] = None,
) -> Decimal:
    """Parse a non-negative (or strictly positive) number or raise ManufacturingError."""
    result = ValidationResult()
    n = parse_number(
        result, value, field, minimum=Decimal(0), allow_equal_minimum=not positive, code=code, label=label or field
    )
    result.raise_if_invalid(ManufacturingError)
    return n  # type: ignore[return-value]


def resolve_rate(
    rate: Any = None,
    percent: Any = None,
    *,
    field: str = "scrap_rate",
    code: str = "INVALID_SCRAP_RATE",
) -> Decimal:
    """Return a fractional rate in ``[0, 1)`` from either a fraction or a percentage."""
    if rate is not None and percent is not None:
        raise ManufacturingError(
            "Give either %s (fraction) or its percent form, not both." % field, code="AMBIGUOUS_RATE", field=field
        )
    if percent is not None:
        pct = number(percent, field.replace("_rate", "_percent"), code=code)
        with calc_context():
            rate = pct / Decimal(100)
    result = ValidationResult()
    value = check_rate(result, 0 if rate is None else rate, field, code)
    result.raise_if_invalid(ManufacturingError)
    return value  # type: ignore[return-value]
