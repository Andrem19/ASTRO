"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the MCP server."""

    app_name: str = Field(default="astrology-mcp-server", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    database_url: str = Field(
        default="sqlite:///./data/astrology_mcp.sqlite3",
        alias="DATABASE_URL",
    )
    sqlite_db_path: str = Field(
        default="./data/astrology_mcp.sqlite3",
        alias="SQLITE_DB_PATH",
    )
    sqlite_echo: bool = Field(default=False, alias="SQLITE_ECHO")
    sqlite_busy_timeout_ms: int = Field(default=5000, alias="SQLITE_BUSY_TIMEOUT_MS")
    sqlite_enable_wal: bool = Field(default=True, alias="SQLITE_ENABLE_WAL")
    sqlite_enable_foreign_keys: bool = Field(default=True, alias="SQLITE_ENABLE_FOREIGN_KEYS")
    astrology_engine: str = Field(default="kerykeion", alias="ASTROLOGY_ENGINE")
    default_house_system: str = Field(default="Placidus", alias="DEFAULT_HOUSE_SYSTEM")
    default_zodiac_type: str = Field(default="tropical", alias="DEFAULT_ZODIAC_TYPE")
    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")
    api_auth_enabled: bool = Field(default=False, alias="API_AUTH_ENABLED")
    api_keys: Annotated[tuple[str, ...], NoDecode] = Field(default=(), alias="API_KEYS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    algo_bot: str | None = Field(default=None, alias="ALGO_BOT")
    chat_id: str | None = Field(default=None, alias="CHAT_ID")
    telegram_outbox_dir: str = Field(
        default="./runtime/telegram_outbox",
        alias="TELEGRAM_OUTBOX_DIR",
    )
    telegram_max_file_size_mb: int = Field(default=20, alias="TELEGRAM_MAX_FILE_SIZE_MB")
    pdf_font_path: str = Field(
        default="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        alias="PDF_FONT_PATH",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, value: Any) -> tuple[str, ...]:
        if value is None or value == "":
            return ()
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        if isinstance(value, list | tuple | set):
            return tuple(str(part).strip() for part in value if str(part).strip())
        raise TypeError("API_KEYS must be a comma-separated string or a sequence of strings")

    @model_validator(mode="after")
    def validate_sqlite_only(self) -> Settings:
        if not self.database_url.startswith("sqlite"):
            raise ValueError("Only SQLite DATABASE_URL values are supported")
        if self.sqlite_busy_timeout_ms < 0:
            raise ValueError("SQLITE_BUSY_TIMEOUT_MS must be >= 0")
        if self.telegram_max_file_size_mb <= 0:
            raise ValueError("TELEGRAM_MAX_FILE_SIZE_MB must be > 0")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for production runtime."""

    return Settings()
