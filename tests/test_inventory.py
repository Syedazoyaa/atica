from decimal import Decimal

import pytest

from atica.exceptions import InventoryError
from atica.inventory import PurchasingConfig, calculate_purchase_order, calculate_purchase_quantity


def test_spec_example():
    r = calculate_purchase_quantity(required_quantity=87, order_multiple=12, minimum_order_quantity=24)
    assert str(r) == "96 pieces"
    assert r.quantity == 96
    assert r.metadata["surplus"] == 9 and r.metadata["constraints"] == ["order_multiple"]


def test_exact_multiple_unchanged():
    assert calculate_purchase_quantity(96, 12).quantity == 96


def test_minimum_order_quantity_binds():
    r = calculate_purchase_quantity(10, order_multiple=12, minimum_order_quantity=24)
    assert r.quantity == 24
    assert r.metadata["constraints"] == ["minimum_order_quantity"]


def test_moq_and_multiple_conflict():
    r = calculate_purchase_quantity(10, order_multiple=12, minimum_order_quantity=30)
    assert r.quantity == 36
    assert r.metadata["constraints"] == ["minimum_order_quantity", "order_multiple"]
    assert r.warnings  # MOQ is not itself a multiple


def test_no_order_when_stock_covers_need():
    r = calculate_purchase_quantity(50, 12, 24, on_hand=60)
    assert r.quantity == 0 and r.metadata["constraints"] == []
    assert calculate_purchase_quantity(0, 12, 24).quantity == 0


def test_on_hand_reduces_need():
    assert calculate_purchase_quantity(100, 12, on_hand=20).quantity == 84


def test_decimal_multiples():
    r = calculate_purchase_quantity("10.2", order_multiple="0.5", unit="kg")
    assert r.quantity == Decimal("10.5") and str(r) == "10.5 kg"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        (dict(required_quantity=10, order_multiple=0), "INVALID_ORDER_MULTIPLE"),
        (dict(required_quantity=10, order_multiple=-2), "INVALID_ORDER_MULTIPLE"),
        (dict(required_quantity=10, order_multiple="x"), "INVALID_ORDER_MULTIPLE"),
        (dict(required_quantity=10, minimum_order_quantity=-1), "INVALID_MINIMUM_ORDER_QUANTITY"),
        (dict(required_quantity=-5), "INVALID_REQUIRED_QUANTITY"),
        (dict(required_quantity=None), "INVALID_REQUIRED_QUANTITY"),
        (dict(required_quantity=5, on_hand=-1), "INVALID_STOCK_QUANTITY"),
    ],
)
def test_invalid_inputs(kwargs, code):
    with pytest.raises(InventoryError) as e:
        calculate_purchase_quantity(**kwargs)
    assert e.value.code == code


# --------------------------------------------------------- supplier configs
def test_config_with_explicit_conversion():
    cfg = PurchasingConfig(
        "SUP-1", "PROD-A", "case", "piece", minimum_order_quantity=2, order_multiple=2,
        conversion_configuration={"stock_units_per_purchase_unit": 24},
    )
    r = calculate_purchase_order(cfg, 100)  # 100 pieces -> 4.17 -> 5 cases -> multiple of 2 -> 6
    assert r.quantity == 6 and r.unit == "case"
    assert r.metadata["stock_quantity"] == 144 and r.metadata["surplus_stock"] == 44


def test_config_from_product_packaging(product_a):
    cfg = PurchasingConfig("SUP-1", "PROD-A", "carton", "box", order_multiple=1)
    r = calculate_purchase_order(cfg, 41, product=product_a)  # 20 boxes per carton
    assert r.quantity == 3
    assert r.metadata["stock_per_purchase_unit"] == 20


def test_config_from_physical_units(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    cfg = PurchasingConfig("SUP-1", "RESIN", "bag", "kg", minimum_order_quantity=4)
    r = calculate_purchase_order(cfg, 60, registry=registry)
    assert r.quantity == 4  # 60 kg = 2.4 bags -> 3 -> MOQ 4
    assert r.metadata["stock_quantity"] == 100
    r = calculate_purchase_order(cfg, 60, on_hand=10, registry=registry)
    assert r.metadata["net_stock_requirement"] == 50


def test_config_same_units():
    cfg = PurchasingConfig("S", "P", "piece", "piece", order_multiple=10)
    assert calculate_purchase_order(cfg, 15).quantity == 20


def test_config_unconvertible_units():
    cfg = PurchasingConfig("S", "P", "pallet", "kg")
    with pytest.raises(InventoryError) as e:
        calculate_purchase_order(cfg, 10)
    assert e.value.code == "MISSING_CONVERSION"
    cfg = PurchasingConfig("S", "P", "kg", "m")
    with pytest.raises(InventoryError) as e:
        calculate_purchase_order(cfg, 10)
    assert e.value.code == "INCOMPATIBLE_UNITS"


def test_config_validation_and_serialization():
    for kwargs in (
        dict(supplier_id="", product_id="p", purchase_unit="a", stock_unit="b"),
        dict(supplier_id="s", product_id="p", purchase_unit="a", stock_unit="b", order_multiple=0),
        dict(supplier_id="s", product_id="p", purchase_unit="a", stock_unit="b", minimum_order_quantity=-1),
        dict(supplier_id="s", product_id="p", purchase_unit="a", stock_unit="b",
             conversion_configuration={"stock_units_per_purchase_unit": 0}),
    ):
        with pytest.raises(InventoryError):
            PurchasingConfig(**kwargs)
    cfg = PurchasingConfig("S", "P", "case", "piece", 24, 12, {"stock_units_per_purchase_unit": "12"})
    assert PurchasingConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()
    with pytest.raises(InventoryError):
        PurchasingConfig.from_dict({"supplier_id": "S"})
