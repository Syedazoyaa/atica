"""Packaging levels and chain resolution.

Direction of a relationship
---------------------------
``PackagingLevel(name, contains, parent)`` states that **one ``name`` contains
``contains`` units of the level called ``parent``** - i.e. ``parent`` is the
immediate *smaller* level. The base level (smallest, e.g. a piece) has no
parent and ``contains == 1``::

    PackagingLevel("piece",  contains=1)
    PackagingLevel("box",    contains=12, parent="piece")    # 1 box    = 12 pieces
    PackagingLevel("carton", contains=20, parent="box")      # 1 carton = 20 boxes
    PackagingLevel("pallet", contains=40, parent="carton")   # 1 pallet = 40 cartons
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..calculations.numeric import plain_number, to_decimal
from ..exceptions import InvalidHierarchyError, InvalidQuantityError


@dataclass(frozen=True)
class PackagingLevel:
    name: str
    contains: Decimal = Decimal(1)
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidHierarchyError("A packaging level needs a non-empty name.", code="INVALID_LEVEL_NAME", field="name")
        object.__setattr__(self, "name", self.name.strip())
        try:
            contains = to_decimal(self.contains, field="contains")
        except InvalidQuantityError as exc:
            raise InvalidHierarchyError(
                "Level %r: %s" % (self.name, exc.message), code="INVALID_PACKAGE_QUANTITY", field="contains"
            ) from exc
        object.__setattr__(self, "contains", contains)
        if self.parent is not None:
            if not isinstance(self.parent, str) or not self.parent.strip():
                raise InvalidHierarchyError("Parent level name must be a non-empty string.", field="parent")
            object.__setattr__(self, "parent", self.parent.strip())

    @property
    def level_id(self) -> str:
        return self.name

    @property
    def quantity_per_parent(self) -> Decimal:
        return self.contains

    @property
    def is_base_level(self) -> bool:
        return self.parent is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "contains": plain_number(self.contains),
            "parent": self.parent,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackagingLevel":
        if not isinstance(data, dict) or "name" not in data:
            raise InvalidHierarchyError("A packaging level must be an object with a 'name'.", code="INVALID_LEVEL")
        meta = data.get("metadata") or {}
        if not isinstance(meta, dict):
            raise InvalidHierarchyError("Level metadata must be an object.", code="INVALID_LEVEL")
        return cls(
            name=data["name"],
            contains=data.get("contains", 1),
            parent=data.get("parent"),
            metadata=meta,
        )


def build_chain(levels: List[PackagingLevel]) -> List[PackagingLevel]:
    """Order *valid* levels from smallest (base) to largest. Validate first."""
    by_parent = {lv.parent.casefold(): lv for lv in levels if lv.parent}
    current = next(lv for lv in levels if lv.parent is None)
    chain = [current]
    while current.name.casefold() in by_parent:
        current = by_parent[current.name.casefold()]
        chain.append(current)
    return chain


def base_sizes(chain: List[PackagingLevel]) -> Dict[str, Decimal]:
    """Map each level (casefolded name) to how many base units it holds."""
    sizes: Dict[str, Decimal] = {}
    running = Decimal(1)
    for lv in chain:
        running = running * lv.contains if lv.parent else Decimal(1)
        sizes[lv.name.casefold()] = running
    return sizes
