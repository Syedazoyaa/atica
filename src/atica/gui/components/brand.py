"""The ATICA brand block: logo first, the word ATICA directly underneath (never beside it)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .. import branding


class BrandBlock(QWidget):
    """Logo above the product name; ``show_name=False`` gives the logo alone (compact sidebar)."""

    def __init__(
        self, logo_height: int = 56, *, show_name: bool = True, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setAccessibleName(branding.PRODUCT_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setAccessibleName("ATICA logo")
        self.name = QLabel(branding.PRODUCT_NAME)
        self.name.setObjectName("brandName")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo)
        layout.addWidget(self.name)
        self.set_logo_height(logo_height)
        self.name.setVisible(show_name)

    def set_logo_height(self, height: int) -> None:
        pixmap = branding.brand_pixmap(branding.ATICA_LOGO, height)
        self.logo.setPixmap(pixmap)
        self.logo.setFixedHeight(height)
        if pixmap.isNull():  # placeholder until the real asset is supplied
            self.logo.setText("[ATICA logo]")

    def set_name_visible(self, visible: bool) -> None:
        self.name.setVisible(visible)
