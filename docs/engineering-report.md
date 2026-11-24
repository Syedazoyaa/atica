# Engineering report - ATICA 1.0.0

Honest account of the rebuild of ATICA 0.8.0 into one product: calculation library + desktop application in a single distribution. "Verified" means checked on the build machine (Windows 10, Python 3.12, PySide6 6.12) while producing this report; everything else is called out as unverified.

## 1. What was wrong with 0.8.0

| Area | Finding |
|---|---|
| Tests | **None.** No `tests/` directory; CI only ran `python -m build`. |
| Scope | Library mixed with config persistence (`AticaConfig`), supplier objects (`PurchasingConfig`), a validation-result framework, a general expression evaluator and a bulk CSV engine. The GUI lived outside the package (`app/gui`, `sys.path` hacks, its own state handling) and was installed through a `[gui]` extra. |
| Bugs reproduced | duplicate BOM ids silently overwrote each other (data loss); `convert("1e299","kg","g")` leaked a raw `decimal.InvalidOperation`; 100 % scrap rejected even for expected output/scrap quantity; zero BOM consumption accepted; results forced to 28 digits for no stated reason. |
| Design | global mutable default registry; mutable `Product` (add/update/remove) re-validated on every call; `PackagingLevel.parent` actually named the *smaller* level; rates were fractions in some functions and `*_percent` in others; yield had no concept of recovery, so first-pass vs final yield and double counting were not distinguishable; approximate (`exact: false`) factors for psi/hp/lb-ft. |
| Numerics | ceilings/floors taken on an already-rounded Decimal division (can cross a package boundary on repeating decimals). |

## 2. What was corrected / added

* **Exact arithmetic**: `Fraction` inside, one `Decimal` conversion at the end, floor/ceil on the exact value; precision (50 digits default) configurable per context. All unit factors exact by definition.
* **Core**: exception hierarchy with `parameter` + `hint`; consistent validation; rounding split into mathematical vs package constraints; specialised frozen result types with `to_dict`/`explain`.
* **Units**: exact factors, temperature offsets, temperature *differences*, custom units/categories, independent registries, read-only default registry.
* **Packaging**: immutable validated products; breakdown with full / remainder / minimum whole packages / surplus; multi-level plan.
* **Materials/BOM**: explicit scrap/wastage denominators, breakdown of allowances, duplicate policy, unit conversion, capacity from stock with limiting material and no silent defaults.
* **Production**: partial batches, batch materials, constraints, time and capacity with stated assumptions.
* **Quality**: scrap, first-pass vs final yield, rework projection, recovery, wastage - a denominator for every percentage, no double counting.
* **Purchasing**: stock deduction, MOQ, multiples, purchase-unit conversion, surplus.
* **Desktop application** (`atica.gui`): 10 screens, brand palette, light theme with swappable tokens, copy/export, CSV/Excel Data Tools, friendly errors with log file, settings, About; `atica-gui`, `python -m atica`, `--version`, `--check`.
* **Packaging/CI/docs**: one `pyproject.toml` (hatchling), one version file, wheel + sdist, CI matrix, TestPyPI-first publish workflow, docs and examples executed by tests.

## 3. What was removed, and why

| Removed | Reason |
|---|---|
| `app/gui` standalone app | rebuilt inside the package on the public API |
| `AticaConfig`, `PurchasingConfig` | persistence / supplier management: out of scope; JSON round-trip of products, BOMs and custom units remains (`to_dict`/`from_dict`) |
| `atica.validation` (ValidationResult) | replaced by `atica.core.validation` raising specific errors |
| `manufacturing.formulas` (expression evaluator) | not tied to any of the six domains; removing it removes the only "dynamic" surface. (It used a hand-written parser, not `eval`, and was sound - it can be restored as an optional module if needed.) |
| Packaging-aware bulk processor | replaced by `atica.integrations` (unit conversion + BOM files); the old one needed product definitions inside spreadsheets |
| `[gui]`, old `[dev]` extras | GUI is default; `[excel]` and a real `[dev]` remain |

## 4. Old -> new mapping

`calculations/*` -> `core/precision.py`, `core/rounding.py` (rewritten) - `results.py` -> `core/results.py` + per-domain results - `exceptions.py` -> `core/exceptions.py` - `units/*` -> `units/*` (model kept, now exact; custom units folded into the registry) - `packaging/*` -> `packaging/*` (redesigned, immutable) - `manufacturing/materials.py` -> `materials/` - `manufacturing/batches.py` -> `production/` - `manufacturing/yield_scrap.py` -> `quality/` - `inventory/purchasing.py` -> `purchasing/` - `io/*` -> `integrations/*` - `validation/*` -> `core/validation.py` - `app/gui/*` -> `gui/*`.

## 5. Formulas independently verified

All formulas in [formulas.md](formulas.md). "Independently" means expected values are hand-calculated or published constants, or computed with a separate `Fraction` oracle - not by re-using the implementation. Highlights: every unit factor class (length, mass, area, volume, time, pressure, force, energy, power, speed, torque, count) against NIST/SI values; temperature scales including `-40 C = -40 F`, `-459.67 F = 0 K`, differences; the 250-piece/carton example and 850-carton/21.25-pallet case; scrap/wastage worked examples (`90 good, 10 % scrap, 2 kg, 20 % wastage -> 250 kg = 180 + 20 + 50`); yield conservation (`945 good + 55 scrap = 1000`); batches (`1 / 0.1 = 10` exactly); MOQ/multiple cases including `0.3 / 0.1`. Property tests (Hypothesis) cover round trips, linearity, conservation and inverse relations.

