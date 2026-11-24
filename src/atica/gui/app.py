"""Application entry point: ``atica-gui`` (console script), ``python -m atica`` and :func:`main`.

Qt is imported lazily inside the functions below, so importing this module never starts Qt or opens a
window, and a missing/broken Qt installation produces a readable message instead of a traceback.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List, Optional, Sequence

from atica.version import __version__

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow
    from .services import AppState

_USAGE = (
    """\
ATICA %s - manufacturing calculations (desktop application)

usage: atica-gui [--version] [--check] [--help]

  --version   print the version and exit
  --check     start the application, create the main window, then exit (installation self-test)
"""
    % __version__
)


def create_application(argv: Optional[Sequence[str]] = None) -> QApplication:
    """Create (or reuse) the ``QApplication`` and apply the ATICA name, icon and stylesheet."""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .styles import LIGHT, build_stylesheet
    from .utils.fonts import apply_application_font, register_fonts
    from .utils.icons import logo_pixmap

    QCoreApplication.setOrganizationName("ATICA")
    QCoreApplication.setApplicationName("ATICA")
    QCoreApplication.setApplicationVersion(__version__)
    app = QApplication.instance() or QApplication(list(argv) if argv is not None else sys.argv)
    assert isinstance(app, QApplication)
    # IBM Plex Sans ships inside the package: register it before the stylesheet names it
    app.setProperty("atica.fonts_loaded", register_fonts())
    apply_application_font(app)
    app.setStyleSheet(build_stylesheet(LIGHT))
    app.setWindowIcon(QIcon(logo_pixmap(64)))
    return app


def _setup_logging() -> None:
    from PySide6.QtCore import QStandardPaths

    from .utils.errors import setup_logging

    setup_logging(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))


def build_window(state: Optional[AppState] = None) -> MainWindow:
    """Create the main window with the stored settings applied."""
    from .main_window import MainWindow
    from .services import AppState
    from .services.settings_store import load_settings

    state = state or AppState()
    load_settings(state)
    return MainWindow(state)


def _install_excepthook() -> None:
    """Uncaught errors in Qt callbacks: log them and tell the user plainly - never show a traceback."""
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .utils.errors import describe

    def hook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
        friendly = describe(exc)
        if QApplication.instance() is not None:
            QMessageBox.warning(None, "ATICA", "%s\n\n%s" % (friendly.message, friendly.hint or ""))

    sys.excepthook = hook


def main(argv: Optional[List[str]] = None) -> int:
    """Start the desktop application and return its exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args:
        print("ATICA " + __version__)
        return 0
    if "--help" in args or "-h" in args:
        print(_USAGE)
        return 0
    unknown = [a for a in args if a not in ("--check",)]
    if unknown:
        print("atica-gui: unknown option %s\n\n%s" % (unknown[0], _USAGE), file=sys.stderr)
        return 2
    try:
        import PySide6  # noqa: F401
    except ImportError as exc:
        print(
            "ATICA could not load its desktop interface (PySide6): %s\n"
            "Reinstall with:  pip install --force-reinstall atica" % exc,
            file=sys.stderr,
        )
        return 1
    try:
        app = create_application(["atica-gui"])
        _setup_logging()
        if not app.property("atica.fonts_loaded"):
            from .utils.errors import LOG

            LOG.warning("The bundled IBM Plex Sans font could not be loaded; using a system font.")
        _install_excepthook()
        window = build_window()
        window.show()
        if "--check" in args:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, app.quit)
        return int(app.exec())
    except Exception as exc:
        print("ATICA could not start: %s" % exc, file=sys.stderr)
        try:
            from .utils.errors import LOG

            LOG.error("Startup failure", exc_info=exc)
        except Exception:
            pass
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
