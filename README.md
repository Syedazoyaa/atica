# ATICA

Manufacturing units, packaging and quantity conversion for Python.

ATICA combines three things in one dependency-free library:

**Physical measurement intelligence** + **product-specific packaging logic** + **a manufacturing calculation engine.**

It ships as a Python library (`pip install atica`) and as a separate desktop application (`app/gui`, PySide6).

## Features

| Module | What it does |
|---|---|
| M01 Units | 16 measurement categories, own conversion engine (no Pint), temperature scales, approximate-factor warnings |
| M02 Custom units | `1 industrial_bag = 25 kg`, chained definitions, circular-definition detection, isolated registries, save/load |
| M03 Packaging | Per-product hierarchies (piece → box → carton → pallet), full validation, serialization |
| M04 Breakdown | Full packages, **remainders**, packages required, exact equivalents |
| M05 Manufacturing | Material requirements, batches, safe formula evaluator (never `eval`) |
| M06 Yield & scrap | Required input, expected output, yield, scrap %, wastage |
| M07 Purchasing | MOQ, order multiples, stock on hand, supplier rules with unit/package conversion |
| M08 Bulk | CSV (stdlib) and Excel (optional) with row-level errors and safe export |
| M09 Validation | Structured `{valid, errors[{code, field, message}], warnings}` results |
| M10 Rounding | Eight policies, chosen **per operation** - never one global rule |

All arithmetic uses `Decimal`. The core needs only the standard library.

## Install

```bash
pip install atica              # core library, no dependencies
pip install "atica[excel]"     # + .xlsx support (openpyxl)
```

Supports Python 3.9+.

## Quick start

```python
from atica.units import convert, register_unit

print(convert("2.5", "kg", "g"))             # 2500 g
print(convert(212, "F", "C"))                # 100 celsius
register_unit("industrial_bag", "mass", "kg", "25")
print(convert(4, "industrial_bag", "kg"))    # 100 kg
```

```python
from atica.packaging import Product, PackagingLevel, breakdown

product = Product("PROD-001", "Product A")
product.add_level(PackagingLevel("piece", contains=1))
product.add_level(PackagingLevel("box", contains=12, parent="piece"))      # 1 box = 12 pieces
product.add_level(PackagingLevel("carton", contains=20, parent="box"))     # 1 carton = 20 boxes
product.add_level(PackagingLevel("pallet", contains=40, parent="carton"))  # 1 pallet = 40 cartons

result = breakdown(product, "850", "carton", "pallet")
result.to_dict()
# {'full_packages': 21, 'remaining_quantity': 10, 'packages_required': 22,
#  'total_quantity': 850, 'exact_equivalent': Decimal('21.25')}
```

```python
from atica.manufacturing import calculate_material_requirement
from atica.inventory import calculate_purchase_quantity

print(calculate_material_requirement(material_per_unit="0.5", production_quantity=1000, material_unit="kg"))  # 500 kg
print(calculate_material_requirement(target_output=1000, scrap_rate="0.05", rounding="up"))                    # 1053
print(calculate_purchase_quantity(required_quantity=87, order_multiple=12, minimum_order_quantity=24))         # 96 pieces
```

```python
from atica.io import process_file, export_results, export_errors

bulk = process_file("orders.csv", products=[product])      # columns: Product, Quantity, From Unit, To Unit
print(bulk.summary)                                         # {'total_rows': 3, 'succeeded': 3, 'failed': 0, ...}
export_results(bulk, "results.csv")
export_errors(bulk, "errors.csv")
```

## Conventions worth knowing

* **Packaging direction.** `PackagingLevel("box", contains=12, parent="piece")` means *one box contains 12 pieces*; `parent` names the smaller level that `contains` counts. The base level has no parent and contains 1.
* **Rates are fractions.** `scrap_rate="0.05"` is 5 %. Every function that takes a rate also accepts a `*_percent` form.
* **Nothing is silently rounded.** Remainders are reported; rounding is requested explicitly per call (`rounding=`, `places=`, `multiple=`).
* **Unit identifiers are case-sensitive** so `mW` and `MW` can never be confused. Aliases such as `lb`, `ft`, `C`, `F` are built in.
* **Errors** derive from `AticaError`; each has a `.code` and `.message`.

## Desktop app

```bash
pip install atica PySide6
python app/gui/main.py
```

See [docs/desktop_app.md](docs/desktop_app.md), including Windows packaging.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Documentation lives in [docs/](docs/): [getting started](docs/getting_started.md), [architecture](docs/architecture.md),
[units](docs/units.md), [packaging](docs/packaging.md), [manufacturing](docs/manufacturing.md),
[inventory](docs/inventory.md), [API reference](docs/api_reference.md).

## Contributing & license

See [CONTRIBUTING.md](CONTRIBUTING.md). Released under the [MIT License](LICENSE).
