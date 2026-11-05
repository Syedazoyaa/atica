"""ATICA - manufacturing units, packaging and quantity conversion library.

Quick start::

    from atica.units import convert
    print(convert("2.5", "kg", "g"))      # 2500 g

The core library uses only the Python standard library.
"""
from .calculations import RoundingPolicy, round_value
from .config import AticaConfig
from .exceptions import (
    AticaError,
    BulkProcessingError,
    ConfigurationError,
    IncompatibleUnitError,
    InvalidConversionError,
    InvalidHierarchyError,
    InvalidQuantityError,
    InventoryError,
    ManufacturingError,
    PackagingError,
    UnitError,
    UnknownProductError,
    UnknownUnitError,
    ValidationError,
)
from .inventory import calculate_purchase_quantity
from .manufacturing import calculate_material_requirement
from .packaging import PackagingLevel, Product, breakdown
from .results import CalculationResult
from .units import UnitRegistry, convert, register_unit

__version__ = "0.8.0"

__all__ = [
    "AticaConfig",
    "AticaError",
    "BulkProcessingError",
    "CalculationResult",
    "ConfigurationError",
    "IncompatibleUnitError",
    "InvalidConversionError",
    "InvalidHierarchyError",
    "InvalidQuantityError",
    "InventoryError",
    "ManufacturingError",
    "PackagingError",
    "PackagingLevel",
    "Product",
    "RoundingPolicy",
    "UnitError",
    "UnitRegistry",
    "UnknownProductError",
    "UnknownUnitError",
    "ValidationError",
    "__version__",
    "breakdown",
    "calculate_material_requirement",
    "calculate_purchase_quantity",
    "convert",
    "register_unit",
    "round_value",
]
