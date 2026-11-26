# Changelog

All notable changes to ATICA. The library and the desktop application share one version.

## 0.5.0 - 2026-11-27

First release: the calculation library **and** the desktop application in one `pip install atica`.

### Calculation library

* **Units** (`atica.units`): 17 categories with exact factors, temperature offsets and temperature differences, custom units and independent registries; incompatible conversions are rejected.
* **Packaging** (`atica.packaging`): multi-level hierarchies, full packages, remainders and minimum whole packages.
* **Materials and BOM** (`atica.materials`): bills of materials with scrap and wastage, unit conversion and capacity from stock.
* **Production** (`atica.production`): batches and batch materials, production time, capacity and quantity constraints.
* **Quality** (`atica.quality`): first-pass and final yield, scrap, rework, recovery and wastage, each with its denominator stated.
* **Purchasing** (`atica.purchasing`): stock deduction, minimum order quantities, order multiples and purchase-unit conversion.
* **Integrations** (`atica.integrations`): CSV (standard library) and Excel (optional) conversion and BOM import with source row numbers.
* **Exact arithmetic** with `Decimal` results, configurable precision, explicit rounding, and errors that name the parameter and suggest a fix.
* Standard library only; type hints (`py.typed`). Python 3.9 or newer.

### Desktop application

* Started with `atica-gui` or `python -m atica`: Dashboard, Unit Converter, Packaging, Materials and BOM, Production, Quality and Yield, Purchasing, Data Tools, Settings and About.
* Copy and export of every result (CSV, or Excel with `openpyxl`); files are never overwritten without confirmation.
* Light, flat interface that adapts to narrow and short windows and to Windows display scaling; keyboard operable.
* The Unit Converter writes time units as `dd`, `hh`, `min` and `ss`.

* Opens maximized; the window is named ATICA, with "ATICA - Manufacturing Calculations" in the footer.
* The mouse wheel scrolls the page and never changes a closed drop-down list.
* A validation message disappears when the input it is about is edited; results are cleared when anything they were calculated from changes.
* Validation messages use the labels shown on screen.
* A BOM file with problems is not imported, and every invalid row and column is reported together.

### License

GNU General Public License v3.0 (GPL-3.0-only).
