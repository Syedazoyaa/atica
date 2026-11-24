"""Packaging levels and the immutable :class:`Product` that owns a hierarchy.

Direction of a relationship
---------------------------
``PackagingLevel(name, contains, of)`` states that **one ``name`` contains
``contains`` units of the level called ``of``** (the next *smaller* level).  The
smallest ("base") level has no ``of`` and contains exactly 1::

    PackagingLevel("piece")
    PackagingLevel("box", 12, "piece")      # 1 box    = 12 pieces
    PackagingLevel("carton", 20, "box")     # 1 carton = 20 boxes
    PackagingLevel("pallet", 40, "carton")  # 1 pallet = 40 cartons

A product has exactly one such chain.  Names are matched ignoring case and
surrounding spaces, so ``"Carton"`` finds ``carton``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.exceptions import (
    InvalidHierarchyError,
    InvalidQuantityError,
    UnknownPackagingLevelError,
    ValidationError,
)
from ..core.precision import fraction_to_decimal, normalize, to_fraction
from ..core.validation import text


def _key(name: str) -> str:
    return name.strip().casefold()


@dataclass(frozen=True)
class PackagingLevel:
    """One level of a packaging hierarchy (see the module docstring for the direction)."""

    name: str
    contains: Decimal = Decimal(1)
    of: Optional[str] = None

    def __post_init__(self) -> None:
        try:
            name = text(self.name, "name", max_length=64)
        except ValidationError as exc:
            raise InvalidHierarchyError(
                "A packaging level needs a non-empty name.", parameter="name"
            ) from exc
        object.__setattr__(self, "name", name)
        try:
            contains = to_fraction(self.contains, "contains")
        except ValidationError as exc:
            raise InvalidHierarchyError("Level %r: %s" % (name, exc.message), parameter="contains") from exc
        if contains <= 0 or contains.denominator != 1:
            raise InvalidHierarchyError(
                "Level %r must contain a positive whole number of units (got %s)." % (name, self.contains),
                parameter="contains",
                hint="Use whole numbers such as 12; a box cannot hold 12.5 pieces.",
            )
        object.__setattr__(self, "contains", Decimal(contains.numerator))
        if self.of is not None:
            try:
                of = text(self.of, "of", max_length=64)
            except ValidationError as exc:
                raise InvalidHierarchyError(
                    "Level %r: 'of' must be a level name." % name, parameter="of"
                ) from exc
            if _key(of) == _key(name):
                raise InvalidHierarchyError(
                    "Level %r cannot contain itself." % name,
                    parameter="of",
                    hint="Name the next smaller level.",
                )
            object.__setattr__(self, "of", of)
        elif contains != 1:
            raise InvalidHierarchyError(
                "Base level %r (without 'of') must contain exactly 1 (got %s)." % (name, self.contains),
                parameter="contains",
                hint="Say what it contains, e.g. PackagingLevel(%r, %s, of='piece')." % (name, self.contains),
            )

    @property
    def is_base(self) -> bool:
        return self.of is None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "contains": int(self.contains), "of": self.of}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PackagingLevel:
        if not isinstance(data, Mapping) or "name" not in data:
            raise InvalidHierarchyError(
                "A packaging level must be an object with a 'name'.", parameter="levels"
            )
        return cls(data["name"], data.get("contains", 1), data.get("of"))


def _build_chain(levels: Tuple[PackagingLevel, ...]) -> Tuple[PackagingLevel, ...]:
    """Validate ``levels`` and return them ordered smallest -> largest."""
    by_key: Dict[str, PackagingLevel] = {}
    for level in levels:
        k = _key(level.name)
        if k in by_key:
            raise InvalidHierarchyError(
                "Duplicate packaging level %r." % level.name,
                parameter="levels",
                hint="Level names must be unique (ignoring case).",
            )
        by_key[k] = level
    bases = [lv for lv in levels if lv.of is None]
    if not bases:
        raise InvalidHierarchyError(
            "No base level: every level refers to another one, so the hierarchy is circular.",
            parameter="levels",
            hint="Exactly one level (the smallest, e.g. 'piece') must have no 'of'.",
        )
    if len(bases) > 1:
        raise InvalidHierarchyError(
            "Several base levels found (%s); a single chain is required." % ", ".join(b.name for b in bases),
            parameter="levels",
        )
    children: Dict[str, List[PackagingLevel]] = {}
    for level in levels:
        if level.of is None:
            continue
        parent_key = _key(level.of)
        if parent_key not in by_key:
            raise InvalidHierarchyError(
                "Level %r is built from %r, which is not defined." % (level.name, level.of),
                parameter="of",
                hint="Add a level named %r or correct the name." % level.of,
            )
        children.setdefault(parent_key, []).append(level)
    for parent_key, kids in children.items():
        if len(kids) > 1:
            raise InvalidHierarchyError(
                "Levels %s are all built from %r; packaging must be a single chain."
                % (", ".join(repr(k.name) for k in kids), by_key[parent_key].name),
                parameter="of",
            )
    chain = [bases[0]]
    while _key(chain[-1].name) in children:
        chain.append(children[_key(chain[-1].name)][0])
    if len(chain) != len(levels):
        missing = [lv.name for lv in levels if lv not in chain]
        raise InvalidHierarchyError(
            "Levels not connected to the base level (circular): %s." % ", ".join(missing), parameter="levels"
        )
    return tuple(chain)


@dataclass(frozen=True)
class Product:
    """A product and its (immutable) packaging hierarchy.

    The hierarchy is validated on construction, so a ``Product`` is always consistent.
    "Modifying" a product returns a new one (:meth:`with_level`, :meth:`without_top_level`);
    the original is never changed.

    >>> p = Product("P001", "Product A", levels=[
    ...     PackagingLevel("piece"), PackagingLevel("box", 12, "piece"), PackagingLevel("carton", 20, "box")])
    >>> p.size_of("carton")
    Decimal('240')
    """

    product_id: str
    name: str = ""
    levels: Tuple[PackagingLevel, ...] = ()
    _sizes: Dict[str, Fraction] = field(default_factory=dict, init=False, repr=False, compare=False)
    _levels_by_key: Dict[str, PackagingLevel] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "product_id", text(self.product_id, "product_id"))
        except ValidationError as exc:
            raise InvalidHierarchyError(
                "A product needs a non-empty product_id.", parameter="product_id"
            ) from exc
        object.__setattr__(self, "name", (self.name or "").strip())
        raw = tuple(self.levels)
        for level in raw:
            if not isinstance(level, PackagingLevel):
                raise InvalidHierarchyError(
                    "levels must contain PackagingLevel objects (got %s)." % type(level).__name__,
                    parameter="levels",
                )
        chain = _build_chain(raw) if raw else ()
        object.__setattr__(self, "levels", chain)
        sizes: Dict[str, Fraction] = {}
        running = Fraction(1)
        for level in chain:
            running = running * int(level.contains) if level.of else Fraction(1)
            sizes[_key(level.name)] = running
        object.__setattr__(self, "_sizes", sizes)
        object.__setattr__(self, "_levels_by_key", {_key(lv.name): lv for lv in chain})

    # ---------------------------------------------------------------- queries
    @property
    def level_names(self) -> Tuple[str, ...]:
        """Level names, smallest first."""
        return tuple(lv.name for lv in self.levels)

    @property
    def base_level(self) -> PackagingLevel:
        self._require_levels()
        return self.levels[0]

    def has_level(self, name: str) -> bool:
        return isinstance(name, str) and _key(name) in self._levels_by_key

    def level(self, name: str) -> PackagingLevel:
        """The level called ``name`` (case-insensitive)."""
        self._require_levels()
        if isinstance(name, str):
            found = self._levels_by_key.get(_key(name))
            if found is not None:
                return found
        raise UnknownPackagingLevelError(
            "Product %s has no packaging level %r." % (self.product_id, name),
            parameter="level",
            hint="Available levels: %s." % ", ".join(self.level_names),
        )

    def _require_levels(self) -> None:
        if not self.levels:
            raise InvalidHierarchyError(
                "Product %s has no packaging levels." % self.product_id,
                parameter="levels",
                hint="Create the product with levels=[PackagingLevel(...), ...].",
            )

    def _size(self, name: str) -> Fraction:
        return self._sizes[_key(self.level(name).name)]

    def size_of(self, name: str) -> Decimal:
        """How many base units (e.g. pieces) one ``name`` holds."""
        return normalize(fraction_to_decimal(self._size(name)))

    def units_per(self, larger: str, smaller: str) -> Decimal:
        """How many ``smaller`` units make one ``larger`` (a fraction if ``larger`` is the smaller one)."""
        return normalize(fraction_to_decimal(self._size(larger) / self._size(smaller)))

    # ---------------------------------------------------- derived (new) products
    def with_level(self, level: PackagingLevel) -> Product:
        """A new product with ``level`` added (this product is unchanged)."""
        return Product(self.product_id, self.name, (*self.levels, level))

    def without_top_level(self) -> Product:
        """A new product without its largest level."""
        self._require_levels()
        return Product(self.product_id, self.name, self.levels[:-1])

    # ---------------------------------------------------------- serialisation
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "levels": [lv.to_dict() for lv in self.levels],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Product:
        if not isinstance(data, Mapping) or "product_id" not in data:
            raise InvalidHierarchyError(
                "Product data must be an object with a 'product_id'.", parameter="data"
            )
        levels = data.get("levels") or []
        if not isinstance(levels, (list, tuple)):
            raise InvalidHierarchyError("'levels' must be a list.", parameter="levels")
        return cls(
            data["product_id"], data.get("name", ""), tuple(PackagingLevel.from_dict(x) for x in levels)
        )


def levels_from_pairs(pairs: Iterable[Tuple[str, Any]]) -> Tuple[PackagingLevel, ...]:
    """Helper: ``[("piece", 1), ("box", 12), ("carton", 20)]`` -> a chain of levels (smallest first)."""
    result: List[PackagingLevel] = []
    previous: Optional[str] = None
    for name, count in pairs:
        if previous is None:
            if to_fraction(count, "contains") != 1:
                raise InvalidQuantityError(
                    "The first (base) level must have a count of 1.", parameter="contains"
                )
            result.append(PackagingLevel(name))
        else:
            result.append(PackagingLevel(name, count, previous))
        previous = name
    return tuple(result)
