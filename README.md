# ATICA

**Manufacturing calculations for Python - and a desktop app on top of them.**

ATICA is one Python package (`atica`) with two parts that share one version:

| Part | What it is | How you use it |
|---|---|---|
| **Calculation library** | Exact, validated manufacturing maths: units, packaging, bills of materials, production, yield & scrap, purchasing. Standard library only. | `from atica.units import convert` |
| **Desktop application** | A polished PySide6 interface over the *same* public API, for people who prefer a window to a script. | `atica-gui` |

```bash
pip install atica
```

That one command installs both. Nothing else is needed to import the library or to launch the app.

## What problem does it solve?

Manufacturing code is full of small calculations that are easy to get *almost* right: `250 pieces` is `1 carton + 10 pieces` but needs `2 cartons` to ship; a 5 % scrap rate means you must *start* `1000 / 0.95` units, not `1000 x 1.05`; `212 F` is not `212 x 5/9 C`. ATICA does these once, exactly (`Decimal` results, exact rational arithmetic inside), with explicit rounding, explicit denominators for every percentage, and errors that say what to fix.

## What ATICA is *not*

Not an ERP, inventory, warehouse, MES, supplier-management or scheduling system; not a database or a GUI framework. It calculates. You keep the data.

## Requirements

* Python **3.9 - 3.13** (the calculation core is tested on all of them).
* `PySide6` is installed automatically (the desktop app is part of the product). The library itself imports nothing outside the standard library and never loads Qt - `import atica` is fast and headless-safe.
* Optional: `pip install "atica[excel]"` for `.xlsx` import/export.

## Method A - use the library

```python
from atica.units import convert

result = convert(25, "kg", "g")
print(result)            # 25000 g
print(result.value)      # Decimal('25000')
```

```python
from atica.packaging import Product, PackagingLevel, breakdown

product = Product("P001", "Product A", levels=[
    PackagingLevel("piece"),
    PackagingLevel("box", 12, "piece"),      # 1 box    = 12 pieces
    PackagingLevel("carton", 20, "box"),     # 1 carton = 20 boxes
])

r = breakdown(product, 250, "piece", "carton")
print(r)                                   # 250 piece = 1 full carton + 10 piece remaining (2 carton required)
print(r.full_packages, r.remainder, r.packages_required)   # 1 10 2
```

```python
from atica.materials import Bom, BomItem, calculate_bom_requirements

bom = Bom([
    BomItem("steel", "0.25", "kg"),
    BomItem("paint", "40", "mL", wastage_percent=10),
])
result = calculate_bom_requirements(bom=bom, production_quantity=1000, scrap_percent=5)
print(result["steel"])                     # 263.1578947368 kg
```

```python
from atica.quality import calculate_required_input

print(calculate_required_input(950, scrap_percent=5))   # 1000
```

Most calculations return a small immutable result object with the answer, the unit, the unrounded value and the formula (`.to_dict()`, `.explain()`). A few single-number helpers return a plain `Decimal` instead: `convert_quantity`, `packages_required`, `required_input_with_rework`, `round_value`, `round_to_multiple`. Bad input always raises a specific `AticaError` subclass; nothing returns a made-up value.

## Method B - use the desktop app

```bash
pip install atica
atica-gui
```

(`python -m atica` does the same.) Ten sections: Dashboard, Unit Converter, Packaging, Materials and BOM, Production, Quality and Yield, Purchasing, Data Tools, Settings, About. A light, flat, engineering-style interface that adapts to laptop screens and Windows display scaling. Every screen calls the public functions listed in this README - the GUI contains no formulas of its own. See [docs/gui.md](https://github.com/Syedazoyaa/atica/blob/main/docs/gui.md).

## Calculation domains

| Module | Import | Highlights |
|---|---|---|
| Units | `atica.units` | 17 categories, exact factors, temperature offsets, custom units & registries, incompatible conversions rejected |
| Packaging | `atica.packaging` | multi-level hierarchies, full packages, remainders, minimum whole packages, immutable products |
| Materials / BOM | `atica.materials` | multi-material BOMs, scrap & wastage allowances, unit conversion, capacity from stock |
| Production | `atica.production` | batches (full vs required), batch materials, time, capacity, quantity constraints |
| Quality | `atica.quality` | first-pass vs final yield, scrap, rework, recovery, wastage - denominators stated |
| Purchasing | `atica.purchasing` | stock deduction, MOQ, order multiples, purchase-unit conversion, surplus |
| Integrations | `atica.integrations` | CSV (stdlib) and Excel (optional) conversion and BOM import |

## Conventions worth knowing

* **Percentages are on the 0-100 scale** and named `*_percent`: `scrap_percent=5` means 5 %. Each result states its denominator.
* **Numbers are `Decimal`.** Inside, arithmetic is exact (`fractions.Fraction`); rounding to `precision` digits (default 50, configurable with `atica.use_precision`) happens once, at the end.
* **Rounding is explicit.** Default is none; choose `rounding="half_up" | "half_even" | "floor" | "ceiling"` and `places=`. Package rounding (`round_to_multiple`, `split_by_multiple`) is separate from mathematical rounding.
* **Unit names are case-sensitive** and never guessed: `"Kg"` is an error with a suggestion, not a silent `kg`.

## Documentation

* [Getting started](https://github.com/Syedazoyaa/atica/blob/main/docs/getting-started.md) - [Units](https://github.com/Syedazoyaa/atica/blob/main/docs/units.md) - [Packaging](https://github.com/Syedazoyaa/atica/blob/main/docs/packaging.md) - [Materials & BOM](https://github.com/Syedazoyaa/atica/blob/main/docs/materials.md) - [Production](https://github.com/Syedazoyaa/atica/blob/main/docs/production.md) - [Quality](https://github.com/Syedazoyaa/atica/blob/main/docs/quality.md) - [Purchasing](https://github.com/Syedazoyaa/atica/blob/main/docs/purchasing.md) - [Integrations](https://github.com/Syedazoyaa/atica/blob/main/docs/integrations.md)
* [Core: precision, rounding, results, errors](https://github.com/Syedazoyaa/atica/blob/main/docs/core.md) - [Architecture](https://github.com/Syedazoyaa/atica/blob/main/docs/architecture.md) - [Desktop app](https://github.com/Syedazoyaa/atica/blob/main/docs/gui.md)
* [API reference](https://github.com/Syedazoyaa/atica/blob/main/docs/api-reference.md) (generated from the source) - [Formulas](https://github.com/Syedazoyaa/atica/blob/main/docs/formulas.md) - [Changelog](https://github.com/Syedazoyaa/atica/blob/main/CHANGELOG.md) - [Release checklist](https://github.com/Syedazoyaa/atica/blob/main/docs/release-checklist.md)

## License

ATICA is free software licensed under the **GNU General Public License v3.0** (GPL-3.0) - see [LICENSE](https://github.com/Syedazoyaa/atica/blob/main/LICENSE). Notices for third-party material are in [THIRD_PARTY_NOTICES.md](https://github.com/Syedazoyaa/atica/blob/main/THIRD_PARTY_NOTICES.md).
