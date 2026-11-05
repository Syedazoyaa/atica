from decimal import Decimal

import pytest

from atica.exceptions import ManufacturingError
from atica.manufacturing import (
    Formula,
    Material,
    calculate_batch_material,
    calculate_batches,
    calculate_bom_requirements,
    calculate_material_requirement,
    calculate_producible_quantity,
    calculate_production_time,
    evaluate_formula,
)


def test_spec_example():
    r = calculate_material_requirement(material_per_unit="0.5", production_quantity=1000, material_unit="kg")
    assert str(r) == "500 kg"
    assert r.quantity == 500 and r.unit == "kg"


def test_scrap_spec_example_unrounded_and_whole_units():
    r = calculate_material_requirement(target_output=1000, scrap_rate="0.05")
    assert str(r.quantity).startswith("1052.6315789473684")
    assert calculate_material_requirement(target_output=1000, scrap_rate="0.05", rounding="up").quantity == 1053


def test_material_with_scrap_and_whole_units_started():
    r = calculate_material_requirement("0.5", 1000, "kg", scrap_rate="0.05", units_rounding="up")
    assert r.metadata["units_to_process"] == 1053
    assert r.quantity == Decimal("526.5")


def test_wastage_rate_increases_material():
    r = calculate_material_requirement("0.5", 1000, "kg", wastage_rate="0.2")
    assert r.quantity == 625


def test_scrap_percent_alternative():
    a = calculate_material_requirement(target_output=950, scrap_percent=5)
    assert a.quantity == Decimal("1000")
    with pytest.raises(ManufacturingError) as e:
        calculate_material_requirement(target_output=950, scrap_rate="0.05", scrap_percent=5)
    assert e.value.code == "AMBIGUOUS_RATE"


