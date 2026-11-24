"""Unit conversion tests.

Expected values are published constants (NIST SP 811 / SI brochure / international agreements),
written as literals - not derived from the library's tables.
"""

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    IncompatibleUnitError,
    InvalidQuantityError,
    InvalidRoundingError,
    UnitDefinitionError,
    UnknownUnitError,
    UnsupportedOperationError,
)
from atica.units import UnitRegistry, are_compatible, convert, default_registry, list_categories, list_units


def D(x):
    return Decimal(x)


# (value, from, to, expected exact)  -- 1 of the first unit expressed in the second
EXACT = [
    (1, "in", "mm", "25.4"),
    (1, "ft", "in", "12"),
    (1, "yd", "ft", "3"),
    (1, "mi", "m", "1609.344"),
    (1, "mi", "ft", "5280"),
    (1, "km", "m", "1000"),
    (1, "lb", "g", "453.59237"),
    (1, "lb", "oz", "16"),
    (1, "t", "kg", "1000"),
    (1, "kg", "mg", "1000000"),
    (1, "gal", "L", "3.785411784"),
    (1, "gal", "qt", "4"),
    (1, "gal", "pt", "8"),
    (1, "gal", "fl_oz", "128"),
    (1, "m3", "L", "1000"),
    (1, "mL", "cm3", "1"),
    (1, "acre", "m2", "4046.8564224"),
    (1, "acre", "ft2", "43560"),
    (1, "ha", "m2", "10000"),
    (1, "ft2", "in2", "144"),
    (1, "h", "min", "60"),
    (1, "d", "h", "24"),
    (1, "wk", "d", "7"),
    (1, "min", "s", "60"),
    (1, "dozen", "piece", "12"),
    (1, "gross", "dozen", "12"),
    (1, "atm", "Pa", "101325"),
    (1, "bar", "kPa", "100"),
    (1, "kWh", "MJ", "3.6"),
    (1, "cal", "J", "4.184"),
    (1, "kcal", "cal", "1000"),
    (1, "mph", "ft/s", "1.466666666666666666666666666666666666666666666667"),  # 22/15, checked below
    (1, "km/h", "m/s", "0.2777777777777777777777777777777777777777777777778"),  # 5/18
    (1, "lbf", "N", "4.4482216152605"),
    (1, "kgf", "N", "9.80665"),
    (36, "km/h", "m/s", "10"),
    (60, "rpm", "Hz", "1"),
    (1, "kW", "W", "1000"),
]


@pytest.mark.parametrize("value, src, dst, expected", EXACT)
def test_exact_factors(value, src, dst, expected):
    got = convert(value, src, dst).value
    assert abs(got - D(expected)) <= D("1e-45") * max(1, abs(D(expected)))


def test_mph_and_kmh_are_exact_rationals():
    assert Fraction(convert(15, "mph", "ft/s").value) == 22
    assert convert(9, "km/h", "m/s").value == D("2.5")


@pytest.mark.parametrize(
    "src, dst, published, tolerance",
    [
        ("psi", "Pa", "6894.757293168", "1e-8"),  # NIST: 6894.757 293 168 Pa
        ("hp", "W", "745.6998715823", "1e-9"),  # mechanical hp: 745.699 871 582 27 W
        ("lbf-ft", "Nm", "1.355817948331", "1e-11"),
    ],
)
def test_derived_factors_match_published_values(src, dst, published, tolerance):
    assert abs(convert(1, src, dst).value - D(published)) < D(tolerance)


