from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    ConstraintError,
    InvalidConfigurationError,
    InvalidPercentageError,
    InvalidQuantityError,
    ValidationError,
    ZeroDenominatorError,
)
from atica.quality import (
    calculate_expected_output,
    calculate_material_recovery,
    calculate_required_input,
    calculate_rework,
    calculate_scrap_percentage,
    calculate_scrap_quantity,
    calculate_wastage,
    calculate_yield,
    required_input_with_rework,
)


def D(x):
    return Decimal(x)


class TestScrap:
    @pytest.mark.parametrize(
        "fn, args, expected",
        [
            (calculate_scrap_quantity, (1000, 5), "50"),
            (calculate_scrap_quantity, (1000, 0), "0"),
            (calculate_scrap_quantity, (1000, 100), "1000"),
            (calculate_scrap_quantity, (0, 50), "0"),
            (calculate_expected_output, (1000, 5), "950"),
            (calculate_expected_output, (1000, 100), "0"),  # 100% scrap is valid here
            (calculate_expected_output, (1000, 0), "1000"),
            (calculate_expected_output, ("33", "33.3"), "22.011"),
            (calculate_required_input, (950, 5), "1000"),
            (calculate_required_input, (0, 100), "0"),
            (calculate_required_input, (900, 10), "1000"),
            (calculate_required_input, (1, 0), "1"),
        ],
    )
    def test_values(self, fn, args, expected):
        assert fn(*args).quantity == D(expected)

    def test_required_input_is_inverse_of_expected_output(self):
        for scrap in (0, 1, "2.5", 10, 33, 99):
            need = calculate_required_input(1000, scrap).exact_quantity
            got = calculate_expected_output(need, scrap).quantity
            assert abs(Fraction(got) - 1000) < Fraction(1, 10**35)

    def test_required_input_rounding_guarantees_target(self):
        r = calculate_required_input(1000, 5, rounding="ceiling")
        assert r.exact_quantity > 1052 and r.quantity == 1053 and r.rounding.value == "ceiling"
        assert float(1053 * 0.95) >= 1000

    def test_100_percent_scrap_needs_infinite_input(self):
        with pytest.raises(ConstraintError):
            calculate_required_input(10, 100)

    @pytest.mark.parametrize("pct", [-0.1, 100.01, "abc", 150])
    def test_percent_range(self, pct):
        for fn in (calculate_scrap_quantity, calculate_expected_output, calculate_required_input):
            with pytest.raises((InvalidPercentageError, InvalidQuantityError)):
                fn(100, pct)

    def test_fraction_given_as_percent_is_explicit_not_guessed(self):
        assert calculate_scrap_quantity(1000, "0.05").quantity == D("0.5")  # 0.05 percent, per docs

    def test_scrap_percentage_and_denominator(self):
        p = calculate_scrap_percentage(1000, 50)
        assert p.percent == 5 and p.denominator == 1000 and "input" in p.denominator_meaning
        assert str(p) == "5%"
        assert abs(Fraction(calculate_scrap_percentage(3, 1).percent) - Fraction(100, 3)) < Fraction(
            1, 10**40
        )
        assert calculate_scrap_percentage(10, 10).percent == 100
        assert calculate_scrap_percentage(10, 0).percent == 0

    def test_scrap_percentage_zero_input_and_overflow(self):
        with pytest.raises(ZeroDenominatorError) as info:
            calculate_scrap_percentage(0, 0)
        assert info.value.hint
        with pytest.raises(ValidationError):
            calculate_scrap_percentage(10, 11)

    def test_rounding_and_unit(self):
        r = calculate_scrap_quantity(333, "2.5", rounding="half_up", places=1, unit="kg")
        assert r.exact_quantity == D("8.325") and r.quantity == D("8.3")  # 8.32|5 -> second decimal decides
        assert str(r).endswith("kg")


