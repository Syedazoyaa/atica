# Contributing to ATICA

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev]"
pytest
```

GUI tests need PySide6 (`pip install PySide6`) and are skipped otherwise.

## Ground rules (from the specification)

1. The core library stays independent of the GUI and uses only the standard library. Optional extras (`openpyxl`) are imported lazily.
2. No Pint or other third-party conversion engine.
3. Use `Decimal` for every calculation that matters. Never `float` arithmetic.
4. Physical conversion (`atica.units`) and packaging conversion (`atica.packaging`) stay separate. Anything needing a physical conversion calls the unit registry; do not build a second engine.
5. No silent failures: invalid input raises a documented `AticaError` subclass with a `code`.
6. Never `eval`/`exec` user input. Formulas go through `atica.manufacturing.formulas`.
7. Rounding is chosen per operation. Do not introduce a global policy.
8. Do not hardcode product packaging configurations.
9. Every public function gets a test and a docstring with an example. Every fixed calculation defect gets a regression test.

## Workflow

* Branch from `main`, open a pull request, get a review from the other developer.
* Keep public signatures stable. Document any API change in `CHANGELOG.md`.
* The GUI must call the public API and must not duplicate calculation formulas.

## Releasing

Build with `python -m build`, install the wheel in a clean virtualenv, run the README examples, publish to TestPyPI, verify, then publish to PyPI (Trusted Publishing via the `publish.yml` workflow) and tag the release.
