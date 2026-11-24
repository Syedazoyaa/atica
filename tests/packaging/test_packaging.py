from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    InvalidHierarchyError,
    InvalidQuantityError,
    UnknownPackagingLevelError,
)
from atica.packaging import (
    PackagingLevel,
    Product,
    breakdown,
    convert_quantity,
    decompose,
    levels_from_pairs,
    packages_required,
)


def D(x):
    return Decimal(x)


class TestSpecExample:
    """1 carton = 20 boxes, 1 box = 12 pieces  =>  1 carton = 240 pieces."""

    def test_250_pieces(self, product):
        r = breakdown(product, 250, "piece", "carton")
        assert r.full_packages == 1  # 240 of the 250 pieces
        assert r.remainder == 10 and r.remainder_unit == "piece"
        assert r.packages_required == 2  # minimum whole cartons to hold everything
        assert r.exact_packages == Decimal(250) / Decimal(240) or abs(
            Fraction(r.exact_packages) - Fraction(25, 24)
        ) < Fraction(1, 10**45)
        assert r.packaged_quantity == 480 and r.surplus == 230
        assert r.units_per_package == 240
        assert str(r) == "250 piece = 1 full carton + 10 piece remaining (2 carton required)"

    def test_exact_vs_whole_distinction(self, product):
        r = breakdown(product, 240, "piece", "carton")
        assert (r.full_packages, r.remainder, r.packages_required, r.surplus) == (1, 0, 1, 0)
        assert r.exact_packages == 1

    def test_decompose_250(self, product):
        plan = decompose(product, 250)
        assert plan.by_level() == {"pallet": 0, "carton": 1, "box": 0, "piece": 10}

    def test_decompose_nested(self, product):
        # 1 pallet + 3 cartons + 5 boxes + 7 pieces = 9600 + 720 + 60 + 7
        plan = decompose(product, 9600 + 720 + 60 + 7)
        assert plan.by_level() == {"pallet": 1, "carton": 3, "box": 5, "piece": 7}

    def test_decompose_from_larger_level(self, product):
        assert decompose(product, "2.5", "carton").by_level() == {
            "pallet": 0,
            "carton": 2,
            "box": 10,
            "piece": 0,
        }

    def test_decompose_fractional_pieces_keep_remainder(self, product):
        assert decompose(product, "12.5").by_level()["piece"] == D("0.5")
        assert decompose(product, "12.5").by_level()["box"] == 1


