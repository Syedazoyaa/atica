"""Materials and BOM screen."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QPushButton, QWidget

from ..components import CalculatorPanel, TableEditor, label, rounding_fields
from ..components.basics import Banner
from ..controllers import data_tools, materials_calc
from ..models import Field
from ..services import AppState
from ..utils.errors import guard
from ..utils.icons import icon
from .base import ToolView

_MATERIAL_KINDS = ("mass", "volume", "length", "area", "count")
_EXAMPLE_BOM = [["steel", "0.25", "kg", "0"], ["paint", "40", "mL", "10"], ["screws", "4", "piece", "0"]]


class MaterialsView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Materials and BOM",
            "Enter the bill of materials for ONE finished unit, then calculate what a production run needs - or what your stock can make.",
            state,
            parent,
        )
        state.bom_rows = [list(r) for r in _EXAMPLE_BOM]
        self.bom = TableEditor(
            ["Material", "Qty per unit", "Unit", "Wastage %"],
            state,
            unit_columns={2: _MATERIAL_KINDS},
            min_height=170,
        )
        self.bom.set_rows(state.bom_rows)
        self.bom.changed.connect(self._bom_edited)
        self._import_banner = Banner("error")
        import_button = QPushButton(" Import BOM from CSV / Excel…")
        import_button.setIcon(icon("folder", "#102B50", 16))
        import_button.clicked.connect(self._import)
        buttons = QWidget()
        bl = QHBoxLayout(buttons)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(import_button)
        bl.addStretch(1)
        explain = label(
            "Quantity per unit is the NET amount in one finished unit. Wastage % is the share of the material issued that is lost in "
            "processing. Scrap % (below) is the share of units started that are rejected.",
            "muted",
            wrap=True,
        )
        self.requirements = CalculatorPanel(
            "Bill of materials",
            [
                Field(
                    "production_quantity",
                    "Good units to produce",
                    "number",
                    "1000",
                    tooltip="Finished, acceptable units wanted.",
                ),
                Field(
                    "scrap_percent",
                    "Scrap %",
                    "number",
                    "0",
                    suffix="%",
                    tooltip="Share of units started that are rejected (0-100, below 100).",
                ),
                *rounding_fields(),
                Field(
                    "allow_duplicates",
                    "Combine lines with the same material ID",
                    "checkbox",
                    "",
                    advanced=True,
                    tooltip="By default a repeated material ID is an error.",
                ),
            ],
            lambda v: self._run_requirements(v),
            state,
            tool="BOM",
            extra_top=[explain, self.bom, buttons, self._import_banner],
        )
        self.stock = TableEditor(
            ["Material", "Available", "Unit"], state, unit_columns={2: _MATERIAL_KINDS}, min_height=150
        )
        fill = QPushButton(" Fill from BOM")
        fill.setIcon(icon("materials", "#102B50", 16))
        fill.clicked.connect(self._fill_stock)
        fill_row = QWidget()
        fl = QHBoxLayout(fill_row)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(fill)
        fl.addStretch(1)
        self.capacity = CalculatorPanel(
            "Production capacity from stock",
            [
                Field("scrap_percent", "Scrap %", "number", "0", suffix="%"),
                Field(
                    "rounding",
                    "Rounding",
                    "choice",
                    "floor",
                    options=rounding_fields()[0].options,
                    tooltip="Default: round down to whole units you can really finish.",
                ),
                Field("places", "Decimal places", "number", "0"),
                Field(
                    "allow_duplicates",
                    "Combine lines with the same material ID",
                    "checkbox",
                    "",
                    advanced=True,
                ),
            ],
            lambda v: self._run_capacity(v),
            state,
            tool="BOM",
            description="Enter the stock on hand for EVERY material; a missing material is never assumed to be zero or unlimited.",
            extra_top=[fill_row, self.stock],
        )
        self.add_tab("Requirements", self.requirements)
        self.add_tab("Capacity from stock", self.capacity)
        state.on_change(self._on_state)

    # ---------------------------------------------------------------- handlers
    def _bom_edited(self) -> None:
        self.state.bom_rows = self.bom.rows()

    def _run_requirements(self, values: Dict[str, Any]):  # type: ignore[no-untyped-def]
        self.state.bom_rows = self.bom.rows()
        return materials_calc.requirements(values, self.state)

    def _run_capacity(self, values: Dict[str, Any]):  # type: ignore[no-untyped-def]
        self.state.bom_rows = self.bom.rows()
        return materials_calc.capacity(values, self.stock.rows(), self.state)

    def _fill_stock(self) -> None:
        self.state.bom_rows = self.bom.rows()
        seen = []
        rows = []
        for row in self.state.bom_rows:
            material, unit = row[0].strip(), row[2]
            if material and material.casefold() not in seen:
                seen.append(material.casefold())
                rows.append([material, "", unit])
        self.stock.set_rows(rows)

    def _import(self) -> None:
        self._import_banner.hide()
        path, _ = QFileDialog.getOpenFileName(self, "Import BOM", "", "BOM files (*.csv *.xlsx *.xlsm)")
        if not path:
            return
        _, err = guard(lambda: data_tools.import_bom(path, self.state))
        if err:
            self._import_banner.show_message(err.title, err.message + ("\n" + err.hint if err.hint else ""))

    def _on_state(self) -> None:
        if self.state.bom_rows != self.bom.rows():
            # the BOM was replaced elsewhere (file import): show it, without echoing it back as an edit
            was_blocked = self.bom.blockSignals(True)
            self.bom.set_rows(self.state.bom_rows)
            self.bom.blockSignals(was_blocked)
        self.requirements.form.refresh_units()
        self.capacity.form.refresh_units()
        self.bom.refresh_units()
        self.stock.refresh_units()
