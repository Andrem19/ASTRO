# Progressions And Directions

The progression tools build structured life-period material for LLM interpretation. They
do not write a final deterministic life prediction.

## Techniques

- `secondary_progressions`: one symbolic day after birth represents one year of life.
- `solar_arc_directions`: the progressed Sun arc is applied to natal planets and angles.

The default overview covers ages `0-84` in `7` year periods and samples each period at
the start, midpoint, and end.

## Profile Request

```json
{
  "profile_id": "uuid",
  "settings": {
    "start_age": 0,
    "end_age": 84,
    "period_years": 7,
    "techniques": ["secondary_progressions", "solar_arc_directions"],
    "sample_strategy": "start_mid_end",
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "max_orb": 2,
    "include_angles": true
  }
}
```

Use `calculate_profile_life_period_overview` through the Codex Apps connector.

## Response

The response contains:

- `natal_chart_summary`
- `periods`
- `key_progressed_aspects`
- `key_directed_aspects`
- `house_activations`
- `major_life_themes`
- `turning_point_periods`
- `llm_life_context`

Each period includes dominant themes and separate signals for inner development
(`secondary_progressions`) and external turning points (`solar_arc_directions`).

## Caveats

Progressions and directions are symbolic interpretive methods. Use the output as reflective
material, not as medical, legal, financial, or irreversible life advice.
