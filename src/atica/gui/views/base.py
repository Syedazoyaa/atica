"""Base class for a screen: page header plus (optionally) tabs."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ..components.basics import label
from ..services import AppState


class ToolView(QWidget):
    """A page with a title, a subtitle and a tab widget. Subclasses add tabs with :meth:`add_tab`."""

    def __init__(self, title: str, subtitle: str, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.state = state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 12)
        layout.setSpacing(4)
        layout.addWidget(label(title, "pageTitle"))
        layout.addWidget(label(subtitle, "pageSubtitle", wrap=True))
        layout.addSpacing(8)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)

    def add_tab(self, name: str, widget: QWidget) -> int:
        return self.tabs.addTab(widget, name)

    def show_tab(self, index: int) -> None:
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
