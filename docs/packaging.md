# Packaging hierarchies (M03) and breakdown (M04)

## Direction of a relationship

```python
PackagingLevel("box", contains=12, parent="piece")   # one box contains 12 pieces
```

`parent` is the **smaller level that `contains` counts** (this follows the example in the specification). The base level
(the smallest) has no parent and `contains == 1`. A valid hierarchy is a single chain: exactly one base level and each level is
the `parent` of at most one other level.

Level names are matched case-insensitively (`"Pallet"` finds `pallet`).

## Product API

```python
Product(product_id, name, description="", metadata=None)
product.add_level(level)                      # rejects duplicates, bad quantities, self-reference
product.update_level("box", contains=6)       # validated, unchanged on failure
product.remove_level("pallet")                # refused while another level is built from it
product.levels / packaging_hierarchy / base_packaging_unit / has_level(name) / get_level(name)
product.validate() -> ValidationResult        # never raises
product.base_size("pallet")                   # base units (pieces) in one pallet
product.units_per("pallet", "carton")         # 40
product.to_dict() / Product.from_dict(d) / product.copy()
```

Levels can be added in any order; the hierarchy is checked when you validate or calculate.

### Validation codes

`MISSING_LEVELS`, `DUPLICATE_LEVEL`, `INVALID_PACKAGE_QUANTITY` (must be a positive whole number), `MISSING_LEVEL`
(parent not defined), `CIRCULAR_HIERARCHY`, `DISCONNECTED_HIERARCHY` (several base levels or branches),
`INCONSISTENT_RELATIONSHIP` (base level must contain 1).

Calculations on an invalid product raise `InvalidHierarchyError` with the first problem (all problems in `exc.details`).

## Breakdown

```python
breakdown(product, quantity, from_unit, to_unit, *, allow_partial=False) -> BreakdownResult
```

| Field | Meaning |
|---|---|
| `full_packages` | complete `to_unit` packages |
| `remaining_quantity` | leftover in `from_unit` - never discarded |
| `packages_required` | packages needed to hold everything (`ceil`) |
| `exact_equivalent` | exact, possibly fractional, equivalent |
| `total_quantity` | the input quantity |

850 cartons into pallets (1 pallet = 40 cartons) gives 21 full pallets, 10 cartons left, 22 pallets required.
Converting to a *smaller* unit (`2 pallet -> carton`) gives 80 full cartons and no remainder.
Fractional quantities raise `PARTIAL_NOT_ALLOWED` unless `allow_partial=True`; negative quantities raise `NEGATIVE_QUANTITY`.

Related helpers: `convert_quantity(product, qty, from, to)` (exact equivalent) and
`decompose(product, qty, from_unit)` (`262 pieces -> {'pallet': 0, 'carton': 1, 'box': 1, 'piece': 10}`).

Each product has its own hierarchy; products never share or leak configuration.
