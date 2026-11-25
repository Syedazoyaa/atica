"""The standard calculation layout.

Wide windows: inputs on the left, results on the right (each scrolls on its own).
Narrow or short windows (for example a 1366 x 768 laptop at 150 % scaling): ONE scrolling column with
the inputs followed by the result, at natural height - no cramped nested scroll areas.
"""

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
        self.result.module = tool
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
        self.reset_button.setIcon(icon("reset", size=16))
        self.reset_button.clicked.connect(self.reset)
        buttons = QHBoxLayout()
        buttons.addWidget(self.reset_button)
        buttons.addStretch(1)
        buttons.addWidget(self.calculate_button)
        card.body.addLayout(buttons)
        card.body.addStretch(1)

        self._left = QScrollArea()
        self._left.setWidgetResizable(True)
        self._left.setFrameShape(QFrame.Shape.NoFrame)
        self._left_holder = QWidget()
        self._left_holder.setObjectName("content")
        lh = QVBoxLayout(self._left_holder)
        lh.setContentsMargins(2, 2, 10, 14)
        lh.addWidget(card)
        lh.addStretch(1)
        self._left.setWidget(self._left_holder)

        right_card = Card("Result")
        right_card.body.addWidget(self.result, 1)
        self._right_holder = QWidget()
        self._right_holder.setObjectName("content")
        rh = QVBoxLayout(self._right_holder)
        rh.setContentsMargins(10, 2, 2, 14)
        rh.addWidget(right_card, 1)

        # wide layout
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._left)
        self._splitter.addWidget(self._right_holder)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 6)
        self._splitter.setSizes([460, 540])
        # narrow layout: one scrolling column (filled lazily when the window becomes narrow)
        self._column_scroll = QScrollArea()
        self._column_scroll.setWidgetResizable(True)
        self._column_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._column = QWidget()
        self._column.setObjectName("content")
        self._column_layout = QVBoxLayout(self._column)
        self._column_layout.setContentsMargins(0, 0, 8, 12)
        self._column_layout.setSpacing(10)
        self._column_scroll.setWidget(self._column)
        self._column_scroll.hide()
        self._stacked = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)
        layout.addWidget(self._column_scroll)
        self.form.submitted.connect(self.calculate)

    #: below this width the inputs and the result form one column instead of two side-by-side panes
    STACK_BELOW = 880

    def is_stacked(self) -> bool:
        return self._stacked

    def _set_stacked(self, stacked: bool) -> None:
        if stacked == self._stacked:
            return
        self._stacked = stacked
        if stacked:
            self._left.takeWidget()
            self._column_layout.addWidget(self._left_holder)
            self._column_layout.addWidget(self._right_holder)
            self._right_holder.setMinimumHeight(340)
            self._splitter.hide()
            self._column_scroll.show()
        else:
            self._column_layout.removeWidget(self._left_holder)
            self._column_layout.removeWidget(self._right_holder)
            self._right_holder.setMinimumHeight(0)
            self._left.setWidget(self._left_holder)
            self._splitter.addWidget(self._right_holder)
            self._splitter.setSizes([460, 540])
            self._column_scroll.hide()
            self._splitter.show()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._set_stacked(self.width() < self.STACK_BELOW)

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
