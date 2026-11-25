"""Spot checks against values worked out by hand (not produced by the library's own formulas)."""

from decimal import Decimal
from fractions import Fraction

from atica.materials import calculate_material_requirement
from atica.production import calculate_batches, production_capacity, production_time
from atica.purchasing import calculate_purchase_quantity
from atica.quality import (
    calculate_expected_output,
    calculate_required_input,
    calculate_scrap_percentage,
    calculate_wastage,
    calculate_yield,
)
from atica.units import convert


def test_scrap_denominator_is_input():
    assert calculate_scrap_percentage(1000, 50).percent == 5
    assert calculate_expected_output(1000, 5).quantity == 950
    assert calculate_required_input(100, 20).quantity == 125  # 100 / 0.8


def test_material_scrap_and_wastage_denominators():
    # 0.5 kg x 1000 good; started = 1000/0.9; gross = 0.5 x started / 0.8 = 6250/9 kg
    r = calculate_material_requirement("0.5", 1000, "kg", scrap_percent=10, wastage_percent=20)
    tol = Fraction(1, 10**40)
    assert abs(Fraction(r.exact_quantity) * 9 - 6250) < tol
    parts = Fraction(r.base_quantity) + Fraction(r.scrap_allowance) + Fraction(r.wastage_allowance)
    assert abs(parts - Fraction(r.exact_quantity)) < tol
    assert r.base_quantity == 500  # 0.5 x 1000, before any loss


def test_production_time_and_capacity_with_setup_and_efficiency():
    # effective rate 250 x 0.8 = 200/h; 1000/200 = 5 h; + 30 min setup (not scaled by efficiency)
    t = production_time(1000, 250, efficiency_percent=80, setup_time=(30, "min"))
    assert t.total_time == Decimal("5.5")
    # (8 h - 1 h setup) x 200 = 1400
    assert production_capacity(250, (8, "h"), efficiency_percent=80, setup_time=(1, "h")).quantity == 1400


def test_batches_conserve_quantity():
    p = calculate_batches(250, 100)
    assert (p.full_batches, p.partial_batch_quantity, p.batches_required) == (2, 50, 3)
    assert p.total_capacity - p.unused_capacity == p.quantity


def test_yield_denominators():
    r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
    assert (r.first_pass_yield_percent, r.final_yield_percent, r.scrap_percent) == (
        90,
        Decimal("94.5"),
        Decimal("5.5"),
    )
    assert r.rework_recovery_percent == 75  # 45 / 60, denominator is the reworked units
    assert r.final_good + r.final_scrap == r.input_quantity


def test_wastage_denominators():
    r = calculate_wastage(1000, 920, recovery_percent=25)
    assert (r.gross_wastage, r.net_wastage, r.net_wastage_percent) == (80, 60, 6)
    assert r.recovery_percent == 25  # of the gross wastage


def test_purchasing_moq_never_forces_unneeded_order():
    assert calculate_purchase_quantity(10, stock_on_hand=15, minimum_order_quantity=100).order_quantity == 0
    r = calculate_purchase_quantity(
        "2.5", unit="kg", stock_on_hand="0.5", minimum_order_quantity=500, order_multiple=750, purchase_unit="g"
    )
    assert r.net_requirement == 2000 and r.order_quantity == 2250  # ceil(2000/750) = 3 x 750


def test_units():
    assert str(convert(100, "C", "F")) == "212 F"
    assert str(convert(0, "C", "K")) == "273.15 K"
    assert str(convert(-40, "C", "F")) == "-40 F"
    assert str(convert(1, "lb", "kg")) == "0.45359237 kg"
