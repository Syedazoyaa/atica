# Formulas

Every formula implemented by ATICA, with its denominator. `s` = scrap fraction (`scrap_percent / 100`), `w` = wastage fraction. All arithmetic is exact; the only rounding is the final conversion to `Decimal` (and any rounding you request).

## Units

| | |
|---|---|
| Linear and offset units | `target = ((value + offset_src) x factor_src) / factor_dst - offset_dst` |
| Celsius / Fahrenheit / Kelvin / Rankine | `K = C + 273.15`, `K = (F + 459.67) x 5/9`, `K = R x 5/9` |
| Temperature difference (`interval=True`) | `target = difference x factor_src / factor_dst` (no offsets) |
| Derived factors | `lbf = 0.45359237 x 9.80665 N`, `psi = lbf / in^2`, `hp = 550 ft x lbf / s`, `gal = 231 in^3` |

## Packaging

| | |
|---|---|
| Size of a level | `size(level) = product of the counts from the base level up` (base = 1) |
| Exact conversion | `exact = quantity x size(from) / size(to)` |
| Full packages | `floor(exact)` |
| Packages required | `ceil(exact)` |
| Remainder, packing up | `quantity - full x size(to) / size(from)` (in the from-level) |
| Remainder, splitting down | `exact - full` (in the to-level) |
| Plan | greedy: for each level largest-first, `n = floor(remaining / size)`, `remaining -= n x size` |

## Materials

| | |
|---|---|
| Units started | `good / (1 - s)` |
| Material used | `per_unit x started` |
| Material issued (gross) | `used / (1 - w)` |
| Breakdown | `base = per_unit x good`, `scrap allowance = per_unit x (started - good)`, `wastage allowance = gross - used` |
| Capacity (one material) | `available x (1 - s) / sum(q_i / (1 - w_i))`; overall = minimum |

## Production

| | |
|---|---|
| Batches | `full = floor(q / size)`, `partial = q - full x size`, `required = ceil(q / size)`, `unused = required x size - q` |
| Batch materials | each batch costed like a run; `total = full x per_full_batch + partial_batch` |
| Time | `run = quantity / (rate x eff/100)`, `total = setup + run` |
| Capacity | `rate x eff/100 x max(available - setup, 0)` |
| Batch capacity | `full = floor(available / time_per_batch)`, `leftover = available - full x time_per_batch` |
| Constraints | zero stays zero -> `max(q, minimum)` -> snap to multiple -> `<= maximum` |

## Quality

| | Denominator |
|---|---|
| `scrap = input x s` ; `good = input x (1 - s)` ; `input = good / (1 - s)` | input |
| `scrap % = scrap / input x 100` | input |
| First-pass yield `= good_first_pass / input` | input |
| Final yield `= (good_first_pass + recovered) / input` | input |
| Rework rate `= sent_to_rework / input` | input |
| Rework recovery `= recovered / sent_to_rework` | reworked units |
| Rework projection: `final yield = FPY + rework% x recovery%` | input |
| Gross wastage `= material_input - material_in_output` ; net `= gross - recovered` | |
| Wastage %, net wastage %, utilisation % | material input |
| Recovery % | gross wastage |

## Purchasing

`net = max(required - stock, 0)`; if `net > 0`: `order = ceil_to_multiple(max(net, MOQ), multiple)`, else `0`; `surplus = order - net`; purchase-unit quantities are the requirement times the exact unit factor.

## How they were verified

Independently of the implementation: published constants for unit factors, hand-calculated expected values for each formula (documented next to each test), exact `Fraction` oracles in property tests (Hypothesis) for conservation and inverse relations (e.g. `expected_output(required_input(g)) == g`, `production_capacity(production_time(q)) == q`, `decompose` reassembles the quantity, `convert` round-trips), and boundary cases (zero, 100 % scrap, zero yield, huge/tiny magnitudes, repeating decimals).
