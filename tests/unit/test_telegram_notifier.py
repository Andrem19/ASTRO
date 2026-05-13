import asyncio
import base64
from pathlib import Path
from typing import Any

import pytest

from astrology_mcp.config import Settings
from astrology_mcp.mcp_server import StartupNotificationMiddleware
from astrology_mcp.services.telegram_notifier import TelegramNotifier, TelegramToolError
from astrology_mcp.tools.telegram_tools import send_telegram_message


def test_telegram_notifier_disabled_without_env() -> None:
    notifier = TelegramNotifier(Settings())

    assert notifier.enabled is False


def test_telegram_notifier_builds_send_message_payload() -> None:
    notifier = TelegramNotifier(Settings(ALGO_BOT="bot123:abc", CHAT_ID="42"))

    assert notifier.enabled is True
    assert notifier._telegram_url() == "https://api.telegram.org/bot123:abc/sendMessage"
    assert notifier._payload("ok") == {
        "chat_id": "42",
        "text": "ok",
        "disable_web_page_preview": True,
    }


def test_telegram_file_outbox_validation(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    allowed_file = outbox / "report.md"
    outside_file = tmp_path / "outside.md"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )
    outbox.mkdir()
    allowed_file.write_text("# report", encoding="utf-8")
    outside_file.write_text("# outside", encoding="utf-8")

    assert notifier._validate_file_path(str(allowed_file)) == allowed_file.resolve()
    with pytest.raises(TelegramToolError, match="file_path must be inside"):
        notifier._validate_file_path(str(outside_file))


def test_telegram_unsupported_file_type_is_rejected(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    file_path = outbox / "script.py"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )
    outbox.mkdir()
    file_path.write_text("print('no')", encoding="utf-8")

    with pytest.raises(TelegramToolError) as exc_info:
        notifier._validate_file_path(str(file_path))

    assert exc_info.value.error_type == "invalid_file_type"


