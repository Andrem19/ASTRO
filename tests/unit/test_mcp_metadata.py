import asyncio

from astrology_mcp.config import Settings
from astrology_mcp.mcp_server import create_mcp_server
from astrology_mcp.tools.metadata import TOOL_GUIDE_URI, TOOL_ROUTING_PROMPT_NAME


def _tools_by_name() -> dict[str, object]:
    tools = asyncio.run(create_mcp_server(Settings()).list_tools())
    return {tool.name: tool for tool in tools}


def test_all_mcp_tools_have_agent_facing_descriptions() -> None:
    tools_by_name = _tools_by_name()

    assert tools_by_name
    assert all(getattr(tool, "description", "") for tool in tools_by_name.values())
    assert all(getattr(tool, "title", "") for tool in tools_by_name.values())
    assert all(getattr(tool, "tags", set()) for tool in tools_by_name.values())


def test_life_overview_tools_are_distinct_from_natal_tools() -> None:
    tools_by_name = _tools_by_name()

    life_description = tools_by_name["calculate_profile_life_period_overview"].description
    natal_description = tools_by_name["calculate_profile_natal_chart"].description

    assert "full life path overview" in life_description
    assert "progressions" in life_description
    assert "directions" in life_description
    assert "Do not use this alone for a full life path overview" in natal_description


def test_telegram_pdf_tool_description_explains_delivery() -> None:
    tool = _tools_by_name()["send_telegram_text_as_pdf"]

    assert "PDF" in tool.description
    assert "Telegram" in tool.description
    assert "full final text" in tool.description


def test_tool_routing_resource_is_registered_and_readable() -> None:
    server = create_mcp_server(Settings())
    resources = asyncio.run(server.list_resources())
    resource_uris = {str(resource.uri) for resource in resources}

    assert TOOL_GUIDE_URI in resource_uris

    result = asyncio.run(server.read_resource(TOOL_GUIDE_URI))
    content = result.contents[0].content

    assert "Full life path overview" in content or "full life path overview" in content
    assert "calculate_profile_life_period_overview" in content
    assert "send_telegram_text_as_pdf" in content
    assert "Do not answer these requests with only a natal chart" in content


def test_tool_routing_prompt_is_registered() -> None:
    prompts = asyncio.run(create_mcp_server(Settings()).list_prompts())
    prompt_names = {prompt.name for prompt in prompts}

    assert TOOL_ROUTING_PROMPT_NAME in prompt_names
