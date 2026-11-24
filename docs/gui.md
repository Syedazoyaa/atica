# Desktop application

```bash
pip install atica
atica-gui          # or: python -m atica
```

`atica-gui --version` prints the version; `atica-gui --check` starts the application, creates the main window and exits (a quick installation self-test; set `QT_QPA_PLATFORM=offscreen` on a machine without a display).

## Screens

| Screen | Core API it calls |
|---|---|
| Dashboard | - (direct access to the modules, quick calculations, *your* recent calculations this session; no invented figures) |
| Unit Converter | `atica.units.convert`, `UnitRegistry.register_unit` (custom units tab) |
| Packaging Calculations | `atica.packaging.Product`, `breakdown`, `decompose` |
| Materials and BOM | `atica.materials.calculate_bom_requirements`, `calculate_producible_quantity` |
| Production Calculations | `calculate_batches`, `calculate_batch_materials`, `production_time`, `production_capacity`, `calculate_batch_capacity`, `constrain_production_quantity` |
| Quality and Yield | `calculate_required_input`, `calculate_expected_output`, `calculate_scrap_quantity`, `calculate_scrap_percentage`, `calculate_yield`, `calculate_rework`, `calculate_wastage`, `calculate_material_recovery` |
| Purchasing Calculations | `atica.purchasing.calculate_purchase_quantity` |
| Data Tools | `atica.integrations` - convert a CSV/Excel file, import a BOM, export converted/problem rows |
| Settings | display decimals (display only) and calculation precision (`use_precision`) |
| About | version, environment, a Python snippet |

Each calculator shows labelled inputs with tooltips, sensible defaults and a **Calculate** button (Enter also works), a result card with the headline answer, details, tables, warnings, the formula and assumptions, and **Copy result** / **Export...** (CSV, or Excel when `openpyxl` is installed). **Reset** restores the defaults. The BOM and the packaging hierarchy are entered once and shared between screens. Custom units you define appear in every unit list for the session.

Errors appear as a red message under the form with the problem and how to fix it, and the offending field is highlighted. Unexpected problems show "Something went wrong" and are logged to `atica-gui.log` in the per-user application-data folder; tracebacks are never shown. Nothing is persisted except the two settings (stored with Qt's `QSettings`); recent activity is in memory only and is never invented.

## Design system

A light, flat, engineering-drawing look: square-edged panels with hairline borders, underlined input fields, a charcoal primary action, and a very faint technical backdrop (grid, construction circles, gears, registration marks).

* **Palette.** Five identity colours, preserved exactly: light grey `#E3E4E7` (controls, sidebar, table headers), cool grey `#C9CCD2` (borders and dividers), soft off-white `#F3F0F2` (application background), muted warm beige `#D9C7C0` (selection) and grey mauve `#B8B5B9` (secondary surfaces and the drawings). Near-black `#23262B` is used for text and primary actions so that text keeps WCAG AA contrast; white is used only for cards and focused inputs; red/amber/green appear only in error, warning and success messages. Everything lives in `gui/styles/theme.py` (`Theme`).
* **Typeface.** IBM Plex Sans (Regular 400, Medium 500, SemiBold 600) is bundled in `gui/resources/fonts/` and registered with Qt at start-up, so it works on any machine; if the files cannot be loaded the interface falls back to a system sans-serif font and logs a warning. Headings are SemiBold, section titles and labels Medium, body Regular; results request tabular figures where Qt supports it. Licence: SIL OFL 1.1, see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
* **Logo.** The ATICA symbol (a squared "A") and the wordmark, which is the word ATICA in IBM Plex Sans SemiBold converted to vector outlines (`logo*.svg`; light variants for dark backgrounds). Regenerate all brand SVGs with `python docs/_make_brand_assets.py`.
* **Backdrops.** `resources/backgrounds/bg_dashboard.svg`, `bg_page.svg`, `bg_nav.svg`, painted *behind* the interface only (cards, inputs and tables are opaque), at three levels of subtlety. A test checks that the darkest pixel any drawing can put behind text still gives >= 4.5:1 contrast.

## Window sizes and display scaling

The minimum window is 760 x 480 logical pixels and the initial size is taken from the screen. Below 1020 px of width the sidebar collapses to icons (titles in tooltips); below 880 px a calculator's inputs and result become one scrolling column instead of two side-by-side panes. This is what a 1366 x 768 laptop at 150 % Windows scaling (about 911 x 512 logical pixels) needs. Tests resize the window to 1920x1080, 1600x900, 1366x768, 1093x614 and 911x512 and also run the whole application under `QT_SCALE_FACTOR` 1, 1.25 and 1.5.

Keyboard: Ctrl+1...Ctrl+0 switch sections; every control is reachable with Tab and shows a visible focus outline; dashboard tiles open with Enter or Space.

## Data Tools files

Unit conversion files: columns `value`, `from_unit`, `to_unit`. BOM files: `material_id`, `quantity_per_unit`, `unit` (+ optional `wastage_percent`, `name`). Rows with problems are listed with the row number and reason; exports never overwrite without the save dialog's confirmation.

## Extending the application

A new calculation screen is three small pieces:

1. **Controller** (`gui/controllers/my_calc.py`, Qt-free): a function `(values: Mapping[str, Any], state: AppState) -> Outcome` that reads the form text, calls a **public** core function and formats the answer (`fmt`, `with_unit`). No arithmetic - a test fails if a controller multiplies, divides or subtracts.
2. **View** (`gui/views/my_view.py`): subclass `ToolView` and add tabs holding `CalculatorPanel(title, fields, runner, state, tool="...")`. `fields` is a list of `Field(key, label, kind, default, ...)` where `key` equals the core argument name, so a core error naming that parameter highlights the right input.
3. **Register** the view in `gui/main_window.py` (`SECTIONS` and the `views` dict).

Colours and typography live in `gui/styles/theme.py` (`Theme` tokens + `build_stylesheet`) - views contain no colour or font literals (a test enforces this); icons are SVGs in `gui/resources/icons/` using `currentColor`, recoloured at runtime from theme tokens by `gui/utils/icons.py`; fonts are loaded by `gui/utils/fonts.py`; backdrops are drawn by `gui/components/backdrop.py`.

Testing: set `QT_QPA_PLATFORM=offscreen`; `tests/gui/` shows controller tests (with spies proving the real core function is called) and widget tests (`CalculatorPanel.calculate()` drives a screen without clicking).
