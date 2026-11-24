"""Controllers: Qt-free adapters between the GUI forms and the ATICA public API.

Each function takes the raw form values (text) plus the session :class:`AppState`, calls the real
core API, and returns a presentation-ready :class:`~atica.gui.models.Outcome`.  They contain **no
calculation formulas** - only argument preparation and formatting.
"""

from . import (
    data_tools,
    materials_calc,
    packaging_calc,
    production_calc,
    purchasing_calc,
    quality_calc,
    unit_conversion,
)

__all__ = [
    "data_tools",
    "materials_calc",
    "packaging_calc",
    "production_calc",
    "purchasing_calc",
    "quality_calc",
    "unit_conversion",
]