class TestTemperature:
    @pytest.mark.parametrize(
        "value, src, dst, expected",
        [
            (0, "C", "F", "32"),
            (100, "C", "F", "212"),
            (212, "F", "C", "100"),
            (32, "F", "C", "0"),
            (-40, "C", "F", "-40"),
            (-40, "F", "C", "-40"),
            (0, "C", "K", "273.15"),
            (0, "K", "C", "-273.15"),
            (20, "C", "K", "293.15"),
            (20, "C", "F", "68"),
            ("98.6", "F", "C", "37"),
            ("-459.67", "F", "K", "0"),
            (0, "K", "F", "-459.67"),
            (491.67, "R", "F", "32.00"),
            (0, "R", "K", "0"),
            (300, "K", "K", "300"),
            ("36.6", "C", "C", "36.6"),
        ],
    )
    def test_absolute(self, value, src, dst, expected):
        assert convert(value, src, dst).value == D(expected)

    def test_fahrenheit_to_celsius_is_exact_even_for_repeating(self):
        # 100 F = 37.777... C exactly 340/9 ; check by cross-multiplication, not by decimal digits
        r = convert(100, "F", "C")
        assert abs(Fraction(r.value) - Fraction(340, 9)) < Fraction(1, 10**45)
        assert abs(Fraction(convert(r.value, "C", "F").value) - 100) < Fraction(1, 10**40)

    def test_not_treated_as_multiplicative(self):
        assert convert(0, "C", "F").value != 0
        assert convert(10, "C", "F").value != convert(5, "C", "F").value * 2

    @pytest.mark.parametrize(
        "value, src, dst, expected",
        [
            (10, "C", "K", "10"),
            (10, "C", "F", "18"),
            (18, "F", "C", "10"),
            (9, "F", "K", "5"),
            (1, "K", "R", "1.8"),
        ],
    )
    def test_interval_ignores_offsets(self, value, src, dst, expected):
        assert convert(value, src, dst, interval=True).value == D(expected)

    def test_interval_only_for_temperature(self):
        with pytest.raises(UnsupportedOperationError):
            convert(1, "kg", "g", interval=True)

    @pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-1, "K"), (-0.1, "R")])
    def test_below_absolute_zero(self, value, unit):
        with pytest.raises(InvalidQuantityError):
            convert(value, unit, "K")

    def test_absolute_zero_itself_is_valid(self):
        assert convert("-273.15", "C", "K").value == 0


class TestCompatibility:
    @pytest.mark.parametrize(
        "src, dst", [("kg", "m"), ("C", "kg"), ("L", "m2"), ("h", "kg"), ("psi", "N"), ("dozen", "kg")]
    )
    def test_incompatible(self, src, dst):
        with pytest.raises(IncompatibleUnitError) as info:
            convert(1, src, dst)
        assert info.value.hint

    def test_are_compatible(self):
        assert are_compatible("kg", "lb") and are_compatible("C", "F")
        assert not are_compatible("kg", "L")

    def test_unknown_unit_suggests(self):
        with pytest.raises(UnknownUnitError) as info:
            convert(1, "kgs", "g")
        assert "kg" in info.value.hint

    @pytest.mark.parametrize("bad", ["Kg", "KG", "", "  ", None, 5])
    def test_unknown_or_case_mismatch_is_not_guessed(self, bad):
        with pytest.raises(UnknownUnitError):
            convert(1, bad, "g")

    def test_case_matters_mw_vs_mw(self):
        assert convert(1, "MW", "kW").value == 1000
        with pytest.raises(UnknownUnitError):
            convert(1, "mW", "W")  # milliwatt is not defined; must not be read as MW

    def test_aliases(self):
        assert convert(1, "kilogram", "pounds").unit == "lb"
        assert convert(1, "°C", "°F").unit == "F"
        assert convert(1, "l", "mL").value == 1000


