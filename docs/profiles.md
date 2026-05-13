# Profiles

Profiles store reusable birth data for people. Use `profile_id` in later tools instead of
sending birth data again.

## Stored Data

`profiles` stores:

- `id`
- `external_id`
- `name`
- `birth_date`
- `birth_time`
- `birth_place`
- `latitude`
- `longitude`
- `timezone`
- `notes`
- `created_at`
- `updated_at`
- `deleted_at`

`profile_tags` stores profile tags. `chart_cache` stores calculated natal chart JSON by
profile and settings hash.

## Tools

- `create_profile`
- `get_profile`
- `get_profile_by_name`
- `list_profiles`
- `update_profile`
- `delete_profile`
- `calculate_profile_natal_chart`
- `clear_profile_chart_cache`

## Create Profile

```json
{
  "external_id": "client_123",
  "name": "Person A",
  "birth_date": "1990-05-17",
  "birth_time": "14:35:00",
  "birth_place": "London, United Kingdom",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "timezone": "Europe/London",
  "tags": ["client", "vip"],
  "notes": "Optional private notes"
}
```

Response:

```json
{
  "profile_id": "uuid",
  "external_id": "client_123",
  "status": "created"
}
```

## Use Profile For Natal Chart

```json
{
  "profile_id": "uuid",
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false
  },
  "use_cache": true
}
```

`calculate_profile_natal_chart` loads the profile, hashes the settings, checks
`chart_cache`, and returns a cached chart when `use_cache=true` and the settings hash
exists. Otherwise it calculates a new chart and stores it.

## Lookup By Name

Use `get_profile_by_name` when a bot knows the person's name but not `profile_id`.
The lookup is exact and case-insensitive.

Example:

```json
{
  "name": "Person A",
  "include_private_notes": false
}
```

Responses:

- `status="found"` with `profile` when one active profile matches.
- `status="ambiguous"` with `profiles` when multiple active profiles share the name.
- `status="not_found"` when no active profile matches.

Private notes are omitted unless `include_private_notes=true`.

## Delete Profile

`delete_profile` is a soft delete. It sets `deleted_at`, so normal `get_profile` and
`list_profiles` calls no longer return the profile. Use an explicit include-deleted mode
only for administrative recovery workflows.

## Privacy Notes

`list_profiles` never returns `notes`. `get_profile` returns `notes` only when
`include_private_notes=true`. Tool execution logs include tool metadata, duration, status,
and error type, but not full birth data.

## Migrations

The project uses SQLite only. The default database file is `./data/astrology_mcp.sqlite3`.

Run migrations only inside `astro`:

```bash
conda run -n astro alembic upgrade head
```

Create a new migration only inside `astro`:

```bash
conda run -n astro alembic revision --autogenerate -m "description"
```
