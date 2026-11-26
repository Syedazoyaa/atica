# Third-party notices

ATICA is released under the GNU General Public License v3.0 (see `LICENSE`).

## Bundled files with their own licence

The interface font files in `atica/gui/resources/fonts/` are distributed under their own licence. Its text, which must
stay with the files, is `atica/gui/resources/fonts/OFL.txt` (in this repository:
`src/atica/gui/resources/fonts/OFL.txt`).

## Brand assets

The ATICA symbol and the background drawings are original artwork released with ATICA under the GNU General Public
License v3.0. The ATICA and Falcon Informatics logos in `gui/resources/branding/` are trademarks/brand assets of their
owners (Falcon Informatics) and are not licensed for reuse as branding of other products.

## PySide6 / Qt for Python (runtime dependency)

The desktop application uses PySide6 (Qt for Python), installed from PyPI as a normal dependency. PySide6 is available
under the LGPLv3 / GPLv3 / commercial licences of The Qt Company; see <https://doc.qt.io/qtforpython-6/> for details.
The Python package does not redistribute Qt: `pip` installs it separately. The separately distributed Windows installer
**does** include Python, Qt, PySide6 and openpyxl; it carries its own notices in its `licenses` folder.

## openpyxl (optional dependency)

Excel import/export (`pip install "atica[excel]"`) uses openpyxl (MIT licence), installed separately by `pip`.