class TestYield:
    def test_distinguishes_first_pass_from_final(self):
        r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
        assert r.first_pass_yield_percent == 90
        assert r.final_yield_percent == D("94.5")
        assert (r.first_pass_scrap, r.rework_scrap, r.final_scrap) == (40, 15, 55)
        assert r.final_good == 945 and r.scrap_percent == D("5.5") and r.rework_percent == 6
        assert r.rework_recovery_percent == 75

    def test_no_double_counting(self):
        r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
        assert r.final_good + r.final_scrap == r.input_quantity
        assert r.good_first_pass + r.sent_to_rework + r.first_pass_scrap == r.input_quantity
        assert r.recovered_from_rework + r.rework_scrap == r.sent_to_rework

    def test_without_rework(self):
        r = calculate_yield(200, 150)
        assert r.first_pass_yield_percent == r.final_yield_percent == 75
        assert r.scrap_percent == 25 and r.rework_recovery_percent is None and r.warnings

    def test_zero_yield(self):
        r = calculate_yield(100, 0)
        assert r.first_pass_yield_percent == 0 and r.scrap_percent == 100 and r.final_good == 0

    def test_all_good(self):
        r = calculate_yield(100, 100)
        assert r.final_yield_percent == 100 and r.final_scrap == 0

    def test_everything_reworked_and_recovered(self):
        r = calculate_yield(100, 0, sent_to_rework=100, recovered_from_rework=100)
        assert (r.first_pass_yield_percent, r.final_yield_percent, r.scrap_percent) == (0, 100, 0)

    def test_nothing_recovered(self):
        r = calculate_yield(100, 80, sent_to_rework=20)
        assert r.final_yield_percent == 80 and r.final_scrap == 20 and r.rework_recovery_percent == 0

    def test_zero_input(self):
        with pytest.raises(ZeroDenominatorError):
            calculate_yield(0, 0)

    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(good_first_pass=101),
            dict(good_first_pass=60, sent_to_rework=41),
            dict(good_first_pass=50, sent_to_rework=10, recovered_from_rework=11),
            dict(good_first_pass=50, sent_to_rework=10, first_pass_scrap=39),
            dict(good_first_pass=-1),
        ],
    )
    def test_contradictions(self, kwargs):
        with pytest.raises(ValidationError):
            calculate_yield(100, **kwargs)

    def test_explicit_first_pass_scrap_consistent(self):
        r = calculate_yield(100, 50, sent_to_rework=10, first_pass_scrap=40)
        assert (r.first_pass_scrap, r.final_scrap) == (40, 50)  # the 10 reworked units were not recovered

    def test_fractional_quantities(self):
        r = calculate_yield("12.5", "10", sent_to_rework="1.25", recovered_from_rework="1")
        assert r.first_pass_yield_percent == 80 and r.final_yield_percent == 88


class TestRework:
    def test_projection(self):
        p = calculate_rework(1000, first_pass_yield_percent=90, rework_percent=6, rework_recovery_percent=75)
        assert (p.good_first_pass, p.sent_to_rework, p.first_pass_scrap) == (900, 60, 40)
        assert (p.recovered_from_rework, p.rework_scrap, p.final_good, p.final_scrap) == (45, 15, 945, 55)
        assert p.final_yield_percent == D("94.5") and p.scrap_percent == D("5.5")

    def test_consistent_with_calculate_yield(self):
        p = calculate_rework(1000, first_pass_yield_percent=90, rework_percent=6, rework_recovery_percent=75)
        y = calculate_yield(
            1000,
            p.good_first_pass,
            sent_to_rework=p.sent_to_rework,
            recovered_from_rework=p.recovered_from_rework,
        )
        assert y.final_yield_percent == p.final_yield_percent and y.final_scrap == p.final_scrap

    def test_default_full_recovery_and_no_rework(self):
        assert calculate_rework(100, first_pass_yield_percent=80, rework_percent=20).final_good == 100
        assert calculate_rework(100, first_pass_yield_percent=80).final_good == 80

    def test_zero_input(self):
        p = calculate_rework(0, first_pass_yield_percent=50)
        assert p.final_good == 0 and p.final_yield_percent == 50

    def test_overcommitted_rates(self):
        with pytest.raises(InvalidConfigurationError):
            calculate_rework(100, first_pass_yield_percent=90, rework_percent=11)

    def test_required_input_with_rework(self):
        # final yield 94.5% -> 945 good needs 1000 started
        assert (
            required_input_with_rework(
                945, first_pass_yield_percent=90, rework_percent=6, rework_recovery_percent=75
            )
            == 1000
        )
        assert required_input_with_rework(0, first_pass_yield_percent=0) == 0
        with pytest.raises(ZeroDenominatorError):
            required_input_with_rework(5, first_pass_yield_percent=0)