def test_output_unit_conversion_uses_unit_registry(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    r = calculate_material_requirement("0.5", 1000, "kg", output_unit="bag", registry=registry)
    assert r.quantity == 20 and r.unit == "bag"
    r = calculate_material_requirement("0.5", 1000, "kg", output_unit="g")
    assert r.quantity == 500000 and r.unit == "g"


def test_rounding_applies_to_final_quantity():
    r = calculate_material_requirement("0.333", 10, "kg", rounding="half_up", places=1)
    assert r.quantity == Decimal("3.3")
    assert r.metadata["exact_quantity"] == Decimal("3.33")


@pytest.mark.parametrize(
    "kwargs,code",
    [
        (dict(material_per_unit="0.5", material_unit="kg"), "MISSING_INPUT"),
        (dict(production_quantity=10), "MISSING_INPUT"),
        (dict(material_per_unit="0.5", production_quantity=-1), "INVALID_PRODUCTION_QUANTITY"),
        (dict(material_per_unit="0.5", production_quantity="x"), "INVALID_PRODUCTION_QUANTITY"),
        (dict(material_per_unit="-1", production_quantity=1), "INVALID_MATERIAL_CONSUMPTION"),
        (dict(production_quantity=1, scrap_rate="1"), "INVALID_SCRAP_RATE"),
        (dict(production_quantity=1, scrap_rate="-0.1"), "INVALID_SCRAP_RATE"),
        (dict(production_quantity=1, scrap_rate="5"), "INVALID_SCRAP_RATE"),
        (dict(production_quantity=1, scrap_rate="abc"), "INVALID_SCRAP_RATE"),
        (dict(material_per_unit=1, production_quantity=1, wastage_rate="1"), "INVALID_WASTAGE_RATE"),
        (dict(production_quantity=1, target_output=2, scrap_rate="0.1"), "AMBIGUOUS_INPUT"),
    ],
)
def test_invalid_inputs(kwargs, code):
    with pytest.raises(ManufacturingError) as e:
        calculate_material_requirement(**kwargs)
    assert e.value.code == code


def test_zero_production_is_zero():
    assert calculate_material_requirement("0.5", 0, "kg").quantity == 0


def test_producible_quantity():
    r = calculate_producible_quantity(500, "0.5", scrap_rate="0.05")
    assert r.quantity == 950  # whole units, rounded down
    assert calculate_producible_quantity(10, "3").quantity == 3


def test_material_class_and_bom():
    cotton = Material("M1", "Cotton", "kg", "0.5", wastage_rate="0.2")
    thread = Material("M2", "Thread", "m", "30")
    assert cotton.requirement(1000).quantity == 625
    bom = calculate_bom_requirements([cotton, thread], 100)
    assert bom["M2"].quantity == 3000 and bom["M2"].unit == "m"
    assert Material.from_dict(cotton.to_dict()).to_dict() == cotton.to_dict()
    with pytest.raises(ManufacturingError):
        Material("", "x", "kg", 1)
    with pytest.raises(ManufacturingError):
        Material("M", "x", "", 1)
    with pytest.raises(ManufacturingError):
        Material("M", "x", "kg", -1)
    with pytest.raises(ManufacturingError):
        Material.from_dict({"name": "no id"})


def test_batches():
    r = calculate_batches(1050, 100)
    assert (r.full_batches, r.remainder, r.batches_required, r.last_batch_quantity) == (10, 50, 11, 50)
    r = calculate_batches(1000, 100)
    assert (r.full_batches, r.remainder, r.batches_required, r.last_batch_quantity) == (10, 0, 10, 100)
    assert calculate_batches(0, 100).batches_required == 0
    assert calculate_batches(30, 100).to_dict()["batches_required"] == 1
    with pytest.raises(ManufacturingError):
        calculate_batches(100, 0)
    assert calculate_batch_material("0.5", 200, "kg").quantity == 100
    assert calculate_production_time(500, 125).quantity == 4


# ------------------------------------------------------------------ formulas
@pytest.mark.parametrize(
    "expr,vars_,expected",
    [
        ("1 + 2 * 3", {}, "7"),
        ("(1 + 2) * 3", {}, "9"),
        ("-2 ^ 2", {}, "-4"),
        ("2 ** 3 ** 2", {}, "512"),
        ("2 ^ -1", {}, "0.5"),
        ("qty * per_unit / (1 - scrap)", dict(qty=95, per_unit="1", scrap="0.05"), "100"),
        ("max(1, 5, 3) - min(4, 2)", {}, "3"),
        ("ceil(1.2) + floor(1.8) + abs(-3)", {}, "6"),
        ("round(2.345, 2)", {}, "2.35"),
        ("sqrt(16)", {}, "4"),
        ("0.1 + 0.2", {}, "0.3"),
        ("1e3 / 4", {}, "250"),
    ],
)
def test_formula_evaluation(expr, vars_, expected):
    assert evaluate_formula(expr, vars_) == Decimal(expected)


def test_formula_variables_and_reuse():
    f = Formula("a * b")
    assert f.variables == {"a", "b"}
    assert f.evaluate(a=2, b=3) == 6
    assert f.evaluate({"a": "1.5", "b": 2}) == 3


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('echo hi')",
        "open('x')",
        "a.b",
        "a[0]",
        "lambda: 1",
        "1 +",
        "(1 + 2",
        "1 2",
        "",
        "   ",
        "eval('1')",
        "2 $ 3",
        "x" * 600,
        "(" * 100 + "1" + ")" * 100,
    ],
)
def test_formula_rejects_unsafe_or_malformed(expr):
    with pytest.raises(ManufacturingError):
        evaluate_formula(expr, {"a": 1, "x": 1})


def test_formula_errors_have_codes():
    with pytest.raises(ManufacturingError) as e:
        evaluate_formula("1 / 0")
    assert e.value.code == "DIVISION_BY_ZERO"
    with pytest.raises(ManufacturingError) as e:
        evaluate_formula("a + 1")
    assert e.value.code == "UNKNOWN_VARIABLE"
    with pytest.raises(ManufacturingError) as e:
        evaluate_formula("9 ^ 999")
    assert e.value.code == "INVALID_EXPONENT"
    with pytest.raises(ManufacturingError) as e:
        evaluate_formula("a", {"a": "x"})
    assert e.value.code == "INVALID_NUMBER"
    with pytest.raises(ManufacturingError) as e:
        evaluate_formula("exec(1)")
    assert e.value.code == "UNKNOWN_FUNCTION"
    with pytest.raises(ManufacturingError):
        evaluate_formula("0 ^ -1")
