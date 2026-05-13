"""Health and capability MCP tools."""

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import (
    HealthResponse,
    ServerInfoResponse,
    SupportedFeaturesResponse,
)
from astrology_mcp.logging import log_tool_call

PLANNED_TOOLS = [
    "calculate_natal_chart",
    "create_profile",
    "get_profile",
    "get_profile_by_name",
    "list_profiles",
    "update_profile",
    "delete_profile",
    "calculate_profile_natal_chart",
    "clear_profile_chart_cache",
    "calculate_synastry",
    "calculate_profile_synastry",
    "calculate_relationship_summary",
    "generate_synastry_chart_svg",
    "calculate_transits",
    "calculate_profile_transits",
    "calculate_month_forecast",
    "calculate_year_forecast",
    "calculate_profile_month_forecast",
    "calculate_profile_year_forecast",
    "calculate_profile_day_forecast",
    "generate_transit_chart_svg",
    "send_telegram_text",
    "send_telegram_markdown",
    "send_telegram_pdf",
    "send_telegram_image",
    "telegram_outbox_info",
]


@log_tool_call("health_check")
def health_check(settings: Settings | None = None) -> dict[str, object]:
    app_version = settings.app_version if settings else "0.1.0"
    return HealthResponse(version=app_version).model_dump()


@log_tool_call("server_info")
def server_info(settings: Settings | None = None) -> dict[str, object]:
    app_name = settings.app_name if settings else "astrology-mcp-server"
    return ServerInfoResponse(name=app_name).model_dump()


@log_tool_call("list_supported_features")
def list_supported_features() -> dict[str, object]:
    return SupportedFeaturesResponse(planned_tools=PLANNED_TOOLS).model_dump()
