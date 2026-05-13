from astrology_mcp.config import Settings
from astrology_mcp.tools.health_tools import health_check, list_supported_features, server_info


def test_health_check_returns_status_ok() -> None:
    response = health_check(Settings())

    assert response == {
        "status": "ok",
        "service": "astrology-mcp-server",
        "version": "0.1.0",
        "environment": "astro",
    }


def test_server_info_returns_expected_structure() -> None:
    response = server_info(Settings())

    assert response["name"] == "astrology-mcp-server"
    assert response["transport"] == "streamable_http"
    assert response["runtime"] == {"python_environment": "astro"}
    assert response["features"] == {
        "natal_chart": True,
        "profiles": True,
        "synastry": True,
        "transits": True,
        "forecast": True,
    }


def test_list_supported_features_returns_planned_tools() -> None:
    response = list_supported_features()

    assert response["planned_tools"] == [
        "calculate_natal_chart",
        "create_profile",
        "get_profile",
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
        "send_telegram_message",
    ]
