from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    DuplicateMaterialError,
    IncompatibleUnitError,
    InvalidConfigurationError,
    InvalidPercentageError,
    InvalidQuantityError,
    InvalidRoundingError,
    MaterialError,
    MissingInputError,
    UnknownUnitError,
    UnsupportedOperationError,
)
from atica.materials import (
    Bom,
    BomItem,
    calculate_bom_requirements,
    calculate_material_requirement,
    calculate_producible_quantity,
)


def D(x):
    return Decimal(x)


class TestSingleMaterial:
    def test_plain(self):
        r = calculate_material_requirement("0.5", 1000, "kg")
        assert (r.quantity, r.unit) == (500, "kg") and r.units_started == 1000
        assert str(r) == "500 kg"

    def test_scrap_hand_calculation(self):
        # 1000 good at 5% scrap -> 1000/0.95 started; 0.5 kg each
        r = calculate_material_requirement("0.5", 950, "kg", scrap_percent=5)
        assert r.units_started == 1000 and r.quantity == 500
        assert r.base_quantity == D("475") and r.scrap_allowance == D("25") and r.wastage_allowance == 0

    def test_wastage_hand_calculation(self):
        # 100 kg net, 20% of the *issued* material is lost -> issue 125 kg
        r = calculate_material_requirement(1, 100, "kg", wastage_percent=20)
        assert r.quantity == 125 and r.wastage_allowance == 25 and r.base_quantity == 100

    def test_scrap_and_wastage_combine_multiplicatively(self):
        # good 90, scrap 10% -> start 100; 2 kg each = 200 kg used; wastage 20% of issued -> 250 kg
        r = calculate_material_requirement(2, 90, "kg", scrap_percent=10, wastage_percent=20)
        assert r.quantity == 250
        assert (r.base_quantity, r.scrap_allowance, r.wastage_allowance) == (180, 20, 50)
        assert r.base_quantity + r.scrap_allowance + r.wastage_allowance == r.exact_quantity

    def test_report_unit_conversion(self):
        assert str(calculate_material_requirement("0.5", 1000, "kg", report_unit="g")) == "500000 g"
        r = calculate_material_requirement(250, 10, "g", report_unit="kg")
        assert r.quantity == D("2.5") and r.per_unit_unit == "g"
        lb = calculate_material_requirement(1, 1, "lb", report_unit="oz")
        assert lb.quantity == 16

    def test_incompatible_report_unit(self):
        with pytest.raises(IncompatibleUnitError):
            calculate_material_requirement(1, 1, "kg", report_unit="m")

    def test_unknown_and_missing_unit(self):
        with pytest.raises(UnknownUnitError):
            calculate_material_requirement(1, 1, "bags")
        with pytest.raises(MissingInputError):
            calculate_material_requirement(1, 1, None)  # type: ignore[arg-type]

    def test_temperature_unit_not_a_material_quantity(self):
        with pytest.raises(UnsupportedOperationError):
            calculate_material_requirement(1, 1, "C")

    def test_custom_unit_via_registry(self, registry):
        r = calculate_material_requirement(1, 10, "bag", report_unit="kg", registry=registry)
        assert r.quantity == 250

    @pytest.mark.parametrize(
        "mode, places, expected",
        [
            ("none", 0, "263.15789473684210526315789473684210526315789473684"),
            ("half_up", 2, "263.16"),
            ("ceiling", 0, "264"),
            ("floor", 1, "263.1"),
            ("half_even", 3, "263.158"),
        ],
    )
    def test_rounding_explicit(self, mode, places, expected):
        r = calculate_material_requirement("0.25", 1000, "kg", scrap_percent=5, rounding=mode, places=places)
        assert r.quantity == D(expected) and r.rounding.value == mode
        assert abs(Fraction(r.exact_quantity) - Fraction(250, 1) / Fraction(95, 100)) < Fraction(1, 10**40)

    def test_zero_production(self):
        r = calculate_material_requirement(3, 0, "kg", scrap_percent=50, wastage_percent=50)
        assert r.quantity == 0 and r.units_started == 0

    @pytest.mark.parametrize("pct", [-1, 100, 101, "x", "100"])
    def test_invalid_percentages(self, pct):
        with pytest.raises((InvalidPercentageError, InvalidQuantityError)):
            calculate_material_requirement(1, 1, "kg", scrap_percent=pct)
        with pytest.raises((InvalidPercentageError, InvalidQuantityError)):
            calculate_material_requirement(1, 1, "kg", wastage_percent=pct)

    def test_fraction_scale_hint(self):
        with pytest.raises(InvalidPercentageError) as info:
            calculate_material_requirement(1, 1, "kg", wastage_percent=-0.05)
        assert "0-100" in info.value.hint

    @pytest.mark.parametrize("qty", [0, -1, "x"])
    def test_per_unit_must_be_positive(self, qty):
        with pytest.raises(InvalidQuantityError):
            calculate_material_requirement(qty, 1, "kg")

    def test_negative_production(self):
        with pytest.raises(InvalidQuantityError):
            calculate_material_requirement(1, -5, "kg")

    def test_places_without_rounding(self):
        with pytest.raises(InvalidRoundingError):
            calculate_material_requirement(1, 1, "kg", places=2)

    def test_extreme_magnitudes(self):
        big = calculate_material_requirement("1e100", "1e100", "kg", scrap_percent=50)
        assert big.quantity == D("2e200")
        tiny = calculate_material_requirement("1e-100", "1e-100", "kg")
        assert tiny.quantity == D("1e-200")


