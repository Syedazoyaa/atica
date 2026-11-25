"""Human-readable durations (presentation only)."""

from decimal import Decimal

import pytest

from atica.core import InvalidQuantityError, format_duration
from atica.production import production_time


@pytest.mark.parametrize(
    "value, unit, expected",
    [
        ("1.5", "h", "1 hour 30 minutes"),
        ("2.25", "h", "2 hours 15 minutes"),
        ("0.5", "h", "30 minutes"),
        ("3.75", "h", "3 hours 45 minutes"),
        (90, "min", "1 hour 30 minutes"),
        ("1.25", "h", "1 hour 15 minutes"),
        (1, "h", "1 hour"),
        (2, "h", "2 hours"),
        (1, "min", "1 minute"),
        (1, "s", "1 second"),
        (3661, "s", "1 hour 1 minute 1 second"),
        (25, "h", "1 day 1 hour"),
        (2, "d", "2 days"),
        ("1.5", "d", "1 day 12 hours"),
        (0, "h", "0 seconds"),
        ("0.0001", "s", "less than 1 second"),
        ("0.4", "s", "less than 1 second"),
        ("0.5", "s", "1 second"),
        (Decimal("0.1") + Decimal("0.2"), "h", "18 minutes"),  # no float drift
        ("59.5", "s", "1 minute"),  # rounds up to the next whole second, units carry
    ],
)
def test_format_duration(value, unit, expected):
    assert format_duration(value, unit) == expected


def test_negative_rejected():
    with pytest.raises(InvalidQuantityError):
        format_duration(-1, "h")


def test_numeric_result_unchanged():
    r = production_time(1500, 1000)  # 1.5 h exactly
    assert r.total_time == Decimal("1.5")
    assert format_duration(r.total_time, r.unit) == "1 hour 30 minutes"
