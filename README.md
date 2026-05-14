# astrology-mcp-server

FastMCP astrology server exposed over Streamable HTTP for multiple bots from one Linux
endpoint. Runtime is Linux + conda `astro` + Python + SQLite.

## Server Install

```bash
git clone <repo-url> astrology-mcp-server
cd astrology-mcp-server

conda env create -f environment.yml
conda activate astro

python -m pip install -e .
alembic upgrade head
python -m astrology_mcp.main
```

Without activating the shell:

```bash
conda run -n astro python -m pip install -e .
conda run -n astro alembic upgrade head
conda run -n astro python -m astrology_mcp.main
```

The MCP endpoint is:

```text
http://<host>:8000/mcp/
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## SQLite

Default database:

```text
./data/astrology_mcp.sqlite3
```

The server creates `data/` automatically and enables SQLite WAL mode, foreign keys, and
busy timeout on application connections.

Backup and restore instructions are in `docs/sqlite.md`.

## Linux Service

Server setup is documented in `docs/linux_server_setup.md`.
The `systemd` unit example is documented in `docs/systemd.md`.

## Checks

```bash
conda run -n astro pytest -n 4
conda run -n astro ruff check .
conda run -n astro mypy astrology_mcp
```

Tests are expected to stay fast and parallel-friendly. Run them with pytest-xdist
(`-n 4`), keep each unit test under 1 second, and mock slow calculations, network calls,
filesystem-heavy work, and external services. Pytest is configured to print the top 20
slowest tests at the end of each run.

## Authentication

Set `API_AUTH_ENABLED=true` and provide comma-separated keys in `API_KEYS`.

Accepted headers:

```text
x-api-key: <key>
Authorization: Bearer <key>
```

With `API_AUTH_ENABLED=false`, no credentials are required.

## Documentation

- `docs/linux_server_setup.md`: Linux install, migrations, health checks, bot endpoint.
- `docs/systemd.md`: service unit and service management commands.
- `docs/sqlite.md`: SQLite backup, restore, and maintenance rules.
- `docs/mcp_tools.md`: MCP tool catalog.
