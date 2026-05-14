# Synastry

Synastry compares two natal charts and returns inter-chart aspects, house overlays,
relationship themes, compatibility scores, and structured context for LLM bots.

## Raw Birth Data Request

```json
{
  "person_a": {
    "name": "Person A",
    "birth_date": "1990-05-17",
    "birth_time": "14:35:00",
    "birth_place": "London, United Kingdom",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone": "Europe/London"
  },
  "person_b": {
    "name": "Person B",
    "birth_date": "1992-09-03",
    "birth_time": "08:10:00",
    "birth_place": "Paris, France",
    "latitude": 48.8566,
    "longitude": 2.3522,
    "timezone": "Europe/Paris"
  },
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "max_orb": 8
  }
}
```

## Profile Request

```json
{
  "profile_id_a": "uuid",
  "profile_id_b": "uuid",
  "settings": {
    "house_system": "Placidus",
    "zodiac_type": "tropical",
    "include_minor_aspects": false,
    "max_orb": 8
  },
  "use_cache": true
}
```

## Response

```json
{
  "chart_type": "synastry",
  "person_a": {},
  "person_b": {},
  "person_a_natal": {},
  "person_b_natal": {},
  "inter_chart_aspects": [],
  "house_overlays": [],
  "relationship_themes": {},
  "compatibility_scores": {},
  "calculation_meta": {
    "engine": "kerykeion",
    "python_environment": "astro",
    "calculated_at": "ISO datetime",
    "warnings": []
  }
}
```

The service calculates both natal charts first, compares planet positions between charts,
finds aspects within `max_orb`, and projects each person's planets into the other person's
houses.

## LLM Bot Use

Use `calculate_relationship_summary` for concise structured context:

- `main_strengths`
- `main_challenges`
- `communication_pattern`
- `emotional_pattern`
- `romantic_pattern`
- `long_term_potential`
- `llm_prompt_context`

The recommended tone is balanced, non-deterministic, and respectful.

## SVG

`generate_synastry_chart_svg` accepts either raw birth data or two profile IDs. SVG
generation is isolated from the main JSON calculation.

## Tests

```bash
conda run -n astro pytest -n 4 tests/unit/test_synastry.py
```
