"""Frameless-window title bar with native window-management behaviour where available."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStyle, QToolButton, QWidget

from .. import branding


class TitleBar(QWidget):
    """A compact application title bar; its owner provides the real window operations."""

    HEIGHT = 30
    minimize_requested = Signal()
    toggle_maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(self.HEIGHT)
        self._move_origin: Optional[QPoint] = None
        self._window_origin: Optional[QPoint] = None
        self._using_system_move = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)
        mark = QLabel()
        mark.setObjectName("titleBarIcon")
        mark.setPixmap(branding.brand_pixmap(branding.ATICA_LOGO, 18))
        mark.setFixedSize(18, 18)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(mark)

        title = QLabel("ATICA - Manufacturing Calculations")
        title.setObjectName("titleBarTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        layout.addStretch(1)

        self.minimize_button = self._button("titleBarMinimize", QStyle.StandardPixmap.SP_TitleBarMinButton)
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(self.minimize_requested)
        self.maximize_button = self._button("titleBarMaximize", QStyle.StandardPixmap.SP_TitleBarMaxButton)
        self.maximize_button.clicked.connect(self.toggle_maximize_requested)
        self.close_button = self._button("titleBarClose", QStyle.StandardPixmap.SP_TitleBarCloseButton)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.close_requested)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)
        self.set_maximized(False)

    def _button(self, name: str, icon: QStyle.StandardPixmap) -> QToolButton:
        button = QToolButton()
        button.setObjectName(name)
        button.setIcon(self.style().standardIcon(icon))
        button.setFixedSize(46, self.HEIGHT)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def set_maximized(self, maximized: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if maximized
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        self.maximize_button.setIcon(self.style().standardIcon(icon))
        self.maximize_button.setToolTip("Restore" if maximized else "Maximize")
        self.maximize_button.setAccessibleName("Restore" if maximized else "Maximize")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.window().isMaximized():
            self._move_origin = event.globalPosition().toPoint()
            self._window_origin = self.window().pos()
            handle = self.window().windowHandle()
            self._using_system_move = bool(handle and handle.startSystemMove())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._move_origin is not None and not self._using_system_move and self._window_origin is not None:
            self.window().move(self._window_origin + event.globalPosition().toPoint() - self._move_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._move_origin = None
        self._window_origin = None
        self._using_system_move = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
