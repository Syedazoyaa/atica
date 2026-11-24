# Purchasing - `atica.purchasing`

One calculation domain, deliberately small: **no suppliers, purchase orders or procurement data**.

```python
from atica.purchasing import calculate_purchase_quantity
from atica.units import UnitRegistry

print(calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12))  # 96 piece

registry = UnitRegistry()
registry.register_unit("bag", 25, "kg")
r = calculate_purchase_quantity(130, unit="kg", purchase_unit="bag", order_multiple=1, registry=registry)
print(r.order_quantity, r.unit, r.received_quantity, r.stock_unit)  # 6 bag 150 kg
```

## `calculate_purchase_quantity(required_quantity, *, unit="", stock_on_hand=0, minimum_order_quantity=0, order_multiple=None, purchase_unit=None, registry=None) -> PurchaseQuantity`

| Parameter | Meaning |
|---|---|
| `required_quantity` | amount needed, `>= 0`, in `unit` |
| `unit` | unit of the requirement and the stock. A registry unit when `purchase_unit` is used; otherwise just a label |
| `stock_on_hand` | `>= 0`, in `unit`; deducted from the need |
| `minimum_order_quantity` | supplier minimum, in the **purchase unit** |
| `order_multiple` | orders must be a multiple of this, in the purchase unit; `None` = any amount (use `1` for indivisible units like bags) |
| `purchase_unit` | the unit you buy in; converted exactly from `unit` through the registry (custom units such as `bag = 25 kg` work) |

**Steps (all exact)**

1. `net = max(required - stock, 0)` (in the purchase unit). If `net == 0` nothing is ordered - the minimum is **not** forced on an order you do not need.
2. Raise to `minimum_order_quantity` if lower.
3. Round **up** to a multiple of `order_multiple` (package ceiling).

Result: `order_quantity` (in `unit` of the result = the purchase unit), `required_quantity`, `stock_deducted`, `net_requirement`, `surplus = order - net`, `constraints` (which of `minimum_order_quantity` / `order_multiple` raised the order), `received_quantity` (in the original `stock_unit`), `warnings` (e.g. a minimum that is not a multiple of the order multiple).

**Raises** `InvalidQuantityError`/`ValidationError` (negative quantities, non-positive multiple), `MissingInputError` (`purchase_unit` without `unit`), `UnknownUnitError`, `IncompatibleUnitError`.

Because arithmetic is exact, `0.3` with an order multiple of `0.1` is exactly `0.3` - never `0.30000000000000004` or a spurious extra step.
