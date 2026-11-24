"""The unit registry: lookup, compatibility, conversion and custom units."""

from __future__ import annotations

import dataclasses
import difflib
import threading
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..core.exceptions import (
    IncompatibleUnitError,
    InvalidQuantityError,
    UnitDefinitionError,
    UnknownUnitError,
    UnsupportedOperationError,
    ValidationError,
)
from ..core.precision import display_decimal, fraction_to_decimal, to_fraction
from ..core.results import Result
from ..core.rounding import Rounding, resolve_rounding, round_fraction
from .definitions import BASE_UNITS, Unit, standard_units

_STANDARD: Tuple[Unit, ...] = standard_units()
_MAX_NAME = 64
_REGISTRY_FORMAT = "atica.unit_registry"
_REGISTRY_VERSION = 1


@dataclasses.dataclass(frozen=True)
class Conversion(Result):
    """Result of :func:`~atica.units.convert`.

    ``value`` is in ``unit``; ``exact_value`` is the same before any requested rounding.
    ``str(conversion)`` is ``"2500 g"``.
    """

    value: Decimal
    unit: str
    source_value: Decimal
    source_unit: str
    category: str
    exact_value: Decimal
    rounding: Rounding = Rounding.NONE
    places: int = 0
    formula: str = ""
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return "%s %s" % (display_decimal(self.value), self.unit)


