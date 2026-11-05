"""Custom (company-defined) unit definitions.

A custom unit is stored as a *definition*: ``1 <name> = <factor> <reference_unit>``.
Definitions are resolved to the category base unit by
:func:`resolve_custom_units`, which also detects circular definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, Optional

from ..calculations.numeric import calc_context, format_quantity, to_decimal
from ..exceptions import (
    IncompatibleUnitError,
    InvalidConversionError,
    InvalidQuantityError,
    UnknownUnitError,
)
from .definitions import Unit

MAX_IDENTIFIER_LENGTH = 64


@dataclass
class CustomUnitDefinition:
    name: str
    category: str
    reference_unit: str
    factor: Decimal
    symbol: Optional[str] = None
    display_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "reference_unit": self.reference_unit,
            "factor": format_quantity(self.factor),
            "symbol": self.symbol,
            "display_name": self.display_name,
            "metadata": dict(self.metadata),
        }


def validate_identifier(name: Any) -> str:
    """Return the cleaned identifier or raise :class:`InvalidConversionError`."""
    if not isinstance(name, str) or not name.strip():
        raise InvalidConversionError(
            "A unit identifier must be a non-empty string.", code="INVALID_IDENTIFIER", field="name"
        )
    name = name.strip()
    if (
        len(name) > MAX_IDENTIFIER_LENGTH
        or not name.isprintable()
        or any(ch.isspace() for ch in name)
    ):
        raise InvalidConversionError(
            "Unit identifier %r is invalid (max %d printable characters, no spaces)."
            % (name, MAX_IDENTIFIER_LENGTH),
            code="INVALID_IDENTIFIER",
            field="name",
        )
    return name


def parse_factor(factor: Any) -> Decimal:
    try:
        value = to_decimal(factor, field="factor", allow_fraction=True)
    except InvalidQuantityError as exc:
        raise InvalidConversionError(
            "Conversion factor %r is not a valid number." % (factor,),
            code="INVALID_FACTOR",
            field="factor",
        ) from exc
    if value <= 0:
        raise InvalidConversionError(
            "Conversion factor must be greater than zero (got %s)." % format_quantity(value),
            code="INVALID_FACTOR",
            field="factor",
        )
    return value


def resolve_custom_units(
    definitions: Dict[str, CustomUnitDefinition],
    lookup_standard: Callable[[str], Optional[Unit]],
) -> Dict[str, Unit]:
    """Resolve every definition to a :class:`Unit` expressed against the base unit.

    Raises on unknown references, category mismatches, non-linear references and
    circular definitions. Nothing is mutated.
    """
    resolved: Dict[str, Unit] = {}

    def resolve(name: str, stack: tuple) -> Unit:
        if name in resolved:
            return resolved[name]
        if name in stack:
            chain = " -> ".join(stack + (name,))
            raise InvalidConversionError(
                "Circular unit definition: %s." % chain, code="CIRCULAR_DEFINITION", field="reference_unit"
            )
        d = definitions[name]
        if d.reference_unit in definitions:
            ref = resolve(d.reference_unit, stack + (name,))
        else:
            ref = lookup_standard(d.reference_unit)
            if ref is None:
                raise UnknownUnitError(
                    "Unknown reference unit %r for custom unit %r." % (d.reference_unit, name),
                    field="reference_unit",
                )
        if ref.conversion_strategy != "linear":
            raise InvalidConversionError(
                "Reference unit %r uses an offset scale and cannot anchor a custom unit." % ref.unit_id,
                code="INVALID_REFERENCE",
                field="reference_unit",
            )
        if d.category != ref.category:
            raise IncompatibleUnitError(
                "Custom unit %r is declared as %r but reference unit %r is %r."
                % (name, d.category, ref.unit_id, ref.category),
                field="category",
            )
        with calc_context():
            factor = d.factor * ref.factor
        unit = Unit(
            unit_id=name,
            name=d.display_name or name,
            symbol=d.symbol or name,
            category=ref.category,
            base_unit=ref.base_unit,
            factor=factor,
            offset=Decimal(0),
            conversion_strategy="linear",
            is_custom=True,
            metadata={
                **d.metadata,
                "exact": True,
                "reference_unit": ref.unit_id,
                "reference_factor": format_quantity(d.factor),
            },
        )
        resolved[name] = unit
        return unit

    for key in definitions:
        resolve(key, ())
    return resolved
