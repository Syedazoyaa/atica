"""Purchasing: stock, minimum order quantity, order multiples and a purchase unit."""

from atica.purchasing import calculate_purchase_quantity
from atica.units import UnitRegistry

print(calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12))  # 96 piece

registry = UnitRegistry()
registry.register_unit("bag", 25, "kg")
r = calculate_purchase_quantity(
    130, unit="kg", stock_on_hand=0, purchase_unit="bag", order_multiple=1, registry=registry
)
print(r.order_quantity, r.unit, "=", r.received_quantity, r.stock_unit, "| surplus:", r.surplus, r.unit)
assert str(r) == "6 bag" and str(r.received_quantity) == "150"
