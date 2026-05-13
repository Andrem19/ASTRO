"""Application entrypoint."""

from __future__ import annotations

import uvicorn

from astrology_mcp.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "astrology_mcp.mcp_server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
