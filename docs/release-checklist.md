# Release checklist

Never publish without explicit sign-off.

## Before building

- [ ] The version is set only in `src/atica/version.py`; `CHANGELOG.md` has a dated entry for it.
- [ ] `INITIAL_RELEASE` and `UPDATED_ON` in `src/atica/gui/branding.py` are correct.
- [ ] The `[project.urls]` in `pyproject.toml` open for a signed-out visitor (the repository must be public, with issues enabled).
- [ ] The PyPI and TestPyPI project name `atica` is free or already owned by you.
- [ ] `python docs/_generate_api.py` (Python 3.12) leaves `docs/api-reference.md` unchanged.
- [ ] `ruff check src tests examples docs`, `ruff format --check src tests examples`, `mypy`
- [ ] `pytest --cov=atica` passes; the CI matrix (Windows and Linux, Python 3.9-3.13) is green.

## Build and inspect

- [ ] Delete `dist/`, then `python -m build` and `python -m twine check --strict dist/*`.
- [ ] The wheel holds the fonts with their licence file, SVG icons and backgrounds, PNG logos, `py.typed` and the three licence files, and no tests or caches.
- [ ] In a fresh virtual environment outside the repository, install the wheel (and separately the sdist), then run `python -c "import atica; print(atica.__version__)"`, `atica-gui --version`, `atica-gui --check` and `python -m atica --version`.

## TestPyPI first, then PyPI

The workflow `.github/workflows/publish.yml` uses PyPI *Trusted Publishing* (no stored token). One-time setup:

1. On TestPyPI and on PyPI add a (pending) trusted publisher: owner and repository of this project, workflow `publish.yml`, environment `testpypi` or `pypi`.
2. In the GitHub repository create the environments `testpypi` and `pypi`; give `pypi` a required reviewer.

Release:

1. Tag the release commit `vX.Y.Z` and publish a GitHub Release for the tag. This runs CI and uploads to **TestPyPI only**.
2. Verify the TestPyPI upload in a fresh environment (`--extra-index-url` lets PySide6 come from PyPI):
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ atica==X.Y.Z`
3. Publish to PyPI deliberately: Actions -> Publish -> *Run workflow*, select the **tag** `vX.Y.Z` (not a branch) and target `pypi`, then approve the `pypi` environment.

## After

- [ ] `pip install atica` works in a clean environment; `atica-gui --check` passes (set `QT_QPA_PLATFORM=offscreen` on headless Linux).
