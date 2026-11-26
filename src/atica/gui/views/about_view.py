"""About screen: product information, authors, company details and licences."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import branding as B
from ..components import Card, label
from ..components.brand import BrandBlock
from ..services import AppState
from .base import ToolView


def _link(text: str, url: str) -> QLabel:
    lab = QLabel('<a href="%s">%s</a>' % (url, text))
    lab.setTextFormat(Qt.TextFormat.RichText)
    lab.setOpenExternalLinks(True)
    lab.setTextInteractionFlags(
        Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
    )
    return lab


def _facts(rows: Sequence[Tuple[str, QWidget]]) -> QGridLayout:
    """Two aligned columns: muted captions, then their values (both left-aligned)."""
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(28)
    grid.setVerticalSpacing(8)
    grid.setColumnMinimumWidth(0, 96)
    grid.setColumnStretch(1, 1)
    for row, (name, widget) in enumerate(rows):
        grid.addWidget(label(name, "muted"), row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(widget, row, 1, Qt.AlignmentFlag.AlignTop)
    return grid


def _divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


class _CompanyBlock(QWidget):
    """The company logo beside its contact details; the logo moves above them when space is short."""

    SPACING = 32

    def __init__(self, logo: QLabel, details: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._logo = logo
        self._details = details
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(self.SPACING)
        self._layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._layout.addWidget(details, 1)

    def minimumSizeHint(self) -> QSize:
        # only the stacked width is required, otherwise the page could never get narrow enough to stack
        width = max(self._logo.sizeHint().width(), self._details.minimumSizeHint().width())
        return QSize(width, self._layout.minimumSize().height())

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        needed = self._logo.sizeHint().width() + self.SPACING + self._details.sizeHint().width()
        direction = (
            QBoxLayout.Direction.LeftToRight if self.width() >= needed else QBoxLayout.Direction.TopToBottom
        )
        if direction != self._layout.direction():
            self._layout.setDirection(direction)
            self.updateGeometry()


class AboutView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__("About ATICA", "Product information, company details and authors.", state, parent)

        product = Card("Product")
        top = QHBoxLayout()
        top.setSpacing(24)
        top.addWidget(BrandBlock(96), 0, Qt.AlignmentFlag.AlignTop)
        facts = QVBoxLayout()
        facts.setSpacing(12)
        facts.addWidget(label(B.PRODUCT_NAME + " " + B.VERSION, "cardTitle"))
        facts.addWidget(label(B.PRODUCT_DESCRIPTION, "muted", wrap=True))
        facts.addWidget(_divider())
        facts.addLayout(
            _facts(
                [
                    (name, label(value, "value", wrap=True))
                    for name, value in (
                        ("Version", B.VERSION),
                        ("Initial release", B.INITIAL_RELEASE),
                        ("Updated on", B.UPDATED_ON),
                        ("License", B.LICENSE_NAME),
                    )
                ]
            )
        )
        facts.addStretch(1)
        top.addLayout(facts, 1)
        product.body.addLayout(top)

        company = Card("Company")
        logo = QLabel()
        logo.setAccessibleName(B.COMPANY_NAME + " logo")
        pix = B.brand_pixmap(B.FALCON_LOGO, 56)
        if pix.isNull():
            logo.setText("[%s logo]" % B.COMPANY_NAME)
        else:
            logo.setPixmap(pix)
        details = QWidget()
        column = QVBoxLayout(details)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(10)
        column.addWidget(label(B.COMPANY_NAME, "cardTitle"))
        contacts = [
            ("Website", _link(B.COMPANY_WEBSITE, B.COMPANY_WEBSITE)),
            ("LinkedIn", _link(B.COMPANY_LINKEDIN, B.COMPANY_LINKEDIN)),
        ]
        for i, mail in enumerate(B.COMPANY_EMAILS):
            contacts.append(("Email" if i == 0 else "", _link(mail, "mailto:" + mail)))
        column.addLayout(_facts(contacts))
        company.body.addWidget(_CompanyBlock(logo, details))
        company.body.addWidget(_divider())
        copyright_label = QLabel(
            '© <span style="color:%s;font-weight:600">Falcon</span> '
            '<span style="color:%s;font-weight:600">Informatics</span>.%s'
            % (B.FALCON_COLOR, B.INFORMATICS_COLOR, B.COPYRIGHT_RIGHTS)
        )
        copyright_label.setTextFormat(Qt.TextFormat.RichText)
        copyright_label.setAccessibleName("Copyright")
        company.body.addWidget(copyright_label)

        authors = Card("Authors")
        authors.body.addWidget(label(", ".join(B.AUTHORS), wrap=True))

        licences = Card("Licences")
        licences.body.addWidget(
            label(
                "ATICA is free software released under the GNU General Public License v3.0 (GPL-3.0); see the "
                "LICENSE file.",
                "muted",
                wrap=True,
            )
        )

        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 2, 8, 14)
        lay.setSpacing(12)
        for card in (product, company, authors, licences):
            lay.addWidget(card)
        lay.addStretch(1)
        self.add_scrolling_tab("About", holder)
