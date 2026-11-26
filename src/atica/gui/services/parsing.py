"""Turn the text typed into GUI tables into core objects (``Product``, ``Bom``).

Only construction - all validation and arithmetic stay in the core.
"""

from __future__ import annotations

from typing import List, Sequence

from atica.core import AticaError, MissingInputError
from atica.materials import Bom, BomItem
from atica.packaging import PackagingLevel, Product

from ..utils.messages import enter_number, translate

#: library argument -> (column of the BOM editor, its heading)
_BOM_COLUMNS = {
    "material_id": (0, "Material"),
    "quantity_per_unit": (1, "Qty per unit"),
    "unit": (2, "Unit"),
    "wastage_percent": (3, "Wastage %"),
}


def _bom_message(exc: AticaError, cells: Sequence[str]) -> str:
    column = _BOM_COLUMNS.get(exc.parameter or "")
    if column is None:
        return exc.message
    index, heading = column
    numeric = exc.parameter in ("quantity_per_unit", "wastage_percent")
    if numeric and (not cells[index] or "is not a valid number" in exc.message):
        return enter_number(heading, blank=not cells[index])
    if not cells[index]:
        return "Fill in %s." % heading
    return translate(
        exc.message, {k: h for k, (_i, h) in _BOM_COLUMNS.items() if "_" in k or k == exc.parameter}
    )[0]


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
            if "is not a valid number" in exc.message:
                exc.message = enter_number("Contains", blank=False)
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
            exc.message = "BOM row %d: %s" % (index, _bom_message(exc, cells))
            raise
    if not items:
        raise MissingInputError(
            "The BOM has no materials.",
            parameter="items",
            hint="Add at least one material row in the BOM editor.",
        )
    return Bom(tuple(items), allow_duplicates=allow_duplicates)
