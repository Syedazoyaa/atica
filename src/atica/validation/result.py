"""Structured validation results (M09)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type

from ..calculations.numeric import to_decimal
from ..exceptions import AticaError, InvalidQuantityError, ValidationError


@dataclass
class ValidationIssue:
    code: str
    field: Optional[str]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "field": self.field, "message": self.message}


@dataclass
class ValidationResult:
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:
        return self.valid

    def add_error(self, code: str, field: Optional[str], message: str) -> None:
        self.errors.append(ValidationIssue(code, field, message))

    def add_warning(self, code: str, field: Optional[str], message: str) -> None:
        self.warnings.append(ValidationIssue(code, field, message))

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def raise_if_invalid(self, exc_class: Type[AticaError] = ValidationError) -> None:
        """Raise ``exc_class`` built from the first error (all errors in ``details``)."""
        if self.errors:
            first = self.errors[0]
            message = first.message
            if len(self.errors) > 1:
                message += " (+%d more problem(s))" % (len(self.errors) - 1)
            raise exc_class(message, code=first.code, field=first.field, details=self)


def parse_number(
    result: ValidationResult,
    value: Any,
    field: str,
    *,
    minimum: Optional[Decimal] = None,
    allow_equal_minimum: bool = True,
    code: str = "INVALID_NUMBER",
    min_code: Optional[str] = None,
    label: Optional[str] = None,
) -> Optional[Decimal]:
    """Parse ``value`` recording an error in ``result`` instead of raising."""
    label = label or field
    try:
        number = to_decimal(value, field=field)
    except InvalidQuantityError as exc:
        result.add_error(exc.code if code == "INVALID_NUMBER" else code, field, "%s: %s" % (label, exc.message))
        return None
    if minimum is not None:
        bad = number < minimum if allow_equal_minimum else number <= minimum
        if bad:
            cmp_text = "at least" if allow_equal_minimum else "greater than"
            result.add_error(min_code or code, field, "%s must be %s %s." % (label, cmp_text, minimum))
            return None
    return number
