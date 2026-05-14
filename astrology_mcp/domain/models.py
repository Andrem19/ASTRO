"""Shared domain models."""

from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


class RuntimeInfo(BaseModel):
    python_environment: str = "astro"


class FeatureFlags(BaseModel):
    natal_chart: bool = True
    profiles: bool = True
    synastry: bool = True
    transits: bool = True
    forecast: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "astrology-mcp-server"
    version: str = "0.1.0"
    environment: str = "astro"


class ServerInfoResponse(BaseModel):
    name: str = "astrology-mcp-server"
    transport: str = "streamable_http"
    runtime: RuntimeInfo = Field(default_factory=RuntimeInfo)
    features: FeatureFlags = Field(default_factory=FeatureFlags)


class SupportedFeaturesResponse(BaseModel):
    planned_tools: list[str]


class GeoLocation(BaseModel):
    birth_place: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str


class ChartCalculationSettings(BaseModel):
    house_system: str = "Placidus"
    zodiac_type: str = "tropical"
    include_minor_aspects: bool = False
    include_asteroids: bool = False
    language: str = "en"


class SynastryCalculationSettings(ChartCalculationSettings):
    max_orb: float = Field(default=8, ge=0, le=15)


class ForecastCalculationSettings(SynastryCalculationSettings):
    sampling: str = "daily"
    include_lunar_transits: bool = True
    include_outer_planet_transits: bool = True


class ProgressionCalculationSettings(ChartCalculationSettings):
    start_age: int = Field(default=0, ge=0, le=120)
    end_age: int = Field(default=84, ge=1, le=120)
    period_years: int = Field(default=7, ge=1, le=30)
    techniques: list[str] = Field(
        default_factory=lambda: ["secondary_progressions", "solar_arc_directions"]
    )
    sample_strategy: str = "start_mid_end"
    max_orb: float = Field(default=2, ge=0, le=10)
    include_angles: bool = True


class BirthData(BaseModel):
    name: str
    birth_date: date
    birth_time: time
    birth_place: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    settings: ChartCalculationSettings = Field(default_factory=ChartCalculationSettings)


class PlanetPosition(BaseModel):
    name: str
    sign: str
    degree_in_sign: float
    absolute_degree: float
    house: int | None
    element: str
    modality: str
    retrograde: bool


class HousePosition(BaseModel):
    house_number: int
    name: str
    sign: str
    degree_in_sign: float
    absolute_degree: float


class Aspect(BaseModel):
    planet_a: str
    planet_b: str
    aspect_type: str
    orb: float
    exact_angle: float
    actual_angle: float
    movement: str | None = None


class NatalChart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart_type: str = "natal"
    subject: dict[str, object]
    settings: dict[str, object]
    angles: dict[str, dict[str, object]]
    planets: list[PlanetPosition]
    houses: list[HousePosition]
    aspects: list[Aspect]
    elements_balance: dict[str, object]
    modalities_balance: dict[str, object]
    hemispheres: dict[str, object]
    dominants: dict[str, object]
    calculation_meta: dict[str, object]


class ProfileCreate(BaseModel):
    external_id: str | None = None
    name: str
    birth_date: date
    birth_time: time
    birth_place: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProfileUpdate(BaseModel):
    external_id: str | None = None
    name: str | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    birth_place: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ProfileResponse(BaseModel):
    id: str
    external_id: str | None
    name: str
    birth_date: str
    birth_time: str
    birth_place: str | None
    latitude: float | None
    longitude: float | None
    timezone: str | None
    tags: list[str]
    created_at: str
    updated_at: str
    notes: str | None = None
