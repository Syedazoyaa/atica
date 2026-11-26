"""Unit Converter screen: calls :mod:`atica.units`."""

from __future__ import annotations

from typing import Any, Mapping

from atica import units
from atica.core import format_duration, use_precision

from ..models import Outcome
from ..services import AppState, fmt, with_unit
from ._common import checked, optional, rounding_args, val

#: How the Unit Converter writes time units. Display only: the library's unit symbols are unchanged.
TIME_NOTATION = {"d": "dd", "h": "hh", "min": "min", "s": "ss"}
#: The words of :func:`atica.core.format_duration`, in the same notation.
_DURATION_WORDS = {
    word + plural: TIME_NOTATION[symbol]
    for word, symbol in (("day", "d"), ("hour", "h"), ("minute", "min"), ("second", "s"))
    for plural in ("", "s")
}


def notation(symbol: str) -> str:
    """The unit symbol as the Unit Converter shows it."""
    return TIME_NOTATION.get(symbol, symbol)


def convert(values: Mapping[str, Any], state: AppState) -> Outcome:
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        result = units.convert(
            val(values, "value"),
            val(values, "from_unit"),  # type: ignore[arg-type]
            val(values, "to_unit"),  # type: ignore[arg-type]
            rounding=rounding,
            places=places,
            interval=checked(values, "interval"),
            registry=state.registry,
        )
    source_unit, unit = notation(result.source_unit), notation(result.unit)
    outcome = Outcome(
        title="Unit conversion",
        headline=with_unit(result.value, unit, state),
        rows=[
            ("Input", with_unit(result.source_value, source_unit, state)),
            ("Measures", result.category),
        ],
        formula=result.formula,
        warnings=list(result.warnings),
        summary="%s = %s"
        % (
            with_unit(result.source_value, source_unit, state),
            with_unit(result.value, unit, state),
        ),
    )
    if result.category == "time":
        outcome.headline = " ".join(
            _DURATION_WORDS.get(part, part)
            for part in format_duration(result.value, result.unit, state.registry).split()
        )
    if result.rounding.value != "none":
        outcome.rows.append(("Exact value", with_unit(result.exact_value, unit, state)))
        outcome.rows.append(
            ("Rounding", "%s, %d decimal places" % (result.rounding.value.replace("_", " "), result.places))
        )
    if checked(values, "interval"):
        outcome.assumptions.append("Treated as a temperature difference (no offset applied).")
    return outcome


def define_unit(values: Mapping[str, Any], state: AppState) -> Outcome:
    aliases = [a.strip() for a in (optional(values, "aliases", "") or "").split(",") if a.strip()]
    unit = state.registry.register_unit(
        val(values, "name"),  # type: ignore[arg-type]
        val(values, "factor"),
        val(values, "reference_unit"),  # type: ignore[arg-type]
        aliases=aliases,
    )
    state.changed()
    ratio = units.convert(1, unit.symbol, val(values, "reference_unit"), registry=state.registry)  # type: ignore[arg-type]
    text = "1 %s = %s %s" % (unit.symbol, fmt(ratio.value, state), notation(ratio.unit))
    return Outcome(
        title="Custom unit defined",
        headline=text,
        rows=[("Measures", unit.category), ("Aliases", ", ".join(unit.aliases) or "none")],
        assumptions=["Custom units exist for this session; they are available in every screen's unit lists."],
        summary="Defined " + text,
    )


def remove_unit(name: str, state: AppState) -> Outcome:
    state.registry.unregister_unit(name)
    state.changed()
    return Outcome(title="Custom unit removed", headline="Removed %s" % name, summary="Removed unit " + name)
