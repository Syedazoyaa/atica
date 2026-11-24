# Packaging - `atica.packaging`

Multi-level packaging hierarchies and exact quantity conversion between levels.

```python
from atica.packaging import Product, PackagingLevel, breakdown, decompose

product = Product(
    "P001",
    "Product A",
    levels=[
        PackagingLevel("piece"),
        PackagingLevel("box", 12, "piece"),  # 1 box    = 12 pieces
        PackagingLevel("carton", 20, "box"),  # 1 carton = 20 boxes  (= 240 pieces)
    ],
)

r = breakdown(product, 250, "piece", "carton")
print(r.full_packages)  # 1     complete cartons
print(r.remainder)  # 10    pieces left over (r.remainder_unit == "piece")
print(r.packages_required)  # 2     minimum whole cartons to hold all 250

print(
    {k: int(v) for k, v in decompose(product, 250).by_level().items()}
)  # {'carton': 1, 'box': 0, 'piece': 10}
```

## `PackagingLevel(name, contains=1, of=None)`

"One `name` contains `contains` units of the level `of`." The base (smallest) level has no `of` and contains exactly 1. `contains` must be a **positive whole number** (a box cannot hold 12.5 pieces). Names are matched ignoring case and surrounding spaces.

## `Product(product_id, name="", levels=())`

Immutable and **validated on construction**, so a `Product` is always consistent. It rejects: duplicate names, no base level, several base levels, a missing referenced level, self-reference, circular chains, branching (two levels built from the same level) - each with `InvalidHierarchyError` and a hint.

Level order in the list does not matter. Calculations never modify a product; "changing" one returns a new product:

| Member | Purpose |
|---|---|
| `level_names`, `levels`, `base_level` | levels, smallest first |
| `level(name)`, `has_level(name)` | lookup (`UnknownPackagingLevelError` lists the available names) |
| `size_of(level) -> Decimal` | base units in one `level` (carton -> 240) |
| `units_per(larger, smaller) -> Decimal` | e.g. `units_per("carton", "box") == 20`; reversed gives `0.05` |
| `with_level(level)`, `without_top_level()` | new products; the original is untouched |
| `to_dict()`, `Product.from_dict(data)` | plain-data round trip |

## `breakdown(product, quantity, from_level, to_level, *, require_whole=False) -> PackagingBreakdown`

| Parameter | Meaning |
|---|---|
| `quantity` | non-negative amount counted in `from_level` units (fractions allowed unless `require_whole=True`) |
| `from_level`, `to_level` | level names (to_level may be larger *or* smaller) |

Result fields:

| Field | Meaning |
|---|---|
| `exact_packages` | exact conversion (a ratio, may be fractional) |
| `full_packages` | complete `to_level` packages: `floor(exact)` |
| `remainder`, `remainder_unit` | what is left after the full packages, in the **smaller** of the two levels (250 piece -> carton leaves `10 piece`; 2.33 carton -> box leaves `0.6 box`) |
| `packages_required` | minimum whole packages to hold **everything**: `ceil(exact)` |
| `packaged_quantity`, `surplus` | quantity those required packages cover and the unused part, in `from_level` units |
| `units_per_package` | `from_level` units per `to_level` package |

**Formulas** `exact = quantity x size(from) / size(to)`; `full = floor(exact)`; `required = ceil(exact)`; going up: `remainder = quantity - full x size(to)/size(from)`; going down: `remainder = exact - full`.

Exact vs whole-package: `exact_packages` is the mathematical conversion; `full_packages` and `packages_required` are the two whole-package answers (round down / round up). Nothing is discarded: the remainder is always reported. All arithmetic is exact, so `240 pieces` is exactly `1` carton - never `0.99999`.

**Raises** `UnknownPackagingLevelError`, `InvalidHierarchyError` (product has no levels), `InvalidQuantityError` (negative, non-numeric, fractional with `require_whole`), `MissingInputError`.

## Other functions

* `convert_quantity(product, quantity, from_level, to_level) -> Decimal` - the exact equivalent only (`850 carton -> 21.25 pallet`).
* `packages_required(product, quantity, from_level, to_level) -> Decimal` - just the minimum whole packages.
* `decompose(product, quantity, from_level="") -> PackagingPlan` - the quantity as whole packages at **every** level, largest first; `remainder` is what is left in the base unit and may be fractional. `by_level()` gives `{level: count}`. Invariant: `sum(count x size(level)) + remainder == quantity` (in base units).
* `levels_from_pairs([("piece", 1), ("box", 12), ("carton", 20)])` - build levels from `(name, count)` pairs, smallest first.
