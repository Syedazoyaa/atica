"""The main window: sidebar navigation and the stacked screens."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from atica.version import __version__

from .components import Sidebar
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


class MainWindow(QMainWindow):
    def __init__(self, state: Optional[AppState] = None) -> None:
        super().__init__()
        self.state = state or AppState()
        self.setWindowTitle("ATICA " + __version__)
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

        central = QWidget()
        central.setObjectName("content")
        central.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        for i in range(len(self._order)):
            action = QAction(self)
            action.setShortcut(QKeySequence("Ctrl+%d" % ((i + 1) % 10)))
            action.triggered.connect(lambda _c=False, n=i: self.sidebar.select(n))
            self.addAction(action)
        self.sidebar.select(0)
        self._apply_layout_mode()
        self._focus_set = False

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        if not self._focus_set:
            # start without a keyboard-focus ring on the first navigation button; Tab still reaches everything
            self._focus_set = True
            self.centralWidget().setFocus(Qt.FocusReason.OtherFocusReason)

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
