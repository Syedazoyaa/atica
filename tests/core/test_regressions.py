"""Regression tests: each one pins a defect that was found and fixed."""

from decimal import Decimal
from fractions import Fraction

import pytest

from atica.core import NumericRangeError, UnitDefinitionError, to_decimal, validation
from atica.core.precision import check_fraction_magnitude, to_fraction
from atica.materials import Bom, BomItem, calculate_bom_requirements
from atica.packaging import PackagingLevel, Product, breakdown
from atica.production import calculate_batch_materials
from atica.quality import calculate_rework, required_input_with_rework
from atica.units import UnitRegistry, convert

HUGE = Fraction(10**301)  # one step beyond the documented limit
TINY = Fraction(1, 10**301)


class TestFractionMagnitudeLimits:
    """Direct Fraction input obeys the same limits as int / Decimal / float / str input."""

    @pytest.mark.parametrize("value", [HUGE, -HUGE, TINY, -TINY, Fraction(10**400), Fraction(1, 10**500)])
    def test_out_of_range_fractions_are_rejected_everywhere(self, value):
        for call in (
            lambda: to_fraction(value, "q"),
            lambda: to_decimal(value, "q"),
            lambda: validation.number(value, "q"),
            lambda: convert(value, "kg", "g"),
        ):
            with pytest.raises(NumericRangeError) as info:
                call()
            assert info.value.parameter in ("q", "value")

    @pytest.mark.parametrize(
        "value", [Fraction(10**301 - 1), Fraction(1, 10**300), Fraction(7, 3), Fraction(0)]
    )
    def test_in_range_fractions_are_accepted_and_stay_exact(self, value):
        assert to_fraction(value) == value

    def test_same_boundary_as_other_input_types(self):
        for accepted in (10**300, "1e300", Decimal("1E-300"), 1e300):
            assert to_decimal(accepted) != 0
        for rejected in (10**301, "1e301", Decimal("1E-301"), 1e301):
            with pytest.raises(NumericRangeError):
                to_decimal(rejected)
        # the Fraction boundary matches: 1e300 ok, 1e301 not (1e301 itself is out of range for every type)
        assert check_fraction_magnitude(Fraction(10**300)) == 10**300
        with pytest.raises(NumericRangeError):
            check_fraction_magnitude(Fraction(10**301))

    def test_ratio_strings_are_checked_after_division(self):
        assert to_fraction("1/3") == Fraction(1, 3)
        with pytest.raises(NumericRangeError):
            to_fraction("1/" + "9" + "0" * 400)
        with pytest.raises(NumericRangeError):
            to_fraction("1" + "0" * 400 + "/3")

    def test_calculations_reject_huge_fraction_arguments_with_the_parameter_name(self, product):
        with pytest.raises(NumericRangeError) as info:
            breakdown(product, HUGE, "piece", "carton")
        assert info.value.parameter == "quantity"

    def test_error_message_states_the_limit(self):
        with pytest.raises(NumericRangeError, match="1e300"):
            to_decimal(HUGE, "x")

    def test_huge_in_range_fraction_converts_exactly(self):
        value = Fraction(10**300, 3)
        result = convert(value, "g", "kg")
        assert abs(Fraction(result.value) - value / 1000) <= Fraction(
            10**250
        )  # rounded to 50 significant digits of a 298-digit number


