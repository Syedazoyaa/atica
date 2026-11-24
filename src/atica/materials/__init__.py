"""Material and BOM calculations (Module 03).

>>> from atica.materials import Bom, BomItem, calculate_bom_requirements
>>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("paint", "40", "mL", wastage_percent=10)])
>>> result = calculate_bom_requirements(bom=bom, production_quantity=1000)
>>> str(result["steel"])
'250 kg'
"""

from .bom import (
    BomRequirements,
    MaterialCapacity,
    ProductionCapacity,
    calculate_bom_requirements,
    calculate_producible_quantity,
)
from .material import Bom, BomItem, MaterialRequirement, calculate_material_requirement

__all__ = [
    "Bom",
    "BomItem",
    "BomRequirements",
    "MaterialCapacity",
    "MaterialRequirement",
    "ProductionCapacity",
    "calculate_bom_requirements",
    "calculate_material_requirement",
    "calculate_producible_quantity",
]
