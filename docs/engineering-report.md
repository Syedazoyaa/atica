# Engineering report - ATICA 1.0.0

Honest account of two stages: the rebuild of ATICA 0.8.0 into one product (calculation library + desktop application in one distribution), and the release-hardening / GUI-redesign pass that followed. "Verified" means checked on the build machine (Windows 10, PySide6 6.12) while producing this report; everything else is called out as unverified.

## 1. What was wrong with 0.8.0

| Area | Finding |
|---|---|
| Tests | **None.** No `tests/` directory; CI only ran `python -m build`. |
| Scope | Library mixed with config persistence (`AticaConfig`), supplier objects (`PurchasingConfig`), a validation-result framework, a general expression evaluator and a bulk CSV engine. The GUI lived outside the package (`app/gui`, `sys.path` hacks, its own state handling) and was installed through a `[gui]` extra. |
| Bugs reproduced | duplicate BOM ids silently overwrote each other (data loss); `convert("1e299","kg","g")` leaked a raw `decimal.InvalidOperation`; 100 % scrap rejected even for expected output/scrap quantity; zero BOM consumption accepted; results forced to 28 digits for no stated reason. |
| Design | global mutable default registry; mutable `Product` re-validated on every call; `PackagingLevel.parent` actually named the *smaller* level; rates were fractions in some functions and `*_percent` in others; yield had no concept of recovery; approximate (`exact: false`) factors for psi/hp/lb-ft. |
| Numerics | ceilings/floors taken on an already-rounded Decimal division. |

## 2. Stage 1 - the rebuild (summary)

Exact `Fraction` arithmetic with one `Decimal` conversion (configurable precision, default 50 digits); exception hierarchy with `parameter` + `hint`; consistent validation and rounding (mathematical vs package); immutable `Product`/`Bom`; units with exact factors, offsets and custom registries; packaging, materials/BOM, production, quality, purchasing modules; optional CSV/Excel integrations; the PySide6 desktop application (`atica.gui`) over the public API; one `pyproject.toml`, one version, CI, docs, examples. Removed: the standalone `app/gui`, `AticaConfig`, `PurchasingConfig`, `atica.validation`, the formula evaluator and the packaging-aware bulk processor (reasons in the CHANGELOG).

## 3. Stage 2 - release hardening and redesign

### 3.1 Defects found and fixed (each has a regression test; the ones marked ★ were confirmed to **fail on the previous commit's code**)

| # | Defect | Fix |
|---|---|---|
| 1 ★ | A `Fraction` passed directly skipped the documented magnitude limits that `int`/`float`/`Decimal`/`str` obey (`10**400` accepted; then `convert` produced absurd values). | `check_fraction_magnitude`, an exact comparison against `1e-300 <= |x| < 1e301`, applied to `Fraction` input, in `to_decimal`, and to `'a/b'` strings. |
| 2 ★ | `register_base_unit` accepted duplicate aliases, an alias equal to the unit name, and a bare string alias (split into letters). | shared `_validate_aliases` for both registration paths; nothing is registered on failure. |
| 3 ★ | `calculate_batch_materials` (and merged duplicate BOM lines) summed *rounded* 50-digit Decimals, so totals differed from a single run for repeating decimals. | exact `Parts` fractions are carried alongside the Decimal result; batches and merges sum fractions and round once. Unrounded `exact_total` now equals the whole-quantity result **exactly**. |
| 4 ★ | `required_input_with_rework` divided by a rounded yield percentage: at 6 digits, `1 / (1/7)` returned `7.00001`. | uses the validated exact fractions (shared `_rework_rates` with `calculate_rework`). |
| 5 | Excel reader silently discarded populated cells beyond the header width or under a blank header (CSV could do the same under a blank header). | raises `IntegrationError` naming row and column, for both formats. |
| 6 | `ConversionReport` had no source row numbers; the GUI table numbered rows 1..n. | `row_numbers` retained for converted rows; errors already carried theirs; the GUI shows real CSV lines / worksheet rows; BOM import errors quote the source row. |
| 7 | `.xlsm` appeared in save dialogs although macro-preserving export does not exist. | export filters offer CSV and `.xlsx` only; `.xlsm` remains readable. The default extension follows the chosen filter. |
| 8 | Optional BOM material names were dropped on GUI import. | 5-column BOM editor and import; names survive CSV/Excel -> editor -> calculation. |
| 9 | openpyxl's `IllegalCharacterError` (not a `ValueError`) escaped as a raw exception; invalid sheet names raised openpyxl errors. | both become actionable `IntegrationError`s; sheet names are validated up front (1-31 chars, no `[]:*?/\`). |
| 10 | README/docs claimed every function returns a result object. | wording corrected (five helpers return plain `Decimal`). |
| 11 | GUI: the "More options" control used a heavy native arrow; the first navigation button showed a keyboard-focus ring at start-up; placeholder text (4.27:1) and the sidebar drawing (4.27:1) failed WCAG AA. | themed chevrons; initial focus placed on the window; darker placeholder/secondary ink and softer drawings (now >= 4.5:1, tested). |

