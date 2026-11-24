"""Unit data model and the built-in unit table.

Conversion model
----------------
Each unit stores an exact ``factor`` and ``offset`` (both :class:`~fractions.Fraction`)
relative to its category's base unit::

    base  = (value + offset) * factor
    value = base / factor - offset

Ordinary units have ``offset == 0``.  Temperature scales that do not start at
absolute zero (Celsius, Fahrenheit) have a non-zero offset - they are *not*
ordinary multiplicative units.

All built-in factors are exact by definition (international yard and pound,
US customary volumes, thermochemical calorie, standard gravity ...), so no
approximate factors exist.  ``psi``, ``lbf``, ``hp`` and ``lbf-ft`` are derived
exactly from those definitions rather than typed in as rounded decimals.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

#: category -> symbol of its base unit
BASE_UNITS: Dict[str, str] = {
    "length": "m",
    "mass": "g",
    "area": "m2",
    "volume": "L",
    "temperature": "K",
    "time": "s",
    "count": "piece",
    "pressure": "Pa",
    "force": "N",
    "speed": "m/s",
    "power": "W",
    "energy": "J",
    "frequency": "Hz",
    "torque": "Nm",
    "voltage": "V",
    "current": "A",
    "resistance": "ohm",
}


@dataclass(frozen=True)
class Unit:
    """A unit of measurement.

    ``symbol`` is the canonical identifier (also what results report); ``aliases``
    are other accepted spellings.  ``definition`` is ``(reference_symbol, ratio)`` for
    custom units (``1 symbol = ratio reference``) and ``None`` for built-ins.
    """

    symbol: str
    name: str
    category: str
    factor: Fraction
    offset: Fraction = Fraction(0)
    aliases: Tuple[str, ...] = ()
    custom: bool = False
    definition: Optional[Tuple[str, Fraction]] = None

    @property
    def is_offset(self) -> bool:
        """True for scales with a zero offset different from the base unit's (Celsius, Fahrenheit)."""
        return self.offset != 0


F = Fraction

# derived exactly from definitions
_FT = F("0.3048")
_IN = F("0.0254")
_LB = F("453.59237")  # g
_G0 = F("9.80665")  # m/s^2 (standard gravity)
_LBF = F("0.45359237") * _G0  # N

