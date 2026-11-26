"""Navigation sidebar: ATICA wordmark, section buttons, company name and product version.

The sidebar has two widths: *expanded* (icons and titles) and *compact* (icons only, titles in
tooltips).  The main window switches to compact automatically on narrow screens - for example a
1366 x 768 laptop at 150 % scaling has only about 910 logical pixels of width.  On short windows the
sidebar also shrinks the brand block and the button padding so that nothing is squeezed.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QButtonGroup, QFrame, QPushButton, QVBoxLayout, QWidget

from atica.version import __version__

from .. import branding as B
from ..styles import CURRENT as T
from ..utils.icons import icon
from .backdrop import draw_backdrop
from .basics import label
from .brand import BrandBlock

# (section key, title, icon name)
Section = Tuple[str, str, str]

EXPANDED_WIDTH = 264
COMPACT_WIDTH = 64
#: below this sidebar height the small brand block and tighter navigation buttons are used
SHORT_BELOW = 660


class Sidebar(QFrame):
    """Emits :attr:`selected` with the index of the chosen section."""

    selected = Signal(int)

    def __init__(self, sections: Sequence[Section], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._titles = [title for _key, title, _icon in sections]
        self._compact = False
        self._short = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 14)
        layout.setSpacing(2)

        self._brand = BrandBlock(64)
        self._tag = label("Manufacturing calculations", "brandTag")
        self._tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self._footer = QWidget()
        footer = QVBoxLayout(self._footer)
        footer.setContentsMargins(4, 0, 4, 0)
        footer.setSpacing(2)
        rule = QFrame()
        rule.setObjectName("divider")
        footer.addWidget(rule)
        footer.addSpacing(6)
        footer.addWidget(label(B.COMPANY_NAME.upper(), "sidebarCompany"))
        footer.addWidget(label("Version " + __version__, "sidebarVersion"))
        layout.addWidget(self._footer)
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
        for button, title in zip(self._buttons, self._titles):
            button.setText("" if compact else "  " + title)
        self._footer.setVisible(not compact)
        self._apply_density()

    def _apply_density(self) -> None:
        small = self._compact or self._short
        self._brand.set_logo_height(34 if small else 64)
        self._brand.set_name_visible(not small)
        self._tag.setVisible(not small)
        for button in self._buttons:
            button.setProperty("compact", self._compact)
            button.setProperty("short", self._short)
            button.style().unpolish(button)
            button.style().polish(button)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        short = self.height() < SHORT_BELOW
        if short != self._short:
            self._short = short
            self._apply_density()

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
