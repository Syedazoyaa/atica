# Core - `atica.core`

Infrastructure shared by every module: exceptions, precision, rounding, validation and result conventions.

## Precision

* Results are `decimal.Decimal`. Inside a calculation ATICA uses exact rational arithmetic (`fractions.Fraction`); it converts to `Decimal` **once**, at the end. Repeating decimals (`1/3`, `5/9`) therefore never accumulate error, and floor/ceiling decisions are made on the exact value (`240` pieces is exactly one carton, never `0.99999`).
* Only that last division can be inexact. It is rounded half-even to `get_precision()` significant digits - **50 by default**, far beyond physical meaning. Some limit is unavoidable for non-terminating results; it is configurable:

```python
from atica.core import get_precision, use_precision
from atica.units import convert

print(get_precision())  # 50
with use_precision(12):
    print(convert(1, "d", "wk").value)  # 0.142857142857
```

`use_precision(digits)` (5-1000) is scoped with a `contextvars.ContextVar`: thread-safe, task-safe, no process-wide mutable state. Because it is context-local, a new thread starts with the default precision - wrap the work *inside* the thread (or use `contextvars.copy_context().run`) if it needs a different value.

* Inputs: `int`, `Decimal`, `Fraction`, numeric `str`, `float` (read via `repr`, so `0.1` means `0.1`). `bool`, `None`, NaN, infinity and magnitudes beyond about 1e300 are rejected. Prefer strings or Decimals for exact decimal input.
* Float arithmetic is never used on quantities.

## Rounding

Two ideas, kept apart:

**Mathematical rounding** - `Rounding`: `NONE`, `HALF_UP` (ties away from zero), `HALF_EVEN` (banker's), `FLOOR`, `CEILING`, with `places` decimal places.

```python
from atica.core import round_value

print(round_value("2.675", "half_up", 2))  # 2.68   (exact decimal, unlike float)
print(round_value("2.5", "half_even"))  # 2
```

**Packaging constraints** - snapping to multiples of a package size:

```python
from atica.core import round_to_multiple, split_by_multiple

print(round_to_multiple(250, 240))  # 480   package ceiling
print(round_to_multiple(250, 240, "floor"))  # 240   package floor
s = split_by_multiple(250, 240)  # remainder preservation
print(s.packages, s.remainder)  # 1 10   (value == packages x multiple + remainder)
```

Functions that round take `rounding=` and `places=`; `places` with `rounding="none"` is contradictory and raises `InvalidRoundingError` instead of being ignored.

## Results

No universal result object. Calculations that produce several related figures return their own frozen dataclass deriving from `Result`; a few single-number helpers return a plain `Decimal` (`convert_quantity`, `packages_required`, `required_input_with_rework`, `round_value`, `round_to_multiple`):

* numbers are `Decimal`; `unit` names the unit of the main value; `exact_*` holds the unrounded value; `warnings` is a tuple of strings; `formula` states the formula used;
* `to_dict(numbers="decimal" | "str" | "float")` - plain data (`"str"` is JSON-safe and lossless);
* `explain()` - readable multi-line summary; `str(result)` is a short form such as `"25000 g"`.

## Exceptions

```text
AticaError
  ValidationError (ValueError)    MissingInputError, InvalidQuantityError, InvalidPercentageError,
                                  InvalidRoundingError, InvalidConfigurationError
  CalculationError (ArithmeticError)   ZeroDenominatorError, NumericRangeError, ConstraintError
  UnsupportedOperationError
  UnitError                       UnknownUnitError, IncompatibleUnitError, UnitDefinitionError
  PackagingError                  InvalidHierarchyError, UnknownPackagingLevelError
  MaterialError                   DuplicateMaterialError
  IntegrationError                MissingDependencyError (ImportError)
```

Each carries `message` (what and why), `parameter` (which input), `hint` (how to fix) and a stable `code` string; `to_dict()` gives all four. `str(exc)` is the message followed by `Hint: ...`.

## Validation helpers

`atica.core.validation`: `require`, `number(value, name, *, minimum, inclusive, maximum)`, `non_negative`, `positive`, `whole_number`, `percentage(value, name, *, allow_100, default)`, `text`. They return exact `Fraction`s (or `str`) and raise the specific errors above. Percentages use the 0-100 scale; the error for `0.05` out of range reminds you of that.
