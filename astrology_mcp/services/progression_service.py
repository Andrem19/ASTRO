"""Secondary progression and solar arc direction calculations."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, ProgressionCalculationSettings
from astrology_mcp.services.astrology_engine import AstrologyEngine
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.services.synastry_service import (
    ASPECT_DEGREES,
    MINOR_ASPECT_NAMES,
    SynastryService,
)

SUPPORTED_TECHNIQUES = {"secondary_progressions", "solar_arc_directions"}
POINT_IMPORTANCE = {
    "Sun": 10,
    "Moon": 9,
    "Ascendant": 9,
    "Medium_Coeli": 9,
    "Venus": 8,
    "Mars": 8,
    "Saturn": 8,
    "Jupiter": 8,
    "Mercury": 7,
    "Uranus": 6,
    "Neptune": 6,
    "Pluto": 6,
}
LIFE_THEME_POINTS = {
    "identity": {"Sun", "Ascendant", "Mars"},
    "family_roots": {"Moon", "Imum_Coeli"},
    "education": {"Mercury", "Jupiter"},
    "career": {"Medium_Coeli", "Sun", "Saturn", "Mars", "Jupiter"},
    "money": {"Venus", "Jupiter", "Saturn"},
    "relationships": {"Venus", "Mars", "Moon"},
    "crisis_and_transformation": {"Pluto", "Saturn", "Uranus"},
    "spiritual_development": {"Neptune", "Jupiter", "Moon"},
}
NATAL_HOUSE_THEMES = {
    2: "money",
    6: "work_and_routines",
    8: "shared_money_and_transformation",
    10: "career_and_public_status",
}


class ProgressionService:
    def __init__(
        self,
        settings: Settings,
        astrology_engine: AstrologyEngine | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self._settings = settings
        self._astrology_engine = astrology_engine or AstrologyEngine(settings)
        self._profile_service = profile_service or ProfileService(settings)

    def calculate_life_period_overview(
        self,
        natal: BirthData,
        settings: ProgressionCalculationSettings,
    ) -> dict[str, object]:
        self._validate_settings(settings)
        natal.settings = settings
        natal_chart = self._astrology_engine.calculate_natal_chart(natal).model_dump()
        periods = [
            self._period(natal, natal_chart, age_start, age_end, settings)
            for age_start, age_end in self._period_ranges(settings)
        ]
        return {
            "chart_type": "life_progressions_overview",
            "subject": natal_chart["subject"],
            "settings": settings.model_dump(),
            "natal_chart_summary": self._chart_summary(natal_chart),
            "periods": periods,
            "major_life_themes": self._major_life_themes(periods),
            "turning_point_periods": self._turning_points(periods),
            "llm_life_context": self._llm_life_context(periods),
            "calculation_meta": {
                "engine": self._settings.astrology_engine,
                "python_environment": "astro",
                "techniques": settings.techniques,
                "warnings": [
                    "Progressions and directions are interpretive symbolic techniques, "
                    "not deterministic prediction."
                ],
            },
        }

    def calculate_profile_life_period_overview(
        self,
        profile_id: str,
        settings: ProgressionCalculationSettings,
    ) -> dict[str, object]:
        natal = self._profile_service.get_birth_data(profile_id, settings)
        result = self.calculate_life_period_overview(natal, settings)
        result["profile_id"] = profile_id
        return result

    def _period(
        self,
        natal: BirthData,
        natal_chart: dict[str, object],
        age_start: int,
        age_end: int,
        settings: ProgressionCalculationSettings,
    ) -> dict[str, object]:
        samples = self._sample_ages(age_start, age_end, settings.sample_strategy)
        progressions: list[dict[str, object]] = []
        directions: list[dict[str, object]] = []
        for age in samples:
            if "secondary_progressions" in settings.techniques:
                progressions.append(self._secondary_progression(natal, natal_chart, age, settings))
            if "solar_arc_directions" in settings.techniques:
                directions.append(self._solar_arc_direction(natal, natal_chart, age, settings))
        progressed_aspects = self._merge_signals(progressions, "key_aspects")
        directed_aspects = self._merge_signals(directions, "key_aspects")
        house_activations = self._house_activations([*progressed_aspects, *directed_aspects])
        dominant_themes = self._dominant_themes([*progressed_aspects, *directed_aspects])
        return {
            "period_label": f"{age_start}-{age_end}",
            "age_start": age_start,
            "age_end": age_end,
            "date_start": self._date_at_age(natal.birth_date, age_start).isoformat(),
            "date_end": self._date_at_age(natal.birth_date, age_end).isoformat(),
            "dominant_themes": dominant_themes,
            "secondary_progressions": {"samples": progressions},
            "solar_arc_directions": {"samples": directions},
            "key_progressed_aspects": progressed_aspects[:12],
            "key_directed_aspects": directed_aspects[:12],
            "house_activations": house_activations,
            "llm_period_context": self._llm_period_context(
                dominant_themes,
                progressed_aspects,
                directed_aspects,
                house_activations,
            ),
        }

    def _secondary_progression(
        self,
        natal: BirthData,
        natal_chart: dict[str, object],
        age: float,
        settings: ProgressionCalculationSettings,
    ) -> dict[str, object]:
        progressed_datetime = self._progressed_datetime(natal, age)
        progressed_birth = BirthData(
            name=f"{natal.name} progressed age {age:g}",
            birth_date=progressed_datetime.date(),
            birth_time=progressed_datetime.time().replace(microsecond=0),
            birth_place=natal.birth_place,
            latitude=natal.latitude,
            longitude=natal.longitude,
            timezone=natal.timezone,
            settings=settings,
        )
        chart = self._astrology_engine.calculate_natal_chart(progressed_birth).model_dump()
        aspects = self._point_aspects(
            self._chart_points(chart, settings.include_angles),
            self._chart_points(natal_chart, settings.include_angles),
            settings,
            technique="secondary_progressions",
        )
        return {
            "age": age,
            "progressed_date": progressed_datetime.date().isoformat(),
            "chart_summary": self._chart_summary(chart),
            "key_aspects": aspects[:12],
        }

    def _solar_arc_direction(
        self,
        natal: BirthData,
        natal_chart: dict[str, object],
        age: float,
        settings: ProgressionCalculationSettings,
    ) -> dict[str, object]:
        progressed_datetime = self._progressed_datetime(natal, age)
        progressed_birth = BirthData(
            name=f"{natal.name} solar arc age {age:g}",
            birth_date=progressed_datetime.date(),
            birth_time=progressed_datetime.time().replace(microsecond=0),
            birth_place=natal.birth_place,
            latitude=natal.latitude,
            longitude=natal.longitude,
            timezone=natal.timezone,
            settings=settings,
        )
        progressed_chart = self._astrology_engine.calculate_natal_chart(
            progressed_birth
        ).model_dump()
        solar_arc = self._solar_arc(natal_chart, progressed_chart)
        directed_points = [
            {
                **point,
                "absolute_degree": self._normalize_degree(
                    self._float(point["absolute_degree"]) + solar_arc
                ),
            }
            for point in self._chart_points(natal_chart, settings.include_angles)
        ]
        aspects = self._point_aspects(
            directed_points,
            self._chart_points(natal_chart, settings.include_angles),
            settings,
            technique="solar_arc_directions",
        )
        return {
            "age": age,
            "progressed_date": progressed_datetime.date().isoformat(),
            "solar_arc_degrees": round(solar_arc, 6),
            "key_aspects": aspects[:12],
        }

    def _point_aspects(
        self,
        moving_points: list[dict[str, object]],
        natal_points: list[dict[str, object]],
        settings: ProgressionCalculationSettings,
        technique: str,
    ) -> list[dict[str, object]]:
        allowed = self._allowed_aspects(settings.include_minor_aspects)
        aspects: list[dict[str, object]] = []
        for moving in moving_points:
            for natal in natal_points:
                if moving["name"] == natal["name"] and technique == "solar_arc_directions":
                    continue
                distance = SynastryService._angular_distance(
                    self._float(moving["absolute_degree"]),
                    self._float(natal["absolute_degree"]),
                )
                for aspect_name, exact_angle in allowed.items():
                    orb = abs(distance - exact_angle)
                    if orb <= settings.max_orb:
                        aspects.append(
                            {
                                "technique": technique,
                                "moving_point": moving["name"],
                                "natal_point": natal["name"],
                                "aspect_type": aspect_name,
                                "orb": round(orb, 4),
                                "exact_angle": exact_angle,
                                "actual_angle": round(distance, 4),
                                "natal_house": natal.get("house"),
                                "themes": self._themes_for(moving, natal),
                                "importance": self._importance(moving, natal, aspect_name, orb),
                            }
                        )
                        break
        return sorted(
            aspects,
            key=lambda item: (-self._float(item["importance"]), self._float(item["orb"])),
        )

    @staticmethod
    def _validate_settings(settings: ProgressionCalculationSettings) -> None:
        if settings.end_age <= settings.start_age:
            raise ValueError("end_age must be greater than start_age")
        unsupported = set(settings.techniques) - SUPPORTED_TECHNIQUES
        if unsupported:
            raise ValueError(f"Unsupported progression techniques: {sorted(unsupported)}")
        if settings.sample_strategy not in {"start_mid_end", "midpoint"}:
            raise ValueError("sample_strategy must be start_mid_end or midpoint")

    @staticmethod
    def _period_ranges(settings: ProgressionCalculationSettings) -> list[tuple[int, int]]:
        ranges = []
        current = settings.start_age
        while current < settings.end_age:
            next_age = min(current + settings.period_years, settings.end_age)
            ranges.append((current, next_age))
            current = next_age
        return ranges

    @staticmethod
    def _sample_ages(start: int, end: int, strategy: str) -> list[float]:
        midpoint = round((start + end) / 2, 2)
        if strategy == "midpoint":
            return [midpoint]
        return [float(start), midpoint, float(end)]

    @staticmethod
    def _progressed_datetime(natal: BirthData, age: float) -> datetime:
        zone = ZoneInfo(natal.timezone or "UTC")
        birth_datetime = datetime.combine(natal.birth_date, natal.birth_time, tzinfo=zone)
        return birth_datetime + timedelta(days=age)

    @staticmethod
    def _date_at_age(birth_date: date, age: int) -> date:
        try:
            return birth_date.replace(year=birth_date.year + age)
        except ValueError:
            return birth_date.replace(year=birth_date.year + age, day=28)

    @staticmethod
    def _chart_points(chart: dict[str, object], include_angles: bool) -> list[dict[str, object]]:
        points = list(cast(list[dict[str, object]], chart["planets"]))
        if include_angles:
            points.extend(cast(dict[str, dict[str, object]], chart["angles"]).values())
        return points

    @staticmethod
    def _allowed_aspects(include_minor: bool) -> dict[str, int]:
        if include_minor:
            return dict(ASPECT_DEGREES)
        return {
            name: degree
            for name, degree in ASPECT_DEGREES.items()
            if name not in MINOR_ASPECT_NAMES
        }

    @classmethod
    def _solar_arc(
        cls,
        natal_chart: dict[str, object],
        progressed_chart: dict[str, object],
    ) -> float:
        natal_sun = cls._point_by_name(cls._chart_points(natal_chart, False), "Sun")
        progressed_sun = cls._point_by_name(cls._chart_points(progressed_chart, False), "Sun")
        return cls._normalize_degree(
            cls._float(progressed_sun["absolute_degree"]) - cls._float(natal_sun["absolute_degree"])
        )

    @staticmethod
    def _point_by_name(points: list[dict[str, object]], name: str) -> dict[str, object]:
        for point in points:
            if point["name"] == name:
                return point
        raise ValueError(f"Point not found: {name}")

    @staticmethod
    def _normalize_degree(value: float) -> float:
        return round(value % 360, 6)

    @staticmethod
    def _float(value: object) -> float:
        if isinstance(value, int | float | str):
            return float(value)
        raise TypeError(f"Expected numeric value, got {type(value).__name__}")

    @classmethod
    def _themes_for(cls, moving: dict[str, object], natal: dict[str, object]) -> list[str]:
        themes = set()
        names = {str(moving["name"]), str(natal["name"])}
        for theme, points in LIFE_THEME_POINTS.items():
            if names & points:
                themes.add(theme)
        house = natal.get("house")
        if isinstance(house, int) and house in NATAL_HOUSE_THEMES:
            themes.add(NATAL_HOUSE_THEMES[house])
        return sorted(themes) or ["identity"]

    @classmethod
    def _importance(
        cls,
        moving: dict[str, object],
        natal: dict[str, object],
        aspect_name: str,
        orb: float,
    ) -> float:
        point_score = POINT_IMPORTANCE.get(str(moving["name"]), 5) + POINT_IMPORTANCE.get(
            str(natal["name"]), 5
        )
        aspect_score = 5 if aspect_name in {"conjunction", "opposition", "square"} else 3
        return round(point_score + aspect_score + max(0, 3 - orb), 4)

    @staticmethod
    def _merge_signals(samples: list[dict[str, object]], key: str) -> list[dict[str, object]]:
        merged: dict[tuple[object, object, object, object], dict[str, object]] = {}
        for sample in samples:
            for aspect in cast(list[dict[str, object]], sample[key]):
                identity = (
                    aspect["technique"],
                    aspect["moving_point"],
                    aspect["natal_point"],
                    aspect["aspect_type"],
                )
                existing = merged.get(identity)
                if existing is None or ProgressionService._float(aspect["orb"]) < (
                    ProgressionService._float(existing["orb"])
                ):
                    merged[identity] = {**aspect, "sample_age": sample["age"]}
        return sorted(
            merged.values(),
            key=lambda item: (
                -ProgressionService._float(item["importance"]),
                ProgressionService._float(item["orb"]),
            ),
        )

    @staticmethod
    def _dominant_themes(aspects: list[dict[str, object]]) -> list[str]:
        counts: dict[str, int] = {}
        for aspect in aspects:
            for theme in cast(list[str], aspect["themes"]):
                counts[theme] = counts.get(theme, 0) + 1
        return [theme for theme, _count in sorted(counts.items(), key=lambda item: -item[1])[:8]]

    @staticmethod
    def _house_activations(aspects: list[dict[str, object]]) -> list[dict[str, object]]:
        counts: dict[int, int] = {}
        for aspect in aspects:
            house = aspect.get("natal_house")
            if isinstance(house, int):
                counts[house] = counts.get(house, 0) + 1
        return [
            {"house": house, "count": count, "theme": NATAL_HOUSE_THEMES.get(house, "general")}
            for house, count in sorted(counts.items(), key=lambda item: -item[1])[:8]
        ]

    @staticmethod
    def _chart_summary(chart: dict[str, object]) -> dict[str, object]:
        return {
            "angles": chart["angles"],
            "dominants": chart["dominants"],
            "elements_balance": chart["elements_balance"],
        }

    @staticmethod
    def _major_life_themes(periods: list[dict[str, object]]) -> list[str]:
        counts: dict[str, int] = {}
        for period in periods:
            for theme in cast(list[str], period["dominant_themes"]):
                counts[theme] = counts.get(theme, 0) + 1
        return [theme for theme, _count in sorted(counts.items(), key=lambda item: -item[1])[:10]]

    @staticmethod
    def _turning_points(periods: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "period_label": period["period_label"],
                "age_start": period["age_start"],
                "age_end": period["age_end"],
                "dominant_themes": period["dominant_themes"],
                "signal_count": len(cast(list[object], period["key_progressed_aspects"]))
                + len(cast(list[object], period["key_directed_aspects"])),
            }
            for period in sorted(
                periods,
                key=lambda item: len(cast(list[object], item["key_progressed_aspects"]))
                + len(cast(list[object], item["key_directed_aspects"])),
                reverse=True,
            )[:5]
        ]

    @staticmethod
    def _llm_period_context(
        themes: list[str],
        progressed: list[dict[str, object]],
        directed: list[dict[str, object]],
        houses: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "main_period_themes": themes,
            "inner_development_signals": progressed[:8],
            "outer_turning_point_signals": directed[:8],
            "activated_life_areas": houses,
            "recommended_tone": "balanced, non-deterministic, reflective",
        }

    @staticmethod
    def _llm_life_context(periods: list[dict[str, object]]) -> dict[str, object]:
        return {
            "recommended_tone": "balanced, non-deterministic, reflective",
            "period_count": len(periods),
            "important_caveats": [
                "Astrology is interpretive, not deterministic.",
                "Avoid medical, legal, financial, or irreversible life advice.",
            ],
            "writing_guidance": [
                "Describe periods as symbolic developmental themes.",
                "Separate inner development from external turning points.",
                "Use dates and ages as approximate interpretive windows.",
            ],
        }
