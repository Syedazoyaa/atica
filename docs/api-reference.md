# API reference

*Generated from the source by `docs/_generate_api.py` - do not edit by hand.*

Narrative guides with formulas and assumptions: [units](units.md), [packaging](packaging.md), [materials](materials.md), [production](production.md), [quality](quality.md), [purchasing](purchasing.md), [integrations](integrations.md), [core](core.md).


## Units - `atica.units`

### class `Conversion(value: 'Decimal', unit: 'str', source_value: 'Decimal', source_unit: 'str', category: 'str', exact_value: 'Decimal', rounding: 'Rounding' = <Rounding.NONE: 'none'>, places: 'int' = 0, formula: 'str' = '', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`~atica.units.convert`.

``value`` is in ``unit``; ``exact_value`` is the same before any requested rounding.
``str(conversion)`` is ``"2500 g"``.

Fields: `value`, `unit`, `source_value`, `source_unit`, `category`, `exact_value`, `rounding`, `places`, `formula`, `warnings`

### class `Unit(symbol: 'str', name: 'str', category: 'str', factor: 'Fraction', offset: 'Fraction' = Fraction(0, 1), aliases: 'Tuple[str, ...]' = (), custom: 'bool' = False, definition: 'Optional[Tuple[str, Fraction]]' = None) -> None`

A unit of measurement.

``symbol`` is the canonical identifier (also what results report); ``aliases``
are other accepted spellings.  ``definition`` is ``(reference_symbol, ratio)`` for
custom units (``1 symbol = ratio reference``) and ``None`` for built-ins.

Fields: `symbol`, `name`, `category`, `factor`, `offset`, `aliases`, `custom`, `definition`

### class `UnitRegistry(*, include_standard: 'bool' = True) -> 'None'`

A set of units. Registries are independent of one another.

``UnitRegistry()`` contains every standard unit and may be extended with
:meth:`register_unit`; a *frozen* registry (such as the shared default one) rejects changes.

#### `UnitRegistry.are_compatible(self, unit_a: 'str', unit_b: 'str') -> 'bool'`

True when both units measure the same kind of quantity.

#### `UnitRegistry.base_unit(self, category: 'str') -> 'str'`

Symbol of the base unit of ``category``.

#### `UnitRegistry.categories(self) -> 'Tuple[str, ...]'`

Names of all measurement categories.

#### `UnitRegistry.convert(self, value: 'Any', from_unit: 'str', to_unit: 'str', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, interval: 'bool' = False) -> 'Conversion'`

Convert ``value`` from ``from_unit`` to ``to_unit`` (see :func:`atica.units.convert`).

#### `UnitRegistry.copy(self) -> 'UnitRegistry'`

An independent, writable copy.

#### `UnitRegistry.custom_units(self) -> 'Tuple[Unit, ...]'`

User-defined units, in registration order.

#### `UnitRegistry.factor(self, from_unit: 'str', to_unit: 'str') -> 'Fraction'`

Exact multiplier ``m`` with ``value_in_to_unit = value_in_from_unit * m``.

Only defined for ordinary (non-offset) units; raises
:class:`~atica.core.exceptions.UnsupportedOperationError` for Celsius/Fahrenheit.

#### `UnitRegistry.freeze(self) -> 'UnitRegistry'`

Make this registry read-only (irreversible; use :meth:`copy` for a writable one).

#### `UnitRegistry.from_dict(data: 'Mapping[str, Any]') -> 'UnitRegistry'`

Rebuild a registry written by :meth:`to_dict` (all-or-nothing).

#### `UnitRegistry.get(self, name: 'str') -> 'Unit'`

Return the unit called ``name`` (symbol or alias, case-sensitive).

#### `UnitRegistry.register_base_unit(self, name: 'str', category: 'str', *, aliases: 'Iterable[str]' = ()) -> 'Unit'`

Create a brand-new measurement category with its base unit (e.g. ``'sheet'``, ``'sheets'``).

Further units of that category are then added with :meth:`register_unit`.

#### `UnitRegistry.register_unit(self, name: 'str', factor: 'Any', reference_unit: 'str', *, aliases: 'Iterable[str]' = (), display_name: 'Optional[str]' = None) -> 'Unit'`

Define ``1 <name> = <factor> <reference_unit>``.

>>> reg = UnitRegistry()
>>> _ = reg.register_unit("bag", 25, "kg")
>>> str(reg.convert(4, "bag", "kg"))
'100 kg'

The new unit belongs to the reference unit's category.  Offset scales
(Celsius, Fahrenheit) cannot be used as a reference.  Existing names can
never be redefined, which also makes circular definitions impossible.

#### `UnitRegistry.to_dict(self) -> 'Dict[str, Any]'`

JSON-friendly description of the custom units/categories (built-ins are implicit).

#### `UnitRegistry.units(self, category: 'Optional[str]' = None) -> 'Tuple[Unit, ...]'`

All units, optionally only those of one ``category``.

#### `UnitRegistry.unregister_unit(self, name: 'str') -> 'None'`

Remove a custom unit (not allowed for built-in units or units others are defined from).

### `are_compatible(unit_a: 'str', unit_b: 'str', *, registry: 'Optional[UnitRegistry]' = None) -> 'bool'`

True if the two units can be converted into each other.

### `convert(value: 'Any', from_unit: 'str', to_unit: 'str', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, interval: 'bool' = False, registry: 'Optional[UnitRegistry]' = None) -> 'Conversion'`

Convert ``value`` from ``from_unit`` to ``to_unit``.

:param value: the amount (int, Decimal, numeric string or float; see
    :func:`atica.core.precision.to_decimal`).
:param from_unit: source unit symbol or alias (case-sensitive), e.g. ``"kg"``.
:param to_unit: target unit; must measure the same kind of quantity.
:param rounding: ``'none'`` (default; exact up to the library precision),
    ``'half_up'``, ``'half_even'``, ``'floor'`` or ``'ceiling'``.
:param places: decimal places for the rounding (requires a rounding policy).
:param interval: treat a temperature as a *difference* (no offsets), e.g. +-5 C in F.
:param registry: a :class:`UnitRegistry` with custom units (default: standard units).
:returns: :class:`Conversion` (``.value``, ``.unit``, ``.exact_value`` ...).
:raises UnknownUnitError: a unit is not defined.
:raises IncompatibleUnitError: the units measure different things.
:raises InvalidQuantityError: invalid number, or a temperature below absolute zero.

Formula: ``target = ((value + offset_src) * factor_src) / factor_dst - offset_dst``
(offsets are zero except for Celsius/Fahrenheit).  Computed exactly, rounded once.

>>> str(convert("212", "F", "C"))
'100 C'

### `default_registry() -> 'UnitRegistry'`

The shared, **read-only** registry holding the standard units.

Use ``UnitRegistry()`` for your own writable registry with custom units.

### `get_unit(name: 'str', *, registry: 'Optional[UnitRegistry]' = None) -> 'Unit'`

Look up a unit by symbol or alias.

### `list_categories(*, registry: 'Optional[UnitRegistry]' = None) -> 'Tuple[str, ...]'`

All measurement categories.

### `list_units(category: 'Optional[str]' = None, *, registry: 'Optional[UnitRegistry]' = None) -> 'Tuple[Unit, ...]'`

All units (optionally of one category).


## Packaging - `atica.packaging`

### class `PackagingBreakdown(product_id: 'str', quantity: 'Decimal', from_level: 'str', to_level: 'str', exact_packages: 'Decimal', full_packages: 'Decimal', remainder: 'Decimal', remainder_unit: 'str', packages_required: 'Decimal', packaged_quantity: 'Decimal', surplus: 'Decimal', units_per_package: 'Decimal', formula: 'str' = 'exact = quantity x size(from) / size(to); full = floor(exact); required = ceil(exact)', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`breakdown` (``quantity`` of ``from_level`` expressed in ``to_level`` packages).

* ``exact_packages``    - the exact (possibly fractional) conversion, a ratio;
* ``full_packages``     - complete ``to_level`` packages (``floor(exact_packages)``);
* ``remainder``         - what is left after the full packages, in ``remainder_unit``
  (the *smaller* of the two levels, so going 250 piece -> carton leaves "10 piece");
* ``packages_required`` - whole packages needed to hold **everything** (``ceil``);
* ``packaged_quantity`` - quantity those required packages cover, in ``from_level`` units;
* ``surplus``           - ``packaged_quantity - quantity`` (>= 0), in ``from_level`` units;
* ``units_per_package`` - how many ``from_level`` units fill one ``to_level`` package.

Fields: `product_id`, `quantity`, `from_level`, `to_level`, `exact_packages`, `full_packages`, `remainder`, `remainder_unit`, `packages_required`, `packaged_quantity`, `surplus`, `units_per_package`, `formula`, `warnings`

