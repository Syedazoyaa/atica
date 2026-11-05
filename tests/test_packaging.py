from decimal import Decimal

import pytest

from atica.exceptions import InvalidHierarchyError, PackagingError
from atica.packaging import PackagingLevel, Product


def codes(product):
    return {e.code for e in product.validate().errors}


def raw_product(*levels):
    """Build a product bypassing add_level's early checks, to test validation of loaded data."""
    p = Product("X", "X")
    for lv in levels:
        p._levels[lv.name.casefold()] = lv
    return p


def test_spec_example_builds_valid_chain(product_a):
    assert product_a.validate().valid
    assert product_a.packaging_hierarchy == ["piece", "box", "carton", "pallet"]
    assert product_a.base_packaging_unit == "piece"
    assert product_a.base_size("pallet") == 40 * 20 * 12
    assert product_a.units_per("pallet", "carton") == 40
    assert product_a.units_per("carton", "pallet") == Decimal("0.025")


def test_levels_can_be_added_in_any_order():
    p = Product("P", "P")
    p.add_level(PackagingLevel("pallet", 40, parent="carton"))
    p.add_level(PackagingLevel("carton", 20, parent="piece"))
    p.add_level(PackagingLevel("piece", 1))
    assert p.packaging_hierarchy == ["piece", "carton", "pallet"]


def test_products_are_independent(product_a, product_b):
    assert product_a.base_size("pallet") == 9600
    assert product_b.base_size("pallet") == 50 * 10 * 24
    product_b.update_level("box", contains=6)
    assert product_a.get_level("box").contains == 12  # no leakage


def test_levels_lookup_is_case_insensitive(product_a):
    assert product_a.get_level("CARTON").name == "carton"
    assert product_a.has_level("Pallet")
    with pytest.raises(InvalidHierarchyError):
        product_a.add_level(PackagingLevel("PALLET", 3, parent="carton"))


def test_duplicate_level_rejected(product_a):
    with pytest.raises(InvalidHierarchyError) as e:
        product_a.add_level(PackagingLevel("box", 5, parent="piece"))
    assert e.value.code == "DUPLICATE_LEVEL"


@pytest.mark.parametrize("bad", [0, -3, "1.5", "x"])
def test_invalid_package_quantity_rejected(bad):
    p = Product("P", "P")
    p.add_level(PackagingLevel("piece", 1))
    with pytest.raises(InvalidHierarchyError) as e:
        p.add_level(PackagingLevel("box", bad, parent="piece"))
    assert e.value.code == "INVALID_PACKAGE_QUANTITY"


def test_self_reference_rejected():
    p = Product("P", "P")
    with pytest.raises(InvalidHierarchyError) as e:
        p.add_level(PackagingLevel("box", 2, parent="box"))
    assert e.value.code == "CIRCULAR_HIERARCHY"


def test_missing_parent_detected():
    p = Product("P", "P")
    p.add_level(PackagingLevel("piece", 1))
    p.add_level(PackagingLevel("pallet", 40, parent="carton"))
    assert "MISSING_LEVEL" in codes(p)


def test_circular_hierarchy_detected():
    p = raw_product(PackagingLevel("a", 2, "b"), PackagingLevel("b", 2, "a"))
    assert "CIRCULAR_HIERARCHY" in codes(p)
    p = raw_product(PackagingLevel("piece", 1), PackagingLevel("a", 2, "b"), PackagingLevel("b", 2, "a"))
    assert "CIRCULAR_HIERARCHY" in codes(p)


def test_disconnected_branches_detected():
    two_roots = raw_product(PackagingLevel("piece", 1), PackagingLevel("unit", 1))
    assert "DISCONNECTED_HIERARCHY" in codes(two_roots)
    branch = raw_product(
        PackagingLevel("piece", 1), PackagingLevel("box", 5, "piece"), PackagingLevel("bundle", 3, "piece")
    )
    assert "DISCONNECTED_HIERARCHY" in codes(branch)


def test_base_level_must_contain_one():
    p = raw_product(PackagingLevel("piece", 3))
    assert "INCONSISTENT_RELATIONSHIP" in codes(p)


def test_empty_product_invalid():
    assert codes(Product("P", "P")) == {"MISSING_LEVELS"}


def test_invalid_hierarchy_blocks_calculations():
    p = Product("P", "P")
    p.add_level(PackagingLevel("pallet", 40, parent="carton"))
    with pytest.raises(InvalidHierarchyError):
        p.base_size("pallet")


def test_remove_level(product_a):
    with pytest.raises(InvalidHierarchyError) as e:
        product_a.remove_level("box")
    assert e.value.code == "LEVEL_IN_USE"
    product_a.remove_level("pallet")
    assert product_a.packaging_hierarchy == ["piece", "box", "carton"]
    with pytest.raises(PackagingError) as e:
        product_a.remove_level("pallet")
    assert e.value.code == "UNKNOWN_LEVEL"


def test_update_level_validates(product_a):
    product_a.update_level("pallet", contains=10)
    assert product_a.base_size("pallet") == 10 * 20 * 12
    with pytest.raises(InvalidHierarchyError):
        product_a.update_level("pallet", contains=0)
    assert product_a.get_level("pallet").contains == 10  # unchanged after failure


def test_serialization_round_trip(product_a):
    product_a.metadata["colour"] = "blue"
    clone = Product.from_dict(product_a.to_dict())
    assert clone.to_dict() == product_a.to_dict()
    assert clone.base_size("pallet") == 9600
    assert clone.metadata == {"colour": "blue"}


def test_copy_is_independent(product_a):
    clone = product_a.copy()
    clone.update_level("box", contains=1)
    assert product_a.get_level("box").contains == 12


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"product_id": "P", "levels": "nope"},
        {"product_id": "P", "levels": [5]},
        {"product_id": "P", "levels": [{"contains": 1}]},
        {"product_id": "P", "schema_version": 99},
    ],
)
def test_from_dict_rejects_malformed(data):
    with pytest.raises(PackagingError):
        Product.from_dict(data)


def test_product_requires_id():
    with pytest.raises(PackagingError):
        Product("  ", "x")
