"""Turn the text typed into GUI tables into core objects (``Product``, ``Bom``).

Only construction - all validation and arithmetic stay in the core.
"""

from __future__ import annotations

from typing import List, Sequence

from atica.core import AticaError, MissingInputError
from atica.materials import Bom, BomItem
from atica.packaging import PackagingLevel, Product


def build_product(product_id: str, name: str, rows: Sequence[Sequence[str]]) -> Product:
    """``rows`` are ``[level name, contains]`` from the smallest level up; the first row is the base level."""
    levels: List[PackagingLevel] = []
    previous = None
    for index, row in enumerate(rows, start=1):
        level_name = (row[0] if row else "").strip()
        if not level_name:
            continue  # blank rows are ignored
        count = (row[1] if len(row) > 1 else "").strip()
        try:
            if previous is None:
                levels.append(PackagingLevel(level_name))
            else:
                if not count:
                    raise MissingInputError(
                        "Level %r needs a count." % level_name,
                        parameter="contains",
                        hint="Enter how many %s one %s contains." % (previous, level_name),
                    )
                levels.append(PackagingLevel(level_name, count, previous))
        except AticaError as exc:
            exc.message = "Row %d: %s" % (index, exc.message)
            raise
        previous = level_name
    if not levels:
        raise MissingInputError(
            "Add at least one packaging level.",
            parameter="levels",
            hint="Start with the smallest unit, e.g. 'piece'.",
        )
    return Product(product_id or "PRODUCT", name, levels)


def build_bom(rows: Sequence[Sequence[str]], *, allow_duplicates: bool = False) -> Bom:
    """``rows`` are ``[material id, quantity per unit, unit, wastage %, name]``; blank rows are ignored.

    The wastage and name cells are optional.
    """
    items: List[BomItem] = []
    for index, row in enumerate(rows, start=1):
        cells = [(c or "").strip() for c in ([*list(row), "", "", "", "", ""])[:5]]
        if not any(cells):
            continue
        try:
            items.append(BomItem(cells[0], cells[1], cells[2], cells[3] or "0", cells[4]))
        except AticaError as exc:
            exc.message = "BOM row %d: %s" % (index, exc.message)
            raise
    if not items:
        raise MissingInputError(
            "The BOM has no materials.",
            parameter="items",
            hint="Add at least one material row in the BOM editor.",
        )
    return Bom(tuple(items), allow_duplicates=allow_duplicates)