### class `PackagingLevel(name: 'str', contains: 'Decimal' = Decimal('1'), of: 'Optional[str]' = None) -> None`

One level of a packaging hierarchy (see the module docstring for the direction).

Fields: `name`, `contains`, `of`

#### `PackagingLevel.from_dict(data: 'Mapping[str, Any]') -> 'PackagingLevel'`

*(no description)*

#### `PackagingLevel.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

### class `PackagingPlan(product_id: 'str', quantity: 'Decimal', from_level: 'str', counts: 'Tuple[Tuple[str, Decimal], ...]', remainder: 'Decimal', base_unit: 'str') -> None`

Result of :func:`decompose`: a quantity as whole packages at every level.

``counts`` lists ``(level, whole_count)`` from the largest level to the *second* smallest;
``remainder`` is what is left in the base unit (``base_unit``) and may be fractional.
``sum(count * size(level)) + remainder == quantity`` in base units.

Fields: `product_id`, `quantity`, `from_level`, `counts`, `remainder`, `base_unit`

#### `PackagingPlan.by_level(self) -> 'Dict[str, Decimal]'`

``{level: count}`` including the base level's remainder.

### class `Product(product_id: 'str', name: 'str' = '', levels: 'Tuple[PackagingLevel, ...]' = ()) -> None`

A product and its (immutable) packaging hierarchy.

The hierarchy is validated on construction, so a ``Product`` is always consistent.
"Modifying" a product returns a new one (:meth:`with_level`, :meth:`without_top_level`);
the original is never changed.

>>> p = Product("P001", "Product A", levels=[
...     PackagingLevel("piece"), PackagingLevel("box", 12, "piece"), PackagingLevel("carton", 20, "box")])
>>> p.size_of("carton")
Decimal('240')

Fields: `product_id`, `name`, `levels`

#### `Product.from_dict(data: 'Mapping[str, Any]') -> 'Product'`

*(no description)*

#### `Product.has_level(self, name: 'str') -> 'bool'`

*(no description)*

#### `Product.level(self, name: 'str') -> 'PackagingLevel'`

The level called ``name`` (case-insensitive).

#### `Product.size_of(self, name: 'str') -> 'Decimal'`

How many base units (e.g. pieces) one ``name`` holds.

#### `Product.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

#### `Product.units_per(self, larger: 'str', smaller: 'str') -> 'Decimal'`

How many ``smaller`` units make one ``larger`` (a fraction if ``larger`` is the smaller one).

#### `Product.with_level(self, level: 'PackagingLevel') -> 'Product'`

A new product with ``level`` added (this product is unchanged).

#### `Product.without_top_level(self) -> 'Product'`

A new product without its largest level.

### `breakdown(product: 'Product', quantity: 'Any', from_level: 'str', to_level: 'str', *, require_whole: 'bool' = False) -> 'PackagingBreakdown'`

Break ``quantity`` of ``from_level`` into ``to_level`` packages.

:param product: the :class:`Product` that defines the hierarchy.
:param quantity: non-negative amount of ``from_level`` units (fractions allowed).
:param from_level: level the quantity is measured in, e.g. ``"piece"``.
:param to_level: level to pack into, e.g. ``"carton"`` (may be larger or smaller).
:param require_whole: reject fractional quantities.
:returns: :class:`PackagingBreakdown`.
:raises UnknownPackagingLevelError: a level is not in the product.
:raises InvalidQuantityError: negative / non-numeric / (with ``require_whole``) fractional quantity.

With 1 carton = 20 boxes = 240 pieces, 250 pieces give ``full_packages=1``,
``remainder=10 piece`` and ``packages_required=2``.

>>> from atica.packaging import PackagingLevel, Product
>>> p = Product("P", "A", levels=[PackagingLevel("piece"), PackagingLevel("box", 12, "piece"),
...                               PackagingLevel("carton", 20, "box")])
>>> r = breakdown(p, 250, "piece", "carton")
>>> (int(r.full_packages), int(r.remainder), int(r.packages_required))
(1, 10, 2)

### `convert_quantity(product: 'Product', quantity: 'Any', from_level: 'str', to_level: 'str') -> 'Decimal'`

Exact equivalent of ``quantity`` ``from_level`` in ``to_level`` (850 cartons -> 21.25 pallets).

Formula: ``quantity x size(from_level) / size(to_level)`` where ``size`` counts base units.

### `decompose(product: 'Product', quantity: 'Any', from_level: 'str' = '') -> 'PackagingPlan'`

Express ``quantity`` as whole packages at every level, largest first.

``from_level`` defaults to the base level.  With 1 box = 12 pieces, 1 carton = 20 boxes,
250 pieces -> 1 carton, 0 boxes, 10 pieces.

>>> from atica.packaging import PackagingLevel, Product
>>> p = Product("P", "A", levels=[PackagingLevel("piece"), PackagingLevel("box", 12, "piece"),
...                               PackagingLevel("carton", 20, "box")])
>>> {k: int(v) for k, v in decompose(p, 250).by_level().items()}
{'carton': 1, 'box': 0, 'piece': 10}

### `levels_from_pairs(pairs: 'Iterable[Tuple[str, Any]]') -> 'Tuple[PackagingLevel, ...]'`

Helper: ``[("piece", 1), ("box", 12), ("carton", 20)]`` -> a chain of levels (smallest first).

### `packages_required(product: 'Product', quantity: 'Any', from_level: 'str', to_level: 'str') -> 'Decimal'`

Minimum whole ``to_level`` packages needed to hold ``quantity`` of ``from_level`` (package ceiling).


## Materials and BOM - `atica.materials`

### class `Bom(items: 'Tuple[BomItem, ...]', product_id: 'str' = '', allow_duplicates: 'bool' = False) -> None`

An immutable bill of materials: the materials needed for **one** finished unit.

Material identifiers must be unique (compared ignoring case) unless
``allow_duplicates=True``; in that case lines with the same identifier are
kept as separate lines and also reported combined in ``totals``.

Fields: `items`, `product_id`, `allow_duplicates`

#### `Bom.from_dict(data: 'Mapping[str, Any]') -> 'Bom'`

*(no description)*

#### `Bom.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

### class `BomItem(material_id: 'str', quantity_per_unit: 'Decimal', unit: 'str', wastage_percent: 'Decimal' = Decimal('0'), name: 'str' = '') -> None`

One material line of a bill of materials.

``quantity_per_unit`` is the **net** amount of material in one finished unit,
expressed in ``unit``; ``wastage_percent`` is the extra process loss (see module docs).

Fields: `material_id`, `quantity_per_unit`, `unit`, `wastage_percent`, `name`

### class `BomRequirements(product_id: 'str', production_quantity: 'Decimal', scrap_percent: 'Decimal', lines: 'Tuple[MaterialRequirement, ...]', totals: 'Tuple[MaterialRequirement, ...]', warnings: 'Tuple[str, ...]' = ()) -> None`

Requirements of every material in a BOM for one production quantity.

