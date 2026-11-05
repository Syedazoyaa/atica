# Architecture

## Layout

```
src/atica/
  exceptions.py        error hierarchy (every error has .code, .message, .field)
  results.py           CalculationResult - the common result model
  config.py            AticaConfig: versioned save/load of units, products, materials, purchasing
  calculations/        numeric.py (Decimal helpers), rounding.py (M10)
  units/               M01 + M02: definitions, categories, registry, custom_units, converter (module API)
  packaging/           M03 + M04: hierarchy (PackagingLevel), product (Product), breakdown
  manufacturing/       M05 + M06: materials, batches, formulas, yield_scrap
  inventory/           M07: purchasing
  validation/          M09: result model + rules per area
  io/                  M08: csv_handler, excel_handler, bulk
app/gui/               PySide6 desktop app (calls the public API only)
```

Dependency direction (no cycles): `exceptions` ← `calculations` ← `results` ← `units` ← `validation`/`packaging` ← `manufacturing`, `inventory` ← `io` ← `config`.
`validation` modules depend only on `calculations` (and `units` for unit rules), so calculators can reuse them.

## Principles

* **Own conversion engine.** `units` holds all physical knowledge. Nothing else converts physical units; `manufacturing` and `inventory` call `UnitRegistry.convert`.
* **Packaging is not physics.** Packaging relationships live on a `Product`, never in the unit registry.
* **Stateless core.** Everything works in memory. `AticaConfig` serialises to plain JSON (no pickle, nothing executable).
* **One validation source.** Validators return a `ValidationResult`; calculators call them and `raise_if_invalid(ExcClass)`, so structured results and exceptions always agree.
* **Isolation.** Custom units live in a `UnitRegistry` instance. The module-level functions in `atica.units` use a shared default registry for convenience; pass `registry=` (or use instances) for per-company isolation.

## Precision

| Concept | Where |
|---|---|
| Calculation precision | 60 digits inside every arithmetic block (`calc_context`) |
| Result precision | results cleaned to 28 significant digits to remove noise (`clean`), e.g. `5/9` |
| Operational rounding | explicit `rounding=` / `places=` / `multiple=` arguments, per call |
| Display precision | `CalculationResult.display(places)` / `format_quantity` - never changes the stored value |

Floats are accepted but converted through `repr` (`0.1` stays `0.1`). `NaN`, infinities, booleans and absurd exponents are rejected.

## Rounding policies (`RoundingPolicy`)

| Policy | Behaviour |
|---|---|
| `none` | unchanged |
| `half_up`, `half_even` | to `places` decimals |
| `down`, `up` | floor / ceiling to `places` decimals (positive quantities: truncate / round up) |
| `ceiling_package`, `floor_package` | to a whole multiple of `multiple` (package size) |
| `preserve_remainder` | floor to whole packages; `round_with_remainder` also returns what was left over |

## Error handling

```
AticaError
 ├ UnitError: UnknownUnitError, IncompatibleUnitError, InvalidConversionError
 ├ PackagingError: InvalidHierarchyError, UnknownProductError
 ├ ManufacturingError
 ├ InventoryError
 ├ ValidationError: InvalidQuantityError
 ├ BulkProcessingError
 └ ConfigurationError
```

The GUI turns these into readable messages and logs unexpected exceptions instead of showing stack traces.

## Data models

| Spec model | Class |
|---|---|
| Unit | `atica.units.Unit` (unit_id, name, symbol, category, base_unit, factor, offset, conversion_strategy, is_custom, metadata) |
| Product | `atica.packaging.Product` |
| Packaging level | `atica.packaging.PackagingLevel` (name = level_id, contains = quantity_per_parent, parent) |
| Manufacturing material | `atica.manufacturing.Material` |
| Purchasing configuration | `atica.inventory.PurchasingConfig` |

## Security and reliability

* No `eval`/`exec`; formulas use a hand-written parser with a small whitelist (length, depth and exponent limits).
* Imports validate content: file size (50 MB) and row (100 000) limits, duplicate headers, encoding, malformed rows.
* Exports never overwrite unless `overwrite=True`, and neutralise spreadsheet formula injection (`=`, `+`, `-`, `@` prefixes).
* Failed updates (`update_unit`, `load_dict`, `AticaConfig.load`) leave the previous state untouched.
