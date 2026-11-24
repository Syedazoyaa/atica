# Integrations - `atica.integrations`

Optional file helpers. Nothing in the calculation modules imports them, and **no function writes a file unless you call an export function with an explicit path**.

```python
from pathlib import Path
from atica.integrations.csv import convert_csv

Path("quantities.csv").write_text("value,from_unit,to_unit\n25,kg,g\n1,kg,m\n", encoding="utf-8")

report = convert_csv("quantities.csv", output_path="converted.csv")
print(report.succeeded, report.failed)  # 1 1
for problem in report.errors:
    print(
        problem.row_number, problem.message
    )  # 3 Cannot convert kg (mass) to m (length): they measure different things.
```

## Input format

Unit conversion files need the columns `value`, `from_unit`, `to_unit` (names can be changed with `value_column=`, `from_column=`, `to_column=`); other columns are kept. BOM files need `material_id`, `quantity_per_unit`, `unit` and optionally `wastage_percent`, `name`.

## Functions

| Function | Purpose |
|---|---|
| `csv.read_csv(path)` / `csv.write_csv(path, fieldnames, rows, *, overwrite=False)` | UTF-8 CSV (BOM accepted); returns `(fieldnames, rows, row_numbers)` |
| `csv.convert_csv(path, *, output_path=None, overwrite=False, registry=None, rounding="none", places=0, ...) -> ConversionReport` | convert every row with `atica.units.convert` |
| `csv.read_bom_csv(path, *, product_id="", allow_duplicates=False) -> Bom` | load a BOM |
| `excel.read_xlsx`, `write_xlsx`, `convert_xlsx`, `read_bom_xlsx` | the same for `.xlsx` (needs `pip install "atica[excel]"`; otherwise `MissingDependencyError` with that hint) |
| `convert_rows(rows, ...)`, `bom_from_rows(rows, ...)` | the format-independent core, for your own readers |

## Behaviour

* **Per-row problems** (bad number, unknown unit, incompatible units) are collected in `report.errors` with the source row number, the error code and the hint - they are never skipped silently. **Whole-file problems** (missing column, unreadable/oversized file, duplicate header, row with extra cells, wrong encoding) raise `IntegrationError`.
* Limits: 50 MB and 100 000 data rows per file.
* Existing files are never overwritten unless `overwrite=True`; the output folder must exist.
* Text cells that begin with `= + - @` are neutralised on export (leading apostrophe) so a spreadsheet cannot execute them as formulas; real numbers are left alone.
