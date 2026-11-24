# Changelog

All notable changes to ATICA. The library and the desktop application share one version.

## 1.0.0 - unreleased

First release as a single product: the calculation library **and** the desktop application in one `pip install atica`. This is a rebuild of 0.8.0; the numbers it produces for valid inputs match 0.8.0 except where 0.8.0 was wrong (see *Corrected*).

### Added

* **Desktop application** inside the package (`atica.gui`, command `atica-gui`, `python -m atica`): ten screens, brand design, copy/export, CSV/Excel Data Tools, settings, About. PySide6 is a normal dependency.
* `atica.production`: `calculate_batch_materials`, `constrain_production_quantity`, `production_capacity`, `calculate_batch_capacity` (time handling and assumptions explicit); `production_time` replaces `calculate_production_time`.
* `atica.materials`: immutable `Bom`/`BomItem` with explicit duplicate handling, `calculate_producible_quantity` (capacity from stock, limiting material), exact scrap/wastage breakdown.
* `atica.quality`: first-pass vs final yield, rework projection, material recovery, net/gross wastage - each with its denominator.
* Units: `interval=True` for temperature differences, Rankine, `count` category (piece, pair, dozen, gross), `rpm`, `ms`, `week`, `kgf`, `qt`, `km2`, `in2`, `um`, `MJ`, `kcal`, `ft/s`; `register_base_unit` for new categories; `UnitRegistry.factor()`.
* Core: `use_precision`, `round_to_multiple`, `split_by_multiple`, `Result.explain()/to_dict(numbers=...)`, exception hierarchy with `parameter` and `hint`.
* Test suite (600+ tests, Hypothesis property tests, GUI and GUI-core integration tests), CI, type hints (`py.typed`), generated API reference.

### Changed (breaking - the main API shifts are listed here)

* **Percentages** are always on the 0-100 scale and named `*_percent` (`scrap_percent=5`). 0.8.0 mixed fractions (`scrap_rate=0.05`) and `*_percent`.
* **Exact arithmetic**: results are exact rationals converted to `Decimal` once (precision 50 digits, configurable) instead of being cleaned to 28 digits.
* `Product` is **immutable** and validated on construction: `Product(id, name, levels=[...])`; `PackagingLevel(name, contains, of)` replaces `contains`/`parent` (the old `parent` actually named the *smaller* level). `add_level`/`update_level`/`remove_level` are replaced by `with_level`/`without_top_level`.
* `breakdown(...)` keyword `allow_partial` -> `require_whole` (fractional quantities are now accepted by default); results gained `remainder_unit`, `packaged_quantity`, `surplus`.
* The module-level unit registry is **read-only**. Create `UnitRegistry()` for custom units: `register_unit(name, factor, reference_unit)` (the redundant `category` argument is gone). `register_unit`, `update_unit`, `remove_unit`, `save_units`, `load_units` module functions were removed; use the registry methods and `to_dict()/from_dict()`.
* `convert(...)`: `precision=` -> `places=`; `rounding` + `places` must be given together (a bare `precision` no longer implies half-up).
* Unit symbols are canonical short forms (`kg`, `g`, `L`, `lb`, `C`, `F`); the long names remain accepted aliases. Results report the canonical symbol.
* `atica.inventory` -> `atica.purchasing` (`calculate_purchase_quantity` now takes keyword options and a `purchase_unit`); `atica.manufacturing` split into `materials`, `production`, `quality`.
* Exceptions: `field` -> `parameter`, new `hint`; `AticaError` subclasses reorganised (see `docs/core.md`).
* Python >= 3.9 (unchanged).

### Release-hardening pass (before the first public release)

Corrected:

