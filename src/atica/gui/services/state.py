"""Session state shared by the GUI screens (Qt-free, held in memory only).

Nothing here is persisted except user *settings*, which :mod:`atica.gui.services.settings_store`
stores through Qt's ``QSettings``.  Custom units live in ``registry`` for the session; the BOM and
the packaging product are shared so they only have to be entered once.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from atica.packaging import Product
from atica.units import UnitRegistry

MAX_ACTIVITY = 25


@dataclass
class Activity:
    """One calculation the user actually ran in this session."""

    when: datetime.datetime
    tool: str
    summary: str


@dataclass
class AppState:
    registry: UnitRegistry = field(default_factory=UnitRegistry)
    product: Optional[Product] = None
    bom_rows: List[List[str]] = field(default_factory=list)  # [material_id, qty/unit, unit, wastage %]
    display_places: int = 6  # display only; never changes stored precision
    precision: int = 50  # significant digits for inexact results (see atica.core.use_precision)
    activity: List[Activity] = field(default_factory=list)
    _listeners: List[Callable[[], None]] = field(default_factory=list, repr=False)

    def record(self, tool: str, summary: str) -> None:
        self.activity.insert(0, Activity(datetime.datetime.now(), tool, summary))
        del self.activity[MAX_ACTIVITY:]
        self.changed()

    def clear_activity(self) -> None:
        self.activity.clear()
        self.changed()

    def on_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def changed(self) -> None:
        for callback in list(self._listeners):
            callback()