# (symbol, name, category, factor, aliases[, offset])
_TABLE: List[Tuple[Any, ...]] = [
    # ---- length (base m)
    ("mm", "Millimetre", "length", F("0.001"), ("millimeter", "millimetre")),
    ("cm", "Centimetre", "length", F("0.01"), ("centimeter", "centimetre")),
    ("m", "Metre", "length", F(1), ("meter", "metre")),
    ("km", "Kilometre", "length", F(1000), ("kilometer", "kilometre")),
    ("um", "Micrometre", "length", F("0.000001"), ("µm", "micron", "micrometer", "micrometre")),
    ("in", "Inch", "length", _IN, ("inch", "inches")),
    ("ft", "Foot", "length", _FT, ("foot", "feet")),
    ("yd", "Yard", "length", F("0.9144"), ("yard", "yards")),
    ("mi", "Mile", "length", F("1609.344"), ("mile", "miles")),
    # ---- mass (base g)
    ("mg", "Milligram", "mass", F("0.001"), ("milligram",)),
    ("g", "Gram", "mass", F(1), ("gram", "grams")),
    ("kg", "Kilogram", "mass", F(1000), ("kilogram", "kilograms")),
    ("t", "Tonne (metric ton)", "mass", F(1_000_000), ("tonne", "tonnes", "metric_ton")),
    ("lb", "Pound", "mass", _LB, ("pound", "pounds", "lbs")),
    ("oz", "Ounce", "mass", _LB / 16, ("ounce", "ounces")),
    # ---- area (base m2)
    ("mm2", "Square millimetre", "area", F("0.000001"), ("mm²",)),
    ("cm2", "Square centimetre", "area", F("0.0001"), ("cm²",)),
    ("m2", "Square metre", "area", F(1), ("m²",)),
    ("km2", "Square kilometre", "area", F(1_000_000), ("km²",)),
    ("ha", "Hectare", "area", F(10_000), ("hectare", "hectares")),
    ("in2", "Square inch", "area", _IN * _IN, ("in²", "sqin")),
    ("ft2", "Square foot", "area", _FT * _FT, ("ft²", "sqft")),
    ("acre", "Acre", "area", F(43_560) * _FT * _FT, ("ac", "acres")),
    # ---- volume (base litre)
    ("mL", "Millilitre", "volume", F("0.001"), ("ml", "milliliter", "millilitre", "cm3", "cm³", "cc")),
    ("L", "Litre", "volume", F(1), ("l", "litre", "liter", "litres", "liters")),
    ("m3", "Cubic metre", "volume", F(1000), ("m³",)),
    ("gal", "US gallon", "volume", F(231) * _IN**3 * 1000, ("gallon", "gallons", "us_gal")),
    ("qt", "US quart", "volume", F(231) * _IN**3 * 1000 / 4, ("quart", "quarts")),
    ("pt", "US pint", "volume", F(231) * _IN**3 * 1000 / 8, ("pint", "pints")),
    ("fl_oz", "US fluid ounce", "volume", F(231) * _IN**3 * 1000 / 128, ("floz", "fl oz")),
    # ---- temperature (base K): K = (value + offset) * factor
    ("K", "Kelvin", "temperature", F(1), ("kelvin",), F(0)),
    ("C", "Celsius", "temperature", F(1), ("celsius", "degC", "°C"), F("273.15")),
    ("F", "Fahrenheit", "temperature", F(5, 9), ("fahrenheit", "degF", "°F"), F("459.67")),
    ("R", "Rankine", "temperature", F(5, 9), ("rankine", "degR", "°R"), F(0)),
    # ---- time (base s)
    ("ms", "Millisecond", "time", F("0.001"), ("millisecond", "milliseconds")),
    ("s", "Second", "time", F(1), ("sec", "second", "seconds")),
    ("min", "Minute", "time", F(60), ("minute", "minutes")),
    ("h", "Hour", "time", F(3600), ("hr", "hour", "hours")),
    ("d", "Day", "time", F(86_400), ("day", "days")),
    ("wk", "Week", "time", F(604_800), ("week", "weeks")),
    # ---- count (base piece)
    ("piece", "Piece", "count", F(1), ("pc", "pcs", "pieces", "each", "ea")),
    ("pair", "Pair", "count", F(2), ("pairs",)),
    ("dozen", "Dozen", "count", F(12), ("doz",)),
    ("gross", "Gross", "count", F(144), ()),
    # ---- pressure (base Pa)
    ("Pa", "Pascal", "pressure", F(1), ("pascal",)),
    ("kPa", "Kilopascal", "pressure", F(1000), ()),
    ("MPa", "Megapascal", "pressure", F(1_000_000), ()),
    ("bar", "Bar", "pressure", F(100_000), ()),
    ("psi", "Pound-force per square inch", "pressure", _LBF / (_IN * _IN), ("PSI",)),
    ("atm", "Standard atmosphere", "pressure", F(101_325), ("atmosphere",)),
    # ---- force (base N)
    ("N", "Newton", "force", F(1), ("newton",)),
    ("kN", "Kilonewton", "force", F(1000), ()),
    ("lbf", "Pound-force", "force", _LBF, ()),
    ("kgf", "Kilogram-force", "force", _G0, ()),
    # ---- speed (base m/s)
    ("m/s", "Metre per second", "speed", F(1), ("mps",)),
    ("km/h", "Kilometre per hour", "speed", F(5, 18), ("kph", "kmh")),
    ("mph", "Mile per hour", "speed", F(1609344, 1000 * 3600), ()),
    ("ft/s", "Foot per second", "speed", _FT, ("fps",)),
    # ---- power (base W)
    ("W", "Watt", "power", F(1), ("watt",)),
    ("kW", "Kilowatt", "power", F(1000), ()),
    ("MW", "Megawatt", "power", F(1_000_000), ()),
    ("hp", "Mechanical horsepower", "power", 550 * _FT * _LBF, ("horsepower",)),
    # ---- energy (base J)
    ("J", "Joule", "energy", F(1), ("joule",)),
    ("kJ", "Kilojoule", "energy", F(1000), ()),
    ("MJ", "Megajoule", "energy", F(1_000_000), ()),
    ("kWh", "Kilowatt-hour", "energy", F(3_600_000), ()),
    ("cal", "Calorie (thermochemical)", "energy", F("4.184"), ("calorie",)),
    ("kcal", "Kilocalorie (thermochemical)", "energy", F("4184"), ("kilocalorie",)),
    # ---- frequency (base Hz)
    ("Hz", "Hertz", "frequency", F(1), ("hertz",)),
    ("kHz", "Kilohertz", "frequency", F(1000), ()),
    ("MHz", "Megahertz", "frequency", F(1_000_000), ()),
    ("rpm", "Revolutions per minute", "frequency", F(1, 60), ()),
    # ---- torque (base N*m)
    ("Nm", "Newton metre", "torque", F(1), ("N.m", "N·m")),
    ("lbf-ft", "Pound-force foot", "torque", _FT * _LBF, ("lb-ft", "lbft", "lb.ft", "lb·ft")),
    # ---- electrical
    ("V", "Volt", "voltage", F(1), ("volt",)),
    ("mV", "Millivolt", "voltage", F("0.001"), ()),
    ("kV", "Kilovolt", "voltage", F(1000), ()),
    ("A", "Ampere", "current", F(1), ("amp", "ampere")),
    ("mA", "Milliampere", "current", F("0.001"), ()),
    ("kA", "Kiloampere", "current", F(1000), ()),
    ("ohm", "Ohm", "resistance", F(1), ("Ω",)),
    ("kohm", "Kilohm", "resistance", F(1000), ("kΩ",)),
    ("Mohm", "Megohm", "resistance", F(1_000_000), ("MΩ",)),
]


def standard_units() -> Tuple[Unit, ...]:
    """Build the immutable tuple of built-in units."""
    units = []
    for row in _TABLE:
        symbol, name, category, factor, aliases = row[:5]
        offset = row[5] if len(row) > 5 else F(0)
        units.append(Unit(symbol, name, category, factor, offset, tuple(aliases)))
    return tuple(units)
