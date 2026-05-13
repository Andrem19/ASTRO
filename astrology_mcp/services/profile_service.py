"""Profile use cases and chart-cache orchestration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from astrology_mcp.config import Settings
from astrology_mcp.domain.models import (
    BirthData,
    ChartCalculationSettings,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from astrology_mcp.services.astrology_engine import AstrologyEngine
from astrology_mcp.storage.database import create_database_engine, create_session_factory
from astrology_mcp.storage.repositories import ChartCacheRepository, ProfileRepository, iso_datetime


class ProfileService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session] | None = None,
        astrology_engine_factory: Callable[[], AstrologyEngine] | None = None,
    ) -> None:
        self._settings = settings
        if session_factory is None:
            engine = create_database_engine(settings)
            session_factory = create_session_factory(engine)
        self._session_factory = session_factory
        self._astrology_engine_factory = astrology_engine_factory or (
            lambda: AstrologyEngine(settings)
        )

    def create_profile(self, payload: ProfileCreate) -> dict[str, str | None]:
        with self._session_factory() as session:
            repository = ProfileRepository(session)
            profile = repository.create(payload)
            session.commit()
            return {
                "profile_id": profile.id,
                "external_id": profile.external_id,
                "status": "created",
            }

    def get_profile(
        self,
        profile_id: str,
        include_private_notes: bool = False,
        include_deleted: bool = False,
    ) -> ProfileResponse:
        with self._session_factory() as session:
            profile = ProfileRepository(session).get(profile_id, include_deleted=include_deleted)
            if profile is None:
                raise ValueError(f"Profile not found: {profile_id}")
            return self._profile_response(profile, include_private_notes=include_private_notes)

    def get_birth_data(
        self,
        profile_id: str,
        settings: ChartCalculationSettings,
    ) -> BirthData:
        with self._session_factory() as session:
            profile = ProfileRepository(session).get(profile_id)
            if profile is None:
                raise ValueError(f"Profile not found: {profile_id}")
            return BirthData(
                name=profile.name,
                birth_date=profile.birth_date,
                birth_time=profile.birth_time,
                birth_place=profile.birth_place,
                latitude=profile.latitude,
                longitude=profile.longitude,
                timezone=profile.timezone,
                settings=settings,
            )

    def list_profiles(
        self,
        include_deleted: bool = False,
        limit: int = 100,
    ) -> list[ProfileResponse]:
        with self._session_factory() as session:
            profiles = ProfileRepository(session).list_profiles(
                include_deleted=include_deleted,
                limit=limit,
            )
            return [
                self._profile_response(profile, include_private_notes=False)
                for profile in profiles
            ]

    def update_profile(self, profile_id: str, payload: ProfileUpdate) -> ProfileResponse:
        with self._session_factory() as session:
            repository = ProfileRepository(session)
            profile = repository.get(profile_id)
            if profile is None:
                raise ValueError(f"Profile not found: {profile_id}")
            updated = repository.update(profile, payload)
            ChartCacheRepository(session).clear_for_profile(profile_id)
            session.commit()
            return self._profile_response(updated, include_private_notes=True)

    def delete_profile(self, profile_id: str) -> dict[str, str]:
        with self._session_factory() as session:
            repository = ProfileRepository(session)
            profile = repository.get(profile_id)
            if profile is None:
                raise ValueError(f"Profile not found: {profile_id}")
            repository.soft_delete(profile)
            session.commit()
            return {"profile_id": profile_id, "status": "deleted"}

    def calculate_profile_natal_chart(
        self,
        profile_id: str,
        settings: ChartCalculationSettings,
        use_cache: bool = True,
    ) -> dict[str, object]:
        settings_hash = self.settings_hash(settings)
        with self._session_factory() as session:
            profile = ProfileRepository(session).get(profile_id)
            if profile is None:
                raise ValueError(f"Profile not found: {profile_id}")
            cache_repository = ChartCacheRepository(session)
            cached = cache_repository.get(profile_id, settings_hash)
            if cached is not None and use_cache:
                cached_payload = dict(cached.chart_json)
                cached_payload["cache"] = {"hit": True, "settings_hash": settings_hash}
                return cached_payload

            birth_data = BirthData(
                name=profile.name,
                birth_date=profile.birth_date,
                birth_time=profile.birth_time,
                birth_place=profile.birth_place,
                latitude=profile.latitude,
                longitude=profile.longitude,
                timezone=profile.timezone,
                settings=settings,
            )
            chart_json = self._astrology_engine_factory().calculate_natal_chart(
                birth_data
            ).model_dump()
            cache_repository.upsert(profile_id, settings_hash, chart_json)
            session.commit()
            result = dict(chart_json)
            result["cache"] = {"hit": False, "settings_hash": settings_hash}
            return result

    def clear_profile_chart_cache(self, profile_id: str) -> dict[str, int | str]:
        with self._session_factory() as session:
            if ProfileRepository(session).get(profile_id) is None:
                raise ValueError(f"Profile not found: {profile_id}")
            deleted = ChartCacheRepository(session).clear_for_profile(profile_id)
            session.commit()
            return {"profile_id": profile_id, "cleared": deleted}

    @staticmethod
    def settings_hash(settings: ChartCalculationSettings) -> str:
        payload = json.dumps(settings.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _profile_response(profile: Any, include_private_notes: bool) -> ProfileResponse:
        return ProfileResponse(
            id=profile.id,
            external_id=profile.external_id,
            name=profile.name,
            birth_date=profile.birth_date.isoformat(),
            birth_time=profile.birth_time.isoformat(),
            birth_place=profile.birth_place,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timezone=profile.timezone,
            tags=[tag.tag for tag in profile.tags],
            created_at=iso_datetime(profile.created_at),
            updated_at=iso_datetime(profile.updated_at),
            notes=profile.notes if include_private_notes else None,
        )
