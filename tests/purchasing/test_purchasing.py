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
