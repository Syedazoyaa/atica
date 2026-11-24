from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    IncompatibleUnitError,
    MissingInputError,
    UnknownUnitError,
    ValidationError,
)
from atica.purchasing import calculate_purchase_quantity
from atica.units import UnitRegistry


def D(x):
    return Decimal(x)


class TestPurchaseQuantity:
    def test_spec_style(self):
        r = calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12)
        assert r.order_quantity == 96 and str(r) == "96 piece"
        assert (r.net_requirement, r.surplus) == (87, 9)
        assert r.constraints == ("order_multiple",)

    def test_stock_deduction(self):
        r = calculate_purchase_quantity(100, stock_on_hand=30)
        assert (r.net_requirement, r.stock_deducted, r.order_quantity, r.surplus) == (70, 30, 70, 0)

    def test_stock_exceeding_requirement_orders_nothing_even_with_moq(self):
        r = calculate_purchase_quantity(100, stock_on_hand=150, minimum_order_quantity=50, order_multiple=10)
        assert r.order_quantity == 0 and r.stock_deducted == 100 and r.constraints == ()

    def test_zero_requirement(self):
        assert calculate_purchase_quantity(0, minimum_order_quantity=500).order_quantity == 0

    @pytest.mark.parametrize(
        "required, moq, mult, expected, constraints",
        [
            (10, 50, None, 50, ("minimum_order_quantity",)),
            (50, 50, None, 50, ()),
            (51, 50, None, 51, ()),
            (
                10,
                50,
                12,
                60,
                ("minimum_order_quantity", "order_multiple"),
            ),  # MOQ 50 not a multiple of 12 -> 60
            (13, 0, 12, 24, ("order_multiple",)),
            (24, 0, 12, 24, ()),
            (1, 0, "0.25", "1", ()),
            ("0.1", 0, "0.25", "0.25", ("order_multiple",)),
            ("0.3", 0, "0.1", "0.3", ()),  # exact decimal arithmetic: 0.3 is 3 x 0.1
        ],
    )
    def test_rules(self, required, moq, mult, expected, constraints):
        r = calculate_purchase_quantity(required, minimum_order_quantity=moq, order_multiple=mult)
        assert r.order_quantity == D(expected) and r.constraints == constraints
        assert r.surplus == r.order_quantity - r.net_requirement

    def test_moq_not_multiple_warns(self):
        r = calculate_purchase_quantity(10, minimum_order_quantity=50, order_multiple=12)
        assert r.warnings and "multiple" in r.warnings[0]

    def test_no_multiple_means_any_amount(self):
        assert calculate_purchase_quantity("12.34", unit="kg").order_quantity == D("12.34")

    def test_purchase_unit_conversion(self, registry):
        # need 130 kg, buy bags of 25 kg in whole bags
        r = calculate_purchase_quantity(
            130, unit="kg", purchase_unit="bag", order_multiple=1, registry=registry
        )
        assert (r.order_quantity, r.unit, r.net_requirement) == (6, "bag", D("5.2"))
        assert r.received_quantity == 150 and r.stock_unit == "kg" and r.surplus == D("0.8")
        assert str(r) == "6 bag"

    def test_purchase_unit_with_stock_and_moq_in_purchase_units(self, registry):
        r = calculate_purchase_quantity(
            130,
            unit="kg",
            stock_on_hand=(0 + 100),
            purchase_unit="bag",
            minimum_order_quantity=4,
            order_multiple=2,
            registry=registry,
        )
        # net 30 kg = 1.2 bags -> MOQ 4 bags -> multiple of 2 stays 4
        assert (
            r.order_quantity == 4
            and r.received_quantity == 100
            and r.constraints == ("minimum_order_quantity",)
        )

    def test_builtin_unit_conversion_without_custom_registry(self):
        r = calculate_purchase_quantity(5, unit="kg", purchase_unit="g", order_multiple=500)
        assert r.order_quantity == 5000

    def test_repeating_conversion_is_exact(self):
        # 1 lb = 453.59237 g; ordering exactly 1 kg in lb must ceil correctly
        r = calculate_purchase_quantity(1, unit="kg", purchase_unit="lb", order_multiple=1)
        assert r.order_quantity == 3 and Fraction(r.net_requirement) > Fraction(22046, 10000)

    def test_purchase_unit_requires_unit(self):
        with pytest.raises(MissingInputError):
            calculate_purchase_quantity(5, purchase_unit="kg")

    def test_unit_errors(self, registry):
        with pytest.raises(IncompatibleUnitError):
            calculate_purchase_quantity(5, unit="kg", purchase_unit="L", registry=registry)
        with pytest.raises(UnknownUnitError):
            calculate_purchase_quantity(
                5, unit="kg", purchase_unit="bag"
            )  # custom unit not in default registry

    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(required_quantity=-1),
            dict(required_quantity=1, stock_on_hand=-1),
            dict(required_quantity=1, minimum_order_quantity=-1),
            dict(required_quantity=1, order_multiple=0),
            dict(required_quantity=1, order_multiple=-2),
            dict(required_quantity="x"),
        ],
    )
    def test_invalid_inputs(self, kwargs):
        with pytest.raises(ValidationError):
            calculate_purchase_quantity(**kwargs)

    def test_missing_required(self):
        with pytest.raises(MissingInputError):
            calculate_purchase_quantity(None)

    def test_huge_and_tiny(self):
        assert int(calculate_purchase_quantity("1e30", order_multiple=7).order_quantity) % 7 == 0
        assert calculate_purchase_quantity("1e-20", order_multiple="1e-19").order_quantity == D("1e-19")

    def test_to_dict(self):
        d = calculate_purchase_quantity(87, unit="piece", order_multiple=12).to_dict(numbers="str")
        assert d["order_quantity"] == "96" and d["constraints"] == ["order_multiple"]


