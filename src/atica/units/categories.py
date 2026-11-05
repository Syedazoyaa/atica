"""Measurement categories and their base units.

Conversions are only allowed between units of the *same* category. Converting
across categories (e.g. watts to volts) needs extra physical information and
a valid formula, so it is rejected.
"""
from __future__ import annotations

from typing import Dict

#: category -> unit id of that category's base unit
BASE_UNITS: Dict[str, str] = {
    "length": "m",
    "mass": "g",
    "area": "m2",
    "volume": "litre",
    "temperature": "kelvin",
    "time": "second",
    "pressure": "Pa",
    "force": "N",
    "speed": "m/s",
    "power": "W",
    "energy": "J",
    "frequency": "Hz",
    "voltage": "V",
    "current": "A",
    "resistance": "ohm",
    "torque": "Nm",
}

CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "length": "Length / distance",
    "mass": "Weight / mass",
    "area": "Area",
    "volume": "Volume / capacity",
    "temperature": "Temperature",
    "time": "Time",
    "pressure": "Pressure",
    "force": "Force",
    "speed": "Speed",
    "power": "Power",
    "energy": "Energy",
    "frequency": "Frequency",
    "voltage": "Electrical voltage",
    "current": "Electrical current",
    "resistance": "Electrical resistance",
    "torque": "Mechanical torque",
}
