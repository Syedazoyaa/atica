from decimal import Decimal

import pytest

from atica.exceptions import ManufacturingError
from atica.manufacturing import (
    calculate_expected_output,
    calculate_required_input,
    calculate_scrap_percentage,
    calculate_scrap_quantity,
    calculate_wastage,
    calculate_yield,
)


def test_required_input_spec_example():
    r = calculate_required_input(1000, "0.05")
    assert str(r.quantity).startswith("1052.631578")
    assert calculate_required_input(1000, "0.05", rounding="up").quantity == 1053
    assert calculate_required_input(1000, scrap_percent=5, rounding="ceiling_package").quantity == 1053
    assert calculate_required_input(1000, "0.05", rounding="half_up").quantity == 1053
    assert calculate_required_input(1000, "0.05", rounding="down").quantity == 1052


def test_required_input_package_rounding():
    r = calculate_required_input(1000, "0.05", rounding="ceiling_package", multiple=100)
    assert r.quantity == 1100


def test_zero_scrap_and_zero_output():
    assert calculate_required_input(1000, 0).quantity == 1000
    assert calculate_required_input(1000).quantity == 1000
    assert calculate_required_input(0, "0.5").quantity == 0


@pytest.mark.parametrize("rate", ["1", "1.0", "-0.01", "1.5", "5", "x", "nan"])
def test_invalid_scrap_rates_rejected(rate):
    with pytest.raises(ManufacturingError) as e:
        calculate_required_input(1000, rate)
    assert e.value.code == "INVALID_SCRAP_RATE"


def test_rate_of_one_cannot_divide_by_zero():
    with pytest.raises(ManufacturingError) as e:
        calculate_required_input(10, 1)
    assert "1" in e.value.message and e.value.code == "INVALID_SCRAP_RATE"


def test_percent_over_100_rejected():
    with pytest.raises(ManufacturingError):
        calculate_required_input(10, scrap_percent=100)
    with pytest.raises(ManufacturingError):
        calculate_required_input(10, scrap_percent=-1)


def test_negative_output_rejected():
    with pytest.raises(ManufacturingError):
        calculate_required_input(-5, "0.1")


def test_expected_output_and_scrap_quantity():
    assert calculate_expected_output(1000, "0.05").quantity == 950
    assert calculate_expected_output(1053, "0.05", rounding="down").quantity == 1000  # 1000.35
    assert calculate_scrap_quantity(1000, scrap_percent=5).quantity == 50


def test_scrap_percentage():
    assert calculate_scrap_percentage(1000, 50) == 5
    assert calculate_scrap_percentage(1000, 0) == 0
    with pytest.raises(ManufacturingError):
        calculate_scrap_percentage(0, 0)
    with pytest.raises(ManufacturingError):
        calculate_scrap_percentage(10, 11)


def test_yield():
    y = calculate_yield(1000, 900, rework_quantity=50)
    assert y.scrap_quantity == 50
    assert y.yield_rate == Decimal("0.9") and y.yield_percent == 90
    assert y.scrap_rate == Decimal("0.05") and y.rework_rate == Decimal("0.05")
    assert y.to_dict()["yield_percent"] == "90"
    assert calculate_yield(10, 10).scrap_quantity == 0


def test_yield_invalid():
    with pytest.raises(ManufacturingError) as e:
        calculate_yield(100, 90, 20)
    assert e.value.code == "OUTPUT_EXCEEDS_INPUT"
    with pytest.raises(ManufacturingError):
        calculate_yield(0, 0)
    with pytest.raises(ManufacturingError):
        calculate_yield(100, -1)


def test_wastage_distinguishes_scrap_and_process_loss():
    w = calculate_wastage(100, 85, scrap_quantity=5)
    assert w.wastage_quantity == 15 and w.process_wastage == 10 and w.scrap_quantity == 5
    assert w.wastage_rate == Decimal("0.15")
    with pytest.raises(ManufacturingError):
        calculate_wastage(100, 101)
    with pytest.raises(ManufacturingError):
        calculate_wastage(100, 95, scrap_quantity=6)
