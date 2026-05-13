"""Transit and forecast calculations."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import BirthData, ForecastCalculationSettings
from astrology_mcp.services.astrology_engine import AstrologyEngine
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.services.synastry_service import (
    ASPECT_DEGREES,
    MINOR_ASPECT_NAMES,
    SynastryService,
)

FORECAST_THEMES = [
    "identity_and_direction",
    "emotions_and_inner_state",
    "communication_and_learning",
    "love_and_relationships",
    "energy_and_conflict",
    "career_and_public_status",
    "home_and_family",
    "money_and_values",
    "growth_and_opportunity",
    "pressure_and_responsibility",
    "deep_transformation",
    "spiritual_and_unconscious",
]
PLANET_THEMES = {
    "Sun": ["identity_and_direction"],
    "Moon": ["emotions_and_inner_state", "home_and_family"],
    "Mercury": ["communication_and_learning"],
    "Venus": ["love_and_relationships", "money_and_values"],
    "Mars": ["energy_and_conflict"],
    "Jupiter": ["growth_and_opportunity"],
    "Saturn": ["pressure_and_responsibility", "career_and_public_status"],
    "Uranus": ["identity_and_direction"],
    "Neptune": ["spiritual_and_unconscious"],
    "Pluto": ["deep_transformation"],
}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
MAJOR_ASPECTS = {"conjunction", "opposition", "trine", "square", "sextile"}


class TransitService:
    def __init__(
        self,
        settings: Settings,
        astrology_engine: AstrologyEngine | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self._settings = settings
        self._astrology_engine = astrology_engine or AstrologyEngine(settings)
        self._profile_service = profile_service or ProfileService(settings)

    def calculate_transits(
        self,
        natal: BirthData,
        transit_datetime: datetime,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        natal.settings = settings
        natal_chart = self._astrology_engine.calculate_natal_chart(natal).model_dump()
        transit_chart = self._transit_chart(natal, transit_datetime, settings)
        aspects = self._transit_to_natal_aspects(natal_chart, transit_chart, settings)
        house_positions = self._transit_house_positions(natal_chart, transit_chart, settings)
        return {
            "chart_type": "transit",
            "natal_chart": natal_chart,
            "transit_chart": transit_chart,
            "transit_to_natal_aspects": aspects,
            "transit_house_positions": house_positions,
            "active_themes": self._active_themes(aspects),
            "calculation_meta": {
                "engine": self._settings.astrology_engine,
                "python_environment": "astro",
                "calculated_at": transit_datetime.astimezone(ZoneInfo("UTC"))
                .isoformat()
                .replace("+00:00", "Z"),
                "warnings": [],
            },
        }

    def calculate_profile_transits(
        self,
        profile_id: str,
        transit_datetime: datetime,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        natal = self._profile_service.get_birth_data(profile_id, settings)
        return self.calculate_transits(natal, transit_datetime, settings)

    def calculate_month_forecast(
        self,
        natal: BirthData,
        year: int,
        month: int,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        settings.sampling = settings.sampling or "daily"
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return self._forecast("month", natal, start, end, settings)

    def calculate_year_forecast(
        self,
        natal: BirthData,
        year: int,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        if settings.sampling == "daily":
            settings.sampling = "weekly"
        if settings.include_lunar_transits:
            settings.include_lunar_transits = False
        return self._forecast("year", natal, date(year, 1, 1), date(year, 12, 31), settings)

    def calculate_profile_month_forecast(
        self,
        profile_id: str,
        year: int,
        month: int,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        natal = self._profile_service.get_birth_data(profile_id, settings)
        return self.calculate_month_forecast(natal, year, month, settings)

    def calculate_profile_year_forecast(
        self,
        profile_id: str,
        year: int,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        natal = self._profile_service.get_birth_data(profile_id, settings)
        return self.calculate_year_forecast(natal, year, settings)

    def calculate_profile_day_forecast(
        self,
        profile_id: str,
        target_date: date,
        target_time: time,
        timezone: str | None,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        natal = self._profile_service.get_birth_data(profile_id, settings)
        zone = ZoneInfo(timezone or natal.timezone or "UTC")
        target_datetime = datetime.combine(target_date, target_time, tzinfo=zone).astimezone(
            ZoneInfo("UTC")
        )
        result = self.calculate_transits(natal, target_datetime, settings)
        natal_chart = cast(dict[str, object], result["natal_chart"])
        transit_chart = cast(dict[str, object], result["transit_chart"])
        active_transits = cast(list[dict[str, object]], result["transit_to_natal_aspects"])
        supportive = self._supportive_transits(active_transits)
        challenging = self._challenging_transits(active_transits)
        dominant_themes = cast(list[str], result["active_themes"])
        return {
            "forecast_type": "day",
            "profile_id": profile_id,
            "date": target_datetime.date().isoformat(),
            "subject": natal_chart["subject"],
            "natal_chart_summary": self._chart_summary(natal_chart),
            "transit_chart_summary": self._chart_summary(transit_chart),
            "active_transits": active_transits[:12],
            "supportive_transits": supportive[:8],
            "challenging_transits": challenging[:8],
            "dominant_themes": dominant_themes,
            "theme_summary": self._theme_summary(active_transits),
            "llm_day_context": self._llm_day_context(
                dominant_themes,
                supportive,
                challenging,
                active_transits,
            ),
            "calculation_meta": result["calculation_meta"],
        }

    def generate_transit_chart_svg(self, transit_result: dict[str, object]) -> dict[str, object]:
        try:
            subject = transit_result["natal_chart"]["subject"]["name"]  # type: ignore[index]
            transit_date = transit_result["calculation_meta"]["calculated_at"]  # type: ignore[index]
            count = len(transit_result["transit_to_natal_aspects"])  # type: ignore[arg-type]
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" '
                'viewBox="0 0 720 360"><rect width="720" height="360" fill="#fff"/>'
                '<circle cx="360" cy="180" r="125" fill="none" stroke="#333" stroke-width="2"/>'
                '<circle cx="360" cy="180" r="90" fill="none" stroke="#777" stroke-width="1"/>'
                f'<text x="40" y="45" font-family="sans-serif" font-size="24">{subject}</text>'
                f'<text x="40" y="78" font-family="sans-serif" font-size="16">{transit_date}</text>'
                f'<text x="255" y="330" font-family="sans-serif" font-size="18">'
                f'{count} transit aspects</text></svg>'
            )
            return {"svg": svg, "status": "ok", "warnings": []}
        except Exception as exc:
            return {"svg": "", "status": "error", "warnings": [type(exc).__name__]}

    def _forecast(
        self,
        forecast_type: str,
        natal: BirthData,
        start: date,
        end: date,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        timeline: list[dict[str, object]] = []
        all_transits: list[dict[str, object]] = []
        natal_chart_summary: dict[str, object] | None = None
        subject: dict[str, object] | None = None
        for current_date in self._sample_dates(start, end, settings.sampling):
            result = self.calculate_transits(
                natal,
                datetime.combine(current_date, time(12, 0), tzinfo=ZoneInfo("UTC")),
                settings,
            )
            if natal_chart_summary is None:
                natal_chart = cast(dict[str, object], result["natal_chart"])
                natal_chart_summary = {
                    "angles": natal_chart["angles"],
                    "dominants": natal_chart["dominants"],
                    "elements_balance": natal_chart["elements_balance"],
                }
                subject = cast(dict[str, object], natal_chart["subject"])
            active = cast(list[dict[str, object]], result["transit_to_natal_aspects"])
            if settings.sampling == "important_events_only" and not active:
                continue
            all_transits.extend([{**aspect, "date": current_date.isoformat()} for aspect in active])
            timeline.append(
                {
                    "date": current_date.isoformat(),
                    "active_transits": active[:8],
                    "dominant_themes": self._active_themes(active)[:4],
                }
            )

        major = [item for item in all_transits if item["aspect_type"] in MAJOR_ASPECTS]
        minor = [item for item in all_transits if item["aspect_type"] not in MAJOR_ASPECTS]
        return {
            "forecast_type": forecast_type,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "subject": subject or {},
            "natal_chart_summary": natal_chart_summary or {},
            "major_transits": major[:80],
            "minor_transits": minor[:80],
            "peak_dates": self._peak_dates(timeline),
            "theme_summary": self._theme_summary(all_transits),
            "timeline": timeline,
            "llm_forecast_context": self._llm_context(forecast_type, major, timeline),
            "calculation_meta": {
                "engine": self._settings.astrology_engine,
                "python_environment": "astro",
                "warnings": [
                    "This is interpretive astrological material, not deterministic prediction"
                ],
            },
        }

    def _transit_chart(
        self,
        natal: BirthData,
        transit_datetime: datetime,
        settings: ForecastCalculationSettings,
    ) -> dict[str, object]:
        utc = transit_datetime.astimezone(ZoneInfo("UTC"))
        transit_birth_data = BirthData(
            name=f"Transits {utc.date().isoformat()}",
            birth_date=utc.date(),
            birth_time=utc.time().replace(tzinfo=None, microsecond=0),
            birth_place=natal.birth_place,
            latitude=natal.latitude,
            longitude=natal.longitude,
            timezone="UTC",
            settings=settings,
        )
        return self._astrology_engine.calculate_natal_chart(transit_birth_data).model_dump()

    def _transit_to_natal_aspects(
        self,
        natal_chart: dict[str, object],
        transit_chart: dict[str, object],
        settings: ForecastCalculationSettings,
    ) -> list[dict[str, object]]:
        natal_points = [
            *cast(list[dict[str, object]], natal_chart["planets"]),
            *cast(dict[str, dict[str, object]], natal_chart["angles"]).values(),
        ]
        transit_planets = self._filtered_transit_planets(
            cast(list[dict[str, object]], transit_chart["planets"]),
            settings,
        )
        allowed = dict(ASPECT_DEGREES)
        if not settings.include_minor_aspects:
            allowed = {
                name: degree
                for name, degree in allowed.items()
                if name not in MINOR_ASPECT_NAMES
            }
        aspects: list[dict[str, object]] = []
        for transit in transit_planets:
            for natal in natal_points:
                distance = SynastryService._angular_distance(
                    SynastryService._float_value(transit["absolute_degree"]),
                    SynastryService._float_value(natal["absolute_degree"]),
                )
                for aspect_name, exact_angle in allowed.items():
                    orb = abs(distance - exact_angle)
                    if orb <= settings.max_orb:
                        themes = self._themes_for(transit["name"], natal["name"])
                        aspects.append(
                            {
                                "transit_planet": transit["name"],
                                "natal_point": natal["name"],
                                "aspect_type": aspect_name,
                                "orb": round(orb, 4),
                                "exact_angle": exact_angle,
                                "actual_angle": round(distance, 4),
                                "themes": themes,
                                "intensity": self._intensity(aspect_name, orb, settings.max_orb),
                            }
                        )
                        break
        return sorted(
            aspects,
            key=lambda item: (
                -SynastryService._float_value(item["intensity"]),
                SynastryService._float_value(item["orb"]),
                str(item["transit_planet"]),
            ),
        )

    def _transit_house_positions(
        self,
        natal_chart: dict[str, object],
        transit_chart: dict[str, object],
        settings: ForecastCalculationSettings,
    ) -> list[dict[str, object]]:
        houses = cast(list[dict[str, object]], natal_chart["houses"])
        positions: list[dict[str, object]] = []
        for planet in self._filtered_transit_planets(
            cast(list[dict[str, object]], transit_chart["planets"]),
            settings,
        ):
            positions.append(
                {
                    "transit_planet": planet["name"],
                    "natal_house": SynastryService._house_for_degree(
                        SynastryService._float_value(planet["absolute_degree"]),
                        houses,
                    ),
                    "themes": self._themes_for(planet["name"], None),
                }
            )
        return positions

    @staticmethod
    def _filtered_transit_planets(
        planets: list[dict[str, object]],
        settings: ForecastCalculationSettings,
    ) -> list[dict[str, object]]:
        filtered = []
        for planet in planets:
            name = str(planet["name"])
            if name == "Moon" and not settings.include_lunar_transits:
                continue
            if name in OUTER_PLANETS and not settings.include_outer_planet_transits:
                continue
            filtered.append(planet)
        return filtered

    @staticmethod
    def _sample_dates(start: date, end: date, sampling: str) -> list[date]:
        step = 7 if sampling in {"weekly", "important_events_only"} else 1
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=step)
        if dates[-1] != end and sampling == "weekly":
            dates.append(end)
        return dates

    @staticmethod
    def _themes_for(transit_planet: object, natal_point: object | None) -> list[str]:
        themes = set(PLANET_THEMES.get(str(transit_planet), []))
        if natal_point is not None:
            themes.update(PLANET_THEMES.get(str(natal_point), []))
        return sorted(themes) or ["identity_and_direction"]

    @staticmethod
    def _active_themes(aspects: list[dict[str, object]]) -> list[str]:
        themes: set[str] = set()
        for aspect in aspects:
            themes.update(str(theme) for theme in cast(list[object], aspect.get("themes", [])))
        return [theme for theme in FORECAST_THEMES if theme in themes]

    @staticmethod
    def _intensity(aspect_name: str, orb: float, max_orb: float) -> int:
        base = 100 if aspect_name in {"conjunction", "opposition", "square"} else 80
        if max_orb <= 0:
            return base
        return max(10, round(base * max(0.1, 1 - (orb / max_orb))))

    @staticmethod
    def _peak_dates(timeline: list[dict[str, object]]) -> list[dict[str, object]]:
        peaks = sorted(
            timeline,
            key=lambda item: len(cast(list[object], item["active_transits"])),
            reverse=True,
        )
        return [
            {
                "date": item["date"],
                "active_transit_count": len(cast(list[object], item["active_transits"])),
                "dominant_themes": item["dominant_themes"],
            }
            for item in peaks[:5]
        ]

    @staticmethod
    def _theme_summary(transits: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
        summary: dict[str, list[dict[str, object]]] = {theme: [] for theme in FORECAST_THEMES}
        for transit in transits:
            for theme in cast(list[object], transit.get("themes", [])):
                summary[str(theme)].append(transit)
        return {theme: values[:8] for theme, values in summary.items()}

    @staticmethod
    def _chart_summary(chart: dict[str, object]) -> dict[str, object]:
        return {
            "angles": chart["angles"],
            "dominants": chart["dominants"],
            "elements_balance": chart["elements_balance"],
        }

    @staticmethod
    def _supportive_transits(transits: list[dict[str, object]]) -> list[dict[str, object]]:
        return [item for item in transits if item["aspect_type"] in {"trine", "sextile"}]

    @staticmethod
    def _challenging_transits(transits: list[dict[str, object]]) -> list[dict[str, object]]:
        return [item for item in transits if item["aspect_type"] in {"square", "opposition"}]

    @staticmethod
    def _theme_focus(
        theme_summary: dict[str, list[dict[str, object]]],
        themes: set[str],
    ) -> list[dict[str, object]]:
        focus: list[dict[str, object]] = []
        for theme in FORECAST_THEMES:
            if theme in themes:
                focus.extend(theme_summary[theme])
        return focus[:8]

    @classmethod
    def _llm_day_context(
        cls,
        dominant_themes: list[str],
        supportive: list[dict[str, object]],
        challenging: list[dict[str, object]],
        active_transits: list[dict[str, object]],
    ) -> dict[str, object]:
        theme_summary = cls._theme_summary(active_transits)
        return {
            "main_day_themes": dominant_themes[:8],
            "emotional_focus": cls._theme_focus(
                theme_summary,
                {"emotions_and_inner_state", "home_and_family"},
            ),
            "relationship_focus": cls._theme_focus(
                theme_summary,
                {"love_and_relationships", "communication_and_learning"},
            ),
            "work_and_direction_focus": cls._theme_focus(
                theme_summary,
                {"identity_and_direction", "career_and_public_status"},
            ),
            "energy_and_conflict_focus": cls._theme_focus(
                theme_summary,
                {"energy_and_conflict", "pressure_and_responsibility"},
            ),
            "supportive_signals": supportive[:8],
            "challenging_signals": challenging[:8],
            "reflection_questions": [
                "Which theme asks for the most attention today?",
                "Where can supportive transits be used deliberately?",
                "Which challenging signals ask for patience or adjustment?",
            ],
            "recommended_tone": "balanced, non-deterministic, respectful",
            "caveats": [
                "This is interpretive astrological material, not deterministic prediction",
                "Avoid making medical, legal, financial, or irreversible life advice",
            ],
        }

    @staticmethod
    def _llm_context(
        forecast_type: str,
        major: list[dict[str, object]],
        timeline: list[dict[str, object]],
    ) -> dict[str, object]:
        supportive = [item for item in major if item["aspect_type"] in {"trine", "sextile"}]
        challenging = [item for item in major if item["aspect_type"] in {"square", "opposition"}]
        main_themes = []
        for item in timeline:
            main_themes.extend(cast(list[str], item["dominant_themes"]))
        return {
            f"main_{forecast_type}_themes": sorted(set(main_themes))[:8],
            "supportive_periods": supportive[:8],
            "challenging_periods": challenging[:8],
            "reflection_questions": [
                "What themes are repeating across the active dates?",
                "Which supportive periods are best suited for deliberate action?",
                "Which challenging periods ask for patience or restructuring?",
            ],
            "caveats": [
                "This is interpretive astrological material, not deterministic prediction"
            ],
        }
