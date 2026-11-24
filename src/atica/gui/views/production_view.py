"""Production Calculations screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ..components import CalculatorPanel, rounding_fields
from ..controllers import production_calc
from ..models import Field
from ..services import AppState
from .base import ToolView

_TIME = ("time",)


class ProductionView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Production Calculations",
            "Batches, production time and capacity. These are straight calculations - nothing is scheduled and no machines are modelled.",
            state,
            parent,
        )
        self.batches = CalculatorPanel(
            "Batch plan",
            [
                Field("quantity", "Quantity to produce", "number", "250"),
                Field(
                    "batch_size",
                    "Batch size (capacity)",
                    "number",
                    "100",
                    tooltip="Units one full batch makes. Must be greater than zero.",
                ),
                Field(
                    "include_materials",
                    "Also calculate materials per batch from the BOM",
                    "checkbox",
                    "",
                    tooltip="Uses the BOM entered on the Materials and BOM screen.",
                ),
                Field("scrap_percent", "Scrap % (for materials)", "number", "0", suffix="%", advanced=True),
                *list(rounding_fields()),
            ],
            lambda v: production_calc.batches(v, self.state),
            state,
            tool="Production",
            description="Full batches, the partial last batch, and the batches required to cover the quantity.",
        )
        self.time = CalculatorPanel(
            "Production time",
            [
                Field("quantity", "Quantity to produce", "number", "1000"),
                Field(
                    "rate",
                    "Production rate",
                    "number",
                    "250",
                    tooltip="Units made per time unit at 100 % efficiency. Must be greater than zero.",
                ),
                Field("per", "Rate is per", "unit", "h", unit_kinds=_TIME),
                Field(
                    "efficiency_percent",
                    "Efficiency %",
                    "number",
                    "100",
                    suffix="%",
                    tooltip="Scales the nominal rate (greater than 0, up to 100).",
                ),
                Field("setup_time", "Setup time (optional)", "number", "", placeholder="none"),
                Field("setup_unit", "Setup time unit", "unit", "h", unit_kinds=_TIME),
                Field("unit", "Show result in", "unit", "h", unit_kinds=_TIME),
            ],
            lambda v: production_calc.time(v, self.state),
            state,
            tool="Production",
            description="Assumes a constant rate: no ramp-up, breaks or breakdowns. Setup is added once.",
        )
        self.capacity = CalculatorPanel(
            "Production capacity",
            [
                Field("rate", "Production rate", "number", "250"),
                Field("per", "Rate is per", "unit", "h", unit_kinds=_TIME),
                Field("available_time", "Available time", "number", "8"),
                Field("time_unit", "Available time unit", "unit", "h", unit_kinds=_TIME),
                Field("efficiency_percent", "Efficiency %", "number", "100", suffix="%"),
                Field("setup_time", "Setup time (optional)", "number", "", placeholder="none"),
                Field("rounding", "Rounding", "choice", "floor", options=rounding_fields()[0].options),
                Field("places", "Decimal places", "number", "0"),
            ],
            lambda v: production_calc.capacity(v, self.state),
            state,
            tool="Production",
            description="How many units fit into the available time (the inverse of production time).",
        )
        self.batch_capacity = CalculatorPanel(
            "Batch capacity",
            [
                Field("available_time", "Available time", "number", "8"),
                Field(
                    "time_per_batch",
                    "Time per batch",
                    "number",
                    "45",
                    tooltip="Measured in the unit below. Must be greater than zero.",
                ),
                Field("time_unit", "Time unit (both values)", "unit", "min", unit_kinds=_TIME),
                Field(
                    "batch_size",
                    "Batch size (optional)",
                    "number",
                    "100",
                    placeholder="to also get a quantity",
                ),
            ],
            lambda v: production_calc.batch_capacity(v, self.state),
            state,
            tool="Production",
            description="Complete batches that fit into the available time.",
        )
        self.constraints = CalculatorPanel(
            "Production quantity constraints",
            [
                Field("requested", "Required quantity", "number", "950"),
                Field("minimum", "Minimum run size (optional)", "number", ""),
                Field("maximum", "Maximum run size (optional)", "number", ""),
                Field("multiple", "Must be a multiple of (optional)", "number", "100"),
                Field(
                    "multiple_rounding",
                    "Snap to multiple",
                    "choice",
                    "ceiling",
                    options=[("Up (package ceiling)", "ceiling"), ("Down (package floor)", "floor")],
                ),
            ],
            lambda v: production_calc.constraints(v, self.state),
            state,
            tool="Production",
            description="Rules in order: zero stays zero → raise to minimum → snap to multiple → must not exceed maximum.",
        )
        self.add_tab("Batches", self.batches)
        self.add_tab("Time", self.time)
        self.add_tab("Capacity", self.capacity)
        self.add_tab("Batch capacity", self.batch_capacity)
        self.add_tab("Quantity constraints", self.constraints)
        state.on_change(self._on_state)

    def _on_state(self) -> None:
        for panel in (self.batches, self.time, self.capacity, self.batch_capacity, self.constraints):
            panel.form.refresh_units()
