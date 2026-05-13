from typing import Any

import pytest
from pydantic import ValidationError

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData
from astrology_mcp.services.astrology_engine import AstrologyEngine
from astrology_mcp.services.geocoding_service import Coordinates


class FakeGeocodingService:
    def geocode(self, query: str) -> Coordinates | None:
        assert query == "London, United Kingdom"
        return Coordinates(latitude=51.5074, longitude=-0.1278)


class FakeTimezoneService:
    def get_timezone(self, latitude: float, longitude: float) -> str:
        assert latitude == 51.5074
        assert longitude == -0.1278
        return "Europe/London"


def _engine() -> AstrologyEngine:
    return AstrologyEngine(
        Settings(),
        geocoding_service=FakeGeocodingService(),  # type: ignore[arg-type]
        timezone_service=FakeTimezoneService(),  # type: ignore[arg-type]
    )


def _birth_data(**overrides: Any) -> BirthData:
    data: dict[str, Any] = {
        "name": "Person A",
        "birth_date": "1990-05-17",
        "birth_time": "14:35:00",
        "birth_place": "London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
        "settings": {
            "house_system": "Placidus",
            "zodiac_type": "tropical",
            "include_minor_aspects": False,
            "include_asteroids": False,
            "language": "ru",
        },
    }
    data.update(overrides)
    return BirthData.model_validate(data)


def test_successful_chart_calculation_with_coordinates() -> None:
    chart = _engine().calculate_natal_chart(_birth_data())
    response = chart.model_dump()

    assert response["chart_type"] == "natal"
    assert response["subject"]["latitude"] == 51.5074
    assert response["subject"]["longitude"] == -0.1278
    assert response["calculation_meta"]["engine"] == "kerykeion"


def test_successful_chart_calculation_with_birth_place_without_coordinates() -> None:
    chart = _engine().calculate_natal_chart(
        _birth_data(latitude=None, longitude=None, timezone=None)
    )

    assert chart.subject["latitude"] == 51.5074
    assert chart.subject["timezone"] == "Europe/London"


def test_invalid_date_returns_validation_error() -> None:
    with pytest.raises(ValidationError, match="birth_date"):
        _birth_data(birth_date="1990-17-05")


def test_invalid_time_returns_validation_error() -> None:
    with pytest.raises(ValidationError, match="birth_time"):
        _birth_data(birth_time="25:01:00")


def test_invalid_coordinates_return_validation_error() -> None:
    with pytest.raises(ValidationError, match="latitude"):
        _birth_data(latitude=91)


def test_unknown_timezone_returns_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown timezone"):
        _engine().calculate_natal_chart(_birth_data(timezone="Unknown/Zone"))


def test_response_contains_all_main_planets() -> None:
    chart = _engine().calculate_natal_chart(_birth_data())
    names = {planet.name for planet in chart.planets}

    assert {
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
    }.issubset(names)
    assert "True_North_Lunar_Node" in names
    assert "Chiron" in names


def test_response_contains_twelve_houses() -> None:
    chart = _engine().calculate_natal_chart(_birth_data())

    assert len(chart.houses) == 12
    assert {house.house_number for house in chart.houses} == set(range(1, 13))


def test_response_contains_ascendant_and_midheaven() -> None:
    chart = _engine().calculate_natal_chart(_birth_data())

    assert "ascendant" in chart.angles
    assert "midheaven" in chart.angles


def test_aspect_structure() -> None:
    chart = _engine().calculate_natal_chart(_birth_data())

    assert chart.aspects
    first = chart.aspects[0].model_dump()
    expected_keys = {"planet_a", "planet_b", "aspect_type", "orb", "exact_angle", "actual_angle"}
    assert expected_keys <= set(first)


def test_same_input_returns_same_output() -> None:
    engine = _engine()
    first = engine.calculate_natal_chart(_birth_data()).model_dump()
    second = engine.calculate_natal_chart(_birth_data()).model_dump()

    assert first == second
