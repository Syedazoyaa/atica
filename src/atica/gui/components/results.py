"""Result presentation: headline, details, tables, warnings, errors, copy and export."""

from __future__ import annotations

import importlib.util
import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..controllers import data_tools
from ..models import Outcome
from ..utils.errors import FriendlyError, guard
from ..utils.icons import icon
from .basics import Banner, label


class ResultPanel(QWidget):
    """Shows the outcome (or the error) of the last calculation; offers *Copy* and *Export*."""

    exported = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._outcome: Optional[Outcome] = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        holder.setObjectName("content")
        self._layout = QVBoxLayout(holder)
        self._layout.setContentsMargins(0, 0, 6, 0)
        self._layout.setSpacing(12)
        scroll.setWidget(holder)
        outer.addWidget(scroll, 1)

        self._empty = label(
            "Enter your values and press Calculate.\nThe result appears here.", "muted", wrap=True
        )
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setMargin(48)
        self._error = Banner("error")
        self._info = Banner("success")
        self._head = QFrame()
        self._head.setObjectName("resultHeadline")
        head_layout = QVBoxLayout(self._head)
        head_layout.setContentsMargins(18, 14, 18, 14)
        head_layout.setSpacing(2)
        self._head_title = label("", "headlineTitle")
        self._headline = label("", "headline", wrap=True)
        self._headline.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        head_layout.addWidget(self._head_title)
        head_layout.addWidget(self._headline)
        self._details = QWidget()
        self._grid = QGridLayout(self._details)
        self._grid.setContentsMargins(2, 0, 2, 0)
        self._grid.setHorizontalSpacing(18)
        self._grid.setVerticalSpacing(7)
        self._grid.setColumnStretch(1, 1)
        self._tables = QVBoxLayout()
        self._tables.setSpacing(10)
        self._notes = QVBoxLayout()
        self._notes.setSpacing(8)
        self._actions = QWidget()
        actions = QHBoxLayout(self._actions)
        actions.setContentsMargins(0, 0, 0, 0)
        copy = QPushButton(" Copy result")
        copy.setIcon(icon("copy", size=16))
        copy.clicked.connect(self.copy)
        export = QPushButton(" Export…")
        export.setIcon(icon("export", size=16))
        export.clicked.connect(self.export)
        actions.addWidget(copy)
        actions.addWidget(export)
        actions.addStretch(1)
        for w in (self._empty, self._error, self._info, self._head, self._details):
            self._layout.addWidget(w)
        self._layout.addLayout(self._tables)
        self._layout.addLayout(self._notes)
        self._layout.addWidget(self._actions)
        self._layout.addStretch(1)
        self.clear()

    # ------------------------------------------------------------------- states
    def clear(self) -> None:
        self._outcome = None
        for w in (self._error, self._info, self._head, self._details, self._actions):
            w.hide()
        self._empty.show()
        self._reset_dynamic()

    def _reset_dynamic(self) -> None:
        for layout in (self._tables, self._notes):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_error(self, err: FriendlyError) -> None:
        self._outcome = None
        for w in (self._info, self._head, self._details, self._actions, self._empty):
            w.hide()
        self._reset_dynamic()
        self._error.show_message(
            err.title + ": " + err.message if not err.unexpected else err.title,
            err.hint or (err.message if err.unexpected else ""),
        )

    def show_outcome(self, outcome: Outcome) -> None:
        self._outcome = outcome
        self._empty.hide()
        self._error.hide()
        self._info.hide()
        self._reset_dynamic()
        self._head_title.setText(outcome.title.upper())
        self._headline.setText(outcome.headline)
        self._head.show()
        for row, (name, value) in enumerate(outcome.rows):
            key = label(name, "muted")
            val = label(value, "fieldLabel")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._grid.addWidget(key, row, 0)
            self._grid.addWidget(val, row, 1)
        self._details.setVisible(bool(outcome.rows))
        for table in outcome.tables:
            self._tables.addWidget(label(table.title, "sectionLabel"))
            self._tables.addWidget(self._make_table(table.columns, table.rows))
        for text in outcome.warnings:
            banner = Banner("warning")
            banner.show_message("Warning", text)
            self._notes.addWidget(banner)
        notes = []
        if outcome.formula:
            notes.append("Formula: " + outcome.formula)
        notes += ["Assumption: " + a for a in outcome.assumptions]
        for text in notes:
            self._notes.addWidget(label(text, "muted", wrap=True))
        self._actions.show()

    @staticmethod
    def _make_table(columns, rows) -> QTableWidget:
        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(list(columns))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                item = QTableWidgetItem(text)
                if c > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(r, c, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(34)
        height = header.height() + 34 * max(len(rows), 1) + 6
        table.setFixedHeight(min(height + 24, 420))
        return table

    # ------------------------------------------------------------------ actions
    @property
    def outcome(self) -> Optional[Outcome]:
        return self._outcome

    def copy(self) -> None:
        if self._outcome is not None:
            QGuiApplication.clipboard().setText(self._outcome.as_text())
            self._info.show_message("Copied to the clipboard.")

    def export(self) -> None:
        if self._outcome is None:
            return
        filters = "CSV file (*.csv)"
        if importlib.util.find_spec("openpyxl") is not None:
            filters += ";;Excel workbook (*.xlsx)"
        path, chosen = QFileDialog.getSaveFileName(self, "Export result", "atica-result", filters)
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".xlsx" if "xlsx" in chosen else ".csv"
        outcome = self._outcome
        # the file dialog already asked about overwriting
        saved, err = guard(lambda: data_tools.export_outcome(outcome, path, overwrite=True))
        if err:
            self.show_error(err)
            self._outcome = outcome
        else:
            self._info.show_message("Saved", saved or path)
            self.exported.emit(path)
