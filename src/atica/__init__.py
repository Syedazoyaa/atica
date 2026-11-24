"""ATICA - manufacturing calculations for Python, plus a desktop application.

One distribution, two components sharing one version:

* the calculation library (this package's ``units``, ``packaging``, ``materials``,
  ``production``, ``quality`` and ``purchasing`` sub-packages) - standard library only;
* the desktop GUI (``atica.gui``, started with the ``atica-gui`` command), which is a
  presentation layer over the same public APIs.

Importing ``atica`` never imports Qt or opens a window.

>>> from atica.units import convert
>>> str(convert(25, "kg", "g"))
'25000 g'
"""

from .core import (
    AticaError,
    Rounding,
    ValidationError,
    get_precision,
    use_precision,
)
from .materials import Bom, BomItem, calculate_bom_requirements, calculate_material_requirement
from .packaging import PackagingLevel, Product, breakdown
from .production import calculate_batches, production_time
from .purchasing import calculate_purchase_quantity
from .quality import calculate_required_input, calculate_yield
from .units import UnitRegistry, convert
from .version import __version__

__all__ = [
    "AticaError",
    "Bom",
    "BomItem",
    "PackagingLevel",
    "Product",
    "Rounding",
    "UnitRegistry",
    "ValidationError",
    "__version__",
    "breakdown",
    "calculate_batches",
    "calculate_bom_requirements",
    "calculate_material_requirement",
    "calculate_purchase_quantity",
    "calculate_required_input",
    "calculate_yield",
    "convert",
    "get_precision",
    "production_time",
    "use_precision",
]
