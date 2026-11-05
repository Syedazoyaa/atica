"""Versioned save / load of a complete ATICA configuration.

The file is plain JSON (never pickle, never executable content). The
``schema_version`` field lets future releases migrate older files.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List

from .exceptions import ConfigurationError, UnknownProductError
from .inventory.purchasing import PurchasingConfig
from .manufacturing.materials import Material
from .packaging.product import Product
from .units.registry import UnitRegistry

CONFIG_TYPE = "atica.configuration"
CURRENT_SCHEMA_VERSION = 1

#: version -> function upgrading a config dict from that version to version + 1
MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade an older configuration dict to the current schema."""
    version = data.get("schema_version")
    if not isinstance(version, int) or version < 1:
        raise ConfigurationError("Configuration has no valid schema_version.")
    if version > CURRENT_SCHEMA_VERSION:
        raise ConfigurationError(
            "Configuration version %d is newer than this ATICA release supports (%d)." % (version, CURRENT_SCHEMA_VERSION)
        )
    while version < CURRENT_SCHEMA_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["schema_version"] = version
    return data


class AticaConfig:
    """Custom units, products, materials and purchasing rules in one saveable object."""

    def __init__(self) -> None:
        self.registry = UnitRegistry()
        self.products: Dict[str, Product] = {}
        self.materials: Dict[str, Material] = {}
        self.purchasing: List[PurchasingConfig] = []

    # ---- products
    def add_product(self, product: Product) -> None:
        if product.product_id in self.products:
            raise ConfigurationError("Product %r already exists." % product.product_id, code="DUPLICATE_PRODUCT")
        self.products[product.product_id] = product

    def get_product(self, product_id: str) -> Product:
        try:
            return self.products[product_id]
        except KeyError:
            raise UnknownProductError("Unknown product %r." % (product_id,), field="product") from None

    def remove_product(self, product_id: str) -> None:
        self.get_product(product_id)
        del self.products[product_id]

    # ---- materials / purchasing
    def add_material(self, material: Material) -> None:
        if material.material_id in self.materials:
            raise ConfigurationError("Material %r already exists." % material.material_id, code="DUPLICATE_MATERIAL")
        self.materials[material.material_id] = material

    def add_purchasing(self, config: PurchasingConfig) -> None:
        self.purchasing.append(config)

    # ---- persistence
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": CONFIG_TYPE,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "units": self.registry.to_dict(),
            "products": [p.to_dict() for p in self.products.values()],
            "materials": [m.to_dict() for m in self.materials.values()],
            "purchasing": [c.to_dict() for c in self.purchasing],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AticaConfig":
        if not isinstance(data, dict) or data.get("type") != CONFIG_TYPE:
            raise ConfigurationError("Not an ATICA configuration file.")
        data = migrate(dict(data))
        cfg = cls()
        for key in ("products", "materials", "purchasing"):
            if not isinstance(data.get(key, []), list):
                raise ConfigurationError("'%s' must be a list." % key)
        try:
            cfg.registry.load_dict(data.get("units") or cfg.registry.to_dict())
            for item in data.get("products", []):
                product = Product.from_dict(item)
                if product.has_levels:  # products with no levels yet are allowed as drafts
                    product.require_valid()
                cfg.add_product(product)
            for item in data.get("materials", []):
                cfg.add_material(Material.from_dict(item))
            for item in data.get("purchasing", []):
                cfg.add_purchasing(PurchasingConfig.from_dict(item))
        except ConfigurationError:
            raise
        except Exception as exc:  # any ATICA error while rebuilding -> clear configuration error
            message = getattr(exc, "message", None) or str(exc)
            raise ConfigurationError("Invalid configuration: %s" % message, details=exc) from exc
        return cfg

    def save(self, path: Any) -> None:
        """Write atomically (temp file + replace) so a crash cannot corrupt an existing file."""
        target = os.fspath(path)
        tmp = target + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, indent=2)
            os.replace(tmp, target)
        except OSError as exc:
            raise ConfigurationError("Cannot save configuration: %s" % exc) from exc

    @classmethod
    def load(cls, path: Any) -> "AticaConfig":
        try:
            with open(os.fspath(path), "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise ConfigurationError("Cannot read configuration: %s" % exc) from exc
        return cls.from_dict(data)
