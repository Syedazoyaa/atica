"""Unit Converter screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components import CalculatorPanel, UnitCombo, label, rounding_fields
from ..components.basics import Banner
from ..controllers import unit_conversion
from ..models import Field
from ..services import AppState
from ..styles import CURRENT
from ..utils.errors import guard
from ..utils.icons import icon
from .base import ToolView

_CATEGORY_ALL = ("All quantity types", "")


def _use_time_notation(widget: QWidget) -> None:
    assert isinstance(widget, UnitCombo)
    widget.set_notation(unit_conversion.TIME_NOTATION)


class UnitsView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Unit Converter",
            "Convert between standard and custom units. Incompatible units (for example kilograms to metres) are rejected, never guessed.",
            state,
            parent,
        )
        self.convert_panel = self._build_convert()
        self.custom_panel = self._build_custom()
        self.add_tab("Convert", self.convert_panel)
        self.add_tab("Custom units", self.custom_panel)
        state.on_change(self._refresh)
        self._refresh()

    # ---------------------------------------------------------------- converter
    def _build_convert(self) -> CalculatorPanel:
        categories = [_CATEGORY_ALL] + [
            (c.replace("_", " ").capitalize(), c) for c in self.state.registry.categories()
        ]
        fields = [
            Field(
                "category",
                "Quantity type",
                "choice",
                "",
                options=categories,
                tooltip="Limits the unit lists below. Leave on 'All' to see every unit.",
            ),
            Field(
                "value",
                "Value",
                "number",
                "1",
                placeholder="e.g. 25",
                tooltip="The amount to convert. Decimals use a dot: 12.5",
            ),
            Field("from_unit", "From", "unit", "kg"),
            Field("to_unit", "To", "unit", "g"),
            *rounding_fields(),
            Field(
                "interval",
                "Treat as a temperature difference",
                "checkbox",
                "",
                tooltip="For tolerances such as ±5 °C: ignores the temperature offset.",
                advanced=True,
            ),
        ]
        swap = QPushButton(" Swap units")
        swap.setIcon(icon("swap", size=16))
        panel = CalculatorPanel(
            "Convert",
            fields,
            lambda v: unit_conversion.convert(v, self.state),
            self.state,
            tool="Unit converter",
            extra_bottom=[swap],
        )
        form = panel.form
        for key in ("from_unit", "to_unit"):
            _use_time_notation(form.widget(key))

        def on_category() -> None:
            category = form.values()["category"]
            kinds = (category,) if category else ()
            for key in ("from_unit", "to_unit"):
                w = form.widget(key)
                assert isinstance(w, UnitCombo)
                w.set_kinds(kinds)

        def do_swap() -> None:
            v = form.values()
            form.set_values({"from_unit": v["to_unit"], "to_unit": v["from_unit"]})

        form.widget("category").currentIndexChanged.connect(on_category)  # type: ignore[attr-defined]
        swap.clicked.connect(do_swap)
        return panel

    # ----------------------------------------------------------- custom units
    def _build_custom(self) -> CalculatorPanel:
        fields = [
            Field(
                "name",
                "New unit name",
                "text",
                "",
                placeholder="e.g. bag",
                tooltip="Case-sensitive, no spaces needed. Must be new.",
            ),
            Field(
                "factor",
                "equals",
                "number",
                "",
                placeholder="e.g. 25",
                tooltip="How many reference units one new unit is. A fraction such as 1/3 is allowed.",
            ),
            Field(
                "reference_unit",
                "of this unit",
                "unit",
                "kg",
                tooltip="The new unit measures the same kind of quantity as this one.",
            ),
            Field(
                "aliases",
                "Other accepted names (optional)",
                "text",
                "",
                placeholder="comma separated",
                advanced=True,
            ),
        ]
        self._custom_table = QTableWidget(0, 3)
        table = self._custom_table
        table.setHorizontalHeaderLabels(["Unit", "Definition", ""])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setMinimumHeight(150)
        self._custom_banner = Banner("error")
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(label("Units defined in this session", "sectionLabel"))
        lay.addWidget(table)
        lay.addWidget(self._custom_banner)
        panel = CalculatorPanel(
            "Define a custom unit",
            fields,
            lambda v: unit_conversion.define_unit(v, self.state),
            self.state,
            tool="Custom units",
            description="Example: 1 bag = 25 kg. Custom units appear in every unit list.",
            extra_bottom=[holder],
            button_text="Define unit",
        )
        _use_time_notation(panel.form.widget("reference_unit"))
        return panel

    def _refresh(self) -> None:
        self.convert_panel.form.refresh_units()
        self.custom_panel.form.refresh_units()
        table = self._custom_table
        units = self.state.registry.custom_units()
        table.setRowCount(len(units))
        for row, unit in enumerate(units):
            ref, ratio = unit.definition if unit.definition else (unit.symbol, 1)
            table.setItem(row, 0, QTableWidgetItem(unit.symbol))
            table.setItem(
                row,
                1,
                QTableWidgetItem(
                    "1 %s = %s %s  (%s)" % (unit.symbol, ratio, unit_conversion.notation(ref), unit.category)
                ),
            )
            button = QPushButton(" Remove")
            button.setObjectName("danger")
            button.setIcon(icon("trash", CURRENT.error, 14))
            button.clicked.connect(lambda _c=False, name=unit.symbol: self._remove(name))
            table.setCellWidget(row, 2, button)
            button.ensurePolished()  # the size must include the stylesheet's padding and font
            table.setColumnWidth(2, button.sizeHint().width() + 8)

    def _remove(self, name: str) -> None:
        self._custom_banner.hide()
        _, err = guard(lambda: unit_conversion.remove_unit(name, self.state))
        if err:
            self._custom_banner.show_message(err.title, err.message + ("\n" + err.hint if err.hint else ""))
