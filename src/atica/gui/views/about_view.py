"""About screen."""

from __future__ import annotations

import platform
from typing import Optional

import PySide6
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from atica.version import __version__

from ..components import Card, label
from ..services import AppState
from ..utils.fonts import fonts_available
from ..utils.icons import wordmark_pixmap
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


class AboutView(ToolView):
    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "About ATICA",
            "Manufacturing calculations for Python developers and for people who prefer a window to a script.",
            state,
            parent,
        )
        head = Card()
        row = QHBoxLayout()
        row.setSpacing(18)
        mark = QLabel()
        mark.setPixmap(wordmark_pixmap(44))
        mark.setAccessibleName("ATICA")
        text = QVBoxLayout()
        text.addWidget(label("Version " + __version__, "cardTitle"))
        text.addWidget(
            label(
                "One package, two ways to work: the calculation library you import in Python, and this desktop "
                "application. Both use exactly the same calculation code and the same version.",
                "muted",
                wrap=True,
            )
        )
        row.addWidget(mark, 0)
        row.addLayout(text, 1)
        head.body.addLayout(row)

        facts = Card("Environment")
        for name, value in (
            ("ATICA version", __version__),
            ("Python", platform.python_version()),
            ("PySide6 / Qt", PySide6.__version__),
            ("Platform", platform.platform()),
            (
                "Interface typeface",
                "IBM Plex Sans" + ("" if fonts_available() else " (not loaded, using a system font)"),
            ),
        ):
            line = QHBoxLayout()
            line.addWidget(label(name, "muted"))
            line.addStretch(1)
            line.addWidget(label(value, "value"))
            facts.body.addLayout(line)

        licences = Card("Licences")
        licences.body.addWidget(label("ATICA is released under the MIT License.", "muted", wrap=True))
        licences.body.addWidget(
            label(
                "The interface typeface is IBM Plex Sans, © 2017 IBM Corp. with Reserved Font Name “Plex”, "
                "bundled unmodified under the SIL Open Font License 1.1 (see THIRD_PARTY_NOTICES.md and "
                "atica/gui/resources/fonts/OFL.txt). The GUI is built with Qt for Python (PySide6).",
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
        for card in (head, facts, use, licences):
            lay.addWidget(card)
        lay.addStretch(1)
        self.add_scrolling_tab("About", holder)
