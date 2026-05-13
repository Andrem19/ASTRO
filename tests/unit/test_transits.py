import asyncio
from datetime import date, time
from typing import Any

import pytest
from sqlalchemy import create_engine

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, ForecastCalculationSettings, ProfileCreate
from astrology_mcp.mcp_server import create_mcp_server
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.services.transit_service import TransitService
from astrology_mcp.storage.database import create_session_factory
from astrology_mcp.storage.models import Base
from astrology_mcp.tools.transit_tools import _datetime


def _natal_payload() -> dict[str, Any]:
    return {
        "name": "Person A",
        "birth_date": "1990-05-17",
        "birth_time": "14:35:00",
        "birth_place": "London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
    }


def _settings(**overrides: Any) -> ForecastCalculationSettings:
    data = {
        "house_system": "Placidus",
        "zodiac_type": "tropical",
        "include_minor_aspects": False,
        "max_orb": 3,
        "sampling": "daily",
        "include_lunar_transits": True,
        "include_outer_planet_transits": True,
    }
    data.update(overrides)
    return ForecastCalculationSettings.model_validate(data)


def _birth_data(settings: ForecastCalculationSettings | None = None) -> BirthData:
    return BirthData.model_validate(
        {**_natal_payload(), "settings": (settings or _settings()).model_dump()}
    )


@pytest.fixture(scope="module")
def transit_service() -> TransitService:
    return TransitService(Settings())


@pytest.fixture
def profile_service() -> ProfileService:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return ProfileService(Settings(), session_factory=create_session_factory(engine))


def test_transits_for_specific_date(transit_service: TransitService) -> None:
    result = transit_service.calculate_transits(
        _birth_data(),
        _datetime("2026-06-01T12:00:00Z"),
        _settings(),
    )

    assert result["chart_type"] == "transit"
    assert result["transit_to_natal_aspects"]
    assert result["transit_house_positions"]


