"""Subtle engineering-drawing backdrops (grid, construction circles, gears, registration marks).

The drawings are lightweight SVG files in ``resources/backgrounds``.  They are painted *behind* the
interface only: cards, inputs and tables are opaque, so the drawing can never sit under text a user
has to read.  Rendering is cached per size and device-pixel ratio.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from ..styles.theme import CURRENT, RESOURCES

BACKGROUND_DIR = os.path.join(RESOURCES, "backgrounds")

_renderers: Dict[str, QSvgRenderer] = {}
_pixmaps: Dict[Tuple[str, int, int, float, str], QPixmap] = {}


def _renderer(name: str) -> QSvgRenderer:
    if name not in _renderers:
        _renderers[name] = QSvgRenderer(os.path.join(BACKGROUND_DIR, name))
    return _renderers[name]


def render_backdrop(name: str, width: int, height: int, ratio: float, anchor: str) -> QPixmap:
    """The drawing ``name`` scaled to *cover* ``width`` x ``height``, aligned to ``anchor`` (cached).

    ``anchor`` is two letters: vertical (``t``/``b``/``m``) then horizontal (``l``/``r``/``c``), e.g. ``"br"``.
    """
    key = (name, width, height, ratio, anchor)
    cached = _pixmaps.get(key)
    if cached is not None:
        return cached
    pixmap = QPixmap(max(1, int(width * ratio)), max(1, int(height * ratio)))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = _renderer(name)
    view = renderer.viewBoxF()
    if renderer.isValid() and view.width() > 0 and view.height() > 0:
        scale = max(width / view.width(), height / view.height())
        w, h = view.width() * scale, view.height() * scale
        x = {"l": 0.0, "c": (width - w) / 2, "r": width - w}[anchor[1]]
        y = {"t": 0.0, "m": (height - h) / 2, "b": height - h}[anchor[0]]
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(x, y, w, h))
        painter.end()
    if len(_pixmaps) > 24:
        _pixmaps.clear()
    _pixmaps[key] = pixmap
    return pixmap


def draw_backdrop(
    widget: QWidget, painter: QPainter, name: str, anchor: str, fill: Optional[str] = None
) -> None:
    """Fill ``widget`` with the background colour and draw the drawing ``name`` over it."""
    painter.fillRect(widget.rect(), QColor(fill or CURRENT.background))
    if widget.width() > 0 and widget.height() > 0:
        ratio = widget.devicePixelRatioF()
        painter.drawPixmap(0, 0, render_backdrop(name, widget.width(), widget.height(), ratio, anchor))


class BackdropWidget(QWidget):
    """A plain widget whose background is the ATICA colour plus an engineering-drawing backdrop."""

    BACKDROP = "bg_page.svg"
    ANCHOR = "tr"

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        draw_backdrop(self, painter, self.BACKDROP, self.ANCHOR)
        painter.end()
