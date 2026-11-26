"""The main window: sidebar navigation and the stacked screens."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from atica.version import __version__

from .components import Sidebar, TitleBar
from .services import AppState
from .views import (
    AboutView,
    DashboardView,
    DataToolsView,
    MaterialsView,
    PackagingView,
    ProductionView,
    PurchasingView,
    QualityView,
    SettingsView,
    UnitsView,
)

#: key, title, icon, short description (None for screens that are not calculation modules)
SECTIONS = [
    ("dashboard", "Dashboard", "dashboard", None),
    (
        "units",
        "Unit Converter",
        "units",
        "Convert standard and custom units. Incompatible units are rejected, temperatures handled correctly.",
    ),
    (
        "packaging",
        "Packaging Calculations",
        "packaging",
        "Multi-level hierarchies, full packages, remainders and minimum whole packages.",
    ),
    (
        "materials",
        "Materials and BOM",
        "materials",
        "Material requirements with scrap and wastage, and capacity from stock.",
    ),
    (
        "production",
        "Production Calculations",
        "production",
        "Batches, partial batches, production time and capacity.",
    ),
    (
        "quality",
        "Quality and Yield",
        "quality",
        "First-pass and final yield, scrap, rework, recovery and wastage.",
    ),
    (
        "purchasing",
        "Purchasing Calculations",
        "purchasing",
        "Order quantities with stock, minimums, multiples and unit conversion.",
    ),
    ("data", "Data Tools", "data", "Convert CSV / Excel files in bulk and import a BOM."),
    ("settings", "Settings", "settings", None),
    ("about", "About ATICA", "about", None),
]

QUICK_TOOLS = [
    ("Convert units", "units", 0),
    ("Packaging breakdown", "packaging", 0),
    ("BOM requirements", "materials", 0),
    ("Required input for scrap", "quality", 0),
    ("Order quantity", "purchasing", 0),
]


MIN_WIDTH = 760
MIN_HEIGHT = 480
#: below this window width the sidebar shows icons only
COMPACT_BELOW = 1100
RESIZE_MARGIN = 6


class MainWindow(QMainWindow):
    def __init__(self, state: Optional[AppState] = None) -> None:
        super().__init__()
        self.state = state or AppState()
        self.setWindowTitle("ATICA " + __version__)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        # Sized from the screen, not fixed: a 1366 x 768 laptop at 150 % scaling offers only ~910 x 510
        # logical pixels, so the minimum must stay small and the layout must adapt (see resizeEvent).
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(self._initial_size())

        self.views: Dict[str, QWidget] = {}
        modules = [(k, t, d, i) for k, t, i, d in SECTIONS if d]
        self.views["dashboard"] = DashboardView(self.state, modules, QUICK_TOOLS, self.navigate)
        self.views["units"] = UnitsView(self.state)
        self.views["packaging"] = PackagingView(self.state)
        self.views["materials"] = MaterialsView(self.state)
        self.views["production"] = ProductionView(self.state)
        self.views["quality"] = QualityView(self.state)
        self.views["purchasing"] = PurchasingView(self.state)
        self.views["data"] = DataToolsView(self.state)
        self.views["settings"] = SettingsView(self.state)
        self.views["about"] = AboutView(self.state)

        self._order: List[str] = [key for key, *_ in SECTIONS]
        self.stack = QStackedWidget()
        for key in self._order:
            self.stack.addWidget(self.views[key])
        self.sidebar = Sidebar([(k, t, i) for k, t, i, _d in SECTIONS])
        self.sidebar.selected.connect(self.stack.setCurrentIndex)

        content = QWidget()
        content.setObjectName("content")
        content.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        layout = QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        self.title_bar = TitleBar()
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.toggle_maximize_requested.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        frame = QWidget()
        frame.setObjectName("windowFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.title_bar)
        frame_layout.addWidget(content, 1)
        self.setCentralWidget(frame)

        for i in range(len(self._order)):
            action = QAction(self)
            action.setShortcut(QKeySequence("Ctrl+%d" % ((i + 1) % 10)))
            action.triggered.connect(lambda _c=False, n=i: self.sidebar.select(n))
            self.addAction(action)
        self.sidebar.select(0)
        self._apply_layout_mode()
        self._focus_set = False
        self._resize_edges: Optional[Qt.Edges] = None
        self._resize_origin: Optional[QPoint] = None
        self._resize_geometry: Optional[QRect] = None

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        # edge resizing needs the mouse events of every child widget, but only while the window is on screen
        QApplication.instance().installEventFilter(self)
        if not self._focus_set:
            # start without a keyboard-focus ring on the first navigation button; Tab still reaches everything
            self._focus_set = True
            self.centralWidget().setFocus(Qt.FocusReason.OtherFocusReason)

    def hideEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        # also runs on close: an application-wide filter must not outlive the visible window
        QApplication.instance().removeEventFilter(self)
        self._end_resize()
        super().hideEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())

    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]
        # The filter sees every object in the application, including ones being destroyed: look at the
        # event first, and answer False without handing unrelated objects back to Qt.
        if event.type() not in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
        ):
            return False
        if not isinstance(watched, QWidget) or watched.window() is not self:
            return False
        mouse_event = event
        if not isinstance(mouse_event, QMouseEvent):
            return False
        if self._resize_edges is not None:
            if event.type() == QEvent.Type.MouseMove:
                self._resize_from(mouse_event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._end_resize()
                return True
        edges = self._resize_edges_at(mouse_event.globalPosition().toPoint())
        if event.type() == QEvent.Type.MouseMove:
            self._set_resize_cursor(edges)
        elif (
            event.type() == QEvent.Type.MouseButtonPress
            and mouse_event.button() == Qt.MouseButton.LeftButton
            and edges
            and self._start_resize(edges, mouse_event.globalPosition().toPoint())
        ):
            return True
        return False

    def _resize_edges_at(self, global_pos: QPoint) -> Qt.Edges:
        if self.isMaximized() or self.isFullScreen():
            return Qt.Edge(0)
        rect = self.geometry()
        edges = Qt.Edge(0)
        if global_pos.x() - rect.left() < RESIZE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        elif rect.right() - global_pos.x() < RESIZE_MARGIN:
            edges |= Qt.Edge.RightEdge
        if global_pos.y() - rect.top() < RESIZE_MARGIN:
            edges |= Qt.Edge.TopEdge
        elif rect.bottom() - global_pos.y() < RESIZE_MARGIN:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _set_resize_cursor(self, edges: Qt.Edges) -> None:
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            cursor = Qt.CursorShape.SizeVerCursor
        elif edges in (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges:
            cursor = Qt.CursorShape.SizeBDiagCursor
        else:
            self.unsetCursor()
            return
        self.setCursor(cursor)

    def _start_resize(self, edges: Qt.Edges, global_pos: QPoint) -> bool:
        handle = self.windowHandle()
        if handle is not None and handle.startSystemResize(edges):
            return True
        self._resize_edges = edges
        self._resize_origin = global_pos
        self._resize_geometry = self.geometry()
        return True

    def _end_resize(self) -> None:
        self._resize_edges = None
        self._resize_origin = None
        self._resize_geometry = None

    def _resize_from(self, global_pos: QPoint) -> None:
        if self._resize_edges is None or self._resize_origin is None or self._resize_geometry is None:
            return
        rect = QRect(self._resize_geometry)
        delta = global_pos - self._resize_origin
        if self._resize_edges & Qt.Edge.LeftEdge:
            rect.setLeft(rect.left() + delta.x())
        if self._resize_edges & Qt.Edge.RightEdge:
            rect.setRight(rect.right() + delta.x())
        if self._resize_edges & Qt.Edge.TopEdge:
            rect.setTop(rect.top() + delta.y())
        if self._resize_edges & Qt.Edge.BottomEdge:
            rect.setBottom(rect.bottom() + delta.y())
        rect.setWidth(max(self.minimumWidth(), rect.width()))
        rect.setHeight(max(self.minimumHeight(), rect.height()))
        self.setGeometry(rect)

    def _toggle_maximize(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _initial_size(self) -> QSize:
        screen = self.screen()
        available = screen.availableGeometry() if screen is not None else None
        if available is None:
            return QSize(1280, 820)
        width = min(1280, int(available.width() * 0.92))
        height = min(820, int(available.height() * 0.92))
        return QSize(max(MIN_WIDTH, width), max(MIN_HEIGHT, height))

    def _apply_layout_mode(self) -> None:
        compact = self.width() < COMPACT_BELOW
        if compact != self.sidebar.compact:
            self.sidebar.set_compact(compact)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._apply_layout_mode()

    def navigate(self, key: str, tab: int = 0) -> None:
        """Show a screen (and one of its tabs)."""
        index = self._order.index(key)
        self.sidebar.select(index)
        view = self.views[key]
        show_tab = getattr(view, "show_tab", None)
        if show_tab:
            show_tab(tab)
