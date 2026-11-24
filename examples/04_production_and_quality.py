"""Production planning and quality figures."""

from atica.production import calculate_batches, production_time
from atica.quality import calculate_required_input, calculate_wastage, calculate_yield

plan = calculate_batches(250, 100)
print(plan.full_batches, plan.partial_batch_quantity, plan.batches_required)  # 2 50 3
assert int(plan.batches_required) == 3 and int(plan.full_batches) == 2

t = production_time(1000, 250, efficiency_percent=80, setup_time=(30, "min"))
print(t)  # 5.5 h
assert str(t) == "5.5 h"

# Quality: every percentage states its denominator.
y = calculate_yield(1000, 900, sent_to_rework=60, recovered_from_rework=45)
print(y.first_pass_yield_percent, y.final_yield_percent, y.scrap_percent)  # 90 94.5 5.5
assert str(y.final_yield_percent) == "94.5"

print(calculate_required_input(950, scrap_percent=5))  # 1000
print(calculate_wastage(1000, 920, recovery_percent=25).net_wastage)  # 60
