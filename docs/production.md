# Production - `atica.production`

Straight calculations - **no scheduling, no machine or shift modelling**.

```python
from atica.production import calculate_batches, production_time

plan = calculate_batches(250, 100)
print(plan.full_batches, plan.partial_batch_quantity, plan.batches_required)  # 2 50 3
print(production_time(1000, 250, efficiency_percent=80, setup_time=(30, "min")))  # 5.5 h
```

## `calculate_batches(quantity, batch_size) -> BatchPlan`

`quantity >= 0`, `batch_size > 0` (zero/negative raise `InvalidQuantityError`).

| Field | Formula |
|---|---|
| `full_batches` | `floor(quantity / batch_size)` - batches that run at full capacity |
| `partial_batch_quantity` | `quantity - full x batch_size` |
| `batches_required` | `full + (1 if partial > 0)` = `ceil(quantity / batch_size)` |
| `total_capacity` | `batches_required x batch_size` |
| `unused_capacity` | `total_capacity - quantity` |

"Required batches" and "full-capacity batches" are different numbers whenever there is a partial batch. Exact arithmetic: `1 / 0.1` is exactly 10 batches.

## `calculate_batch_materials(bom, quantity, batch_size, *, scrap_percent=0, rounding="none", places=0, report_units=None, registry=None) -> BatchMaterialPlan`

Materials for one full batch, for the partial batch, and in total. Each batch is costed like a small production run, so scrap/wastage apply per batch. `total = full_batches x per_full_batch + partial_batch` using the **rounded** per-batch figures (what is actually issued); `exact_total` uses the unrounded ones. With `rounding="none"` the totals equal one calculation for the whole quantity.

## `constrain_production_quantity(requested, *, minimum=None, maximum=None, multiple=None, multiple_rounding="ceiling") -> ConstrainedQuantity`

Rules, in order: (1) a **zero** request stays zero; (2) raise to `minimum`; (3) snap to a `multiple` (ceiling by default or `"floor"`); (4) the result must not exceed `maximum`. `adjustments` lists the rules that changed the quantity. Raises `ConstraintError` if the result exceeds `maximum` (or falls below `minimum` after a floor), `InvalidConfigurationError` if `minimum > maximum`.

## `production_time(quantity, rate, *, per="h", unit="h", efficiency_percent=100, setup_time=0, setup_unit=None, registry=None) -> ProductionTime`

**Formula** `run_time = quantity / (rate x efficiency/100)`; `total = setup_time + run_time`; converted to `unit` exactly.

**Assumptions** (also in `result.assumptions`): constant rate - no ramp-up, breaks or breakdowns; efficiency scales the nominal rate; setup is added once and is not scaled by efficiency. `rate` must be `> 0` and `efficiency_percent` in `(0, 100]`; `per`, `unit`, `setup_unit` must be **time** units (`IncompatibleUnitError` otherwise). `setup_time` is a number in `setup_unit` (default `per`) or a `(number, unit)` pair.

## `production_capacity(rate, available_time, *, per="h", time_unit="h", efficiency_percent=100, setup_time=0, rounding="none", places=0, registry=None) -> CapacityResult`

The inverse: `quantity = rate x efficiency/100 x max(available - setup, 0)`. If setup consumes all the time the capacity is 0 and `warnings` says so. `available_time` may be `(8, "h")`. Use `rounding="floor"` for whole units. `available_time == 0` is valid (capacity 0).

## `calculate_batch_capacity(available_time, time_per_batch, *, time_unit="h", batch_size=None, registry=None) -> BatchCapacity`

Complete batches that fit: `floor(available / time_per_batch)`, `leftover_time`, `next_batch_fraction` and (with `batch_size`) `quantity`. `time_per_batch` must be `> 0`; times may be `(number, unit)` pairs.

## Verification

Hand-calculated cases for every function, partial/zero/huge/repeating inputs, and property tests: batches reassemble the quantity, and `production_capacity(production_time(q)) == q` for any rate and efficiency.
