"""Production time estimation and capacity over a time window.

Assumptions (stated in every result's ``assumptions``)
------------------------------------------------------
* production runs at one **constant** rate - no ramp-up, breaks or breakdowns;
* ``efficiency_percent`` scales the nominal rate: ``effective_rate = rate x efficiency/100``;
* setup time is a one-off block added before production and is not scaled by efficiency;
* nothing is scheduled: calendars, shifts and machines are out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Optional, Tuple

from ..core.exceptions import ValidationError
from ..core.precision import dec, display_decimal
from ..core.results import Result
from ..core.rounding import Rounding, resolve_rounding, round_fraction
from ..core.validation import non_negative, percentage, positive
from ..units import UnitRegistry, default_registry

_HUNDRED = Fraction(100)


def duration(value: Any, name: str, default_unit: str, target_unit: str, registry: UnitRegistry) -> Fraction:
    """A duration given as a number (in ``default_unit``) or ``(number, unit)``, expressed in ``target_unit``."""
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ValidationError("%s must be a number or (number, unit)." % name, parameter=name)
        amount, unit = non_negative(value[0], name), value[1]
    else:
        amount, unit = non_negative(value, name), default_unit
    _require_time(registry, unit, name)
    return amount * registry.factor(unit, target_unit)


def _require_time(registry: UnitRegistry, unit: str, name: str) -> None:
    from ..core.exceptions import IncompatibleUnitError

    u = registry.get(unit)
    if u.category != "time":
        raise IncompatibleUnitError(
            "%s must be a time unit; %s measures %s." % (name, u.symbol, u.category),
            parameter=name,
            hint="Use units such as 's', 'min', 'h', 'd'.",
        )


def _efficiency(value: Any) -> Fraction:
    eff = percentage(value, "efficiency_percent")
    if eff == 0:
        raise ValidationError(
            "efficiency_percent must be greater than 0.",
            parameter="efficiency_percent",
            hint="0% efficiency means nothing is produced.",
        )
    return eff


_ASSUMPTIONS = (
    "constant production rate (no ramp-up, breaks or breakdowns)",
    "efficiency scales the nominal rate",
    "setup time is added once and is not scaled by efficiency",
)


@dataclass(frozen=True)
class ProductionTime(Result):
    """Result of :func:`production_time`: ``total_time = setup_time + run_time`` in ``unit``."""

    total_time: Decimal
    unit: str
    run_time: Decimal
    setup_time: Decimal
    quantity: Decimal
    rate: Decimal
    rate_per: str
    efficiency_percent: Decimal
    effective_rate: Decimal
    formula: str = "run_time = quantity / (rate x efficiency/100); total = setup + run_time"
    assumptions: Tuple[str, ...] = _ASSUMPTIONS
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return "%s %s" % (display_decimal(self.total_time), self.unit)


def production_time(
    quantity: Any,
    rate: Any,
    *,
    per: str = "h",
    unit: str = "h",
    efficiency_percent: Any = 100,
    setup_time: Any = 0,
    setup_unit: Optional[str] = None,
    registry: Optional[UnitRegistry] = None,
) -> ProductionTime:
    """Time needed to produce ``quantity`` at ``rate`` units per ``per``.

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
    """
    reg = registry or default_registry()
    q = non_negative(quantity, "quantity")
    r = positive(rate, "rate")
    eff = _efficiency(efficiency_percent)
    _require_time(reg, per, "per")
    _require_time(reg, unit, "unit")
    setup = duration(setup_time, "setup_time", setup_unit or per, unit, reg)
    effective = r * eff / _HUNDRED
    run = q / effective * reg.factor(per, unit)
    total = setup + run
    return ProductionTime(
        total_time=dec(total),
        unit=reg.get(unit).symbol,
        run_time=dec(run),
        setup_time=dec(setup),
        quantity=dec(q),
        rate=dec(r),
        rate_per=reg.get(per).symbol,
        efficiency_percent=dec(eff),
        effective_rate=dec(effective),
    )


@dataclass(frozen=True)
class CapacityResult(Result):
    """Result of :func:`production_capacity`: units producible in the available time."""

    quantity: Decimal
    exact_quantity: Decimal
    available_time: Decimal
    time_unit: str
    productive_time: Decimal
    rate: Decimal
    rate_per: str
    efficiency_percent: Decimal
    rounding: Rounding = Rounding.NONE
    places: int = 0
    formula: str = "quantity = rate x efficiency/100 x max(available_time - setup_time, 0)"
    assumptions: Tuple[str, ...] = _ASSUMPTIONS
    warnings: Tuple[str, ...] = ()


def production_capacity(
    rate: Any,
    available_time: Any,
    *,
    per: str = "h",
    time_unit: str = "h",
    efficiency_percent: Any = 100,
    setup_time: Any = 0,
    rounding: Any = Rounding.NONE,
    places: int = 0,
    registry: Optional[UnitRegistry] = None,
) -> CapacityResult:
    """Units that can be produced in ``available_time`` (the inverse of :func:`production_time`).

    ``available_time`` is a number in ``time_unit`` or a ``(number, unit)`` pair; ``setup_time`` likewise.
    If setup consumes all available time the capacity is 0 and a warning is returned.
    Use ``rounding='floor'`` for whole finished units.

    >>> str(production_capacity(250, (8, "h")).quantity)
    '2000'
    """
    reg = registry or default_registry()
    r = positive(rate, "rate")
    eff = _efficiency(efficiency_percent)
    policy, places = resolve_rounding(rounding, places)
    _require_time(reg, per, "per")
    _require_time(reg, time_unit, "time_unit")
    avail = duration(available_time, "available_time", time_unit, time_unit, reg)
    setup = duration(setup_time, "setup_time", time_unit, time_unit, reg)
    productive = max(avail - setup, Fraction(0))
    warnings: Tuple[str, ...] = ()
    if setup > avail:
        warnings = ("Setup time exceeds the available time; nothing can be produced.",)
    exact = r * eff / _HUNDRED * productive * reg.factor(time_unit, per)
    return CapacityResult(
        quantity=round_fraction(exact, policy, places) if policy is not Rounding.NONE else dec(exact),
        exact_quantity=dec(exact),
        available_time=dec(avail),
        time_unit=reg.get(time_unit).symbol,
        productive_time=dec(productive),
        rate=dec(r),
        rate_per=reg.get(per).symbol,
        efficiency_percent=dec(eff),
        rounding=policy,
        places=places,
        warnings=warnings,
    )
