# ATICA Desktop

A PySide6 front end for non-technical users. It contains **no calculation logic**: every screen calls the public ATICA API.

## Run from source

```bash
pip install atica PySide6          # or: pip install -e . PySide6 from a checkout
python app/gui/main.py
```

## Screens

Dashboard · Standard Unit Converter · Custom Unit Manager · Packaging Hierarchy Builder · Quantity Breakdown ·
Manufacturing Calculator (material, batches, custom formula) · Yield & Scrap Calculator · Purchasing & Inventory
(quick calculation and saved supplier rules) · Bulk File Import (CSV / Excel, export results and errors) · Validation & Reports.

## Saved data

*File > Save / Open* work with the versioned JSON configuration (`AticaConfig`): custom units, products and packaging
hierarchies, materials and supplier rules. The app also auto-saves to its application-data folder on exit and restores it on start.
Errors appear as readable messages with an error code; stack traces go to `~/.atica_gui.log`.

## Windows distribution

The GUI is packaged separately from the library and pins a compatible `atica` version.

```bash
pip install pyside6 atica
pyside6-deploy app/gui/main.py          # or: pip install pyinstaller && pyinstaller --noconsole --name "ATICA Desktop" ^
                                        #     --paths app/gui --add-data "app/gui/resources;resources" app/gui/main.py
```

Smoke-test the produced executable on a clean machine before publishing. An installer (for example Inno Setup) can wrap the
output folder.

## Tests

`tests/test_gui_smoke.py` drives every page headlessly (`QT_QPA_PLATFORM=offscreen`) and is skipped when PySide6 is absent.
