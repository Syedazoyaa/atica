"""Bulk (file) validation rules."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, Mapping

from .result import ValidationResult, parse_number

REQUIRED_FIELDS = ("quantity", "from_unit", "to_unit")


def validate_columns(headers: Iterable[str], mapping: Mapping[str, str]) -> ValidationResult:
    """Check that every required logical field is mapped to an existing column."""
    result = ValidationResult()
    present = set(headers)
    for logical in REQUIRED_FIELDS:
        column = mapping.get(logical)
        if column is None:
            result.add_error("MISSING_COLUMN", logical, "Required column for '%s' was not found." % logical)
        elif column not in present:
            result.add_error("MISSING_COLUMN", logical, "Column %r (mapped to '%s') is not in the file." % (column, logical))
    return result


def validate_row_fields(row: Mapping[str, Any], mapping: Mapping[str, str]) -> ValidationResult:
    """Check emptiness and numeric format of a bulk row's required fields."""
    result = ValidationResult()
    for logical in REQUIRED_FIELDS:
        raw = row.get(mapping[logical])
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            result.add_error("EMPTY_VALUE", logical, "'%s' is empty." % logical)
    if all(e.field != "quantity" for e in result.errors):
        parse_number(result, row.get(mapping["quantity"]), "quantity", label="Quantity")
    return result
