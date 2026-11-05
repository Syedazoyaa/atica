"""Centralised exception hierarchy for ATICA.

Every exception carries a machine-readable ``code`` and a human-readable
``message`` so that callers (and the GUI) can react programmatically or show
a readable message without exposing stack traces.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class AticaError(Exception):
    """Base class for every error raised by ATICA."""

    code = "ATICA_ERROR"

    def __init__(
        self,
        message: str = "",
        *,
        code: Optional[str] = None,
        field: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.field = field
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "field": self.field, "message": self.message}


class UnitError(AticaError):
    code = "UNIT_ERROR"


class UnknownUnitError(UnitError):
    code = "UNKNOWN_UNIT"


class IncompatibleUnitError(UnitError):
    code = "INCOMPATIBLE_UNITS"


class InvalidConversionError(UnitError):
    code = "INVALID_CONVERSION"


class PackagingError(AticaError):
    code = "PACKAGING_ERROR"


class InvalidHierarchyError(PackagingError):
    code = "INVALID_HIERARCHY"


class UnknownProductError(PackagingError):
    code = "UNKNOWN_PRODUCT"


class ManufacturingError(AticaError):
    code = "MANUFACTURING_ERROR"


class InventoryError(AticaError):
    code = "INVENTORY_ERROR"


class ValidationError(AticaError):
    code = "VALIDATION_ERROR"


class InvalidQuantityError(ValidationError):
    code = "INVALID_QUANTITY"


class BulkProcessingError(AticaError):
    code = "BULK_PROCESSING_ERROR"


class ConfigurationError(AticaError):
    """Raised when a saved configuration cannot be loaded or is malformed."""

    code = "CONFIGURATION_ERROR"
