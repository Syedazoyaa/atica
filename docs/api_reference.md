# API reference

Quantities may be `int`, `str`, `float` (via `repr`), `Decimal` or `Fraction`. Pass strings for exactness.
Everything returns `Decimal`.

## Result model

`CalculationResult` (frozen dataclass): `output_quantity`, `output_unit`, `input_quantity`, `input_unit`, `formula`,
`rounding_policy`, `warnings`, `metadata`. Aliases `.quantity`, `.unit`. `str(r)` is `"2500 g"`; `r.display(places)`
formats with display precision only; `r.to_dict()` is JSON friendly.

Multi-output results are dedicated dataclasses with `to_dict()`: `BreakdownResult`, `BatchResult`, `YieldResult`, `WastageResult`.

## atica.units

| Function | Notes |
|---|---|
| `convert(value, from_unit, to_unit, *, precision=None, rounding=None, registry=None)` | `UnknownUnitError`, `IncompatibleUnitError`, `InvalidQuantityError`, `InvalidConversionError` |
| `get_unit`, `list_units`, `list_categories`, `get_base_unit`, `are_compatible` | lookups |
| `register_unit`, `update_unit`, `remove_unit`, `get_custom_unit`, `list_custom_units` | custom units |
| `save_units`, `load_units` | JSON persistence of custom units |
| `UnitRegistry` | isolated registry: same methods plus `to_dict/load_dict/from_dict/save/load/copy` |
| `get_default_registry`, `reset_default_registry` | the shared registry used by module-level functions |

## atica.packaging

`Product`, `PackagingLevel`, `breakdown`, `convert_quantity`, `decompose`, `BreakdownResult` - see [packaging.md](packaging.md).

## atica.manufacturing

`calculate_material_requirement`, `calculate_producible_quantity`, `calculate_bom_requirements`, `Material`,
`calculate_batches`, `calculate_batch_material`, `calculate_production_time`, `calculate_required_input`,
`calculate_expected_output`, `calculate_scrap_quantity`, `calculate_scrap_percentage`, `calculate_yield`,
`calculate_wastage`, `Formula`, `evaluate_formula` - see [manufacturing.md](manufacturing.md).

## atica.inventory

`calculate_purchase_quantity`, `calculate_purchase_order`, `PurchasingConfig` - see [inventory.md](inventory.md).

## atica.calculations

`RoundingPolicy`, `round_value(value, policy, *, places=0, multiple=1)`, `round_with_remainder(...)`, `to_decimal`,
`format_quantity(value, places=None)`.

## atica.validation

`ValidationResult(valid, errors, warnings, to_dict(), raise_if_invalid(ExcClass))`, `validate_unit_conversion`,
`validate_custom_unit`, `validate_levels`, `validate_production_inputs`, `validate_material`, `validate_purchase_inputs`,
`check_rate`.

```python
{"valid": False, "errors": [{"code": "INCOMPATIBLE_UNITS", "field": "to_unit", "message": "..."}], "warnings": []}
```

## atica.io

`process_file(path, *, products=None, registry=None, column_map=None, on_error="collect", precision=None, rounding=None, allow_partial=False, sheet=None, max_rows=None)`,
`process_rows(rows_or_table, ...)`, `export_results(bulk, path, *, overwrite=False)`, `export_errors(...)`,
`read_csv`, `write_csv`, `read_xlsx`, `write_xlsx`, `map_columns`.

* Required columns (auto-detected, case/space-insensitive): quantity, from unit, to unit; `Product` is optional. Override with `column_map={"from_unit": "Source"}`.
* **File-level** problems (missing file/column, bad encoding, too many rows) raise `BulkProcessingError`; **row-level** problems are reported on the row (`RowResult.errors`, each `{code, field, message}`) while other rows are unaffected.
* `on_error`: `"collect"` (default), `"stop"` (halt at first bad row, `stopped_early=True`), `"raise"`.
* `BulkResult.summary`, `.successes()`, `.failures()`. Original row data is kept untouched in `RowResult.original`.
* A row is a packaging breakdown when its product has both units as levels, a physical conversion when both are physical units, and an error otherwise.

## atica (top level) and configuration

`AticaConfig` (registry, products, materials, purchasing; `save/load/to_dict/from_dict`), all exceptions, `RoundingPolicy`,
`convert`, `register_unit`, `Product`, `PackagingLevel`, `breakdown`, `calculate_material_requirement`,
`calculate_purchase_quantity`, `__version__`.

Configuration files are JSON with `type: "atica.configuration"` and `schema_version`; older versions are upgraded by `atica.config.MIGRATIONS`.
