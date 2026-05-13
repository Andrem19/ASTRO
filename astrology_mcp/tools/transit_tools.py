"""Transit and forecast MCP tool wrappers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from astrology_mcp.config import get_settings
from astrology_mcp.domain.models import BirthData, ForecastCalculationSettings
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.transit_service import TransitService


def _service() -> TransitService:
    return TransitService(get_settings())


def _settings(
    payload: dict[str, object] | None,
    default_sampling: str,
) -> ForecastCalculationSettings:
    data = dict(payload or {})
    data.setdefault("sampling", default_sampling)
    return ForecastCalculationSettings.model_validate(data)


def _datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(ZoneInfo("UTC"))


@log_tool_call("calculate_transits")
def calculate_transits(
    natal: dict[str, object],
    transit_datetime: str,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "daily")
    birth_data = BirthData.model_validate({**natal, "settings": forecast_settings.model_dump()})
    return _service().calculate_transits(birth_data, _datetime(transit_datetime), forecast_settings)


@log_tool_call("calculate_profile_transits")
def calculate_profile_transits(
    profile_id: str,
    transit_datetime: str,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "daily")
    return _service().calculate_profile_transits(
        profile_id,
        _datetime(transit_datetime),
        forecast_settings,
    )


@log_tool_call("calculate_month_forecast")
def calculate_month_forecast(
    natal: dict[str, object],
    year: int,
    month: int,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "daily")
    birth_data = BirthData.model_validate({**natal, "settings": forecast_settings.model_dump()})
    return _service().calculate_month_forecast(birth_data, year, month, forecast_settings)


@log_tool_call("calculate_year_forecast")
def calculate_year_forecast(
    natal: dict[str, object],
    year: int,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "weekly")
    forecast_settings.include_lunar_transits = bool(
        (settings or {}).get("include_lunar_transits", False)
    )
    birth_data = BirthData.model_validate({**natal, "settings": forecast_settings.model_dump()})
    return _service().calculate_year_forecast(birth_data, year, forecast_settings)


@log_tool_call("calculate_profile_month_forecast")
def calculate_profile_month_forecast(
    profile_id: str,
    year: int,
    month: int,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "daily")
    return _service().calculate_profile_month_forecast(profile_id, year, month, forecast_settings)


@log_tool_call("calculate_profile_year_forecast")
def calculate_profile_year_forecast(
    profile_id: str,
    year: int,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "weekly")
    forecast_settings.include_lunar_transits = bool(
        (settings or {}).get("include_lunar_transits", False)
    )
    return _service().calculate_profile_year_forecast(profile_id, year, forecast_settings)


@log_tool_call("generate_transit_chart_svg")
def generate_transit_chart_svg(
    natal: dict[str, object] | None = None,
    profile_id: str | None = None,
    transit_datetime: str = "2026-06-01T12:00:00Z",
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    forecast_settings = _settings(settings, "daily")
    service = _service()
    if profile_id:
        result = service.calculate_profile_transits(
            profile_id,
            _datetime(transit_datetime),
            forecast_settings,
        )
    elif natal is not None:
        birth_data = BirthData.model_validate({**natal, "settings": forecast_settings.model_dump()})
        result = service.calculate_transits(
            birth_data,
            _datetime(transit_datetime),
            forecast_settings,
        )
    else:
        raise ValueError("Provide natal birth data or profile_id")
    return service.generate_transit_chart_svg(result)
