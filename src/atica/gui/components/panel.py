"""The standard two-column calculation layout: inputs on the left, results on the right."""

from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..models import Field, Outcome
from ..services import AppState
from ..utils.errors import guard
from ..utils.icons import icon
from .basics import Banner, Card
from .forms import FormPanel
from .results import ResultPanel

Runner = Callable[[Dict[str, object]], Outcome]


class CalculatorPanel(QWidget):
    """Inputs card + result card for one calculation.

    ``runner`` receives the form values and returns an :class:`Outcome` (it calls the controller);
    errors it raises are shown inline - never as a traceback - and the offending field is highlighted.
    ``extra_top`` widgets (such as a table editor) are placed above the form.
    """

    def __init__(
        self,
        title: str,
        fields: Sequence[Field],
        runner: Runner,
        state: AppState,
        *,
        tool: str,
        description: str = "",
        extra_top: Sequence[QWidget] = (),
        extra_bottom: Sequence[QWidget] = (),
        button_text: str = "Calculate",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._state = state
        self._tool = tool
        self.form = FormPanel(fields, state)
        self.result = ResultPanel()
        self.error_banner = Banner("error")

        card = Card(title, description)
        for w in extra_top:
            card.body.addWidget(w)
        if fields:
            card.body.addWidget(self.form)
        for w in extra_bottom:
            card.body.addWidget(w)
        card.body.addWidget(self.error_banner)
        self.calculate_button = QPushButton(button_text)
        self.calculate_button.setObjectName("primary")
        self.calculate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.calculate_button.clicked.connect(self.calculate)
        self.reset_button = QPushButton(" Reset")
        self.reset_button.setIcon(icon("reset", "#102B50", 16))
        self.reset_button.clicked.connect(self.reset)
        buttons = QHBoxLayout()
        buttons.addWidget(self.reset_button)
        buttons.addStretch(1)
        buttons.addWidget(self.calculate_button)
        card.body.addLayout(buttons)
        card.body.addStretch(1)

        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFrameShape(QFrame.Shape.NoFrame)
        left_holder = QWidget()
        left_holder.setObjectName("content")
        lh = QVBoxLayout(left_holder)
        lh.setContentsMargins(2, 2, 10, 14)
        lh.addWidget(card)
        lh.addStretch(1)
        left.setWidget(left_holder)

        right_card = Card("Result", shadow=True)
        right_card.body.addWidget(self.result, 1)
        right_holder = QWidget()
        rh = QVBoxLayout(right_holder)
        rh.setContentsMargins(10, 2, 2, 14)
        rh.addWidget(right_card, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left)
        splitter.addWidget(right_holder)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 6)
        splitter.setSizes([460, 540])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.form.submitted.connect(self.calculate)

    # ------------------------------------------------------------------ actions
    def calculate(self) -> Optional[Outcome]:
        self.form.clear_invalid()
        self.error_banner.hide()
        outcome, err = guard(lambda: self._runner(self.form.values()))
        if err is not None:
            self.result.clear()
            self.form.highlight(err.parameter)
            message = err.message
            friendly = self.form.label_for(err.parameter or "")
            if friendly and err.parameter:
                # the core names its parameters; show the label the user sees on the form instead
                message = message.replace(err.parameter, "‘%s’" % friendly)
            body = message + ("\n" + err.hint if err.hint else "")
            self.error_banner.show_message(err.title, body)
            return None
        assert outcome is not None
        self.result.show_outcome(outcome)
        self._state.record(self._tool, outcome.summary or outcome.headline)
        return outcome

    def reset(self) -> None:
        self.form.reset()
        self.error_banner.hide()
        self.result.clear()
