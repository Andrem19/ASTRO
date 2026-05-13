from typing import Any

import pytest
from sqlalchemy import create_engine

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, ProfileCreate, SynastryCalculationSettings
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.services.synastry_service import SynastryService
from astrology_mcp.storage.database import create_session_factory
from astrology_mcp.storage.models import Base


def _person_a() -> dict[str, Any]:
    return {
        "name": "Person A",
        "birth_date": "1990-05-17",
        "birth_time": "14:35:00",
        "birth_place": "London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
    }


def _person_b() -> dict[str, Any]:
    return {
        "name": "Person B",
        "birth_date": "1992-09-03",
        "birth_time": "08:10:00",
        "birth_place": "Paris, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
    }


def _settings(include_minor_aspects: bool = False) -> SynastryCalculationSettings:
    return SynastryCalculationSettings(
        house_system="Placidus",
        zodiac_type="tropical",
        include_minor_aspects=include_minor_aspects,
        max_orb=8,
    )


@pytest.fixture
def profile_service() -> ProfileService:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return ProfileService(Settings(), session_factory=create_session_factory(engine))


def _synastry_service(profile_service: ProfileService | None = None) -> SynastryService:
    return SynastryService(Settings(), profile_service=profile_service)


def _calculate_raw(include_minor_aspects: bool = False) -> dict[str, object]:
    return _synastry_service().calculate_synastry(
        BirthData.model_validate({**_person_a(), "settings": _settings().model_dump()}),
        BirthData.model_validate({**_person_b(), "settings": _settings().model_dump()}),
        _settings(include_minor_aspects=include_minor_aspects),
    )


def test_synastry_from_raw_birth_data() -> None:
    result = _calculate_raw()

    assert result["chart_type"] == "synastry"
    assert result["person_a"]["name"] == "Person A"  # type: ignore[index]
    assert result["person_b"]["name"] == "Person B"  # type: ignore[index]


def test_synastry_from_profile_ids(profile_service: ProfileService) -> None:
    profile_a = profile_service.create_profile(ProfileCreate.model_validate(_person_a()))
    profile_b = profile_service.create_profile(ProfileCreate.model_validate(_person_b()))

    result = _synastry_service(profile_service).calculate_profile_synastry(
        str(profile_a["profile_id"]),
        str(profile_b["profile_id"]),
        _settings(),
    )

    assert result["chart_type"] == "synastry"
    assert result["cache"] == {"hit": False, "use_cache": True}


def test_profile_synastry_missing_profile(profile_service: ProfileService) -> None:
    with pytest.raises(ValueError, match="Profile not found"):
        _synastry_service(profile_service).calculate_profile_synastry(
            "missing-a",
            "missing-b",
            _settings(),
        )


def test_inter_chart_aspects_present() -> None:
    result = _calculate_raw()

    assert result["inter_chart_aspects"]


def test_relationship_themes_present() -> None:
    result = _calculate_raw()
    themes = result["relationship_themes"]

    assert "emotional_connection" in themes  # type: ignore[operator]
    assert "growth_points" in themes  # type: ignore[operator]


def test_compatibility_scores_present() -> None:
    result = _calculate_raw()
    scores = result["compatibility_scores"]

    assert set(scores) == {  # type: ignore[arg-type]
        "overall",
        "emotional",
        "mental",
        "romantic",
        "stability",
        "challenge",
    }
    assert scores["challenge"]["explanation"]  # type: ignore[index]


def test_score_stability_for_same_input() -> None:
    first = _calculate_raw()["compatibility_scores"]
    second = _calculate_raw()["compatibility_scores"]

    assert first == second


def test_minor_aspects_are_included_when_enabled() -> None:
    major_only = _calculate_raw(include_minor_aspects=False)
    with_minor = _calculate_raw(include_minor_aspects=True)

    major_count = len(major_only["inter_chart_aspects"])  # type: ignore[arg-type]
    minor_count = len(with_minor["inter_chart_aspects"])  # type: ignore[arg-type]
    aspect_types = {
        aspect["aspect_type"] for aspect in with_minor["inter_chart_aspects"]  # type: ignore[index]
    }

    assert minor_count >= major_count
    assert {"semi-sextile", "quincunx"} & aspect_types


def test_svg_generation_smoke() -> None:
    result = _calculate_raw()
    svg = _synastry_service().generate_synastry_chart_svg(result)

    assert svg["status"] == "ok"
    assert str(svg["svg"]).startswith("<svg")


def test_relationship_summary_shape() -> None:
    result = _calculate_raw()
    summary = _synastry_service().calculate_relationship_summary(result)

    assert "main_strengths" in summary
    assert summary["llm_prompt_context"]["recommended_tone"] == (  # type: ignore[index]
        "balanced, non-deterministic, respectful"
    )
