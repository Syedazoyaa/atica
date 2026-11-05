"""Application state: the ATICA configuration plus where it is saved."""
from __future__ import annotations

import os
from typing import List, Optional

from PySide6.QtCore import QObject, QStandardPaths, Signal

from atica import AticaConfig
from atica.packaging import Product
from atica.units import UnitRegistry


class AppState(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.config = AticaConfig()
        self.path: Optional[str] = None  # explicit file chosen by the user
        self.dirty = False

    # ------------------------------------------------------------------ access
    @property
    def registry(self) -> UnitRegistry:
        return self.config.registry

    def products(self) -> List[Product]:
        return sorted(self.config.products.values(), key=lambda p: p.name.casefold())

    def notify(self, dirty: bool = True) -> None:
        self.dirty = self.dirty or dirty
        self.changed.emit()

    # ------------------------------------------------------------- persistence
    @staticmethod
    def autosave_path() -> str:
        folder = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~/.atica")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "atica_config.json")

    def new(self) -> None:
        self.config = AticaConfig()
        self.path = None
        self.dirty = False
        self.changed.emit()

    def load(self, path: str) -> None:
        self.config = AticaConfig.load(path)  # raises ConfigurationError, leaving state untouched
        self.path = path
        self.dirty = False
        self.changed.emit()

    def save(self, path: Optional[str] = None) -> str:
        target = path or self.path or self.autosave_path()
        self.config.save(target)
        if path or self.path:
            self.path = target
        self.dirty = False
        return target
