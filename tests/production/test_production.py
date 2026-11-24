from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from atica.core import (
    ConstraintError,
    IncompatibleUnitError,
    InvalidConfigurationError,
    InvalidQuantityError,
    ValidationError,
)
from atica.materials import Bom, BomItem, calculate_bom_requirements
from atica.production import (
    calculate_batch_capacity,
    calculate_batch_materials,
    calculate_batches,
    constrain_production_quantity,
    production_capacity,
    production_time,
)


def D(x):
    return Decimal(x)


class TestBatches:
    @pytest.mark.parametrize(
        "qty, size, full, partial, required, capacity, unused",
        [
            (250, 100, 2, 50, 3, 300, 50),
            (300, 100, 3, 0, 3, 300, 0),
            (99, 100, 0, 99, 1, 100, 1),
            (1, 100, 0, 1, 1, 100, 99),
            (0, 100, 0, 0, 0, 0, 0),
            ("250.5", "100", 2, "50.5", 3, 300, "49.5"),
            (1000, "0.3", 3333, "0.1", 3334, "1000.2", "0.2"),  # 1000 = 3333 * 0.3 + 0.1
        ],
    )
    def test_cases(self, qty, size, full, partial, required, capacity, unused):
        p = calculate_batches(qty, size)
        assert (
            p.full_batches,
            p.partial_batch_quantity,
            p.batches_required,
            p.total_capacity,
            p.unused_capacity,
        ) == (
            D(full),
            D(partial),
            D(required),
            D(capacity),
            D(unused),
        )
        assert p.has_partial_batch == (D(partial) > 0)

    def test_required_vs_full_capacity_are_distinct(self):
        p = calculate_batches(250, 100)
        assert p.full_batches == 2 and p.batches_required == 3 and p.total_capacity == 300

    @pytest.mark.parametrize("size", [0, -5, "abc", None])
    def test_batch_size_must_be_positive(self, size):
        with pytest.raises(ValidationError):
            calculate_batches(100, size)

    def test_negative_quantity(self):
        with pytest.raises(InvalidQuantityError):
            calculate_batches(-1, 10)

    def test_repeating_division_is_exact(self):
        p = calculate_batches(1, "0.1")  # 1 / 0.1 = 10 exactly (binary floats get this wrong)
        assert p.full_batches == 10 and p.partial_batch_quantity == 0
        p = calculate_batches("0.3", "0.1")
        assert p.full_batches == 3 and p.partial_batch_quantity == 0

    def test_huge(self):
        p = calculate_batches("1e30", 7)
        assert p.full_batches * 7 + p.partial_batch_quantity == D("1e30")


class TestBatchMaterials:
    @pytest.fixture
    def bom(self):
        return Bom([BomItem("resin", "2", "kg"), BomItem("dye", "3", "g", wastage_percent=25)])

    def test_per_batch_and_total(self, bom):
        plan = calculate_batch_materials(bom, 250, 100)
        by = {m.material_id: m for m in plan.materials}
        assert (by["resin"].per_full_batch, by["resin"].partial_batch, by["resin"].total) == (200, 100, 500)
        # dye: 3 g /0.75 = 4 g per piece -> 400 per full batch, 200 partial, total 1000
        assert (by["dye"].per_full_batch, by["dye"].partial_batch, by["dye"].total) == (400, 200, 1000)
        assert plan.batches.batches_required == 3 and plan.partial_batch is not None

    def test_totals_equal_single_calculation_without_rounding(self, bom):
        plan = calculate_batch_materials(bom, "257.3", 40)
        whole = calculate_bom_requirements(bom, "257.3")
        for m in plan.materials:
            assert abs(Fraction(m.exact_total) - Fraction(whole[m.material_id].exact_quantity)) < Fraction(
                1, 10**35
            )

    def test_no_partial_batch(self, bom):
        plan = calculate_batch_materials(bom, 300, 100)
        assert plan.partial_batch is None and plan.materials[0].partial_batch == 0

    def test_per_batch_rounding_reflects_what_is_issued(self):
        bom = Bom([BomItem("m", "0.333", "kg")])
        plan = calculate_batch_materials(bom, 3, 1, rounding="half_up", places=2)
        # each batch issues 0.33 kg; three batches issue 0.99 kg while the exact need is 0.999
        assert plan.materials[0].total == D("0.99") and plan.materials[0].exact_total == D("0.999")

    def test_scrap_and_report_units(self, bom):
        plan = calculate_batch_materials(bom, 100, 100, scrap_percent=50, report_units={"resin": "g"})
        assert plan.materials[0].unit == "g" and plan.materials[0].total == 400000


