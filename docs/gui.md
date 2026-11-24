# Desktop application

```bash
pip install atica
atica-gui          # or: python -m atica
```

`atica-gui --version` prints the version; `atica-gui --check` starts the application, creates the main window and exits (a quick installation self-test; set `QT_QPA_PLATFORM=offscreen` on a machine without a display).

## Screens

| Screen | Core API it calls |
|---|---|
| Dashboard | - (navigation, quick tools, *your* recent calculations this session) |
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

## Data Tools files

Unit conversion files: columns `value`, `from_unit`, `to_unit`. BOM files: `material_id`, `quantity_per_unit`, `unit` (+ optional `wastage_percent`, `name`). Rows with problems are listed with the row number and reason; exports never overwrite without the save dialog's confirmation.

## Extending the application

A new calculation screen is three small pieces:

1. **Controller** (`gui/controllers/my_calc.py`, Qt-free): a function `(values: Mapping[str, Any], state: AppState) -> Outcome` that reads the form text, calls a **public** core function and formats the answer (`fmt`, `with_unit`). No arithmetic - a test fails if a controller multiplies, divides or subtracts.
2. **View** (`gui/views/my_view.py`): subclass `ToolView` and add tabs holding `CalculatorPanel(title, fields, runner, state, tool="...")`. `fields` is a list of `Field(key, label, kind, default, ...)` where `key` equals the core argument name, so a core error naming that parameter highlights the right input.
3. **Register** the view in `gui/main_window.py` (`SECTIONS` and the `views` dict).

Colours and typography live in `gui/styles/theme.py` (`Theme` tokens + `build_stylesheet`); icons are SVGs in `gui/resources/icons/` using `currentColor`, recoloured at runtime by `gui/utils/icons.py`.

Testing: set `QT_QPA_PLATFORM=offscreen`; `tests/gui/` shows controller tests (with spies proving the real core function is called) and widget tests (`CalculatorPanel.calculate()` drives a screen without clicking).
