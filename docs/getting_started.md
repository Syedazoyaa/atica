# Getting started

```bash
pip install atica
```

## 1. Convert units

```python
from atica.units import convert

r = convert("2.5", "kg", "g")
str(r)                 # '2500 g'
r.output_quantity      # Decimal('2500')
r.formula              # 'value x 1000'
convert(1, "minute", "hour", precision=4).output_quantity   # Decimal('0.0167')
```

Converting across categories raises `IncompatibleUnitError` (code `INCOMPATIBLE_UNITS`):

```python
from atica.exceptions import IncompatibleUnitError
try:
    convert(10, "W", "V")
except IncompatibleUnitError as e:
    print(e.code, e.message)
```

## 2. Define your own units

```python
from atica.units import UnitRegistry

acme = UnitRegistry()                        # isolated from every other registry
acme.register_unit("industrial_bag", "mass", "kg", "25")
acme.convert(2, "industrial_bag", "kg")      # 50 kg
acme.save("acme_units.json")
```

## 3. Model a product's packaging

```python
from atica.packaging import Product, PackagingLevel, breakdown

p = Product("PROD-001", "Product A")
p.add_level(PackagingLevel("piece", contains=1))
p.add_level(PackagingLevel("box", contains=12, parent="piece"))
p.add_level(PackagingLevel("carton", contains=20, parent="box"))
p.add_level(PackagingLevel("pallet", contains=40, parent="carton"))
print(breakdown(p, 850, "carton", "pallet"))
# 850 carton = 21 full pallet + 10 carton remaining (22 pallet required)
```

## 4. Manufacturing and purchasing

```python
from atica.manufacturing import calculate_material_requirement
from atica.inventory import calculate_purchase_quantity

need = calculate_material_requirement("0.5", 1000, "kg", scrap_rate="0.05", units_rounding="up")
need.quantity                         # Decimal('526.5')   (1053 units started x 0.5 kg)
calculate_purchase_quantity(need.quantity, order_multiple=25, unit="kg").quantity   # Decimal('550')
```

## 5. Process a file

```python
from atica.io import process_file, export_results, export_errors

bulk = process_file("orders.csv", products=[p])
print(bulk.summary)
for row in bulk.failures():
    print(row.row_number, row.errors)
export_results(bulk, "results.csv")
```

## 6. Save everything

```python
from atica import AticaConfig
cfg = AticaConfig()
cfg.registry.register_unit("bag", "mass", "kg", 25)
cfg.add_product(p)
cfg.save("company.json")
cfg = AticaConfig.load("company.json")
```

## 7. Validate without raising

```python
from atica.validation import validate_unit_conversion
validate_unit_conversion(1, "kg", "m").to_dict()
# {'valid': False, 'errors': [{'code': 'INCOMPATIBLE_UNITS', 'field': 'to_unit', 'message': ...}], 'warnings': []}
p.validate().to_dict()
```
