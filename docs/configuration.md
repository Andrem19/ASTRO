# Configuration

Configuration is loaded by `astrology_mcp.config.Settings` from environment variables or
`.env`. There is no CLI argument parsing.

Core variables:

- `APP_NAME`
- `APP_VERSION`
- `HOST`
- `PORT`
- `ASTROLOGY_ENGINE`
- `DEFAULT_HOUSE_SYSTEM`
- `DEFAULT_ZODIAC_TYPE`
- `DEFAULT_LANGUAGE`
- `API_AUTH_ENABLED`
- `API_KEYS`
- `LOG_LEVEL`

SQLite-only variables:

- `DATABASE_URL`
- `SQLITE_DB_PATH`
- `SQLITE_ECHO`
- `SQLITE_BUSY_TIMEOUT_MS`
- `SQLITE_ENABLE_WAL`
- `SQLITE_ENABLE_FOREIGN_KEYS`

Defaults:

```text
DATABASE_URL=sqlite:///./data/astrology_mcp.sqlite3
SQLITE_DB_PATH=./data/astrology_mcp.sqlite3
SQLITE_ECHO=false
SQLITE_BUSY_TIMEOUT_MS=5000
SQLITE_ENABLE_WAL=true
SQLITE_ENABLE_FOREIGN_KEYS=true
```

Only SQLite database URLs are supported. The application creates the SQLite parent
directory automatically.

Authentication:

- `API_AUTH_ENABLED=false`: requests are accepted without credentials.
- `API_AUTH_ENABLED=true`: requests must include `x-api-key: <key>` or `Authorization: Bearer <key>`.
- Valid keys are read from comma-separated `API_KEYS`.
