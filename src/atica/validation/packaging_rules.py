"""Packaging hierarchy validation rules.

Direction: a level's ``parent`` names the immediate *smaller* level that it is
built from, and ``contains`` says how many of those it holds
(``PackagingLevel("box", contains=12, parent="piece")`` = 1 box holds 12 pieces).
The base level has no ``parent`` and always ``contains == 1``.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List

from .result import ValidationResult


def validate_levels(levels: Iterable) -> ValidationResult:
    """Validate a collection of packaging levels (objects with name/contains/parent)."""
    result = ValidationResult()
    levels = list(levels)
    if not levels:
        result.add_error("MISSING_LEVELS", "levels", "The product has no packaging levels.")
        return result

    by_name: Dict[str, object] = {}
    for lv in levels:
        key = lv.name.casefold()
        if key in by_name:
            result.add_error("DUPLICATE_LEVEL", "levels", "Duplicate packaging level %r." % lv.name)
        else:
            by_name[key] = lv

    for lv in levels:
        c = lv.contains
        if not isinstance(c, Decimal) or not c.is_finite() or c <= 0 or c != c.to_integral_value():
            result.add_error(
                "INVALID_PACKAGE_QUANTITY",
                "contains",
                "Level %r must contain a positive whole number of units (got %s)." % (lv.name, c),
            )

    roots: List = []
    children = defaultdict(list)
    for lv in levels:
        if lv.parent is None:
            roots.append(lv)
            if isinstance(lv.contains, Decimal) and lv.contains != 1:
                result.add_error(
                    "INCONSISTENT_RELATIONSHIP",
                    "contains",
                    "Base level %r must contain exactly 1 (got %s)." % (lv.name, lv.contains),
                )
            continue
        pkey = lv.parent.casefold()
        if pkey == lv.name.casefold():
            result.add_error("CIRCULAR_HIERARCHY", "parent", "Level %r cannot contain itself." % lv.name)
        elif pkey not in by_name:
            result.add_error(
                "MISSING_LEVEL", "parent", "Level %r refers to undefined level %r." % (lv.name, lv.parent)
            )
        else:
            children[pkey].append(lv)

    if len(roots) == 0:
        result.add_error(
            "CIRCULAR_HIERARCHY", "levels", "No base level (a level without parent) was found; the hierarchy is circular."
        )
    elif len(roots) > 1:
        result.add_error(
            "DISCONNECTED_HIERARCHY",
            "levels",
            "Multiple base levels found: %s. A single chain is required." % ", ".join(r.name for r in roots),
        )
    for pkey, kids in children.items():
        if len(kids) > 1:
            result.add_error(
                "DISCONNECTED_HIERARCHY",
                "parent",
                "Several levels (%s) are built from %r; a single chain is required."
                % (", ".join(k.name for k in kids), by_name[pkey].name),
            )

    # Cycle / reachability check: walk upward from the root(s).
    if result.valid:
        seen = set()
        current = roots[0]
        while current is not None:
            seen.add(current.name.casefold())
            nxt = children.get(current.name.casefold(), [])
            current = nxt[0] if nxt else None
        unreachable = [lv.name for lv in levels if lv.name.casefold() not in seen]
        if unreachable:
            result.add_error(
                "CIRCULAR_HIERARCHY",
                "levels",
                "Levels not connected to the base level (circular or disconnected): %s."
                % ", ".join(unreachable),
            )
    return result