``lines`` has one entry per BOM line (in BOM order).  ``totals`` has one entry per
distinct material - identical to ``lines`` unless the BOM allows duplicate
identifiers, in which case lines of one material are summed (units converted to
the first line's report unit) and rounded once.

Fields: `product_id`, `production_quantity`, `scrap_percent`, `lines`, `totals`, `warnings`

#### `BomRequirements.by_material(self) -> 'Dict[str, MaterialRequirement]'`

``{material_id: total requirement}``.

### class `MaterialCapacity(material_id: 'str', available: 'Decimal', unit: 'str', required_per_unit: 'Decimal', producible_units: 'Decimal') -> None`

How many good units one material alone could support.

Fields: `material_id`, `available`, `unit`, `required_per_unit`, `producible_units`

### class `MaterialRequirement(material_id: 'str', unit: 'str', production_quantity: 'Decimal', units_started: 'Decimal', base_quantity: 'Decimal', scrap_allowance: 'Decimal', wastage_allowance: 'Decimal', exact_quantity: 'Decimal', quantity: 'Decimal', quantity_per_unit: 'Decimal', per_unit_unit: 'str', scrap_percent: 'Decimal', wastage_percent: 'Decimal', rounding: 'Rounding' = <Rounding.NONE: 'none'>, places: 'int' = 0, formula: 'str' = 'units_started = good / (1 - scrap%); gross = per_unit x units_started / (1 - wastage%)', warnings: 'Tuple[str, ...]' = ()) -> None`

Material needed to make ``production_quantity`` good units.

``exact_quantity == base_quantity + scrap_allowance + wastage_allowance`` (all in ``unit``);
``quantity`` is ``exact_quantity`` after the requested rounding.

Fields: `material_id`, `unit`, `production_quantity`, `units_started`, `base_quantity`, `scrap_allowance`, `wastage_allowance`, `exact_quantity`, `quantity`, `quantity_per_unit`, `per_unit_unit`, `scrap_percent`, `wastage_percent`, `rounding`, `places`, `formula`, `warnings`

### class `ProductionCapacity(producible_quantity: 'Decimal', exact_quantity: 'Decimal', limiting_material: 'str', materials: 'Tuple[MaterialCapacity, ...]', scrap_percent: 'Decimal', rounding: 'Rounding' = <Rounding.FLOOR: 'floor'>, places: 'int' = 0, formula: 'str' = 'min over materials of available x (1 - scrap%) / (sum of per_unit / (1 - wastage%))', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`calculate_producible_quantity`.

``producible_quantity`` is limited by the scarcest material (``limiting_material``).
``exact_quantity`` is the unrounded figure.

Fields: `producible_quantity`, `exact_quantity`, `limiting_material`, `materials`, `scrap_percent`, `rounding`, `places`, `formula`, `warnings`

### `calculate_bom_requirements(bom: 'Bom', production_quantity: 'Any', *, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, report_units: 'Optional[Mapping[str, str]]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'BomRequirements'`

Material requirements of every BOM line for ``production_quantity`` good units.

Each line follows :func:`~atica.materials.calculate_material_requirement` (with the
line's own ``wastage_percent``); ``scrap_percent`` applies to the whole product.

:param report_units: optional ``{material_id: unit}`` to report selected materials in
    another compatible unit (e.g. ``{"steel": "kg"}`` for a BOM written in grams).
:raises IncompatibleUnitError: a report unit measures a different quantity.
:raises InvalidConfigurationError: ``report_units`` names a material that is not in the BOM.

>>> from atica.materials import Bom, BomItem
>>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("paint", "40", "mL")])
>>> r = calculate_bom_requirements(bom, 1000)
>>> str(r["steel"]), str(r["paint"])
('250 kg', '40000 mL')

### `calculate_material_requirement(quantity_per_unit: 'Any', production_quantity: 'Any', unit: 'str', *, wastage_percent: 'Any' = 0, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, report_unit: 'Optional[str]' = None, material_id: 'str' = '', registry: 'Optional[UnitRegistry]' = None) -> 'MaterialRequirement'`

Total quantity of one material needed for ``production_quantity`` good units.

:param quantity_per_unit: net material in one finished unit (``> 0``), measured in ``unit``.
:param production_quantity: good units wanted (``>= 0``).
:param unit: unit of ``quantity_per_unit`` (a registry unit, e.g. ``"kg"``).
:param wastage_percent: 0-100 (<100); share of *issued material* lost in processing.
:param scrap_percent: 0-100 (<100); share of *units started* that are rejected.
:param rounding: rounding of the final figure (default ``'none'``); ``places`` = decimal places.
:param report_unit: express the result in this (compatible) unit instead of ``unit``.
:param registry: registry holding custom units (default: standard units).
:raises IncompatibleUnitError: ``report_unit`` measures a different quantity.

Formula: ``started = good / (1 - scrap/100)``;
``total = quantity_per_unit x started / (1 - wastage/100)``.

>>> str(calculate_material_requirement("0.5", 1000, "kg"))
'500 kg'
>>> str(calculate_material_requirement("0.5", 1000, "kg", report_unit="g"))
'500000 g'

### `calculate_producible_quantity(bom: 'Bom', available: 'Mapping[str, Any]', *, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.FLOOR: 'floor'>, places: 'int' = 0, registry: 'Optional[UnitRegistry]' = None) -> 'ProductionCapacity'`

How many good units can be made from the available materials.

:param available: ``{material_id: quantity}`` (in the BOM line's unit) or
    ``{material_id: (quantity, unit)}`` for any compatible unit.  **Every** BOM
    material must be listed: a missing one is an error, never assumed zero or unlimited.
:param rounding: default ``'floor'`` (whole units you can really finish); use ``'none'`` for the exact figure.

Formula per material: ``producible = available x (1 - scrap/100) / sum(q_i / (1 - wastage_i/100))``
over that material's BOM lines; the answer is the minimum over materials.

>>> from atica.materials import Bom, BomItem
>>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("screws", 4, "piece")])
>>> cap = calculate_producible_quantity(bom, {"steel": (100, "kg"), "screws": 1000})
>>> int(cap.producible_quantity), cap.limiting_material
(250, 'screws')


## Production - `atica.production`

### class `BatchCapacity(full_batches: 'Decimal', leftover_time: 'Decimal', time_unit: 'str', next_batch_fraction: 'Decimal', time_per_batch: 'Decimal', batch_size: 'Optional[Decimal]' = None, quantity: 'Optional[Decimal]' = None, formula: 'str' = 'full = floor(available_time / time_per_batch); leftover = available - full x time_per_batch', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`calculate_batch_capacity`.

``full_batches`` complete batches fit; ``leftover_time`` is what remains (shorter than one
batch) and ``next_batch_fraction`` how much of another batch it covers.  ``quantity`` is
the output of the full batches when a ``batch_size`` was given.

Fields: `full_batches`, `leftover_time`, `time_unit`, `next_batch_fraction`, `time_per_batch`, `batch_size`, `quantity`, `formula`, `warnings`

### class `BatchMaterial(material_id: 'str', unit: 'str', per_full_batch: 'Decimal', partial_batch: 'Decimal', total: 'Decimal', exact_total: 'Decimal') -> None`

One material across a batch plan: per full batch, in the partial batch, and in total.

``total = full_batches x per_full_batch + partial_batch`` using the *rounded* per-batch
quantities (what is actually issued); ``exact_total`` uses the unrounded figures.

Fields: `material_id`, `unit`, `per_full_batch`, `partial_batch`, `total`, `exact_total`

### class `BatchMaterialPlan(batches: 'BatchPlan', per_full_batch: 'BomRequirements', partial_batch: 'Optional[BomRequirements]', materials: 'Tuple[BatchMaterial, ...]') -> None`

Result of :func:`calculate_batch_materials`.

Fields: `batches`, `per_full_batch`, `partial_batch`, `materials`

### class `BatchPlan(quantity: 'Decimal', batch_size: 'Decimal', full_batches: 'Decimal', partial_batch_quantity: 'Decimal', batches_required: 'Decimal', total_capacity: 'Decimal', unused_capacity: 'Decimal', formula: 'str' = 'full = floor(quantity / batch_size); partial = quantity - full x batch_size; required = ceil(quantity / batch_size)', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`calculate_batches`.

* ``full_batches``           - batches that run at full ``batch_size`` (``floor``);
* ``partial_batch_quantity`` - size of the last, partly filled batch (0 if none);
* ``batches_required``       - ``full_batches`` plus one if there is a partial batch (``ceil``);
* ``total_capacity``         - ``batches_required x batch_size``;
* ``unused_capacity``        - ``total_capacity - quantity``.

Fields: `quantity`, `batch_size`, `full_batches`, `partial_batch_quantity`, `batches_required`, `total_capacity`, `unused_capacity`, `formula`, `warnings`

### class `CapacityResult(quantity: 'Decimal', exact_quantity: 'Decimal', available_time: 'Decimal', time_unit: 'str', productive_time: 'Decimal', rate: 'Decimal', rate_per: 'str', efficiency_percent: 'Decimal', rounding: 'Rounding' = <Rounding.NONE: 'none'>, places: 'int' = 0, formula: 'str' = 'quantity = rate x efficiency/100 x max(available_time - setup_time, 0)', assumptions: 'Tuple[str, ...]' = ('constant production rate (no ramp-up, breaks or breakdowns)', 'efficiency scales the nominal rate', 'setup time is added once and is not scaled by efficiency'), warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`production_capacity`: units producible in the available time.

Fields: `quantity`, `exact_quantity`, `available_time`, `time_unit`, `productive_time`, `rate`, `rate_per`, `efficiency_percent`, `rounding`, `places`, `formula`, `assumptions`, `warnings`

### class `ConstrainedQuantity(requested: 'Decimal', quantity: 'Decimal', increase: 'Decimal', adjustments: 'Tuple[str, ...]', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`constrain_production_quantity`; ``adjustments`` names the rules that changed it.

Fields: `requested`, `quantity`, `increase`, `adjustments`, `warnings`

### class `ProductionTime(total_time: 'Decimal', unit: 'str', run_time: 'Decimal', setup_time: 'Decimal', quantity: 'Decimal', rate: 'Decimal', rate_per: 'str', efficiency_percent: 'Decimal', effective_rate: 'Decimal', formula: 'str' = 'run_time = quantity / (rate x efficiency/100); total = setup + run_time', assumptions: 'Tuple[str, ...]' = ('constant production rate (no ramp-up, breaks or breakdowns)', 'efficiency scales the nominal rate', 'setup time is added once and is not scaled by efficiency'), warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`production_time`: ``total_time = setup_time + run_time`` in ``unit``.

