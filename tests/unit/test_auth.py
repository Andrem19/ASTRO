import asyncio
from typing import Any

from astrology_mcp.config import Settings
from astrology_mcp.mcp_server import ApiKeyAuthMiddleware


async def _empty_receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _ok_app(_scope: dict[str, Any], _receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _run_request(headers: list[tuple[bytes, bytes]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    settings = Settings(API_AUTH_ENABLED=True, API_KEYS="valid-key")
    app = ApiKeyAuthMiddleware(_ok_app, settings)

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {"type": "http", "headers": headers}
    asyncio.run(app(scope, _empty_receive, send))
    return messages


def test_authorization_allows_valid_api_key() -> None:
    messages = _run_request([(b"x-api-key", b"valid-key")])

    assert messages[0]["status"] == 200


def test_authorization_allows_valid_bearer_token() -> None:
    messages = _run_request([(b"authorization", b"Bearer valid-key")])

    assert messages[0]["status"] == 200


def test_authorization_rejects_invalid_key() -> None:
    messages = _run_request([(b"x-api-key", b"invalid")])

    assert messages[0]["status"] == 401
