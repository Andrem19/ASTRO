"""Domain enumerations."""

from enum import StrEnum


class AstrologyEngine(StrEnum):
    KERYKEION = "kerykeion"
    SWISSEPH = "pyswisseph"


class ZodiacType(StrEnum):
    TROPICAL = "tropical"
    SIDEREAL = "sidereal"


class HouseSystem(StrEnum):
    PLACIDUS = "Placidus"
    KOCH = "Koch"
    WHOLE_SIGN = "Whole Sign"
    EQUAL = "Equal"
