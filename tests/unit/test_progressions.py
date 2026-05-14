from __future__ import annotations

import asyncio
from datetime import date, time

import pytest
from sqlalchemy import create_engine

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import (
    BirthData,
    ProfileCreate,
    ProgressionCalculationSettings,
)
from astrology_mcp.mcp_server import create_mcp_server
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.services.progression_service import ProgressionService
from astrology_mcp.storage.database import create_session_factory
from astrology_mcp.storage.models import Base


class FakeChart:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class FakeAstrologyEngine:
    def calculate_natal_chart(self, birth_data: BirthData) -> FakeChart:
        day_offset = (birth_data.birth_date - date(1990, 1, 1)).days
        sun_degree = (10 + day_offset) % 360
        moon_degree = (80 + day_offset * 13) % 360
        mc_degree = (120 + day_offset) % 360
        payload: dict[str, object] = {
            "subject": {
                "name": birth_data.name,
                "birth_date": birth_data.birth_date.isoformat(),
                "birth_time": birth_data.birth_time.isoformat(),
                "birth_place": birth_data.birth_place,
                "latitude": birth_data.latitude,
                "longitude": birth_data.longitude,
                "timezone": birth_data.timezone,
            },
            "settings": birth_data.settings.model_dump(),
            "angles": {
                "ascendant": {
                    "name": "Ascendant",
                    "absolute_degree": (30 + day_offset) % 360,
                    "sign": "Aries",
                    "degree_in_sign": 0,
                    "element": "Fire",
                    "modality": "Cardinal",
                },
                "midheaven": {
                    "name": "Medium_Coeli",
                    "absolute_degree": mc_degree,
                    "sign": "Cancer",
                    "degree_in_sign": 0,
                    "element": "Water",
                    "modality": "Cardinal",
                },
            },
            "planets": [
                _planet("Sun", sun_degree, 10),
                _planet("Moon", moon_degree, 4),
                _planet("Venus", (150 + day_offset) % 360, 2),
                _planet("Saturn", (210 + day_offset) % 360, 10),
            ],
            "houses": [
                {"house_number": house, "absolute_degree": (house - 1) * 30}
                for house in range(1, 13)
            ],
            "aspects": [],
            "elements_balance": {"Fire": 1},
            "modalities_balance": {"Cardinal": 1},
            "hemispheres": {},
            "dominants": {"element": "Fire", "modality": "Cardinal"},
            "calculation_meta": {"normalized_utc_datetime": "1990-01-01T10:00:00Z"},
        }
        return FakeChart(payload)


def _planet(name: str, degree: float, house: int) -> dict[str, object]:
    return {
        "name": name,
        "sign": "Aries",
        "degree_in_sign": degree % 30,
        "absolute_degree": degree,
        "house": house,
        "element": "Fire",
        "modality": "Cardinal",
        "retrograde": False,
    }


def _birth_data() -> BirthData:
    return BirthData(
        name="Person A",
        birth_date=date(1990, 1, 1),
        birth_time=time(10, 0),
        birth_place="Kyiv, Ukraine",
        latitude=50.45,
        longitude=30.52,
        timezone="Europe/Kyiv",
        settings=ProgressionCalculationSettings(),
    )


def _service(profile_service: ProfileService | None = None) -> ProgressionService:
    return ProgressionService(
        Settings(),
        astrology_engine=FakeAstrologyEngine(),  # type: ignore[arg-type]
        profile_service=profile_service,
    )


def test_progressed_datetime_uses_day_for_year_symbolism() -> None:
    progressed = ProgressionService._progressed_datetime(_birth_data(), 10)

    assert progressed.date().isoformat() == "1990-01-11"


def test_life_period_overview_returns_twelve_seven_year_periods() -> None:
    result = _service().calculate_life_period_overview(
        _birth_data(),
        ProgressionCalculationSettings(),
    )

    assert result["chart_type"] == "life_progressions_overview"
    assert len(result["periods"]) == 12  # type: ignore[arg-type]
    first = result["periods"][0]  # type: ignore[index]
    assert first["period_label"] == "0-7"
    assert "secondary_progressions" in first
    assert "solar_arc_directions" in first
    assert "llm_life_context" in result


def test_life_period_overview_is_deterministic() -> None:
    service = _service()
    settings = ProgressionCalculationSettings(end_age=14)

    first = service.calculate_life_period_overview(_birth_data(), settings)
    second = service.calculate_life_period_overview(_birth_data(), settings)

    assert first == second


def test_progression_settings_reject_invalid_technique() -> None:
    with pytest.raises(ValueError, match="Unsupported progression techniques"):
        _service().calculate_life_period_overview(
            _birth_data(),
            ProgressionCalculationSettings(techniques=["unknown"]),
        )


def test_profile_life_period_overview(profile_service: ProfileService | None = None) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    service = ProfileService(Settings(), session_factory=create_session_factory(engine))
    created = service.create_profile(
        ProfileCreate.model_validate(
            {
                "name": "Андрей",
                "birth_date": "1990-01-01",
                "birth_time": "10:00:00",
                "birth_place": "Kyiv, Ukraine",
                "latitude": 50.45,
                "longitude": 30.52,
                "timezone": "Europe/Kyiv",
            }
        )
    )

    result = _service(service).calculate_profile_life_period_overview(
        str(created["profile_id"]),
        ProgressionCalculationSettings(end_age=14),
    )

    assert result["profile_id"] == created["profile_id"]
    assert len(result["periods"]) == 2  # type: ignore[arg-type]


def test_progression_tools_are_registered_as_mcp_tools() -> None:
    tools = asyncio.run(create_mcp_server(Settings()).list_tools())
    names = {tool.name for tool in tools}

    expected = {
        "calculate_life_progressions",
        "calculate_profile_life_progressions",
        "calculate_life_period_overview",
        "calculate_profile_life_period_overview",
        "astro1_calculate_life_progressions",
        "astro1_calculate_profile_life_progressions",
        "astro1_calculate_life_period_overview",
        "astro1_calculate_profile_life_period_overview",
    }
    assert expected <= names
