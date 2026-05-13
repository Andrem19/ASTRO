# Natal Chart

`calculate_natal_chart` calculates a structured natal chart with Kerykeion.

## Request

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

If `latitude` and `longitude` are present, they are used directly. If either is missing,
`birth_place` is geocoded. If `timezone` is missing, it is resolved from coordinates.

## Response

```json
{
  "chart_type": "natal",
  "subject": {
    "name": "Person A",
    "birth_date": "1990-05-17",
    "birth_time": "14:35:00",
    "birth_place": "London, United Kingdom",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone": "Europe/London"
  },
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical"
  },
  "angles": {
    "ascendant": {},
    "midheaven": {},
    "descendant": {},
    "imum_coeli": {}
  },
  "planets": [],
  "houses": [],
  "aspects": [],
  "elements_balance": {},
  "modalities_balance": {},
  "hemispheres": {},
  "dominants": {},
  "calculation_meta": {
    "engine": "kerykeion",
    "python_environment": "astro",
    "calculated_at": "1990-05-17T13:35:00Z",
    "normalized_utc_datetime": "1990-05-17T13:35:00Z",
    "warnings": []
  }
}
```

`calculated_at` is deterministic and equals the normalized UTC birth datetime. This keeps
identical inputs byte-for-byte stable for tests and backtests.

## Fields

- `planets`: name, sign, degree in sign, absolute zodiac degree, house, element, modality,
  and retrograde flag.
- `houses`: 12 house cusps with sign, degree in sign, and absolute degree.
- `aspects`: point pair, aspect type, orb, exact angle, actual angular distance, and
  applying/separating movement when Kerykeion provides it.
- `angles`: ASC, MC, DSC, and IC with sign and degree data.
- `elements_balance`: count summary for Fire, Earth, Air, and Water.
- `modalities_balance`: count summary for Cardinal, Fixed, and Mutable.
- `hemispheres`: simple planet distribution by house hemisphere.
- `dominants`: dominant element and modality by count.

## House Systems

Supported values:

- `Placidus`
- `Koch`
- `Whole Sign`
- `Equal`

The service maps these names to Kerykeion house system identifiers before calculation.

## Timezone Handling

Input `birth_date` and `birth_time` are local civil birth data. The service validates the
IANA timezone with `zoneinfo`, converts the local datetime to UTC for metadata, and passes
the local data plus timezone to Kerykeion for calculation.

## Precision

Astrological positions come from Kerykeion and pyswisseph. Coordinates, timezone data,
historical time changes, and ephemeris details affect precision. Output degrees are rounded
to 6 decimal places and aspect orbs to 4 decimal places.

## Tests

Run natal chart tests only inside `astro`:

```bash
conda run -n astro pytest tests/unit/test_natal_chart.py
```
