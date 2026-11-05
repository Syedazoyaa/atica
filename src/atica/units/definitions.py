"""Unit data model and the built-in unit table.

Conversion model
----------------
Every unit stores a ``factor`` and an optional ``offset`` relative to its
category's base unit::

    base   = (value + offset) * factor
    value' = base / target.factor - target.offset

For ordinary units ``offset`` is 0, which gives the simple rule
``base = value * factor`` / ``target = base / target_factor``. Temperature
scales use a non-zero offset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from ..calculations.numeric import calc_context, to_decimal
from .categories import BASE_UNITS


@dataclass(frozen=True)
class Unit:
    unit_id: str
    name: str
    symbol: str
    category: str
    base_unit: str
    factor: Decimal
    offset: Decimal = Decimal(0)
    conversion_strategy: str = "linear"  # "linear" | "offset"
    is_custom: bool = False
    aliases: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def exact(self) -> bool:
        return bool(self.metadata.get("exact", True))


# (id, name, symbol, category, factor-to-base, aliases, exact?)
_L = "length"
_STANDARD = [
    # length (base: m)
    ("mm", "Millimetre", "mm", _L, "0.001", ("millimeter",), True),
    ("cm", "Centimetre", "cm", _L, "0.01", ("centimeter",), True),
    ("m", "Metre", "m", _L, "1", ("meter", "metre"), True),
    ("km", "Kilometre", "km", _L, "1000", ("kilometer",), True),
    ("inch", "Inch", "in", _L, "0.0254", ("in", "inches"), True),
    ("foot", "Foot", "ft", _L, "0.3048", ("ft", "feet"), True),
    ("yard", "Yard", "yd", _L, "0.9144", ("yd", "yards"), True),
    ("mile", "Mile", "mi", _L, "1609.344", ("mi", "miles"), True),
    # mass (base: g)
    ("mg", "Milligram", "mg", "mass", "0.001", ("milligram",), True),
    ("g", "Gram", "g", "mass", "1", ("gram",), True),
    ("kg", "Kilogram", "kg", "mass", "1000", ("kilogram",), True),
    ("tonne", "Tonne", "t", "mass", "1000000", ("t", "metric_ton"), True),
    ("pound", "Pound", "lb", "mass", "453.59237", ("lb", "lbs", "pounds"), True),
    ("ounce", "Ounce", "oz", "mass", "28.349523125", ("oz", "ounces"), True),
    # area (base: m2)
    ("mm2", "Square millimetre", "mm²", "area", "0.000001", ("mm²",), True),
    ("cm2", "Square centimetre", "cm²", "area", "0.0001", ("cm²",), True),
    ("m2", "Square metre", "m²", "area", "1", ("m²",), True),
    ("hectare", "Hectare", "ha", "area", "10000", ("ha",), True),
    ("ft2", "Square foot", "ft²", "area", "0.09290304", ("ft²", "sqft"), True),
    ("acre", "Acre", "ac", "area", "4046.8564224", ("ac", "acres"), True),
    # volume (base: litre)
    ("ml", "Millilitre", "mL", "volume", "0.001", ("mL", "milliliter"), True),
    ("litre", "Litre", "L", "volume", "1", ("l", "L", "liter"), True),
    ("m3", "Cubic metre", "m³", "volume", "1000", ("m³",), True),
    ("gallon", "US gallon", "gal", "volume", "3.785411784", ("gal", "gallons"), True),
    ("pint", "US pint", "pt", "volume", "0.473176473", ("pt", "pints"), True),
    ("floz", "US fluid ounce", "fl oz", "volume", "0.0295735295625", ("fl_oz",), True),
    # temperature (base: kelvin). base = (value + offset) * factor
    ("celsius", "Celsius", "°C", "temperature", "1", ("C", "degC", "°C"), True),
    ("fahrenheit", "Fahrenheit", "°F", "temperature", "5/9", ("F", "degF", "°F"), True),
    ("kelvin", "Kelvin", "K", "temperature", "1", ("K",), True),
    # time (base: second)
    ("second", "Second", "s", "time", "1", ("s", "sec"), True),
    ("minute", "Minute", "min", "time", "60", ("min",), True),
    ("hour", "Hour", "h", "time", "3600", ("h", "hr"), True),
    ("day", "Day", "d", "time", "86400", ("d",), True),
    # pressure (base: Pa)
    ("Pa", "Pascal", "Pa", "pressure", "1", ("pascal",), True),
    ("kPa", "Kilopascal", "kPa", "pressure", "1000", (), True),
    ("MPa", "Megapascal", "MPa", "pressure", "1000000", (), True),
    ("bar", "Bar", "bar", "pressure", "100000", (), True),
    ("psi", "Pound-force per square inch", "psi", "pressure", "6894.757293168361", ("PSI",), False),
    ("atm", "Standard atmosphere", "atm", "pressure", "101325", ("atmosphere",), True),
    # force (base: N)
    ("N", "Newton", "N", "force", "1", ("newton",), True),
    ("kN", "Kilonewton", "kN", "force", "1000", (), True),
    ("lbf", "Pound-force", "lbf", "force", "4.4482216152605", (), True),
    # speed (base: m/s)
    ("m/s", "Metre per second", "m/s", "speed", "1", ("mps",), True),
    ("km/h", "Kilometre per hour", "km/h", "speed", "5/18", ("kph", "kmh"), True),
    ("mph", "Mile per hour", "mph", "speed", "0.44704", (), True),
    # power (base: W)
    ("W", "Watt", "W", "power", "1", ("watt",), True),
    ("kW", "Kilowatt", "kW", "power", "1000", (), True),
    ("MW", "Megawatt", "MW", "power", "1000000", (), True),
    ("hp", "Mechanical horsepower", "hp", "power", "745.69987158227022", ("horsepower",), False),
    # energy (base: J)
    ("J", "Joule", "J", "energy", "1", ("joule",), True),
    ("kJ", "Kilojoule", "kJ", "energy", "1000", (), True),
    ("kWh", "Kilowatt-hour", "kWh", "energy", "3600000", (), True),
    ("cal", "Calorie (thermochemical)", "cal", "energy", "4.184", ("calorie",), True),
    # frequency (base: Hz)
    ("Hz", "Hertz", "Hz", "frequency", "1", ("hertz",), True),
    ("kHz", "Kilohertz", "kHz", "frequency", "1000", (), True),
    ("MHz", "Megahertz", "MHz", "frequency", "1000000", (), True),
    # electrical
    ("V", "Volt", "V", "voltage", "1", ("volt",), True),
    ("mV", "Millivolt", "mV", "voltage", "0.001", (), True),
    ("kV", "Kilovolt", "kV", "voltage", "1000", (), True),
    ("A", "Ampere", "A", "current", "1", ("amp", "ampere"), True),
    ("mA", "Milliampere", "mA", "current", "0.001", (), True),
    ("kA", "Kiloampere", "kA", "current", "1000", (), True),
    ("ohm", "Ohm", "Ω", "resistance", "1", ("Ohm", "Ω"), True),
    ("kohm", "Kilohm", "kΩ", "resistance", "1000", ("kOhm", "kΩ"), True),
    ("Mohm", "Megohm", "MΩ", "resistance", "1000000", ("MOhm", "MΩ"), True),
    # torque (base: Nm)
    ("Nm", "Newton metre", "N·m", "torque", "1", ("N.m", "N·m"), True),
    ("lb-ft", "Pound-foot", "lb·ft", "torque", "1.3558179483314004", ("lbft", "lb.ft"), False),
]

_OFFSETS = {"celsius": "273.15", "fahrenheit": "459.67"}


def build_standard_units() -> List[Unit]:
    """Create the built-in :class:`Unit` objects."""
    units = []
    for uid, name, symbol, category, factor, aliases, exact in _STANDARD:
        offset = Decimal(_OFFSETS.get(uid, "0"))
        units.append(
            Unit(
                unit_id=uid,
                name=name,
                symbol=symbol,
                category=category,
                base_unit=BASE_UNITS[category],
                factor=to_decimal(factor, field="factor", allow_fraction=True),
                offset=offset,
                conversion_strategy="offset" if offset != 0 else "linear",
                is_custom=False,
                aliases=tuple(aliases),
                metadata={"exact": exact},
            )
        )
    return units


def scale(a: Decimal, b: Decimal) -> Decimal:
    with calc_context():
        return a * b
