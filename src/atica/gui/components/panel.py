"""The standard calculation layout.

Wide windows: inputs on the left, results on the right (each scrolls on its own).
Narrow or short windows (for example a 1366 x 768 laptop at 150 % scaling): ONE scrolling column with
the inputs followed by the result, at natural height - no cramped nested scroll areas.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence, Set, Tuple

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

from atica.core import InvalidQuantityError
from atica.core.precision import to_fraction

from ..models import Field, Outcome
from ..services import AppState
from ..utils.errors import FriendlyError, guard
from ..utils.icons import icon
from ..utils.messages import enter_number, plain_hint, translate
from .basics import Banner, Card
from .forms import FormPanel
from .results import ResultPanel
from .tables import TableEditor

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
        depends_on: Optional[Callable[[], object]] = None,
        error_aliases: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._state = state
        self._tool = tool
        self._depends_on = depends_on  # shared data (BOM, packaging) this calculation also reads
        self._error_aliases = dict(error_aliases or {})  # library argument name -> field key
        self._shown_for: Optional[Tuple[object, ...]] = None  # the inputs behind the visible result
        self._error_fields: Set[str] = set()  # the fields the visible error is about
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
        self.form.edited.connect(self._field_edited)
        self.form.field_hidden.connect(self._field_gone)
        self._tables = [w for top in (*extra_top, *extra_bottom) for w in _tables_in(top)]
        for table in self._tables:
            table.changed.connect(self._table_edited)
        state.on_change(self.discard_stale_result)

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

    # ------------------------------------------------------------- staying current
    def _inputs(self) -> Tuple[object, ...]:
        """Everything the result depends on; any difference makes a visible result out of date."""
        state = self._state
        return (
            self.form.values(),
            [table.rows() for table in self._tables],
            repr(self._depends_on()) if self._depends_on else "",
            (state.precision, state.display_places),
            repr(state.registry.custom_units()),
        )

    def discard_stale_result(self) -> None:
        if (
            self._shown_for is not None
            and self.result.outcome is not None
            and self._inputs() != self._shown_for
        ):
            self._shown_for = None
            self.result.clear()

    def _dismiss_error(self) -> None:
        self._error_fields = set()
        self.error_banner.hide()
        self.form.clear_invalid()

    def _field_edited(self, key: str) -> None:
        # an error disappears when a field it is about is edited (or hidden); others stay
        if not self.error_banner.isHidden() and key in self._error_fields:
            self._dismiss_error()
        self.discard_stale_result()

    def _field_gone(self, key: str) -> None:
        if not self.error_banner.isHidden() and key in self._error_fields:
            self._dismiss_error()

    def _table_edited(self) -> None:
        # errors that belong to no single field come from the table (BOM, stock or packaging rows)
        if not self.error_banner.isHidden() and not self._error_fields:
            self._dismiss_error()
        self.discard_stale_result()

    # ------------------------------------------------------------------ actions
    def _check_numbers(self) -> None:
        for key, text_label, text in self.form.number_fields_in_use():
            if not text:
                continue
            try:
                to_fraction(text, key)
            except (InvalidQuantityError, ValueError, ArithmeticError) as exc:
                if "is not a valid number" in str(exc):
                    raise InvalidQuantityError(enter_number(text_label, blank=False), parameter=key) from None

    def _run(self) -> Outcome:
        self._check_numbers()
        return self._runner(self.form.values())

    def _word(self, err: FriendlyError) -> Tuple[str, Set[str]]:
        """The message in the words of the form, and the keys of the fields it is about."""
        labels = self.form.labels()
        param = self._error_aliases.get(err.parameter or "", err.parameter or "")
        own = {param} if param in labels else set()
        if own and self.form.is_blank(param):
            numeric = any(key == param for key, _l, _t in self.form.number_fields_in_use())
            text = enter_number(labels[param], blank=True) if numeric else "Fill in %s." % labels[param]
            return text, own
        if err.message.startswith("Enter a valid number for "):
            return err.message + "\n" + (plain_hint("Pass an int, Decimal") or ""), own
        # internal names (those with an underscore are never ordinary words) plus the offending one
        names = {key: text for key, text in labels.items() if "_" in key}
        for alias, key in self._error_aliases.items():
            if key in labels:
                names[alias] = labels[key]
        if err.parameter and param in labels:
            names[err.parameter] = labels[param]
        message, found = translate(err.message, names)
        hint, _ = translate(plain_hint(err.hint) or "", names)
        related = own | {self._error_aliases.get(n, n) for n in found}
        return message + ("\n" + hint if hint else ""), related

    def calculate(self) -> Optional[Outcome]:
        self._dismiss_error()
        outcome, err = guard(self._run)
        if err is not None:
            self._shown_for = None
            self.result.clear()
            body, self._error_fields = self._word(err)
            self.form.highlight(self._error_aliases.get(err.parameter or "", err.parameter))
            self.error_banner.show_message(err.title, body)
            return None
        assert outcome is not None
        self.result.show_outcome(outcome)
        self._shown_for = self._inputs()  # taken after the run: it may itself update shared data
        self._state.record(self._tool, outcome.summary or outcome.headline)
        return outcome

    def reset(self) -> None:
        self.form.reset()
        self._dismiss_error()
        self._shown_for = None
        self.result.clear()


def _tables_in(widget: QWidget) -> Sequence[TableEditor]:
    own = [widget] if isinstance(widget, TableEditor) else []
    return own + widget.findChildren(TableEditor)
