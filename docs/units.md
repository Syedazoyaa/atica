# Units (M01) and custom units (M02)

## Model

`base = (value + offset) * factor`, `result = base / target.factor - target.offset`.
Ordinary units have `offset = 0` (strategy `linear`), so this is `value x source_factor / target_factor`.
Temperature scales use strategy `offset`:

| Unit | factor | offset | base (kelvin) |
|---|---|---|---|
| celsius | 1 | 273.15 | `C + 273.15` |
| fahrenheit | 5/9 | 459.67 | `(F + 459.67) x 5/9` |
| kelvin | 1 | 0 | `K` |

Values below absolute zero raise `InvalidConversionError` (`BELOW_ABSOLUTE_ZERO`).

## Categories and base units

length `m` · mass `g` · area `m2` · volume `litre` · temperature `kelvin` · time `second` · pressure `Pa` · force `N` ·
speed `m/s` · power `W` · energy `J` · frequency `Hz` · voltage `V` · current `A` · resistance `ohm` · torque `Nm`.

`list_units(category)` lists every built-in unit. Each carries `metadata["exact"]`; conversions
using approximate factors (`psi`, `hp`, `lb-ft`) return a warning.

## Identifiers

Identifiers are **case-sensitive**: `mW` is unknown rather than silently read as `MW`. Common aliases exist
(`lb`, `oz`, `in`, `ft`, `C`, `F`, `K`, `L`, `h`, `min`, `kph`, ...).

## API

```python
convert(value, from_unit, to_unit, *, precision=None, rounding=None, registry=None) -> CalculationResult
get_unit(name) / list_units(category=None) / list_categories() / get_base_unit(category) / are_compatible(a, b)
register_unit(name, category, reference_unit, factor, *, symbol=None, display_name=None, metadata=None)
update_unit(name, factor=..., reference_unit=..., category=...) / remove_unit(name)
get_custom_unit / list_custom_units / save_units(path) / load_units(path)
```

`precision` is a number of decimal places and `rounding` a policy (default `half_up` when `precision` is set).
The unrounded value stays in `result.metadata["exact_quantity"]`.

Fractional factors are accepted as strings: `register_unit("third", "mass", "kg", "1/3")`.

## Custom unit rules

`register_unit` rejects: unknown reference or category, a category different from the reference's, zero / negative / non-numeric
factors, duplicate identifiers (including built-in names and aliases), offset scales (Celsius/Fahrenheit) as a reference, and
circular definitions (checked on `update_unit`). Definitions may chain (`pallet_of_bags = 40 bag`); updating a unit
recomputes everything that depends on it, and removal is refused while something depends on the unit.
Failed operations change nothing.

## Persistence

`registry.save(path)` / `registry.load(path)` write JSON `{type, schema_version, custom_units: [...]}`. Loading is all-or-nothing and
rejects wrong types, unknown schema versions and invalid definitions.
