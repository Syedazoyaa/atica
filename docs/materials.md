# Materials and BOM - `atica.materials`

Material requirements and capacity. This is **not** a material database or an inventory system: you pass the data in, you get numbers out.

```python
from atica.materials import Bom, BomItem, calculate_bom_requirements

bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("paint", "40", "mL", wastage_percent=10)])
result = calculate_bom_requirements(bom=bom, production_quantity=1000)
print(result["steel"])  # 250 kg
print(result["paint"])  # 44444.4444444444 mL
```

## The two percentages, and their denominators

| Parameter | Meaning | Denominator | Effect |
|---|---|---|---|
| `scrap_percent` | share of **units started** that are rejected | units started | `started = good / (1 - scrap/100)` |
| `wastage_percent` | share of **material issued** (gross) lost in processing | gross material | `gross = used / (1 - wastage/100)` |

Both are on the 0-100 scale and must be **below 100**. They describe different losses and are both applied (a scrapped unit consumed its full material, *and* the process loses wastage on everything issued). If your plant quotes wastage as a *markup on net* `m` %, use `wastage_percent = 100 x m / (100 + m)`.

## `BomItem(material_id, quantity_per_unit, unit, wastage_percent=0, name="")`

One line. `quantity_per_unit` is the **net** amount in one finished unit and must be `> 0`. The unit must be known to the registry used for the calculation (checked at calculation time; a missing unit is a `MissingInputError`).

## `Bom(items, product_id="", allow_duplicates=False)`

Immutable. Material ids are compared ignoring case. **Duplicates are rejected** (`DuplicateMaterialError`) unless `allow_duplicates=True`, in which case the lines are kept separately in `lines` *and* summed per material in `totals` (units converted to the first line's unit; incompatible units raise). `to_dict()` / `Bom.from_dict()` round-trip.

## `calculate_material_requirement(quantity_per_unit, production_quantity, unit, *, wastage_percent=0, scrap_percent=0, rounding="none", places=0, report_unit=None, material_id="", registry=None) -> MaterialRequirement`

**Formula** `started = good / (1 - s)`; `used = per_unit x started`; `gross = used / (1 - w)` (s, w as fractions).

Result: `quantity` (after rounding) and `exact_quantity`, plus the **breakdown**
`exact_quantity = base_quantity + scrap_allowance + wastage_allowance` where
`base = per_unit x good`, `scrap_allowance = per_unit x (started - good)`, `wastage_allowance = gross - used`; also `units_started`, `unit` (the `report_unit` if given, converted exactly), `rounding`, `places`.

**Raises** `UnknownUnitError`, `IncompatibleUnitError` (`report_unit`), `UnsupportedOperationError` (offset temperature units), `InvalidQuantityError`, `InvalidPercentageError` (outside 0..<100), `InvalidRoundingError`.

## `calculate_bom_requirements(bom, production_quantity, *, scrap_percent=0, rounding="none", places=0, report_units=None, registry=None) -> BomRequirements`

The above for every line. `report_units={"steel": "g"}` reports chosen materials in another compatible unit; naming a material that is not in the BOM raises `InvalidConfigurationError`. Result: `lines`, `totals`, `by_material()`, `result["steel"]`.

Rounding is applied **per material total** and is explicit (default none).

## `calculate_producible_quantity(bom, available, *, scrap_percent=0, rounding="floor", places=0, registry=None) -> ProductionCapacity`

How many **good** units the stock can make. `available` is `{material_id: quantity}` (in the BOM line's unit) or `{material_id: (quantity, unit)}` for any compatible unit.

**Formula** per material: `producible = available x (1 - s) / sum(q_i / (1 - w_i))` over that material's lines; the answer is the minimum, and `limiting_material` names it.

* **Every BOM material must be listed**: a missing one raises `MissingInputError` (never assumed zero or unlimited); listing a material not in the BOM raises `InvalidConfigurationError` (usually a typo).
* Default rounding is `floor` (whole units you can really finish); use `rounding="none"` for the exact figure.

Result: `producible_quantity`, `exact_quantity`, `limiting_material`, `materials` (per-material `available`, `required_per_unit`, `producible_units`).

```python
from atica.materials import Bom, BomItem, calculate_producible_quantity

bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("screws", 4, "piece")])
cap = calculate_producible_quantity(bom, {"steel": (100, "kg"), "screws": 1000})
print(int(cap.producible_quantity), cap.limiting_material)  # 250 screws
```

## Verification

Hand-calculated cases (e.g. 90 good, 10 % scrap, 2 kg each, 20 % wastage -> `250 kg`, split `180 + 20 + 50`), the invariant `base + scrap + wastage == exact`, capacity/requirement consistency, and property tests against an independent `Fraction` formula.
