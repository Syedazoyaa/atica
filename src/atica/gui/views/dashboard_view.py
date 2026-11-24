"""Dashboard: direct access to the calculation modules, quick calculations and this session's activity.

It deliberately shows no invented data: the activity list contains only calculations the user has run in
the current session, and says so when it is empty.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
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

from ..components import Card, label
from ..components.backdrop import BackdropWidget
from ..services import AppState
from ..styles import CURRENT as T
from ..utils.icons import icon, pixmap

# (section key, title, one-line description, icon)
Module = Tuple[str, str, str, str]


class ModuleCard(QFrame):
    """A clickable (and keyboard-operable) tile that opens a section."""

    clicked = Signal()

    def __init__(self, title: str, text: str, icon_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAccessibleName(title)
        self.setMinimumHeight(92)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)
        badge = QLabel()
        badge.setObjectName("iconBadge")
        badge.setPixmap(pixmap(icon_name, T.ink, 22))
        badge.setFixedSize(40, 40)
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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class ResponsiveGrid(QWidget):
    """Lays widgets out in as many equal columns as fit (``min_cell`` logical pixels per column)."""

    def __init__(self, min_cell: int, max_columns: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._min_cell = min_cell
        self._max_columns = max_columns
        self._items: List[QWidget] = []
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)

    def set_items(self, items: Sequence[QWidget]) -> None:
        self._items = list(items)
        self._relayout(max(1, self._columns or self._max_columns))

    @property
    def columns(self) -> int:
        return self._columns

    def _relayout(self, columns: int) -> None:
        self._columns = columns
        while self._grid.count():
            self._grid.takeAt(0)
        for i, widget in enumerate(self._items):
            self._grid.addWidget(widget, i // columns, i % columns)
        for c in range(self._max_columns):
            self._grid.setColumnStretch(c, 1 if c < columns else 0)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        columns = max(1, min(self._max_columns, self.width() // self._min_cell))
        if columns != self._columns:
            self._relayout(columns)


class DashboardView(BackdropWidget):
    """``navigate(section_key, tab_index)`` is called when a tile or quick calculation is chosen."""

    BACKDROP = "bg_dashboard.svg"
    ANCHOR = "br"

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
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(label("Dashboard", "pageTitle"))
        titles.addWidget(
            label(
                "Exact manufacturing calculations: units, packaging, materials, production, quality and purchasing. "
                "The same engine is available in Python (import atica).",
                "pageSubtitle",
                wrap=True,
            )
        )
        head.addLayout(titles, 1)
        head.addWidget(label("Version " + __version__, "muted"), 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)
        lay.addSpacing(6)

        lay.addWidget(label("CALCULATION MODULES", "sectionLabel"))
        tiles: List[QWidget] = []
        for key, title, desc, icon_name in modules:
            tile = ModuleCard(title, desc, icon_name)
            tile.clicked.connect(lambda k=key: navigate(k, 0))
            tiles.append(tile)
        self.modules_grid = ResponsiveGrid(min_cell=300, max_columns=3)
        self.modules_grid.set_items(tiles)
        lay.addWidget(self.modules_grid)

        lay.addSpacing(6)
        lay.addWidget(label("QUICK CALCULATIONS", "sectionLabel"))
        buttons: List[QWidget] = []
        icons = {key: icon_name for key, _t, _d, icon_name in modules}
        for text, key, tab in quick_tools:
            button = QPushButton(" " + text)
            button.setIcon(icon(icons.get(key, "units"), T.ink, 16))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, k=key, t=tab: navigate(k, t))
            buttons.append(button)
        self.quick_grid = ResponsiveGrid(min_cell=210, max_columns=5)
        self.quick_grid.set_items(buttons)
        lay.addWidget(self.quick_grid)

        lay.addSpacing(6)
        lay.addWidget(label("RECENT ACTIVITY (THIS SESSION)", "sectionLabel"))
        self._activity_card = Card()
        self._activity_rows = QVBoxLayout()
        self._activity_rows.setSpacing(0)
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
            row = QFrame()
            row.setObjectName("activityRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 7, 0, 7)
            rl.setSpacing(14)
            when = label(entry.when.strftime("%H:%M"), "muted")
            when.setFixedWidth(44)
            tool = label(entry.tool, "value")
            tool.setFixedWidth(130)
            rl.addWidget(when)
            rl.addWidget(tool)
            rl.addWidget(label(entry.summary, "muted", wrap=True), 1)
            self._activity_rows.addWidget(row)