Fields: `total_time`, `unit`, `run_time`, `setup_time`, `quantity`, `rate`, `rate_per`, `efficiency_percent`, `effective_rate`, `formula`, `assumptions`, `warnings`

### `calculate_batch_capacity(available_time: 'Any', time_per_batch: 'Any', *, time_unit: 'str' = 'h', batch_size: 'Any' = None, registry: 'Optional[UnitRegistry]' = None) -> 'BatchCapacity'`

Number of complete batches that fit into ``available_time``.

Times are numbers in ``time_unit`` or ``(number, unit)`` pairs (so 8 hours against 45-minute
batches is ``calculate_batch_capacity(8, (45, "min"))``).  ``time_per_batch`` must be > 0.

>>> r = calculate_batch_capacity(8, (45, "min"), batch_size=100)
>>> (int(r.full_batches), int(r.quantity))
(10, 1000)

### `calculate_batch_materials(bom: 'Bom', quantity: 'Any', batch_size: 'Any', *, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, report_units: 'Optional[Mapping[str, str]]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'BatchMaterialPlan'`

Material needed per batch and in total for ``quantity`` units made in batches of ``batch_size``.

Each batch is costed like a small production run (:func:`~atica.materials.calculate_bom_requirements`),
so scrap and wastage apply per batch.  With ``rounding='none'`` the totals equal a single
calculation for the whole quantity; with rounding they can differ by the per-batch rounding,
which is exactly what would be issued.

>>> from atica.materials import Bom, BomItem
>>> bom = Bom([BomItem("resin", "2", "kg")])
>>> plan = calculate_batch_materials(bom, 250, 100)
>>> str(plan.materials[0].total)
'500'

### `calculate_batches(quantity: 'Any', batch_size: 'Any') -> 'BatchPlan'`

Split ``quantity`` into batches of ``batch_size``, keeping the partial batch explicit.

:param quantity: units to make (``>= 0``; fractions allowed).
:param batch_size: capacity of one batch (``> 0``).

>>> plan = calculate_batches(250, 100)
>>> (int(plan.full_batches), int(plan.partial_batch_quantity), int(plan.batches_required))
(2, 50, 3)

### `constrain_production_quantity(requested: 'Any', *, minimum: 'Any' = None, maximum: 'Any' = None, multiple: 'Any' = None, multiple_rounding: 'Any' = <PackageRounding.CEILING: 'package_ceiling'>) -> 'ConstrainedQuantity'`

Adjust a required quantity to production constraints.

Order of rules: (1) a **zero** request stays zero; (2) raise to ``minimum`` run size;
(3) snap to a ``multiple`` (package ceiling by default, or ``'floor'``);
(4) the result must not exceed ``maximum``.

:raises ConstraintError: the adjusted quantity exceeds ``maximum`` or (with package floor)
    falls below ``minimum``.
:raises InvalidConfigurationError: ``minimum`` is larger than ``maximum``.

>>> str(constrain_production_quantity(950, minimum=500, multiple=100).quantity)
'1000'

### `production_capacity(rate: 'Any', available_time: 'Any', *, per: 'str' = 'h', time_unit: 'str' = 'h', efficiency_percent: 'Any' = 100, setup_time: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, registry: 'Optional[UnitRegistry]' = None) -> 'CapacityResult'`

Units that can be produced in ``available_time`` (the inverse of :func:`production_time`).

``available_time`` is a number in ``time_unit`` or a ``(number, unit)`` pair; ``setup_time`` likewise.
If setup consumes all available time the capacity is 0 and a warning is returned.
Use ``rounding='floor'`` for whole finished units.

>>> str(production_capacity(250, (8, "h")).quantity)
'2000'

### `production_time(quantity: 'Any', rate: 'Any', *, per: 'str' = 'h', unit: 'str' = 'h', efficiency_percent: 'Any' = 100, setup_time: 'Any' = 0, setup_unit: 'Optional[str]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'ProductionTime'`

Time needed to produce ``quantity`` at ``rate`` units per ``per``.

:param quantity: units to produce (``>= 0``).
:param rate: nominal units made per ``per`` (``> 0``; zero or negative rates are rejected).
:param per: the time unit of ``rate`` (default hour).
:param unit: unit of the returned time (any time unit; default hour).
:param efficiency_percent: ``(0, 100]``; scales the rate.
:param setup_time: one-off setup, in ``setup_unit`` (default ``per``).
:raises IncompatibleUnitError: ``per``, ``unit`` or ``setup_unit`` is not a time unit.

>>> str(production_time(1000, 250))
'4 h'
>>> str(production_time(1000, 250, unit="min"))
'240 min'


## Quality - `atica.quality`

### class `PercentageResult(percent: 'Decimal', numerator: 'Decimal', denominator: 'Decimal', denominator_meaning: 'str', formula: 'str', warnings: 'Tuple[str, ...]' = ()) -> None`

A percentage together with the numbers and the **denominator** it was computed from.

Fields: `percent`, `numerator`, `denominator`, `denominator_meaning`, `formula`, `warnings`

### class `QualityQuantity(quantity: 'Decimal', exact_quantity: 'Decimal', unit: 'str', scrap_percent: 'Decimal', rounding: 'Rounding', places: 'int', formula: 'str', warnings: 'Tuple[str, ...]' = ()) -> None`

A calculated quantity (``quantity``) with its unrounded value and formula.

Fields: `quantity`, `exact_quantity`, `unit`, `scrap_percent`, `rounding`, `places`, `formula`, `warnings`

### class `RecoveryResult(waste_quantity: 'Decimal', recovered_quantity: 'Decimal', unrecovered_quantity: 'Decimal', recovery_percent: 'Decimal', unit: 'str' = '', formula: 'str' = 'recovered = waste x recovery% / 100', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`calculate_material_recovery` (denominator of ``recovery_percent``: the waste).

Fields: `waste_quantity`, `recovered_quantity`, `unrecovered_quantity`, `recovery_percent`, `unit`, `formula`, `warnings`

### class `ReworkProjection(input_quantity: 'Decimal', good_first_pass: 'Decimal', sent_to_rework: 'Decimal', first_pass_scrap: 'Decimal', recovered_from_rework: 'Decimal', rework_scrap: 'Decimal', final_good: 'Decimal', final_scrap: 'Decimal', first_pass_yield_percent: 'Decimal', final_yield_percent: 'Decimal', scrap_percent: 'Decimal', unit: 'str' = '', formula: 'str' = 'final yield = first-pass yield + rework% x recovery%/100', warnings: 'Tuple[str, ...]' = ()) -> None`

Expected outcome of ``input_quantity`` given first-pass yield, rework and recovery rates.

Values are *expected* (statistical) quantities and may be fractional; they are not rounded
so that ``final_good + final_scrap == input_quantity`` holds exactly.

Fields: `input_quantity`, `good_first_pass`, `sent_to_rework`, `first_pass_scrap`, `recovered_from_rework`, `rework_scrap`, `final_good`, `final_scrap`, `first_pass_yield_percent`, `final_yield_percent`, `scrap_percent`, `unit`, `formula`, `warnings`

### class `WastageResult(material_input: 'Decimal', material_in_output: 'Decimal', gross_wastage: 'Decimal', recovered: 'Decimal', net_wastage: 'Decimal', gross_wastage_percent: 'Decimal', net_wastage_percent: 'Decimal', utilisation_percent: 'Decimal', recovery_percent: 'Optional[Decimal]', unit: 'str' = '', formula: 'str' = 'gross = input - in_output; net = gross - recovered; percentages are of input', warnings: 'Tuple[str, ...]' = ()) -> None`

Result of :func:`calculate_wastage` (see the module docstring for the definitions).

Fields: `material_input`, `material_in_output`, `gross_wastage`, `recovered`, `net_wastage`, `gross_wastage_percent`, `net_wastage_percent`, `utilisation_percent`, `recovery_percent`, `unit`, `formula`, `warnings`

### class `YieldResult(input_quantity: 'Decimal', good_first_pass: 'Decimal', sent_to_rework: 'Decimal', recovered_from_rework: 'Decimal', first_pass_scrap: 'Decimal', rework_scrap: 'Decimal', final_good: 'Decimal', final_scrap: 'Decimal', first_pass_yield_percent: 'Decimal', final_yield_percent: 'Decimal', rework_percent: 'Decimal', scrap_percent: 'Decimal', rework_recovery_percent: 'Optional[Decimal]', unit: 'str' = '', formula: 'str' = 'first-pass yield = good_first_pass / input x 100; final yield = (good_first_pass + recovered) / input x 100', warnings: 'Tuple[str, ...]' = ()) -> None`