* **Numeric limits** - a `Fraction` passed directly bypassed the documented magnitude limits (about 1e-300 .. 1e301) that apply to `int`, `float`, `Decimal` and `str` input; it is now checked the same way (exactly, before any conversion), including `'a/b'` ratio strings.
* **`UnitRegistry.register_base_unit`** accepted duplicate aliases, an alias equal to the unit's own name, and a bare string as `aliases` (split into characters); all are now rejected like `register_unit`, with no half-registered state.
* **`calculate_batch_materials`** and merged duplicate BOM lines summed *rounded* Decimals (50 significant digits), so repeating decimals were not exact; they now sum the exact fractions and round once (`exact_total` equals a single whole-quantity run exactly).
* **`required_input_with_rework`** divided by an already-rounded yield percentage; at reduced precision `1 / (1/7)` came out as `7.00001`. It now uses the exact fractions (shared validation with `calculate_rework`).
* **Excel**: populated cells beyond the header width (or under a blank header) were silently dropped; they now raise an `IntegrationError` naming the row and column. The same check applies to CSV. Invalid worksheet names and control characters in exported text now raise clear `IntegrationError`s instead of openpyxl errors.
* **Source row numbers**: `ConversionReport` gained `row_numbers` (the file position of every converted row); the Data Tools table now shows real CSV line / Excel row numbers for converted *and* failed rows, and BOM import errors quote the true source row.
* **`.xlsm`** is readable but is no longer offered (or accepted) as an export format; save dialogs offer CSV and `.xlsx` only, and a missing extension follows the chosen filter.
* **BOM names**: the optional material name now survives import (CSV/Excel -> GUI editor -> calculation); the editor has a "Name (optional)" column.
* README/docs no longer claim every function returns a result object (a few return plain `Decimal`).

Desktop application redesign:

* New visual identity: the five-colour palette (`#E3E4E7`, `#C9CCD2`, `#F3F0F2`, `#D9C7C0`, `#B8B5B9`) with near-black text, flat square-edged panels, underlined inputs, charcoal primary action, no gradients or shadows; all tokens centralised in `gui/styles/theme.py`, no colour or font literals elsewhere.
* **IBM Plex Sans** (Regular, Medium, SemiBold) bundled and registered with Qt; SIL OFL 1.1 licence and `THIRD_PARTY_NOTICES.md` shipped in the wheel and sdist.
* The ATICA wordmark is IBM Plex Sans SemiBold converted to vector outlines (light and dark variants); the symbol is kept (squared "A") and recoloured to the palette.
* Subtle engineering-drawing SVG backdrops (grid, construction circles, meshing gears, registration marks) at three intensities, painted behind opaque cards only.
* The dashboard's "Welcome to ATICA" banner and its container were removed; the dashboard is now module shortcuts, quick calculations and real session activity.
* Responsive: screen-aware initial size, minimum 760 x 480, icon-only sidebar below 1020 px, single scrolling column for calculators below 880 px; verified at 1920x1080, 1600x900, 1366x768 and at Qt scale factors 1, 1.25 and 1.5.
* Accessibility: visible focus outlines for every control, keyboard-operable dashboard tiles, WCAG AA text contrast (tested).

### Corrected (original rebuild)

* Duplicate BOM material ids silently overwrote each other; now rejected (or explicitly merged).
* A 100 % scrap rate was rejected even for expected output and scrap quantity; now valid there (and an explicit error where it makes a calculation impossible).
* `convert("1e299", ...)` could leak a raw `decimal.InvalidOperation`; extreme values are now handled or reported as `NumericRangeError`.
* Zero BOM consumption was accepted; now rejected.
* Approximate "exact: false" factors (psi, hp, lb-ft) are now exact derivations.
* Floor/ceiling decisions no longer depend on a rounded Decimal division.
* The old `rework_quantity` yield model had no recovery concept; yield now separates first-pass from final yield and cannot double-count reworked units.
* Global mutable default registry, mutable products, per-call re-validation of the whole hierarchy removed.

### Removed

* The standalone `app/gui` application (rebuilt as `atica.gui` inside the package, using the public API; the old one duplicated state handling and depended on `AticaConfig`).
* `AticaConfig` (save/load of everything), `PurchasingConfig` (supplier objects), `atica.validation` (ValidationResult framework) and `atica.manufacturing.formulas` (a general expression evaluator not tied to any calculation domain) - out of scope for a calculation library; their safe parsing/validation duties are covered by `atica.core`.
* The packaging-aware bulk CSV/Excel processor; replaced by `atica.integrations` (unit conversion and BOM files).
* `[gui]` and `[dev]` extras of 0.8.0 (the GUI is now part of the default install; development tools are in `[dev]`, Excel in `[excel]`).
