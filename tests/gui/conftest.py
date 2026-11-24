import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from atica.gui.app import create_application

    return create_application(["atica-test"])


@pytest.fixture
def state():
    from atica.gui.services import AppState
    from atica.packaging import PackagingLevel, Product

    s = AppState()
    s.product = Product(
        "P001",
        "Product A",
        [PackagingLevel("piece"), PackagingLevel("box", 12, "piece"), PackagingLevel("carton", 20, "box")],
    )
    s.bom_rows = [["steel", "0.25", "kg", "0"], ["paint", "40", "mL", "10"], ["screws", "4", "piece", "0"]]
    return s


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from atica.gui.main_window import MainWindow
    from atica.gui.services import AppState

    w = MainWindow(AppState())
    w.show()
    yield w
    w.close()
