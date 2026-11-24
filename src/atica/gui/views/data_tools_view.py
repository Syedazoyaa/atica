"""Data Tools screen: CSV/Excel import and export through the integrations package."""

from __future__ import annotations

import importlib.util
import os
from typing import Optional

from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from atica.integrations import ConversionReport

from ..components import Card, FormPanel, label, rounding_fields
from ..components.basics import Banner
from ..controllers import data_tools
from ..services import AppState
from ..utils.errors import guard
from ..utils.icons import icon
from .base import ToolView

_EXCEL = importlib.util.find_spec("openpyxl") is not None


def _file_filter(kind: str) -> str:
    """Files that can be **read**: CSV and Excel workbooks (``.xlsm`` is read, never written)."""
    base = "*.csv *.xlsx *.xlsm" if _EXCEL else "*.csv"
    return "%s (%s)" % (kind, base)


def _export_filter() -> str:
    """Files that can be **written**: CSV, and ``.xlsx`` when openpyxl is installed (no macro-enabled workbooks)."""
    return "CSV file (*.csv);;Excel workbook (*.xlsx)" if _EXCEL else "CSV file (*.csv)"


class DataToolsView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Data Tools",
            "Convert a whole file of quantities at once, or load a bill of materials. Files are only read; nothing is overwritten unless you confirm.",
            state,
            parent,
        )
        self._report: Optional[ConversionReport] = None
        self._path: Optional[str] = None
        self.add_scrolling_tab("Convert a file", self._build_convert())
        self.add_scrolling_tab("Import a BOM", self._build_bom())

    # --------------------------------------------------------------- converter
    def _build_convert(self) -> QWidget:
        card = Card(
            "Unit conversion file",
            "Columns needed: value, from_unit, to_unit. Other columns are kept. Rows with problems are listed with the reason, never skipped silently.",
        )
        self._file_label = label("No file chosen.", "muted", wrap=True)
        choose = QPushButton(" Choose file…")
        choose.setIcon(icon("folder", size=16))
        choose.clicked.connect(self._choose_convert)
        self._form = FormPanel(rounding_fields(), self.state)
        self._convert_button = QPushButton("Convert file")
        self._convert_button.setObjectName("primary")
        self._convert_button.setEnabled(False)
        self._convert_button.clicked.connect(self._convert)
        self._banner = Banner("error")
        self._ok_banner = Banner("success")
        self._table = QTableWidget(0, 0)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(220)
        self._export_results = QPushButton(" Export converted rows…")
        self._export_results.setIcon(icon("export", size=16))
        self._export_results.clicked.connect(lambda: self._export(errors=False))
        self._export_errors = QPushButton(" Export problem rows…")
        self._export_errors.setIcon(icon("export", size=16))
        self._export_errors.clicked.connect(lambda: self._export(errors=True))
        for b in (self._export_results, self._export_errors):
            b.setEnabled(False)
        row = QHBoxLayout()
        row.addWidget(choose)
        row.addWidget(self._file_label, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self._export_results)
        buttons.addWidget(self._export_errors)
        buttons.addStretch(1)
        buttons.addWidget(self._convert_button)
        card.body.addLayout(row)
        card.body.addWidget(self._form)
        card.body.addWidget(self._banner)
        card.body.addWidget(self._ok_banner)
        card.body.addWidget(self._table, 1)
        card.body.addLayout(buttons)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(2, 2, 2, 14)
        lay.addWidget(card)
        return holder

    def _choose_convert(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file", "", _file_filter("Data files"))
        if path:
            self.set_file(path)

    def set_file(self, path: str) -> None:
        self._path = path
        self._file_label.setText(path)
        self._convert_button.setEnabled(True)

    def _convert(self) -> None:
        self._banner.hide()
        self._ok_banner.hide()
        path = self._path
        if not path:
            return
        report, err = guard(lambda: data_tools.convert_file(path, self._form.values(), self.state))
        if err or report is None:
            self._report = None
            self._table.setRowCount(0)
            if err:
                self._banner.show_message(err.title, err.message + ("\n" + err.hint if err.hint else ""))
            for b in (self._export_results, self._export_errors):
                b.setEnabled(False)
            return
        self._report = report
        self._show_report(report)
        self.state.record(
            "Data tools",
            "Converted %d row(s) from %s (%d problem(s))"
            % (report.succeeded, os.path.basename(path), report.failed),
        )

    def _show_report(self, report: ConversionReport) -> None:
        columns = ["Row", "Status", *report.fieldnames]
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.setRowCount(report.succeeded + report.failed)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        r = 0
        for number, data in zip(report.row_numbers, report.rows):  # real source row numbers
            self._table.setItem(r, 0, QTableWidgetItem(str(number)))
            self._table.setItem(r, 1, QTableWidgetItem("Converted"))
            for c, name in enumerate(report.fieldnames):
                self._table.setItem(r, 2 + c, QTableWidgetItem(data.get(name, "")))
            r += 1
        for err in report.errors:
            self._table.setItem(r, 0, QTableWidgetItem(str(err.row_number)))
            self._table.setItem(
                r, 1, QTableWidgetItem("Problem: " + err.message + (" " + err.hint if err.hint else ""))
            )
            r += 1
        summary = "%d of %d row(s) converted" % (report.succeeded, report.total_rows)
        if report.failed:
            self._banner.show_message(
                "%s - %d row(s) need attention" % (summary, report.failed),
                "See the 'Problem' rows below. Row numbers refer to the file.",
            )
        else:
            self._ok_banner.show_message(summary)
        self._export_results.setEnabled(report.succeeded > 0)
        self._export_errors.setEnabled(report.failed > 0)

    def _export(self, *, errors: bool) -> None:
        report = self._report
        if report is None:
            return
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export", "atica-errors" if errors else "atica-converted", _export_filter()
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".xlsx" if "xlsx" in chosen else ".csv"
        fn = data_tools.export_errors if errors else data_tools.export_report
        saved, err = guard(
            lambda: fn(report, path, overwrite=True)
        )  # the save dialog already confirmed overwriting
        self._ok_banner.hide()
        if err:
            self._banner.show_message(err.title, err.message + ("\n" + err.hint if err.hint else ""))
        else:
            self._ok_banner.show_message("Saved", saved or path)

    # --------------------------------------------------------------------- BOM
    def _build_bom(self) -> QWidget:
        card = Card(
            "Import a bill of materials",
            "Columns needed: material_id, quantity_per_unit, unit. Optional: wastage_percent, name. The imported BOM is used on the Materials and BOM and Production screens.",
        )
        choose = QPushButton(" Choose BOM file…")
        choose.setIcon(icon("folder", size=16))
        choose.clicked.connect(self._choose_bom)
        self._bom_error = Banner("error")
        self._bom_ok = Banner("success")
        card.body.addWidget(choose)
        card.body.addWidget(self._bom_error)
        card.body.addWidget(self._bom_ok)
        card.body.addStretch(1)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(2, 2, 2, 14)
        lay.addWidget(card)
        lay.addStretch(1)
        return holder

    def _choose_bom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a BOM file", "", _file_filter("BOM files"))
        if path:
            self.import_bom(path)

    def import_bom(self, path: str) -> None:
        self._bom_error.hide()
        self._bom_ok.hide()
        outcome, err = guard(lambda: data_tools.import_bom(path, self.state))
        if err or outcome is None:
            if err:
                self._bom_error.show_message(err.title, err.message + ("\n" + err.hint if err.hint else ""))
            return
        self._bom_ok.show_message(outcome.headline, "Open Materials and BOM to calculate with it.")
        self.state.record("Data tools", outcome.summary)
