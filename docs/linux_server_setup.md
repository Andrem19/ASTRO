# Linux Server Setup

This project runs directly on a Linux server through the conda environment
`astro`. The runtime model is:

```text
Linux server
  -> conda environment: astro
  -> Python MCP HTTP server
  -> SQLite database file
  -> bots connect to one MCP endpoint
```

## Install

```bash
git clone <repo-url> astrology-mcp-server
cd astrology-mcp-server

conda env create -f environment.yml
conda activate astro

python -m pip install -e .
alembic upgrade head
python -m astrology_mcp.main
```

Without shell activation:

```bash
conda run -n astro python -m pip install -e .
conda run -n astro alembic upgrade head
conda run -n astro python -m astrology_mcp.main
```

## Configuration

Copy the example environment file and edit it for the server:

```bash
cp .env.example .env
```

The default SQLite database is:

```text
./data/astrology_mcp.sqlite3
```

The application creates `data/` automatically. SQLite WAL mode, foreign keys,
and busy timeout are enabled on application connections.

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "astrology-mcp-server",
  "version": "0.1.0",
  "environment": "astro"
}
```

## MCP Endpoint

Bots connect to:

```text
http://<host>:8000/mcp/
```

Multiple bots can use the same endpoint. If authentication is enabled, each bot
must send either:

```text
x-api-key: <key>
Authorization: Bearer <key>
```

## Migrations

```bash
conda run -n astro alembic upgrade head
conda run -n astro alembic revision --autogenerate -m "message"
```

## Checks

```bash
conda run -n astro pytest
conda run -n astro ruff check .
conda run -n astro mypy astrology_mcp
```

## Service Mode

Use `systemd` for normal server operation. See `docs/systemd.md`.

## SQLite Operations

Backups and restores are described in `docs/sqlite.md`.
