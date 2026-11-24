"""Purchasing Calculations screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ..components import CalculatorPanel
from ..controllers import purchasing_calc
from ..models import Field
from ..services import AppState
from .base import ToolView


class PurchasingView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Purchasing Calculations",
            "How much to order, after stock on hand, minimum order quantity and order multiples. No suppliers or purchase orders are kept.",
            state,
            parent,
        )
        self.panel = CalculatorPanel(
            "Recommended order",
            [
                Field("required_quantity", "Quantity required", "number", "130"),
                Field(
                    "unit",
                    "Unit of the quantity and stock",
                    "text",
                    "kg",
                    tooltip="A unit such as kg. Needed to convert into a purchase unit; otherwise just a label.",
                ),
                Field(
                    "stock_on_hand",
                    "Stock on hand",
                    "number",
                    "0",
                    tooltip="Deducted from the requirement (same unit).",
                ),
                Field(
                    "purchase_unit",
                    "Purchase unit (optional)",
                    "text",
                    "",
                    placeholder="e.g. bag",
                    tooltip="The unit you buy in. Define custom units such as 1 bag = 25 kg on the Unit Converter screen.",
                ),
                Field(
                    "minimum_order_quantity",
                    "Minimum order quantity",
                    "number",
                    "0",
                    tooltip="In the purchase unit (or the unit above if none).",
                ),
                Field(
                    "order_multiple",
                    "Order multiple (optional)",
                    "number",
                    "",
                    placeholder="any amount",
                    tooltip="Orders must be a multiple of this, in the purchase unit. Use 1 for whole bags/boxes.",
                ),
            ],
            lambda v: purchasing_calc.purchase(v, self.state),
            state,
            tool="Purchasing",
            description="Net requirement → minimum order quantity → round up to the order multiple. Nothing is ordered when stock already covers the need.",
        )
        self.add_tab("Order quantity", self.panel)