class TestResultObject:
    def test_fields_and_str(self):
        r = convert(25, "kg", "g")
        assert (r.value, r.unit, r.source_value, r.source_unit, r.category) == (
            D(25000),
            "g",
            D(25),
            "kg",
            "mass",
        )
        assert str(r) == "25000 g"
        assert r.to_dict(numbers="str")["value"] == "25000"

    def test_rounding_keeps_exact_value(self):
        r = convert(1, "ft", "mm", rounding="half_up", places=0)
        assert r.exact_value == D("304.8") and r.value == 305 and r.rounding.value == "half_up"

    def test_repeating_result_rounded(self):
        r = convert(1, "d", "wk", rounding="half_even", places=4)
        assert r.value == D("0.1429")

    def test_places_without_rounding_rejected(self):
        with pytest.raises(InvalidRoundingError):
            convert(1, "kg", "g", places=2)

    @pytest.mark.parametrize("value", [0, "0", "0.000"])
    def test_zero(self, value):
        assert convert(value, "kg", "g").value == 0

    def test_negative_non_temperature_allowed(self):
        assert convert(-2, "kg", "g").value == -2000  # signed quantities (e.g. adjustments) are legal

    @pytest.mark.parametrize("bad", ["x", None, True, float("nan"), float("inf")])
    def test_invalid_value(self, bad):
        with pytest.raises(InvalidQuantityError):
            convert(bad, "kg", "g")

    def test_extreme_values_do_not_leak_decimal_errors(self):
        assert convert("1e299", "kg", "g").value == D("1e302")
        assert convert("1e-299", "kg", "g").value == D("1e-296")

    def test_fraction_input_is_exact(self):
        assert convert(Fraction(1, 3), "d", "h").value == 8

    def test_precision_is_configurable(self):
        from atica.core import use_precision

        with use_precision(8):
            assert str(convert(1, "lb", "kg").value) == "0.45359237"
            assert len(str(convert(1, "d", "wk").value)) <= 10


class TestRegistryAndCustomUnits:
    def test_default_registry_is_read_only(self):
        with pytest.raises(UnsupportedOperationError):
            default_registry().register_unit("bag", 25, "kg")

    def test_custom_unit(self, registry):
        assert registry.convert(4, "bag", "kg").value == 100
        assert abs(
            Fraction(registry.convert(1, "bag", "lb").value) - Fraction(25000) / Fraction("453.59237")
        ) < Fraction(1, 10**40)
        assert registry.get("bag").custom

    def test_independent_registries(self, registry):
        other = UnitRegistry()
        assert "bag" in registry and "bag" not in other
        with pytest.raises(UnknownUnitError):
            convert(1, "bag", "kg")  # not in the default registry
        other.register_unit("bag", 50, "kg")
        assert other.convert(1, "bag", "kg").value == 50 and registry.convert(1, "bag", "kg").value == 25

    def test_chained_and_fractional_definitions(self, registry):
        registry.register_unit("pallet_of_bags", 40, "bag")
        registry.register_unit("third", "1/3", "kg", aliases=["tkg"])
        assert registry.convert(1, "pallet_of_bags", "kg").value == 1000
        assert abs(Fraction(registry.convert(1, "tkg", "g").value) - Fraction(1000, 3)) < Fraction(1, 10**40)
        assert registry.convert(3, "third", "kg").value == 1

    def test_custom_unit_has_reference_category(self, registry):
        with pytest.raises(IncompatibleUnitError):
            registry.convert(1, "bag", "m")

    @pytest.mark.parametrize("factor", [0, -1, "abc", None, "1/0", float("nan")])
    def test_invalid_factor(self, factor):
        with pytest.raises(UnitDefinitionError):
            UnitRegistry().register_unit("x", factor, "kg")

    @pytest.mark.parametrize("name", ["kg", "g", "lb", "kilogram", "", "  ", "a" * 65, "bad\x00name"])
    def test_name_conflicts_and_invalid_names(self, name):
        with pytest.raises(UnitDefinitionError):
            UnitRegistry().register_unit(name, 2, "kg")

    def test_cannot_redefine_so_no_cycles(self, registry):
        with pytest.raises(UnitDefinitionError):
            registry.register_unit("bag", 30, "kg")
        registry.register_unit("b2", 2, "bag")
        with pytest.raises(UnitDefinitionError):
            registry.register_unit("bag", 1, "b2")

    def test_unknown_reference(self):
        with pytest.raises(UnknownUnitError):
            UnitRegistry().register_unit("x", 2, "nothing")

    def test_offset_scale_cannot_be_reference(self):
        with pytest.raises(UnitDefinitionError):
            UnitRegistry().register_unit("warm", 1, "C")

    def test_custom_temperature_via_kelvin(self):
        reg = UnitRegistry()
        reg.register_unit("mK", "0.001", "K")
        assert reg.convert(1500, "mK", "K").value == D("1.5")

    def test_new_category(self):
        reg = UnitRegistry()
        reg.register_base_unit("sheet", "paper_count", aliases=["sheets"])
        reg.register_unit("ream", 500, "sheet")
        assert reg.convert(2, "ream", "sheets").value == 1000
        with pytest.raises(IncompatibleUnitError):
            reg.convert(1, "ream", "piece")
        assert "paper_count" in reg.categories()

    def test_unregister(self, registry):
        registry.register_unit("b2", 2, "bag")
        with pytest.raises(UnsupportedOperationError):
            registry.unregister_unit("bag")  # b2 depends on it
        registry.unregister_unit("b2")
        registry.unregister_unit("bag")
        assert "bag" not in registry
        with pytest.raises(UnsupportedOperationError):
            registry.unregister_unit("kg")

    def test_serialisation_round_trip(self, registry):
        registry.register_unit("third", "1/3", "kg", aliases=["tkg"], display_name="Third")
        registry.register_base_unit("sheet", "paper_count")
        restored = UnitRegistry.from_dict(registry.to_dict())
        assert restored.convert(3, "third", "kg").value == 1
        assert restored.convert(1, "tkg", "g").value == registry.convert(1, "tkg", "g").value
        assert restored.get("third").name == "Third"
        assert [u.symbol for u in restored.custom_units()] == [u.symbol for u in registry.custom_units()]

    @pytest.mark.parametrize(
        "bad", [{}, {"format": "other"}, {"format": "atica.unit_registry", "version": 99}, "x", None]
    )
    def test_from_dict_rejects(self, bad):
        with pytest.raises(UnitDefinitionError):
            UnitRegistry.from_dict(bad)

    def test_from_dict_all_or_nothing_and_malformed(self):
        data = {"format": "atica.unit_registry", "version": 1, "custom_units": [{"name": "x"}]}
        with pytest.raises(UnitDefinitionError):
            UnitRegistry.from_dict(data)

    def test_copy_is_independent_and_writable(self, registry):
        c = registry.copy()
        c.register_unit("extra", 2, "kg")
        assert "extra" not in registry
        assert not c.frozen and default_registry().copy().frozen is False


