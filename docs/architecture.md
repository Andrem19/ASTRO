# Architecture

`astrology-mcp-server` is a FastMCP application exposed over Streamable HTTP.

Runtime:

```text
Linux server
  -> conda environment: astro
  -> Python MCP HTTP server
  -> SQLite database file
  -> bots connect to one MCP endpoint
```

Layers:

- `astrology_mcp.config`: pydantic-settings configuration from environment variables.
- `astrology_mcp.mcp_server`: FastMCP assembly, HTTP app creation, and API key middleware.
- `astrology_mcp.tools`: MCP tool functions.
- `astrology_mcp.services`: calculation, timezone, and geocoding service boundaries.
- `astrology_mcp.domain`: typed domain models, enums, and errors.
- `astrology_mcp.storage`: database engine and repository boundaries.

The calculation layer is intentionally isolated so future Kerykeion and pyswisseph work does not slow down health tools or test startup.

The storage layer is SQLite-only. Application connections enable WAL mode, foreign keys,
and busy timeout.