class TestBreakdownDirections:
    @pytest.mark.parametrize(
        "qty, src, dst, full, rem, rem_unit, required",
        [
            (850, "carton", "pallet", 21, 10, "carton", 22),  # 850 = 21*40 + 10
            (80, "carton", "pallet", 2, 0, "carton", 2),
            (0, "piece", "carton", 0, 0, "piece", 0),
            (1, "piece", "carton", 0, 1, "piece", 1),
            (239, "piece", "carton", 0, 239, "piece", 1),
            (241, "piece", "carton", 1, 1, "piece", 2),
            (5, "box", "box", 5, 0, "box", 5),
            (3, "carton", "box", 60, 0, "box", 60),
            (2, "pallet", "piece", 19200, 0, "piece", 19200),
        ],
    )
    def test_cases(self, product, qty, src, dst, full, rem, rem_unit, required):
        r = breakdown(product, qty, src, dst)
        assert (r.full_packages, r.remainder, r.remainder_unit, r.packages_required) == (
            full,
            rem,
            rem_unit,
            required,
        )

    def test_splitting_down_with_fraction(self, product):
        r = breakdown(product, "2.33", "carton", "box")  # 2.33 * 20 = 46.6 boxes
        assert r.full_packages == 46 and r.remainder == D("0.6") and r.remainder_unit == "box"
        assert r.packages_required == 47 and r.exact_packages == D("46.6")

    def test_fractional_quantity_going_up(self, product):
        r = breakdown(product, "250.5", "piece", "carton")
        assert r.remainder == D("10.5") and r.packages_required == 2

    def test_repeating_ratio_stays_exact(self, product):
        # 1 piece is 1/240 of a carton: ceil must still be exactly 1, floor 0
        r = breakdown(product, 1, "piece", "carton")
        assert (r.full_packages, r.packages_required) == (0, 1)
        # 240 * (1/240) never drifts across the boundary
        assert breakdown(product, 240, "piece", "carton").full_packages == 1

    def test_case_insensitive_levels(self, product):
        assert breakdown(product, 250, " PIECE ", "Carton").full_packages == 1

    def test_quantity_types(self, product):
        for q in (250, "250", D(250), 250.0, Fraction(250)):
            assert breakdown(product, q, "piece", "carton").full_packages == 1

    @pytest.mark.parametrize("bad", [-1, "-0.1", "abc", True, float("nan")])
    def test_invalid_quantity(self, product, bad):
        with pytest.raises(InvalidQuantityError):
            breakdown(product, bad, "piece", "carton")

    def test_missing_quantity(self, product):
        from atica.core import MissingInputError

        with pytest.raises(MissingInputError):
            breakdown(product, None, "piece", "carton")

    def test_require_whole(self, product):
        with pytest.raises(InvalidQuantityError):
            breakdown(product, "1.5", "piece", "box", require_whole=True)
        assert breakdown(product, 2, "piece", "box", require_whole=True).full_packages == 0

    def test_unknown_level(self, product):
        with pytest.raises(UnknownPackagingLevelError) as info:
            breakdown(product, 1, "piece", "crate")
        assert "carton" in info.value.hint

    def test_very_large_quantity(self, product):
        r = breakdown(product, "1e30", "piece", "pallet")
        assert r.full_packages * 9600 + r.remainder == D("1e30")

    def test_very_small_quantity(self, product):
        r = breakdown(product, "0.000001", "piece", "box")
        assert r.full_packages == 0 and r.remainder == D("0.000001") and r.packages_required == 1

    def test_convert_quantity_and_packages_required(self, product):
        assert convert_quantity(product, 850, "carton", "pallet") == D("21.25")
        assert convert_quantity(product, 1, "carton", "piece") == 240
        assert packages_required(product, 250, "piece", "carton") == 2

    def test_to_dict_is_json_safe_with_str(self, product):
        import json

        d = breakdown(product, 250, "piece", "carton").to_dict(numbers="str")
        assert json.loads(json.dumps(d))["packages_required"] == "2"


class TestHierarchyValidation:
    def test_valid_order_independent(self):
        levels = [
            PackagingLevel("carton", 20, "box"),
            PackagingLevel("piece"),
            PackagingLevel("box", 12, "piece"),
        ]
        p = Product("P", "x", levels)
        assert p.level_names == ("piece", "box", "carton")
        assert p.size_of("carton") == 240 and p.units_per("carton", "box") == 20
        assert p.units_per("box", "carton") == D("0.05")

    def test_circular(self):
        with pytest.raises(InvalidHierarchyError, match="circular"):
            Product("P", "x", [PackagingLevel("a", 2, "b"), PackagingLevel("b", 2, "a")])

    def test_cycle_detached_from_base(self):
        with pytest.raises(InvalidHierarchyError):
            Product(
                "P", "x", [PackagingLevel("piece"), PackagingLevel("a", 2, "b"), PackagingLevel("b", 2, "a")]
            )

    def test_self_reference(self):
        with pytest.raises(InvalidHierarchyError):
            PackagingLevel("box", 2, "box")

    def test_duplicate_levels_case_insensitive(self):
        with pytest.raises(InvalidHierarchyError, match="Duplicate"):
            Product(
                "P",
                "x",
                [
                    PackagingLevel("piece"),
                    PackagingLevel("Box", 2, "piece"),
                    PackagingLevel("box", 3, "piece"),
                ],
            )

    def test_two_bases(self):
        with pytest.raises(InvalidHierarchyError, match="base"):
            Product("P", "x", [PackagingLevel("piece"), PackagingLevel("unit")])

    def test_branching_rejected(self):
        with pytest.raises(InvalidHierarchyError, match="single chain"):
            Product(
                "P",
                "x",
                [
                    PackagingLevel("piece"),
                    PackagingLevel("box", 2, "piece"),
                    PackagingLevel("bag", 3, "piece"),
                ],
            )

    def test_missing_parent(self):
        with pytest.raises(InvalidHierarchyError, match="not defined"):
            Product("P", "x", [PackagingLevel("piece"), PackagingLevel("box", 2, "ghost")])

    @pytest.mark.parametrize("contains", [0, -3, "1.5", "abc", None, float("inf")])
    def test_invalid_contains(self, contains):
        with pytest.raises(InvalidHierarchyError):
            PackagingLevel("box", contains, "piece")

    def test_base_must_contain_one(self):
        with pytest.raises(InvalidHierarchyError):
            PackagingLevel("piece", 5)

    @pytest.mark.parametrize("name", ["", "  ", None])
    def test_names(self, name):
        with pytest.raises(InvalidHierarchyError):
            PackagingLevel(name)

    def test_empty_product_cannot_calculate(self):
        p = Product("P001", "Product A")
        with pytest.raises(InvalidHierarchyError, match="no packaging levels"):
            breakdown(p, 1, "piece", "box")

    def test_product_id_required(self):
        with pytest.raises(InvalidHierarchyError):
            Product("  ", "x")


