# Architecture

One distribution (`atica`), one `pyproject.toml`, one version (`src/atica/version.py`), two components.

```text
Developer application ──┐
                        ▼
                  ATICA core API  ◀──── atica.gui (PySide6 desktop app)
```

The core never imports the GUI; the GUI is a presentation layer that calls the **same public functions** a developer would. A test (`test_core_never_imports_gui`) and a second test (`test_no_arithmetic_in_controllers_and_services`) enforce both rules.

## Package layout

```text
src/atica/
  __init__.py        convenient top-level exports; imports no Qt
  version.py         the single version source
  __main__.py        `python -m atica` -> GUI
  core/              exceptions, precision, rounding, validation, results
  units/             definitions (exact factors), registry, convert()
  packaging/         hierarchy (PackagingLevel, Product), breakdown
  materials/         material (BomItem, Bom, single material), bom (BOM + capacity)
  production/        batches, time (time & capacity), capacity (batch capacity)
  quality/           scrap, yields, wastage
  purchasing/        calculations
  integrations/      csv, excel (optional), shared row handling
  gui/
    app.py           main(): QApplication, logging, error hook, --check/--version
    main_window.py   sidebar + stacked screens
    models/          Field, Outcome, ResultTable (Qt-free)
    services/        AppState (session), formatting, parsing, settings storage
    controllers/     one module per domain: form text -> core API -> Outcome   (Qt-free, no maths)
    components/      cards, banners, FormPanel, TableEditor, ResultPanel, Sidebar, CalculatorPanel
    views/           the ten screens
    styles/          design tokens (Theme) + stylesheet generator
    resources/       branding/ (ATICA and Falcon Informatics PNG logos), icons/ (SVG icons + fallback logos), backgrounds/ (SVG drawings), fonts/ (IBM Plex Sans + OFL licence)
    utils/           icon/logo loader, font registration, error translation and logging
tests/               core/ units/ packaging/ materials/ production/ quality/ purchasing/ integration/ gui/
```

## Design decisions

* **Exact arithmetic.** Fractions inside, `Decimal` out, one rounding at the end (see [core.md](core.md)).
* **Immutability.** `Product`, `Bom`, `BomItem`, `PackagingLevel` and all results are frozen; "changing" a product returns a new one. Calculations cannot mutate inputs.
* **No shared mutable state.** The module-level `convert` uses a read-only default registry; custom units live in registries you own. Precision is a `ContextVar`.
* **Fail loudly.** Invalid input raises a specific error with parameter and hint; nothing returns `0`, `None` or a guess.
* **No dynamic execution, no network, no implicit files.** Tests assert the package contains no `eval`/`exec`/`pickle`/`subprocess`/`socket` and that the core imports only the standard library. Files are touched only by the explicit integration functions.
* **Thread safety.** Results, products, BOMs and unit definitions are immutable, and precision is context-local, so calculations can run in parallel. The only mutable object, `UnitRegistry`, serialises *writes* (registering/removing units) with a lock; reads are not locked, so finish registering custom units before sharing a registry across threads (or give each thread its own `registry.copy()`). The shared default registry is read-only.
* **Lazy Qt.** `import atica` and `import atica.gui` (models, services, controllers) never import PySide6; `atica.gui.app.main` imports it on demand and turns a broken Qt install into a readable message.
* **Theming.** All colours are tokens in `gui/styles/theme.py::Theme` and all text uses the bundled IBM Plex Sans; a dark theme is another `Theme` instance (the stylesheet, icons and backdrops are generated from the tokens).
* **Responsive layout.** The main window picks its size from the screen; the sidebar collapses to icons and calculators fold into one scrolling column on narrow windows, so nothing depends on fixed pixel sizes.

## Complexity

Unit/packaging/BOM/production/quality/purchasing calls are O(1) in the quantity and O(n) in the number of BOM lines/levels (`Product` validates and indexes its chain once, on construction; lookups are O(1)). `convert` does a dictionary lookup and a handful of rational operations. `Bom` merging of duplicate lines is O(n). CSV conversion is a single pass, O(rows), reading the file once with a row and size cap.
