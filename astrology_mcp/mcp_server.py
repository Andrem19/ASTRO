"""FastMCP server assembly and HTTP authorization."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from http import HTTPStatus
from typing import Any

from fastmcp import FastMCP

from astrology_mcp.config import Settings, get_settings
from astrology_mcp.logging import configure_logging
from astrology_mcp.services.telegram_notifier import TelegramNotifier
from astrology_mcp.tools.health_tools import health_check, list_supported_features, server_info
from astrology_mcp.tools.natal_chart_tools import calculate_natal_chart
from astrology_mcp.tools.profile_tools import (
    calculate_profile_natal_chart,
    clear_profile_chart_cache,
    create_profile,
    delete_profile,
    get_profile,
    get_profile_by_name,
    list_profiles,
    update_profile,
)
from astrology_mcp.tools.synastry_tools import (
    calculate_profile_synastry,
    calculate_relationship_summary,
    calculate_synastry,
    generate_synastry_chart_svg,
)
from astrology_mcp.tools.telegram_tools import send_telegram_message
from astrology_mcp.tools.transit_tools import (
    calculate_month_forecast,
    calculate_profile_day_forecast,
    calculate_profile_month_forecast,
    calculate_profile_transits,
    calculate_profile_year_forecast,
    calculate_transits,
    calculate_year_forecast,
    generate_transit_chart_svg,
)

AsgiMessage = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[AsgiMessage]]
Send = Callable[[AsgiMessage], Awaitable[None]]
AsgiScope = MutableMapping[str, Any]
AsgiApp = Callable[[AsgiScope, Receive, Send], Awaitable[None]]


class ApiKeyAuthMiddleware:
    """ASGI middleware that accepts x-api-key or Authorization: Bearer tokens."""

    def __init__(self, app: AsgiApp, settings: Settings) -> None:
        self._app = app
        self._settings = settings

    async def __call__(self, scope: AsgiScope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or not self._settings.api_auth_enabled:
            await self._app(scope, receive, send)
            return

        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        token = self._extract_token(headers)
        if token in self._settings.api_keys:
            await self._app(scope, receive, send)
            return

        await self._reject(send)

    @staticmethod
    def _extract_token(headers: dict[str, str]) -> str | None:
        api_key = headers.get("x-api-key")
        if api_key:
            return api_key
        authorization = headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token
        return None

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"Unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": HTTPStatus.UNAUTHORIZED,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class HealthRouteMiddleware:
    """Serve a plain HTTP health endpoint for Linux/server checks."""

    def __init__(self, app: AsgiApp, settings: Settings) -> None:
        self._app = app
        self._settings = settings

    async def __call__(self, scope: AsgiScope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http" and scope.get("path") == "/health":
            body = (
                "{"
                '"status":"ok",'
                f'"service":"{self._settings.app_name}",'
                f'"version":"{self._settings.app_version}",'
                '"environment":"astro"'
                "}"
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": HTTPStatus.OK,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self._app(scope, receive, send)


class StartupNotificationMiddleware:
    """Send Telegram notifications for ASGI startup success or failure."""

    def __init__(self, app: AsgiApp, settings: Settings) -> None:
        self._app = app
        self._notifier = TelegramNotifier(settings)

    async def __call__(self, scope: AsgiScope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "lifespan":
            await self._app(scope, receive, send)
            return

        async def notifying_send(message: AsgiMessage) -> None:
            await send(message)
            message_type = message.get("type")
            if message_type == "lifespan.startup.complete":
                asyncio.create_task(self._notifier.send_startup_success())
            elif message_type == "lifespan.startup.failed":
                detail = str(message.get("message") or "startup failed")
                asyncio.create_task(self._notifier.send_startup_failure(detail))

        try:
            await self._app(scope, receive, notifying_send)
        except Exception as exc:
            asyncio.create_task(self._notifier.send_startup_failure(exc))
            raise


def create_mcp_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()
    mcp = FastMCP(settings.app_name)

    @mcp.tool(name="health_check")
    def health_check_tool() -> dict[str, object]:
        return health_check(settings)

    @mcp.tool(name="server_info")
    def server_info_tool() -> dict[str, object]:
        return server_info(settings)

    @mcp.tool(name="list_supported_features")
    def list_supported_features_tool() -> dict[str, object]:
        return list_supported_features()

    @mcp.tool(name="calculate_natal_chart")
    def calculate_natal_chart_tool(
        name: str,
        birth_date: str,
        birth_time: str,
        birth_place: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str | None = None,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_natal_chart(
            name=name,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=birth_place,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            settings=settings,
        )

    @mcp.tool(name="create_profile")
    def create_profile_tool(
        name: str,
        birth_date: str,
        birth_time: str,
        external_id: str | None = None,
        birth_place: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, str | None]:
        return create_profile(
            name=name,
            external_id=external_id,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=birth_place,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            tags=tags,
            notes=notes,
        )

    @mcp.tool(name="get_profile")
    def get_profile_tool(
        profile_id: str,
        include_private_notes: bool = False,
        include_deleted: bool = False,
    ) -> dict[str, object]:
        return get_profile(profile_id, include_private_notes, include_deleted)

    @mcp.tool(name="get_profile_by_name")
    def get_profile_by_name_tool(
        name: str,
        include_private_notes: bool = False,
        include_deleted: bool = False,
        limit: int = 10,
    ) -> dict[str, object]:
        return get_profile_by_name(
            name,
            include_private_notes=include_private_notes,
            include_deleted=include_deleted,
            limit=limit,
        )

    @mcp.tool(name="list_profiles")
    def list_profiles_tool(include_deleted: bool = False, limit: int = 100) -> dict[str, object]:
        return list_profiles(include_deleted=include_deleted, limit=limit)

    @mcp.tool(name="update_profile")
    def update_profile_tool(profile_id: str, updates: dict[str, object]) -> dict[str, object]:
        return update_profile(profile_id, updates)

    @mcp.tool(name="delete_profile")
    def delete_profile_tool(profile_id: str) -> dict[str, str]:
        return delete_profile(profile_id)

    @mcp.tool(name="calculate_profile_natal_chart")
    def calculate_profile_natal_chart_tool(
        profile_id: str,
        settings: dict[str, object] | None = None,
        use_cache: bool = True,
    ) -> dict[str, object]:
        return calculate_profile_natal_chart(profile_id, settings=settings, use_cache=use_cache)

    @mcp.tool(name="clear_profile_chart_cache")
    def clear_profile_chart_cache_tool(profile_id: str) -> dict[str, int | str]:
        return clear_profile_chart_cache(profile_id)

    @mcp.tool(name="calculate_synastry")
    def calculate_synastry_tool(
        person_a: dict[str, object],
        person_b: dict[str, object],
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_synastry(person_a, person_b, settings)

    @mcp.tool(name="calculate_profile_synastry")
    def calculate_profile_synastry_tool(
        profile_id_a: str,
        profile_id_b: str,
        settings: dict[str, object] | None = None,
        use_cache: bool = True,
    ) -> dict[str, object]:
        return calculate_profile_synastry(
            profile_id_a,
            profile_id_b,
            settings=settings,
            use_cache=use_cache,
        )

    @mcp.tool(name="calculate_relationship_summary")
    def calculate_relationship_summary_tool(synastry: dict[str, object]) -> dict[str, object]:
        return calculate_relationship_summary(synastry)

    @mcp.tool(name="generate_synastry_chart_svg")
    def generate_synastry_chart_svg_tool(
        person_a: dict[str, object] | None = None,
        person_b: dict[str, object] | None = None,
        profile_id_a: str | None = None,
        profile_id_b: str | None = None,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return generate_synastry_chart_svg(
            person_a=person_a,
            person_b=person_b,
            profile_id_a=profile_id_a,
            profile_id_b=profile_id_b,
            settings=settings,
        )

    @mcp.tool(name="calculate_transits")
    def calculate_transits_tool(
        natal: dict[str, object],
        transit_datetime: str,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_transits(natal, transit_datetime, settings)

    @mcp.tool(name="calculate_profile_transits")
    def calculate_profile_transits_tool(
        profile_id: str,
        transit_datetime: str,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_profile_transits(profile_id, transit_datetime, settings)

    @mcp.tool(name="calculate_month_forecast")
    def calculate_month_forecast_tool(
        natal: dict[str, object],
        year: int,
        month: int,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_month_forecast(natal, year, month, settings)

    @mcp.tool(name="calculate_year_forecast")
    def calculate_year_forecast_tool(
        natal: dict[str, object],
        year: int,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_year_forecast(natal, year, settings)

    @mcp.tool(name="calculate_profile_month_forecast")
    def calculate_profile_month_forecast_tool(
        profile_id: str,
        year: int,
        month: int,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_profile_month_forecast(profile_id, year, month, settings)

    @mcp.tool(name="calculate_profile_year_forecast")
    def calculate_profile_year_forecast_tool(
        profile_id: str,
        year: int,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_profile_year_forecast(profile_id, year, settings)

    @mcp.tool(name="calculate_profile_day_forecast")
    def calculate_profile_day_forecast_tool(
        profile_id: str,
        date: str,
        time: str | None = None,
        timezone: str | None = None,
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return calculate_profile_day_forecast(
            profile_id,
            date,
            time=time,
            timezone=timezone,
            settings=settings,
        )

    @mcp.tool(name="generate_transit_chart_svg")
    def generate_transit_chart_svg_tool(
        natal: dict[str, object] | None = None,
        profile_id: str | None = None,
        transit_datetime: str = "2026-06-01T12:00:00Z",
        settings: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return generate_transit_chart_svg(
            natal=natal,
            profile_id=profile_id,
            transit_datetime=transit_datetime,
            settings=settings,
        )

    @mcp.tool(name="send_telegram_message")
    async def send_telegram_message_tool(
        text: str | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        text_content: str | None = None,
        content_base64: str | None = None,
        caption: str | None = None,
    ) -> dict[str, object]:
        return await send_telegram_message(
            text=text,
            file_path=file_path,
            file_name=file_name,
            text_content=text_content,
            content_base64=content_base64,
            caption=caption,
        )

    return mcp


def create_app(settings: Settings | None = None) -> AsgiApp:
    settings = settings or get_settings()
    configure_logging(settings)
    mcp = create_mcp_server(settings)
    app = mcp.http_app(path="/mcp/", transport="streamable-http")
    authorized_app = ApiKeyAuthMiddleware(app, settings)
    health_app = HealthRouteMiddleware(authorized_app, settings)
    return StartupNotificationMiddleware(health_app, settings)