class UnitRegistry:
    """A set of units. Registries are independent of one another.

    ``UnitRegistry()`` contains every standard unit and may be extended with
    :meth:`register_unit`; a *frozen* registry (such as the shared default one) rejects changes.
    """

    def __init__(self, *, include_standard: bool = True) -> None:
        self._units: Dict[str, Unit] = {}  # canonical symbol -> unit (insertion ordered)
        self._lookup: Dict[str, Unit] = {}  # any accepted spelling -> unit
        self._bases: Dict[str, str] = {}  # category -> base unit symbol
        self._frozen = False
        self._lock = threading.RLock()
        if include_standard:
            self._bases.update(BASE_UNITS)
            for unit in _STANDARD:
                self._add(unit)

    # --------------------------------------------------------------- internals
    def _add(self, unit: Unit) -> None:
        for key in (unit.symbol, *unit.aliases):
            self._lookup[key] = unit
        self._units[unit.symbol] = unit

    def _check_mutable(self) -> None:
        if self._frozen:
            raise UnsupportedOperationError(
                "This registry is read-only (it is the shared default registry).",
                hint="Create your own with UnitRegistry() (or default_registry().copy()) and register units there.",
            )

    @property
    def frozen(self) -> bool:
        """True when the registry cannot be modified."""
        return self._frozen

    def freeze(self) -> UnitRegistry:
        """Make this registry read-only (irreversible; use :meth:`copy` for a writable one)."""
        self._frozen = True
        return self

    # ------------------------------------------------------------------ lookup
    def get(self, name: str) -> Unit:
        """Return the unit called ``name`` (symbol or alias, case-sensitive)."""
        if isinstance(name, str):
            found = self._lookup.get(name.strip())
            if found is not None:
                return found
        shown = repr(name)
        hint = "Unit names are case-sensitive."
        if isinstance(name, str):
            close = difflib.get_close_matches(name.strip(), list(self._lookup), n=3, cutoff=0.6)
            if close:
                hint = "Did you mean: %s?" % ", ".join(close)
        else:
            hint = "Unit names must be strings."
        raise UnknownUnitError("Unknown unit %s." % shown, parameter="unit", hint=hint)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.strip() in self._lookup

    def units(self, category: Optional[str] = None) -> Tuple[Unit, ...]:
        """All units, optionally only those of one ``category``."""
        if category is not None:
            self.base_unit(category)  # validates the category
            return tuple(u for u in self._units.values() if u.category == category)
        return tuple(self._units.values())

    def categories(self) -> Tuple[str, ...]:
        """Names of all measurement categories."""
        return tuple(self._bases)

    def base_unit(self, category: str) -> str:
        """Symbol of the base unit of ``category``."""
        try:
            return self._bases[category]
        except KeyError:
            raise UnknownUnitError(
                "Unknown category %r." % (category,),
                parameter="category",
                hint="Available: %s." % ", ".join(self._bases),
            ) from None

    def are_compatible(self, unit_a: str, unit_b: str) -> bool:
        """True when both units measure the same kind of quantity."""
        return self.get(unit_a).category == self.get(unit_b).category

    # -------------------------------------------------------------- conversion
    def _pair(self, from_unit: str, to_unit: str) -> Tuple[Unit, Unit]:
        src, dst = self.get(from_unit), self.get(to_unit)
        if src.category != dst.category:
            same = [u.symbol for u in self.units(src.category)][:6]
            raise IncompatibleUnitError(
                "Cannot convert %s (%s) to %s (%s): they measure different things."
                % (src.symbol, src.category, dst.symbol, dst.category),
                parameter="to_unit",
                hint="Units compatible with %s include: %s." % (src.symbol, ", ".join(same)),
            )
        return src, dst

    def factor(self, from_unit: str, to_unit: str) -> Fraction:
        """Exact multiplier ``m`` with ``value_in_to_unit = value_in_from_unit * m``.

        Only defined for ordinary (non-offset) units; raises
        :class:`~atica.core.exceptions.UnsupportedOperationError` for Celsius/Fahrenheit.
        """
        src, dst = self._pair(from_unit, to_unit)
        if src.is_offset or dst.is_offset:
            raise UnsupportedOperationError(
                "%s -> %s has an offset and cannot be expressed as one multiplier."
                % (src.symbol, dst.symbol),
                parameter="from_unit",
                hint="Use convert() for absolute temperatures, or convert(..., interval=True) for differences.",
            )
        return src.factor / dst.factor

    def convert(
        self,
        value: Any,
        from_unit: str,
        to_unit: str,
        *,
        rounding: Any = Rounding.NONE,
        places: int = 0,
        interval: bool = False,
    ) -> Conversion:
        """Convert ``value`` from ``from_unit`` to ``to_unit`` (see :func:`atica.units.convert`)."""
        src, dst = self._pair(from_unit, to_unit)
        policy, places = resolve_rounding(rounding, places)
        amount = to_fraction(value, "value")
        if interval:
            if src.category != "temperature":
                raise UnsupportedOperationError(
                    "interval=True only applies to temperature units.", parameter="interval"
                )
            result = amount * src.factor / dst.factor
            formula = "difference x %s" % _show(src.factor / dst.factor)
        else:
            base = (amount + src.offset) * src.factor
            if src.category == "temperature" and base < 0:
                raise InvalidQuantityError(
                    "%s %s is below absolute zero." % (_show(amount), src.symbol),
                    parameter="value",
                    hint="Temperatures cannot be below absolute zero (0 K).",
                )
            result = base / dst.factor - dst.offset
            if src.is_offset or dst.is_offset:
                formula = "((value + %s) x %s) / %s - %s" % (
                    _show(src.offset),
                    _show(src.factor),
                    _show(dst.factor),
                    _show(dst.offset),
                )
            else:
                formula = "value x %s" % _show(src.factor / dst.factor)
        exact = fraction_to_decimal(result)
        rounded = round_fraction(result, policy, places)
        return Conversion(
            value=rounded if policy is not Rounding.NONE else _norm(exact),
            unit=dst.symbol,
            source_value=_norm(fraction_to_decimal(amount)),
            source_unit=src.symbol,
            category=src.category,
            exact_value=_norm(exact),
            rounding=policy,
            places=places,
            formula=formula,
        )

    # ------------------------------------------------------------ custom units
    def _validate_new_name(self, name: str, what: str = "unit") -> str:
        if not isinstance(name, str) or not name.strip():
            raise UnitDefinitionError("A %s name must be a non-empty string." % what, parameter="name")
        name = name.strip()
        if len(name) > _MAX_NAME or not name.isprintable():
            raise UnitDefinitionError(
                "%r is not a valid %s name (max %d printable characters)." % (name, what, _MAX_NAME),
                parameter="name",
            )
        if name in self._lookup:
            raise UnitDefinitionError(
                "The name %r is already used by unit %r." % (name, self._lookup[name].symbol),
                parameter="name",
                hint="Choose a different name; existing units cannot be redefined.",
            )
        return name

    def _validate_aliases(self, name: str, aliases: Iterable[str]) -> List[str]:
        """Each alias must be a new name, different from ``name`` and from the other aliases."""
        if isinstance(aliases, str):
            raise UnitDefinitionError(
                "aliases must be a list of names, not a single string.",
                parameter="aliases",
                hint="Write aliases=[%r]." % aliases,
            )
        checked: List[str] = []
        for alias in aliases:
            alias = self._validate_new_name(alias, "alias")
            if alias == name or alias in checked:
                raise UnitDefinitionError("Duplicate alias %r." % alias, parameter="aliases")
            checked.append(alias)
        return checked

    def register_unit(
        self,
        name: str,
        factor: Any,
        reference_unit: str,
        *,
        aliases: Iterable[str] = (),
        display_name: Optional[str] = None,
    ) -> Unit:
        """Define ``1 <name> = <factor> <reference_unit>``.

        >>> reg = UnitRegistry()
        >>> _ = reg.register_unit("bag", 25, "kg")
        >>> str(reg.convert(4, "bag", "kg"))
        '100 kg'

        The new unit belongs to the reference unit's category.  Offset scales
        (Celsius, Fahrenheit) cannot be used as a reference.  Existing names can
        never be redefined, which also makes circular definitions impossible.
        """
        with self._lock:
            self._check_mutable()
            name = self._validate_new_name(name)
            ref = self.get(reference_unit)
            if ref.is_offset:
                raise UnitDefinitionError(
                    "%s is an offset scale and cannot be the reference of a custom unit." % ref.symbol,
                    parameter="reference_unit",
                    hint="Use the absolute scale (K) as reference instead.",
                )
            try:
                ratio = to_fraction(factor, "factor")
            except ValidationError as exc:
                raise UnitDefinitionError(str(exc), parameter="factor") from exc
            if ratio <= 0:
                raise UnitDefinitionError(
                    "The conversion factor must be greater than zero (got %s)." % _show(ratio),
                    parameter="factor",
                )
            alias_list = self._validate_aliases(name, aliases)
            unit = Unit(
                symbol=name,
                name=display_name or name,
                category=ref.category,
                factor=ratio * ref.factor,
                aliases=tuple(alias_list),
                custom=True,
                definition=(ref.symbol, ratio),
            )
            self._add(unit)
            return unit

    def register_base_unit(self, name: str, category: str, *, aliases: Iterable[str] = ()) -> Unit:
        """Create a brand-new measurement category with its base unit (e.g. ``'sheet'``, ``'sheets'``).

        Further units of that category are then added with :meth:`register_unit`.
        """
        with self._lock:
            self._check_mutable()
            if not isinstance(category, str) or not category.strip():
                raise UnitDefinitionError("A category name must be a non-empty string.", parameter="category")
            category = category.strip()
            if category in self._bases:
                raise UnitDefinitionError("Category %r already exists." % category, parameter="category")
            name = self._validate_new_name(name)
            alias_list = self._validate_aliases(name, aliases)
            unit = Unit(
                name,
                name,
                category,
                Fraction(1),
                aliases=tuple(alias_list),
                custom=True,
                definition=(name, Fraction(1)),
            )
            self._bases[category] = name
            self._add(unit)
            return unit

    def unregister_unit(self, name: str) -> None:
        """Remove a custom unit (not allowed for built-in units or units others are defined from)."""
        with self._lock:
            self._check_mutable()
            unit = self.get(name)
            if not unit.custom:
                raise UnsupportedOperationError(
                    "%s is a built-in unit and cannot be removed." % unit.symbol, parameter="name"
                )
            if self._bases.get(unit.category) == unit.symbol:
                raise UnsupportedOperationError(
                    "%s is the base unit of a custom category." % unit.symbol, parameter="name"
                )
            users = [
                u.symbol
                for u in self._units.values()
                if u.definition and u.definition[0] == unit.symbol and u is not unit
            ]
            if users:
                raise UnsupportedOperationError(
                    "%s is the reference of %s." % (unit.symbol, ", ".join(users)),
                    parameter="name",
                    hint="Remove those units first.",
                )
            for key in (unit.symbol, *unit.aliases):
                self._lookup.pop(key, None)
            del self._units[unit.symbol]

    def custom_units(self) -> Tuple[Unit, ...]:
        """User-defined units, in registration order."""
        return tuple(u for u in self._units.values() if u.custom)

    # ----------------------------------------------------------- serialisation
    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly description of the custom units/categories (built-ins are implicit)."""
        items: List[Dict[str, Any]] = []
        for unit in self.custom_units():
            assert unit.definition is not None
            if self._bases.get(unit.category) == unit.symbol:
                items.append({"name": unit.symbol, "category": unit.category, "aliases": list(unit.aliases)})
            else:
                ref, ratio = unit.definition
                items.append(
                    {
                        "name": unit.symbol,
                        "reference_unit": ref,
                        "factor": "%d/%d" % (ratio.numerator, ratio.denominator),
                        "aliases": list(unit.aliases),
                        "display_name": unit.name,
                    }
                )
        return {"format": _REGISTRY_FORMAT, "version": _REGISTRY_VERSION, "custom_units": items}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UnitRegistry:
        """Rebuild a registry written by :meth:`to_dict` (all-or-nothing)."""
        if not isinstance(data, Mapping) or data.get("format") != _REGISTRY_FORMAT:
            raise UnitDefinitionError("Not an ATICA unit registry description.", parameter="data")
        if data.get("version") != _REGISTRY_VERSION:
            raise UnitDefinitionError(
                "Unsupported registry version %r." % (data.get("version"),), parameter="data"
            )
        registry = cls()
        for item in data.get("custom_units", []):
            try:
                if "category" in item:
                    registry.register_base_unit(
                        item["name"], item["category"], aliases=item.get("aliases", ())
                    )
                else:
                    registry.register_unit(
                        item["name"],
                        item["factor"],
                        item["reference_unit"],
                        aliases=item.get("aliases", ()),
                        display_name=item.get("display_name"),
                    )
            except (KeyError, TypeError) as exc:
                raise UnitDefinitionError(
                    "Malformed custom unit entry: %r (%s)." % (item, exc), parameter="data"
                ) from None
        return registry

    def copy(self) -> UnitRegistry:
        """An independent, writable copy."""
        return UnitRegistry.from_dict(self.to_dict())


def _show(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    from ..core.precision import format_decimal

    exact = fraction_to_decimal(value)
    if Fraction(exact) == value:
        return format_decimal(exact)
    return "%d/%d" % (value.numerator, value.denominator)


def _norm(value: Decimal) -> Decimal:
    from ..core.precision import normalize

    return normalize(value)
