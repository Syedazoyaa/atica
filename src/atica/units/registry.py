"""The unit registry: unit lookup, compatibility and conversion."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from ..calculations.numeric import calc_context, clean, format_quantity, to_decimal
from ..calculations.rounding import RoundingPolicy, round_value
from ..exceptions import (
    ConfigurationError,
    IncompatibleUnitError,
    InvalidConversionError,
    UnknownUnitError,
)
from ..results import CalculationResult
from .categories import BASE_UNITS
from .custom_units import (
    CustomUnitDefinition,
    parse_factor,
    resolve_custom_units,
    validate_identifier,
)
from .definitions import Unit, build_standard_units

SCHEMA_VERSION = 1

# conversion strategies: (to_base, from_base)
def _to_base(value: Decimal, unit: Unit) -> Decimal:
    return (value + unit.offset) * unit.factor


def _from_base(base: Decimal, unit: Unit) -> Decimal:
    return base / unit.factor - unit.offset


_STRATEGIES = {
    "linear": (_to_base, _from_base),
    "offset": (_to_base, _from_base),
}


class UnitRegistry:
    """Holds standard and custom units. Registries are fully independent."""

    def __init__(self, *, load_standard: bool = True) -> None:
        self._standard: Dict[str, Unit] = {}
        self._aliases: Dict[str, str] = {}
        self._definitions: Dict[str, CustomUnitDefinition] = {}
        self._custom: Dict[str, Unit] = {}
        if load_standard:
            for unit in build_standard_units():
                self._add_standard(unit)

    # ------------------------------------------------------------------ lookup
    def _add_standard(self, unit: Unit) -> None:
        for key in (unit.unit_id,) + unit.aliases:
            if key in self._aliases:
                raise InvalidConversionError(
                    "Duplicate unit identifier %r in standard definitions." % key,
                    code="DUPLICATE_UNIT",
                )
            self._aliases[key] = unit.unit_id
        self._standard[unit.unit_id] = unit

    def _lookup(self, name: str) -> Optional[Unit]:
        if not isinstance(name, str):
            return None
        name = name.strip()
        if name in self._custom:
            return self._custom[name]
        std_id = self._aliases.get(name)
        return self._standard.get(std_id) if std_id else None

    def _lookup_standard(self, name: str) -> Optional[Unit]:
        std_id = self._aliases.get(name.strip()) if isinstance(name, str) else None
        return self._standard.get(std_id) if std_id else None

    def get(self, unit: str) -> Unit:
        found = self._lookup(unit)
        if found is None:
            raise UnknownUnitError("Unknown unit %r." % (unit,), field="unit")
        return found

    def has_unit(self, unit: str) -> bool:
        return self._lookup(unit) is not None

    __contains__ = has_unit

    def list_units(self, category: Optional[str] = None, *, include_custom: bool = True) -> List[Unit]:
        units: List[Unit] = list(self._standard.values())
        if include_custom:
            units += list(self._custom.values())
        if category is not None:
            if category not in BASE_UNITS:
                raise UnknownUnitError("Unknown category %r." % (category,), field="category")
            units = [u for u in units if u.category == category]
        return units

    def categories(self) -> List[str]:
        return list(BASE_UNITS)

    def base_unit(self, category: str) -> str:
        try:
            return BASE_UNITS[category]
        except KeyError:
            raise UnknownUnitError("Unknown category %r." % (category,), field="category") from None

    def are_compatible(self, unit_a: str, unit_b: str) -> bool:
        return self.get(unit_a).category == self.get(unit_b).category

    # -------------------------------------------------------------- conversion
    def convert(
        self,
        value: Any,
        from_unit: str,
        to_unit: str,
        *,
        precision: Optional[int] = None,
        rounding: Any = None,
    ) -> CalculationResult:
        """Convert ``value`` between compatible units.

        ``precision`` (decimal places) and ``rounding`` control *output* rounding;
        without them the result keeps full calculation precision. The unrounded
        value is always available as ``result.metadata['exact_quantity']``.
        """
        src = self.get(from_unit)
        dst = self.get(to_unit)
        amount = to_decimal(value, field="value")
        if src.category != dst.category:
            raise IncompatibleUnitError(
                "Cannot convert %s (%s) to %s (%s)." % (src.unit_id, src.category, dst.unit_id, dst.category),
                field="to_unit",
            )
        to_base, _ = _STRATEGIES[src.conversion_strategy]
        _, from_base = _STRATEGIES[dst.conversion_strategy]
        with calc_context():
            base = to_base(amount, src)
            if src.category == "temperature" and base < 0:
                raise InvalidConversionError(
                    "%s %s is below absolute zero." % (format_quantity(amount), src.unit_id),
                    code="BELOW_ABSOLUTE_ZERO",
                    field="value",
                )
            exact = clean(from_base(base, dst))
        policy = RoundingPolicy.parse(rounding)
        if precision is not None and policy is RoundingPolicy.NONE:
            policy = RoundingPolicy.HALF_UP
        out = round_value(exact, policy, places=precision or 0) if precision is not None else exact
        if src.conversion_strategy == "linear" and dst.conversion_strategy == "linear":
            with calc_context():
                ratio = clean(src.factor / dst.factor)
            formula = "value x %s" % format_quantity(ratio)
        else:
            formula = "(value + %s) x %s -> base; base / %s - %s" % (
                format_quantity(src.offset),
                format_quantity(src.factor),
                format_quantity(dst.factor),
                format_quantity(dst.offset),
            )
        warnings = ()
        if not (src.exact and dst.exact):
            warnings = ("Conversion uses an approximate factor.",)
        return CalculationResult(
            output_quantity=out,
            output_unit=dst.unit_id,
            input_quantity=amount,
            input_unit=src.unit_id,
            formula=formula,
            rounding_policy=policy if precision is not None else RoundingPolicy.NONE,
            warnings=warnings,
            metadata={"category": src.category, "exact_quantity": exact},
        )

    # ------------------------------------------------------------ custom units
    def _commit(self, definitions: Dict[str, CustomUnitDefinition]) -> None:
        resolved = resolve_custom_units(definitions, self._lookup_standard)
        self._definitions = definitions
        self._custom = resolved

    def register_unit(
        self,
        name: str,
        category: str,
        reference_unit: str,
        factor: Any,
        *,
        symbol: Optional[str] = None,
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Unit:
        """Register ``1 <name> = <factor> <reference_unit>``."""
        name = validate_identifier(name)
        if self._lookup(name) is not None or name in self._aliases:
            raise InvalidConversionError(
                "Unit identifier %r already exists." % name, code="DUPLICATE_UNIT", field="name"
            )
        if category not in BASE_UNITS:
            raise UnknownUnitError("Unknown category %r." % (category,), field="category")
        if not isinstance(reference_unit, str) or self._lookup(reference_unit) is None:
            raise UnknownUnitError("Unknown reference unit %r." % (reference_unit,), field="reference_unit")
        ref = self._lookup(reference_unit)
        defs = dict(self._definitions)
        defs[name] = CustomUnitDefinition(
            name=name,
            category=category,
            reference_unit=ref.unit_id,
            factor=parse_factor(factor),
            symbol=symbol,
            display_name=display_name,
            metadata=dict(metadata or {}),
        )
        self._commit(defs)
        return self._custom[name]

    def get_custom_unit(self, name: str) -> Unit:
        if name not in self._custom:
            raise UnknownUnitError("Unknown custom unit %r." % (name,), field="name")
        return self._custom[name]

    def list_custom_units(self) -> List[Unit]:
        return list(self._custom.values())

    def update_unit(
        self,
        name: str,
        *,
        category: Optional[str] = None,
        reference_unit: Optional[str] = None,
        factor: Any = None,
        symbol: Optional[str] = None,
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Unit:
        """Change a custom definition. The registry is untouched if validation fails."""
        if name not in self._definitions:
            raise UnknownUnitError("Unknown custom unit %r." % (name,), field="name")
        old = self._definitions[name]
        ref_name = old.reference_unit
        if reference_unit is not None:
            found = self._lookup(reference_unit)
            if found is None:
                raise UnknownUnitError("Unknown reference unit %r." % (reference_unit,), field="reference_unit")
            ref_name = found.unit_id
        new = CustomUnitDefinition(
            name=name,
            category=category or old.category,
            reference_unit=ref_name,
            factor=parse_factor(factor) if factor is not None else old.factor,
            symbol=symbol if symbol is not None else old.symbol,
            display_name=display_name if display_name is not None else old.display_name,
            metadata=dict(metadata) if metadata is not None else dict(old.metadata),
        )
        defs = dict(self._definitions)
        defs[name] = new
        self._commit(defs)
        return self._custom[name]

    def remove_unit(self, name: str) -> None:
        if name not in self._definitions:
            if self._lookup(name) is not None:
                raise InvalidConversionError(
                    "%r is a standard unit and cannot be removed." % name, code="STANDARD_UNIT", field="name"
                )
            raise UnknownUnitError("Unknown custom unit %r." % (name,), field="name")
        dependents = [d.name for d in self._definitions.values() if d.reference_unit == name]
        if dependents:
            raise InvalidConversionError(
                "Cannot remove %r: it is the reference of %s." % (name, ", ".join(sorted(dependents))),
                code="UNIT_IN_USE",
                field="name",
            )
        defs = dict(self._definitions)
        del defs[name]
        self._commit(defs)

    # ----------------------------------------------------------- serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialise the custom units (standard units are built in)."""
        return {
            "type": "atica.unit_registry",
            "schema_version": SCHEMA_VERSION,
            "custom_units": [d.to_dict() for d in self._definitions.values()],
        }

    def load_dict(self, data: Dict[str, Any]) -> None:
        """Replace the custom units with those in ``data`` (all-or-nothing)."""
        if not isinstance(data, dict) or data.get("type") != "atica.unit_registry":
            raise ConfigurationError("Not an ATICA unit registry configuration.")
        version = data.get("schema_version")
        if not isinstance(version, int) or version < 1 or version > SCHEMA_VERSION:
            raise ConfigurationError("Unsupported unit registry schema version %r." % (version,))
        items = data.get("custom_units")
        if not isinstance(items, list):
            raise ConfigurationError("'custom_units' must be a list.")
        defs: Dict[str, CustomUnitDefinition] = {}
        for item in items:
            if not isinstance(item, dict):
                raise ConfigurationError("Each custom unit must be an object.")
            try:
                name = validate_identifier(item["name"])
                if name in defs or name in self._aliases:
                    raise InvalidConversionError(
                        "Duplicate unit identifier %r." % name, code="DUPLICATE_UNIT", field="name"
                    )
                meta = item.get("metadata") or {}
                if not isinstance(meta, dict):
                    raise ConfigurationError("metadata must be an object.")
                defs[name] = CustomUnitDefinition(
                    name=name,
                    category=str(item["category"]),
                    reference_unit=str(item["reference_unit"]),
                    factor=parse_factor(item["factor"]),
                    symbol=item.get("symbol"),
                    display_name=item.get("display_name"),
                    metadata=meta,
                )
            except KeyError as exc:
                raise ConfigurationError("Custom unit is missing field %s." % exc) from None
        self._commit(defs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnitRegistry":
        reg = cls()
        reg.load_dict(data)
        return reg

    def save(self, path: str) -> None:
        with open(os.fspath(path), "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    def load(self, path: str) -> None:
        try:
            with open(os.fspath(path), "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise ConfigurationError("Cannot read unit configuration: %s" % exc) from exc
        self.load_dict(data)

    def copy(self) -> "UnitRegistry":
        other = UnitRegistry()
        other.load_dict(self.to_dict())
        return other