## 6. Test results (verified)

| | |
|---|---|
| Total | **668 passed, 0 failed** (Windows, Python 3.12, PySide6 6.12), coverage **94 %** (branch) |
| By area | core 104, units 142, packaging 62, materials 52, production 55, quality 57, purchasing 31, integration 94 (CSV/Excel, import hygiene, docs/examples), gui 71 |
| Against the **installed wheel** | 663/663 (the one deselected test regenerates the API docs from the source tree) |
| Core (everything except `tests/gui`) on other Pythons | 3.9: 595 passed, 2 skipped; 3.10: 597 passed; 3.11 and 3.13: 596 passed, 1 skipped (skips are by design: two version-specific checks - stdlib-module introspection needs 3.10+, API-reference regeneration is pinned to 3.12) |
| Static | `ruff check` and `ruff format --check` clean; `mypy --strict` clean on the 32 non-GUI modules (target 3.10, the oldest mypy still accepts) |
| Distributions | `python -m build` -> exactly one wheel (129 KB) and one sdist (159 KB); `twine check` passed for both |
| Clean install | wheel in a fresh venv: `import atica`, calculations, `atica.__file__` in site-packages, GUI window built from installed resources, `atica-gui --version`, `atica-gui --check` (offscreen **and** the real Windows display), `python -m atica`, all six examples; `pip check` clean. Same for the sdist (`--check`). |
| GUI <-> core | spies prove each controller calls the real public function; AST tests prove controllers/services contain no arithmetic, the GUI uses no private core module, the core never imports the GUI or Qt |

## 7. Performance and complexity (measured)

`convert` 26 us, temperature convert 54 us, `breakdown` 44 us, `calculate_batches` 45 us, `calculate_yield` 77 us, `Product` construction 30 us (validated once), 1000-line BOM 68 ms (linear, ~68 us/line). `import atica` ~0.2 s and loads no Qt. GUI: main window builds in ~1.5 s, cold start to window ~2.3 s. Complexity is O(1) in quantities and O(n) in BOM lines / packaging levels / CSV rows; no repeated validation, no per-call registry rebuilds.

## 8. Dependency analysis

* Runtime: `PySide6>=6.5,<7` only (normal dependency, as required). The calculation core imports **only the standard library** (enforced by a test). No NumPy/Pandas/SciPy/Pint/SQLAlchemy/database - confirmed absent from the installed environment.
* Optional: `openpyxl` (`[excel]`), lazily imported, with a clear error if missing.
* Dev: pytest, pytest-cov, hypothesis, ruff, mypy, build, twine, openpyxl.
* Note: installing `PySide6` pulls the full meta-package (Essentials + Addons + WebEngine + Pdf; several hundred MB). The GUI needs only QtCore/Gui/Widgets/Svg, which `PySide6-Essentials` provides. The spec said "PySide6", so that is what is declared; switching is a one-line change if install size matters.

## 9. Security review

No `eval`/`exec`/`pickle`/`subprocess`/`socket`/network in the package (test-enforced). No filesystem writes except explicit export functions (never overwrite unless asked; formula-injection neutralised; size/row caps on input). No global mutable state: default registry read-only, precision in a `ContextVar`. GUI never shows tracebacks; unexpected errors are logged to `atica-gui.log` under the per-user app-data folder (Qt-provided, nothing hard-coded). The only broad `except Exception` sites are the GUI error boundary (`guard`, startup handler), which convert to a message and log.

## 10. Known limitations and unverified areas

* **GUI platform coverage**: verified on Windows 10 / Python 3.12 / PySide6 6.12 only. macOS, Linux, Python 3.9-3.11/3.13 for the GUI, and older PySide6 versions (>=6.5) are covered by the CI matrix but **have not been run**. CI itself has not been run (no repository was available).
* **Human UI review**: layout and visuals were reviewed from rendered screenshots and driven programmatically; no one has used it with a mouse for a working session, no accessibility (screen reader, high-DPI scaling) or localisation review. The offscreen test platform has no fonts, so screenshots used the Windows font folder.
* **Dark theme**: not implemented (structure only: tokens in `Theme`).
* **Units**: fixed catalogue; no compound expressions (`kg/m3`), no density/volume<->mass conversion (needs physical information), no month/year; "gallon" is the US gallon.
* **Packaging**: one linear chain per product, whole-number counts.
* **BOM**: single level (no sub-assemblies); the scrap/wastage conventions are explicit but are *one* convention - plants using "% of net" must convert (documented).
* **Precision**: results that cannot be exact (1/3) are rounded to 50 digits by default; inputs beyond ~1e300 are rejected.
* **Excel**: `.xlsx` only, values written as text; tested with `openpyxl` 3.1.
* **Packaging metadata**: no project URLs/author contact (no repository URL was provided); the `publish.yml` workflow is untested.
* **Floats**: accepted for convenience (converted through `repr`), so a float already carries binary error from its origin; use strings/Decimals for exact input.
* **Not done by design**: standalone Windows installer; publishing to PyPI/TestPyPI (never done without explicit authorisation).

## 11. Is it ready for PyPI?

**Technically yes, for a first release candidate; organisationally not yet.** The artifacts build, validate, install cleanly from the wheel and the sdist, and work from site-packages on Windows/Python 3.12. Before uploading: run the CI matrix (especially GUI on Linux/macOS and Python 3.9/3.13), add the real project URLs/author, decide the final version and date the changelog, optionally switch to `PySide6-Essentials`, upload to **TestPyPI** first and repeat the clean install from there ([release-checklist.md](release-checklist.md)). Nothing was uploaded anywhere.
