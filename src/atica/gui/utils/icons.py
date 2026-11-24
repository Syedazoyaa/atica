"""Icon loading: SVG files from ``resources/icons`` recoloured at runtime (so themes can recolour them)."""

from __future__ import annotations

import os
from functools import cache
from typing import Dict

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
ICON_DIR = os.path.join(RESOURCES, "icons")


@cache
def _svg_text(name: str) -> str:
    path = os.path.join(ICON_DIR, name + ".svg")
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def pixmap(name: str, color: str = "#192B40", size: int = 22) -> QPixmap:
    """Render icon ``name`` in ``color`` at ``size`` logical pixels (crisp on high-DPI screens)."""
    data = _svg_text(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(ratio)
    return pm


_CACHE: Dict[tuple, QIcon] = {}


def icon(name: str, color: str = "#192B40", size: int = 22) -> QIcon:
    key = (name, color, size)
    if key not in _CACHE:
        _CACHE[key] = QIcon(pixmap(name, color, size))
    return _CACHE[key]


def logo_pixmap(size: int = 40) -> QPixmap:
    renderer = QSvgRenderer(os.path.join(ICON_DIR, "logo.svg"))
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(ratio)
    return pm
