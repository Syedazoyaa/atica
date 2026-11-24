"""Navigation sidebar: ATICA wordmark, section buttons and the product version.

The sidebar has two widths: *expanded* (icons and titles) and *compact* (icons only, titles in
tooltips).  The main window switches to compact automatically on narrow screens - for example a
1366 x 768 laptop at 150 % scaling has only about 910 logical pixels of width.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from atica.version import __version__

from ..styles import CURRENT as T
from ..utils.icons import icon, logo_pixmap, wordmark_pixmap
from .backdrop import draw_backdrop
from .basics import label

# (section key, title, icon name)
Section = Tuple[str, str, str]

EXPANDED_WIDTH = 236
COMPACT_WIDTH = 64


class Sidebar(QFrame):
    """Emits :attr:`selected` with the index of the chosen section."""

    selected = Signal(int)

    def __init__(self, sections: Sequence[Section], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._titles = [title for _key, title, _icon in sections]
        self._compact = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 14)
        layout.setSpacing(2)

        self._brand = QLabel()
        self._brand.setAccessibleName("ATICA")
        self._brand.setContentsMargins(4, 0, 0, 0)
        self._tag = label("Manufacturing calculations", "brandTag")
        self._tag.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(self._brand)
        layout.addWidget(self._tag)
        layout.addSpacing(18)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: List[QPushButton] = []
        self._icon_names: List[str] = []
        for index, (_key, title, icon_name) in enumerate(sections):
            button = QPushButton("  " + title)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setIconSize(QSize(20, 20))
            button.setToolTip("%s  (Ctrl+%d)" % (title, (index + 1) % 10))
            button.setAccessibleName(title)
            button.clicked.connect(lambda _checked=False, i=index: self.select(i))
            self._group.addButton(button, index)
            self._buttons.append(button)
            self._icon_names.append(icon_name)
            layout.addWidget(button)
        layout.addStretch(1)
        self._version = label("Version " + __version__, "sidebarVersion")
        self._version.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(self._version)
        self.set_compact(False)
        self._refresh_icons(-1)

    # -------------------------------------------------------------- behaviour
    @property
    def compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        """Switch between the expanded and the icon-only layout."""
        self._compact = compact
        self.setFixedWidth(COMPACT_WIDTH if compact else EXPANDED_WIDTH)
        self._brand.setPixmap(logo_pixmap(32) if compact else wordmark_pixmap(30))
        self._tag.setVisible(not compact)
        self._version.setVisible(not compact)
        for button, title in zip(self._buttons, self._titles):
            button.setText("" if compact else "  " + title)
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)

    def select(self, index: int) -> None:
        self._refresh_icons(index)
        for i, button in enumerate(self._buttons):
            button.setChecked(i == index)
        self.selected.emit(index)

    def current(self) -> int:
        return self._group.checkedId()

    def _refresh_icons(self, active: int) -> None:
        for i, button in enumerate(self._buttons):
            color = T.ink if i == active else T.ink_secondary
            button.setIcon(icon(self._icon_names[i], color, 20))

    # ---------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        draw_backdrop(self, painter, "bg_nav.svg", "bl", fill=T.layer)
        painter.setPen(QColor(T.border))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.end()
