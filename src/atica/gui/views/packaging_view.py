"""Packaging Calculations screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ..components import CalculatorPanel, TableEditor, label
from ..controllers import packaging_calc
from ..models import Field
from ..services import AppState
from ..services.parsing import build_product
from ..utils.errors import guard
from .base import ToolView

_DEFAULT_LEVELS = [["piece", "1"], ["box", "12"], ["carton", "20"], ["pallet", "40"]]


class PackagingView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Packaging Calculations",
            "Define how a product is packed (piece → box → carton → pallet), then convert quantities, count full packages and see the remainder.",
            state,
            parent,
        )
        self._known_levels: list = []
        self.levels = TableEditor(
            ["Level (smallest first)", "Contains (of the previous level)"],
            state,
            locked_first_cell=(1, "1"),
            min_height=170,
        )
        self.levels.set_rows(_DEFAULT_LEVELS)
        self.hierarchy = CalculatorPanel(
            "Product packaging",
            [
                Field("product_id", "Product ID", "text", "P001"),
                Field("name", "Product name", "text", "Product A"),
            ],
            self._apply,
            state,
            tool="Packaging",
            description="Each row says how many of the previous level it holds, e.g. 1 box = 12 piece, 1 carton = 20 box.",
            extra_bottom=[
                label("Level names are matched ignoring upper/lower case.", "muted", wrap=True),
                self.levels,
            ],
            button_text="Validate and apply levels",
        )
        self.breakdown = CalculatorPanel(
            "Packaging breakdown",
            [
                Field(
                    "quantity",
                    "Quantity",
                    "number",
                    "250",
                    tooltip="How many units you have, measured in the level chosen below.",
                ),
                Field(
                    "from_level",
                    "Quantity is in",
                    "choice",
                    "",
                    tooltip="The level the quantity is counted in.",
                ),
                Field("to_level", "Pack into", "choice", "", tooltip="The level to count full packages of."),
                Field("require_whole", "Only allow whole quantities", "checkbox", "", advanced=True),
            ],
            lambda v: packaging_calc.breakdown(v, self.state),
            state,
            tool="Packaging",
            description="Full packages, the leftover, and the minimum whole packages needed to hold everything.",
            depends_on=lambda: state.product,
        )
        self.plan = CalculatorPanel(
            "Packaging plan",
            [
                Field("quantity", "Quantity", "number", "250"),
                Field("from_level", "Quantity is in", "choice", ""),
            ],
            lambda v: packaging_calc.decompose(v, self.state),
            state,
            tool="Packaging",
            description="Splits a quantity into whole packages at every level, largest first, plus the loose remainder.",
            depends_on=lambda: state.product,
        )
        self.add_tab("Breakdown", self.breakdown)
        self.add_tab("Packaging plan", self.plan)
        self.add_tab("Hierarchy", self.hierarchy)
        state.on_change(self._sync_levels)
        # make the example hierarchy ready to use, silently
        self._silent_apply()

    def _apply(self, values):  # type: ignore[no-untyped-def]
        return packaging_calc.apply_levels(values, self.levels.rows(), self.state)

    def _silent_apply(self) -> None:
        product, err = guard(lambda: build_product("P001", "Product A", self.levels.rows()))
        if product is not None and err is None:
            self.state.product = product
            self._sync_levels()

    def _sync_levels(self) -> None:
        product = self.state.product
        names = list(product.level_names) if product else []
        options = [(n, n) for n in names]
        for panel in (self.breakdown, self.plan):
            panel.form.set_options("from_level", options)
        self.breakdown.form.set_options("to_level", options)
        if names != self._known_levels:  # a new hierarchy was applied: choose sensible defaults
            self._known_levels = names
            if names:
                self.breakdown.form.set_values(
                    {"from_level": names[0], "to_level": names[min(2, len(names) - 1)]}
                )
                self.plan.form.set_values({"from_level": names[0]})
