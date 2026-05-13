"""Telegram MCP tool wrappers."""

from __future__ import annotations

from astrology_mcp.config import get_settings
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.telegram_notifier import TelegramNotifier, TelegramToolError


def _service() -> TelegramNotifier:
    return TelegramNotifier(get_settings())


def _telegram_error(exc: TelegramToolError) -> dict[str, object]:
    error: dict[str, object] = {
        "status": "error",
        "error_type": exc.error_type,
        "message": exc.message,
        "warnings": [],
    }
    if exc.debug_file_path:
        error["debug_file_path"] = exc.debug_file_path
    return error


@log_tool_call("send_telegram_text_as_pdf")
async def send_telegram_text_as_pdf(
    file_name: str,
    content: str,
    title: str | None = None,
    caption: str | None = None,
) -> dict[str, object]:
    """Create a PDF from text on the server, send it to Telegram, then delete it."""

    try:
        return await _service().create_pdf_from_text_and_send(
            file_name=file_name,
            content=content,
            title=title,
            caption=caption,
        )
    except TelegramToolError as exc:
        return _telegram_error(exc)