Not changed on purpose: all other formulas; the exact-arithmetic design; public signatures (other than additions: `ConversionReport.row_numbers`, `check_fraction_magnitude`).

### 3.2 GUI redesign

* **Identity**: the five supplied colours preserved exactly (`#E3E4E7`, `#C9CCD2`, `#F3F0F2`, `#D9C7C0`, `#B8B5B9`); near-black ink for text and the primary action, white only for cards/focused inputs, semantic colours only in messages. Flat, square-edged, hairline borders, underlined inputs, no gradients or shadows (tests enforce this).
* **Typography**: IBM Plex Sans Regular/Medium/SemiBold bundled (SIL OFL 1.1), registered with Qt at start-up; a test asserts that *every* label, button, input, tab bar, table and text box in the running window resolves to IBM Plex Sans, and that headings are SemiBold (600), section titles/labels Medium (500), body Regular (400). No other font family is named anywhere in the code.
* **Brand**: the squared-"A" symbol kept, recoloured to the palette; wordmark = "ATICA" in IBM Plex Sans SemiBold as vector outlines (dark and light variants), used in the sidebar and About.
* **Dashboard**: the "Welcome to ATICA" banner and its container were deleted (not hidden); the page is module shortcuts, quick calculations and real session activity only.
* **Backdrops**: three SVG engineering drawings (grid, construction circles, meshing gears, registration marks) painted behind opaque cards; a test proves the darkest pixel they can put behind text still gives >= 4.5:1.
* **Responsive**: screen-aware initial size, 760x480 minimum, icon-only sidebar < 1020 px, single scrolling column for calculators < 880 px.
* **Accessibility**: visible focus styles for every control type, keyboard-operable tiles, accessible names and tooltips, all text pairs >= WCAG AA (contrast ratios are computed in the tests).

## 4. Test and verification results (all executed; nothing assumed)

| Check | Result |
|---|---|
| Full suite, source tree (Windows, Python 3.12, PySide6 6.12) | **822 passed, 0 failed**; branch coverage **95 %** (4 229 statements, 864 branches) |
| Full suite against the **installed wheel**, Python 3.12 (fresh venv, repo not on the path) | 822 passed |
| Full suite against the installed wheel, Python **3.13** | 821 passed, 1 skipped (the API-reference regeneration test is pinned to 3.12 by design) |
| Non-GUI suite, source tree, Python 3.9 / 3.10 / 3.11 / 3.13 | 689 passed + 2 skipped / 690 + 1 skipped / 690 + 1 skipped / 690 + 1 skipped |
| `ruff check` / `ruff format --check` (src, tests, examples, docs) | clean (121 files) |
| `mypy --strict` | clean on the 32 non-GUI modules (the GUI package is excluded from type-checking) |
| Doctests, 6 example scripts, every README/docs code block | all executed by the suite and passing |
| Regression tests vs previous commit's code | the ★ items above fail there and pass now |
| Layout at 1920x1080, 1600x900, 1366x768, 1093x614, 911x512 (logical) | no clipped control, no horizontal scrollbar, correct sidebar/column mode; a negative-control test proves the checker detects clipping |
| Real Qt display scaling `QT_SCALE_FACTOR` 1, 1.25, 1.5 on a 1366x768 screen | whole application checked in subprocesses, all OK |
| `python -m build`, `twine check` | one wheel (435 KB), one sdist (483 KB), both PASSED |
| Wheel contents | 3 TTFs + `OFL.txt`, 4 logos, 3 backdrops, 20 icons, `py.typed`, notices in `dist-info/licenses`; no tests/docs/caches |
| Clean-venv install of the wheel (Windows, 3.12) | `pip check` clean; `import atica`; `atica-gui --version`; `atica-gui --check` offscreen **and on the real display**; `python -m atica`; fonts load from site-packages; all SVGs valid; all 10 screens open; only IBM Plex Sans in use; no "Welcome"; core imports load no Qt |

