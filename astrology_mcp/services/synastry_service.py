"""Synastry and relationship summary calculations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, SynastryCalculationSettings
from astrology_mcp.services.astrology_engine import AstrologyEngine
from astrology_mcp.services.profile_service import ProfileService

ASPECT_DEGREES = {
    "conjunction": 0,
    "opposition": 180,
    "trine": 120,
    "square": 90,
    "sextile": 60,
    "semi-sextile": 30,
    "semi-square": 45,
    "quintile": 72,
    "sesquiquadrate": 135,
    "quincunx": 150,
}
MINOR_ASPECT_NAMES = {"semi-sextile", "semi-square", "quintile", "sesquiquadrate", "quincunx"}
ASPECT_WEIGHTS = {
    "conjunction": 9,
    "trine": 8,
    "sextile": 6,
    "opposition": 5,
    "square": 4,
    "semi-sextile": 2,
    "semi-square": 2,
    "quintile": 3,
    "sesquiquadrate": 2,
    "quincunx": 3,
}
THEME_POINTS = {
    "emotional": {"Moon", "Venus", "Sun"},
    "mental": {"Mercury", "Moon", "Sun"},
    "romantic": {"Venus", "Mars", "Sun", "Moon"},
    "stability": {"Saturn", "Jupiter", "Sun", "Moon"},
    "challenge": {"Mars", "Saturn", "Uranus", "Pluto"},
}
THEME_RESPONSE_KEYS = {
    "emotional": "emotional_connection",
    "mental": "communication",
    "romantic": "romantic_attraction",
    "stability": "long_term_stability",
    "challenge": "conflict_points",
}


class SynastryService:
    def __init__(
        self,
        settings: Settings,
        astrology_engine: AstrologyEngine | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self._settings = settings
        self._astrology_engine = astrology_engine or AstrologyEngine(settings)
        self._profile_service = profile_service or ProfileService(settings)

    def calculate_synastry(
        self,
        person_a: BirthData,
        person_b: BirthData,
        settings: SynastryCalculationSettings,
    ) -> dict[str, object]:
        person_a.settings = settings
        person_b.settings = settings
        natal_a = self._astrology_engine.calculate_natal_chart(person_a).model_dump()
        natal_b = self._astrology_engine.calculate_natal_chart(person_b).model_dump()
        inter_aspects = self._inter_chart_aspects(
            natal_a["planets"],
            natal_b["planets"],
            settings,
        )
        overlays = self._house_overlays(natal_a, natal_b)
        scores = self._compatibility_scores(inter_aspects)
        themes = self._relationship_themes(inter_aspects, scores)
        return {
            "chart_type": "synastry",
            "person_a": natal_a["subject"],
            "person_b": natal_b["subject"],
            "person_a_natal": natal_a,
            "person_b_natal": natal_b,
            "inter_chart_aspects": inter_aspects,
            "house_overlays": overlays,
            "relationship_themes": themes,
            "compatibility_scores": scores,
            "calculation_meta": {
                "engine": self._settings.astrology_engine,
                "python_environment": "astro",
                "calculated_at": self._calculated_at(natal_a, natal_b),
                "warnings": [
                    "Compatibility scores are interpretive signals, not deterministic predictions."
                ],
            },
        }

    def calculate_profile_synastry(
        self,
        profile_id_a: str,
        profile_id_b: str,
        settings: SynastryCalculationSettings,
        use_cache: bool = True,
    ) -> dict[str, object]:
        person_a = self._profile_service.get_birth_data(profile_id_a, settings)
        person_b = self._profile_service.get_birth_data(profile_id_b, settings)
        result = self.calculate_synastry(person_a, person_b, settings)
        result["cache"] = {"hit": False, "use_cache": use_cache}
        return result

    def calculate_relationship_summary(
        self,
        synastry: dict[str, object],
    ) -> dict[str, object]:
        aspects = cast(list[dict[str, object]], synastry["inter_chart_aspects"])
        strengths = [a for a in aspects if a["aspect_type"] in {"trine", "sextile", "conjunction"}]
        challenge_names = {"square", "opposition", "quincunx"}
        challenges = [a for a in aspects if a["aspect_type"] in challenge_names]
        key_points = [
            f"{a['planet_a']} {a['aspect_type']} {a['planet_b']} orb {a['orb']}"
            for a in aspects[:8]
        ]
        return {
            "main_strengths": self._aspect_phrases(strengths[:5]),
            "main_challenges": self._aspect_phrases(challenges[:5]),
            "communication_pattern": self._theme_phrases(aspects, {"Mercury", "Moon"}),
            "emotional_pattern": self._theme_phrases(aspects, {"Moon", "Venus"}),
            "romantic_pattern": self._theme_phrases(aspects, {"Venus", "Mars", "Sun"}),
            "long_term_potential": self._theme_phrases(aspects, {"Saturn", "Jupiter"}),
            "llm_prompt_context": {
                "recommended_tone": "balanced, non-deterministic, respectful",
                "important_caveats": [
                    "Astrology is interpretive, not deterministic",
                    "Avoid making medical, legal, or irreversible life advice",
                ],
                "key_points": key_points,
            },
        }

    def generate_synastry_chart_svg(self, synastry: dict[str, object]) -> dict[str, object]:
        try:
            person_a = synastry["person_a"]["name"]  # type: ignore[index]
            person_b = synastry["person_b"]["name"]  # type: ignore[index]
            aspects_count = len(synastry["inter_chart_aspects"])  # type: ignore[arg-type]
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" '
                'viewBox="0 0 720 360">'
                '<rect width="720" height="360" fill="#fff"/>'
                '<circle cx="250" cy="180" r="120" fill="none" stroke="#333" stroke-width="2"/>'
                '<circle cx="470" cy="180" r="120" fill="none" stroke="#777" stroke-width="2"/>'
                f'<text x="40" y="40" font-family="sans-serif" font-size="24">{person_a}</text>'
                f'<text x="520" y="40" font-family="sans-serif" font-size="24">{person_b}</text>'
                f'<text x="260" y="330" font-family="sans-serif" font-size="18">'
                f'{aspects_count} inter-chart aspects</text></svg>'
            )
            return {"svg": svg, "status": "ok", "warnings": []}
        except Exception as exc:
            return {"svg": "", "status": "error", "warnings": [type(exc).__name__]}

    @staticmethod
    def _inter_chart_aspects(
        planets_a: list[dict[str, object]],
        planets_b: list[dict[str, object]],
        settings: SynastryCalculationSettings,
    ) -> list[dict[str, object]]:
        allowed = dict(ASPECT_DEGREES)
        if not settings.include_minor_aspects:
            allowed = {
                name: degree
                for name, degree in allowed.items()
                if name not in MINOR_ASPECT_NAMES
            }
        aspects: list[dict[str, object]] = []
        for planet_a in planets_a:
            for planet_b in planets_b:
                distance = SynastryService._angular_distance(
                    SynastryService._float_value(planet_a["absolute_degree"]),
                    SynastryService._float_value(planet_b["absolute_degree"]),
                )
                for aspect_name, exact_angle in allowed.items():
                    orb = abs(distance - exact_angle)
                    if orb <= settings.max_orb:
                        aspects.append(
                            {
                                "planet_a": planet_a["name"],
                                "planet_b": planet_b["name"],
                                "aspect_type": aspect_name,
                                "orb": round(orb, 4),
                                "exact_angle": exact_angle,
                                "actual_angle": round(distance, 4),
                                "weight": SynastryService._aspect_weight(aspect_name, orb),
                            }
                        )
                        break
        return sorted(
            aspects,
            key=lambda item: (
                SynastryService._float_value(item["orb"]),
                str(item["planet_a"]),
                str(item["planet_b"]),
            ),
        )

    @staticmethod
    def _house_overlays(
        natal_a: dict[str, object],
        natal_b: dict[str, object],
    ) -> list[dict[str, object]]:
        return [
            *SynastryService._project_planets(
                natal_a["planets"], natal_b["houses"], "person_a", "person_b"
            ),
            *SynastryService._project_planets(
                natal_b["planets"], natal_a["houses"], "person_b", "person_a"
            ),
        ]

    @staticmethod
    def _project_planets(
        planets: object,
        houses: object,
        owner: str,
        house_owner: str,
    ) -> list[dict[str, object]]:
        house_list = cast(list[dict[str, object]], houses)
        result: list[dict[str, object]] = []
        for planet in cast(list[dict[str, object]], planets):
            result.append(
                {
                    "planet": planet["name"],
                    "planet_owner": owner,
                    "house_owner": house_owner,
                    "projected_house": SynastryService._house_for_degree(
                        SynastryService._float_value(planet["absolute_degree"]),
                        house_list,
                    ),
                }
            )
        return result

    @staticmethod
    def _house_for_degree(degree: float, houses: list[Any]) -> int:
        sorted_houses = sorted(
            houses,
            key=lambda house: SynastryService._float_value(house["absolute_degree"]),
        )
        for index, house in enumerate(sorted_houses):
            start = SynastryService._float_value(house["absolute_degree"])
            end = SynastryService._float_value(
                sorted_houses[(index + 1) % len(sorted_houses)]["absolute_degree"]
            )
            if end < start:
                end += 360
            adjusted = degree + 360 if degree < start else degree
            if start <= adjusted < end:
                return int(house["house_number"])
        return int(sorted_houses[-1]["house_number"])

    @staticmethod
    def _compatibility_scores(aspects: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        grouped: dict[str, list[dict[str, object]]] = {theme: [] for theme in THEME_POINTS}
        for aspect in aspects:
            planets = {str(aspect["planet_a"]), str(aspect["planet_b"])}
            for theme, theme_planets in THEME_POINTS.items():
                if planets & theme_planets:
                    grouped[theme].append(aspect)
        scores: dict[str, dict[str, object]] = {
            theme: SynastryService._score_theme(theme, theme_aspects)
            for theme, theme_aspects in grouped.items()
        }
        overall_value = round(
            (
                SynastryService._int_value(scores["emotional"]["value"])
                + SynastryService._int_value(scores["mental"]["value"])
                + SynastryService._int_value(scores["romantic"]["value"])
                + SynastryService._int_value(scores["stability"]["value"])
                + SynastryService._int_value(scores["challenge"]["value"]) * 0.5
            )
            / 4.5
        )
        scores["overall"] = {
            "value": overall_value,
            "explanation": (
                "Significant inter-chart aspects are weighted, grouped by theme, and "
                "normalized to a 0-100 interpretive scale."
            ),
            "supporting_aspects": [SynastryService._aspect_label(a) for a in aspects[:8]],
        }
        return {
            "overall": scores["overall"],
            "emotional": scores["emotional"],
            "mental": scores["mental"],
            "romantic": scores["romantic"],
            "stability": scores["stability"],
            "challenge": scores["challenge"],
        }

    @staticmethod
    def _score_theme(theme: str, aspects: list[dict[str, object]]) -> dict[str, object]:
        raw = sum(SynastryService._float_value(aspect["weight"]) for aspect in aspects[:12])
        value = min(100, round(raw * 6))
        explanation = (
            "Challenge shows tension and growth potential, not a bad result."
            if theme == "challenge"
            else "Score is based on weighted aspects connected to this relationship theme."
        )
        return {
            "value": value,
            "explanation": explanation,
            "supporting_aspects": [SynastryService._aspect_label(aspect) for aspect in aspects[:6]],
        }

    @staticmethod
    def _relationship_themes(
        aspects: list[dict[str, object]],
        scores: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        themes: dict[str, dict[str, object]] = {
            response_key: {
                "score": scores[theme],
                "key_aspects": SynastryService._theme_phrases(aspects, planets),
            }
            for theme, planets in THEME_POINTS.items()
            for response_key in [THEME_RESPONSE_KEYS[theme]]
        }
        themes["sexual_chemistry"] = {
            "score": scores["romantic"],
            "key_aspects": SynastryService._theme_phrases(aspects, {"Mars", "Venus"}),
        }
        themes["growth_points"] = {
            "score": scores["challenge"],
            "key_aspects": SynastryService._theme_phrases(aspects, {"Saturn", "Pluto", "Uranus"}),
        }
        return themes

    @staticmethod
    def _aspect_weight(aspect_name: str, orb: float) -> float:
        base = ASPECT_WEIGHTS[aspect_name]
        precision = max(0.25, 1 - (orb / 10))
        return round(base * precision, 4)

    @staticmethod
    def _angular_distance(degree_a: float, degree_b: float) -> float:
        distance = abs(degree_a - degree_b) % 360
        return min(distance, 360 - distance)

    @staticmethod
    def _aspect_label(aspect: dict[str, object]) -> str:
        return f"{aspect['planet_a']} {aspect['aspect_type']} {aspect['planet_b']}"

    @staticmethod
    def _aspect_phrases(aspects: list[dict[str, object]]) -> list[str]:
        return [
            f"{aspect['planet_a']} {aspect['aspect_type']} {aspect['planet_b']} "
            f"(orb {aspect['orb']})"
            for aspect in aspects
        ]

    @staticmethod
    def _theme_phrases(aspects: list[dict[str, object]], planets: set[str]) -> list[str]:
        matching = [
            aspect
            for aspect in aspects
            if {str(aspect["planet_a"]), str(aspect["planet_b"])} & planets
        ]
        return SynastryService._aspect_phrases(matching[:5])

    @staticmethod
    def _calculated_at(natal_a: dict[str, object], natal_b: dict[str, object]) -> str:
        first = str(natal_a["calculation_meta"]["normalized_utc_datetime"])  # type: ignore[index]
        second = str(natal_b["calculation_meta"]["normalized_utc_datetime"])  # type: ignore[index]
        later = max(
            datetime.fromisoformat(first.replace("Z", "+00:00")),
            datetime.fromisoformat(second.replace("Z", "+00:00")),
        )
        return later.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _float_value(value: object) -> float:
        if isinstance(value, int | float | str):
            return float(value)
        raise TypeError(f"Expected numeric value, got {type(value).__name__}")

    @staticmethod
    def _int_value(value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float | str):
            return int(value)
        raise TypeError(f"Expected integer-compatible value, got {type(value).__name__}")