Outcome of a production run (see the module docstring for definitions).

Fields: `input_quantity`, `good_first_pass`, `sent_to_rework`, `recovered_from_rework`, `first_pass_scrap`, `rework_scrap`, `final_good`, `final_scrap`, `first_pass_yield_percent`, `final_yield_percent`, `rework_percent`, `scrap_percent`, `rework_recovery_percent`, `unit`, `formula`, `warnings`

### `calculate_expected_output(input_quantity: 'Any', scrap_percent: 'Any', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, unit: 'str' = '') -> 'QualityQuantity'`

Expected good output from ``input_quantity`` started: ``input x (1 - scrap%/100)``.

A 100 % scrap rate is valid and gives zero good output.

>>> str(calculate_expected_output(1000, 5))
'950'

### `calculate_material_recovery(waste_quantity: 'Any', recovery_percent: 'Any', *, unit: 'str' = '') -> 'RecoveryResult'`

Material reclaimed from ``waste_quantity``: ``waste x recovery% / 100``.

>>> str(calculate_material_recovery(200, 40).recovered_quantity)
'80'

### `calculate_required_input(good_output: 'Any', scrap_percent: 'Any', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, unit: 'str' = '') -> 'QualityQuantity'`

Quantity to start to obtain ``good_output`` good units: ``good / (1 - scrap%/100)``.

Use ``rounding='ceiling'`` for whole units that still guarantee the target.

:raises ConstraintError: ``scrap_percent`` is 100 and ``good_output`` is positive (impossible).

>>> str(calculate_required_input(950, 5))
'1000'

### `calculate_rework(input_quantity: 'Any', *, first_pass_yield_percent: 'Any', rework_percent: 'Any' = 0, rework_recovery_percent: 'Any' = 100, unit: 'str' = '') -> 'ReworkProjection'`

Project good output and scrap when part of the failures are reworked.

:param first_pass_yield_percent: % of input that is good first time (denominator: input).
:param rework_percent: % of input sent to rework (denominator: input).
:param rework_recovery_percent: % of the *reworked* units that become good (denominator: reworked units).
:raises InvalidConfigurationError: ``first_pass_yield_percent + rework_percent`` exceeds 100.

Formula: ``final yield = FPY + rework% x recovery% / 100``; scrap is the rest.

>>> p = calculate_rework(1000, first_pass_yield_percent=90, rework_percent=6, rework_recovery_percent=75)
>>> (str(p.final_good), str(p.final_scrap))
('945', '55')

### `calculate_scrap_percentage(input_quantity: 'Any', scrap_quantity: 'Any') -> 'PercentageResult'`

Scrap as a percentage of the quantity started: ``scrap / input x 100``.

:raises ZeroDenominatorError: ``input_quantity`` is 0 (the percentage is undefined).
:raises ValidationError: ``scrap_quantity`` exceeds ``input_quantity``.

>>> str(calculate_scrap_percentage(1000, 50))
'5%'

### `calculate_scrap_quantity(input_quantity: 'Any', scrap_percent: 'Any', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, unit: 'str' = '') -> 'QualityQuantity'`

Scrap expected from ``input_quantity`` started: ``input x scrap% / 100``.

>>> str(calculate_scrap_quantity(1000, 5))
'50'

### `calculate_wastage(material_input: 'Any', material_in_output: 'Any', *, recovered_quantity: 'Any' = None, recovery_percent: 'Any' = None, unit: 'str' = '') -> 'WastageResult'`

Material wastage of a process, optionally net of recovered material.

:param material_input: material consumed (``> 0``).
:param material_in_output: material contained in the good output (``<= material_input``).
:param recovered_quantity: material reclaimed from the waste (absolute), **or**
:param recovery_percent: % of the gross wastage that is reclaimed - give at most one.
:raises ZeroDenominatorError: ``material_input`` is 0.
:raises InvalidConfigurationError: both recovery arguments given.
:raises ValidationError: output exceeds input, or recovery exceeds the waste.

>>> r = calculate_wastage(1000, 920, recovery_percent=25)
>>> (str(r.gross_wastage), str(r.net_wastage), str(r.net_wastage_percent))
('80', '60', '6')

### `calculate_yield(input_quantity: 'Any', good_first_pass: 'Any', *, sent_to_rework: 'Any' = 0, recovered_from_rework: 'Any' = 0, first_pass_scrap: 'Any' = None, unit: 'str' = '') -> 'YieldResult'`

First-pass and final yield of a run.

:param input_quantity: units started (``> 0``; zero would make every percentage undefined).
:param good_first_pass: units that passed inspection the first time.
:param sent_to_rework: units that failed but were sent to rework.
:param recovered_from_rework: of those, units that became good after rework.
:param first_pass_scrap: optional; units scrapped at first inspection.  If given it must equal
    ``input - good_first_pass - sent_to_rework`` (a consistency check); if omitted it is derived.
:raises ZeroDenominatorError: ``input_quantity`` is 0.
:raises ValidationError: the quantities contradict each other.

>>> r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
>>> (str(r.first_pass_yield_percent), str(r.final_yield_percent), str(r.scrap_percent))
('90', '94.5', '5.5')

### `required_input_with_rework(good_output: 'Any', *, first_pass_yield_percent: 'Any', rework_percent: 'Any' = 0, rework_recovery_percent: 'Any' = 100) -> 'Decimal'`

Units to start to obtain ``good_output`` final good units: ``good / final_yield``.

:raises ZeroDenominatorError: the final yield is 0 and ``good_output`` is positive.


## Purchasing - `atica.purchasing`

### class `PurchaseQuantity(order_quantity: 'Decimal', unit: 'str', required_quantity: 'Decimal', stock_deducted: 'Decimal', net_requirement: 'Decimal', surplus: 'Decimal', constraints: 'Tuple[str, ...]', minimum_order_quantity: 'Decimal', order_multiple: 'Optional[Decimal]', received_quantity: 'Decimal', stock_unit: 'str', formula: 'str' = 'net = max(required - stock, 0); order = ceil_to_multiple(max(net, MOQ)); 0 if net = 0', warnings: 'Tuple[str, ...]' = ()) -> None`

Recommended order.

All quantities except ``received_quantity`` are in ``unit`` (the *purchase* unit);
``received_quantity`` is what arrives in ``stock_unit``.  ``constraints`` lists which rules
raised the quantity (``'minimum_order_quantity'``, ``'order_multiple'``).
``surplus = order_quantity - net_requirement`` (>= 0).

Fields: `order_quantity`, `unit`, `required_quantity`, `stock_deducted`, `net_requirement`, `surplus`, `constraints`, `minimum_order_quantity`, `order_multiple`, `received_quantity`, `stock_unit`, `formula`, `warnings`

### `calculate_purchase_quantity(required_quantity: 'Any', *, unit: 'str' = '', stock_on_hand: 'Any' = 0, minimum_order_quantity: 'Any' = 0, order_multiple: 'Any' = None, purchase_unit: 'Optional[str]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'PurchaseQuantity'`

How much to order to cover ``required_quantity``.

Steps (all exact):

1. ``net = max(required - stock_on_hand, 0)``; if ``net`` is 0 nothing is ordered (the minimum
   order quantity is **not** forced on an order you do not need);
2. raise to ``minimum_order_quantity`` if lower;
3. round **up** to a multiple of ``order_multiple`` (package ceiling).

:param required_quantity: needed amount (``>= 0``) in ``unit``.
:param unit: unit of ``required_quantity`` and ``stock_on_hand`` (a registry unit when
    ``purchase_unit`` is used, otherwise just a label).
:param stock_on_hand: available stock in ``unit`` (``>= 0``).
:param minimum_order_quantity: supplier minimum, in the **purchase unit** (default 0 = none).
:param order_multiple: orders must be a multiple of this, in the purchase unit (``None`` = any
    amount; pass ``1`` for indivisible units such as bags).
:param purchase_unit: the unit you buy in, e.g. a custom ``"bag"`` registered as 25 kg.  Must
    be convertible from ``unit``; omit to buy in ``unit``.
:param registry: registry with custom units.

>>> r = calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12)
>>> str(r)
'96 piece'


## Core - `atica.core`

### class `AticaError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Base class of every error raised by ATICA.

#### `AticaError.to_dict(self) -> 'Dict[str, Any]'`

Plain-data form, handy for APIs and logs.

### class `CalculationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Valid inputs for which the requested calculation has no valid answer.

### class `ConstraintError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Requested constraints (minimum, maximum, multiples ...) cannot be satisfied together.

### class `DuplicateMaterialError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

The same material identifier appears more than once where that is not allowed.

