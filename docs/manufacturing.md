# Manufacturing (M05) and yield / scrap / wastage (M06)

**Rates are fractions** - `0.05` means 5 %. Each rate argument has a `*_percent` twin (`scrap_percent=5`); give only one.
A rate must satisfy `0 <= rate < 1`; `1` would mean zero usable output (division by zero) and is rejected with
`INVALID_SCRAP_RATE` / `INVALID_WASTAGE_RATE`.

## Terms

* **scrap** - rejected, unrecoverable units. Lowers good output per unit started.
* **rework** - units failing first pass but recovered (tracked by `calculate_yield`).
* **wastage** - material lost in the process (`input - material in good output`): scrap plus unavoidable process loss.

## calculate_material_requirement

```python
calculate_material_requirement(
    material_per_unit=None, production_quantity=None, material_unit=None, *,
    target_output=None,          # synonym of production_quantity
    scrap_rate=None, scrap_percent=None, wastage_rate=None,
    rounding="none", places=0, multiple=1,      # rounds the returned figure
    units_rounding="none", units_places=0,      # rounds units started (e.g. "up" for whole units)
    output_unit=None, registry=None)            # convert the material total through the unit registry
```

| Call | Result |
|---|---|
| `("0.5", 1000, "kg")` | `500 kg` |
| `(target_output=1000, scrap_rate="0.05")` | `1052.631578...` units to start |
| `(target_output=1000, scrap_rate="0.05", rounding="up")` | `1053` |
| `("0.5", 1000, "kg", scrap_rate="0.05", units_rounding="up")` | `526.5 kg` (1053 units x 0.5) |
| `("0.5", 1000, "kg", wastage_rate="0.2")` | `625 kg` (0.5 / 0.8 per unit) |
| `("0.5", 1000, "kg", output_unit="g")` | `500000 g` |

`result.metadata` holds `units_to_process`, `exact_quantity`, and the rates used.

## Other functions

* `calculate_required_input(good, scrap_rate)` / `calculate_expected_output(input, scrap_rate)` / `calculate_scrap_quantity`
* `calculate_scrap_percentage(total_input, scrap_quantity)` -> percent
* `calculate_yield(total_input, good_output, rework_quantity=0)` -> `YieldResult` (yield, scrap, rework rates)
* `calculate_wastage(material_input, material_in_output, scrap_quantity=0)` -> `WastageResult` (total, scrap, process loss)
* `calculate_batches(total, batch_size)` -> full batches, leftover, batches required, last batch size
* `calculate_batch_material`, `calculate_production_time`, `calculate_producible_quantity(available, per_unit, ...)`
* `Material(material_id, name, unit, consumption_per_unit, wastage_rate)` with `.requirement(qty, scrap_rate=...)`;
  `calculate_bom_requirements(materials, qty)`

## Formulas

```python
from atica.manufacturing import Formula, evaluate_formula
evaluate_formula("qty * per_unit / (1 - scrap)", qty=1000, per_unit="0.5", scrap="0.05")
f = Formula("max(a, b) * 2"); f.variables   # {'a', 'b'}
```

Supported: numbers, variables, `+ - * / ^` (or `**`), parentheses and `min max abs ceil floor round sqrt`.
It is a hand-written parser; there is no `eval`, attribute access, indexing or lambda. Limits: 500 characters,
nesting depth 40, whole-number exponents within ±100. Errors raise `ManufacturingError` with codes such as
`INVALID_FORMULA`, `UNKNOWN_VARIABLE`, `UNKNOWN_FUNCTION`, `DIVISION_BY_ZERO`.
