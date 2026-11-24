from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    InvalidQuantityError,
    InvalidRoundingError,
    NumericRangeError,
    PackageRounding,
    Rounding,
    ValidationError,
    get_precision,
    round_to_multiple,
    round_value,
    split_by_multiple,
    to_decimal,
    use_precision,
)
from atica.core.precision import dec, display_decimal, normalize, to_fraction


class TestToDecimal:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            (5, "5"),
            ("0.1", "0.1"),
            (0.1, "0.1"),
            (Decimal("2.50"), "2.50"),
            (" 7 ", "7"),
            ("1e3", "1E+3"),
            (Fraction(1, 4), "0.25"),
        ],
    )
    def test_accepts(self, raw, expected):
        assert to_decimal(raw) == Decimal(expected)

    def test_float_is_not_binary_expanded(self):
        assert to_decimal(0.1) == Decimal("0.1")
        assert to_decimal(0.1 + 0.2) == Decimal("0.30000000000000004")  # what the float really is

    @pytest.mark.parametrize(
        "bad", [None, True, False, "abc", "", "NaN", "inf", float("nan"), float("inf"), [], {}, "1,5"]
    )
    def test_rejects(self, bad):
        with pytest.raises(InvalidQuantityError):
            to_decimal(bad, "qty")

    def test_error_names_parameter(self):
        with pytest.raises(InvalidQuantityError) as info:
            to_decimal("x", "batch_size")
        assert info.value.parameter == "batch_size"
        assert info.value.hint

    @pytest.mark.parametrize("huge", ["1e301", "1e-301", Decimal("1E+5000")])
    def test_range_limit(self, huge):
        with pytest.raises(NumericRangeError):
            to_decimal(huge)

    def test_limit_edge_ok(self):
        assert to_decimal("1e300") == Decimal("1e300")
        assert to_decimal("1e-300") == Decimal("1e-300")


class TestPrecision:
    def test_default_and_override(self):
        assert get_precision() == 50
        with use_precision(10):
            assert get_precision() == 10
            assert str(dec(Fraction(1, 3))) == "0.3333333333"
        assert get_precision() == 50

    def test_repeating_decimal_has_configured_digits(self):
        assert len(str(dec(Fraction(2, 3))).replace("0.", "")) == 50

    @pytest.mark.parametrize("bad", [0, 4, 1001, "10", True, 3.5])
    def test_invalid_precision(self, bad):
        with pytest.raises(InvalidQuantityError), use_precision(bad):
            pass

    def test_exact_fractions_stay_exact(self):
        assert dec(Fraction(5, 4)) == Decimal("1.25")
        assert dec(Fraction(10**40)) == Decimal(10**40)

    def test_normalize_and_display(self):
        assert str(normalize(Decimal("2500.00"))) == "2500"
        assert str(normalize(Decimal("1E+3"))) == "1000"
        assert str(normalize(Decimal("0.50"))) == "0.5"
        assert str(normalize(Decimal("0.000"))) == "0"
        assert display_decimal(Decimal(1) / Decimal(3)) == "0.3333333333"
        assert display_decimal(Decimal("12.5000")) == "12.5"
        assert display_decimal(Decimal("100")) == "100"

    def test_to_fraction_ratio_strings(self):
        assert to_fraction("5/9") == Fraction(5, 9)
        assert to_fraction("0.25") == Fraction(1, 4)
        with pytest.raises(InvalidQuantityError):
            to_fraction("1/0")


@pytest.mark.parametrize(
    "value, mode, places, expected",
    [
        ("2.5", "half_up", 0, "3"),
        ("3.5", "half_up", 0, "4"),
        ("-2.5", "half_up", 0, "-3"),
        ("2.5", "half_even", 0, "2"),
        ("3.5", "half_even", 0, "4"),
        ("2.675", "half_up", 2, "2.68"),  # exact decimal, unlike float 2.675
        ("2.675", "half_even", 2, "2.68"),
        ("2.665", "half_even", 2, "2.66"),
        ("2.001", "ceiling", 2, "2.01"),
        ("2.999", "floor", 2, "2.99"),
        ("-2.001", "ceiling", 2, "-2.00"),
        ("-2.001", "floor", 2, "-2.01"),
        ("1234", "half_up", -2, "1.2E+3"),
        ("1250", "half_even", -2, "1.2E+3"),
        ("7", "none", 0, "7"),
        ("0.4999999", "half_up", 0, "0"),
        ("0.5", "half_up", 0, "1"),
    ],
)
def test_round_value(value, mode, places, expected):
    assert round_value(value, mode, places) == Decimal(expected)


