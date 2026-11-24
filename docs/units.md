# Units - `atica.units`

Unit conversion between standard and custom units. Independent of any third-party conversion library.

```python
from atica.units import convert, UnitRegistry

print(convert(25, "kg", "g"))  # 25000 g

registry = UnitRegistry()  # your own, writable registry
registry.register_unit("bag", 25, "kg")  # 1 bag = 25 kg
print(convert(4, "bag", "kg", registry=registry))  # 100 kg
```

## Model

* Every unit belongs to a **category** (length, mass, area, volume, temperature, time, count, pressure, force, speed, power, energy, frequency, torque, voltage, current, resistance, or one you define). Only units of the **same category** convert; anything else raises `IncompatibleUnitError`.
* Each unit has an exact `factor` (and `offset`) to its category's base unit: `base = (value + offset) x factor`. All built-in factors are **exact by definition** (international yard and pound, US customary volumes, thermochemical calorie, standard gravity). `psi`, `lbf`, `hp`, `lbf-ft` are derived exactly from those definitions, not typed as rounded decimals.
* Conversion is exact rational arithmetic, rounded **once**, at the end, to `get_precision()` digits (default 50). So `212 F -> C` is exactly `100`.
* Unit names are **case-sensitive**; `mW`/`MW` can never be confused. An unknown name is an error with suggestions - never guessed.
* Time has no month/year (their length is ambiguous).

Built-in categories and base units: `length m`, `mass g`, `area m2`, `volume L`, `temperature K`, `time s`, `count piece`, `pressure Pa`, `force N`, `speed m/s`, `power W`, `energy J`, `frequency Hz`, `torque Nm`, `voltage V`, `current A`, `resistance ohm`. List them with `list_categories()` / `list_units("mass")`.

## `convert(value, from_unit, to_unit, *, rounding="none", places=0, interval=False, registry=None) -> Conversion`

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `value` | int, Decimal, Fraction, numeric str, float | yes | amount. Floats are read through `repr` (`0.1` is `0.1`). NaN, infinity, bool, `None` rejected; magnitude must be within about 1e-300..1e300 |
| `from_unit`, `to_unit` | str | yes | symbol or alias, e.g. `"kg"`, `"kilogram"`, `"C"`, `"degC"` |
| `rounding` | `"none"`, `"half_up"`, `"half_even"`, `"floor"`, `"ceiling"` | no | rounding of the result; `"none"` keeps the exact value |
| `places` | int | no | decimal places for the rounding (negative = tens, hundreds ...). Non-zero `places` with `rounding="none"` is rejected |
| `interval` | bool | no | temperature **differences** (no offsets) - only for temperature units |
| `registry` | `UnitRegistry` | no | registry with custom units; default is the read-only standard registry |

**Returns** `Conversion`: `value`, `unit` (canonical symbol), `source_value`, `source_unit`, `category`, `exact_value`, `rounding`, `places`, `formula`, `warnings`. `str()` gives `"25000 g"`.

**Formula** `target = ((value + offset_src) x factor_src) / factor_dst - offset_dst`; offsets are zero except Celsius (273.15) and Fahrenheit (459.67). With `interval=True` the offsets are ignored.

**Assumptions** absolute temperatures are physical: anything below absolute zero is rejected. Rankine/Kelvin are linear, Celsius/Fahrenheit offset scales.

**Raises** `UnknownUnitError`, `IncompatibleUnitError`, `InvalidQuantityError` (bad number or below absolute zero), `NumericRangeError`, `InvalidRoundingError`, `UnsupportedOperationError` (`interval` on a non-temperature).

```python
from atica.units import convert

print(convert(100, "C", "F"))  # 212 F
print(convert(5, "C", "F", interval=True))  # 9 F
print(convert("0.5", "kg", "lb", rounding="half_up", places=3))  # 1.102 lb
```

## `UnitRegistry`

A set of units. Registries are fully independent; there is **no shared mutable state**: the module-level functions use a *read-only* default registry (`default_registry()`), and custom units live in registries you create.

| Method | Purpose |
|---|---|
| `convert(...)` | same as the module function, on this registry |
| `factor(from_unit, to_unit) -> Fraction` | exact multiplier (non-offset units only; used by BOM/purchasing) |
| `get(name) -> Unit`, `name in registry` | lookup |
| `units(category=None)`, `categories()`, `base_unit(category)` | catalogue |
| `are_compatible(a, b)` | same category? |
| `register_unit(name, factor, reference_unit, *, aliases=(), display_name=None)` | define `1 name = factor reference_unit`. `factor` may be `25`, `"0.5"`, `"1/3"` |
| `register_base_unit(name, category, *, aliases=())` | create a new category (e.g. `sheet`) |
| `unregister_unit(name)` | remove a custom unit that nothing else is defined from |
| `to_dict()` / `UnitRegistry.from_dict(data)` | JSON-friendly save/load of custom units (the library never touches files itself) |
| `copy()`, `freeze()`, `frozen` | writable copy / make read-only |

Rules: names must be new (existing units can never be redefined, which also rules out circular definitions); the reference must exist; offset scales (C, F) cannot be a reference (use K); the factor must be `> 0`.

```python
from atica.units import UnitRegistry

reg = UnitRegistry()
reg.register_base_unit("sheet", "paper_count", aliases=["sheets"])
reg.register_unit("ream", 500, "sheet")
print(reg.convert(2, "ream", "sheets"))  # 1000 sheet
```

## Other functions

`are_compatible(a, b, *, registry=None)`, `get_unit(name, *, registry=None)`, `list_units(category=None, *, registry=None)`, `list_categories(*, registry=None)`, `default_registry()`.

## Verification

Factors are checked in the test suite against published constants (NIST SP 811, SI brochure): e.g. `1 in = 25.4 mm`, `1 lb = 453.59237 g`, `1 gal = 3.785411784 L`, `1 acre = 4046.8564224 m2`, `1 psi = 6894.757293168 Pa`, `1 hp = 745.69987158227 W`; temperatures `0 C = 32 F`, `-40 C = -40 F`, `-459.67 F = 0 K`; plus round-trip and linearity property tests.