class TestBom:
    @pytest.fixture
    def bom(self):
        return Bom(
            [
                BomItem("steel", "0.25", "kg"),
                BomItem("paint", "40", "mL", wastage_percent=10),
                BomItem("screws", 4, "piece"),
            ],
            product_id="P001",
        )

    def test_spec_call_style(self, bom):
        result = calculate_bom_requirements(bom=bom, production_quantity=1000)
        assert str(result["steel"]) == "250 kg"
        assert str(result["screws"]) == "4000 piece"
        assert abs(Fraction(result["paint"].exact_quantity) - Fraction(400000, 9)) < Fraction(1, 10**40)
        assert [t.material_id for t in result.totals] == ["steel", "paint", "screws"]

    def test_scrap_applies_to_all_lines(self, bom):
        r = calculate_bom_requirements(bom, 950, scrap_percent=5)
        assert r["steel"].quantity == D("250") and r["screws"].quantity == 4000

    def test_report_units(self, bom):
        r = calculate_bom_requirements(bom, 1000, report_units={"steel": "g", "paint": "L"})
        assert (r["steel"].quantity, r["steel"].unit) == (250000, "g")
        assert r["paint"].unit == "L"
        with pytest.raises(InvalidConfigurationError):
            calculate_bom_requirements(bom, 1000, report_units={"glue": "kg"})
        with pytest.raises(IncompatibleUnitError):
            calculate_bom_requirements(bom, 1000, report_units={"steel": "L"})

    def test_rounding_applied_per_line(self, bom):
        r = calculate_bom_requirements(bom, 1000, rounding="ceiling")
        assert r["paint"].quantity == 44445 and r["steel"].quantity == 250

    def test_input_not_mutated(self, bom):
        before = bom.to_dict()
        calculate_bom_requirements(bom, 123, scrap_percent=3)
        assert bom.to_dict() == before

    def test_empty_bom(self):
        with pytest.raises(MissingInputError):
            Bom([])

    def test_duplicate_ids_rejected_consistently_ignoring_case(self):
        with pytest.raises(DuplicateMaterialError):
            Bom([BomItem("steel", 1, "kg"), BomItem("steel", 2, "kg")])
        with pytest.raises(DuplicateMaterialError):
            Bom([BomItem("steel", 1, "kg"), BomItem("STEEL", 2, "g")])

    def test_duplicates_allowed_are_combined_across_units(self):
        bom = Bom([BomItem("steel", 1, "kg"), BomItem("steel", 500, "g")], allow_duplicates=True)
        r = calculate_bom_requirements(bom, 10)
        assert len(r.lines) == 2 and len(r.totals) == 1
        assert r["steel"].quantity == D("15") and r["steel"].unit == "kg"
        assert r["steel"].warnings

    def test_duplicates_with_incompatible_units(self):
        bom = Bom([BomItem("steel", 1, "kg"), BomItem("steel", 1, "m")], allow_duplicates=True)
        with pytest.raises(IncompatibleUnitError):
            calculate_bom_requirements(bom, 1)

    def test_item_validation(self):
        for kwargs in (
            dict(quantity_per_unit=0),
            dict(quantity_per_unit=-1),
            dict(wastage_percent=100),
            dict(wastage_percent=-1),
        ):
            base = dict(material_id="m", quantity_per_unit=1, unit="kg")
            base.update(kwargs)
            with pytest.raises((InvalidQuantityError, InvalidPercentageError)):
                BomItem(**base)
        for bad_id in ("", "  ", None):
            with pytest.raises(Exception) as info:
                BomItem(bad_id, 1, "kg")
            assert isinstance(info.value, (MissingInputError,))
        with pytest.raises(MissingInputError):
            BomItem("m", 1, "")

    def test_missing_or_unknown_unit_detected_at_calculation(self):
        bom = Bom([BomItem("x", 1, "furlongs")])
        with pytest.raises(UnknownUnitError):
            calculate_bom_requirements(bom, 1)

    def test_round_trip_dict(self, bom):
        again = Bom.from_dict(bom.to_dict())
        assert again == bom
        with pytest.raises(MaterialError):
            Bom.from_dict({"items": [{"material_id": "x"}]})

    def test_immutability(self, bom):
        with pytest.raises(AttributeError):
            bom.items = ()  # type: ignore[misc]


