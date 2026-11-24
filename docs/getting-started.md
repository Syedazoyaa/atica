# Getting started

## Install

```bash
pip install atica
```

Installs the library and the desktop app (PySide6 is a normal dependency). Optional Excel support: `pip install "atica[excel]"`.

## Your first calculations

```python
from atica.units import convert

print(convert(25, "kg", "g"))  # 25000 g
print(convert("212", "F", "C"))  # 100 C   (exact: temperatures use offsets)
print(convert(5, "C", "F", interval=True))  # 9 F    (a *difference* of 5 C is 9 F)
```

Results are objects, not bare numbers:

```python
from atica.units import convert

r = convert(1, "ft", "mm", rounding="half_up", places=0)
print(r.value)  # 305            - what you asked for
print(r.exact_value)  # 304.8          - before rounding
print(r.unit)  # mm
print(r.to_dict(numbers="str"))  # plain data, JSON-safe
print(r.explain())  # readable summary of every field
```

## Errors are specific and actionable

```python
from atica.units import convert
from atica.core import AticaError, IncompatibleUnitError

try:
    convert(1, "kg", "m")
except IncompatibleUnitError as exc:
    print(exc.message)  # Cannot convert kg (mass) to m (length): they measure different things.
    print(exc.parameter)  # to_unit
    print(exc.hint)  # Units compatible with kg include: mg, g, kg, t, lb, oz.
```

Every error derives from `AticaError`; validation errors are also `ValueError`, arithmetic ones `ArithmeticError`. Nothing is silently replaced by `0`, `None` or a guess.

## Precision

```python
from fractions import Fraction
from atica.core import use_precision
from atica.units import convert

print(convert(1, "d", "wk").value)  # 0.14285714285714285714285714285714285714285714285714  (50 digits)
with use_precision(10):
    print(convert(1, "d", "wk").value)  # 0.1428571429
```

## The desktop app

```bash
atica-gui
```

See [gui.md](gui.md).
