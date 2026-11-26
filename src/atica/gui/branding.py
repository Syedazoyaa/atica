"""Product and company metadata plus brand-image loading - the single place to change either.

To replace a logo, overwrite the PNG in ``resources/branding`` (same file name); nothing else needs
editing.  Images keep their aspect ratio and transparency and are rendered at ``RATIO`` x the logical
size so they stay sharp on high-DPI screens.
"""

from __future__ import annotations

import os
from functools import cache
from typing import Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPixmap

from atica.version import __version__

from .styles.theme import FALCON_BLUE, FALCON_GOLD, RESOURCES

BRANDING_DIR = os.path.join(RESOURCES, "branding")
ATICA_LOGO = "atica_logo.png"
FALCON_LOGO = "falcon_informatics_logo.png"
RATIO = 3

# ------------------------------------------------------------------ product metadata
PRODUCT_NAME = "ATICA"
PRODUCT_DESCRIPTION = (
    "An integrated toolkit for smarter manufacturing, precision calculations, and industrial workflows."
)
VERSION = __version__
INITIAL_RELEASE = "27 November 2026"
UPDATED_ON = "27 November 2026"
LICENSE_NAME = "GNU General Public License v3.0 (GPL-3.0)"
AUTHORS = (
    "Zabiullah Khan",
    "Syeda Zoya",
    "Juveria Talha",
    "Insiya Maryam",
    "RajuKumar Allam",
    "Sasi Kumar A",
)

# ------------------------------------------------------------------ company metadata
COMPANY_NAME = "Falcon Informatics"
COMPANY_WEBSITE = "https://falconinformatics.com/"
COMPANY_LINKEDIN = "https://www.linkedin.com/company/falconinformatics"
COMPANY_EMAILS = ("info@falconinformatics.com", "cs@falconinformatics.com")
#: The two complementary brand colours of the name "Falcon" + "Informatics" (taken from the logo).
FALCON_COLOR = FALCON_BLUE
INFORMATICS_COLOR = FALCON_GOLD
COPYRIGHT_RIGHTS = " All rights reserved."


def logo_path(name: str) -> str:
    return os.path.join(BRANDING_DIR, name)


@cache
def _trimmed(name: str) -> QImage:
    """The image with fully transparent margins removed (the ATICA artwork has large ones)."""
    image = QImage(logo_path(name))
    if image.isNull() or not image.hasAlphaChannel():
        return image
    w, h = image.width(), image.height()
    left, top, right, bottom = w, h, -1, -1
    step = max(1, min(w, h) // 400)
    for y in range(0, h, step):
        for x in range(0, w, step):
            if image.pixelColor(x, y).alpha() > 8:
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)
    if right < 0:
        return image
    pad = step
    rect = QRect(left, top, right - left + 1, bottom - top + 1).adjusted(-pad, -pad, pad, pad)
    return image.copy(rect.intersected(image.rect()))


def has_logo(name: str) -> bool:
    return os.path.isfile(logo_path(name)) and not QImage(logo_path(name)).isNull()


def logo_size(name: str, height: int) -> Tuple[int, int]:
    """Logical ``(width, height)`` of the trimmed logo scaled to ``height``."""
    image = _trimmed(name)
    if image.isNull() or image.height() == 0:
        return height, height
    return max(1, round(height * image.width() / image.height())), height


@cache
def brand_pixmap(name: str, height: int) -> QPixmap:
    """The logo scaled (smoothly, aspect preserved) to ``height`` logical pixels, DPR-aware."""
    image = _trimmed(name)
    if image.isNull():
        return QPixmap()
    scaled = image.scaledToHeight(height * RATIO, Qt.TransformationMode.SmoothTransformation)
    pixmap = QPixmap.fromImage(scaled)
    pixmap.setDevicePixelRatio(RATIO)
    return pixmap
