"""Packaging hierarchies and quantity breakdown (Module 02).

>>> from atica.packaging import Product, PackagingLevel, breakdown
>>> product = Product("P001", "Product A", levels=[
...     PackagingLevel("piece"),
...     PackagingLevel("box", 12, "piece"),       # 1 box = 12 pieces
...     PackagingLevel("carton", 20, "box"),      # 1 carton = 20 boxes
... ])
>>> print(breakdown(product, 250, "piece", "carton"))
250 piece = 1 full carton + 10 piece remaining (2 carton required)
"""

from .breakdown import (
    PackagingBreakdown,
    PackagingPlan,
    breakdown,
    convert_quantity,
    decompose,
    packages_required,
)
from .hierarchy import PackagingLevel, Product, levels_from_pairs

__all__ = [
    "PackagingBreakdown",
    "PackagingLevel",
    "PackagingPlan",
    "Product",
    "breakdown",
    "convert_quantity",
    "decompose",
    "levels_from_pairs",
    "packages_required",
]