@given(
    st.fractions(min_value=0, max_value=10**5),
    st.fractions(min_value=0, max_value=10**5),
    st.fractions(min_value=0, max_value=1000),
    st.integers(min_value=1, max_value=500),
)
def test_order_invariants(required, stock, moq, multiple):
    r = calculate_purchase_quantity(
        required, stock_on_hand=stock, minimum_order_quantity=moq, order_multiple=multiple
    )
    tol = Fraction(1, 10**30)
    net = max(required - stock, 0)
    order = Fraction(r.order_quantity)
    assert order + tol >= net
    if net > 0:
        assert order + tol >= moq
        assert abs(order / multiple - round(order / multiple)) < tol
        assert order - net < max(moq, multiple) + multiple + tol
    else:
        assert order == 0


class TestRealisticPurchasingScenarios:
    """Worked examples a purchasing clerk would recognise; every expected figure is hand-calculated."""

    def test_cement_in_25kg_bags_ordered_by_the_pallet_of_10(self):
        reg = UnitRegistry()
        reg.register_unit("bag", 25, "kg")
        # need 12.5 t, 1.8 t in stock -> 10 700 kg = 428 bags; supplier ships whole pallets of 10 bags
        r = calculate_purchase_quantity(
            "12.5",
            unit="t",
            stock_on_hand="1.8",
            purchase_unit="bag",
            minimum_order_quantity=40,
            order_multiple=10,
            registry=reg,
        )
        assert (r.net_requirement, r.order_quantity, r.unit) == (428, 430, "bag")
        assert r.received_quantity == D("10.75") and r.stock_unit == "t"  # 430 bags x 25 kg
        assert r.surplus == 2 and r.constraints == ("order_multiple",)

    def test_resin_in_200_litre_drums_from_a_cubic_metre_requirement(self):
        reg = UnitRegistry()
        reg.register_unit("drum", 200, "L")
        r = calculate_purchase_quantity(
            "1.234", unit="m3", stock_on_hand="0.1", purchase_unit="drum", order_multiple=1, registry=reg
        )
        # 1234 L - 100 L = 1134 L = 5.67 drums -> 6 drums = 1200 L = 1.2 m3
        assert r.net_requirement == D("5.67") and r.order_quantity == 6
        assert r.received_quantity == D("1.2") and r.surplus == D("0.33")

    def test_minimum_order_forces_a_larger_order_than_needed(self):
        reg = UnitRegistry()
        reg.register_unit("box", 500, "piece")
        r = calculate_purchase_quantity(
            600,
            unit="piece",
            stock_on_hand=250,
            purchase_unit="box",
            minimum_order_quantity=2,
            order_multiple=1,
            registry=reg,
        )
        assert r.net_requirement == D("0.7") and r.order_quantity == 2 and r.received_quantity == 1000
        assert r.constraints == ("minimum_order_quantity",) and r.surplus == D("1.3")

    def test_stock_covering_the_requirement_orders_nothing_despite_a_minimum(self):
        reg = UnitRegistry()
        reg.register_unit("box", 500, "piece")
        r = calculate_purchase_quantity(
            400, unit="piece", stock_on_hand=450, purchase_unit="box", minimum_order_quantity=2, registry=reg
        )
        assert (r.order_quantity, r.received_quantity, r.stock_deducted) == (0, 0, D("0.8"))

    def test_imperial_requirement_metric_packs(self):
        reg = UnitRegistry()
        reg.register_unit("sack", 25, "kg")
        # 100 lb = 45.359237 kg = 1.81436948 sacks -> 2 sacks
        r = calculate_purchase_quantity(100, unit="lb", purchase_unit="sack", order_multiple=1, registry=reg)
        assert r.order_quantity == 2
        # 2 sacks = 50 kg, reported back in the requirement's own unit (lb): 50 / 0.45359237
        assert abs(Fraction(r.received_quantity) - Fraction(5_000_000_000, 45_359_237)) < Fraction(1, 10**40)
        assert Fraction(r.net_requirement) == Fraction("45.359237") / 25

    def test_fabric_rolls_with_kilometre_requirement(self):
        reg = UnitRegistry()
        reg.register_unit("roll", 50, "m")
        r = calculate_purchase_quantity(3, unit="km", purchase_unit="roll", order_multiple=5, registry=reg)
        assert r.order_quantity == 60 and r.surplus == 0 and r.constraints == ()

    def test_moq_not_a_multiple_of_the_order_multiple_is_flagged_and_still_valid(self):
        r = calculate_purchase_quantity(5, unit="kg", minimum_order_quantity=50, order_multiple=12)
        assert r.order_quantity == 60 and "multiple" in r.warnings[0]
