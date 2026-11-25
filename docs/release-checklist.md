# PyPI release-readiness checklist

Never publish without explicit sign-off. Items marked **(verified)** were checked on the development machine while building 1.0.0; the others need a person or a CI run.

## Before building

- [ ] Choose the final version in `src/atica/version.py` (the only place; the wheel, `atica.__version__`, the GUI and `atica-gui --version` all read it) and date the `CHANGELOG.md` entry.
- [ ] Add a `[project.urls]` table (Homepage, Source, Changelog, Issues) with the real repository URLs and set the real author/maintainer - none are declared yet because no repository URL was provided.
- [ ] Set the real initial release date in `src/atica/gui/branding.py` (`INITIAL_RELEASE`, currently a placeholder) and update `UPDATED_ON`.
- [ ] Licence: `LICENSE` is the unmodified GPL-3.0 text and `pyproject.toml` says `GPL-3.0-only`; the wheel's `dist-info/licenses` carries `LICENSE`.
- [ ] Confirm the PyPI project name `atica` is available / owned.
- [ ] `python docs/_generate_api.py` (regenerates `docs/api-reference.md`) and, if the brand or backdrop drawings changed, `python docs/_make_brand_assets.py`.
- [ ] Font licensing: `THIRD_PARTY_NOTICES.md` and `src/atica/gui/resources/fonts/OFL.txt` are present and the wheel's `dist-info/licenses` contains both **(verified)**.
- [ ] `ruff check src tests && ruff format --check src tests && mypy` **(verified)**
- [ ] `pytest --cov=atica` on every supported Python (CI matrix 3.9-3.13); GUI tests run with `QT_QPA_PLATFORM=offscreen`. Core tests on 3.9, 3.10, 3.11, 3.12, 3.13 **(verified locally)**

## Build and inspect

- [ ] `python -m build` -> exactly one wheel and one sdist **(verified)**
- [ ] `twine check dist/*` **(verified)**
- [ ] Wheel contains `atica/py.typed`, the SVG icons/logos/backgrounds, the three IBM Plex Sans TTFs and `OFL.txt`, and no `tests/`, `docs/` or scratch files; sdist contains sources, tests, docs (without screenshots), examples and the notices **(verified)**
- [ ] `METADATA` shows `Requires-Dist: PySide6>=6.5,<7` as a normal dependency and `Provides-Extra: excel, dev`; `[project.scripts] atica-gui` **(verified)**
- [ ] Fresh virtual environment: `pip install dist/atica-*.whl`, then `import atica`, a real calculation, `atica-gui --version`, `atica-gui --check` (offscreen and on a real display) - run from a directory that is *not* the repository; confirm the About screen shows "IBM Plex Sans" and all ten screens open **(verified for Windows / Python 3.12)**
- [ ] Same install test from the sdist (`pip install dist/atica-*.tar.gz`)

## TestPyPI

```bash
python -m twine upload --repository testpypi dist/*          # needs your TestPyPI token
python -m venv /tmp/t && /tmp/t/bin/pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ atica
/tmp/t/bin/python -c "import atica; print(atica.__version__)" && /tmp/t/bin/atica-gui --version
```

(`--extra-index-url` lets PySide6 resolve from real PyPI.) The included GitHub workflow `publish.yml` uses PyPI *Trusted Publishing* (no stored token): configure the publisher on TestPyPI/PyPI, then publish a GitHub Release. It targets TestPyPI by default; switching it to PyPI is a deliberate one-line change.

## After

- [ ] Tag `v1.0.0`, create the GitHub Release (triggers publish), verify `pip install atica` in a clean environment on Windows, macOS and Linux (the GUI needs a display; use `atica-gui --check` with `QT_QPA_PLATFORM=offscreen` on headless Linux).