class TestBaseUnitAliases:
    def test_duplicate_alias_is_rejected(self):
        with pytest.raises(UnitDefinitionError, match="Duplicate alias"):
            UnitRegistry().register_base_unit("sheet", "paper", aliases=["sheets", "sheets"])

    def test_alias_equal_to_name_is_rejected(self):
        with pytest.raises(UnitDefinitionError, match="Duplicate alias"):
            UnitRegistry().register_base_unit("sheet", "paper", aliases=["sheet"])

    def test_alias_that_exists_elsewhere_is_rejected(self):
        with pytest.raises(UnitDefinitionError):
            UnitRegistry().register_base_unit("sheet", "paper", aliases=["kg"])

    def test_single_string_is_not_split_into_characters(self):
        reg = UnitRegistry()
        with pytest.raises(UnitDefinitionError, match="list of names"):
            reg.register_base_unit("sheet", "paper", aliases="sheets")
        with pytest.raises(UnitDefinitionError, match="list of names"):
            reg.register_unit("bag", 25, "kg", aliases="bags")
        assert "bag" not in reg and "sheet" not in reg  # nothing was half-registered

    def test_valid_aliases_resolve_and_failed_registration_leaves_no_trace(self):
        reg = UnitRegistry()
        reg.register_base_unit("sheet", "paper", aliases=["sheets", "sh"])
        assert reg.get("sh").symbol == "sheet"
        with pytest.raises(UnitDefinitionError):
            reg.register_base_unit("ream", "paper2", aliases=["rm", "rm"])
        assert "ream" not in reg and "rm" not in reg and "paper2" not in reg.categories()


def thirds_bom(duplicates=False):
    items = [BomItem("resin", "0.3", "kg", wastage_percent=7), BomItem("dye", "11", "g", wastage_percent=3)]
    if duplicates:
        items.append(BomItem("resin", "250", "g", wastage_percent=1))
    return Bom(items, allow_duplicates=duplicates)


class TestBatchMaterialsAreBuiltFromExactFractions:
    @pytest.mark.parametrize(
        "quantity, size, scrap",
        [(250, 100, 5), ("1000", 300, 7), ("777.7", 13, 3), (1, 3, 11), ("0.5", 7, 0), (999, 1000, 33)],
    )
    @pytest.mark.parametrize("duplicates", [False, True])
    def test_unrounded_totals_equal_one_run_exactly(self, quantity, size, scrap, duplicates):
        bom = thirds_bom(duplicates)
        plan = calculate_batch_materials(bom, quantity, size, scrap_percent=scrap)
        whole = calculate_bom_requirements(bom, quantity, scrap_percent=scrap)
        for row, total in zip(plan.materials, whole.totals):
            # identical Decimals: both come from the same exact fraction, not from a rounded sum
            assert row.exact_total == total.exact_quantity
            assert row.total == total.exact_quantity

    def test_rounded_totals_are_the_sum_of_what_is_issued(self):
        bom = Bom([BomItem("m", "0.3333", "kg")])
        plan = calculate_batch_materials(bom, 250, 100, rounding="half_up", places=2)
        row = plan.materials[0]
        assert row.per_full_batch == Decimal("33.33") and row.partial_batch == Decimal("16.67")
        assert row.total == 2 * Decimal("33.33") + Decimal("16.67") == Decimal("83.33")
        assert row.exact_total == Decimal("0.3333") * 250  # 83.325

    def test_no_precision_loss_with_a_repeating_scrap_factor(self):
        bom = Bom([BomItem("m", "1", "kg")])
        plan = calculate_batch_materials(bom, "1e12", 3, scrap_percent=1)
        expected = Fraction(10**12) / Fraction(99, 100)
        assert abs(Fraction(plan.materials[0].exact_total) - expected) < Fraction(1, 10**30)
        assert (
            plan.materials[0].exact_total
            == calculate_bom_requirements(bom, "1e12", scrap_percent=1)["m"].exact_quantity
        )

    def test_merged_duplicates_are_summed_from_exact_parts(self):
        bom = Bom(
            [BomItem("a", "1", "kg", wastage_percent=1), BomItem("a", "1", "kg", wastage_percent=2)],
            allow_duplicates=True,
        )
        r = calculate_bom_requirements(bom, 3, scrap_percent=7)
        expected = Fraction(3) / Fraction(93, 100) * (1 / Fraction(99, 100) + 1 / Fraction(98, 100))
        assert abs(Fraction(r["a"].exact_quantity) - expected) < Fraction(1, 10**45)
        parts = sum(
            Fraction(getattr(r["a"], f)) for f in ("base_quantity", "scrap_allowance", "wastage_allowance")
        )
        assert abs(parts - expected) < Fraction(1, 10**45)  # the allowances add up to the total


