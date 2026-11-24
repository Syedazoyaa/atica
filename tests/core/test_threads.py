"""Thread-safety claims: precision is context-local, results are immutable, registry writes are serialised."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from atica.core import get_precision, use_precision
from atica.units import UnitRegistry, convert


def digits(value: Decimal) -> int:
    return len(value.as_tuple().digits)


def test_precision_is_isolated_between_threads():
    def work(precision: int) -> int:
        with use_precision(precision):
            # many conversions while other threads use other precisions
            sizes = {digits(convert(1, "d", "wk").value) for _ in range(300)}
            assert get_precision() == precision
            return sizes.pop() if len(sizes) == 1 else -1

    wanted = [8, 12, 20, 33, 50, 80, 8, 12]
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(work, wanted))
    assert got == wanted
    assert get_precision() == 50  # the main thread is unaffected


def test_parallel_conversions_agree_with_serial():
    inputs = [(i, "kg", "lb") for i in range(500)]
    serial = [convert(*args).value for args in inputs]
    with ThreadPoolExecutor(max_workers=8) as pool:
        parallel = list(pool.map(lambda a: convert(*a).value, inputs))
    assert parallel == serial


def test_concurrent_registration_in_one_registry_loses_nothing():
    registry = UnitRegistry()

    def add(i: int) -> None:
        registry.register_unit("u%d" % i, i + 1, "kg")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(200)))
    assert len(registry.custom_units()) == 200
    assert all(registry.convert(1, "u%d" % i, "kg").value == i + 1 for i in range(200))


def test_registries_do_not_leak_into_each_other_or_the_default():
    a, b = UnitRegistry(), UnitRegistry()
    a.register_unit("bag", 25, "kg")
    assert "bag" not in b and "bag" not in UnitRegistry()
    assert a.copy() is not a and "bag" in a.copy()
