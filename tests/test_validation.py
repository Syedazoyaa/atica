import pytest

from atica.exceptions import (
    AticaError,
    BulkProcessingError,
    IncompatibleUnitError,
    InvalidConversionError,
    InvalidHierarchyError,
    InvalidQuantityError,
    InventoryError,
    ManufacturingError,
    PackagingError,
    UnitError,
    UnknownProductError,
    UnknownUnitError,
    ValidationError,
)
from atica.packaging import PackagingLevel, Product
from atica.validation import (
    ValidationResult,
    check_rate,
    validate_custom_unit,
    validate_levels,
    validate_material,
    validate_production_inputs,
    validate_purchase_inputs,
    validate_unit_conversion,
)


def test_structured_format_matches_spec():
    r = validate_unit_conversion(1, "kg", "m")
    assert r.to_dict() == {
        "valid": False,
        "errors": [
            {"code": "INCOMPATIBLE_UNITS", "field": "to_unit", "message": "Cannot convert kg to m (mass vs length)."}
        ],
        "warnings": [],
    }
    assert not r and not r.valid


def test_valid_conversion_has_no_errors():
    r = validate_unit_conversion("5", "kg", "g")
    assert r.valid and r.to_dict() == {"valid": True, "errors": [], "warnings": []}


def test_multiple_problems_reported_together():
    r = validate_unit_conversion("abc", "nope", "")
    assert {(e.code, e.field) for e in r.errors} == {
        ("INVALID_NUMBER", "value"), ("UNKNOWN_UNIT", "from_unit"), ("MISSING_UNIT", "to_unit")}


def test_warning_for_approximate_factor():
    r = validate_unit_conversion(1, "psi", "bar")
    assert r.valid and r.warnings[0].code == "APPROXIMATE_FACTOR"


def test_validate_custom_unit_is_a_dry_run(registry):
    assert validate_custom_unit("bag", "mass", "kg", 25, registry).valid
    assert not registry.has_unit("bag")
    assert validate_custom_unit("bag", "mass", "kg", 0, registry).errors[0].code == "INVALID_FACTOR"
    assert validate_custom_unit("kg", "mass", "g", 1, registry).errors[0].code == "DUPLICATE_UNIT"
    assert validate_custom_unit("x", "mass", "zzz", 1, registry).errors[0].code == "UNKNOWN_UNIT"
    assert validate_custom_unit("x", "length", "kg", 1, registry).errors[0].code == "INCOMPATIBLE_UNITS"


def test_every_error_has_code_and_message():
    for result in (
        validate_unit_conversion("x", "y", "z"),
        validate_levels([]),
        validate_production_inputs(-1, -1, 5, 5),
        validate_purchase_inputs(-1, 0, -1, -1),
        validate_material("", "", "x", 2),
    ):
        assert result.errors
        for e in result.errors:
            assert e.code and e.message and isinstance(e.code, str)


def test_levels_validation_codes():
    lv = PackagingLevel
    assert {e.code for e in validate_levels([lv("a", 1), lv("A", 1)]).errors} >= {"DUPLICATE_LEVEL"}
    assert {e.code for e in validate_levels([lv("a", 1), lv("b", 0, "a")]).errors} == {"INVALID_PACKAGE_QUANTITY"}
    assert validate_levels([lv("a", 1), lv("b", 3, "a"), lv("c", 2, "b")]).valid


def test_production_input_validation():
    codes = {e.code for e in validate_production_inputs(-5, -1, "2", "1").errors}
    assert codes == {"INVALID_PRODUCTION_QUANTITY", "INVALID_MATERIAL_CONSUMPTION", "INVALID_SCRAP_RATE", "INVALID_WASTAGE_RATE"}
    assert validate_production_inputs(None).errors[0].code == "MISSING_INPUT"
    assert validate_production_inputs(10, "0.5", "0.1", "0.2").valid


def test_rate_boundaries():
    r = ValidationResult()
    assert check_rate(r, "0", "x") == 0 and check_rate(r, "0.999", "x") is not None
    assert r.valid
    for bad in ("1", "-0.001", "1.01"):
        r = ValidationResult()
        assert check_rate(r, bad, "x", "CODE") is None and r.errors[0].code == "CODE"


def test_purchase_validation():
    assert validate_purchase_inputs(10, 12, 24).valid
    assert {e.code for e in validate_purchase_inputs(10, 0, -1).errors} == {
        "INVALID_ORDER_MULTIPLE", "INVALID_MINIMUM_ORDER_QUANTITY"}


def test_raise_if_invalid_carries_details():
    r = validate_production_inputs(-5, None, "2")
    with pytest.raises(ManufacturingError) as e:
        r.raise_if_invalid(ManufacturingError)
    assert e.value.code == "INVALID_PRODUCTION_QUANTITY"
    assert e.value.details is r
    assert "+1 more" in e.value.message
    ValidationResult().raise_if_invalid()  # valid: no exception


def test_merge():
    a = ValidationResult(); a.add_error("A", "f", "m")
    b = ValidationResult(); b.add_warning("W", None, "w")
    assert a.merge(b).to_dict()["warnings"][0]["code"] == "W"


def test_exception_hierarchy_and_codes():
    tree = {
        UnitError: AticaError, UnknownUnitError: UnitError, IncompatibleUnitError: UnitError,
        InvalidConversionError: UnitError, PackagingError: AticaError, InvalidHierarchyError: PackagingError,
        UnknownProductError: PackagingError, ManufacturingError: AticaError, InventoryError: AticaError,
        ValidationError: AticaError, BulkProcessingError: AticaError, InvalidQuantityError: ValidationError,
    }
    for child, parent in tree.items():
        assert issubclass(child, parent)
        assert child.code
    err = UnknownUnitError("boom", field="unit")
    assert err.to_dict() == {"code": "UNKNOWN_UNIT", "field": "unit", "message": "boom"}
    assert str(err) == "boom"


def test_product_validate_returns_structured_result():
    p = Product("P", "P")
    p.add_level(PackagingLevel("piece", 1))
    p.add_level(PackagingLevel("pallet", 4, parent="carton"))
    d = p.validate().to_dict()
    assert d["valid"] is False and d["errors"][0]["code"] == "MISSING_LEVEL"