class TestRequiredInputWithReworkIsExact:
    @pytest.mark.parametrize(
        "fpy, rework, recovery",
        [
            ("100/3", "100/3", "100/7"),
            (90, 6, 75),
            ("99.9", "0.1", 50),
            (1, 0, 100),
            ("33.333333333333333333", 33, 33),
        ],
    )
    def test_matches_an_independent_exact_oracle(self, fpy, rework, recovery):
        f, r, c = Fraction(fpy), Fraction(rework), Fraction(recovery)
        final = (f + r * c / 100) / 100
        result = required_input_with_rework(
            1000, first_pass_yield_percent=fpy, rework_percent=rework, rework_recovery_percent=recovery
        )
        assert abs(Fraction(result) - 1000 / final) < Fraction(1, 10**44) * (1000 / final)

    def test_round_trip_through_the_projection(self):
        kwargs = {
            "first_pass_yield_percent": "100/3",
            "rework_percent": "100/3",
            "rework_recovery_percent": "100/7",
        }
        needed = required_input_with_rework(1000, **kwargs)
        # feeding the (50-digit) answer back must reproduce the target to far better than a rounded yield could
        projected = calculate_rework(needed, **kwargs).final_good
        assert abs(Fraction(projected) - 1000) < Fraction(1, 10**40)

    def test_not_derived_from_a_rounded_percentage(self):
        """Old code divided by Decimal(final_yield_percent) - a 50-digit rounding of a repeating value."""
        kwargs = {
            "first_pass_yield_percent": "100/3",
            "rework_percent": "100/3",
            "rework_recovery_percent": 100,
        }
        # FPY 100/3 + all 100/3 reworked units recovered = exactly 2/3 final yield -> 1500 for 1000 good
        assert required_input_with_rework(1000, **kwargs) == 1500

    @pytest.mark.parametrize(
        "target, fpy, expected",
        [
            (1, "100/7", "7"),
            (1000, "100/7", "7000"),
            (10**6, "100/7", "7000000"),
            (1, "100/9", "9"),
            ("123456.789", "100/3", "370370"),
        ],
    )
    def test_reduced_precision_does_not_leak_a_rounded_yield_into_the_answer(self, target, fpy, expected):
        """Earlier development builds divided by an already-rounded yield: at 6 digits 1 / (1/7) came out as 7.00001."""
        from atica.core import use_precision

        with use_precision(6):
            result = required_input_with_rework(target, first_pass_yield_percent=fpy)
        assert result == Decimal(expected)

    def test_zero_target_and_zero_yield_and_invalid_rates(self):
        from atica.core import InvalidConfigurationError, ZeroDenominatorError

        assert required_input_with_rework(0, first_pass_yield_percent=0) == 0
        with pytest.raises(ZeroDenominatorError):
            required_input_with_rework(
                1, first_pass_yield_percent=0, rework_percent=50, rework_recovery_percent=0
            )
        with pytest.raises(InvalidConfigurationError):
            required_input_with_rework(1, first_pass_yield_percent=60, rework_percent=50)

    def test_recovered_units_are_never_double_counted(self):
        kwargs = {"first_pass_yield_percent": 80, "rework_percent": 20, "rework_recovery_percent": 50}
        p = calculate_rework(1000, **kwargs)
        assert p.final_good + p.final_scrap == p.input_quantity
        assert p.good_first_pass + p.recovered_from_rework == p.final_good  # recovered units only once
        assert required_input_with_rework(p.final_good, **kwargs) == 1000


def test_product_levels_unaffected_by_limits(product):
    assert isinstance(product, Product) and PackagingLevel("x").contains == 1
