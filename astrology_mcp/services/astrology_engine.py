"""Kerykeion-backed astrology calculation service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kerykeion import AstrologicalSubject
from kerykeion.chart_data_factory import ChartDataFactory
from pydantic import ValidationError

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import (
    Aspect,
    BirthData,
    GeoLocation,
    HousePosition,
    NatalChart,
    PlanetPosition,
)
from astrology_mcp.services.geocoding_service import GeocodingService
from astrology_mcp.services.timezone_service import TimezoneService

HOUSE_SYSTEM_IDENTIFIERS = {
    "placidus": "P",
    "koch": "K",
    "whole sign": "W",
    "whole_sign": "W",
    "equal": "A",
}
SUPPORTED_ZODIAC_TYPES = {"tropical": "Tropical", "sidereal": "Sidereal"}

MAIN_POINTS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "True_North_Lunar_Node",
    "Chiron",
]
ANGLE_POINTS = ["Ascendant", "Medium_Coeli", "Descendant", "Imum_Coeli"]
MINOR_ASPECTS = [
    {"name": "semi-sextile", "orb": 2},
    {"name": "semi-square", "orb": 2},
    {"name": "quintile", "orb": 1},
    {"name": "sesquiquadrate", "orb": 2},
    {"name": "quincunx", "orb": 3},
]
HOUSE_NAMES = [
    "first_house",
    "second_house",
    "third_house",
    "fourth_house",
    "fifth_house",
    "sixth_house",
    "seventh_house",
    "eighth_house",
    "ninth_house",
    "tenth_house",
    "eleventh_house",
    "twelfth_house",
]
HOUSE_NUMBER_BY_NAME = {
    "First_House": 1,
    "Second_House": 2,
    "Third_House": 3,
    "Fourth_House": 4,
    "Fifth_House": 5,
    "Sixth_House": 6,
    "Seventh_House": 7,
    "Eighth_House": 8,
    "Ninth_House": 9,
    "Tenth_House": 10,
    "Eleventh_House": 11,
    "Twelfth_House": 12,
}
ANGLE_RESPONSE_KEYS = {
    "ascendant": "ascendant",
    "medium_coeli": "midheaven",
    "descendant": "descendant",
    "imum_coeli": "imum_coeli",
}


class AstrologyEngine:
    """High-level astrology calculation facade."""

    def __init__(
        self,
        settings: Settings,
        geocoding_service: GeocodingService | None = None,
        timezone_service: TimezoneService | None = None,
    ) -> None:
        self._settings = settings
        self._geocoding_service = geocoding_service or GeocodingService()
        self._timezone_service = timezone_service or TimezoneService()

    @property
    def engine_name(self) -> str:
        return self._settings.astrology_engine

    def calculate_natal_chart(self, birth_data: BirthData) -> NatalChart:
        location = self._resolve_location(birth_data)
        local_datetime = datetime.combine(birth_data.birth_date, birth_data.birth_time)
        utc_datetime = self._normalize_to_utc(local_datetime, location.timezone)
        house_identifier = self._house_identifier(birth_data.settings.house_system)
        zodiac_type = self._zodiac_type(birth_data.settings.zodiac_type)

        subject = AstrologicalSubject(
            birth_data.name,
            birth_data.birth_date.year,
            birth_data.birth_date.month,
            birth_data.birth_date.day,
            birth_data.birth_time.hour,
            birth_data.birth_time.minute,
            city=location.birth_place,
            lng=location.longitude,
            lat=location.latitude,
            tz_str=location.timezone,
            zodiac_type=cast(Any, zodiac_type),
            online=False,
            houses_system_identifier=cast(Any, house_identifier),
        ).model()

        active_points = [*MAIN_POINTS, *ANGLE_POINTS]
        if birth_data.settings.include_asteroids:
            active_points.extend(["Ceres", "Pallas", "Juno", "Vesta"])
        chart_data = ChartDataFactory().create_natal_chart_data(
            subject,
            active_points=cast(Any, active_points),
            active_aspects=cast(
                Any,
                self._active_aspects(birth_data.settings.include_minor_aspects),
            ),
        )

        planets = self.calculate_planet_positions(subject)
        houses = self.calculate_houses(subject)
        aspects = self.calculate_aspects(chart_data.aspects)
        summary = self.calculate_chart_summary(planets)

        return NatalChart(
            subject={
                "name": birth_data.name,
                "birth_date": birth_data.birth_date.isoformat(),
                "birth_time": birth_data.birth_time.isoformat(),
                "birth_place": birth_data.birth_place,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
            },
            settings={
                "house_system": birth_data.settings.house_system,
                "zodiac_type": birth_data.settings.zodiac_type,
            },
            angles=self._angles(subject),
            planets=planets,
            houses=houses,
            aspects=aspects,
            elements_balance=summary["elements_balance"],
            modalities_balance=summary["modalities_balance"],
            hemispheres=summary["hemispheres"],
            dominants=summary["dominants"],
            calculation_meta={
                "engine": self._settings.astrology_engine,
                "python_environment": "astro",
                "calculated_at": utc_datetime.isoformat().replace("+00:00", "Z"),
                "normalized_utc_datetime": utc_datetime.isoformat().replace("+00:00", "Z"),
                "warnings": [],
            },
        )

    def calculate_planet_positions(self, subject: Any) -> list[PlanetPosition]:
        positions: list[PlanetPosition] = []
        for attribute in self._planet_attributes(subject):
            point = getattr(subject, attribute, None)
            if point is None:
                continue
            positions.append(self._planet_position(point))
        return positions

    def calculate_houses(self, subject: Any) -> list[HousePosition]:
        houses: list[HousePosition] = []
        for index, attribute in enumerate(HOUSE_NAMES, start=1):
            point = getattr(subject, attribute)
            houses.append(
                HousePosition(
                    house_number=index,
                    name=point.name,
                    sign=point.sign,
                    degree_in_sign=self._round_degree(point.position),
                    absolute_degree=self._round_degree(point.abs_pos),
                )
            )
        return houses

    def calculate_aspects(self, aspects: list[Any]) -> list[Aspect]:
        result: list[Aspect] = []
        for aspect in aspects:
            result.append(
                Aspect(
                    planet_a=aspect.p1_name,
                    planet_b=aspect.p2_name,
                    aspect_type=aspect.aspect,
                    orb=round(float(aspect.orbit), 4),
                    exact_angle=float(aspect.aspect_degrees),
                    actual_angle=round(self._angular_distance(float(aspect.diff)), 4),
                    movement=getattr(aspect, "aspect_movement", None),
                )
            )
        return result

    def calculate_chart_summary(
        self, planets: list[PlanetPosition]
    ) -> dict[str, dict[str, object]]:
        elements = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
        modalities = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
        hemispheres = {
            "eastern": 0,
            "western": 0,
            "northern": 0,
            "southern": 0,
        }
        for planet in planets:
            if planet.element in elements:
                elements[planet.element] += 1
            if planet.modality in modalities:
                modalities[planet.modality] += 1
            if planet.house is not None:
                east_west = "eastern" if planet.house in {10, 11, 12, 1, 2, 3} else "western"
                north_south = "northern" if planet.house in {1, 2, 3, 4, 5, 6} else "southern"
                hemispheres[east_west] += 1
                hemispheres[north_south] += 1

        return {
            "elements_balance": cast(dict[str, object], elements),
            "modalities_balance": cast(dict[str, object], modalities),
            "hemispheres": cast(dict[str, object], hemispheres),
            "dominants": {
                "element": max(elements, key=elements.__getitem__),
                "modality": max(modalities, key=modalities.__getitem__),
            },
        }

    def _resolve_location(self, birth_data: BirthData) -> GeoLocation:
        if birth_data.latitude is not None and birth_data.longitude is not None:
            latitude = birth_data.latitude
            longitude = birth_data.longitude
        elif birth_data.birth_place:
            coordinates = self._geocoding_service.geocode(birth_data.birth_place)
            if coordinates is None:
                raise ValueError(f"Could not geocode birth_place: {birth_data.birth_place}")
            latitude = coordinates.latitude
            longitude = coordinates.longitude
        else:
            raise ValueError("Either latitude/longitude or birth_place must be provided")

        timezone = birth_data.timezone or self._timezone_service.get_timezone(latitude, longitude)
        if timezone is None:
            raise ValueError("Could not determine timezone from coordinates")
        self._validate_timezone(timezone)
        return GeoLocation(
            birth_place=birth_data.birth_place,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )

    @staticmethod
    def _normalize_to_utc(local_datetime: datetime, timezone: str) -> datetime:
        return local_datetime.replace(tzinfo=ZoneInfo(timezone)).astimezone(ZoneInfo("UTC"))

    @staticmethod
    def _validate_timezone(timezone: str) -> None:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {timezone}") from exc

    @staticmethod
    def _house_identifier(house_system: str) -> str:
        identifier = HOUSE_SYSTEM_IDENTIFIERS.get(house_system.strip().lower())
        if identifier is None:
            supported = ", ".join(sorted(HOUSE_SYSTEM_IDENTIFIERS))
            raise ValueError(f"Unsupported house_system: {house_system}. Supported: {supported}")
        return identifier

    @staticmethod
    def _zodiac_type(zodiac_type: str) -> str:
        normalized = zodiac_type.strip().lower()
        if normalized not in SUPPORTED_ZODIAC_TYPES:
            supported = ", ".join(sorted(SUPPORTED_ZODIAC_TYPES))
            raise ValueError(f"Unsupported zodiac_type: {zodiac_type}. Supported: {supported}")
        return SUPPORTED_ZODIAC_TYPES[normalized]

    @staticmethod
    def _active_aspects(include_minor_aspects: bool) -> list[dict[str, object]]:
        major_aspects: list[dict[str, object]] = [
            {"name": "conjunction", "orb": 10},
            {"name": "opposition", "orb": 10},
            {"name": "trine", "orb": 8},
            {"name": "sextile", "orb": 6},
            {"name": "square", "orb": 5},
        ]
        return [*major_aspects, *MINOR_ASPECTS] if include_minor_aspects else major_aspects

    @staticmethod
    def _planet_attributes(subject: Any) -> list[str]:
        attributes = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]
        if getattr(subject, "true_north_lunar_node", None) is not None:
            attributes.append("true_north_lunar_node")
        if getattr(subject, "chiron", None) is not None:
            attributes.append("chiron")
        return attributes

    @staticmethod
    def _planet_position(point: Any) -> PlanetPosition:
        return PlanetPosition(
            name=point.name,
            sign=point.sign,
            degree_in_sign=AstrologyEngine._round_degree(point.position),
            absolute_degree=AstrologyEngine._round_degree(point.abs_pos),
            house=HOUSE_NUMBER_BY_NAME.get(point.house),
            element=point.element,
            modality=point.quality,
            retrograde=bool(point.retrograde),
        )

    @staticmethod
    def _angles(subject: Any) -> dict[str, dict[str, object]]:
        angles: dict[str, dict[str, object]] = {}
        for attribute, response_key in ANGLE_RESPONSE_KEYS.items():
            point = getattr(subject, attribute)
            angles[response_key] = {
                "name": point.name,
                "sign": point.sign,
                "degree_in_sign": AstrologyEngine._round_degree(point.position),
                "absolute_degree": AstrologyEngine._round_degree(point.abs_pos),
                "element": point.element,
                "modality": point.quality,
            }
        return angles

    @staticmethod
    def _round_degree(value: float) -> float:
        return round(float(value), 6)

    @staticmethod
    def _angular_distance(diff: float) -> float:
        distance = abs(diff) % 360
        return min(distance, 360 - distance)


def validation_error_message(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error["loc"])
    return f"{location}: {first_error['msg']}"
