"""Display formatting helpers (no arithmetic: they only choose how a Decimal is written)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from atica.core.precision import display_decimal

from .state import AppState


def fmt(value: Optional[Decimal], state: AppState) -> str:
    """A plain number with at most ``state.display_places`` decimals.

    Deliberately no thousands separator: the same text is used by *Copy* and *Export*, and a plain
    number pastes into a spreadsheet or CSV as a number.
    """
    if value is None:
        return "n/a"
    return display_decimal(value, state.display_places)


def with_unit(value: Decimal, unit: str, state: AppState) -> str:
    text = fmt(value, state)
    return "%s %s" % (text, unit) if unit else text


def percent(value: Optional[Decimal], state: AppState) -> str:
    return "n/a" if value is None else fmt(value, state) + " %"


def text_of(values: Any, key: str, default: str = "") -> str:
    """A form value as stripped text (``None`` -> default)."""
    raw = values.get(key, default)
    return default if raw is None else str(raw).strip()
