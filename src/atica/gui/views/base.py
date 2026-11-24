"""Base class for a screen: page header plus (optionally) tabs, over the engineering-drawing backdrop."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from ..components.backdrop import BackdropWidget
from ..components.basics import label
from ..services import AppState


class ToolView(BackdropWidget):
    """A page with a title, a subtitle and a tab widget. Subclasses add tabs with :meth:`add_tab`."""

    BACKDROP = "bg_page.svg"
    ANCHOR = "tr"

    def __init__(self, title: str, subtitle: str, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.state = state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 8)
        layout.setSpacing(4)
        layout.addWidget(label(title, "pageTitle"))
        layout.addWidget(label(subtitle, "pageSubtitle", wrap=True))
        layout.addSpacing(8)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)

    def add_tab(self, name: str, widget: QWidget) -> int:
        return self.tabs.addTab(widget, name)

    def add_scrolling_tab(self, name: str, widget: QWidget) -> int:
        """Add ``widget`` inside a scroll area so that it stays reachable on short screens."""
        widget.setObjectName("content")
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidget(widget)
        return self.tabs.addTab(area, name)

    def show_tab(self, index: int) -> None:
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
