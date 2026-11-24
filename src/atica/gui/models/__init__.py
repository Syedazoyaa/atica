"""Qt-free data models shared by the GUI layers.

* :class:`Field`       - declarative description of one input control;
* :class:`Outcome`     - what a controller returns to a view (already formatted for display);
* :class:`ResultTable` - an optional table inside an outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Field:
    """One input of a calculation form.

    ``key`` equals the name of the core API argument it feeds, so an error raised by the core
    (which names its ``parameter``) can highlight exactly this field.

    ``kind``: ``number`` | ``text`` | ``choice`` | ``unit`` | ``checkbox``.
    ``unit_kinds`` restricts a ``unit`` field to those measurement categories (empty = all).
    """

    key: str
    label: str
    kind: str = "number"
    default: str = ""
    placeholder: str = ""
    tooltip: str = ""
    options: Sequence[Tuple[str, str]] = ()  # (label, value) for ``choice``
    unit_kinds: Tuple[str, ...] = ()
    suffix: str = ""
    advanced: bool = False  # shown in a collapsible "More options" section


@dataclass
class ResultTable:
    """A small table of result rows (all cells pre-formatted strings)."""

    title: str
    columns: List[str]
    rows: List[List[str]]


@dataclass
class Outcome:
    """Presentation-ready result of one calculation."""

    title: str
    headline: str  # the main answer, e.g. "25 000 g"
    rows: List[Tuple[str, str]] = field(default_factory=list)  # label / value details
    tables: List[ResultTable] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    formula: str = ""
    assumptions: List[str] = field(default_factory=list)
    summary: str = ""  # one line for the activity log

    def as_text(self) -> str:
        """Plain text (used for *Copy*)."""
        lines = [self.title, self.headline, ""]
        lines += ["%s: %s" % (k, v) for k, v in self.rows]
        for table in self.tables:
            lines += ["", table.title, "\t".join(table.columns)]
            lines += ["\t".join(r) for r in table.rows]
        if self.formula:
            lines += ["", "Formula: " + self.formula]
        lines += ["", *("Note: " + a for a in self.assumptions), *("Warning: " + w for w in self.warnings)]
        return "\n".join(lines).strip()

    def as_rows(self) -> List[Dict[str, str]]:
        """Structured rows for CSV/Excel export."""
        out: List[Dict[str, str]] = [{"section": self.title, "item": "result", "value": self.headline}]
        out += [{"section": self.title, "item": k, "value": v} for k, v in self.rows]
        for table in self.tables:
            for r in table.rows:
                out.append(
                    {
                        "section": table.title,
                        "item": r[0],
                        "value": "; ".join("%s=%s" % (c, v) for c, v in zip(table.columns[1:], r[1:])),
                    }
                )
        out += [{"section": self.title, "item": "warning", "value": w} for w in self.warnings]
        return out
