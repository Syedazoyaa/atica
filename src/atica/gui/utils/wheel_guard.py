"""The mouse wheel must never change a closed drop-down: scrolling a page is not choosing a value.

One application-wide event filter covers every :class:`~PySide6.QtWidgets.QComboBox`, including ones
created later (table cells, new screens).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QComboBox


class ComboWheelGuard(QObject):
    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]
        # test the event type first: this filter sees every event in the application
        if event.type() != QEvent.Type.Wheel or not isinstance(watched, QComboBox):
            return False
        if watched.view().isVisible():
            return False  # the list was opened on purpose: let it scroll
        event.ignore()  # not handled here, so Qt passes it on to the surrounding scroll area
        return True


def install_wheel_guard(app: QApplication) -> None:
    """Install the guard once per application."""
    if app.findChild(ComboWheelGuard) is None:
        app.installEventFilter(ComboWheelGuard(app))
