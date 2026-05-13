"""Application entrypoint."""

from __future__ import annotations

import uvicorn

from astrology_mcp.config import get_settings
from astrology_mcp.services.telegram_notifier import TelegramNotifier


def main() -> None:
    settings = get_settings()
    try:
        uvicorn.run(
            "astrology_mcp.mcp_server:create_app",
            factory=True,
            host=settings.host,
            port=settings.port,
        )
    except Exception as exc:
        TelegramNotifier(settings).send_startup_failure_sync(exc)
        raise


if __name__ == "__main__":
    main()
