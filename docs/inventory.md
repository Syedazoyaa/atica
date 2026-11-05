# Purchasing and inventory (M07)

## calculate_purchase_quantity

```python
calculate_purchase_quantity(required_quantity, order_multiple=1, minimum_order_quantity=0, *, on_hand=0, unit="pieces")
```

1. `net = max(required - on_hand, 0)`; nothing is ordered when `net` is 0.
2. If `net` is below `minimum_order_quantity`, raise it to the MOQ.
3. Round **up** to the next multiple of `order_multiple`.

`calculate_purchase_quantity(87, 12, 24)` -> `96 pieces`. When the MOQ is not a multiple of the order multiple
(MOQ 30, multiple 12 -> 36) the result is still a valid multiple and `result.warnings` says so.
`result.metadata` has `net_requirement`, `surplus` and `constraints` (which rules changed the quantity:
`minimum_order_quantity`, `order_multiple`).

Invalid inputs raise `InventoryError` (`INVALID_ORDER_MULTIPLE`, `INVALID_MINIMUM_ORDER_QUANTITY`,
`INVALID_REQUIRED_QUANTITY`, `INVALID_STOCK_QUANTITY`).

## Supplier configurations

```python
cfg = PurchasingConfig("SUP-1", "PROD-A", purchase_unit="carton", stock_unit="box",
                       minimum_order_quantity=2, order_multiple=2,
                       conversion_configuration={"stock_units_per_purchase_unit": 20})   # optional
calculate_purchase_order(cfg, 41, on_hand=0, product=product, registry=registry)
```

MOQ and multiples are expressed in the **purchase unit**. The stock-to-purchase ratio comes from, in order:

1. `conversion_configuration["stock_units_per_purchase_unit"]`,
2. the same unit on both sides (ratio 1),
3. the product's packaging levels (when both units are levels of the product passed in),
4. the unit registry (e.g. `bag` and `kg`).

Otherwise `InventoryError` `MISSING_CONVERSION`. With `whole_units=True` (default) a partial purchase unit is rounded up first.
`result.metadata` includes `stock_quantity` (what arrives, in stock units) and `surplus_stock`.
