"""Reusable widgets and helpers for the ATICA desktop app.

The GUI contains **no calculation logic**: every page calls the public ATICA API
and only formats what it returns.
"""
from __future__ import annotations

import functools
import logging
from typing import Callable, Iterable, Optional

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QComboBox, QPlainTextEdit

from atica.exceptions import AticaError
from atica.results import CalculationResult
from atica.validation import ValidationResult

log = logging.getLogger("atica.gui")

ROUNDING_CHOICES = [
    ("No rounding", "none"),
    ("Round half up", "half_up"),
    ("Round half even", "half_even"),
    ("Round down", "down"),
    ("Round up", "up"),
    ("Ceiling to whole package", "ceiling_package"),
    ("Floor to whole package", "floor_package"),
]


def friendly_error(exc: BaseException) -> str:
    """Readable text for users; unexpected errors are logged, never shown as stack traces."""
    if isinstance(exc, AticaError):
        return "%s\n\n(code: %s)" % (exc.message, exc.code)
    log.exception("Unexpected error", exc_info=exc)
    return "Something unexpected went wrong. Please check your input and try again."


class ResultBox(QPlainTextEdit):
    """Read-only area that shows a result, an error or a validation report."""

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setPlaceholderText("Results appear here.")
        self.setMinimumHeight(140)

    def show_text(self, text: str) -> None:
        self.setProperty("state", "ok")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPlainText(text)

    def show_error(self, text: str) -> None:
        self.setProperty("state", "error")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPlainText("Could not calculate\n\n" + text)

    def show_validation(self, result: ValidationResult, ok_text: str = "No problems found.") -> None:
        if result.valid and not result.warnings:
            self.show_text(ok_text)
            return
        lines = []
        for e in result.errors:
            lines.append("ERROR   [%s] %s" % (e.code, e.message))
        for w in result.warnings:
            lines.append("WARNING [%s] %s" % (w.code, w.message))
        (self.show_error if result.errors else self.show_text)("\n".join(lines))


def format_calc(result: CalculationResult, extra: Optional[Iterable[str]] = None) -> str:
    lines = ["Result:   %s" % result.display()]
    if result.input_quantity is not None:
        unit = " " + result.input_unit if result.input_unit else ""
        lines.append("Input:    %s%s" % (result.to_dict()["input_quantity"], unit))
    if result.formula:
        lines.append("Formula:  %s" % result.formula)
    if result.rounding_policy.value != "none":
        lines.append("Rounding: %s" % result.rounding_policy.value)
    for key, value in result.to_dict()["metadata"].items():
        if isinstance(value, (str, int)) and key not in ("category",):
            lines.append("%-9s %s" % (key.replace("_", " ") + ":", value))
    lines.extend("Note:     " + w for w in result.warnings)
    if extra:
        lines.extend(extra)
    return "\n".join(lines)


def guarded(attr: str = "result") -> Callable:
    """Decorator for button slots: show friendly errors in ``self.<attr>`` instead of crashing."""

    def decorate(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *_ignored):
            box: ResultBox = getattr(self, attr)
            try:
                method(self)
            except Exception as exc:  # noqa: BLE001 - UI boundary: translate every error
                box.show_error(friendly_error(exc))

        return wrapper

    return decorate


def fill_combo(combo: QComboBox, items: Iterable[tuple], keep_selection: bool = True) -> None:
    """Fill ``combo`` with ``(label, data)`` pairs, keeping the current choice if still present."""
    current = combo.currentData() if keep_selection else None
    combo.blockSignals(True)
    combo.clear()
    for label, data in items:
        combo.addItem(label, data)
    idx = combo.findData(current) if current is not None else -1
    combo.setCurrentIndex(idx if idx >= 0 else 0)
    combo.blockSignals(False)


def rounding_combo() -> QComboBox:
    combo = QComboBox()
    for label, value in ROUNDING_CHOICES:
        combo.addItem(label, value)
    return combo