### class `IncompatibleUnitError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Units measure different kinds of quantity and cannot be converted.

### class `IntegrationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A file could not be read, written or understood.

### class `InvalidConfigurationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A combination of arguments or a configuration object is not usable.

### class `InvalidHierarchyError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A packaging hierarchy is inconsistent, circular, disconnected or duplicated.

### class `InvalidPercentageError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A percentage is outside its permitted range.

### class `InvalidQuantityError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A quantity is not a finite number, or is negative/zero where that is not allowed.

### class `InvalidRoundingError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

An unknown rounding policy, or an inconsistent rounding configuration.

### class `MaterialError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Base class for BOM / material problems.

### class `MissingDependencyError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

An optional dependency required by an integration is not installed.

### class `MissingInputError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A required input was not supplied.

### class `MultipleSplit(value: 'Decimal', multiple: 'Decimal', packages: 'Decimal', remainder: 'Decimal') -> None`

``value == packages * multiple + remainder`` with ``0 <= remainder < multiple``.

Fields: `value`, `multiple`, `packages`, `remainder`

### class `NumericRangeError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A number is outside the range ATICA can represent safely.

### class `PackageRounding(*values)`

Direction for snapping a quantity to a multiple of a package size.

### class `PackagingError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Base class for packaging problems.

### class `Result() -> None`

Base class for all calculation results.

#### `Result.explain(self) -> 'str'`

Readable multi-line summary of every field.

#### `Result.to_dict(self, *, numbers: 'str' = 'decimal') -> 'Dict[str, Any]'`

Plain-data form.

``numbers`` is ``'decimal'`` (default, lossless), ``'str'`` (JSON-safe, lossless)
or ``'float'`` (convenient, may lose precision).

### class `Rounding(*values)`

Mathematical rounding policy.

### class `UnitDefinitionError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A custom unit definition is invalid.

### class `UnitError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Base class for unit problems.

### class `UnknownPackagingLevelError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A packaging level name is not part of the product's hierarchy.

### class `UnknownUnitError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A unit name is not defined in the registry.

### class `UnsupportedOperationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

The operation is not supported for these inputs (for example, offset units in a BOM).

### class `ValidationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

An input value is missing, malformed or outside its allowed range.

### class `ZeroDenominatorError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

A ratio or percentage would divide by zero.

### `format_duration(value: 'Any', unit: 'str' = 'h', registry: 'Optional[Any]' = None) -> 'str'`

Write ``value`` (a non-negative number of ``unit``) as days, hours, minutes and seconds.

Zero-valued units are left out, labels are singular/plural, and the value is rounded to the
nearest whole second.  A positive duration under half a second reads ``less than 1 second``.

>>> format_duration("1.5", "h")
'1 hour 30 minutes'
>>> format_duration(90, "min")
'1 hour 30 minutes'
>>> format_duration(0)
'0 seconds'

### `get_precision() -> 'int'`

Return the number of significant digits used for inexact results.

### `round_to_multiple(value: 'Any', multiple: 'Any', mode: 'Union[PackageRounding, str]' = <PackageRounding.CEILING: 'package_ceiling'>) -> 'Decimal'`

Snap ``value`` to a multiple of ``multiple`` (package ceiling or package floor).

>>> str(round_to_multiple(250, 240))   # package ceiling: 2 packages of 240
'480'
>>> str(round_to_multiple(250, 240, "floor"))
'240'

### `round_value(value: 'Any', rounding: 'Union[Rounding, str, None]' = <Rounding.HALF_UP: 'half_up'>, places: 'int' = 0) -> 'Decimal'`

Round ``value`` to ``places`` decimal places using ``rounding``.

>>> from atica.core import round_value
>>> str(round_value("2.675", "half_up", 2))
'2.68'
>>> str(round_value("2.5", "half_even"))
'2'

### `split_by_multiple(value: 'Any', multiple: 'Any') -> 'MultipleSplit'`

Remainder preservation: whole packages *and* what is left over (nothing is discarded).

>>> s = split_by_multiple(250, 240)
>>> (str(s.packages), str(s.remainder))
('1', '10')

### `to_decimal(value: 'Any', name: 'str' = 'value') -> 'Decimal'`

Convert ``value`` to a finite :class:`~decimal.Decimal`, or raise.

Accepts ``int``, ``Decimal``, ``Fraction``, numeric ``str`` and ``float``.
A float is converted through ``repr`` (so ``0.1`` is ``Decimal('0.1')``, not
its binary expansion) - pass strings or Decimals when you need exactness
beyond what a float carries.  ``bool``, ``None``, NaN and infinities are
rejected, as are magnitudes beyond about ``1e300``.

### `use_precision(digits: 'int') -> 'Iterator[int]'`

Temporarily set the precision (significant digits) for ATICA calculations.

>>> from atica.core import use_precision
>>> with use_precision(10):
...     pass


## Integrations (CSV) - `atica.integrations.csv`

### `read_csv(path: 'Any', *, max_rows: 'int' = 100000) -> 'Tuple[List[str], List[Row], List[int]]'`

Read a CSV file -> ``(fieldnames, rows, row_numbers)``; blank lines are skipped.

:raises IntegrationError: missing/oversized/unsupported file, no header, duplicate or ragged columns.

### `write_csv(path: 'Any', fieldnames: 'Sequence[str]', rows: 'Sequence[Dict[str, Any]]', *, overwrite: 'bool' = False) -> 'str'`

Write ``rows`` to ``path`` and return the path.

### `convert_csv(path: 'Any', *, output_path: 'Optional[Any]' = None, overwrite: 'bool' = False, registry: 'Optional[UnitRegistry]' = None, **options: 'Any') -> 'ConversionReport'`

Convert every row of a CSV (columns ``value``, ``from_unit``, ``to_unit``) with :func:`atica.units.convert`.

``options`` are ``value_column``, ``from_column``, ``to_column``, ``rounding`` and ``places``.
If ``output_path`` is given the converted rows are written there.

### `read_bom_csv(path: 'Any', *, product_id: 'str' = '', allow_duplicates: 'bool' = False) -> 'Bom'`

Load a BOM from a CSV with columns ``material_id, quantity_per_unit, unit`` (+ optional ``wastage_percent``, ``name``).


## Integrations (Excel, optional) - `atica.integrations.excel`

### `read_xlsx(path: 'Any', *, sheet: 'Optional[str]' = None, max_rows: 'int' = 100000) -> 'Tuple[List[str], List[Row], List[int]]'`

Read the first (or named) sheet -> ``(fieldnames, rows, row_numbers)``; the first non-empty row is the header.

### `write_xlsx(path: 'Any', fieldnames: 'Sequence[str]', rows: 'Sequence[Dict[str, Any]]', *, overwrite: 'bool' = False, sheet_name: 'str' = 'Results') -> 'str'`

Write ``rows`` to an .xlsx file and return the path.

### `convert_xlsx(path: 'Any', *, sheet: 'Optional[str]' = None, output_path: 'Optional[Any]' = None, overwrite: 'bool' = False, registry: 'Optional[UnitRegistry]' = None, **options: 'Any') -> 'ConversionReport'`

Like :func:`atica.integrations.csv.convert_csv` for an Excel sheet.

### `read_bom_xlsx(path: 'Any', *, sheet: 'Optional[str]' = None, product_id: 'str' = '', allow_duplicates: 'bool' = False) -> 'Bom'`

Load a BOM from a sheet (see :func:`atica.integrations.csv.read_bom_csv` for the columns).


## Integrations (shared) - `atica.integrations`

### class `ConversionReport(fieldnames: 'Tuple[str, ...]', rows: 'Tuple[Row, ...]', errors: 'Tuple[RowError, ...]' = (), total_rows: 'int' = 0, row_numbers: 'Tuple[int, ...]' = ()) -> None`

Outcome of converting many rows: converted rows (original columns + result columns) and errors.

``row_numbers[i]`` is the position **in the source file** (CSV line / Excel row) of ``rows[i]``;
every :class:`RowError` carries its source row number too.

Fields: `fieldnames`, `rows`, `errors`, `total_rows`, `row_numbers`

### class `RowError(row_number: 'int', message: 'str', code: 'str' = '', hint: 'Optional[str]' = None) -> None`

A problem found in one row (``row_number`` is the position in the source file).

Fields: `row_number`, `message`, `code`, `hint`

### `bom_from_rows(rows: 'Sequence[Mapping[str, Any]]', *, product_id: 'str' = '', allow_duplicates: 'bool' = False, row_numbers: 'Optional[Sequence[int]]' = None) -> 'Bom'`

Build a :class:`~atica.materials.Bom` from rows with ``material_id, quantity_per_unit, unit``
(optional ``wastage_percent`` and ``name``).