class TestCatalogue:
    def test_categories_and_units(self):
        assert {"length", "mass", "area", "volume", "time", "temperature"} <= set(list_categories())
        assert all(u.category == "mass" for u in list_units("mass"))
        with pytest.raises(UnknownUnitError):
            list_units("nonsense")

    def test_no_alias_collisions_and_every_unit_roundtrips(self):
        reg = default_registry()
        seen = {}
        for unit in reg.units():
            for key in (unit.symbol, *unit.aliases):
                assert key not in seen or seen[key] == unit.symbol, key
                seen[key] = unit.symbol
        for unit in reg.units():
            base = reg.base_unit(unit.category)
            if unit.is_offset:
                continue
            there = convert(7, unit.symbol, base).value
            back = convert(there, base, unit.symbol).value
            assert abs(back - 7) < D("1e-40")


@given(st.decimals(min_value=-(10**6), max_value=10**6, places=6, allow_nan=False, allow_infinity=False))
def test_round_trip_linear(value):
    for a, b in (("kg", "lb"), ("m", "ft"), ("L", "gal"), ("h", "min")):
        assert abs(convert(convert(value, a, b).value, b, a).value - value) < D("1e-35")


@given(st.decimals(min_value=-273, max_value=10**5, places=4, allow_nan=False, allow_infinity=False))
def test_temperature_round_trip(value):
    f = convert(value, "C", "F").value
    assert abs(convert(f, "F", "C").value - value) < D("1e-35")
    k = convert(value, "C", "K").value
    assert abs(k - (value + D("273.15"))) < D("1e-35")


@given(st.decimals(min_value=0, max_value=10**4, places=3, allow_nan=False, allow_infinity=False))
def test_linearity(value):
    assert abs(convert(2 * value, "kg", "g").value - 2 * convert(value, "kg", "g").value) < D("1e-35")
