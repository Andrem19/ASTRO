"""Progression and direction MCP tool wrappers."""

from __future__ import annotations

from astrology_mcp.config import get_settings
from astrology_mcp.domain.models import BirthData, ProgressionCalculationSettings
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.progression_service import ProgressionService


def _service() -> ProgressionService:
    return ProgressionService(get_settings())


def _settings(payload: dict[str, object] | None) -> ProgressionCalculationSettings:
    return ProgressionCalculationSettings.model_validate(payload or {})


@log_tool_call("calculate_life_progressions")
def calculate_life_progressions(
    natal: dict[str, object],
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    progression_settings = _settings(settings)
    birth_data = BirthData.model_validate(
        {**natal, "settings": progression_settings.model_dump()}
    )
    return _service().calculate_life_period_overview(birth_data, progression_settings)


@log_tool_call("calculate_profile_life_progressions")
def calculate_profile_life_progressions(
    profile_id: str,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    return _service().calculate_profile_life_period_overview(profile_id, _settings(settings))


@log_tool_call("calculate_life_period_overview")
def calculate_life_period_overview(
    natal: dict[str, object],
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    return calculate_life_progressions(natal, settings)


@log_tool_call("calculate_profile_life_period_overview")
def calculate_profile_life_period_overview(
    profile_id: str,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    return calculate_profile_life_progressions(profile_id, settings)
