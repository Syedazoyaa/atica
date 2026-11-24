"""Shared fixtures. Expected values in tests are written out by hand or taken from published
constants - never computed with the library's own formulas."""

from __future__ import annotations

import os

import pytest

# Qt must never need a display during tests.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from atica.packaging import PackagingLevel, Product
from atica.units import UnitRegistry


@pytest.fixture
def product() -> Product:
    """1 box = 12 pieces, 1 carton = 20 boxes (=240 pieces), 1 pallet = 40 cartons (=9600 pieces)."""
    return Product(
        "P001",
        "Product A",
        levels=[
            PackagingLevel("piece"),
            PackagingLevel("box", 12, "piece"),
            PackagingLevel("carton", 20, "box"),
            PackagingLevel("pallet", 40, "carton"),
        ],
    )


@pytest.fixture
def registry() -> UnitRegistry:
    reg = UnitRegistry()
    reg.register_unit("bag", 25, "kg")
    return reg
