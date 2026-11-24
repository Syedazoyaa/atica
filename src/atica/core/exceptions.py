"""Exception hierarchy for ATICA.

Every error raised deliberately by ATICA derives from :class:`AticaError` and
carries:

* ``message``   - what went wrong and why;
* ``parameter`` - the argument (or field) that caused it, when there is one;
* ``hint``      - how the caller can correct it, when that is known;
* ``code``      - a stable, machine-readable identifier (class attribute).

Validation errors also derive from :class:`ValueError`, and arithmetic errors
from :class:`ArithmeticError`, so generic ``except ValueError`` code keeps working.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AticaError(Exception):
    """Base class of every error raised by ATICA."""

    code = "ATICA_ERROR"

    def __init__(
        self,
        message: str,
        *,
        parameter: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.parameter = parameter
        self.hint = hint

    def __str__(self) -> str:
        text = self.message
        if self.hint:
            text += " Hint: " + self.hint
        return text

    def to_dict(self) -> Dict[str, Any]:
        """Plain-data form, handy for APIs and logs."""
        return {
            "code": self.code,
            "message": self.message,
            "parameter": self.parameter,
            "hint": self.hint,
        }


# --------------------------------------------------------------------- validation
class ValidationError(AticaError, ValueError):
    """An input value is missing, malformed or outside its allowed range."""

    code = "VALIDATION_ERROR"


class MissingInputError(ValidationError):
    """A required input was not supplied."""

    code = "MISSING_INPUT"


class InvalidQuantityError(ValidationError):
    """A quantity is not a finite number, or is negative/zero where that is not allowed."""

    code = "INVALID_QUANTITY"


class InvalidPercentageError(ValidationError):
    """A percentage is outside its permitted range."""

    code = "INVALID_PERCENTAGE"


class InvalidRoundingError(ValidationError):
    """An unknown rounding policy, or an inconsistent rounding configuration."""

    code = "INVALID_ROUNDING"


class InvalidConfigurationError(ValidationError):
    """A combination of arguments or a configuration object is not usable."""

    code = "INVALID_CONFIGURATION"


# ------------------------------------------------------------------- calculation
class CalculationError(AticaError, ArithmeticError):
    """Valid inputs for which the requested calculation has no valid answer."""

    code = "CALCULATION_ERROR"


class ZeroDenominatorError(CalculationError, ZeroDivisionError):
    """A ratio or percentage would divide by zero."""

    code = "ZERO_DENOMINATOR"


class NumericRangeError(CalculationError, OverflowError):
    """A number is outside the range ATICA can represent safely."""

    code = "NUMERIC_RANGE"


class ConstraintError(CalculationError):
    """Requested constraints (minimum, maximum, multiples ...) cannot be satisfied together."""

    code = "CONSTRAINT_VIOLATION"


class UnsupportedOperationError(AticaError):
    """The operation is not supported for these inputs (for example, offset units in a BOM)."""

    code = "UNSUPPORTED_OPERATION"


# --------------------------------------------------------------------------- units
class UnitError(AticaError):
    """Base class for unit problems."""

    code = "UNIT_ERROR"


class UnknownUnitError(UnitError, ValueError):
    """A unit name is not defined in the registry."""

    code = "UNKNOWN_UNIT"


class IncompatibleUnitError(UnitError, ValueError):
    """Units measure different kinds of quantity and cannot be converted."""

    code = "INCOMPATIBLE_UNITS"


class UnitDefinitionError(UnitError, ValueError):
    """A custom unit definition is invalid."""

    code = "INVALID_UNIT_DEFINITION"


# ------------------------------------------------------------------------ packaging
class PackagingError(AticaError):
    """Base class for packaging problems."""

    code = "PACKAGING_ERROR"


class InvalidHierarchyError(PackagingError, ValueError):
    """A packaging hierarchy is inconsistent, circular, disconnected or duplicated."""

    code = "INVALID_HIERARCHY"


class UnknownPackagingLevelError(PackagingError, ValueError):
    """A packaging level name is not part of the product's hierarchy."""

    code = "UNKNOWN_PACKAGING_LEVEL"


# ------------------------------------------------------------------------ materials
class MaterialError(AticaError):
    """Base class for BOM / material problems."""

    code = "MATERIAL_ERROR"


class DuplicateMaterialError(MaterialError, ValueError):
    """The same material identifier appears more than once where that is not allowed."""

    code = "DUPLICATE_MATERIAL"


# --------------------------------------------------------------------- integrations
class IntegrationError(AticaError):
    """A file could not be read, written or understood."""

    code = "INTEGRATION_ERROR"


class MissingDependencyError(IntegrationError, ImportError):
    """An optional dependency required by an integration is not installed."""

    code = "MISSING_DEPENDENCY"
