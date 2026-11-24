"""Bill of materials: requirements with scrap/wastage, and what the stock can make."""

from atica.materials import Bom, BomItem, calculate_bom_requirements, calculate_producible_quantity

bom = Bom(
    [
        BomItem("steel", "0.25", "kg"),
        BomItem("paint", "40", "mL", wastage_percent=10),
        BomItem("screws", 4, "piece"),
    ],
    product_id="P001",
)

result = calculate_bom_requirements(bom=bom, production_quantity=1000, scrap_percent=5, rounding="ceiling")
for line in result.totals:
    print(f"{line.material_id:<7}{line.quantity:>8} {line.unit}")
assert str(result["steel"]) == "264 kg"  # 0.25 x 1000 / 0.95 = 263.16 -> ceiling

capacity = calculate_producible_quantity(bom, {"steel": (100, "kg"), "paint": (50, "L"), "screws": 1000})
print(capacity.producible_quantity, "units, limited by", capacity.limiting_material)
assert capacity.limiting_material == "screws" and int(capacity.producible_quantity) == 250
