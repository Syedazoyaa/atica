"""Editable table (:class:`TableEditor`) used for BOM lines, packaging levels and stock lists."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services import AppState
from ..utils.icons import icon
from .forms import UnitCombo


class TableEditor(QWidget):
    """A small spreadsheet-like editor.

    ``unit_columns`` maps a column index to the measurement categories offered in that column's
    unit selector.  ``readonly_first`` locks the given column of row 0 to a fixed text (used for the base
    packaging level, which always contains exactly 1).
    """

    changed = Signal()

    def __init__(
        self,
        columns: Sequence[str],
        state: AppState,
        *,
        unit_columns: Optional[Dict[int, Sequence[str]]] = None,
        locked_first_cell: Optional[tuple[int, str]] = None,
        placeholders: Optional[Sequence[str]] = None,
        min_height: int = 140,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._unit_columns = dict(unit_columns or {})
        self._locked = locked_first_cell
        self._placeholders = list(placeholders or [])
        self._table = QTableWidget(0, len(columns))
        self._table.setHorizontalHeaderLabels(list(columns))
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setMinimumHeight(min_height)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        self._table.itemChanged.connect(lambda _i: self.changed.emit())

        add = QPushButton(" Add row")
        add.setIcon(icon("plus", "#102B50", 16))
        add.clicked.connect(lambda: self.add_row())
        remove = QPushButton(" Remove selected")
        remove.setIcon(icon("trash", "#102B50", 16))
        remove.clicked.connect(self.remove_selected)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(add)
        bar.addWidget(remove)
        bar.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._table)
        layout.addLayout(bar)

    # ------------------------------------------------------------------ editing
    def add_row(self, cells: Optional[Sequence[str]] = None) -> int:
        row = self._table.rowCount()
        self._table.insertRow(row)
        cells = list(cells or [])
        for col in range(self._table.columnCount()):
            text = cells[col] if col < len(cells) else ""
            if col in self._unit_columns:
                combo = UnitCombo(self._state, self._unit_columns[col], compact=True)
                if text:
                    combo.set_symbol(text)
                combo.currentIndexChanged.connect(lambda _i: self.changed.emit())
                self._table.setCellWidget(row, col, combo)
            else:
                item = QTableWidgetItem(text)
                if row == 0 and self._locked and self._locked[0] == col:
                    item.setText(self._locked[1])
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)
        self._table.setCurrentCell(row, 0)
        self.changed.emit()
        return row

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()}, reverse=True) or (
            [self._table.rowCount() - 1] if self._table.rowCount() else []
        )
        for row in rows:
            self._table.removeRow(row)
        if self._locked and self._table.rowCount():
            item = self._table.item(0, self._locked[0])
            if item is not None:
                item.setText(self._locked[1])
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.changed.emit()

    def clear(self) -> None:
        self._table.setRowCount(0)
        self.changed.emit()

    def rows(self) -> List[List[str]]:
        out: List[List[str]] = []
        for r in range(self._table.rowCount()):
            row: List[str] = []
            for c in range(self._table.columnCount()):
                widget = self._table.cellWidget(r, c)
                if isinstance(widget, UnitCombo):
                    row.append(widget.symbol())
                else:
                    item = self._table.item(r, c)
                    row.append(item.text().strip() if item else "")
            out.append(row)
        return out

    def set_rows(self, rows: Sequence[Sequence[str]]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for cells in rows:
            self.add_row(cells)
        self._table.blockSignals(False)
        self.changed.emit()

    def refresh_units(self) -> None:
        """Reload the unit lists (e.g. after a custom unit was defined). Does not emit ``changed``."""
        was_blocked = self.blockSignals(True)
        try:
            for r in range(self._table.rowCount()):
                for c in self._unit_columns:
                    widget = self._table.cellWidget(r, c)
                    if isinstance(widget, UnitCombo):
                        widget.refresh()
        finally:
            self.blockSignals(was_blocked)

    def row_count(self) -> int:
        return self._table.rowCount()