class TestCapacity:
    @pytest.fixture
    def bom(self):
        return Bom(
            [
                BomItem("steel", "0.25", "kg"),
                BomItem("screws", 4, "piece"),
                BomItem("paint", 40, "mL", wastage_percent=10),
            ]
        )

    def test_limiting_material(self, bom):
        cap = calculate_producible_quantity(bom, {"steel": (100, "kg"), "screws": 1000, "paint": (100, "L")})
        # steel 400, screws 250, paint 100000 / (40/0.9) = 2250
        assert cap.producible_quantity == 250 and cap.limiting_material == "screws"
        per = {m.material_id: m.producible_units for m in cap.materials}
        assert per["steel"] == 400 and per["screws"] == 250 and per["paint"] == 2250

    def test_default_floor_and_exact(self, bom):
        cap = calculate_producible_quantity(bom, {"steel": 10, "screws": 1000, "paint": 100000})
        assert cap.exact_quantity == 40 and cap.producible_quantity == 40
        cap = calculate_producible_quantity(bom, {"steel": "10.1", "screws": 1000, "paint": 100000})
        assert cap.exact_quantity == D("40.4") and cap.producible_quantity == 40
        cap = calculate_producible_quantity(
            bom, {"steel": "10.1", "screws": 1000, "paint": 100000}, rounding="none"
        )
        assert cap.producible_quantity == D("40.4")

    def test_scrap_reduces_good_output(self, bom):
        cap = calculate_producible_quantity(
            bom, {"steel": 10, "screws": 1000, "paint": 100000}, scrap_percent=50
        )
        assert cap.producible_quantity == 20

    def test_zero_stock(self, bom):
        cap = calculate_producible_quantity(bom, {"steel": 0, "screws": 1000, "paint": 100000})
        assert cap.producible_quantity == 0 and cap.limiting_material == "steel"

    def test_missing_material_is_an_error_not_zero(self, bom):
        with pytest.raises(MissingInputError) as info:
            calculate_producible_quantity(bom, {"steel": 10, "screws": 10})
        assert "paint" in info.value.message

    def test_unknown_material_rejected(self, bom):
        with pytest.raises(InvalidConfigurationError):
            calculate_producible_quantity(bom, {"steel": 1, "screws": 1, "paint": 1, "glue": 1})

    def test_incompatible_availability_unit(self, bom):
        with pytest.raises(IncompatibleUnitError):
            calculate_producible_quantity(bom, {"steel": (10, "L"), "screws": 1, "paint": 1})

    def test_negative_availability(self, bom):
        with pytest.raises(InvalidQuantityError):
            calculate_producible_quantity(bom, {"steel": -1, "screws": 1, "paint": 1})

    def test_duplicate_lines_sum_consumption(self):
        bom = Bom([BomItem("steel", 1, "kg"), BomItem("steel", 500, "g")], allow_duplicates=True)
        cap = calculate_producible_quantity(bom, {"steel": (30, "kg")})
        assert cap.producible_quantity == 20

    def test_capacity_is_consistent_with_requirement(self, bom):
        cap = calculate_producible_quantity(
            bom, {"steel": 12345, "screws": 10**9, "paint": 10**9}, rounding="none"
        )
        need = calculate_bom_requirements(bom, cap.exact_quantity)
        assert abs(Fraction(need["steel"].exact_quantity) - 12345) < Fraction(1, 10**30)


@given(
    st.fractions(min_value=Fraction(1, 100), max_value=100),
    st.integers(min_value=0, max_value=10**6),
    st.integers(min_value=0, max_value=90),
    st.integers(min_value=0, max_value=90),
)
def test_requirement_matches_independent_formula(per_unit, good, scrap, wastage):
    r = calculate_material_requirement(per_unit, good, "kg", scrap_percent=scrap, wastage_percent=wastage)
    expected = per_unit * good / (1 - Fraction(scrap, 100)) / (1 - Fraction(wastage, 100))
    assert abs(Fraction(r.exact_quantity) - expected) <= Fraction(1, 10**40) * max(1, expected)
    assert abs(
        Fraction(r.base_quantity) + Fraction(r.scrap_allowance) + Fraction(r.wastage_allowance) - expected
    ) <= Fraction(1, 10**38) * max(1, expected)


@given(st.integers(min_value=1, max_value=10**5), st.integers(min_value=0, max_value=50))
def test_requirement_is_monotonic_in_quantity(good, scrap):
    a = calculate_material_requirement(1, good, "kg", scrap_percent=scrap).exact_quantity
    b = calculate_material_requirement(1, good + 1, "kg", scrap_percent=scrap).exact_quantity
    assert b > a
