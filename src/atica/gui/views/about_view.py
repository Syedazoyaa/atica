"""About screen."""

from __future__ import annotations

import platform
from typing import Optional

import PySide6
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from atica.version import __version__

from ..components import Card, label
from ..services import AppState
from ..utils.icons import logo_pixmap
from .base import ToolView

_SNIPPET = """from atica.units import convert
from atica.packaging import Product, PackagingLevel, breakdown

print(convert(25, "kg", "g"))          # 25000 g

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
        mark = QLabel()
        mark.setPixmap(logo_pixmap(64))
        mark.setFixedSize(64, 64)
        text = QVBoxLayout()
        text.addWidget(label("ATICA " + __version__, "cardTitle"))
        text.addWidget(
            label(
                "One package, two ways to work: the calculation library you import in Python, and this desktop application. "
                "Both use exactly the same calculation code and the same version.",
                "muted",
                wrap=True,
            )
        )
        row.addWidget(mark)
        row.addLayout(text, 1)
        head.body.addLayout(row)

        facts = Card("Environment")
        for name, value in (
            ("ATICA version", __version__),
            ("Python", platform.python_version()),
            ("PySide6 / Qt", PySide6.__version__),
            ("Platform", platform.platform()),
            ("License", "MIT"),
        ):
            line = QHBoxLayout()
            line.addWidget(label(name, "muted"))
            line.addStretch(1)
            line.addWidget(label(value, "fieldLabel"))
            facts.body.addLayout(line)

        use = Card("Use the same calculations from Python")
        code = QPlainTextEdit(_SNIPPET)
        code.setReadOnly(True)
        code.setStyleSheet(
            'QPlainTextEdit { font-family: "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace; font-size: 12px; }'
        )
        code.setFixedHeight(220)
        use.body.addWidget(code)

        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(2, 2, 2, 14)
        lay.setSpacing(14)
        for card in (head, facts, use):
            lay.addWidget(card)
        lay.addStretch(1)
        self.add_tab("About", holder)
