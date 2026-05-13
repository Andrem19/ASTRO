"""Telegram notifications for Linux service lifecycle events."""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path
from typing import cast

import httpx

from astrology_mcp.config import Settings

LOGGER = logging.getLogger(__name__)
TELEGRAM_TIMEOUT_SECONDS = 5.0
DOCUMENT_EXTENSIONS = {".pdf", ".md"}
PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | PHOTO_EXTENSIONS


class TelegramToolError(ValueError):
    def __init__(
        self,
        error_type: str,
        message: str,
        debug_file_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.debug_file_path = debug_file_path


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self._settings.algo_bot and self._settings.chat_id)

    async def send_startup_success(self) -> None:
        await self._send("astro-mcp перезапущен успешно")

    async def send_startup_failure(self, error: BaseException | str) -> None:
        error_text = type(error).__name__ if isinstance(error, BaseException) else error
        await self._send(f"astro-mcp неуспешный запуск: {error_text}")

    async def send_message(self, text: str) -> dict[str, object]:
        if not text.strip():
            raise TelegramToolError("invalid_request", "text must not be empty")
        response = await self._post_json("sendMessage", self._payload(text))
        return self._success_response(response, "message")

    async def send_file(self, file_path: str, caption: str | None = None) -> dict[str, object]:
        path = self._validate_file_path(file_path)
        endpoint = "sendPhoto" if path.suffix.lower() in PHOTO_EXTENSIONS else "sendDocument"
        field_name = "photo" if endpoint == "sendPhoto" else "document"
        response = await self._post_file(endpoint, field_name, path, caption)
        return self._success_response(response, "photo" if endpoint == "sendPhoto" else "document")

    async def create_temp_file_and_send(
        self,
        file_name: str,
        text_content: str | None = None,
        content_base64: str | None = None,
        caption: str | None = None,
    ) -> dict[str, object]:
        path = self._create_outbox_file(file_name, text_content, content_base64)
        try:
            result = await self.send_file(str(path), caption=caption)
        except Exception as exc:
            if isinstance(exc, TelegramToolError):
                exc.debug_file_path = str(path)
            raise
        path.unlink(missing_ok=True)
        return {**result, "file_deleted": True}

    def send_startup_failure_sync(self, error: BaseException | str) -> None:
        if not self.enabled:
            return
        try:
            httpx.post(
                self._telegram_url("sendMessage"),
                json=self._payload(
                    f"astro-mcp неуспешный запуск: "
                    f"{type(error).__name__ if isinstance(error, BaseException) else error}"
                ),
                timeout=TELEGRAM_TIMEOUT_SECONDS,
            )
        except Exception:
            LOGGER.warning("telegram_startup_failure_notification_failed", exc_info=True)

    async def _send(self, text: str) -> None:
        if not self.enabled:
            return
        try:
            await self._post_json("sendMessage", self._payload(text))
        except Exception:
            LOGGER.warning("telegram_notification_failed", exc_info=True)

    def _telegram_url(self, method: str = "sendMessage") -> str:
        token = str(self._settings.algo_bot or "").strip()
        if token.startswith("bot"):
            token = token[3:]
        return f"https://api.telegram.org/bot{token}/{method}"

    def _payload(self, text: str) -> dict[str, object]:
        return {
            "chat_id": str(self._settings.chat_id),
            "text": text,
            "disable_web_page_preview": True,
        }

    async def _post_json(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        self._ensure_enabled()
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT_SECONDS) as client:
            response = await client.post(self._telegram_url(method), json=payload)
        return self._parse_response(response)

    async def _post_file(
        self,
        method: str,
        field_name: str,
        path: Path,
        caption: str | None,
    ) -> dict[str, object]:
        self._ensure_enabled()
        data: dict[str, object] = {"chat_id": str(self._settings.chat_id)}
        if caption:
            data["caption"] = caption
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT_SECONDS) as client:
            with path.open("rb") as file_handle:
                response = await client.post(
                    self._telegram_url(method),
                    data=data,
                    files={field_name: (path.name, file_handle)},
                )
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, object]:
        try:
            payload = cast(dict[str, object], response.json())
        except ValueError as exc:
            raise TelegramToolError(
                "telegram_api_error",
                f"Telegram returned non-JSON response with status {response.status_code}",
            ) from exc
        if response.status_code >= 400 or payload.get("ok") is not True:
            description = str(payload.get("description") or f"HTTP {response.status_code}")
            raise TelegramToolError("telegram_api_error", description)
        return payload

    @staticmethod
    def _success_response(response: dict[str, object], sent_type: str) -> dict[str, object]:
        result = response.get("result")
        message_id = result.get("message_id") if isinstance(result, dict) else None
        chat = result.get("chat") if isinstance(result, dict) else None
        chat_id = chat.get("id") if isinstance(chat, dict) else "from_env"
        return {
            "status": "sent",
            "message_id": message_id,
            "chat_id": str(chat_id),
            "sent_type": sent_type,
            "file_deleted": False,
            "warnings": [],
        }

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise TelegramToolError(
                "telegram_not_configured",
                "ALGO_BOT and CHAT_ID must be configured",
            )

    def _validate_file_path(self, file_path: str) -> Path:
        outbox = self._ensure_outbox_dir()
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        resolved = path.resolve()
        if not resolved.is_relative_to(outbox):
            raise TelegramToolError(
                "invalid_file_path",
                "file_path must be inside TELEGRAM_OUTBOX_DIR",
            )
        if not resolved.exists() or not resolved.is_file():
            raise TelegramToolError("file_not_found", "file_path does not exist")
        self._validate_file_metadata(resolved)
        return resolved

    def _create_outbox_file(
        self,
        file_name: str,
        text_content: str | None,
        content_base64: str | None,
    ) -> Path:
        if bool(text_content is not None) == bool(content_base64 is not None):
            raise TelegramToolError(
                "invalid_request",
                "Provide exactly one of text_content or content_base64",
            )
        outbox = self._ensure_outbox_dir()
        safe_name = f"{uuid.uuid4().hex}_{Path(file_name).name}"
        path = (outbox / safe_name).resolve()
        if not path.is_relative_to(outbox):
            raise TelegramToolError("invalid_file_path", "file_name must stay inside outbox")
        self._validate_file_extension(path)
        if text_content is not None:
            path.write_text(text_content, encoding="utf-8")
        else:
            try:
                path.write_bytes(base64.b64decode(str(content_base64), validate=True))
            except ValueError as exc:
                raise TelegramToolError("invalid_base64", "content_base64 is invalid") from exc
        self._validate_file_metadata(path)
        return path

    def _ensure_outbox_dir(self) -> Path:
        outbox = Path(self._settings.telegram_outbox_dir)
        if not outbox.is_absolute():
            outbox = Path.cwd() / outbox
        outbox = outbox.resolve()
        outbox.mkdir(mode=0o700, parents=True, exist_ok=True)
        outbox.chmod(0o700)
        return outbox

    def _validate_file_metadata(self, path: Path) -> None:
        self._validate_file_extension(path)
        max_bytes = self._settings.telegram_max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise TelegramToolError("file_too_large", "file exceeds TELEGRAM_MAX_FILE_SIZE_MB")

    @staticmethod
    def _validate_file_extension(path: Path) -> None:
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise TelegramToolError("invalid_file_type", "Unsupported Telegram file type")
