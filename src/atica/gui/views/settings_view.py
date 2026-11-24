"""Settings screen."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSpinBox, QVBoxLayout, QWidget

from atica.units import UnitRegistry

from ..components import Card, label
from ..components.basics import Banner
from ..services import AppState
from ..services.settings_store import save_settings
from ..utils.errors import log_path
from .base import ToolView


class SettingsView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Settings",
            "Display and precision preferences. They are saved for the next time you open ATICA.",
            state,
            parent,
        )
        card = Card("Numbers")
        self.places = QSpinBox()
        self.places.setRange(0, 30)
        self.places.setValue(state.display_places)
        self.places.setToolTip(
            "Only changes how results are written on screen. Calculations are not affected."
        )
        self.precision = QSpinBox()
        self.precision.setRange(10, 200)
        self.precision.setValue(state.precision)
        self.precision.setToolTip(
            "Significant digits kept for results that cannot be exact, such as 1/3. 50 is plenty for any manufacturing use."
        )
        card.body.addWidget(label("Decimal places shown", "fieldLabel"))
        card.body.addWidget(self.places)
        card.body.addWidget(
            label("Results are displayed with at most this many decimals (display only).", "muted", wrap=True)
        )
        card.body.addWidget(label("Calculation precision (significant digits)", "fieldLabel"))
        card.body.addWidget(self.precision)
        card.body.addWidget(
            label(
                "Applies to results that cannot be written exactly, such as repeating decimals.",
                "muted",
                wrap=True,
            )
        )

        session = Card("This session")
        clear_activity = QPushButton("Clear recent activity")
        reset_units = QPushButton("Remove all custom units")
        self.banner = Banner("success")
        row = QHBoxLayout()
        row.addWidget(clear_activity)
        row.addWidget(reset_units)
        row.addStretch(1)
        session.body.addLayout(row)
        session.body.addWidget(self.banner)
        where = log_path()
        session.body.addWidget(
            label("Diagnostic log: " + (where if where else "not available"), "muted", wrap=True)
        )

        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(2, 2, 2, 14)
        lay.setSpacing(14)
        lay.addWidget(card)
        lay.addWidget(session)
        lay.addStretch(1)
        self.add_tab("Preferences", holder)

        self.places.valueChanged.connect(self._changed)
        self.precision.valueChanged.connect(self._changed)
        clear_activity.clicked.connect(self._clear_activity)
        reset_units.clicked.connect(self._reset_units)

    def _changed(self) -> None:
        self.state.display_places = self.places.value()
        self.state.precision = self.precision.value()
        save_settings(self.state)
        self.state.changed()

    def _clear_activity(self) -> None:
        self.state.clear_activity()
        self.banner.show_message("Recent activity cleared.")

    def _reset_units(self) -> None:
        self.state.registry = UnitRegistry()
        self.state.changed()
        self.banner.show_message("Custom units removed.")
