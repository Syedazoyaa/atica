"""Unit validation rules."""
from __future__ import annotations

from typing import Any, Optional

from ..calculations.numeric import to_decimal
from ..exceptions import (
    AticaError,
    IncompatibleUnitError,
    InvalidConversionError,
    InvalidQuantityError,
    UnknownUnitError,
)
from ..units.converter import get_default_registry
from ..units.registry import UnitRegistry
from .result import ValidationResult


def validate_unit_conversion(
    value: Any, from_unit: str, to_unit: str, registry: Optional[UnitRegistry] = None
) -> ValidationResult:
    """Check a conversion request without performing it."""
    reg = registry or get_default_registry()
    result = ValidationResult()
    try:
        to_decimal(value, field="value")
    except InvalidQuantityError as exc:
        result.add_error(exc.code, "value", exc.message)
    units = {}
    for fld, name in (("from_unit", from_unit), ("to_unit", to_unit)):
        if not isinstance(name, str) or not name.strip():
            result.add_error("MISSING_UNIT", fld, "%s is required." % fld)
        elif not reg.has_unit(name):
            result.add_error("UNKNOWN_UNIT", fld, "Unknown unit %r." % name)
        else:
            units[fld] = reg.get(name)
    if len(units) == 2:
        a, b = units["from_unit"], units["to_unit"]
        if a.category != b.category:
            result.add_error(
                "INCOMPATIBLE_UNITS",
                "to_unit",
                "Cannot convert %s to %s (%s vs %s)." % (a.unit_id, b.unit_id, a.category, b.category),
            )
        elif not (a.exact and b.exact):
            result.add_warning("APPROXIMATE_FACTOR", None, "Conversion uses an approximate factor.")
    return result


def validate_custom_unit(
    name: Any, category: str, reference_unit: str, factor: Any, registry: Optional[UnitRegistry] = None
) -> ValidationResult:
    """Dry-run a custom unit registration on a copy of the registry."""
    reg = (registry or get_default_registry()).copy()
    result = ValidationResult()
    try:
        reg.register_unit(name, category, reference_unit, factor)
    except (UnknownUnitError, IncompatibleUnitError, InvalidConversionError, AticaError) as exc:
        result.add_error(exc.code, exc.field, exc.message)
    return result