class TestConstraints:
    def test_rules_in_order(self):
        assert constrain_production_quantity(950, multiple=100).quantity == 1000
        assert constrain_production_quantity(300, minimum=500).quantity == 500
        r = constrain_production_quantity(300, minimum=450, multiple=100)
        assert r.quantity == 500 and r.adjustments == ("minimum", "multiple") and r.increase == 200
        assert constrain_production_quantity(950).adjustments == ()
        assert constrain_production_quantity(1000, multiple=100).adjustments == ()

    def test_zero_request_stays_zero(self):
        assert constrain_production_quantity(0, minimum=500, multiple=100).quantity == 0

    def test_floor_multiple(self):
        assert constrain_production_quantity(950, multiple=100, multiple_rounding="floor").quantity == 900
        with pytest.raises(ConstraintError):
            constrain_production_quantity(50, multiple=100, minimum=60, multiple_rounding="floor")

    def test_maximum(self):
        assert constrain_production_quantity(900, maximum=1000).quantity == 900
        with pytest.raises(ConstraintError):
            constrain_production_quantity(950, maximum=900)
        with pytest.raises(ConstraintError):
            constrain_production_quantity(950, maximum=1000, multiple=300)  # rounds to 1200

    def test_min_above_max_is_configuration_error(self):
        with pytest.raises(InvalidConfigurationError):
            constrain_production_quantity(1, minimum=10, maximum=5)

    @pytest.mark.parametrize("kw", [dict(multiple=0), dict(maximum=0), dict(minimum=-1)])
    def test_invalid(self, kw):
        with pytest.raises(InvalidQuantityError):
            constrain_production_quantity(10, **kw)


class TestProductionTime:
    def test_basic_units(self):
        assert str(production_time(1000, 250)) == "4 h"
        assert str(production_time(1000, 250, unit="min")) == "240 min"
        assert str(production_time(1000, 250, unit="s")) == "14400 s"

    def test_rate_per_other_unit(self):
        # 10 pieces per minute: 600 pieces take 60 minutes = 1 hour
        r = production_time(600, 10, per="min", unit="h")
        assert r.total_time == 1 and r.rate_per == "min"
        assert production_time(5, 1, per="d", unit="h").total_time == 120

    def test_efficiency_and_setup(self):
        r = production_time(1000, 250, efficiency_percent=80, setup_time=(30, "min"))
        # run = 1000 / 200 = 5 h ; setup 0.5 h
        assert (r.run_time, r.setup_time, r.total_time, r.effective_rate) == (5, D("0.5"), D("5.5"), 200)
        assert r.assumptions and "constant" in r.assumptions[0]
        assert production_time(1000, 250, setup_time=2).setup_time == 2  # default unit = per

    def test_repeating_time(self):
        r = production_time(1, 3)
        assert abs(Fraction(r.total_time) - Fraction(1, 3)) < Fraction(1, 10**45)
        assert production_time(1, 3, unit="min").total_time == 20

    def test_zero_quantity(self):
        assert production_time(0, 5).total_time == 0
        assert production_time(0, 5, setup_time=1).total_time == 1

    @pytest.mark.parametrize("rate", [0, -1, "x"])
    def test_rate_validation(self, rate):
        with pytest.raises(ValidationError):
            production_time(10, rate)

    @pytest.mark.parametrize("eff", [0, -5, 101, "x"])
    def test_efficiency_validation(self, eff):
        with pytest.raises(ValidationError):
            production_time(10, 1, efficiency_percent=eff)

    def test_non_time_units_rejected(self):
        for kwargs in (dict(per="kg"), dict(unit="m"), dict(setup_time=(1, "kg"))):
            with pytest.raises(IncompatibleUnitError):
                production_time(10, 1, **kwargs)

    def test_negative_setup(self):
        with pytest.raises(InvalidQuantityError):
            production_time(10, 1, setup_time=-1)


