from decimal import Decimal

import pytest

from atica.exceptions import InvalidHierarchyError, InvalidQuantityError, PackagingError
from atica.packaging import PackagingLevel, Product, breakdown, convert_quantity, decompose


def test_spec_example(product_a):
    r = breakdown(product=product_a, quantity="850", from_unit="carton", to_unit="pallet")
    assert r.to_dict() == {
        "full_packages": 21,
        "remaining_quantity": 10,
        "packages_required": 22,
        "total_quantity": 850,
        "exact_equivalent": Decimal("21.25"),
    }
    assert r.full_packages == 21 and r.remaining_quantity == 10 and r.packages_required == 22
    assert r.package_size == 40
    assert "21 full pallet" in str(r) and "10 carton remaining" in str(r)


def test_exact_multiple_has_no_remainder(product_a):
    r = breakdown(product_a, 800, "carton", "pallet")
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (20, 0, 20)


def test_smaller_than_one_package(product_a):
    r = breakdown(product_a, 10, "carton", "pallet")
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (0, 10, 1)


def test_zero_quantity(product_a):
    r = breakdown(product_a, 0, "carton", "pallet")
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (0, 0, 0)


def test_across_several_levels(product_a):
    r = breakdown(product_a, 10000, "piece", "pallet")  # 9600 pieces per pallet
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (1, 400, 2)


def test_larger_to_smaller(product_a):
    r = breakdown(product_a, 2, "pallet", "carton")
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (80, 0, 80)


def test_same_unit(product_a):
    r = breakdown(product_a, 7, "box", "box")
    assert (r.full_packages, r.remaining_quantity) == (7, 0)


def test_products_with_different_hierarchies(product_a, product_b):
    assert breakdown(product_a, 850, "carton", "pallet").full_packages == 21
    rb = breakdown(product_b, 850, "carton", "pallet")
    assert (rb.full_packages, rb.remaining_quantity, rb.packages_required) == (17, 0, 17)


def test_fractional_requires_opt_in(product_a):
    with pytest.raises(InvalidQuantityError) as e:
        breakdown(product_a, "850.5", "carton", "pallet")
    assert e.value.code == "PARTIAL_NOT_ALLOWED"
    r = breakdown(product_a, "850.5", "carton", "pallet", allow_partial=True)
    assert r.remaining_quantity == Decimal("10.5") and r.full_packages == 21


def test_partial_pallet_to_cartons(product_a):
    r = breakdown(product_a, "0.5", "pallet", "carton", allow_partial=True)
    assert r.full_packages == 20 and r.remaining_quantity == 0


def test_negative_rejected(product_a):
    with pytest.raises(InvalidQuantityError) as e:
        breakdown(product_a, -1, "carton", "pallet")
    assert e.value.code == "NEGATIVE_QUANTITY"


@pytest.mark.parametrize("bad", ["abc", None, "", float("nan")])
def test_invalid_quantity(product_a, bad):
    with pytest.raises(InvalidQuantityError):
        breakdown(product_a, bad, "carton", "pallet")


def test_unknown_level(product_a):
    with pytest.raises(PackagingError) as e:
        breakdown(product_a, 5, "carton", "container")
    assert e.value.code == "UNKNOWN_LEVEL"


def test_not_a_product():
    with pytest.raises(PackagingError):
        breakdown("PROD-1", 5, "carton", "pallet")


def test_invalid_hierarchy_rejected():
    p = Product("P", "P")
    p.add_level(PackagingLevel("piece", 1))
    p.add_level(PackagingLevel("pallet", 40, parent="carton"))
    with pytest.raises(InvalidHierarchyError):
        breakdown(p, 5, "piece", "pallet")


def test_breakdown_does_not_mutate_product(product_a):
    before = product_a.to_dict()
    breakdown(product_a, 850, "carton", "pallet")
    assert product_a.to_dict() == before


def test_very_large_quantity(product_a):
    r = breakdown(product_a, "1000000000000000000000", "carton", "pallet")
    assert r.full_packages == Decimal("25000000000000000000")
    assert r.remaining_quantity == 0


def test_convert_quantity(product_a):
    assert convert_quantity(product_a, 850, "carton", "pallet") == Decimal("21.25")
    assert convert_quantity(product_a, 2, "pallet", "piece") == 19200


def test_decompose(product_a):
    assert decompose(product_a, 262, "piece") == {"pallet": 0, "carton": 1, "box": 1, "piece": 10}
    out = decompose(product_a, 850, "carton")
    assert out["pallet"] == 21 and out["carton"] == 10 and out["box"] == 0 and out["piece"] == 0
    with pytest.raises(InvalidQuantityError):
        decompose(product_a, "0.5", "piece")
