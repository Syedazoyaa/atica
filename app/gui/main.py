"""ATICA Desktop entry point.

Run from the repository root (with the library importable, e.g. ``pip install -e .``)::

    pip install PySide6
    python app/gui/main.py
"""
from __future__ import annotations

import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:  # allow running straight from a source checkout
    import atica  # noqa: F401
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from atica.exceptions import AticaError  # noqa: E402
from windows.main_window import MainWindow  # noqa: E402
from windows.state import AppState  # noqa: E402


def load_style(app: QApplication) -> None:
    path = os.path.join(HERE, "resources", "style.qss")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())
    except OSError:
        pass  # cosmetic only


def build_window(restore: bool = True):
    state = AppState()
    warning = None
    auto = state.autosave_path()
    if restore and os.path.exists(auto):
        try:
            state.load(auto)
        except AticaError as exc:
            warning = "Your last session could not be restored:\n%s\n\nStarting with an empty configuration." % exc.message
    return state, MainWindow(state), warning


def main() -> int:
    logging.basicConfig(filename=os.path.join(os.path.expanduser("~"), ".atica_gui.log"), level=logging.WARNING)
    QCoreApplication.setOrganizationName("ATICA")
    QCoreApplication.setApplicationName("ATICA Desktop")
    app = QApplication(sys.argv)
    load_style(app)
    state, window, warning = build_window()
    window.show()
    if warning:
        QMessageBox.warning(window, "ATICA", warning)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
