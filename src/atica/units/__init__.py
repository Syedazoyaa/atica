"""Physical unit conversion (M01) and custom units (M02)."""
from .categories import BASE_UNITS, CATEGORY_DESCRIPTIONS
from .converter import (
    are_compatible,
    convert,
    get_base_unit,
    get_custom_unit,
    get_default_registry,
    get_unit,
    list_categories,
    list_custom_units,
    list_units,
    load_units,
    register_unit,
    remove_unit,
    reset_default_registry,
    save_units,
    update_unit,
)
from .definitions import Unit
from .registry import UnitRegistry

__all__ = [
    "BASE_UNITS",
    "CATEGORY_DESCRIPTIONS",
    "Unit",
    "UnitRegistry",
    "are_compatible",
    "convert",
    "get_base_unit",
    "get_custom_unit",
    "get_default_registry",
    "get_unit",
    "list_categories",
    "list_custom_units",
    "list_units",
    "load_units",
    "register_unit",
    "remove_unit",
    "reset_default_registry",
    "save_units",
    "update_unit",
]
