# Quality - `atica.quality`

Yield, scrap, rework, recovery and wastage - four different things, kept apart:

| Term | Meaning | Counted in |
|---|---|---|
| **scrap** | units rejected and **not** recovered | units |
| **rework** | units that failed first inspection but are reprocessed | units |
| **recovery** | material reclaimed from waste (regrind, offcuts) | material |
| **wastage** | material that does not end up in good output (includes the material of scrapped units) | material |

Every percentage names its **denominator**. All percentages are on the 0-100 scale.

## Scrap, expected output, required input (`atica.quality.scrap`)

`scrap_percent = scrap / input x 100` where *input* is the quantity **started**.

| Function | Formula | Notes |
|---|---|---|
| `calculate_scrap_quantity(input_quantity, scrap_percent, *, rounding, places, unit)` | `input x s` | |
| `calculate_expected_output(input_quantity, scrap_percent, ...)` | `input x (1 - s)` | **100 % scrap is valid** and gives 0 |
| `calculate_required_input(good_output, scrap_percent, ...)` | `good / (1 - s)` | 100 % scrap with a positive target raises `ConstraintError` (impossible); with target 0 the answer is 0 |
| `calculate_scrap_percentage(input_quantity, scrap_quantity) -> PercentageResult` | `scrap / input x 100` | `input == 0` raises `ZeroDenominatorError`; `scrap > input` raises `ValidationError` |

The first three return `QualityQuantity` (`quantity`, `exact_quantity`, `unit`, `scrap_percent`, `rounding`, `formula`). Use `rounding="ceiling"` with `calculate_required_input` for whole units that still reach the target.

```python
from atica.quality import calculate_required_input, calculate_expected_output

print(calculate_required_input(950, 5))  # 1000
print(calculate_required_input(1000, 5, rounding="ceiling"))  # 1053
print(calculate_expected_output(500, 100))  # 0
```

## Yield and rework (`atica.quality.yields`)

Every started unit has exactly **one** first-pass outcome, and a reworked unit is counted **once**:

```text
input        = good_first_pass + sent_to_rework + first_pass_scrap
sent_to_rework = recovered_from_rework + rework_scrap
final_good   = good_first_pass + recovered_from_rework
final_scrap  = first_pass_scrap + rework_scrap
```

### `calculate_yield(input_quantity, good_first_pass, *, sent_to_rework=0, recovered_from_rework=0, first_pass_scrap=None, unit="") -> YieldResult`

| Field | Denominator |
|---|---|
| `first_pass_yield_percent` = good_first_pass / input | input |
| `final_yield_percent` = final_good / input | input |
| `rework_percent` = sent_to_rework / input | input |
| `scrap_percent` = final_scrap / input | input |
| `rework_recovery_percent` = recovered / sent_to_rework (`None` if nothing was reworked, with a warning) | reworked units |

`input_quantity` must be `> 0` (`ZeroDenominatorError`). Contradictions raise `ValidationError`: `good + rework > input`; `recovered > sent_to_rework`; a supplied `first_pass_scrap` that does not equal `input - good - rework`. Zero yield (`good_first_pass=0`) is valid.

```python
from atica.quality import calculate_yield

r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
print(r.first_pass_yield_percent, r.final_yield_percent, r.scrap_percent)  # 90 94.5 5.5
```

### `calculate_rework(input_quantity, *, first_pass_yield_percent, rework_percent=0, rework_recovery_percent=100) -> ReworkProjection`

*Projects* expected quantities from rates. `final yield = FPY + rework% x recovery% / 100`. `FPY + rework%` over 100 raises `InvalidConfigurationError`. Values are expected (statistical) quantities and not rounded, so `final_good + final_scrap == input` exactly.

### `required_input_with_rework(good_output, *, first_pass_yield_percent, rework_percent=0, rework_recovery_percent=100) -> Decimal`

Units to start to reach `good_output` final good units: `good / final_yield`; a final yield of 0 with a positive target raises `ZeroDenominatorError`.

## Wastage and recovery (`atica.quality.wastage`)

`gross_wastage = material_input - material_in_output`; `net_wastage = gross - recovered`. Percentages: `gross_wastage_percent`, `net_wastage_percent`, `utilisation_percent` are of **material_input**; `recovery_percent` is of the **gross wastage**.

* `calculate_wastage(material_input, material_in_output, *, recovered_quantity=None, recovery_percent=None, unit="") -> WastageResult` - give at most one recovery argument (`InvalidConfigurationError` if both); input `0` raises `ZeroDenominatorError`; output above input and recovery above waste raise `ValidationError`.
* `calculate_material_recovery(waste_quantity, recovery_percent, *, unit="") -> RecoveryResult` - `recovered = waste x recovery%/100`.

All quantities must be in one unit; `unit` is only a label.

## Verification

Hand-computed cases for every function (e.g. 1000 started, 900 first-pass, 60 reworked of which 45 recovered -> 94.5 % final, 55 scrapped = 40 + 15), 100 % scrap and zero-yield boundaries, conservation properties (`final_good + final_scrap == input`) and input/output round-trip properties.