def test_month_forecast(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_month_forecast(_birth_data(), 2026, 6, _settings())

    assert forecast["forecast_type"] == "month"
    assert forecast["period"] == {"start": "2026-06-01", "end": "2026-06-30"}
    assert forecast["timeline"]


def test_year_forecast(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_year_forecast(
        _birth_data(_settings(sampling="weekly", include_lunar_transits=False)),
        2026,
        _settings(sampling="weekly", include_lunar_transits=False),
    )

    assert forecast["forecast_type"] == "year"
    assert forecast["period"] == {"start": "2026-01-01", "end": "2026-12-31"}


def test_profile_month_forecast(profile_service: ProfileService) -> None:
    created = profile_service.create_profile(ProfileCreate.model_validate(_natal_payload()))
    service = TransitService(Settings(), profile_service=profile_service)

    forecast = service.calculate_profile_month_forecast(
        str(created["profile_id"]),
        2026,
        6,
        _settings(),
    )

    assert forecast["subject"]["name"] == "Person A"  # type: ignore[index]


def test_profile_day_forecast(profile_service: ProfileService) -> None:
    created = profile_service.create_profile(ProfileCreate.model_validate(_natal_payload()))
    service = TransitService(Settings(), profile_service=profile_service)

    forecast = service.calculate_profile_day_forecast(
        str(created["profile_id"]),
        date(2026, 6, 1),
        time(12, 0),
        None,
        _settings(),
    )

    assert forecast["forecast_type"] == "day"
    assert forecast["profile_id"] == str(created["profile_id"])
    assert forecast["date"] == "2026-06-01"
    assert forecast["subject"]["name"] == "Person A"  # type: ignore[index]
    assert forecast["active_transits"]
    assert forecast["dominant_themes"]
    assert forecast["theme_summary"]
    assert forecast["llm_day_context"]["recommended_tone"] == (  # type: ignore[index]
        "balanced, non-deterministic, respectful"
    )


def test_profile_day_forecast_uses_profile_timezone_by_default(
    profile_service: ProfileService,
) -> None:
    created = profile_service.create_profile(ProfileCreate.model_validate(_natal_payload()))
    service = TransitService(Settings(), profile_service=profile_service)

    forecast = service.calculate_profile_day_forecast(
        str(created["profile_id"]),
        date(2026, 6, 1),
        time(12, 0),
        None,
        _settings(),
    )

    assert forecast["calculation_meta"]["calculated_at"] == "2026-06-01T11:00:00Z"  # type: ignore[index]


def test_profile_day_forecast_accepts_explicit_timezone(profile_service: ProfileService) -> None:
    created = profile_service.create_profile(ProfileCreate.model_validate(_natal_payload()))
    service = TransitService(Settings(), profile_service=profile_service)

    forecast = service.calculate_profile_day_forecast(
        str(created["profile_id"]),
        date(2026, 6, 1),
        time(12, 0),
        "UTC",
        _settings(),
    )

    assert forecast["calculation_meta"]["calculated_at"] == "2026-06-01T12:00:00Z"  # type: ignore[index]


def test_profile_day_forecast_unknown_profile(profile_service: ProfileService) -> None:
    service = TransitService(Settings(), profile_service=profile_service)

    with pytest.raises(ValueError, match="Profile not found"):
        service.calculate_profile_day_forecast(
            "missing",
            date(2026, 6, 1),
            time(12, 0),
            None,
            _settings(),
        )


def test_profile_day_forecast_is_deterministic(profile_service: ProfileService) -> None:
    created = profile_service.create_profile(ProfileCreate.model_validate(_natal_payload()))
    service = TransitService(Settings(), profile_service=profile_service)

    first = service.calculate_profile_day_forecast(
        str(created["profile_id"]),
        date(2026, 6, 1),
        time(12, 0),
        None,
        _settings(),
    )
    second = service.calculate_profile_day_forecast(
        str(created["profile_id"]),
        date(2026, 6, 1),
        time(12, 0),
        None,
        _settings(),
    )

    assert first == second


def test_day_forecast_classifies_supportive_and_challenging_transits() -> None:
    transits = [
        {"aspect_type": "trine", "themes": ["love_and_relationships"]},
        {"aspect_type": "sextile", "themes": ["communication_and_learning"]},
        {"aspect_type": "square", "themes": ["energy_and_conflict"]},
        {"aspect_type": "opposition", "themes": ["pressure_and_responsibility"]},
        {"aspect_type": "conjunction", "themes": ["identity_and_direction"]},
    ]

    supportive = TransitService._supportive_transits(transits)
    challenging = TransitService._challenging_transits(transits)

    assert [item["aspect_type"] for item in supportive] == ["trine", "sextile"]
    assert [item["aspect_type"] for item in challenging] == ["square", "opposition"]


def test_profile_day_forecast_registered_as_mcp_tool() -> None:
    tools = asyncio.run(create_mcp_server(Settings()).list_tools())

    assert "calculate_profile_day_forecast" in {tool.name for tool in tools}


def test_month_date_range(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_month_forecast(_birth_data(), 2026, 6, _settings())

    assert forecast["timeline"][0]["date"] == "2026-06-01"  # type: ignore[index]
    assert forecast["timeline"][-1]["date"] == "2026-06-30"  # type: ignore[index]


def test_year_date_range(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_year_forecast(
        _birth_data(_settings(sampling="weekly", include_lunar_transits=False)),
        2026,
        _settings(sampling="weekly", include_lunar_transits=False),
    )

    assert forecast["timeline"][0]["date"] == "2026-01-01"  # type: ignore[index]
    assert forecast["timeline"][-1]["date"] == "2026-12-31"  # type: ignore[index]


def test_sampling_daily(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_month_forecast(
        _birth_data(),
        2026,
        6,
        _settings(sampling="daily"),
    )

    assert len(forecast["timeline"]) == 30  # type: ignore[arg-type]


def test_sampling_weekly(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_month_forecast(
        _birth_data(_settings(sampling="weekly")),
        2026,
        6,
        _settings(sampling="weekly"),
    )

    assert len(forecast["timeline"]) < 10  # type: ignore[arg-type]


def test_disabling_lunar_transits(transit_service: TransitService) -> None:
    result = transit_service.calculate_transits(
        _birth_data(_settings(include_lunar_transits=False)),
        _datetime("2026-06-01T12:00:00Z"),
        _settings(include_lunar_transits=False),
    )

    assert all(
        aspect["transit_planet"] != "Moon"
        for aspect in result["transit_to_natal_aspects"]  # type: ignore[index]
    )


def test_forecast_structures_present(transit_service: TransitService) -> None:
    forecast = transit_service.calculate_month_forecast(_birth_data(), 2026, 6, _settings())

    assert forecast["major_transits"]
    assert forecast["peak_dates"]
    assert forecast["theme_summary"]
    assert forecast["llm_forecast_context"]


def test_forecast_stability(transit_service: TransitService) -> None:
    first = transit_service.calculate_month_forecast(_birth_data(), 2026, 6, _settings())
    second = transit_service.calculate_month_forecast(_birth_data(), 2026, 6, _settings())

    assert first == second


def test_transit_svg_smoke(transit_service: TransitService) -> None:
    result = transit_service.calculate_transits(
        _birth_data(),
        _datetime("2026-06-01T12:00:00Z"),
        _settings(),
    )
    svg = transit_service.generate_transit_chart_svg(result)

    assert svg["status"] == "ok"
    assert str(svg["svg"]).startswith("<svg")