Nothing is returned unless every row is valid.  Otherwise one :class:`IntegrationError` reports **all**
invalid rows and columns (also available as ``error.errors``, a tuple of :class:`RowError`).

### `convert_rows(rows: 'Sequence[Mapping[str, Any]]', *, value_column: 'str' = 'value', from_column: 'str' = 'from_unit', to_column: 'str' = 'to_unit', rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, registry: 'Optional[UnitRegistry]' = None, row_numbers: 'Optional[Sequence[int]]' = None) -> 'ConversionReport'`

Convert every row with :func:`atica.units.convert`; rows that fail are reported, not skipped silently.

A missing *column* is a whole-input failure (:class:`IntegrationError`); a bad *value in a row*
is reported for that row only.


## Top-level shortcuts - `atica`

### class `AticaError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

Base class of every error raised by ATICA.

#### `AticaError.to_dict(self) -> 'Dict[str, Any]'`

Plain-data form, handy for APIs and logs.

### class `Bom(items: 'Tuple[BomItem, ...]', product_id: 'str' = '', allow_duplicates: 'bool' = False) -> None`

An immutable bill of materials: the materials needed for **one** finished unit.

Material identifiers must be unique (compared ignoring case) unless
``allow_duplicates=True``; in that case lines with the same identifier are
kept as separate lines and also reported combined in ``totals``.

Fields: `items`, `product_id`, `allow_duplicates`

#### `Bom.from_dict(data: 'Mapping[str, Any]') -> 'Bom'`

*(no description)*

#### `Bom.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

### class `BomItem(material_id: 'str', quantity_per_unit: 'Decimal', unit: 'str', wastage_percent: 'Decimal' = Decimal('0'), name: 'str' = '') -> None`

One material line of a bill of materials.

``quantity_per_unit`` is the **net** amount of material in one finished unit,
expressed in ``unit``; ``wastage_percent`` is the extra process loss (see module docs).

Fields: `material_id`, `quantity_per_unit`, `unit`, `wastage_percent`, `name`

### class `PackagingLevel(name: 'str', contains: 'Decimal' = Decimal('1'), of: 'Optional[str]' = None) -> None`

One level of a packaging hierarchy (see the module docstring for the direction).

Fields: `name`, `contains`, `of`

#### `PackagingLevel.from_dict(data: 'Mapping[str, Any]') -> 'PackagingLevel'`

*(no description)*

#### `PackagingLevel.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

### class `Product(product_id: 'str', name: 'str' = '', levels: 'Tuple[PackagingLevel, ...]' = ()) -> None`

A product and its (immutable) packaging hierarchy.

The hierarchy is validated on construction, so a ``Product`` is always consistent.
"Modifying" a product returns a new one (:meth:`with_level`, :meth:`without_top_level`);
the original is never changed.

>>> p = Product("P001", "Product A", levels=[
...     PackagingLevel("piece"), PackagingLevel("box", 12, "piece"), PackagingLevel("carton", 20, "box")])
>>> p.size_of("carton")
Decimal('240')

Fields: `product_id`, `name`, `levels`

#### `Product.from_dict(data: 'Mapping[str, Any]') -> 'Product'`

*(no description)*

#### `Product.has_level(self, name: 'str') -> 'bool'`

*(no description)*

#### `Product.level(self, name: 'str') -> 'PackagingLevel'`

The level called ``name`` (case-insensitive).

#### `Product.size_of(self, name: 'str') -> 'Decimal'`

How many base units (e.g. pieces) one ``name`` holds.

#### `Product.to_dict(self) -> 'Dict[str, Any]'`

*(no description)*

#### `Product.units_per(self, larger: 'str', smaller: 'str') -> 'Decimal'`

How many ``smaller`` units make one ``larger`` (a fraction if ``larger`` is the smaller one).

#### `Product.with_level(self, level: 'PackagingLevel') -> 'Product'`

A new product with ``level`` added (this product is unchanged).

#### `Product.without_top_level(self) -> 'Product'`

A new product without its largest level.

### class `Rounding(*values)`

Mathematical rounding policy.

### class `UnitRegistry(*, include_standard: 'bool' = True) -> 'None'`

A set of units. Registries are independent of one another.

``UnitRegistry()`` contains every standard unit and may be extended with
:meth:`register_unit`; a *frozen* registry (such as the shared default one) rejects changes.

#### `UnitRegistry.are_compatible(self, unit_a: 'str', unit_b: 'str') -> 'bool'`

True when both units measure the same kind of quantity.

#### `UnitRegistry.base_unit(self, category: 'str') -> 'str'`

Symbol of the base unit of ``category``.

#### `UnitRegistry.categories(self) -> 'Tuple[str, ...]'`

Names of all measurement categories.

#### `UnitRegistry.convert(self, value: 'Any', from_unit: 'str', to_unit: 'str', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, interval: 'bool' = False) -> 'Conversion'`

Convert ``value`` from ``from_unit`` to ``to_unit`` (see :func:`atica.units.convert`).

#### `UnitRegistry.copy(self) -> 'UnitRegistry'`

An independent, writable copy.

#### `UnitRegistry.custom_units(self) -> 'Tuple[Unit, ...]'`

User-defined units, in registration order.

#### `UnitRegistry.factor(self, from_unit: 'str', to_unit: 'str') -> 'Fraction'`

Exact multiplier ``m`` with ``value_in_to_unit = value_in_from_unit * m``.

Only defined for ordinary (non-offset) units; raises
:class:`~atica.core.exceptions.UnsupportedOperationError` for Celsius/Fahrenheit.

#### `UnitRegistry.freeze(self) -> 'UnitRegistry'`

Make this registry read-only (irreversible; use :meth:`copy` for a writable one).

#### `UnitRegistry.from_dict(data: 'Mapping[str, Any]') -> 'UnitRegistry'`

Rebuild a registry written by :meth:`to_dict` (all-or-nothing).

#### `UnitRegistry.get(self, name: 'str') -> 'Unit'`

Return the unit called ``name`` (symbol or alias, case-sensitive).

#### `UnitRegistry.register_base_unit(self, name: 'str', category: 'str', *, aliases: 'Iterable[str]' = ()) -> 'Unit'`

Create a brand-new measurement category with its base unit (e.g. ``'sheet'``, ``'sheets'``).

Further units of that category are then added with :meth:`register_unit`.

#### `UnitRegistry.register_unit(self, name: 'str', factor: 'Any', reference_unit: 'str', *, aliases: 'Iterable[str]' = (), display_name: 'Optional[str]' = None) -> 'Unit'`

Define ``1 <name> = <factor> <reference_unit>``.

>>> reg = UnitRegistry()
>>> _ = reg.register_unit("bag", 25, "kg")
>>> str(reg.convert(4, "bag", "kg"))
'100 kg'

The new unit belongs to the reference unit's category.  Offset scales
(Celsius, Fahrenheit) cannot be used as a reference.  Existing names can
never be redefined, which also makes circular definitions impossible.

#### `UnitRegistry.to_dict(self) -> 'Dict[str, Any]'`

JSON-friendly description of the custom units/categories (built-ins are implicit).

#### `UnitRegistry.units(self, category: 'Optional[str]' = None) -> 'Tuple[Unit, ...]'`

All units, optionally only those of one ``category``.

#### `UnitRegistry.unregister_unit(self, name: 'str') -> 'None'`

Remove a custom unit (not allowed for built-in units or units others are defined from).

### class `ValidationError(message: 'str', *, parameter: 'Optional[str]' = None, hint: 'Optional[str]' = None) -> 'None'`

An input value is missing, malformed or outside its allowed range.

### `breakdown(product: 'Product', quantity: 'Any', from_level: 'str', to_level: 'str', *, require_whole: 'bool' = False) -> 'PackagingBreakdown'`

Break ``quantity`` of ``from_level`` into ``to_level`` packages.

:param product: the :class:`Product` that defines the hierarchy.
:param quantity: non-negative amount of ``from_level`` units (fractions allowed).
:param from_level: level the quantity is measured in, e.g. ``"piece"``.
:param to_level: level to pack into, e.g. ``"carton"`` (may be larger or smaller).
:param require_whole: reject fractional quantities.
:returns: :class:`PackagingBreakdown`.
:raises UnknownPackagingLevelError: a level is not in the product.
:raises InvalidQuantityError: negative / non-numeric / (with ``require_whole``) fractional quantity.

With 1 carton = 20 boxes = 240 pieces, 250 pieces give ``full_packages=1``,
``remainder=10 piece`` and ``packages_required=2``.

>>> from atica.packaging import PackagingLevel, Product
>>> p = Product("P", "A", levels=[PackagingLevel("piece"), PackagingLevel("box", 12, "piece"),
...                               PackagingLevel("carton", 20, "box")])
>>> r = breakdown(p, 250, "piece", "carton")
>>> (int(r.full_packages), int(r.remainder), int(r.packages_required))
(1, 10, 2)