class TestRoundingConfig:
    def test_parse_variants(self):
        assert Rounding.parse("Half-Up") is Rounding.HALF_UP
        assert Rounding.parse("HALF EVEN") is Rounding.HALF_EVEN
        assert Rounding.parse(None) is Rounding.NONE
        assert Rounding.parse(Rounding.FLOOR) is Rounding.FLOOR

    @pytest.mark.parametrize("bad", ["nearest", 3, "", "up"])
    def test_unknown(self, bad):
        with pytest.raises(InvalidRoundingError):
            Rounding.parse(bad)

    def test_places_without_policy_is_contradictory(self):
        with pytest.raises(InvalidRoundingError):
            round_value("1.5", "none", 2)

    @pytest.mark.parametrize("bad", [1.5, "2", True, 101, -101])
    def test_bad_places(self, bad):
        with pytest.raises(InvalidRoundingError):
            round_value("1.5", "half_up", bad)

    def test_floor_ceiling_decided_on_exact_value(self):
        # 1/3 + 1/3 + 1/3 as exact fractions is exactly 1: no float/decimal drift.
        third = Fraction(1, 3)
        assert round_value(third * 3, "ceiling") == 1
        assert round_value(third * 3, "floor") == 1
        # a tiny excess beyond 1 must still ceil to 2
        assert round_value(Fraction(1) + Fraction(1, 10**60), "ceiling") == 2


class TestPackageRounding:
    @pytest.mark.parametrize(
        "value, multiple, mode, expected",
        [
            (250, 240, "ceiling", "480"),
            (250, 240, "floor", "240"),
            (240, 240, "ceiling", "240"),
            (0, 12, "ceiling", "0"),
            ("0.1", "0.25", "ceiling", "0.25"),
            (7, 1, "floor", "7"),
            (95, 10, "package_ceiling", "100"),
            (95, 10, "package_floor", "90"),
        ],
    )
    def test_round_to_multiple(self, value, multiple, mode, expected):
        assert round_to_multiple(value, multiple, mode) == Decimal(expected)

    @pytest.mark.parametrize("bad", [0, -5])
    def test_multiple_must_be_positive(self, bad):
        with pytest.raises(ValidationError):
            round_to_multiple(10, bad)

    def test_unknown_mode(self):
        with pytest.raises(InvalidRoundingError):
            round_to_multiple(10, 3, "nearest")

    def test_split_preserves_remainder(self):
        s = split_by_multiple(250, 240)
        assert (s.packages, s.remainder) == (Decimal(1), Decimal(10))
        s = split_by_multiple("10.5", 4)
        assert (s.packages, s.remainder) == (Decimal(2), Decimal("2.5"))
        s = split_by_multiple(0, 4)
        assert (s.packages, s.remainder) == (0, 0)

    def test_split_rejects_negative(self):
        with pytest.raises(ValidationError):
            split_by_multiple(-1, 4)

    def test_modes_enum(self):
        assert PackageRounding.parse("floor") is PackageRounding.FLOOR


@given(st.fractions(min_value=0, max_value=10**6), st.integers(min_value=1, max_value=500))
def test_split_invariant(value, multiple):
    s = split_by_multiple(value, multiple)
    # Decimal results are rounded at 50 digits, hence the tolerance for fractions like 1/7.
    assert abs(Fraction(s.packages) * multiple + Fraction(s.remainder) - value) < Fraction(1, 10**40)
    assert 0 <= s.remainder < multiple


@given(st.fractions(min_value=-(10**5), max_value=10**5), st.integers(min_value=0, max_value=6))
def test_floor_le_value_le_ceiling(value, places):
    lo, hi = Fraction(round_value(value, "floor", places)), Fraction(round_value(value, "ceiling", places))
    assert lo <= value + Fraction(1, 10**40) and hi >= value - Fraction(1, 10**40)
    assert hi - lo in (0, Fraction(1, 10**places))
