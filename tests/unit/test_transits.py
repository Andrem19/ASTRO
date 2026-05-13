from typing import Any

import pytest
from sqlalchemy import create_engine

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, ForecastCalculationSettings, ProfileCreate
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
