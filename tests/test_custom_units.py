import json
from decimal import Decimal

import pytest

from atica.exceptions import (
    ConfigurationError,
    IncompatibleUnitError,
    InvalidConversionError,
    UnknownUnitError,
)
from atica.units import UnitRegistry, convert, register_unit


def test_spec_example_default_registry():
    register_unit(name="industrial_bag", category="mass", reference_unit="kg", factor="25")
    assert convert(1, "industrial_bag", "kg").output_quantity == 25
    assert convert(2, "industrial_bag", "g").output_quantity == 50000
    assert convert(100, "kg", "industrial_bag").output_quantity == 4


def test_registered_unit_metadata(registry):
    u = registry.register_unit("bag", "mass", "kg", "25", symbol="bg", display_name="Bag")
    assert u.is_custom and u.base_unit == "g" and u.factor == 25000
    assert u.metadata["reference_unit"] == "kg"
    assert registry.get_custom_unit("bag") is registry.get("bag")
    assert [x.unit_id for x in registry.list_custom_units()] == ["bag"]


@pytest.mark.parametrize("factor", ["0", "-5", "abc", "", None, "nan"])
def test_invalid_factors_rejected(registry, factor):
    with pytest.raises(InvalidConversionError) as e:
        registry.register_unit("bag", "mass", "kg", factor)
    assert e.value.code == "INVALID_FACTOR"
    assert not registry.has_unit("bag")


def test_fraction_factor(registry):
    registry.register_unit("third_kg", "mass", "kg", "1/3")
    assert registry.convert(3, "third_kg", "kg").output_quantity == 1


def test_unknown_reference_rejected(registry):
    with pytest.raises(UnknownUnitError):
        registry.register_unit("bag", "mass", "nope", 5)


def test_incompatible_category_rejected(registry):
    with pytest.raises(IncompatibleUnitError):
        registry.register_unit("bag", "length", "kg", 5)


def test_unknown_category_rejected(registry):
    with pytest.raises(UnknownUnitError):
        registry.register_unit("bag", "weirdness", "kg", 5)


def test_duplicate_identifier_rejected(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    for name in ("bag", "kg", "lb", "celsius"):  # custom, standard id, standard alias
        with pytest.raises(InvalidConversionError) as e:
            registry.register_unit(name, "mass", "g", 1)
        assert e.value.code == "DUPLICATE_UNIT"


@pytest.mark.parametrize("name", ["", "  ", "has space", "x" * 65, None, 5, "tab\there"])
def test_invalid_identifier(registry, name):
    with pytest.raises(InvalidConversionError) as e:
        registry.register_unit(name, "mass", "kg", 1)
    assert e.value.code == "INVALID_IDENTIFIER"


def test_offset_scale_cannot_be_reference(registry):
    with pytest.raises(InvalidConversionError) as e:
        registry.register_unit("hot", "temperature", "celsius", 2)
    assert e.value.code == "INVALID_REFERENCE"


def test_chained_definitions(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    registry.register_unit("pallet_of_bags", "mass", "bag", 40)
    assert registry.convert(1, "pallet_of_bags", "kg").output_quantity == 1000


def test_update_recomputes_dependents(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    registry.register_unit("pallet_of_bags", "mass", "bag", 40)
    registry.update_unit("bag", factor="20")
    assert registry.convert(1, "bag", "kg").output_quantity == 20
    assert registry.convert(1, "pallet_of_bags", "kg").output_quantity == 800


def test_circular_definition_rejected_and_state_preserved(registry):
    registry.register_unit("a", "mass", "kg", 2)
    registry.register_unit("b", "mass", "a", 3)
    with pytest.raises(InvalidConversionError) as e:
        registry.update_unit("a", reference_unit="b")
    assert e.value.code == "CIRCULAR_DEFINITION"
    # nothing changed
    assert registry.convert(1, "b", "kg").output_quantity == 6
    with pytest.raises(InvalidConversionError) as e:
        registry.update_unit("a", reference_unit="a")
    assert e.value.code == "CIRCULAR_DEFINITION"


def test_failed_update_leaves_registry_intact(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    with pytest.raises(InvalidConversionError):
        registry.update_unit("bag", factor="0")
    with pytest.raises(IncompatibleUnitError):
        registry.update_unit("bag", reference_unit="m")
    assert registry.convert(1, "bag", "kg").output_quantity == 25


def test_update_unknown(registry):
    with pytest.raises(UnknownUnitError):
        registry.update_unit("ghost", factor=1)


def test_remove(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    registry.register_unit("big", "mass", "bag", 4)
    with pytest.raises(InvalidConversionError) as e:
        registry.remove_unit("bag")
    assert e.value.code == "UNIT_IN_USE"
    registry.remove_unit("big")
    registry.remove_unit("bag")
    assert not registry.has_unit("bag")
    with pytest.raises(InvalidConversionError) as e:
        registry.remove_unit("kg")
    assert e.value.code == "STANDARD_UNIT"
    with pytest.raises(UnknownUnitError):
        registry.remove_unit("bag")


def test_registries_are_isolated():
    company_a, company_b = UnitRegistry(), UnitRegistry()
    company_a.register_unit("bag", "mass", "kg", 25)
    company_b.register_unit("bag", "mass", "kg", 50)
    assert company_a.convert(1, "bag", "kg").output_quantity == 25
    assert company_b.convert(1, "bag", "kg").output_quantity == 50
    assert not UnitRegistry().has_unit("bag")


def test_save_and_load_round_trip(registry, tmp_path):
    registry.register_unit("bag", "mass", "kg", "25.5", symbol="bg")
    registry.register_unit("tray", "mass", "bag", "4")
    path = tmp_path / "units.json"
    registry.save(path)
    fresh = UnitRegistry()
    fresh.load(path)
    assert fresh.convert(1, "tray", "kg").output_quantity == Decimal("102")
    assert fresh.get("bag").symbol == "bg"
    assert json.loads(path.read_text())["schema_version"] == 1


def test_load_is_all_or_nothing(registry):
    registry.register_unit("keep", "mass", "kg", 2)
    bad = {
        "type": "atica.unit_registry",
        "schema_version": 1,
        "custom_units": [
            {"name": "ok", "category": "mass", "reference_unit": "kg", "factor": "1"},
            {"name": "broken", "category": "mass", "reference_unit": "ghost", "factor": "1"},
        ],
    }
    with pytest.raises(UnknownUnitError):
        registry.load_dict(bad)
    assert registry.has_unit("keep") and not registry.has_unit("ok")


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"type": "other"},
        {"type": "atica.unit_registry", "schema_version": 99, "custom_units": []},
        {"type": "atica.unit_registry", "schema_version": 1, "custom_units": "x"},
        {"type": "atica.unit_registry", "schema_version": 1, "custom_units": [5]},
        {"type": "atica.unit_registry", "schema_version": 1, "custom_units": [{"name": "x"}]},
    ],
)
def test_load_rejects_malformed(registry, data):
    with pytest.raises(ConfigurationError):
        registry.load_dict(data)


def test_load_rejects_non_json(registry, tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{not json")
    with pytest.raises(ConfigurationError):
        registry.load(p)


def test_copy_is_independent(registry):
    registry.register_unit("bag", "mass", "kg", 25)
    clone = registry.copy()
    clone.update_unit("bag", factor=1)
    assert registry.convert(1, "bag", "kg").output_quantity == 25
