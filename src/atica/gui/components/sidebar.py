"""Navigation sidebar with the ATICA brand, section buttons and the product version."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from atica.version import __version__

from ..utils.icons import icon, logo_pixmap
from .basics import label

# (section key, title, icon name)
Section = Tuple[str, str, str]


class Sidebar(QFrame):
    """Emits :attr:`selected` with the index of the chosen section."""

    selected = Signal(int)

    def __init__(self, sections: Sequence[Section], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(248)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 16)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 0)
        brand.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(logo_pixmap(40))
        mark.setFixedSize(40, 40)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("ATICA", "brandName"))
        names.addWidget(label("Manufacturing calculations", "brandTag"))
        brand.addWidget(mark)
        brand.addLayout(names)
        layout.addLayout(brand)
        layout.addSpacing(14)
        rule = QFrame()
        rule.setObjectName("sidebarRule")
        layout.addWidget(rule)
        layout.addSpacing(10)

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
            button.setIcon(icon(icon_name, "#C9DBEF", 20))
            button.setIconSize(QSize(20, 20))
            button.setToolTip("%s  (Ctrl+%d)" % (title, (index + 1) % 10))
            button.clicked.connect(lambda _checked=False, i=index: self.select(i))
            self._group.addButton(button, index)
            self._buttons.append(button)
            self._icon_names.append(icon_name)
            layout.addWidget(button)
        layout.addStretch(1)
        rule2 = QFrame()
        rule2.setObjectName("sidebarRule")
        layout.addWidget(rule2)
        layout.addSpacing(6)
        layout.addWidget(label("Version " + __version__, "sidebarVersion"))

    def select(self, index: int) -> None:
        for i, button in enumerate(self._buttons):
            button.setChecked(i == index)
            button.setIcon(icon(self._icon_names[i], "#FFFFFF" if i == index else "#C9DBEF", 20))
        self.selected.emit(index)

    def current(self) -> int:
        return self._group.checkedId()
