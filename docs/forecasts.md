# Forecasts

Forecast tools produce structured astrological material for LLM bots. They do not write a
final artistic forecast.

## Pipeline

1. Calculate the natal chart.
2. Build dates for the month or year.
3. Calculate a transit chart for each sampled date.
4. Find transit-to-natal aspects.
5. Group active aspects by themes.
6. Return timelines, peak dates, themes, and LLM context.

## Tools

- `calculate_profile_day_forecast`
- `calculate_month_forecast`
- `calculate_year_forecast`
- `calculate_profile_month_forecast`
- `calculate_profile_year_forecast`

## Day Forecast

`calculate_profile_day_forecast` builds one-day structured material for a stored profile.
It calculates transits for the selected local date and time, compares them against the
profile natal chart, groups the active transits by themes, and returns `llm_day_context`.

Input:

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

Defaults:

- `time`: `12:00:00`.
- `timezone`: profile timezone, then `UTC`.

The day forecast returns structured material only. The bot should use `llm_day_context`
to write the final daily interpretation.

## Sampling

- `daily`: every date in the period.
- `weekly`: every 7 days, with year/month end included for weekly forecasts.
- `important_events_only`: weekly scan that keeps dates with active transits.

Defaults:

- Month forecast: `daily`.
- Year forecast: `weekly`.
- Lunar transits for year: disabled by default to reduce noise.
- Outer planet transits for year: enabled by default.

## Peak Dates

`peak_dates` are dates with the highest number of active transits in the sampled timeline.
They are not deterministic predictions; they are attention points for interpretation.

## LLM Context

`llm_forecast_context` contains:

- main period themes
- supportive periods
- challenging periods
- reflection questions
- caveats

Use this as structured input for a bot that writes the final user-facing text.

## Limitations

Forecasts depend on sampling frequency, orb settings, birth data accuracy, timezone data,
and ephemeris calculations. The result is interpretive material, not certainty.

## Tests

```bash
conda run -n astro pytest tests/unit/test_transits.py
```
