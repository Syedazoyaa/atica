"""Manufacturing, yield/scrap and inventory validation rules.

Rates are **fractions** (``0.05`` = 5 %) and must satisfy ``0 <= rate < 1``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from .result import ValidationResult, parse_number


def check_rate(
    result: ValidationResult, value: Any, field: str, code: str = "INVALID_SCRAP_RATE"
) -> Optional[Decimal]:
    """Validate a fractional rate in ``[0, 1)``."""
    rate = parse_number(result, value, field, code=code, label=field)
    if rate is None:
        return None
    if rate < 0 or rate >= 1:
        hint = " (a rate of 1 would mean zero usable output)" if rate == 1 else ""
        result.add_error(
            code,
            field,
            "%s must be a fraction from 0 up to (but excluding) 1, e.g. 0.05 for 5%%%s; got %s." % (field, hint, rate),
        )
        return None
    return rate


def validate_production_inputs(
    production_quantity: Any = None,
    material_per_unit: Any = None,
    scrap_rate: Any = None,
    wastage_rate: Any = None,
    *,
    require_quantity: bool = True,
) -> ValidationResult:
    result = ValidationResult()
    if production_quantity is None:
        if require_quantity:
            result.add_error("MISSING_INPUT", "production_quantity", "A production quantity / target output is required.")
    else:
        parse_number(
            result,
            production_quantity,
            "production_quantity",
            minimum=Decimal(0),
            min_code="INVALID_PRODUCTION_QUANTITY",
            code="INVALID_PRODUCTION_QUANTITY",
            label="Production quantity",
        )
    if material_per_unit is not None:
        parse_number(
            result,
            material_per_unit,
            "material_per_unit",
            minimum=Decimal(0),
            code="INVALID_MATERIAL_CONSUMPTION",
            label="Material per unit",
        )
    if scrap_rate is not None:
        check_rate(result, scrap_rate, "scrap_rate", "INVALID_SCRAP_RATE")
    if wastage_rate is not None:
        check_rate(result, wastage_rate, "wastage_rate", "INVALID_WASTAGE_RATE")
    return result


def validate_material(material_id: Any, unit: Any, consumption_per_unit: Any, wastage_rate: Any = 0) -> ValidationResult:
    result = ValidationResult()
    if not isinstance(material_id, str) or not material_id.strip():
        result.add_error("MISSING_MATERIAL", "material_id", "A material identifier is required.")
    if not isinstance(unit, str) or not unit.strip():
        result.add_error("MISSING_UNIT", "unit", "A material unit is required.")
    parse_number(
        result, consumption_per_unit, "consumption_per_unit", minimum=Decimal(0),
        code="INVALID_MATERIAL_CONSUMPTION", label="Consumption per unit",
    )
    check_rate(result, wastage_rate, "wastage_rate", "INVALID_WASTAGE_RATE")
    return result


def validate_purchase_inputs(
    required_quantity: Any, order_multiple: Any = 1, minimum_order_quantity: Any = 0, on_hand: Any = 0
) -> ValidationResult:
    result = ValidationResult()
    parse_number(result, required_quantity, "required_quantity", minimum=Decimal(0),
                 code="INVALID_REQUIRED_QUANTITY", label="Required quantity")
    parse_number(result, order_multiple, "order_multiple", minimum=Decimal(0), allow_equal_minimum=False,
                 code="INVALID_ORDER_MULTIPLE", label="Order multiple")
    parse_number(result, minimum_order_quantity, "minimum_order_quantity", minimum=Decimal(0),
                 code="INVALID_MINIMUM_ORDER_QUANTITY", label="Minimum order quantity")
    parse_number(result, on_hand, "on_hand", minimum=Decimal(0), code="INVALID_STOCK_QUANTITY", label="On-hand quantity")
    return result
