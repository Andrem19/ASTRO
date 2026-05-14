"""Agent-facing MCP metadata and routing guidance."""

from dataclasses import dataclass

TOOL_GUIDE_URI = "astro://tool-guide"
TOOL_ROUTING_PROMPT_NAME = "astro_tool_routing_guide"


@dataclass(frozen=True)
class ToolMetadata:
    title: str
    description: str
    tags: set[str]


TOOL_METADATA: dict[str, ToolMetadata] = {
    "health_check": ToolMetadata(
        title="Health check",
        description="Check that the astrology MCP server is running and return service status.",
        tags={"system"},
    ),
    "server_info": ToolMetadata(
        title="Server information",
        description=(
            "Return transport, runtime, and feature information for this astrology MCP server."
        ),
        tags={"system", "discovery"},
    ),
    "list_supported_features": ToolMetadata(
        title="Supported features",
        description="List the astrology capabilities and public tools exposed by this MCP server.",
        tags={"system", "discovery"},
    ),
    "calculate_natal_chart": ToolMetadata(
        title="Calculate natal chart",
        description=(
            "Use for a birth chart, personality baseline, planets, houses, angles, and aspects "
            "from raw birth data. Do not use this alone for a full life path overview."
        ),
        tags={"natal", "raw-birth-data"},
    ),
    "create_profile": ToolMetadata(
        title="Create birth profile",
        description=(
            "Create a reusable saved profile from birth data before profile-based chart, "
            "forecast, synastry, or life overview work."
        ),
        tags={"profiles", "birth-data"},
    ),
    "get_profile": ToolMetadata(
        title="Get profile by ID",
        description=(
            "Fetch one saved birth profile by profile_id; use before profile-based calculations."
        ),
        tags={"profiles"},
    ),
    "get_profile_by_name": ToolMetadata(
        title="Find profile by name",
        description=(
            "Find a saved profile by case-insensitive name. Use when the user names a person "
            "but does not provide profile_id."
        ),
        tags={"profiles", "lookup"},
    ),
    "list_profiles": ToolMetadata(
        title="List profiles",
        description="List saved birth profiles, excluding private notes by default.",
        tags={"profiles", "lookup"},
    ),
    "update_profile": ToolMetadata(
        title="Update profile",
        description="Update saved birth profile fields such as birth data, tags, or notes.",
        tags={"profiles"},
    ),
    "delete_profile": ToolMetadata(
        title="Delete profile",
        description="Soft-delete a saved birth profile by profile_id.",
        tags={"profiles"},
    ),
    "calculate_profile_natal_chart": ToolMetadata(
        title="Calculate profile natal chart",
        description=(
            "Use for a saved profile's birth chart and personality baseline. Do not use this "
            "alone for a full life path overview."
        ),
        tags={"natal", "profiles"},
    ),
    "clear_profile_chart_cache": ToolMetadata(
        title="Clear profile chart cache",
        description="Clear cached natal chart calculations for a saved profile.",
        tags={"profiles", "cache"},
    ),
    "calculate_synastry": ToolMetadata(
        title="Calculate synastry",
        description=(
            "Compare two people from raw birth data for relationship compatibility, aspects, "
            "themes, and scoring."
        ),
        tags={"synastry", "raw-birth-data", "relationships"},
    ),
    "calculate_profile_synastry": ToolMetadata(
        title="Calculate profile synastry",
        description=(
            "Compare two saved profiles for relationship compatibility. Prefer this when both "
            "people already have profiles."
        ),
        tags={"synastry", "profiles", "relationships"},
    ),
    "calculate_relationship_summary": ToolMetadata(
        title="Summarize relationship",
        description=(
            "Convert a synastry result into structured LLM context for a relationship reading; "
            "call after calculate_synastry or calculate_profile_synastry."
        ),
        tags={"synastry", "relationships", "summary"},
    ),
    "generate_synastry_chart_svg": ToolMetadata(
        title="Generate synastry SVG",
        description="Generate an SVG visual chart for a synastry comparison.",
        tags={"synastry", "svg", "relationships"},
    ),
    "calculate_transits": ToolMetadata(
        title="Calculate transits",
        description=(
            "Calculate current or specified-date transits against raw natal birth data for a "
            "specific datetime."
        ),
        tags={"transits", "raw-birth-data"},
    ),
    "calculate_profile_transits": ToolMetadata(
        title="Calculate profile transits",
        description="Calculate current or specified-date transits for a saved profile.",
        tags={"transits", "profiles"},
    ),
    "calculate_month_forecast": ToolMetadata(
        title="Calculate month forecast",
        description=(
            "Build a month forecast from raw natal birth data, including timeline and themes."
        ),
        tags={"forecast", "monthly", "raw-birth-data"},
    ),
    "calculate_year_forecast": ToolMetadata(
        title="Calculate year forecast",
        description=(
            "Build a year forecast from raw natal birth data, including timeline and themes."
        ),
        tags={"forecast", "yearly", "raw-birth-data"},
    ),
    "calculate_profile_month_forecast": ToolMetadata(
        title="Calculate profile month forecast",
        description=(
            "Build a month forecast for a saved profile. Prefer this for named/profile users."
        ),
        tags={"forecast", "monthly", "profiles"},
    ),
    "calculate_profile_year_forecast": ToolMetadata(
        title="Calculate profile year forecast",
        description=(
            "Build a year forecast for a saved profile. Prefer this for named/profile users."
        ),
        tags={"forecast", "yearly", "profiles"},
    ),
    "calculate_profile_day_forecast": ToolMetadata(
        title="Calculate profile day forecast",
        description=(
            "Build structured material for a one-day forecast for a saved profile and date; "
            "the agent writes the final user-facing interpretation."
        ),
        tags={"forecast", "daily", "profiles"},
    ),
    "generate_transit_chart_svg": ToolMetadata(
        title="Generate transit SVG",
        description=(
            "Generate an SVG visual chart for a transit calculation using raw birth data "
            "or profile_id."
        ),
        tags={"transits", "svg"},
    ),
    "calculate_life_progressions": ToolMetadata(
        title="Calculate life progressions",
        description=(
            "Use for a full life path overview, life periods, secondary progressions, and solar "
            "arc directions from raw natal birth data."
        ),
        tags={"life-overview", "progressions", "directions", "raw-birth-data"},
    ),
    "calculate_profile_life_progressions": ToolMetadata(
        title="Calculate profile life progressions",
        description=(
            "Use for a full life path overview, life periods, secondary progressions, and solar "
            "arc directions for a saved profile."
        ),
        tags={"life-overview", "progressions", "directions", "profiles"},
    ),
    "calculate_life_period_overview": ToolMetadata(
        title="Calculate life period overview",
        description=(
            "Preferred raw-birth-data tool for full life path overview requests: life periods, "
            "progressions, directions, and long-range development themes."
        ),
        tags={"life-overview", "progressions", "directions", "raw-birth-data"},
    ),
    "calculate_profile_life_period_overview": ToolMetadata(
        title="Calculate profile life period overview",
        description=(
            "Preferred profile tool for full life path overview requests: life periods, "
            "progressions, directions, and long-range development themes."
        ),
        tags={"life-overview", "progressions", "directions", "profiles"},
    ),
    "send_telegram_text_as_pdf": ToolMetadata(
        title="Send Telegram PDF",
        description=(
            "Create a PDF from the agent's full final text, send it to Telegram, then delete "
            "the temporary file. Use when the user asks to send, export, or deliver a PDF."
        ),
        tags={"telegram", "pdf", "delivery"},
    ),
}


