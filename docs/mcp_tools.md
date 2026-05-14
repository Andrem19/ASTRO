# MCP Tools

The server exposes health, discovery, natal chart, profile, synastry, transit,
forecast, and SVG helper tools over Streamable HTTP.

## `health_check`

Returns service status:

```json
{
  "status": "ok",
  "service": "astrology-mcp-server",
  "version": "0.1.0",
  "environment": "astro"
}
```

## `server_info`

Returns transport, runtime, and feature flags.

## `list_supported_features`

Returns planned MCP tools:

- `calculate_natal_chart`
- `create_profile`
- `get_profile`
- `get_profile_by_name`
- `list_profiles`
- `update_profile`
- `delete_profile`
- `calculate_profile_natal_chart`
- `clear_profile_chart_cache`
- `calculate_synastry`
- `calculate_profile_synastry`
- `calculate_relationship_summary`
- `generate_synastry_chart_svg`
- `calculate_transits`
- `calculate_profile_transits`
- `calculate_month_forecast`
- `calculate_year_forecast`
- `calculate_profile_month_forecast`
- `calculate_profile_year_forecast`
- `calculate_profile_day_forecast`
- `generate_transit_chart_svg`
- `calculate_life_progressions`
- `calculate_profile_life_progressions`
- `calculate_life_period_overview`
- `calculate_profile_life_period_overview`
- `send_telegram_text_as_pdf`

The server intentionally exposes only base tool names. MCP clients already namespace
tools by server name, so `astro1_*` aliases are not registered.

Each tool has an agent-facing English description in `tools/list`. The server also
exposes `astro://tool-guide` and the `astro_tool_routing_guide` prompt with routing rules
for choosing natal, forecast, synastry, life overview, profile, and Telegram PDF tools.

## `calculate_natal_chart`

Calculates a full natal chart from local birth date, birth time, and birth location.

Example request:

```json
{
  "name": "Person A",
  "birth_date": "1990-05-17",
  "birth_time": "14:35:00",
  "birth_place": "London, United Kingdom",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "timezone": "Europe/London",
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "include_asteroids": false,
    "language": "ru"
  }
}
```

Returns:

- subject input preserved as local birth data
- normalized UTC datetime in `calculation_meta.normalized_utc_datetime`
- angles: ASC, MC, DSC, IC
- main planets, North Node, and Chiron when available
- 12 houses
- aspects with orb and movement
- element, modality, hemisphere, and dominant summaries

## Profile Tools

Profiles store reusable birth data.

- `create_profile`: create a soft-deletable profile.
- `get_profile`: return one profile; private notes are included only when requested.
- `get_profile_by_name`: return a profile by exact case-insensitive name, or candidates if ambiguous.
- `list_profiles`: return profile summaries without private notes by default.
- `update_profile`: update profile fields.
- `delete_profile`: soft delete a profile.
- `calculate_profile_natal_chart`: calculate a natal chart by `profile_id`.
- `clear_profile_chart_cache`: clear cached charts for a profile.

See `docs/profiles.md` for the full model, cache behavior, privacy rules, and
migration commands.

## Synastry Tools

`calculate_synastry` compares two raw birth data payloads.
`calculate_profile_synastry` compares two stored profiles.
`calculate_relationship_summary` turns a synastry result into structured LLM context.
`generate_synastry_chart_svg` returns an SVG string.

See `docs/synastry.md` and `docs/compatibility_scoring.md`.

## Transit And Forecast Tools

`calculate_transits` and `calculate_profile_transits` compare transit planets with natal
planets and angles. Month and year forecast tools sample transit dates and return timelines,
peak dates, themes, and LLM context.

- `calculate_transits`: calculate transits for raw natal birth data.
- `calculate_profile_transits`: calculate transits for a stored profile.
- `calculate_month_forecast`: build a month forecast from raw natal birth data.
- `calculate_year_forecast`: build a year forecast from raw natal birth data.
- `calculate_profile_month_forecast`: build a month forecast for a stored profile.
- `calculate_profile_year_forecast`: build a year forecast for a stored profile.
- `calculate_profile_day_forecast`: build a day forecast for a stored profile.
- `generate_transit_chart_svg`: return a transit chart SVG payload.

See `docs/transits.md` and `docs/forecasts.md`.

## Progression And Direction Tools

Life overview tools combine secondary progressions and solar arc directions. They return
structured periods and LLM context; the agent writes the final interpretation.

- `calculate_life_progressions`: life-period overview from raw natal birth data.
- `calculate_profile_life_progressions`: life-period overview for a stored profile.
- `calculate_life_period_overview`: alias for raw natal life overview.
- `calculate_profile_life_period_overview`: alias for profile life overview.

Use `calculate_profile_life_period_overview` through the Codex Apps connector.
See `docs/progressions_directions.md`.

### `calculate_profile_day_forecast`

Builds structured LLM material for one profile and one date. It does not write the final
user-facing interpretation.

Example request:

```json
{
  "profile_id": "uuid",
  "date": "2026-06-01",
  "time": "12:00:00",
  "timezone": "Europe/London",
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "max_orb": 3,
    "include_lunar_transits": true,
    "include_outer_planet_transits": true
  }
}
```

If `time` is omitted, the server uses `12:00:00`. If `timezone` is omitted, the server
uses the profile timezone, then falls back to `UTC`.

Returns:

- `active_transits`
- `supportive_transits`
- `challenging_transits`
- `dominant_themes`
- `theme_summary`
- `llm_day_context`

## Telegram Tools

Only one Telegram MCP tool is exposed to agents. This keeps the tool choice explicit:
the agent sends full text, and the MCP server creates the PDF locally before sending it.

### `send_telegram_text_as_pdf`

Preferred tool for forecast PDFs. The agent sends full text, and the MCP server creates
the PDF inside `TELEGRAM_OUTBOX_DIR`, sends it, and deletes it after success.
When the tool is accessed through the Codex Apps `astro1` connector, use
`send_telegram_text_as_pdf`.

```json
{
  "file_name": "forecast.pdf",
  "title": "Дневной прогноз",
  "content": "Полный текст прогноза...",
  "caption": "Дневной прогноз PDF"
}
```

Response:

```json
{
  "status": "sent",
  "message_id": 123,
  "chat_id": "42",
  "sent_type": "document",
  "file_deleted": true,
  "warnings": []
}
```

## Error Shape

Tool validation errors are returned by the MCP transport as standard MCP errors.
Application-level payloads that can degrade without failing, such as SVG helpers,
return:

```json
{
  "status": "error",
  "warnings": ["ErrorType"]
}
```

## Bot Connection

Connect bots to the Streamable HTTP endpoint:

```text
http://<host>:<port>/mcp/
```

When auth is enabled, configure the bot to send either `x-api-key` or a bearer token.
