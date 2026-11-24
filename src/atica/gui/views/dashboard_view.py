"""Dashboard: branding, welcome, module cards, quick tools and the session's recent activity."""

from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from atica.version import __version__

from ..components import Card, add_shadow, label
from ..services import AppState
from ..utils.icons import logo_pixmap, pixmap

# (section key, title, one-line description, icon)
Module = Tuple[str, str, str, str]


class ModuleCard(QFrame):
    """A clickable tile that opens a section."""

    clicked = Signal()

    def __init__(self, title: str, text: str, icon_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(92)
        add_shadow(self, blur=18, dy=3, alpha=16)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)
        badge = QLabel()
        badge.setObjectName("iconBadge")
        badge.setPixmap(pixmap(icon_name, "#2464A8", 26))
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column = QVBoxLayout()
        column.setSpacing(3)
        column.addWidget(label(title, "moduleTitle"))
        column.addWidget(label(text, "moduleText", wrap=True))
        column.addStretch(1)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(column, 1)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DashboardView(QWidget):
    """``navigate(section_key, tab_index)`` is called when a tile or quick tool is chosen."""

    def __init__(
        self,
        state: AppState,
        modules: Sequence[Module],
        quick_tools: Sequence[Tuple[str, str, int]],
        navigate: Callable[[str, int], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.state = state
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        content = QWidget()
        content.setObjectName("content")
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("hero")
        add_shadow(hero, blur=30, dy=8, alpha=40)
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(26, 22, 26, 22)
        hl.setSpacing(18)
        mark = QLabel()
        mark.setPixmap(logo_pixmap(64))
        mark.setFixedSize(64, 64)
        text = QVBoxLayout()
        text.setSpacing(4)
        text.addWidget(label("Welcome to ATICA", "heroTitle"))
        text.addWidget(
            label(
                "Accurate, reproducible manufacturing calculations: units, packaging, materials, production, yield and purchasing. "
                "Pick a tool below, or use a quick tool to get started.",
                "heroText",
                wrap=True,
            )
        )
        version = label("Version " + __version__, "heroText")
        hl.addWidget(mark)
        hl.addLayout(text, 1)
        hl.addWidget(version, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(hero)

        lay.addWidget(label("CALCULATION MODULES", "sectionLabel"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        for i, (key, title, desc, icon_name) in enumerate(modules):
            tile = ModuleCard(title, desc, icon_name)
            tile.clicked.connect(lambda k=key: navigate(k, 0))
            grid.addWidget(tile, i // 2, i % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        lay.addWidget(label("QUICK TOOLS", "sectionLabel"))
        quick = QHBoxLayout()
        quick.setSpacing(10)
        for text_, key, tab in quick_tools:
            button = QPushButton(text_)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, k=key, t=tab: navigate(k, t))
            quick.addWidget(button)
        quick.addStretch(1)
        lay.addLayout(quick)

        lay.addWidget(label("RECENT ACTIVITY (THIS SESSION)", "sectionLabel"))
        self._activity_card = Card(shadow=True)
        self._activity_rows = QVBoxLayout()
        self._activity_rows.setSpacing(6)
        self._activity_card.body.addLayout(self._activity_rows)
        lay.addWidget(self._activity_card)
        lay.addStretch(1)
        state.on_change(self.refresh_activity)
        self.refresh_activity()

    def refresh_activity(self) -> None:
        while self._activity_rows.count():
            item = self._activity_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.state.activity:
            self._activity_rows.addWidget(
                label(
                    "Nothing yet. Calculations you run appear here until you close ATICA.", "muted", wrap=True
                )
            )
            return
        for entry in self.state.activity[:6]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(label(entry.when.strftime("%H:%M"), "muted"))
            rl.addWidget(label(entry.tool, "fieldLabel"))
            rl.addWidget(label(entry.summary, "muted", wrap=False), 1)
            self._activity_rows.addWidget(row)
