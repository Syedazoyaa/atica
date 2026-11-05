"""Drives the desktop app headlessly. Skipped when PySide6 is not installed."""
import os
import sys

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "gui")
sys.path.insert(0, GUI_DIR)

from PySide6.QtCore import QStandardPaths  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from atica.packaging import PackagingLevel, Product  # noqa: E402
from windows.main_window import MainWindow  # noqa: E402
from windows.state import AppState  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    QStandardPaths.setTestModeEnabled(True)  # never touch the real app-data folder
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(qapp):
    state = AppState()
    window = MainWindow(state)
    yield window
    window.state.dirty = False


def page(win, cls_name):
    for i in range(win.stack.count()):
        w = win.stack.widget(i)
        if type(w).__name__ == cls_name:
            return w
    raise AssertionError(cls_name)


def select(combo, data):
    idx = combo.findData(data)
    assert idx >= 0, data
    combo.setCurrentIndex(idx)


def text(p):
    return p.result.toPlainText()


def test_all_ten_screens_exist(win):
    names = [win.nav.item(i).text() for i in range(win.nav.count())]
    assert names == [
        "Dashboard", "Standard Unit Converter", "Custom Unit Manager", "Packaging Hierarchy Builder",
        "Quantity Breakdown", "Manufacturing Calculator", "Yield & Scrap Calculator",
        "Purchasing & Inventory", "Bulk File Import", "Validation & Reports"]


def test_unit_converter(win):
    p = page(win, "UnitConverterPage")
    select(p.from_unit, "kg")
    select(p.to_unit, "g")
    p.value.setText("2.5")
    p.run()
    assert "2500 g" in text(p)
    select(p.to_unit, "m") if p.to_unit.findData("m") >= 0 else None
    p.category.setCurrentIndex(0)
    select(p.to_unit, "m")
    p.run()
    assert "Could not calculate" in text(p) and "INCOMPATIBLE_UNITS" in text(p)
    assert "Traceback" not in text(p)


def test_custom_unit_then_convert(win):
    p = page(win, "CustomUnitPage")
    p.name.setText("industrial_bag")
    select(p.category, "mass")
    select(p.reference, "kg")
    p.factor.setText("25")
    p.add()
    assert "Added" in text(p)
    assert win.state.registry.has_unit("industrial_bag")
    assert p.table.rowCount() == 1
    p.add()  # duplicate
    assert "DUPLICATE_UNIT" in text(p)
    conv = page(win, "UnitConverterPage")
    assert conv.from_unit.findData("industrial_bag") >= 0  # dropdowns refreshed


def build_product(win):
    p = Product("PROD-A", "Product A")
    for lv in (PackagingLevel("piece", 1), PackagingLevel("box", 12, "piece"),
               PackagingLevel("carton", 20, "box"), PackagingLevel("pallet", 40, "carton")):
        p.add_level(lv)
    win.state.config.add_product(p)
    win.state.notify()
    return p


def test_packaging_builder_and_breakdown(win):
    b = page(win, "PackagingBuilderPage")
    win.state.config.add_product(Product("P1", "Empty"))
    win.state.notify()
    for name, contains, parent in (("piece", "1", None), ("box", "12", "piece")):
        b.level.setText(name)
        b.contains.setText(contains)
        select(b.parent, parent)
        b.add_level()
    assert b.table.rowCount() == 2 and "valid" in text(b)
    b.level.setText("box")
    b.contains.setText("3")
    b.add_level()
    assert "DUPLICATE_LEVEL" in text(b)

    build_product(win)
    bp = page(win, "BreakdownPage")
    select(bp.product, "PROD-A")
    bp.quantity.setText("850")
    select(bp.from_level, "carton")
    select(bp.to_level, "pallet")
    bp.run()
    out = text(bp)
    assert "21 full pallet" in out and "10 carton" in out and "22 pallet required" in out
    bp.quantity.setText("850.5")
    bp.run()
    assert "PARTIAL_NOT_ALLOWED" in text(bp)
    bp.partial.setChecked(True)
    bp.run()
    assert "10.5" in text(bp)


def test_manufacturing(win):
    m = page(win, "ManufacturingPage")
    select(m.material_unit, "kg")
    m.per_unit.setText("0.5")
    m.qty.setText("1000")
    m.material()
    assert "500 kg" in text(m)
    m.scrap.setText("1.5")
    m.material()
    assert "INVALID_SCRAP_RATE" in text(m)
    m.batches()
    assert "Full batches:       10" in text(m)
    m.formula()
    assert "526.31578947" in text(m)
    m.expr.setText("__import__('os')")
    m.formula()
    assert "Could not calculate" in text(m)


def test_yield_and_scrap(win):
    y = page(win, "YieldScrapPage")
    y.required()
    assert "1053" in text(y)
    y.yield_()
    assert "90" in text(y)
    y.wastage()
    assert "Total wastage:    15" in text(y)
    y.percent.setText("5")
    y.required()
    assert "1053" in text(y)


def test_purchasing(win):
    p = page(win, "PurchasingPage")
    p.simple()
    assert "96 pieces" in text(p)
    build_product(win)
    select(p.product, "PROD-A")
    p.purchase_unit.setText("carton")
    p.stock_unit.setText("box")
    p.need.setText("41")
    p.supplier_order()
    assert "3 carton" in text(p)
    p.save_rule()
    assert len(win.state.config.purchasing) == 1 and p.rules.count() == 2


def test_bulk_import_and_export(win, tmp_path):
    build_product(win)
    src = tmp_path / "in.csv"
    src.write_text("Product,Quantity,From Unit,To Unit\nPROD-A,850,carton,pallet\nx,1,kg,g\ny,1,kg,m\n")
    b = page(win, "BulkPage")
    b.path.setText(str(src))
    b.run()
    assert b.table.rowCount() == 3
    assert "2 succeeded, 1 failed" in b.summary.text()
    assert b.table.item(2, 1).text() == "ERROR" and "INCOMPATIBLE_UNITS" in b.table.item(2, 4).text()
    assert b.export_ok.isEnabled() and b.export_bad.isEnabled()
    b.path.setText(str(tmp_path / "missing.csv"))
    b.run()
    assert "FILE_NOT_FOUND" in text(b)


def test_validation_report(win):
    v = page(win, "ValidationReportPage")
    v.run()
    assert "Nothing to validate" in text(v)
    bad = Product("BAD", "Bad")
    bad.add_level(PackagingLevel("piece", 1))
    bad.add_level(PackagingLevel("pallet", 5, "carton"))
    win.state.config.add_product(bad)
    build_product(win)
    v.run()
    out = text(v)
    assert "Product BAD: 1 problem" in out and "MISSING_LEVEL" in out and "Product PROD-A: OK" in out


def test_save_and_load_configuration(win, tmp_path):
    build_product(win)
    win.state.registry.register_unit("bag", "mass", "kg", 25)
    win.state.notify()
    path = str(tmp_path / "cfg.json")
    assert win.state.save(path) == path and not win.state.dirty
    other = AppState()
    other.load(path)
    assert other.registry.has_unit("bag") and "PROD-A" in other.config.products
    dash = page(win, "DashboardPage")
    assert "1 custom unit(s)" in dash.summary.text() and "1 product(s)" in dash.summary.text()