class TestWastageAndRecovery:
    def test_wastage_basic(self):
        r = calculate_wastage(1000, 920)
        assert (r.gross_wastage, r.net_wastage, r.gross_wastage_percent, r.utilisation_percent) == (
            80,
            80,
            8,
            92,
        )
        assert r.recovery_percent == 0

    def test_recovery_percent_denominator_is_the_waste(self):
        r = calculate_wastage(1000, 920, recovery_percent=25)
        assert (r.recovered, r.net_wastage, r.net_wastage_percent, r.recovery_percent) == (20, 60, 6, 25)

    def test_recovery_quantity(self):
        r = calculate_wastage(1000, 920, recovered_quantity=40)
        assert r.net_wastage == 40 and r.recovery_percent == 50

    def test_both_recovery_args(self):
        with pytest.raises(InvalidConfigurationError):
            calculate_wastage(1000, 920, recovered_quantity=1, recovery_percent=1)

    def test_no_waste(self):
        r = calculate_wastage(100, 100)
        assert r.gross_wastage == 0 and r.recovery_percent is None and r.warnings

    def test_total_waste(self):
        assert calculate_wastage(100, 0).gross_wastage_percent == 100

    @pytest.mark.parametrize(
        "args, exc",
        [((0, 0), ZeroDenominatorError), ((100, 101), ValidationError), ((-1, 0), InvalidQuantityError)],
    )
    def test_invalid(self, args, exc):
        with pytest.raises(exc):
            calculate_wastage(*args)

    def test_recovery_exceeding_waste(self):
        with pytest.raises(ValidationError):
            calculate_wastage(100, 90, recovered_quantity=11)

    def test_material_recovery(self):
        r = calculate_material_recovery(200, 40)
        assert (r.recovered_quantity, r.unrecovered_quantity) == (80, 120)
        assert calculate_material_recovery(0, 50).recovered_quantity == 0
        assert calculate_material_recovery(10, 100).unrecovered_quantity == 0
        with pytest.raises(InvalidPercentageError):
            calculate_material_recovery(10, 101)


@given(
    st.integers(min_value=1, max_value=10**6),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=100),
)
def test_yield_conservation(total, a, b):
    good = total * a // 100
    rework = (total - good) * b // 100
    recovered = rework // 2
    r = calculate_yield(total, good, sent_to_rework=rework, recovered_from_rework=recovered)
    assert r.final_good + r.final_scrap == total
    assert r.first_pass_yield_percent <= r.final_yield_percent
    assert abs(Fraction(r.final_yield_percent) + Fraction(r.scrap_percent) - 100) < Fraction(1, 10**30)


@given(st.fractions(min_value=0, max_value=10**6), st.fractions(min_value=0, max_value=99))
def test_input_output_roundtrip(good, scrap):
    need = calculate_required_input(good, scrap)
    back = calculate_expected_output(need.exact_quantity, scrap)
    assert abs(Fraction(back.exact_quantity) - good) <= Fraction(1, 10**30) * max(1, good)
