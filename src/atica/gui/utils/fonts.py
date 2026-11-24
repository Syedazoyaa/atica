"""IBM Plex Sans, bundled with ATICA (SIL Open Font License 1.1 - see ``resources/fonts/OFL.txt``).

The font files ship inside the package, so the typeface does not depend on anything installed on the
user's machine.  :func:`register_fonts` registers them with Qt; it must run after the ``QApplication``
exists and before the stylesheet is applied.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List

from PySide6.QtGui import QFont, QFontDatabase

from ..styles.theme import FONT_FAMILY, RESOURCES

LOG = logging.getLogger("atica.gui")

FONT_DIR = os.path.join(RESOURCES, "fonts")
#: Regular (400), Medium (500) and SemiBold (600) - the three weights the interface uses.
FONT_FILES = ("IBMPlexSans-Regular.ttf", "IBMPlexSans-Medium.ttf", "IBMPlexSans-SemiBold.ttf")

_loaded: List[int] = []


def register_fonts() -> bool:
    """Register the bundled files with Qt. Returns True when the family is available afterwards.

    A failure is logged and is not fatal: the stylesheet falls back to a system sans-serif font.
    """
    if _loaded and FONT_FAMILY in QFontDatabase.families():
        return True
    ok = True
    for name in FONT_FILES:
        font_id = QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, name))
        if font_id < 0:
            LOG.warning("Could not load the bundled font file %s; a system font will be used.", name)
            ok = False
        else:
            _loaded.append(font_id)
    available = FONT_FAMILY in QFontDatabase.families()
    if not available:
        LOG.warning("%s is not available after registration; a system font will be used.", FONT_FAMILY)
    return ok and available


def fonts_available() -> bool:
    """True when IBM Plex Sans is registered with Qt."""
    return FONT_FAMILY in QFontDatabase.families()


def apply_application_font(app: Any) -> None:
    """Make IBM Plex Sans the application default (widgets without a stylesheet rule included)."""
    font = QFont(FONT_FAMILY)
    font.setPixelSize(13)
    app.setFont(font)


def tabular(widget: Any) -> None:
    """Ask for tabular (fixed-width) figures so columns of numbers line up, where Qt supports it."""
    font = widget.font()
    try:
        font.setFeature(QFont.Tag("tnum"), 1)  # Qt >= 6.7; harmless to skip on older versions
    except (AttributeError, TypeError):
        return
    widget.setFont(font)