def test_telegram_large_file_is_rejected(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    file_path = outbox / "large.md"
    notifier = TelegramNotifier(
        Settings(
            ALGO_BOT="token",
            CHAT_ID="42",
            TELEGRAM_OUTBOX_DIR=str(outbox),
            TELEGRAM_MAX_FILE_SIZE_MB=1,
        )
    )
    outbox.mkdir()
    file_path.write_bytes(b"x" * (1024 * 1024 + 1))

    with pytest.raises(TelegramToolError) as exc_info:
        notifier._validate_file_path(str(file_path))

    assert exc_info.value.error_type == "file_too_large"


def test_telegram_send_message_uses_send_message_endpoint(monkeypatch: Any) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    notifier = TelegramNotifier(Settings(ALGO_BOT="token", CHAT_ID="42"))

    async def fake_post_json(method: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((method, payload))
        return {"ok": True, "result": {"message_id": 7, "chat": {"id": 42}}}

    monkeypatch.setattr(notifier, "_post_json", fake_post_json)

    result = asyncio.run(notifier.send_message("hello"))

    assert calls == [("sendMessage", notifier._payload("hello"))]
    assert result["status"] == "sent"
    assert result["sent_type"] == "message"
    assert result["message_id"] == 7


def test_telegram_document_and_photo_endpoints(monkeypatch: Any, tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    pdf = outbox / "report.pdf"
    image = outbox / "image.png"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )
    outbox.mkdir()
    pdf.write_bytes(b"%PDF")
    image.write_bytes(b"png")
    calls: list[tuple[str, str, str, str | None]] = []

    async def fake_post_file(
        method: str,
        field_name: str,
        path: Path,
        caption: str | None,
    ) -> dict[str, object]:
        calls.append((method, field_name, path.name, caption))
        return {"ok": True, "result": {"message_id": 8, "chat": {"id": 42}}}

    monkeypatch.setattr(notifier, "_post_file", fake_post_file)

    document = asyncio.run(notifier.send_file(str(pdf), caption="doc"))
    photo = asyncio.run(notifier.send_file(str(image), caption="img"))

    assert calls == [
        ("sendDocument", "document", "report.pdf", "doc"),
        ("sendPhoto", "photo", "image.png", "img"),
    ]
    assert document["sent_type"] == "document"
    assert photo["sent_type"] == "photo"


def test_telegram_create_text_file_sends_and_deletes(monkeypatch: Any, tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )
    sent_paths: list[Path] = []

    async def fake_post_file(
        _method: str,
        _field_name: str,
        path: Path,
        _caption: str | None,
    ) -> dict[str, object]:
        sent_paths.append(path)
        assert path.read_text(encoding="utf-8") == "# report"
        return {"ok": True, "result": {"message_id": 9, "chat": {"id": 42}}}

    monkeypatch.setattr(notifier, "_post_file", fake_post_file)

    result = asyncio.run(
        notifier.create_temp_file_and_send("report.md", text_content="# report")
    )

    assert result["file_deleted"] is True
    assert sent_paths
    assert not sent_paths[0].exists()


def test_telegram_create_base64_file_sends_and_deletes(monkeypatch: Any, tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )
    payload = base64.b64encode(b"%PDF").decode("ascii")
    sent_paths: list[Path] = []

    async def fake_post_file(
        _method: str,
        _field_name: str,
        path: Path,
        _caption: str | None,
    ) -> dict[str, object]:
        sent_paths.append(path)
        assert path.read_bytes() == b"%PDF"
        return {"ok": True, "result": {"message_id": 10, "chat": {"id": 42}}}

    monkeypatch.setattr(notifier, "_post_file", fake_post_file)

    result = asyncio.run(
        notifier.create_temp_file_and_send("report.pdf", content_base64=payload)
    )

    assert result["file_deleted"] is True
    assert sent_paths
    assert not sent_paths[0].exists()


def test_telegram_failed_send_keeps_created_file(monkeypatch: Any, tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    notifier = TelegramNotifier(
        Settings(ALGO_BOT="token", CHAT_ID="42", TELEGRAM_OUTBOX_DIR=str(outbox))
    )

    async def fake_post_file(
        _method: str,
        _field_name: str,
        _path: Path,
        _caption: str | None,
    ) -> dict[str, object]:
        raise TelegramToolError("telegram_api_error", "failed")

    monkeypatch.setattr(notifier, "_post_file", fake_post_file)

    with pytest.raises(TelegramToolError) as exc_info:
        asyncio.run(notifier.create_temp_file_and_send("report.md", text_content="# report"))

    assert exc_info.value.debug_file_path is not None
    assert Path(exc_info.value.debug_file_path).exists()


def test_telegram_tool_reports_not_configured() -> None:
    result = asyncio.run(send_telegram_message(text="hello"))

    assert result["status"] == "error"
    assert result["error_type"] == "telegram_not_configured"


def test_startup_notification_middleware_sends_success(monkeypatch: Any) -> None:
    calls: list[str] = []

    async def fake_success(self: TelegramNotifier) -> None:
        calls.append("success")

    monkeypatch.setattr(TelegramNotifier, "send_startup_success", fake_success)

    async def lifespan_app(_scope: dict[str, Any], _receive: Any, send: Any) -> None:
        await send({"type": "lifespan.startup.complete"})

    async def run() -> None:
        messages: list[dict[str, Any]] = []
        app = StartupNotificationMiddleware(
            lifespan_app,
            Settings(ALGO_BOT="token", CHAT_ID="42"),
        )

        async def receive() -> dict[str, Any]:
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        await app({"type": "lifespan"}, receive, send)
        await asyncio.sleep(0)
        assert messages == [{"type": "lifespan.startup.complete"}]

    asyncio.run(run())
    assert calls == ["success"]


def test_startup_notification_middleware_sends_failure(monkeypatch: Any) -> None:
    calls: list[str] = []

    async def fake_failure(self: TelegramNotifier, error: BaseException | str) -> None:
        calls.append(str(error))

    monkeypatch.setattr(TelegramNotifier, "send_startup_failure", fake_failure)

    async def failing_app(_scope: dict[str, Any], _receive: Any, _send: Any) -> None:
        raise RuntimeError("boom")

    async def run() -> None:
        app = StartupNotificationMiddleware(
            failing_app,
            Settings(ALGO_BOT="token", CHAT_ID="42"),
        )

        async def receive() -> dict[str, Any]:
            return {"type": "lifespan.startup"}

        async def send(_message: dict[str, Any]) -> None:
            return None

        try:
            await app({"type": "lifespan"}, receive, send)
        except RuntimeError:
            await asyncio.sleep(0)

    asyncio.run(run())
    assert calls == ["boom"]
