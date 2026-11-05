"""Dashboard, unit converter, custom units, packaging builder and breakdown pages."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from atica import __version__
from atica.packaging import PackagingLevel, Product, breakdown
from atica.units import BASE_UNITS

from widgets.common import ResultBox, fill_combo, format_calc, guarded, rounding_combo
from .state import AppState


class Page(QWidget):
    """Base page: re-reads shared state whenever it changes."""

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        state.changed.connect(self.refresh)

    def refresh(self) -> None:  # overridden
        pass

    @staticmethod
    def title(text: str, hint: str = "") -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 6)
        head = QLabel(text)
        head.setObjectName("pageTitle")
        lay.addWidget(head)
        if hint:
            sub = QLabel(hint)
            sub.setObjectName("pageHint")
            sub.setWordWrap(True)
            lay.addWidget(sub)
        return box


def unit_items(registry, category=None):
    units = registry.list_units(category)
    return [("%s — %s" % (u.unit_id, u.name), u.unit_id) for u in units]


# ------------------------------------------------------------------ dashboard
class DashboardPage(Page):
    navigate = Signal(int)

    def __init__(self, state: AppState, entries: List[tuple]) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("ATICA", "Manufacturing units, packaging and quantity conversion. Version %s." % __version__))
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        lay.addWidget(self.summary)
        grid = QGridLayout()
        for i, (index, name, blurb) in enumerate(entries):
            btn = QPushButton("%s\n%s" % (name, blurb))
            btn.setObjectName("tile")
            btn.clicked.connect(lambda _=False, idx=index: self.navigate.emit(idx))
            grid.addWidget(btn, i // 3, i % 3)
        lay.addLayout(grid)
        lay.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        cfg = self.state.config
        where = self.state.path or "not saved to a file yet (auto-saved on exit)"
        self.summary.setText(
            "%d custom unit(s)  ·  %d product(s)  ·  %d material(s)  ·  %d purchasing rule(s)\nConfiguration: %s"
            % (len(cfg.registry.list_custom_units()), len(cfg.products), len(cfg.materials), len(cfg.purchasing), where)
        )


# ----------------------------------------------------------- standard converter
class UnitConverterPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Standard Unit Converter", "Convert between compatible physical units. Custom units appear here too."))
        form = QFormLayout()
        self.category = QComboBox()
        self.value = QLineEdit("1")
        self.from_unit = QComboBox()
        self.to_unit = QComboBox()
        self.precision = QSpinBox()
        self.precision.setRange(-1, 20)
        self.precision.setValue(-1)
        self.precision.setSpecialValueText("Full precision")
        self.rounding = rounding_combo()
        self.rounding.setCurrentIndex(1)
        form.addRow("Category", self.category)
        form.addRow("Value", self.value)
        form.addRow("From", self.from_unit)
        form.addRow("To", self.to_unit)
        form.addRow("Decimal places", self.precision)
        form.addRow("Rounding (when places set)", self.rounding)
        lay.addLayout(form)
        row = QHBoxLayout()
        go = QPushButton("Convert")
        go.setObjectName("primary")
        swap = QPushButton("Swap units")
        row.addWidget(go)
        row.addWidget(swap)
        row.addStretch(1)
        lay.addLayout(row)
        self.result = ResultBox()
        lay.addWidget(self.result, 1)
        go.clicked.connect(self.run)
        swap.clicked.connect(self.swap)
        self.category.currentIndexChanged.connect(self._fill_units)
        self.value.returnPressed.connect(self.run)
        self.refresh()

    def refresh(self) -> None:
        reg = self.state.registry
        fill_combo(self.category, [("All categories", None)] + [(c.capitalize(), c) for c in BASE_UNITS])
        self._fill_units()

    def _fill_units(self) -> None:
        items = unit_items(self.state.registry, self.category.currentData())
        fill_combo(self.from_unit, items)
        fill_combo(self.to_unit, items)
        if self.to_unit.count() > 1 and self.to_unit.currentIndex() == self.from_unit.currentIndex():
            self.to_unit.setCurrentIndex(1)

    def swap(self) -> None:
        a, b = self.from_unit.currentIndex(), self.to_unit.currentIndex()
        self.from_unit.setCurrentIndex(b)
        self.to_unit.setCurrentIndex(a)

    @guarded()
    def run(self) -> None:
        places = self.precision.value()
        res = self.state.registry.convert(
            self.value.text(),
            self.from_unit.currentData(),
            self.to_unit.currentData(),
            precision=None if places < 0 else places,
            rounding=self.rounding.currentData() if places >= 0 else None,
        )
        self.result.show_text("%s %s  =  %s\n\n%s" % (res.to_dict()["input_quantity"], res.input_unit, res.display(), format_calc(res)))


# ---------------------------------------------------------------- custom units
class CustomUnitPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Custom Unit Manager", "Define company units such as 1 industrial_bag = 25 kg."))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Unit", "Category", "Equals", "Reference unit"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._load_selected)
        lay.addWidget(self.table, 1)
        box = QGroupBox("Add or update a unit")
        form = QFormLayout(box)
        self.name = QLineEdit()
        self.name.setPlaceholderText("industrial_bag")
        self.category = QComboBox()
        self.reference = QComboBox()
        self.factor = QLineEdit()
        self.factor.setPlaceholderText("25")
        form.addRow("Name", self.name)
        form.addRow("Category", self.category)
        form.addRow("1 unit equals", self.factor)
        form.addRow("of reference unit", self.reference)
        lay.addWidget(box)
        row = QHBoxLayout()
        add, upd, rem = QPushButton("Add unit"), QPushButton("Update selected"), QPushButton("Remove selected")
        add.setObjectName("primary")
        for b in (add, upd, rem):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.result = ResultBox()
        self.result.setMaximumHeight(110)
        lay.addWidget(self.result)
        add.clicked.connect(self.add)
        upd.clicked.connect(self.update)
        rem.clicked.connect(self.remove)
        self.category.currentIndexChanged.connect(self._fill_reference)
        self.refresh()

    def refresh(self) -> None:
        fill_combo(self.category, [(c.capitalize(), c) for c in BASE_UNITS])
        self._fill_reference()
        units = self.state.registry.list_custom_units()
        self.table.setRowCount(len(units))
        for r, u in enumerate(units):
            ref = u.metadata.get("reference_unit", "")
            vals = [u.unit_id, u.category, u.metadata.get("reference_factor", ""), ref]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

    def _fill_reference(self) -> None:
        fill_combo(self.reference, unit_items(self.state.registry, self.category.currentData()))

    def _load_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        self.name.setText(self.table.item(r, 0).text())
        idx = self.category.findData(self.table.item(r, 1).text())
        if idx >= 0:
            self.category.setCurrentIndex(idx)
        self.factor.setText(self.table.item(r, 2).text())
        ridx = self.reference.findData(self.table.item(r, 3).text())
        if ridx >= 0:
            self.reference.setCurrentIndex(ridx)

    @guarded()
    def add(self) -> None:
        u = self.state.registry.register_unit(
            self.name.text(), self.category.currentData(), self.reference.currentData(), self.factor.text()
        )
        self.state.notify()
        self.result.show_text("Added: 1 %s = %s %s" % (u.unit_id, u.metadata["reference_factor"], u.metadata["reference_unit"]))

    @guarded()
    def update(self) -> None:
        u = self.state.registry.update_unit(
            self.name.text(), category=self.category.currentData(),
            reference_unit=self.reference.currentData(), factor=self.factor.text(),
        )
        self.state.notify()
        self.result.show_text("Updated: 1 %s = %s %s" % (u.unit_id, u.metadata["reference_factor"], u.metadata["reference_unit"]))

    @guarded()
    def remove(self) -> None:
        name = self.name.text().strip()
        if QMessageBox.question(self, "Remove unit", "Remove custom unit %r?" % name) != QMessageBox.Yes:
            return
        self.state.registry.remove_unit(name)
        self.state.notify()
        self.result.show_text("Removed %s." % name)


# ------------------------------------------------------------ packaging builder
class PackagingBuilderPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title(
            "Packaging Hierarchy Builder",
            "Each level holds a number of the level below it, e.g. 1 box = 12 pieces, 1 carton = 20 boxes. "
            "Start with the smallest level (it contains 1 of itself).",
        ))
        top = QHBoxLayout()
        self.product = QComboBox()
        self.product.setMinimumWidth(240)
        new, delete = QPushButton("New product…"), QPushButton("Delete product")
        top.addWidget(QLabel("Product"))
        top.addWidget(self.product, 1)
        top.addWidget(new)
        top.addWidget(delete)
        lay.addLayout(top)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Level (small → large)", "Contains", "Of level"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lay.addWidget(self.table, 1)
        box = QGroupBox("Add a level")
        form = QFormLayout(box)
        self.level = QLineEdit()
        self.level.setPlaceholderText("carton")
        self.contains = QLineEdit()
        self.contains.setPlaceholderText("20")
        self.parent = QComboBox()
        form.addRow("Level name", self.level)
        form.addRow("Contains (number)", self.contains)
        form.addRow("of this smaller level", self.parent)
        lay.addWidget(box)
        row = QHBoxLayout()
        add, rem, val = QPushButton("Add level"), QPushButton("Remove selected level"), QPushButton("Validate")
        add.setObjectName("primary")
        for b in (add, rem, val):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.result = ResultBox()
        self.result.setMaximumHeight(110)
        lay.addWidget(self.result)
        new.clicked.connect(self.new_product)
        delete.clicked.connect(self.delete_product)
        add.clicked.connect(self.add_level)
        rem.clicked.connect(self.remove_level)
        val.clicked.connect(self.validate)
        self.product.currentIndexChanged.connect(self._show_levels)
        self.refresh()

    def current(self):
        pid = self.product.currentData()
        return self.state.config.products.get(pid) if pid else None

    def refresh(self) -> None:
        fill_combo(self.product, [("%s (%s)" % (p.name, p.product_id), p.product_id) for p in self.state.products()])
        self._show_levels()

    def _show_levels(self) -> None:
        p = self.current()
        levels = p.levels if p else []
        self.table.setRowCount(len(levels))
        for r, lv in enumerate(levels):
            for c, v in enumerate([lv.name, str(lv.contains), lv.parent or "(base level)"]):
                self.table.setItem(r, c, QTableWidgetItem(v))
        fill_combo(self.parent, [("(none — base level)", None)] + [(lv.name, lv.name) for lv in levels], keep_selection=False)
        if levels:
            self.parent.setCurrentIndex(self.parent.count() - 1)  # most likely: build on the largest level

    @guarded()
    def new_product(self) -> None:
        pid, ok = QInputDialog.getText(self, "New product", "Product ID (e.g. PROD-001):")
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "New product", "Product name:")
        if not ok:
            return
        self.state.config.add_product(Product(pid, name or pid))
        self.state.notify()
        self.product.setCurrentIndex(self.product.findData(pid.strip()))
        self.result.show_text("Product %s created. Add its packaging levels, smallest first." % pid.strip())

    @guarded()
    def delete_product(self) -> None:
        p = self.current()
        if p is None:
            raise_no_product()
        if QMessageBox.question(self, "Delete product", "Delete %s?" % p.name) != QMessageBox.Yes:
            return
        self.state.config.remove_product(p.product_id)
        self.state.notify()
        self.result.show_text("Deleted %s." % p.name)

    @guarded()
    def add_level(self) -> None:
        p = self.current()
        if p is None:
            raise_no_product()
        p.add_level(PackagingLevel(self.level.text(), self.contains.text() or 1, self.parent.currentData()))
        self.level.clear()
        self.contains.clear()
        self.state.notify()
        self.result.show_validation(p.validate(), "Level added. Hierarchy is valid.")

    @guarded()
    def remove_level(self) -> None:
        p = self.current()
        rows = self.table.selectionModel().selectedRows()
        if p is None or not rows:
            raise_no_product("Select a level in the table first.")
        name = self.table.item(rows[0].row(), 0).text()
        p.remove_level(name)
        self.state.notify()
        self.result.show_text("Removed level %s." % name)

    @guarded()
    def validate(self) -> None:
        p = self.current()
        if p is None:
            raise_no_product()
        self.result.show_validation(p.validate(), "Hierarchy is valid: %s" % "  →  ".join(p.packaging_hierarchy))


def raise_no_product(message: str = "Create or select a product first.") -> None:
    from atica.exceptions import PackagingError

    raise PackagingError(message, code="NO_SELECTION")


# --------------------------------------------------------------------- breakdown
class BreakdownPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Quantity Breakdown Calculator", "Full packages, remainders and packages required for a product."))
        form = QFormLayout()
        self.product = QComboBox()
        self.quantity = QLineEdit("850")
        self.from_level = QComboBox()
        self.to_level = QComboBox()
        self.partial = QCheckBox("Allow partial (fractional) quantities")
        form.addRow("Product", self.product)
        form.addRow("Quantity", self.quantity)
        form.addRow("In", self.from_level)
        form.addRow("Break down into", self.to_level)
        form.addRow("", self.partial)
        lay.addLayout(form)
        go = QPushButton("Calculate")
        go.setObjectName("primary")
        lay.addWidget(go, 0, Qt.AlignLeft)
        self.result = ResultBox()
        lay.addWidget(self.result, 1)
        go.clicked.connect(self.run)
        self.product.currentIndexChanged.connect(self._levels)
        self.refresh()

    def refresh(self) -> None:
        fill_combo(self.product, [("%s (%s)" % (p.name, p.product_id), p.product_id) for p in self.state.products()])
        self._levels()

    def _levels(self) -> None:
        p = self.state.config.products.get(self.product.currentData() or "")
        items = [(lv.name, lv.name) for lv in p.levels] if p else []
        fill_combo(self.from_level, items)
        fill_combo(self.to_level, items)
        if len(items) > 1 and self.to_level.currentIndex() == self.from_level.currentIndex():
            self.to_level.setCurrentIndex(len(items) - 1)

    @guarded()
    def run(self) -> None:
        pid = self.product.currentData()
        if not pid:
            raise_no_product()
        p = self.state.config.get_product(pid)
        r = breakdown(p, self.quantity.text(), self.from_level.currentData(), self.to_level.currentData(), allow_partial=self.partial.isChecked())
        d = r.to_dict()
        self.result.show_text(
            "%s\n\nFull %s packages:        %s\nRemaining quantity:       %s %s\n%s packages required:   %s\n"
            "Exact equivalent:         %s %s"
            % (r, r.to_unit, d["full_packages"], d["remaining_quantity"], r.from_unit, r.to_unit.capitalize(),
               d["packages_required"], d["exact_equivalent"], r.to_unit)
        )
