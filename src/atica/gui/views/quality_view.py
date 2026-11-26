"""Quality and Yield screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ..components import CalculatorPanel, rounding_fields
from ..controllers import quality_calc
from ..models import Field
from ..services import AppState
from .base import ToolView

_MODES = [
    ("Input needed for a good-output target", "required_input"),
    ("Expected good output from an input", "expected_output"),
    ("Expected scrap from an input", "scrap_quantity"),
    ("Scrap percentage from actual scrap", "scrap_percentage"),
]
_UNIT = Field("unit", "Unit label (optional)", "text", "", placeholder="e.g. pieces, kg", advanced=True)


class QualityView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Quality and Yield",
            "Scrap, yield, rework, recovery and wastage - each with its denominator stated, so the percentages mean one thing only.",
            state,
            parent,
        )
        self.scrap = CalculatorPanel(
            "Scrap and required input",
            [
                Field("mode", "What do you want to know?", "choice", "required_input", options=_MODES),
                Field("good_output", "Good units wanted", "number", "950"),
                Field("input_quantity", "Input quantity (units started)", "number", "1000"),
                Field("scrap_quantity", "Scrap quantity", "number", "50"),
                Field(
                    "scrap_percent",
                    "Scrap %",
                    "number",
                    "5",
                    suffix="%",
                    tooltip="Scrap as a percentage of the quantity started (0-100).",
                ),
                *rounding_fields(),
                _UNIT,
            ],
            lambda v: quality_calc.scrap(v, self.state),
            state,
            tool="Quality",
            description="Scrap % is always measured against the quantity started. 100 % scrap is valid for expected output.",
        )
        self.yield_panel = CalculatorPanel(
            "Yield",
            [
                Field("input_quantity", "Input quantity (units started)", "number", "1000"),
                Field(
                    "good_first_pass",
                    "Good at first inspection",
                    "number",
                    "900",
                    tooltip="Passed the first time, with no rework.",
                ),
                Field(
                    "sent_to_rework",
                    "Sent to rework",
                    "number",
                    "60",
                    tooltip="Failed first inspection but were reprocessed.",
                ),
                Field(
                    "recovered_from_rework",
                    "Recovered by rework",
                    "number",
                    "45",
                    tooltip="Of those reworked, how many became good.",
                ),
                Field(
                    "first_pass_scrap",
                    "Scrapped at first inspection (optional)",
                    "number",
                    "",
                    advanced=True,
                    tooltip="Optional check: must equal input - good - rework.",
                ),
            ],
            lambda v: quality_calc.yield_(v, self.state),
            state,
            tool="Quality",
            description="First-pass yield counts only units good the first time. Final yield also counts units recovered by rework. Each unit is counted once.",
        )
        self.rework = CalculatorPanel(
            "Rework projection",
            [
                Field("input_quantity", "Input quantity", "number", "1000"),
                Field(
                    "first_pass_yield_percent",
                    "First-pass yield %",
                    "number",
                    "90",
                    suffix="%",
                    tooltip="% of input that is good first time.",
                ),
                Field(
                    "rework_percent",
                    "Rework rate %",
                    "number",
                    "6",
                    suffix="%",
                    tooltip="% of input sent to rework.",
                ),
                Field(
                    "rework_recovery_percent",
                    "Rework recovery %",
                    "number",
                    "75",
                    suffix="%",
                    tooltip="% of the reworked units that become good.",
                ),
                Field(
                    "good_target",
                    "Good units wanted (optional)",
                    "number",
                    "",
                    tooltip="Also calculates the input needed to reach this target.",
                ),
            ],
            lambda v: quality_calc.rework(v, self.state),
            state,
            tool="Quality",
            description="Expected good and scrapped units when part of the failures are reworked.",
            error_aliases={"good_output": "good_target"},
        )
        self.wastage = CalculatorPanel(
            "Material wastage",
            [
                Field("material_input", "Material consumed", "number", "1000"),
                Field("material_in_output", "Material in the good output", "number", "920"),
                Field(
                    "recovery_percent",
                    "Recovery % of the waste (optional)",
                    "number",
                    "25",
                    suffix="%",
                    tooltip="Share of the wasted material that is reclaimed (regrind, offcuts).",
                ),
                Field(
                    "recovered_quantity",
                    "...or recovered quantity (optional)",
                    "number",
                    "",
                    advanced=True,
                    tooltip="Give either the percentage or the quantity, not both.",
                ),
                Field("unit", "Unit label (optional)", "text", "kg"),
            ],
            lambda v: quality_calc.wastage(v, self.state),
            state,
            tool="Quality",
            description="Wastage is material that does not end up in good output. Percentages are of the material consumed; recovery is of the waste.",
        )
        self.recovery = CalculatorPanel(
            "Material recovery",
            [
                Field("waste_quantity", "Waste quantity", "number", "200"),
                Field("recovery_percent", "Recovery %", "number", "40", suffix="%"),
                Field("unit", "Unit label (optional)", "text", "kg"),
            ],
            lambda v: quality_calc.recovery(v, self.state),
            state,
            tool="Quality",
            description="Material reclaimed from waste: waste × recovery %.",
        )
        self.add_tab("Scrap and input", self.scrap)
        self.add_tab("Yield", self.yield_panel)
        self.add_tab("Rework", self.rework)
        self.add_tab("Wastage", self.wastage)
        self.add_tab("Recovery", self.recovery)
        combo = self.scrap.form.widget("mode")
        combo.currentIndexChanged.connect(self._mode_changed)  # type: ignore[attr-defined]
        self._mode_changed()

    def _mode_changed(self) -> None:
        mode = self.scrap.form.values()["mode"]
        form = self.scrap.form
        form.set_visible("good_output", mode == "required_input")
        form.set_visible("input_quantity", mode != "required_input")
        form.set_visible("scrap_quantity", mode == "scrap_percentage")
        form.set_visible("scrap_percent", mode != "scrap_percentage")
