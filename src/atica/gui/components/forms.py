"""Declarative form builder (:class:`FormPanel`) and the unit selector (:class:`UnitCombo`)."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..controllers._common import ROUNDING_CHOICES
from ..models import Field
from ..services import AppState
from ..utils.icons import icon
from .basics import label


class UnitCombo(QComboBox):
    """A combo box listing the registry's units, optionally limited to some measurement categories."""

    def __init__(
        self,
        state: AppState,
        kinds: Sequence[str] = (),
        parent: Optional[QWidget] = None,
        *,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._kinds = tuple(kinds)
        self._compact = compact
        self._notation: Mapping[str, str] = {}
        self.setMaxVisibleItems(16)
        self.refresh()

    def set_kinds(self, kinds: Sequence[str]) -> None:
        self._kinds = tuple(kinds)
        self.refresh()

    def set_notation(self, notation: Mapping[str, str]) -> None:
        """Show some symbols differently; :meth:`symbol` still returns the library's own symbol."""
        self._notation = notation
        self.refresh()

    def refresh(self) -> None:
        """Reload items from the session registry (keeps the current selection when still present)."""
        current = self.symbol()
        self.blockSignals(True)
        self.clear()
        registry = self._state.registry
        categories = [c for c in registry.categories() if not self._kinds or c in self._kinds]
        for category in categories:
            units = registry.units(category)
            if not units:
                continue
            if len(categories) > 1:
                self.addItem(category.replace("_", " ").upper())
                item = self.model().item(self.count() - 1)  # type: ignore[attr-defined]
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            for unit in units:
                shown = self._notation.get(unit.symbol, unit.symbol)
                text = (
                    shown if (self._compact or unit.name == unit.symbol) else "%s  ·  %s" % (shown, unit.name)
                )
                self.addItem(text, unit.symbol)
                self.setItemData(self.count() - 1, unit.name, Qt.ItemDataRole.ToolTipRole)
        self.blockSignals(False)
        if current:
            self.set_symbol(current)
        elif self.count():
            self.setCurrentIndex(self._first_selectable())

    def _first_selectable(self) -> int:
        for i in range(self.count()):
            if self.itemData(i) is not None:
                return i
        return 0

    def symbol(self) -> str:
        data = self.currentData()
        return str(data) if data is not None else ""

    def set_symbol(self, symbol: str) -> bool:
        index = self.findData(symbol)
        if index >= 0:
            self.setCurrentIndex(index)
            return True
        return False


def rounding_fields() -> List[Field]:
    """The standard pair of rounding controls (``rounding`` + ``places``)."""
    return [
        Field(
            "rounding",
            "Rounding",
            "choice",
            "none",
            options=ROUNDING_CHOICES,
            tooltip="How the final figure is rounded. 'No rounding' shows the exact value.",
        ),
        Field(
            "places",
            "Decimal places",
            "number",
            "2",
            tooltip="Number of decimals kept when a rounding mode is chosen.",
            advanced=False,
        ),
    ]


class FormPanel(QWidget):
    """Builds labelled input controls from :class:`Field` descriptions and reads them back as a dict."""

    submitted = Signal()  # Enter pressed in a text box
    edited = Signal(str)  # the key of the field whose value changed
    field_hidden = Signal(str)  # the key of a field that a mode or option has just hidden

    def __init__(self, fields: Sequence[Field], state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._fields: Dict[str, Field] = {f.key: f for f in fields}
        self._widgets: Dict[str, QWidget] = {}
        self._containers: Dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        advanced_box = QVBoxLayout()
        advanced_box.setSpacing(12)
        advanced_fields = [f for f in fields if f.advanced]
        for f in fields:
            (advanced_box if f.advanced else layout).addWidget(self._build(f))
        self._advanced = QWidget()
        self._advanced.setLayout(advanced_box)
        self._advanced.setVisible(False)
        if advanced_fields:
            toggle = QToolButton()
            toggle.setText("More options")
            toggle.setCheckable(True)
            toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            toggle.setIcon(icon("expand", size=14))
            toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle.setObjectName("moreToggle")

            def flip(on: bool) -> None:
                self._advanced.setVisible(on)
                toggle.setIcon(icon("collapse" if on else "expand", size=14))

            toggle.toggled.connect(flip)
            layout.addWidget(toggle)
            layout.addWidget(self._advanced)
            self._toggle = toggle
        if "rounding" in self._widgets and "places" in self._widgets:
            combo = self._widgets["rounding"]
            assert isinstance(combo, QComboBox)
            combo.currentIndexChanged.connect(self._sync_places)
            self._sync_places()

    # ----------------------------------------------------------------- building
    def _build(self, f: Field) -> QWidget:
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        if f.kind == "checkbox":
            widget: QWidget = QCheckBox(f.label)
            widget.setChecked(f.default in ("1", "true", "True"))
            box.addWidget(widget)
        else:
            caption = label(f.label, "fieldLabel")
            caption.setToolTip(f.tooltip)
            box.addWidget(caption)
            if f.kind == "choice":
                widget = QComboBox()
                for text, value in f.options:
                    widget.addItem(text, value)
                index = widget.findData(f.default)
                widget.setCurrentIndex(max(index, 0))
            elif f.kind == "unit":
                widget = UnitCombo(self._state, f.unit_kinds)
                if f.default:
                    widget.set_symbol(f.default)
            else:
                widget = QLineEdit(f.default)
                widget.setPlaceholderText(f.placeholder)
                widget.returnPressed.connect(self.submitted.emit)
                widget.textChanged.connect(lambda _t, w=widget: self._clear_invalid(w))
            if f.suffix:
                row = QHBoxLayout()
                row.setSpacing(8)
                row.addWidget(widget, 1)
                row.addWidget(label(f.suffix, "unitSuffix"))
                box.addLayout(row)
            else:
                box.addWidget(widget)
        changed = (
            widget.textChanged
            if isinstance(widget, QLineEdit)
            else widget.toggled
            if isinstance(widget, QCheckBox)
            else widget.currentIndexChanged  # type: ignore[attr-defined]
        )
        changed.connect(lambda *_a, key=f.key: self.edited.emit(key))
        widget.setToolTip(f.tooltip)
        widget.setObjectName("field_" + f.key)
        self._widgets[f.key] = widget
        self._containers[f.key] = container
        return container

    def _sync_places(self) -> None:
        combo = self._widgets["rounding"]
        assert isinstance(combo, QComboBox)
        enabled = combo.currentData() != "none"
        self._widgets["places"].setEnabled(enabled)
        self._containers["places"].setVisible(enabled)

    # -------------------------------------------------------------------- access
    def widget(self, key: str) -> QWidget:
        return self._widgets[key]

    def values(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, w in self._widgets.items():
            if isinstance(w, QLineEdit):
                out[key] = w.text().strip()
            elif isinstance(w, UnitCombo):
                out[key] = w.symbol()
            elif isinstance(w, QComboBox):
                out[key] = w.currentData()
            elif isinstance(w, QCheckBox):
                out[key] = w.isChecked()
        return out

    def set_values(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            w = self._widgets.get(key)
            if isinstance(w, QLineEdit):
                w.setText(str(value))
            elif isinstance(w, UnitCombo):
                w.set_symbol(str(value))
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(max(w.findData(value), 0))
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(value))

    def reset(self) -> None:
        self.clear_invalid()
        for key, f in self._fields.items():
            w = self._widgets[key]
            if isinstance(w, QLineEdit):
                w.setText(f.default)
            elif isinstance(w, UnitCombo):
                if not (f.default and w.set_symbol(f.default)) and w.count():
                    w.setCurrentIndex(w._first_selectable())
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(max(w.findData(f.default), 0))
            elif isinstance(w, QCheckBox):
                w.setChecked(f.default in ("1", "true", "True"))

    def set_options(self, key: str, options: Iterable[Tuple[str, str]], keep: bool = True) -> None:
        combo = self._widgets[key]
        assert isinstance(combo, QComboBox)
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for text, value in options:
            combo.addItem(text, value)
        combo.blockSignals(False)
        if keep and current is not None and combo.findData(current) >= 0:
            combo.setCurrentIndex(combo.findData(current))

    def labels(self) -> Dict[str, str]:
        return {key: f.label for key, f in self._fields.items()}

    def number_fields_in_use(self) -> List[Tuple[str, str, str]]:
        """``(key, label, text)`` of every number box that takes part in the calculation (not hidden)."""
        out = []
        for key, f in self._fields.items():
            w = self._widgets[key]
            if f.kind == "number" and isinstance(w, QLineEdit) and not self._containers[key].isHidden():
                out.append((key, f.label, w.text().strip()))
        return out

    def is_blank(self, key: str) -> bool:
        w = self._widgets.get(key)
        return isinstance(w, QLineEdit) and not w.text().strip()

    def label_for(self, key: str) -> Optional[str]:
        field = self._fields.get(key)
        return field.label if field else None

    def refresh_units(self) -> None:
        for w in self._widgets.values():
            if isinstance(w, UnitCombo):
                w.refresh()

    def set_visible(self, key: str, visible: bool) -> None:
        self._containers[key].setVisible(visible)
        if not visible:
            self.field_hidden.emit(key)

    # --------------------------------------------------------------- validation
    def highlight(self, key: Optional[str]) -> bool:
        """Mark the field ``key`` as invalid and focus it. Returns False if there is no such field."""
        self.clear_invalid()
        w = self._widgets.get(key or "")
        if w is None:
            return False
        w.setProperty("invalid", True)
        w.style().unpolish(w)
        w.style().polish(w)
        w.setFocus()
        return True

    def clear_invalid(self) -> None:
        for w in self._widgets.values():
            if w.property("invalid"):
                self._clear_invalid(w)

    @staticmethod
    def _clear_invalid(w: QWidget) -> None:
        if w.property("invalid"):
            w.setProperty("invalid", False)
            w.style().unpolish(w)
            w.style().polish(w)