class TestCapacity:
    def test_basic(self):
        assert production_capacity(250, (8, "h")).quantity == 2000
        assert production_capacity(250, 8).quantity == 2000
        assert production_capacity(10, (1, "h"), per="min").quantity == 600

    def test_efficiency_setup(self):
        r = production_capacity(250, 8, efficiency_percent=80, setup_time=(1, "h"))
        assert r.quantity == 1400 and r.productive_time == 7

    def test_setup_exceeds_available(self):
        r = production_capacity(250, 1, setup_time=2)
        assert r.quantity == 0 and r.warnings

    def test_rounding_and_inverse_of_time(self):
        r = production_capacity(7, (1, "h"), per="min", efficiency_percent=33, rounding="floor")
        assert r.exact_quantity == D("138.6") and r.quantity == 138
        t = production_time(r.exact_quantity, 7, per="min", efficiency_percent=33, unit="h")
        assert abs(t.total_time - 1) < D("1e-40")

    def test_validation(self):
        with pytest.raises(ValidationError):
            production_capacity(0, 8)
        with pytest.raises(InvalidQuantityError):
            production_capacity(5, -1)
        assert production_capacity(5, 0).quantity == 0


class TestBatchCapacity:
    def test_with_units(self):
        r = calculate_batch_capacity(8, (45, "min"), batch_size=100)
        assert (r.full_batches, r.leftover_time, r.quantity) == (10, D("0.5"), 1000)
        assert abs(Fraction(r.next_batch_fraction) - Fraction(2, 3)) < Fraction(1, 10**45)

    def test_exact_fit(self):
        r = calculate_batch_capacity(6, 2)
        assert (r.full_batches, r.leftover_time, r.quantity) == (3, 0, None)

    def test_less_than_one_batch(self):
        assert calculate_batch_capacity(1, 2).full_batches == 0

    @pytest.mark.parametrize("per", [0, -1])
    def test_batch_time_positive(self, per):
        with pytest.raises(ValidationError):
            calculate_batch_capacity(8, per)

    def test_bad_unit(self):
        with pytest.raises(IncompatibleUnitError):
            calculate_batch_capacity(8, (1, "kg"))


@given(st.fractions(min_value=0, max_value=10**6), st.fractions(min_value=Fraction(1, 1000), max_value=10**4))
def test_batch_invariants(qty, size):
    p = calculate_batches(qty, size)
    tol = Fraction(1, 10**35)
    assert abs(Fraction(p.full_batches) * size + Fraction(p.partial_batch_quantity) - qty) < tol
    assert 0 <= p.partial_batch_quantity < size or abs(Fraction(p.partial_batch_quantity) - size) < tol
    assert p.batches_required - p.full_batches in (0, 1)
    assert Fraction(p.total_capacity) + tol >= qty


@given(
    st.integers(min_value=0, max_value=10**6),
    st.integers(min_value=1, max_value=10**4),
    st.integers(min_value=1, max_value=100),
)
def test_time_capacity_round_trip(qty, rate, eff):
    t = production_time(qty, rate, efficiency_percent=eff)
    c = production_capacity(rate, t.total_time, efficiency_percent=eff)
    assert abs(Fraction(c.exact_quantity) - qty) < Fraction(1, 10**30) * max(1, qty)
