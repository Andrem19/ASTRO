"""Telegram MCP tool wrappers."""

from __future__ import annotations

from astrology_mcp.config import get_settings
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.telegram_notifier import TelegramNotifier, TelegramToolError


def _service() -> TelegramNotifier:
    return TelegramNotifier(get_settings())


@log_tool_call("send_telegram_message")
async def send_telegram_message(
    text: str | None = None,
    file_path: str | None = None,
    file_name: str | None = None,
    text_content: str | None = None,
    content_base64: str | None = None,
    caption: str | None = None,
) -> dict[str, object]:
    try:
        return await _send_telegram_message(
            text=text,
            file_path=file_path,
            file_name=file_name,
            text_content=text_content,
            content_base64=content_base64,
            caption=caption,
        )
    except TelegramToolError as exc:
        error: dict[str, object] = {
            "status": "error",
            "error_type": exc.error_type,
            "message": exc.message,
            "warnings": [],
        }
        if exc.debug_file_path:
            error["debug_file_path"] = exc.debug_file_path
        return error


async def _send_telegram_message(
    text: str | None,
    file_path: str | None,
    file_name: str | None,
    text_content: str | None,
    content_base64: str | None,
    caption: str | None,
) -> dict[str, object]:
    service = _service()
    has_existing_file = file_path is not None
    has_created_file = (
        file_name is not None or text_content is not None or content_base64 is not None
    )
    if has_existing_file and has_created_file:
        raise TelegramToolError(
            "invalid_request",
            "Use either file_path or file_name with content, not both",
        )
    if has_created_file:
        if file_name is None:
            raise TelegramToolError("invalid_request", "file_name is required with file content")
        file_caption = caption or text
        return await service.create_temp_file_and_send(
            file_name=file_name,
            text_content=text_content,
            content_base64=content_base64,
            caption=file_caption,
        )
    if has_existing_file:
        file_caption = caption or text
        return await service.send_file(str(file_path), caption=file_caption)
    if text:
        return await service.send_message(text)
    raise TelegramToolError("invalid_request", "Provide text, file_path, or file content")
