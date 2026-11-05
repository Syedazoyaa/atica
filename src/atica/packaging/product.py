"""Product model with its own packaging hierarchy."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..calculations.numeric import calc_context, to_decimal
from ..exceptions import InvalidHierarchyError, PackagingError
from ..validation.packaging_rules import validate_levels
from ..validation.result import ValidationResult
from .hierarchy import PackagingLevel, base_sizes, build_chain

PRODUCT_SCHEMA_VERSION = 1


class Product:
    """A product and its packaging hierarchy. Each product is fully independent."""

    def __init__(
        self,
        product_id: str,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not isinstance(product_id, str) or not product_id.strip():
            raise PackagingError("A product needs a non-empty product_id.", code="INVALID_PRODUCT_ID", field="product_id")
        self.product_id = product_id.strip()
        self.name = name if isinstance(name, str) else str(name)
        self.description = description
        self.metadata: Dict[str, Any] = dict(metadata or {})
        self._levels: Dict[str, PackagingLevel] = {}  # casefolded name -> level (insertion order)

    # ------------------------------------------------------------------ levels
    def add_level(self, level: PackagingLevel) -> None:
        if not isinstance(level, PackagingLevel):
            raise InvalidHierarchyError("add_level expects a PackagingLevel.", code="INVALID_LEVEL")
        key = level.name.casefold()
        if key in self._levels:
            raise InvalidHierarchyError(
                "Packaging level %r already exists for product %s." % (level.name, self.product_id),
                code="DUPLICATE_LEVEL",
                field="name",
            )
        self._check_level_quantity(level)
        if level.parent is not None and level.parent.casefold() == key:
            raise InvalidHierarchyError("Level %r cannot contain itself." % level.name, code="CIRCULAR_HIERARCHY", field="parent")
        self._levels[key] = level

    @staticmethod
    def _check_level_quantity(level: PackagingLevel) -> None:
        c = level.contains
        if c <= 0 or c != c.to_integral_value():
            raise InvalidHierarchyError(
                "Level %r must contain a positive whole number of units (got %s)." % (level.name, c),
                code="INVALID_PACKAGE_QUANTITY",
                field="contains",
            )

    def update_level(self, name: str, *, contains: Any = None, parent: Any = "__keep__", metadata: Optional[dict] = None) -> PackagingLevel:
        """Replace a level's quantity / parent. Nothing changes if the new level is invalid."""
        old = self.get_level(name)
        new = PackagingLevel(
            old.name,
            contains=old.contains if contains is None else contains,
            parent=old.parent if parent == "__keep__" else parent,
            metadata=old.metadata if metadata is None else metadata,
        )
        self._check_level_quantity(new)
        if new.parent is not None and new.parent.casefold() == old.name.casefold():
            raise InvalidHierarchyError("Level %r cannot contain itself." % old.name, code="CIRCULAR_HIERARCHY", field="parent")
        self._levels[old.name.casefold()] = new
        return new

    def remove_level(self, name: str) -> None:
        """Remove a level. Refused while another level is built from it."""
        level = self.get_level(name)
        dependents = [lv.name for lv in self._levels.values() if lv.parent and lv.parent.casefold() == level.name.casefold()]
        if dependents:
            raise InvalidHierarchyError(
                "Cannot remove %r: %s is built from it. Remove the larger level first." % (level.name, ", ".join(dependents)),
                code="LEVEL_IN_USE",
                field="name",
            )
        del self._levels[level.name.casefold()]

    def get_level(self, name: str) -> PackagingLevel:
        try:
            return self._levels[name.strip().casefold()]
        except (KeyError, AttributeError):
            raise PackagingError(
                "Product %s has no packaging level %r." % (self.product_id, name), code="UNKNOWN_LEVEL", field="level"
            ) from None

    def has_level(self, name: str) -> bool:
        return isinstance(name, str) and name.strip().casefold() in self._levels

    @property
    def levels(self) -> List[PackagingLevel]:
        """Levels ordered smallest -> largest when valid, otherwise insertion order."""
        if self.validate().valid:
            return build_chain(list(self._levels.values()))
        return list(self._levels.values())

    @property
    def has_levels(self) -> bool:
        return bool(self._levels)

    @property
    def base_packaging_unit(self) -> Optional[str]:
        for lv in self._levels.values():
            if lv.parent is None:
                return lv.name
        return None

    @property
    def packaging_hierarchy(self) -> List[str]:
        return [lv.name for lv in self.levels]

    # -------------------------------------------------------------- validation
    def validate(self) -> ValidationResult:
        return validate_levels(self._levels.values())

    def require_valid(self) -> None:
        self.validate().raise_if_invalid(InvalidHierarchyError)

    # ------------------------------------------------------------- conversions
    def base_size(self, level: str) -> Decimal:
        """How many base units (e.g. pieces) one ``level`` holds."""
        self.require_valid()
        lv = self.get_level(level)
        return base_sizes(build_chain(list(self._levels.values())))[lv.name.casefold()]

    def units_per(self, larger: str, smaller: str) -> Decimal:
        """How many ``smaller`` units make one ``larger`` (may be fractional if reversed)."""
        a, b = self.base_size(larger), self.base_size(smaller)
        with calc_context():
            return a / b

    # ----------------------------------------------------------- serialization
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": PRODUCT_SCHEMA_VERSION,
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
            "levels": [lv.to_dict() for lv in self._levels.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        if not isinstance(data, dict) or "product_id" not in data:
            raise PackagingError("Product data must be an object with a 'product_id'.", code="INVALID_PRODUCT")
        version = data.get("schema_version", 1)
        if not isinstance(version, int) or version < 1 or version > PRODUCT_SCHEMA_VERSION:
            raise PackagingError("Unsupported product schema version %r." % (version,), code="INVALID_PRODUCT")
        meta = data.get("metadata") or {}
        levels = data.get("levels") or []
        if not isinstance(meta, dict) or not isinstance(levels, list):
            raise PackagingError("Product metadata / levels have the wrong type.", code="INVALID_PRODUCT")
        product = cls(data["product_id"], data.get("name", data["product_id"]), data.get("description", ""), meta)
        for item in levels:
            product.add_level(PackagingLevel.from_dict(item))
        return product

    def copy(self) -> "Product":
        return Product.from_dict(self.to_dict())

    def __repr__(self) -> str:
        return "Product(%r, %r, levels=%s)" % (self.product_id, self.name, [lv.name for lv in self._levels.values()])
