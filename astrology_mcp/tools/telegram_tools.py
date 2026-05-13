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


@log_tool_call("send_telegram_text")
async def send_telegram_text(text: str) -> dict[str, object]:
    """Send a plain Telegram text message to CHAT_ID from .env."""

    try:
        return await _service().send_message(text)
    except TelegramToolError as exc:
        return _telegram_error(exc)


@log_tool_call("send_telegram_markdown")
async def send_telegram_markdown(
    file_name: str,
    markdown: str,
    caption: str | None = None,
) -> dict[str, object]:
    """Create a temporary .md file, send it to Telegram, and delete it after success."""

    try:
        return await _service().create_temp_file_and_send(
            file_name=file_name,
            text_content=markdown,
            caption=caption,
        )
    except TelegramToolError as exc:
        return _telegram_error(exc)


@log_tool_call("send_telegram_pdf")
async def send_telegram_pdf(
    file_name: str,
    pdf_base64: str,
    caption: str | None = None,
) -> dict[str, object]:
    """Create a temporary PDF from base64, send it to Telegram, and delete it after success."""

    try:
        return await _service().create_temp_file_and_send(
            file_name=file_name,
            content_base64=pdf_base64,
            caption=caption,
        )
    except TelegramToolError as exc:
        return _telegram_error(exc)


@log_tool_call("send_telegram_image")
async def send_telegram_image(
    file_name: str,
    image_base64: str,
    caption: str | None = None,
) -> dict[str, object]:
    """Create a temporary image from base64, send it as Telegram photo, and delete it."""

    try:
        return await _service().create_temp_file_and_send(
            file_name=file_name,
            content_base64=image_base64,
            caption=caption,
        )
    except TelegramToolError as exc:
        return _telegram_error(exc)


@log_tool_call("telegram_outbox_info")
def telegram_outbox_info() -> dict[str, object]:
    """Return Telegram file outbox settings for advanced existing-file sends."""

    settings = get_settings()
    return {
        "status": "ok",
        "outbox_dir": settings.telegram_outbox_dir,
        "allowed_extensions": [".pdf", ".md", ".png", ".jpg", ".jpeg", ".webp"],
        "max_file_size_mb": settings.telegram_max_file_size_mb,
    }