### `calculate_batches(quantity: 'Any', batch_size: 'Any') -> 'BatchPlan'`

Split ``quantity`` into batches of ``batch_size``, keeping the partial batch explicit.

:param quantity: units to make (``>= 0``; fractions allowed).
:param batch_size: capacity of one batch (``> 0``).

>>> plan = calculate_batches(250, 100)
>>> (int(plan.full_batches), int(plan.partial_batch_quantity), int(plan.batches_required))
(2, 50, 3)

### `calculate_bom_requirements(bom: 'Bom', production_quantity: 'Any', *, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, report_units: 'Optional[Mapping[str, str]]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'BomRequirements'`

Material requirements of every BOM line for ``production_quantity`` good units.

Each line follows :func:`~atica.materials.calculate_material_requirement` (with the
line's own ``wastage_percent``); ``scrap_percent`` applies to the whole product.

:param report_units: optional ``{material_id: unit}`` to report selected materials in
    another compatible unit (e.g. ``{"steel": "kg"}`` for a BOM written in grams).
:raises IncompatibleUnitError: a report unit measures a different quantity.
:raises InvalidConfigurationError: ``report_units`` names a material that is not in the BOM.

>>> from atica.materials import Bom, BomItem
>>> bom = Bom([BomItem("steel", "0.25", "kg"), BomItem("paint", "40", "mL")])
>>> r = calculate_bom_requirements(bom, 1000)
>>> str(r["steel"]), str(r["paint"])
('250 kg', '40000 mL')

### `calculate_material_requirement(quantity_per_unit: 'Any', production_quantity: 'Any', unit: 'str', *, wastage_percent: 'Any' = 0, scrap_percent: 'Any' = 0, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, report_unit: 'Optional[str]' = None, material_id: 'str' = '', registry: 'Optional[UnitRegistry]' = None) -> 'MaterialRequirement'`

Total quantity of one material needed for ``production_quantity`` good units.

:param quantity_per_unit: net material in one finished unit (``> 0``), measured in ``unit``.
:param production_quantity: good units wanted (``>= 0``).
:param unit: unit of ``quantity_per_unit`` (a registry unit, e.g. ``"kg"``).
:param wastage_percent: 0-100 (<100); share of *issued material* lost in processing.
:param scrap_percent: 0-100 (<100); share of *units started* that are rejected.
:param rounding: rounding of the final figure (default ``'none'``); ``places`` = decimal places.
:param report_unit: express the result in this (compatible) unit instead of ``unit``.
:param registry: registry holding custom units (default: standard units).
:raises IncompatibleUnitError: ``report_unit`` measures a different quantity.

Formula: ``started = good / (1 - scrap/100)``;
``total = quantity_per_unit x started / (1 - wastage/100)``.

>>> str(calculate_material_requirement("0.5", 1000, "kg"))
'500 kg'
>>> str(calculate_material_requirement("0.5", 1000, "kg", report_unit="g"))
'500000 g'

### `calculate_purchase_quantity(required_quantity: 'Any', *, unit: 'str' = '', stock_on_hand: 'Any' = 0, minimum_order_quantity: 'Any' = 0, order_multiple: 'Any' = None, purchase_unit: 'Optional[str]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'PurchaseQuantity'`

How much to order to cover ``required_quantity``.

Steps (all exact):

1. ``net = max(required - stock_on_hand, 0)``; if ``net`` is 0 nothing is ordered (the minimum
   order quantity is **not** forced on an order you do not need);
2. raise to ``minimum_order_quantity`` if lower;
3. round **up** to a multiple of ``order_multiple`` (package ceiling).

:param required_quantity: needed amount (``>= 0``) in ``unit``.
:param unit: unit of ``required_quantity`` and ``stock_on_hand`` (a registry unit when
    ``purchase_unit`` is used, otherwise just a label).
:param stock_on_hand: available stock in ``unit`` (``>= 0``).
:param minimum_order_quantity: supplier minimum, in the **purchase unit** (default 0 = none).
:param order_multiple: orders must be a multiple of this, in the purchase unit (``None`` = any
    amount; pass ``1`` for indivisible units such as bags).
:param purchase_unit: the unit you buy in, e.g. a custom ``"bag"`` registered as 25 kg.  Must
    be convertible from ``unit``; omit to buy in ``unit``.
:param registry: registry with custom units.

>>> r = calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12)
>>> str(r)
'96 piece'

### `calculate_required_input(good_output: 'Any', scrap_percent: 'Any', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, unit: 'str' = '') -> 'QualityQuantity'`

Quantity to start to obtain ``good_output`` good units: ``good / (1 - scrap%/100)``.

Use ``rounding='ceiling'`` for whole units that still guarantee the target.

:raises ConstraintError: ``scrap_percent`` is 100 and ``good_output`` is positive (impossible).

>>> str(calculate_required_input(950, 5))
'1000'

### `calculate_yield(input_quantity: 'Any', good_first_pass: 'Any', *, sent_to_rework: 'Any' = 0, recovered_from_rework: 'Any' = 0, first_pass_scrap: 'Any' = None, unit: 'str' = '') -> 'YieldResult'`

First-pass and final yield of a run.

:param input_quantity: units started (``> 0``; zero would make every percentage undefined).
:param good_first_pass: units that passed inspection the first time.
:param sent_to_rework: units that failed but were sent to rework.
:param recovered_from_rework: of those, units that became good after rework.
:param first_pass_scrap: optional; units scrapped at first inspection.  If given it must equal
    ``input - good_first_pass - sent_to_rework`` (a consistency check); if omitted it is derived.
:raises ZeroDenominatorError: ``input_quantity`` is 0.
:raises ValidationError: the quantities contradict each other.

>>> r = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
>>> (str(r.first_pass_yield_percent), str(r.final_yield_percent), str(r.scrap_percent))
('90', '94.5', '5.5')

### `convert(value: 'Any', from_unit: 'str', to_unit: 'str', *, rounding: 'Any' = <Rounding.NONE: 'none'>, places: 'int' = 0, interval: 'bool' = False, registry: 'Optional[UnitRegistry]' = None) -> 'Conversion'`

Convert ``value`` from ``from_unit`` to ``to_unit``.

:param value: the amount (int, Decimal, numeric string or float; see
    :func:`atica.core.precision.to_decimal`).
:param from_unit: source unit symbol or alias (case-sensitive), e.g. ``"kg"``.
:param to_unit: target unit; must measure the same kind of quantity.
:param rounding: ``'none'`` (default; exact up to the library precision),
    ``'half_up'``, ``'half_even'``, ``'floor'`` or ``'ceiling'``.
:param places: decimal places for the rounding (requires a rounding policy).
:param interval: treat a temperature as a *difference* (no offsets), e.g. +-5 C in F.
:param registry: a :class:`UnitRegistry` with custom units (default: standard units).
:returns: :class:`Conversion` (``.value``, ``.unit``, ``.exact_value`` ...).
:raises UnknownUnitError: a unit is not defined.
:raises IncompatibleUnitError: the units measure different things.
:raises InvalidQuantityError: invalid number, or a temperature below absolute zero.

Formula: ``target = ((value + offset_src) * factor_src) / factor_dst - offset_dst``
(offsets are zero except for Celsius/Fahrenheit).  Computed exactly, rounded once.

>>> str(convert("212", "F", "C"))
'100 C'

### `get_precision() -> 'int'`

Return the number of significant digits used for inexact results.

### `production_time(quantity: 'Any', rate: 'Any', *, per: 'str' = 'h', unit: 'str' = 'h', efficiency_percent: 'Any' = 100, setup_time: 'Any' = 0, setup_unit: 'Optional[str]' = None, registry: 'Optional[UnitRegistry]' = None) -> 'ProductionTime'`

Time needed to produce ``quantity`` at ``rate`` units per ``per``.

:param quantity: units to produce (``>= 0``).
:param rate: nominal units made per ``per`` (``> 0``; zero or negative rates are rejected).
:param per: the time unit of ``rate`` (default hour).
:param unit: unit of the returned time (any time unit; default hour).
:param efficiency_percent: ``(0, 100]``; scales the rate.
:param setup_time: one-off setup, in ``setup_unit`` (default ``per``).
:raises IncompatibleUnitError: ``per``, ``unit`` or ``setup_unit`` is not a time unit.

>>> str(production_time(1000, 250))
'4 h'
>>> str(production_time(1000, 250, unit="min"))
'240 min'

### `use_precision(digits: 'int') -> 'Iterator[int]'`

Temporarily set the precision (significant digits) for ATICA calculations.

>>> from atica.core import use_precision
>>> with use_precision(10):
...     pass

