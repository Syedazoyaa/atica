import pytest

from atica.packaging import PackagingLevel, Product
from atica.units import UnitRegistry, reset_default_registry


def build_product(product_id, name, box, carton, pallet):
    p = Product(product_id, name)
    p.add_level(PackagingLevel("piece", contains=1))
    p.add_level(PackagingLevel("box", contains=box, parent="piece"))
    p.add_level(PackagingLevel("carton", contains=carton, parent="box"))
    p.add_level(PackagingLevel("pallet", contains=pallet, parent="carton"))
    return p


@pytest.fixture(autouse=True)
def _fresh_default_registry():
    reset_default_registry()
    yield
    reset_default_registry()


@pytest.fixture
def registry():
    return UnitRegistry()


@pytest.fixture
def product_a():
    # 1 pallet = 40 cartons, 1 carton = 20 boxes, 1 box = 12 pieces
    return build_product("PROD-A", "Product A", 12, 20, 40)


@pytest.fixture
def product_b():
    # 1 pallet = 50 cartons, 1 carton = 10 boxes, 1 box = 24 pieces
    return build_product("PROD-B", "Product B", 24, 10, 50)