Screenshots (captured from the real Windows display platform, bundled fonts) are in `docs/screenshots/` (excluded from the sdist).

## 5. Performance and complexity (measured earlier, unchanged)

`convert` 26 us, temperature convert 54 us, `breakdown` 44 us, `calculate_batches` 45 us, 1000-line BOM 68 ms (linear). `import atica` loads no Qt. GUI cold start to window ~2.3 s. Backdrops are rendered once per size and cached.

## 6. Dependency analysis

* Runtime: `PySide6>=6.5,<7` only. The core imports only the standard library (test-enforced). No NumPy/Pandas/SciPy/Pint/SQLAlchemy/database.
* Optional: `openpyxl` (`[excel]`).
* Bundled (not a dependency): IBM Plex Sans, OFL 1.1 - 624 KB of TTFs.
* `pip install atica` pulls the full PySide6 meta-package (Essentials + Addons + WebEngine + Pdf; several hundred MB). The GUI needs only Essentials; the spec said "PySide6", so that is declared.

## 7. Security review

No `eval`/`exec`/`pickle`/`subprocess`/`socket` in the package (test-enforced). Files are written only by explicit export calls (never overwriting unless asked; formula-injection neutralised; size/row limits on input; hidden/unmapped data refused). Fonts and backdrops are read-only package resources; no network access. The GUI shows no tracebacks; unexpected errors are logged to the per-user application-data folder.

## 8. Known limitations and unverified areas

* **GUI platform coverage**: verified on Windows 10 with Python 3.12 and 3.13 and PySide6 6.12 (3.9: see the release checklist for its status). macOS, Linux, older PySide6 (6.5-6.11) and high-DPI *physical* monitors are covered by the CI matrix but **have not been run**. CI itself has not been run.
* **Human review**: the interface was reviewed from screenshots and driven programmatically (including keyboard focus order, tab navigation and every calculator); no one has used it with a mouse for a working session, and no screen-reader pass was done (accessible names and contrast are in place and tested, but assistive-technology behaviour is untested).
* **Display scaling** was emulated with Qt's `QT_SCALE_FACTOR` on the offscreen platform and spot-checked on the real platform; fractional Windows scaling on a real second monitor was not tested.
* **GUI type checking**: mypy covers the core only; the GUI is covered by tests, ruff and review.
* **Fonts**: tabular figures are requested where Qt supports it (Qt >= 6.7); on older Qt the proportional default figures are used (columns of numbers are right-aligned either way).
* **Dark theme**: not implemented (tokens only).
* **Units / packaging / BOM / precision**: as before - fixed unit catalogue, single linear packaging chain, single-level BOM, 50-digit default precision.
* **Excel**: `.xlsx` only for writing; values are written as text; formulas in input cells are read as their cached values (a never-calculated formula reads as empty).
* **Packaging metadata**: no project URLs/author contact; `publish.yml` untested; nothing was published.

## 9. Is it ready for PyPI?

**Technically yes as a release candidate; a human sign-off is still required.** The artifacts build, validate, install cleanly from the wheel and the sdist, and behave identically from site-packages. Before uploading: run the CI matrix (Linux/macOS GUI, Python 3.9-3.11), have someone use the application for a working session, add the real project URLs/author, confirm the version and date the changelog, decide whether to depend on `PySide6-Essentials`, and upload to **TestPyPI** first ([release-checklist.md](release-checklist.md)). Nothing was uploaded anywhere.
