"""Bulk import and validation/report pages."""
from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from atica.exceptions import AticaError
from atica.io import BulkResult, export_errors, export_results, process_file
from atica.validation import ValidationResult

from widgets.common import ResultBox, friendly_error, guarded
from .pages_basic import Page
from .state import AppState


class BulkPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self.bulk: Optional[BulkResult] = None
        lay = QVBoxLayout(self)
        lay.addWidget(self.title(
            "Bulk File Import",
            "CSV or Excel with columns Product, Quantity, From Unit, To Unit. Packaging rows use the products configured in this app.",
        ))
        row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("Choose a .csv or .xlsx file…")
        browse, run = QPushButton("Browse…"), QPushButton("Process file")
        run.setObjectName("primary")
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        row.addWidget(run)
        lay.addLayout(row)
        self.partial = QCheckBox("Allow partial (fractional) package quantities")
        lay.addWidget(self.partial)
        self.summary = QLabel("No file processed yet.")
        lay.addWidget(self.summary)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Row", "Status", "Input", "Result", "Problem"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lay.addWidget(self.table, 1)
        row2 = QHBoxLayout()
        self.export_ok, self.export_bad = QPushButton("Export results…"), QPushButton("Export errors…")
        self.export_ok.setEnabled(False)
        self.export_bad.setEnabled(False)
        row2.addWidget(self.export_ok)
        row2.addWidget(self.export_bad)
        row2.addStretch(1)
        lay.addLayout(row2)
        self.result = ResultBox()
        self.result.setMaximumHeight(90)
        lay.addWidget(self.result)
        browse.clicked.connect(self.browse)
        run.clicked.connect(self.run)
        self.export_ok.clicked.connect(lambda: self.export(False))
        self.export_bad.clicked.connect(lambda: self.export(True))

    def browse(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open data file", "", "Data files (*.csv *.xlsx);;All files (*)")
        if name:
            self.path.setText(name)

    @guarded()
    def run(self) -> None:
        self.bulk = process_file(
            self.path.text().strip(),
            products=self.state.config.products,
            registry=self.state.registry,
            allow_partial=self.partial.isChecked(),
        )
        s = self.bulk.summary
        self.summary.setText("%d row(s): %d succeeded, %d failed." % (s["total_rows"], s["succeeded"], s["failed"]))
        self.table.setRowCount(len(self.bulk.rows))
        bad = QColor("#b3261e")
        for r, row in enumerate(self.bulk.rows):
            o = row.output
            if o.get("operation") == "breakdown":
                res = "%s full %s + %s (need %s)" % (o["full_packages"], o["result_unit"], o["remaining_quantity"], o["packages_required"])
            elif o:
                res = "%s %s" % (o["result_quantity"], o["result_unit"])
            else:
                res = ""
            problem = "; ".join("[%s] %s" % (e["code"], e["message"]) for e in row.errors) or "; ".join(row.warnings)
            vals = [str(row.row_number), "OK" if row.ok else "ERROR", " | ".join(str(v) for v in row.original.values()), res, problem]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if not row.ok:
                    item.setForeground(bad)
                self.table.setItem(r, c, item)
        self.export_ok.setEnabled(s["succeeded"] > 0)
        self.export_bad.setEnabled(s["failed"] > 0)
        self.result.show_text("Processed %s. Original data is unchanged." % self.path.text().strip())

    @guarded()
    def export(self, errors: bool) -> None:
        if self.bulk is None:
            return
        name, _ = QFileDialog.getSaveFileName(self, "Export", "errors.csv" if errors else "results.csv", "CSV (*.csv);;Excel (*.xlsx)")
        if not name:
            return
        fn = export_errors if errors else export_results
        out = fn(self.bulk, name, overwrite=True)  # the save dialog already asked about replacing
        self.result.show_text("Saved %s" % out)


class ValidationReportPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Validation & Reports", "Checks every product hierarchy, custom unit and purchasing rule in the current configuration."))
        row = QHBoxLayout()
        run, save = QPushButton("Run validation"), QPushButton("Save report…")
        run.setObjectName("primary")
        row.addWidget(run)
        row.addWidget(save)
        row.addStretch(1)
        lay.addLayout(row)
        self.result = ResultBox()
        lay.addWidget(self.result, 1)
        self.report: dict = {}
        run.clicked.connect(self.run)
        save.clicked.connect(self.save)

    @guarded()
    def run(self) -> None:
        cfg = self.state.config
        report = {"products": {}, "units": {}, "purchasing": []}
        lines = []
        for p in self.state.products():
            v = p.validate() if p.has_levels else _draft(p)
            report["products"][p.product_id] = v.to_dict()
            lines.append("Product %s: %s" % (p.product_id, "OK" if v.valid else "%d problem(s)" % len(v.errors)))
            lines.extend("    [%s] %s" % (e.code, e.message) for e in v.errors)
            lines.extend("    (warning) %s" % w.message for w in v.warnings)
        try:
            cfg.registry.copy()
            report["units"] = {"valid": True, "custom_units": len(cfg.registry.list_custom_units())}
            if cfg.registry.list_custom_units():
                lines.append("Custom units: OK (%d)" % len(cfg.registry.list_custom_units()))
        except AticaError as exc:
            report["units"] = {"valid": False, "error": exc.to_dict()}
            lines.append("Custom units: [%s] %s" % (exc.code, exc.message))
        for rule in cfg.purchasing:
            product = cfg.products.get(rule.product_id)
            try:
                ratio = rule.stock_per_purchase_unit(product=product, registry=cfg.registry)
                report["purchasing"].append({"supplier": rule.supplier_id, "product": rule.product_id, "valid": True})
                lines.append("Purchasing %s/%s: OK (1 %s = %s %s)" % (rule.supplier_id, rule.product_id, rule.purchase_unit, ratio.normalize(), rule.stock_unit))
            except AticaError as exc:
                report["purchasing"].append({"supplier": rule.supplier_id, "product": rule.product_id, "valid": False, "error": exc.to_dict()})
                lines.append("Purchasing %s/%s: [%s] %s" % (rule.supplier_id, rule.product_id, exc.code, exc.message))
        self.report = report
        if not lines:
            lines.append("Nothing to validate yet. Add products, units or purchasing rules.")
        self.result.show_text("\n".join(lines))

    @guarded()
    def save(self) -> None:
        if not self.report:
            self.run()
        name, _ = QFileDialog.getSaveFileName(self, "Save report", "atica_report.json", "JSON (*.json)")
        if name:
            with open(name, "w", encoding="utf-8") as fh:
                json.dump(self.report, fh, indent=2)
            self.result.show_text("Report saved to %s" % name)


def _draft(product) -> ValidationResult:
    result = ValidationResult()
    result.add_warning("NO_LEVELS", "levels", "Product %s has no packaging levels yet." % product.product_id)
    return result
