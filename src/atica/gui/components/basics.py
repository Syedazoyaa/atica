"""Small building blocks: labels, cards, banners."""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget


def label(text: str = "", name: str = "", wrap: bool = False, parent: Optional[QWidget] = None) -> QLabel:
    widget = QLabel(text, parent)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def add_shadow(widget: QWidget, blur: int = 24, dy: int = 4, alpha: int = 22) -> None:
    """A soft, subtle drop shadow (navy-tinted)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(16, 43, 80, alpha))
    widget.setGraphicsEffect(effect)


class Card(QFrame):
    """A white rounded panel. Add content through :attr:`body`."""

    def __init__(
        self, title: str = "", subtitle: str = "", parent: Optional[QWidget] = None, shadow: bool = True
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)
        if title:
            outer.addWidget(label(title, "cardTitle"))
        if subtitle:
            outer.addWidget(label(subtitle, "muted", wrap=True))
        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        self.body.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self.body)
        if shadow:
            add_shadow(self)


class Banner(QFrame):
    """An inline message: ``kind`` is ``error``, ``warning``, ``info`` or ``success``."""

    def __init__(self, kind: str = "info", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("banner" + kind.capitalize())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)
        self._title = label("", "fieldLabel", wrap=True)
        self._title.setStyleSheet("font-weight: 600; background: transparent;")
        self._text = label("", "", wrap=True)
        self._text.setStyleSheet("background: transparent;")
        layout.addWidget(self._title)
        layout.addWidget(self._text)
        self.hide()

    def show_message(self, title: str, text: str = "") -> None:
        self._title.setText(title)
        self._title.setVisible(bool(title))
        self._text.setText(text)
        self._text.setVisible(bool(text))
        self.show()

    def message_text(self) -> str:
        return (self._title.text() + " " + self._text.text()).strip()
