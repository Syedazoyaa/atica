"""Module-level convenience API backed by a shared default registry.

Every function accepts ``registry=`` so that applications (or companies) can
use an isolated :class:`~atica.units.registry.UnitRegistry` instead.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..results import CalculationResult
from .definitions import Unit
from .registry import UnitRegistry

_default_registry = UnitRegistry()


def get_default_registry() -> UnitRegistry:
    return _default_registry


def reset_default_registry() -> UnitRegistry:
    """Discard all custom units from the shared registry."""
    global _default_registry
    _default_registry = UnitRegistry()
    return _default_registry


def _reg(registry: Optional[UnitRegistry]) -> UnitRegistry:
    return registry if registry is not None else _default_registry


def convert(
    value: Any,
    from_unit: str,
    to_unit: str,
    *,
    precision: Optional[int] = None,
    rounding: Any = None,
    registry: Optional[UnitRegistry] = None,
) -> CalculationResult:
    """Convert ``value`` from ``from_unit`` to ``to_unit``.

    >>> str(convert("2.5", "kg", "g"))
    '2500 g'
    """
    return _reg(registry).convert(value, from_unit, to_unit, precision=precision, rounding=rounding)


def get_unit(unit: str, *, registry: Optional[UnitRegistry] = None) -> Unit:
    return _reg(registry).get(unit)


def list_units(category: Optional[str] = None, *, registry: Optional[UnitRegistry] = None) -> List[Unit]:
    return _reg(registry).list_units(category)


def list_categories(*, registry: Optional[UnitRegistry] = None) -> List[str]:
    return _reg(registry).categories()


def get_base_unit(category: str, *, registry: Optional[UnitRegistry] = None) -> str:
    return _reg(registry).base_unit(category)


def are_compatible(unit_a: str, unit_b: str, *, registry: Optional[UnitRegistry] = None) -> bool:
    return _reg(registry).are_compatible(unit_a, unit_b)


def register_unit(
    name: str,
    category: str,
    reference_unit: str,
    factor: Any,
    *,
    symbol: Optional[str] = None,
    display_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    registry: Optional[UnitRegistry] = None,
) -> Unit:
    """Register a custom unit: ``1 <name> = <factor> <reference_unit>``."""
    return _reg(registry).register_unit(
        name, category, reference_unit, factor, symbol=symbol, display_name=display_name, metadata=metadata
    )


def update_unit(name: str, *, registry: Optional[UnitRegistry] = None, **changes: Any) -> Unit:
    return _reg(registry).update_unit(name, **changes)


def remove_unit(name: str, *, registry: Optional[UnitRegistry] = None) -> None:
    _reg(registry).remove_unit(name)


def get_custom_unit(name: str, *, registry: Optional[UnitRegistry] = None) -> Unit:
    return _reg(registry).get_custom_unit(name)


def list_custom_units(*, registry: Optional[UnitRegistry] = None) -> List[Unit]:
    return _reg(registry).list_custom_units()


def save_units(path: str, *, registry: Optional[UnitRegistry] = None) -> None:
    _reg(registry).save(path)


def load_units(path: str, *, registry: Optional[UnitRegistry] = None) -> None:
    _reg(registry).load(path)
