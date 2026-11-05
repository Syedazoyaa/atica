from decimal import Decimal

import pytest

from atica.exceptions import (
    IncompatibleUnitError,
    InvalidConversionError,
    InvalidQuantityError,
    UnknownUnitError,
)
from atica.units import (
    BASE_UNITS,
    are_compatible,
    convert,
    get_base_unit,
    get_unit,
    list_categories,
    list_units,
)

SPEC_UNITS = {
    "length": ["mm", "cm", "m", "km", "inch", "foot", "yard", "mile"],
    "mass": ["mg", "g", "kg", "tonne", "pound", "ounce"],
    "area": ["mm2", "cm2", "m2", "hectare", "ft2", "acre"],
    "volume": ["ml", "litre", "m3", "gallon", "pint", "floz"],
    "temperature": ["celsius", "fahrenheit", "kelvin"],
    "time": ["second", "minute", "hour", "day"],
    "pressure": ["Pa", "kPa", "MPa", "bar", "psi", "atm"],
    "force": ["N", "kN", "lbf"],
    "speed": ["m/s", "km/h", "mph"],
    "power": ["W", "kW", "MW", "hp"],
    "energy": ["J", "kJ", "kWh", "cal"],
    "frequency": ["Hz", "kHz", "MHz"],
    "voltage": ["V", "mV", "kV"],
    "current": ["A", "mA", "kA"],
    "resistance": ["ohm", "kohm", "Mohm"],
    "torque": ["Nm", "lb-ft"],
}


def test_spec_examples():
    assert str(convert("2.5", "kg", "g")) == "2500 g"
    assert str(convert("100", "cm", "m")) == "1 m"


def test_result_structure():
    r = convert("2.5", "kg", "g")
    assert r.input_quantity == Decimal("2.5") and r.input_unit == "kg"
    assert r.output_quantity == 2500 and r.output_unit == "g"
    assert r.quantity == 2500 and r.unit == "g"
    assert r.metadata["category"] == "mass"
    d = r.to_dict()
    assert d["output_quantity"] == "2500" and d["output_unit"] == "g"


@pytest.mark.parametrize("category,units", SPEC_UNITS.items())
def test_every_spec_unit_exists_and_round_trips(category, units):
    assert category in list_categories()
    for u in units:
        unit = get_unit(u)
        assert unit.category == category
        base = get_base_unit(category)
        there = convert("12.5", u, base)
        back = convert(there.output_quantity, base, u)
        # Fahrenheit uses 5/9, which has no finite decimal form; allow noise far below display precision.
        assert abs(back.output_quantity - Decimal("12.5")) < Decimal("1e-20"), u


def test_base_units_exist_and_have_factor_one():
    for category, base in BASE_UNITS.items():
        unit = get_unit(base)
        assert unit.category == category
        if category != "temperature":
            assert unit.factor == 1


def test_mm_to_inch():
    assert convert("25.4", "mm", "inch").output_quantity == 1


def test_float_input_does_not_leak_binary_noise():
    assert convert(0.1, "kg", "g").output_quantity == 100
    assert convert(0.3, "m", "cm").output_quantity == 30


@pytest.mark.parametrize(
    "value,src,dst,expected",
    [
        ("0", "celsius", "fahrenheit", "32"),
        ("100", "C", "F", "212"),
        ("212", "F", "C", "100"),
        ("-40", "C", "F", "-40"),
        ("0", "C", "K", "273.15"),
        ("273.15", "K", "C", "0"),
        ("32", "F", "K", "273.15"),
        ("0", "K", "F", "-459.67"),
        ("-273.15", "C", "K", "0"),
    ],
)
def test_temperature(value, src, dst, expected):
    assert convert(value, src, dst).output_quantity == Decimal(expected)


def test_below_absolute_zero_rejected():
    with pytest.raises(InvalidConversionError) as e:
        convert("-300", "C", "K")
    assert e.value.code == "BELOW_ABSOLUTE_ZERO"
    with pytest.raises(InvalidConversionError):
        convert("-1", "K", "C")


def test_incompatible_units_rejected():
    with pytest.raises(IncompatibleUnitError) as e:
        convert(1, "kg", "m")
    assert e.value.code == "INCOMPATIBLE_UNITS"
    assert "kg" in e.value.message


def test_watts_to_volts_rejected():
    with pytest.raises(IncompatibleUnitError):
        convert(10, "W", "V")


def test_unknown_unit():
    with pytest.raises(UnknownUnitError) as e:
        convert(1, "kg", "bananas")
    assert e.value.code == "UNKNOWN_UNIT"
    with pytest.raises(UnknownUnitError):
        convert(1, "KG", "g")  # identifiers are case-sensitive: mW vs MW must never be confused


def test_milliwatt_is_not_megawatt():
    with pytest.raises(UnknownUnitError):
        convert(1, "mW", "W")


@pytest.mark.parametrize("bad", ["abc", "", None, True, float("nan"), float("inf"), "1e999999", [1]])
def test_invalid_numbers(bad):
    with pytest.raises(InvalidQuantityError):
        convert(bad, "kg", "g")


def test_zero_negative_fractional_and_large():
    assert convert(0, "kg", "g").output_quantity == 0
    assert convert("-2", "kg", "g").output_quantity == -2000
    assert convert("0.000001", "kg", "mg").output_quantity == 1
    assert convert("1e20", "km", "mm").output_quantity == Decimal("1e26")
    assert str(convert("1e20", "km", "mm")) == "100000000000000000000000000 mm"


def test_precision_and_rounding_are_operation_level():
    r = convert(1, "minute", "hour", precision=4)
    assert r.output_quantity == Decimal("0.0167")
    assert r.metadata["exact_quantity"] > Decimal("0.016666")
    assert convert(1, "minute", "hour", precision=4, rounding="up").output_quantity == Decimal("0.0167")
    assert convert(1, "minute", "hour", precision=4, rounding="down").output_quantity == Decimal("0.0166")
    # without precision the full calculation precision is kept
    assert len(str(convert(1, "minute", "hour").output_quantity)) > 10


def test_approximate_factor_warning():
    assert convert(1, "psi", "kPa").warnings
    assert not convert(1, "kg", "g").warnings


def test_aliases():
    assert get_unit("in").unit_id == "inch"
    assert get_unit("L").unit_id == "litre"


def test_lb_to_oz_is_16():
    assert convert(1, "lb", "oz").output_quantity == 16


def test_listing_and_compatibility():
    assert {u.unit_id for u in list_units("mass")} >= {"mg", "g", "kg"}
    assert all(u.category == "length" for u in list_units("length"))
    assert are_compatible("kg", "pound")
    assert not are_compatible("kg", "m")
    assert get_base_unit("mass") == "g"
    with pytest.raises(UnknownUnitError):
        list_units("nonsense")


def test_unit_model_fields():
    u = get_unit("kg")
    assert (u.name, u.symbol, u.category, u.base_unit) == ("Kilogram", "kg", "mass", "g")
    assert u.factor == 1000 and u.offset == 0 and u.is_custom is False
    assert u.conversion_strategy == "linear"
    assert get_unit("celsius").conversion_strategy == "offset"


def test_kmh_exact_fraction_factor():
    assert convert(36, "km/h", "m/s").output_quantity == 10
