"""Main application window: navigation list + stacked pages."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStyle,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from atica import __version__

from widgets.common import friendly_error
from .pages_basic import (
    BreakdownPage,
    CustomUnitPage,
    DashboardPage,
    PackagingBuilderPage,
    UnitConverterPage,
)
from .pages_calc import ManufacturingPage, PurchasingPage, YieldScrapPage
from .pages_data import BulkPage, ValidationReportPage
from .state import AppState


class MainWindow(QMainWindow):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.setWindowTitle("ATICA Desktop")
        self.resize(1100, 760)
        self.setMinimumSize(900, 600)

        pages = [
            ("Standard Unit Converter", "Convert physical units", UnitConverterPage(state)),
            ("Custom Unit Manager", "Company-defined units", CustomUnitPage(state)),
            ("Packaging Hierarchy Builder", "Products and packaging levels", PackagingBuilderPage(state)),
            ("Quantity Breakdown", "Pallets, cartons, remainders", BreakdownPage(state)),
            ("Manufacturing Calculator", "Materials, batches, formulas", ManufacturingPage(state)),
            ("Yield & Scrap Calculator", "Scrap, yield, wastage", YieldScrapPage(state)),
            ("Purchasing & Inventory", "MOQ and order multiples", PurchasingPage(state)),
            ("Bulk File Import", "CSV and Excel", BulkPage(state)),
            ("Validation & Reports", "Check configuration", ValidationReportPage(state)),
        ]
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(248)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setSpacing(2)
        self.stack = QStackedWidget()
        dashboard = DashboardPage(state, [(i + 1, name, blurb) for i, (name, blurb, _p) in enumerate(pages)])
        dashboard.navigate.connect(self.nav.setCurrentRow)
        self._add_nav_item("Dashboard", QStyle.SP_ComputerIcon)
        self.stack.addWidget(dashboard)
        icons = (
            QStyle.SP_DialogApplyButton,
            QStyle.SP_FileDialogDetailedView,
            QStyle.SP_DirOpenIcon,
            QStyle.SP_ArrowRight,
            QStyle.SP_ComputerIcon,
            QStyle.SP_DialogCancelButton,
            QStyle.SP_DriveHDIcon,
            QStyle.SP_DialogOpenButton,
            QStyle.SP_MessageBoxInformation,
        )
        for (name, _blurb, page), icon in zip(pages, icons):
            self._add_nav_item(name, icon)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        central = QWidget()
        central.setObjectName("appSurface")
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._sidebar())
        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_lay = QVBoxLayout(workspace)
        workspace_lay.setContentsMargins(0, 0, 0, 0)
        workspace_lay.setSpacing(0)
        workspace_lay.addWidget(self._workspace_header())
        workspace_lay.addWidget(self.stack, 1)
        lay.addWidget(workspace, 1)
        self.setCentralWidget(central)
        self._menu()
        state.changed.connect(self._update_title)
        self._update_title()
        self.statusBar().showMessage("ATICA library %s — all calculations run offline." % __version__)

    def _add_nav_item(self, label: str, icon: QStyle.StandardPixmap) -> None:
        item = QListWidgetItem(self.style().standardIcon(icon), label)
        item.setToolTip(label)
        self.nav.addItem(item)

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 14)
        layout.setSpacing(0)

        brand = QLabel("ATICA")
        brand.setObjectName("brand")
        tagline = QLabel("Manufacturing intelligence")
        tagline.setObjectName("tagline")
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(22)
        layout.addWidget(self.nav, 1)

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)
        version = QLabel("ATICA Desktop %s" % __version__)
        version.setObjectName("sidebarVersion")
        info = QLabel("Offline workspace  •  File settings in File menu")
        info.setObjectName("sidebarInfo")
        info.setWordWrap(True)
        layout.addWidget(version)
        layout.addWidget(info)
        return sidebar

    def _workspace_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("workspaceHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(26, 20, 26, 14)
        layout.setSpacing(6)
        title = QLabel("Operations workspace")
        title.setObjectName("workspaceTitle")
        detail = QLabel("Select a module from the navigation to get started.")
        detail.setObjectName("workspaceDetail")
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch(1)
        layout.setSizeConstraint(QLayout.SetDefaultConstraint)
        return header

    # ------------------------------------------------------------------- menu
    def _menu(self) -> None:
        menu = self.menuBar().addMenu("&File")
        for text, shortcut, slot in (
            ("&New configuration", QKeySequence.New, self.new),
            ("&Open configuration…", QKeySequence.Open, self.open),
            ("&Save", QKeySequence.Save, self.save),
            ("Save &as…", QKeySequence.SaveAs, self.save_as),
        ):
            act = QAction(text, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            menu.addAction(act)
        menu.addSeparator()
        quit_ = QAction("E&xit", self)
        quit_.triggered.connect(self.close)
        menu.addAction(quit_)

    def _update_title(self) -> None:
        name = os.path.basename(self.state.path) if self.state.path else "Untitled"
        self.setWindowTitle("%s%s — ATICA Desktop" % (name, " *" if self.state.dirty else ""))

    def _error(self, exc: BaseException) -> None:
        QMessageBox.warning(self, "ATICA", friendly_error(exc))

    def _confirm_discard(self) -> bool:
        if not self.state.dirty:
            return True
        answer = QMessageBox.question(self, "Unsaved changes", "Discard unsaved changes?")
        return answer == QMessageBox.Yes

    def new(self) -> None:
        if self._confirm_discard():
            self.state.new()
            self._update_title()

    def open(self) -> None:
        if not self._confirm_discard():
            return
        name, _ = QFileDialog.getOpenFileName(self, "Open configuration", "", "ATICA configuration (*.json)")
        if name:
            try:
                self.state.load(name)
                self._update_title()
            except Exception as exc:  # noqa: BLE001
                self._error(exc)

    def save(self) -> None:
        if not self.state.path:
            return self.save_as()
        self._save(None)

    def save_as(self) -> None:
        name, _ = QFileDialog.getSaveFileName(self, "Save configuration", "atica_config.json", "ATICA configuration (*.json)")
        if name:
            self._save(name)

    def _save(self, path) -> None:
        try:
            target = self.state.save(path)
            self.statusBar().showMessage("Saved %s" % target, 5000)
            self._update_title()
        except Exception as exc:  # noqa: BLE001
            self._error(exc)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        """Auto-save to the app data folder so work survives a restart."""
        try:
            self.state.save(None if not self.state.path else self.state.path)
        except Exception as exc:  # noqa: BLE001
            if QMessageBox.question(self, "ATICA", friendly_error(exc) + "\n\nClose anyway?") != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
