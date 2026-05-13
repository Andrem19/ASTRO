from astrology_mcp.config import Settings


def test_configuration_loads_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "astrology-mcp-server"
    assert settings.app_version == "0.1.0"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.database_url == "sqlite:///./data/astrology_mcp.sqlite3"
    assert settings.sqlite_db_path == "./data/astrology_mcp.sqlite3"
    assert settings.sqlite_enable_wal is True
    assert settings.sqlite_enable_foreign_keys is True
    assert settings.api_auth_enabled is False
    assert settings.algo_bot is None
    assert settings.chat_id is None
    assert settings.telegram_outbox_dir == "./runtime/telegram_outbox"
    assert settings.telegram_max_file_size_mb == 20


def test_api_keys_parse_comma_separated_values() -> None:
    settings = Settings(API_KEYS="one,two, three ")

    assert settings.api_keys == ("one", "two", "three")