class TestImmutability:
    def test_with_level_returns_new_product(self, product):
        bigger = product.with_level(PackagingLevel("truck", 20, "pallet"))
        assert "truck" not in product.level_names and "truck" in bigger.level_names
        assert bigger.size_of("truck") == 192000

    def test_without_top_level(self, product):
        smaller = product.without_top_level()
        assert smaller.level_names == ("piece", "box", "carton") and len(product.levels) == 4

    def test_invalid_change_leaves_original_intact(self, product):
        with pytest.raises(InvalidHierarchyError):
            product.with_level(PackagingLevel("piece", 2, "carton"))
        assert product.level_names == ("piece", "box", "carton", "pallet")

    def test_frozen(self, product):
        with pytest.raises(AttributeError):
            product.name = "other"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            product.levels[0].name = "x"  # type: ignore[misc]

    def test_calculations_do_not_change_product(self, product):
        before = product.to_dict()
        breakdown(product, 999, "piece", "pallet")
        decompose(product, 999)
        assert product.to_dict() == before

    def test_equality_and_hash(self, product):
        again = Product.from_dict(product.to_dict())
        assert again == product and hash(again) == hash(product)

    def test_round_trip_and_errors(self, product):
        assert Product.from_dict(product.to_dict()).size_of("pallet") == 9600
        with pytest.raises(InvalidHierarchyError):
            Product.from_dict({"name": "no id"})
        with pytest.raises(InvalidHierarchyError):
            Product.from_dict({"product_id": "X", "levels": "nope"})

    def test_levels_from_pairs(self):
        p = Product("P", "x", levels_from_pairs([("piece", 1), ("box", 12), ("carton", 20)]))
        assert p.size_of("carton") == 240
        with pytest.raises(InvalidQuantityError):
            levels_from_pairs([("piece", 2)])


@given(
    st.fractions(min_value=0, max_value=10**6),
    st.sampled_from(["piece", "box", "carton", "pallet"]),
    st.sampled_from(["piece", "box", "carton", "pallet"]),
)
def test_breakdown_invariants(qty, src, dst):
    product = Product(
        "P",
        "x",
        [
            PackagingLevel("piece"),
            PackagingLevel("box", 12, "piece"),
            PackagingLevel("carton", 20, "box"),
            PackagingLevel("pallet", 40, "carton"),
        ],
    )
    sizes = {"piece": 1, "box": 12, "carton": 240, "pallet": 9600}
    r = breakdown(product, qty, src, dst)
    tol = Fraction(1, 10**35)
    exact = qty * sizes[src] / Fraction(sizes[dst])
    assert abs(Fraction(r.exact_packages) - exact) < tol
    assert (
        r.full_packages <= Fraction(r.exact_packages) + tol
        and r.packages_required >= Fraction(r.exact_packages) - tol
    )
    assert r.packages_required - r.full_packages in (0, 1)
    assert r.surplus >= -Fraction(1, 10**35) and Fraction(r.packaged_quantity) + tol >= qty
    if sizes[dst] >= sizes[src]:
        per = Fraction(sizes[dst], sizes[src])
        assert abs(Fraction(r.full_packages) * per + Fraction(r.remainder) - qty) < tol
        assert 0 <= r.remainder < per


@given(st.integers(min_value=0, max_value=10**9))
def test_decompose_reassembles(total):
    product = Product(
        "P",
        "x",
        [PackagingLevel("piece"), PackagingLevel("box", 12, "piece"), PackagingLevel("carton", 20, "box")],
    )
    plan = decompose(product, total).by_level()
    assert plan["carton"] * 240 + plan["box"] * 12 + plan["piece"] == total
    assert 0 <= plan["box"] < 20 and 0 <= plan["piece"] < 12
