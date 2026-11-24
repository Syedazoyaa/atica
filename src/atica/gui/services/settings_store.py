"""User settings persisted with Qt's ``QSettings`` (platform-appropriate location, no hard-coded paths)."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from .state import AppState

_DEFAULTS = {"display_places": 6, "precision": 50}


def _settings() -> QSettings:
    return QSettings("ATICA", "ATICA")


def load_settings(state: AppState) -> None:
    """Copy stored settings into ``state``; invalid or missing values fall back to defaults."""
    store = _settings()
    for key, default in _DEFAULTS.items():
        try:
            value = int(store.value(key, default))
        except (TypeError, ValueError):
            value = default
        setattr(state, key, value)
    state.display_places = min(max(state.display_places, 0), 30)
    state.precision = min(max(state.precision, 10), 200)


def save_settings(state: AppState) -> None:
    store = _settings()
    store.setValue("display_places", state.display_places)
    store.setValue("precision", state.precision)
    store.sync()
