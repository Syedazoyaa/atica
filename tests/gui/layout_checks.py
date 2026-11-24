"""Layout checks shared by the in-process tests and the display-scaling subprocess probe.

A window is resized to a *logical* size.  At Windows scaling ``s`` a physical 1366 x 768 screen offers
1366/s x 768/s logical pixels: 1366x768 (100 %), 1093x614 (125 %), 911x512 (150 %).
"""

from __future__ import annotations

from typing import List

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
)

LOGICAL_SIZES = [(1920, 1080), (1600, 900), (1366, 768), (1093, 614), (911, 512)]


def settle() -> None:
    app = QApplication.instance()
    for _ in range(3):
        app.processEvents()


def check_window(window, width: int, height: int) -> List[str]:
    """Resize ``window`` and return a list of layout problems (empty = fine)."""
    from atica.gui.main_window import COMPACT_BELOW, SECTIONS

    problems: List[str] = []
    window.resize(width, height)
    settle()
    where = "%dx%d" % (window.width(), window.height())
    if window.width() > width or window.height() > height:
        problems.append("%s: window cannot shrink to the requested %dx%d" % (where, width, height))
    if window.sidebar.compact != (window.width() < COMPACT_BELOW):
        problems.append("%s: sidebar compact mode is wrong" % where)
    for index, (key, title, _icon, _description) in enumerate(SECTIONS):
        window.sidebar.select(index)
        settle()
        view = window.views[key]
        tabs = getattr(view, "tabs", None)
        for tab in range(tabs.count() if tabs is not None else 1):
            if tabs is not None:
                tabs.setCurrentIndex(tab)
                settle()
            label = "%s %s/tab%d" % (where, title, tab)
            page = view.rect()
            if view.minimumSizeHint().width() > page.width():
                problems.append(
                    "%s: needs %dpx but only %dpx are available"
                    % (label, view.minimumSizeHint().width(), page.width())
                )
            for area in view.findChildren(QScrollArea):
                if area.isVisible() and area.horizontalScrollBar().isVisible():
                    problems.append(
                        "%s: a horizontal scrollbar appears (content wider than its pane)" % label
                    )
            for widget in [
                w for kind in (QPushButton, QLineEdit, QComboBox, QCheckBox) for w in view.findChildren(kind)
            ]:
                if not widget.isVisible() or isinstance(widget.parent(), QTableWidget):
                    continue
                left = widget.mapTo(window, widget.rect().topLeft()).x()
                right = left + widget.width()
                if left < -1 or right > window.width() + 1:
                    problems.append(
                        "%s: %s %r is clipped horizontally (x=%d..%d of %d)"
                        % (label, type(widget).__name__, widget.objectName(), left, right, window.width())
                    )
    return problems