ASTRO_TOOL_GUIDE = """# Astro MCP Tool Routing Guide

Use this guide to choose tools on the `astro1` MCP server.

## Core rules

- For a birth chart, natal chart, personality baseline, planets, houses, angles, or aspects:
  use `calculate_profile_natal_chart` when a profile exists, otherwise `calculate_natal_chart`.
- For a full life path overview, life periods, long-range development, secondary progressions,
  or solar arc directions: use `calculate_profile_life_period_overview` when a profile exists,
  otherwise `calculate_life_period_overview`. Do not answer these requests with only a natal chart.
- For daily, monthly, or yearly forecasts: use the matching forecast tool. Prefer profile tools
  when the person has a saved profile.
- For relationship compatibility: use `calculate_profile_synastry` for saved profiles or
  `calculate_synastry` for raw birth data, then call `calculate_relationship_summary` when you
  need structured interpretation context.
- For Telegram PDF delivery: first write the complete final text, then call
  `send_telegram_text_as_pdf` with `file_name`, `content`, optional `title`, and optional `caption`.

## Profile lookup pattern

When the user names a person but does not provide `profile_id`, call `get_profile_by_name`.
If no profile exists and the user supplied birth data, create one with `create_profile` or use
raw-data tools directly.
"""


def tool_metadata(name: str) -> ToolMetadata:
    return TOOL_METADATA[name]
