"""Natal chart MCP tool wrappers."""

from astrology_mcp.config import get_settings
from astrology_mcp.domain.models import BirthData
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.astrology_engine import AstrologyEngine


@log_tool_call("calculate_natal_chart")
def calculate_natal_chart(
    name: str,
    birth_date: str,
    birth_time: str,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: str | None = None,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    birth_data = BirthData.model_validate(
        {
            "name": name,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "settings": settings or {},
        }
    )
    return AstrologyEngine(get_settings()).calculate_natal_chart(birth_data).model_dump()
