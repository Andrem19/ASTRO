# Transits

Transit tools compare current or future planetary positions against a natal chart.

## Tool

`calculate_transits` accepts raw natal birth data and a UTC transit datetime:

```json
{
  "natal": {
    "name": "Person A",
    "birth_date": "1990-05-17",
    "birth_time": "14:35:00",
    "birth_place": "London, United Kingdom",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone": "Europe/London"
  },
  "transit_datetime": "2026-06-01T12:00:00Z",
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "max_orb": 3
  }
}
```

`calculate_profile_transits` accepts `profile_id` instead of raw natal data.

## Output

- `natal_chart`: calculated natal chart.
- `transit_chart`: chart for the transit datetime.
- `transit_to_natal_aspects`: aspects from transit planets to natal planets and angles.
- `transit_house_positions`: transit planets projected into natal houses.
- `active_themes`: themes derived from active planets and natal points.

## Method

The service calculates the natal chart, calculates a transit chart for the target UTC
datetime, compares transit planet degrees to natal planet and angle degrees, and keeps
aspects within `max_orb`.

Minor aspects are included only when `include_minor_aspects=true`.

## SVG

`generate_transit_chart_svg` returns a simple SVG string. SVG generation is separate from
the main transit JSON path, so rendering failures do not break transit calculations.

## Tests

```bash
conda run -n astro pytest -n 4 tests/unit/test_transits.py
```
