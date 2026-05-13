"""Structured logging helpers for tool execution."""

from __future__ import annotations

import functools
import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from astrology_mcp.config import Settings

P = ParamSpec("P")
R = TypeVar("R")


class JsonFormatter(logging.Formatter):
    """Small JSON formatter for operational logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "tool_name", "duration_ms", "status", "error_type"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level.upper(), handlers=[logging.StreamHandler()])
    for handler in logging.getLogger().handlers:
        handler.setFormatter(JsonFormatter())


def log_tool_call(tool_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Log request_id, duration, status, and error type for a tool function."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request_id = str(uuid.uuid4())
            started = time.perf_counter()
            logger = logging.getLogger("astrology_mcp.tools")
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = round((time.perf_counter() - started) * 1000, 3)
                logger.info(
                    "tool_call",
                    extra={
                        "request_id": request_id,
                        "tool_name": tool_name,
                        "duration_ms": duration_ms,
                        "status": "error",
                        "error_type": type(exc).__name__,
                    },
                )
                raise
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            logger.info(
                "tool_call",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "status": "ok",
                },
            )
            return result

        return wrapper

    return decorator
