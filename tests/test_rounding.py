from decimal import Decimal

import pytest

from atica.calculations import RoundingPolicy, round_value, round_with_remainder
from atica.exceptions import ValidationError


@pytest.mark.parametrize(
    "value,policy,expected",
    [
        ("2.5", "half_up", "3"),
        ("3.5", "half_up", "4"),
        ("2.5", "half_even", "2"),
        ("3.5", "half_even", "4"),
        ("2.7", "down", "2"),
        ("2.1", "up", "3"),
        ("2.0", "up", "2"),
        ("2.123456", "none", "2.123456"),
    ],
)
def test_whole_number_policies(value, policy, expected):
    assert round_value(value, policy) == Decimal(expected)


def test_decimal_places():
    assert round_value("1.005", "half_up", places=2) == Decimal("1.01")
    assert round_value("1.005", "half_even", places=2) == Decimal("1.00")
    assert round_value("1.999", "down", places=2) == Decimal("1.99")
    assert round_value("1.001", "up", places=2) == Decimal("1.01")


def test_package_policies():
    assert round_value(87, "ceiling_package", multiple=12) == 96
    assert round_value(87, "floor_package", multiple=12) == 84
    assert round_value(96, "ceiling_package", multiple=12) == 96
    assert round_value("0.1", "ceiling_package", multiple="0.25") == Decimal("0.25")


def test_preserve_remainder():
    r = round_with_remainder(87, "preserve_remainder", multiple=12)
    assert (r.rounded, r.remainder, r.original) == (84, 3, 87)
    r = round_with_remainder(87, RoundingPolicy.CEILING_PACKAGE, multiple=12)
    assert (r.rounded, r.remainder) == (96, -9)


def test_policy_parsing():
    assert RoundingPolicy.parse("Half-Up") is RoundingPolicy.HALF_UP
    assert RoundingPolicy.parse(None) is RoundingPolicy.NONE
    with pytest.raises(ValidationError) as e:
        RoundingPolicy.parse("sideways")
    assert e.value.code == "INVALID_ROUNDING_POLICY"


def test_invalid_arguments():
    with pytest.raises(ValidationError):
        round_value(5, "ceiling_package", multiple=0)
    with pytest.raises(ValidationError):
        round_value(5, "half_up", places=-1)
    with pytest.raises(ValidationError):
        round_value(5, "half_up", places=1.5)


def test_different_operations_use_different_policies():
    """No global policy: physical conversion keeps decimals, shipping rounds up, issuing rounds down."""
    from atica.units import convert

    assert convert("2.5", "kg", "g").output_quantity == 2500
    exact = Decimal("21.25")
    assert round_value(exact, "ceiling_package") == 22  # shipment
    assert round_value(exact, "floor_package") == 21  # inventory issue
    assert exact == Decimal("21.25")  # inputs are never mutated
