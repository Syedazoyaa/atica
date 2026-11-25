"""About screen: product information, authors, company details and licences."""

from __future__ import annotations

import platform
from typing import Optional

import PySide6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from .. import branding as B
from ..components import Card, label
from ..components.brand import BrandBlock
from ..services import AppState
from ..utils.fonts import fonts_available
from .base import ToolView

_SNIPPET = """from atica.units import convert
from atica.packaging import Product, PackagingLevel, breakdown

print(convert(25, "kg", "g"))

product = Product("P001", "Product A", levels=[
    PackagingLevel("piece"),
    PackagingLevel("box", 12, "piece"),
    PackagingLevel("carton", 20, "box"),
])
print(breakdown(product, 250, "piece", "carton"))
"""



def _link(text: str, url: str) -> QLabel:
    lab = QLabel('<a href="%s">%s</a>' % (url, text))
    lab.setTextFormat(Qt.TextFormat.RichText)
    lab.setOpenExternalLinks(True)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
    return lab


def _row(name: str, widget: QWidget) -> QHBoxLayout:
    line = QHBoxLayout()
    line.addWidget(label(name, "muted"))
    line.addStretch(1)
    line.addWidget(widget)
    return line


class AboutView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__("About ATICA", B.PRODUCT_DESCRIPTION, state, parent)

        product = Card("Product")
        top = QHBoxLayout()
        top.setSpacing(24)
        top.addWidget(BrandBlock(96), 0, Qt.AlignmentFlag.AlignTop)
        facts = QVBoxLayout()
        facts.addWidget(label(B.PRODUCT_NAME + " " + B.VERSION, "cardTitle"))
        facts.addWidget(label(B.PRODUCT_DESCRIPTION, "muted", wrap=True))
        for name, value in (
            ("Version", B.VERSION),
            ("Initial release", B.INITIAL_RELEASE),
            ("Updated on", B.UPDATED_ON),
            ("License", B.LICENSE_NAME),
        ):
            facts.addLayout(_row(name, label(value, "value")))
        top.addLayout(facts, 1)
        product.body.addLayout(top)

        authors = Card("Authors")
        for i, name in enumerate(B.AUTHORS, 1):
            authors.body.addWidget(label("%d.  %s" % (i, name), "value"))

        company = Card("Company")
        crow = QHBoxLayout()
        crow.setSpacing(24)
        logo = QLabel()
        logo.setAccessibleName(B.COMPANY_NAME + " logo")
        pix = B.brand_pixmap(B.FALCON_LOGO, 64)
        if pix.isNull():
            logo.setText("[%s logo]" % B.COMPANY_NAME)
        else:
            logo.setPixmap(pix)
        crow.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)
        details = QVBoxLayout()
        details.addWidget(label(B.COMPANY_NAME, "cardTitle"))
        details.addLayout(_row("Website", _link(B.COMPANY_WEBSITE, B.COMPANY_WEBSITE)))
        details.addLayout(_row("LinkedIn", _link(B.COMPANY_LINKEDIN, B.COMPANY_LINKEDIN)))
        for mail in B.COMPANY_EMAILS:
            details.addLayout(_row("Email", _link(mail, "mailto:" + mail)))
        crow.addLayout(details, 1)
        company.body.addLayout(crow)
        copyright_label = QLabel(
            '© <span style="color:%s;font-weight:600">Falcon</span> '
            '<span style="color:%s;font-weight:600">Informatics</span>.%s'
            % (B.FALCON_COLOR, B.INFORMATICS_COLOR, B.COPYRIGHT_RIGHTS)
        )
        copyright_label.setTextFormat(Qt.TextFormat.RichText)
        copyright_label.setAccessibleName("Copyright")
        company.body.addWidget(copyright_label)

        env = Card("Environment")
        for name, value in (
            ("Python", platform.python_version()),
            ("PySide6 / Qt", PySide6.__version__),
            ("Platform", platform.platform()),
            (
                "Interface typeface",
                "IBM Plex Sans" + ("" if fonts_available() else " (not loaded, using a system font)"),
            ),
        ):
            env.body.addLayout(_row(name, label(value, "value")))

        licences = Card("Licences")
        licences.body.addWidget(
            label(
                "ATICA is free software released under the GNU General Public License v3.0 (GPL-3.0); see the "
                "LICENSE file.",
                "muted",
                wrap=True,
            )
        )
        licences.body.addWidget(
            label(
                "The interface typeface is IBM Plex Sans, © 2017 IBM Corp. with Reserved Font Name “Plex”, "
                "bundled unmodified under the SIL Open Font License 1.1 (see THIRD_PARTY_NOTICES.md and "
                "atica/gui/resources/fonts/OFL.txt). The GUI is built with Qt for Python (PySide6).",
                "muted",
                wrap=True,
            )
        )

        session = Card("Your data")
        session.body.addWidget(
            label(
                "Custom units, the imported or edited BOM, the packaging product and the activity list are kept "
                "for this session only and are lost when ATICA closes. Settings (display decimal places and "
                "calculation precision) stay saved.",
                "muted",
                wrap=True,
            )
        )

        use = Card("Use the same calculations from Python")
        code = QPlainTextEdit(_SNIPPET)
        code.setReadOnly(True)
        code.setFixedHeight(250)
        code.setAccessibleName("Python example")
        use.body.addWidget(code)

        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 2, 8, 14)
        lay.setSpacing(12)
        for card in (product, authors, company, session, env, use, licences):
            lay.addWidget(card)
        lay.addStretch(1)
        self.add_scrolling_tab("About", holder)
