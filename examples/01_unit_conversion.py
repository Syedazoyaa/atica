"""Unit conversion: standard units, temperatures, rounding and custom units."""

from atica.units import UnitRegistry, convert

print(convert(25, "kg", "g"))  # 25000 g
print(convert("212", "F", "C"))  # 100 C   (exact: offsets, not just a factor)
print(convert(5, "C", "F", interval=True))  # 9 F     (a temperature *difference*)

r = convert(1, "ft", "mm", rounding="half_up", places=0)
print(r.value, r.exact_value)  # 305 304.8
assert str(r.value) == "305" and str(r.exact_value) == "304.8"

# Your own units live in your own registry (the default one is read-only).
registry = UnitRegistry()
registry.register_unit("bag", 25, "kg")  # 1 bag = 25 kg
print(convert(4, "bag", "kg", registry=registry))  # 100 kg
assert str(convert(4, "bag", "kg", registry=registry)) == "100 kg"

# Incompatible units are rejected - never guessed.
try:
    convert(1, "kg", "m")
except ValueError as exc:  # IncompatibleUnitError is a ValueError (and an AticaError)
    print("rejected:", exc.message)
