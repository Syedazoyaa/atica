"""Manufacturing, yield/scrap and purchasing pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from atica.inventory import PurchasingConfig, calculate_purchase_order, calculate_purchase_quantity
from atica.manufacturing import (
    calculate_batches,
    calculate_material_requirement,
    calculate_required_input,
    calculate_wastage,
    calculate_yield,
    evaluate_formula,
)

from widgets.common import ResultBox, fill_combo, format_calc, guarded, rounding_combo
from .pages_basic import Page, unit_items
from .state import AppState


def _tab(form_rows, button_text, slot, result: ResultBox) -> QWidget:
    """A tab holding a form, one button and the shared result box."""
    w = QWidget()
    lay = QVBoxLayout(w)
    form = QFormLayout()
    for label, widget in form_rows:
        form.addRow(label, widget)
    lay.addLayout(form)
    btn = QPushButton(button_text)
    btn.setObjectName("primary")
    btn.clicked.connect(slot)
    lay.addWidget(btn, 0, Qt.AlignLeft)
    lay.addStretch(1)
    return w


class ManufacturingPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title(
            "Manufacturing Calculator",
            "Material for a production target. Rates are fractions: 0.05 means 5 %.",
        ))
        self.result = ResultBox()
        tabs = QTabWidget()
        # --- material requirement
        self.per_unit = QLineEdit("0.5")
        self.qty = QLineEdit("1000")
        self.material_unit = QComboBox()
        self.output_unit = QComboBox()
        self.scrap = QLineEdit()
        self.scrap.setPlaceholderText("optional, e.g. 0.05")
        self.wastage = QLineEdit()
        self.wastage.setPlaceholderText("optional, e.g. 0.02")
        self.units_rounding = rounding_combo()
        self.rounding = rounding_combo()
        tabs.addTab(_tab(
            [("Material per finished unit", self.per_unit), ("Production target (good units)", self.qty),
             ("Material unit", self.material_unit), ("Show result in", self.output_unit),
             ("Scrap rate", self.scrap), ("Material wastage rate", self.wastage),
             ("Rounding of units started", self.units_rounding), ("Rounding of result", self.rounding)],
            "Calculate material", self.material, self.result), "Material requirement")
        # --- batches
        self.total = QLineEdit("1050")
        self.batch = QLineEdit("100")
        tabs.addTab(_tab([("Total quantity", self.total), ("Batch size", self.batch)],
                         "Calculate batches", self.batches, self.result), "Batches")
        # --- formula
        self.expr = QLineEdit("quantity * per_unit / (1 - scrap)")
        self.vars = QPlainTextEdit("quantity = 1000\nper_unit = 0.5\nscrap = 0.05")
        self.vars.setMaximumHeight(90)
        tabs.addTab(_tab([("Formula", self.expr), ("Variables (name = value)", self.vars)],
                         "Evaluate formula", self.formula, self.result), "Custom formula")
        lay.addWidget(tabs)
        lay.addWidget(self.result, 1)
        self.refresh()

    def refresh(self) -> None:
        items = [("(none)", None)] + unit_items(self.state.registry)
        fill_combo(self.material_unit, items)
        fill_combo(self.output_unit, [("(same as material unit)", None)] + unit_items(self.state.registry))
        idx = self.material_unit.findData("kg")
        if idx >= 0 and self.material_unit.currentIndex() == 0:
            self.material_unit.setCurrentIndex(idx)

    @guarded()
    def material(self) -> None:
        r = calculate_material_requirement(
            self.per_unit.text() or None,
            self.qty.text(),
            self.material_unit.currentData(),
            scrap_rate=self.scrap.text() or None,
            wastage_rate=self.wastage.text() or None,
            units_rounding=self.units_rounding.currentData(),
            rounding=self.rounding.currentData(),
            output_unit=self.output_unit.currentData(),
            registry=self.state.registry,
        )
        self.result.show_text(format_calc(r))

    @guarded()
    def batches(self) -> None:
        b = calculate_batches(self.total.text(), self.batch.text())
        d = b.to_dict()
        self.result.show_text(
            "Full batches:       %s\nLeftover quantity:  %s\nBatches required:   %s (last batch holds %s)"
            % (d["full_batches"], d["remainder"], d["batches_required"], d["last_batch_quantity"])
        )

    @guarded()
    def formula(self) -> None:
        values = {}
        for line in self.vars.toPlainText().splitlines():
            if line.strip():
                name, _, value = line.partition("=")
                values[name.strip()] = value.strip()
        self.result.show_text("Result: %s" % evaluate_formula(self.expr.text(), values))


class YieldScrapPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Yield & Scrap Calculator", "Rates are fractions: 0.05 means 5 %. Leave the percentage empty unless you prefer it."))
        self.result = ResultBox()
        tabs = QTabWidget()
        self.good = QLineEdit("1000")
        self.rate = QLineEdit("0.05")
        self.percent = QLineEdit()
        self.percent.setPlaceholderText("optional, e.g. 5 (instead of rate)")
        self.rounding = rounding_combo()
        self.rounding.setCurrentIndex(4)  # round up: whole units issued
        tabs.addTab(_tab(
            [("Required good output", self.good), ("Scrap rate (fraction)", self.rate),
             ("or scrap percent", self.percent), ("Rounding", self.rounding)],
            "Calculate required input", self.required, self.result), "Required input")
        self.t_in = QLineEdit("1000")
        self.t_good = QLineEdit("900")
        self.t_rework = QLineEdit("50")
        tabs.addTab(_tab([("Total input", self.t_in), ("Good output", self.t_good), ("Reworked units", self.t_rework)],
                         "Calculate yield", self.yield_, self.result), "Yield")
        self.m_in = QLineEdit("100")
        self.m_out = QLineEdit("85")
        self.m_scrap = QLineEdit("5")
        tabs.addTab(_tab([("Material input", self.m_in), ("Material in good output", self.m_out), ("Of which scrapped", self.m_scrap)],
                         "Calculate wastage", self.wastage, self.result), "Wastage")
        lay.addWidget(tabs)
        lay.addWidget(self.result, 1)

    @guarded()
    def required(self) -> None:
        r = calculate_required_input(
            self.good.text(),
            None if self.percent.text().strip() else (self.rate.text() or None),
            scrap_percent=self.percent.text().strip() or None,
            rounding=self.rounding.currentData(),
        )
        self.result.show_text(format_calc(r))

    @guarded()
    def yield_(self) -> None:
        y = calculate_yield(self.t_in.text(), self.t_good.text(), self.t_rework.text() or 0).to_dict()
        self.result.show_text(
            "Yield:    %s %%\nScrap:    %s units (rate %s)\nRework:   %s units (rate %s)"
            % (y["yield_percent"], y["scrap_quantity"], y["scrap_rate"], y["rework_quantity"], y["rework_rate"])
        )

    @guarded()
    def wastage(self) -> None:
        w = calculate_wastage(self.m_in.text(), self.m_out.text(), self.m_scrap.text() or 0).to_dict()
        self.result.show_text(
            "Total wastage:    %s (rate %s)\n  of which scrap:        %s\n  of which process loss: %s"
            % (w["wastage_quantity"], w["wastage_rate"], w["scrap_quantity"], w["process_wastage"])
        )


class PurchasingPage(Page):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        lay = QVBoxLayout(self)
        lay.addWidget(self.title("Purchasing & Inventory Calculator", "Order quantities respecting minimum order quantity and order multiples."))
        self.result = ResultBox()
        tabs = QTabWidget()
        # simple
        self.required = QLineEdit("87")
        self.multiple = QLineEdit("12")
        self.moq = QLineEdit("24")
        self.on_hand = QLineEdit("0")
        tabs.addTab(_tab(
            [("Required quantity", self.required), ("Order multiple", self.multiple),
             ("Minimum order quantity", self.moq), ("Already in stock", self.on_hand)],
            "Recommend order quantity", self.simple, self.result), "Quick calculation")
        # supplier rule
        self.rules = QComboBox()
        self.supplier = QLineEdit("SUP-1")
        self.product = QComboBox()
        self.purchase_unit = QLineEdit("carton")
        self.stock_unit = QLineEdit("box")
        self.s_moq = QLineEdit("0")
        self.s_multiple = QLineEdit("1")
        self.explicit = QLineEdit()
        self.explicit.setPlaceholderText("optional: stock units in one purchase unit")
        self.need = QLineEdit("100")
        self.s_on_hand = QLineEdit("0")
        save = QPushButton("Save this supplier rule")
        save.clicked.connect(self.save_rule)
        self.rules.activated.connect(self.load_rule)
        tab = _tab(
            [("Saved rules", self.rules), ("Supplier", self.supplier), ("Product", self.product),
             ("Purchase unit", self.purchase_unit), ("Stock unit", self.stock_unit),
             ("Minimum order quantity (purchase units)", self.s_moq), ("Order multiple (purchase units)", self.s_multiple),
             ("Explicit conversion", self.explicit), ("Required (stock units)", self.need), ("Already in stock (stock units)", self.s_on_hand)],
            "Calculate purchase order", self.supplier_order, self.result)
        tab.layout().insertWidget(1, save, 0, Qt.AlignLeft)
        tabs.addTab(tab, "Supplier rule")
        lay.addWidget(tabs)
        lay.addWidget(self.result, 1)
        self.refresh()

    def refresh(self) -> None:
        fill_combo(self.product, [("(no product)", None)] + [("%s (%s)" % (p.name, p.product_id), p.product_id) for p in self.state.products()])
        rules = [("(new rule)", None)] + [("%s / %s" % (c.supplier_id, c.product_id), i) for i, c in enumerate(self.state.config.purchasing)]
        fill_combo(self.rules, rules, keep_selection=False)

    def _config(self) -> PurchasingConfig:
        conv = {"stock_units_per_purchase_unit": self.explicit.text().strip()} if self.explicit.text().strip() else None
        return PurchasingConfig(
            self.supplier.text(), self.product.currentData() or self.supplier.text(), self.purchase_unit.text(),
            self.stock_unit.text(), self.s_moq.text() or 0, self.s_multiple.text() or 1, conv,
        )

    @guarded()
    def simple(self) -> None:
        r = calculate_purchase_quantity(
            self.required.text(), self.multiple.text() or 1, self.moq.text() or 0, on_hand=self.on_hand.text() or 0
        )
        extra = ["Constraints applied: %s" % (", ".join(r.metadata["constraints"]) or "none")]
        self.result.show_text(format_calc(r, extra))

    @guarded()
    def supplier_order(self) -> None:
        cfg = self._config()
        product = self.state.config.products.get(self.product.currentData() or "")
        r = calculate_purchase_order(cfg, self.need.text(), on_hand=self.s_on_hand.text() or 0,
                                     product=product, registry=self.state.registry)
        self.result.show_text(format_calc(r))

    @guarded()
    def save_rule(self) -> None:
        cfg = self._config()
        self.state.config.add_purchasing(cfg)
        self.state.notify()
        self.result.show_text("Saved supplier rule %s / %s." % (cfg.supplier_id, cfg.product_id))

    def load_rule(self, _index: int = 0) -> None:
        i = self.rules.currentData()
        if i is None:
            return
        c = self.state.config.purchasing[i]
        self.supplier.setText(c.supplier_id)
        self.purchase_unit.setText(c.purchase_unit)
        self.stock_unit.setText(c.stock_unit)
        self.s_moq.setText(str(c.minimum_order_quantity))
        self.s_multiple.setText(str(c.order_multiple))
        self.explicit.setText(str(c.conversion_configuration.get("stock_units_per_purchase_unit", "")))
        idx = self.product.findData(c.product_id)
        self.product.setCurrentIndex(max(idx, 0))
