import json
from decimal import Decimal
from fractions import Fraction

import pytest

from atica.core import (
    AticaError,
    CalculationError,
    IncompatibleUnitError,
    InvalidPercentageError,
    InvalidQuantityError,
    MissingInputError,
    PackagingError,
    UnknownUnitError,
    ValidationError,
    ZeroDenominatorError,
    validation,
)
from atica.packaging import breakdown
from atica.production import calculate_batches
from atica.units import convert


class TestResultConventions:
    def test_to_dict_number_modes(self):
        result = convert(25, "kg", "g")
        assert result.to_dict()["value"] == Decimal(25000)
        assert result.to_dict(numbers="str")["value"] == "25000"
        assert result.to_dict(numbers="float")["value"] == 25000.0
        assert json.loads(json.dumps(result.to_dict(numbers="str")))["unit"] == "g"
        with pytest.raises(ValueError):
            result.to_dict(numbers="bogus")

    def test_nested_results_and_enums_become_plain_data(self, product):
        plan = calculate_batches(250, 100).to_dict(numbers="str")
        assert plan["batches_required"] == "3" and plan["warnings"] == []
        data = breakdown(product, 250, "piece", "carton").to_dict(numbers="str")
        assert data["remainder_unit"] == "piece" and isinstance(data["warnings"], list)
        assert convert(1, "ft", "mm", rounding="half_up").to_dict()["rounding"] == "half_up"

    def test_explain_lists_fields(self):
        text = calculate_batches(250, 100).explain()
        assert (
            text.startswith("BatchPlan")
            and "batches required: 3" in text
            and "partial batch quantity: 50" in text
        )

    def test_results_are_immutable(self):
        result = calculate_batches(1, 1)
        with pytest.raises(AttributeError):
            result.full_batches = Decimal(5)  # type: ignore[misc]

    def test_numbers_are_decimal_never_float(self):
        for value in calculate_batches("0.3", "0.1").to_dict().values():
            assert not isinstance(value, float)


class TestExceptionHierarchy:
    def test_every_error_is_an_aticaerror_and_carries_context(self):
        with pytest.raises(AticaError) as info:
            convert(1, "kg", "m")
        err = info.value
        assert isinstance(err, IncompatibleUnitError) and err.parameter == "to_unit" and err.hint
        assert err.to_dict() == {
            "code": "INCOMPATIBLE_UNITS",
            "message": err.message,
            "parameter": "to_unit",
            "hint": err.hint,
        }
        assert err.hint in str(err) and err.message in str(err)

    @pytest.mark.parametrize(
        "exc, bases",
        [
            (ValidationError, (ValueError,)),
            (UnknownUnitError, (ValueError,)),
            (ZeroDenominatorError, (ZeroDivisionError, ArithmeticError, CalculationError)),
            (InvalidQuantityError, (ValidationError, ValueError)),
            (PackagingError, (AticaError,)),
        ],
    )
    def test_standard_bases_so_generic_handlers_work(self, exc, bases):
        assert all(issubclass(exc, b) for b in bases)

    def test_codes_are_unique_and_stable(self):
        import atica.core.exceptions as ex

        codes = {}
        for name in dir(ex):
            obj = getattr(ex, name)
            if isinstance(obj, type) and issubclass(obj, AticaError) and obj is not AticaError:
                assert obj.code not in codes, (name, codes.get(obj.code))
                codes[obj.code] = name
        assert {"INVALID_QUANTITY", "UNKNOWN_UNIT", "ZERO_DENOMINATOR", "INVALID_HIERARCHY"} <= set(codes)

    def test_no_hint_means_no_hint_text(self):
        assert str(AticaError("plain")) == "plain"


class TestValidationHelpers:
    def test_number_bounds(self):
        assert validation.number("5", "x", minimum=5) == 5
        with pytest.raises(InvalidQuantityError, match="greater than 5"):
            validation.number(5, "x", minimum=5, inclusive=False)
        with pytest.raises(InvalidQuantityError, match="at most 10"):
            validation.number(11, "x", maximum=10)
        assert validation.number(Fraction(1, 3), "x") == Fraction(1, 3)

    def test_sign_helpers(self):
        assert validation.non_negative(0, "x") == 0
        with pytest.raises(InvalidQuantityError):
            validation.non_negative(-1, "x")
        with pytest.raises(InvalidQuantityError):
            validation.positive(0, "x")
        assert validation.positive("0.001", "x") == Fraction(1, 1000)

    def test_whole_number(self):
        assert validation.whole_number("3.0", "n") == 3
        assert validation.whole_number(Decimal("7"), "n", minimum=7) == 7
        with pytest.raises(InvalidQuantityError, match="whole number"):
            validation.whole_number("2.5", "n")
        with pytest.raises(InvalidQuantityError, match="at least 1"):
            validation.whole_number(0, "n", minimum=1)

    def test_percentage(self):
        assert validation.percentage(0, "p") == 0 and validation.percentage("100", "p") == 100
        assert validation.percentage(None, "p", default=7) == 7
        with pytest.raises(InvalidPercentageError, match="below 100"):
            validation.percentage(100, "p", allow_100=False)
        with pytest.raises(InvalidPercentageError):
            validation.percentage(-0.01, "p")
        with pytest.raises(MissingInputError):
            validation.percentage(None, "p")

    def test_text(self):
        assert validation.text("  hi  ", "t") == "hi"
        with pytest.raises(MissingInputError):
            validation.text("   ", "t")
        with pytest.raises(ValidationError, match="must be text"):
            validation.text(5, "t")
        with pytest.raises(ValidationError, match="longer than"):
            validation.text("x" * 11, "t", max_length=10)

    def test_require(self):
        assert validation.require(0, "x") == 0
        with pytest.raises(MissingInputError) as info:
            validation.require(None, "x", hint="give x")
        assert info.value.parameter == "x" and "give x" in str(info.value)
