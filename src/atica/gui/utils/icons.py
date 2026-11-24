"""Icon and logo loading: SVG files from ``resources/icons``, recoloured at runtime from theme tokens."""

from __future__ import annotations

import os
from functools import cache
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ..styles.theme import CURRENT, RESOURCES

ICON_DIR = os.path.join(RESOURCES, "icons")
#: Pixmaps are rendered at this multiple of their logical size so they stay crisp at 150-200 % scaling.
RATIO = 3


@cache
def _svg_text(name: str) -> str:
    path = os.path.join(ICON_DIR, name + ".svg")
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _render(renderer: QSvgRenderer, width: int, height: int) -> QPixmap:
    pm = QPixmap(width * RATIO, height * RATIO)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(RATIO)
    return pm


def pixmap(name: str, color: Optional[str] = None, size: int = 22) -> QPixmap:
    """Render icon ``name`` (a stroke icon using ``currentColor``) in ``color`` at ``size`` logical pixels."""
    data = _svg_text(name).replace("currentColor", color or CURRENT.ink)
    return _render(QSvgRenderer(QByteArray(data.encode("utf-8"))), size, size)


_CACHE: Dict[Tuple[str, str, int], QIcon] = {}


def icon(name: str, color: Optional[str] = None, size: int = 22) -> QIcon:
    key = (name, color or CURRENT.ink, size)
    if key not in _CACHE:
        _CACHE[key] = QIcon(pixmap(name, color, size))
    return _CACHE[key]


def logo_pixmap(size: int = 40, light: bool = False) -> QPixmap:
    """The ATICA symbol (square). ``light=True`` is the variant for dark backgrounds."""
    name = "logo_light.svg" if light else "logo.svg"
    return _render(QSvgRenderer(os.path.join(ICON_DIR, name)), size, size)


def wordmark_pixmap(height: int = 28, light: bool = False) -> QPixmap:
    """Symbol + the word ATICA (IBM Plex Sans SemiBold outlines) at ``height`` logical pixels."""
    name = "logo_wordmark_light.svg" if light else "logo_wordmark.svg"
    renderer = QSvgRenderer(os.path.join(ICON_DIR, name))
    view = renderer.viewBoxF()
    width = max(1, round(height * view.width() / view.height()))
    return _render(renderer, width, height)
