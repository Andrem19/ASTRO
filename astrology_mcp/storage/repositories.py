"""Repositories for profiles and chart cache."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from astrology_mcp.domain.models import ProfileCreate, ProfileUpdate
from astrology_mcp.storage.models import ChartCacheModel, ProfileModel, ProfileTagModel, utc_now


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: ProfileCreate) -> ProfileModel:
        profile = ProfileModel(
            external_id=payload.external_id,
            name=payload.name,
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            birth_place=payload.birth_place,
            latitude=payload.latitude,
            longitude=payload.longitude,
            timezone=payload.timezone,
            notes=payload.notes,
            tags=[ProfileTagModel(tag=tag) for tag in self._normalize_tags(payload.tags)],
        )
        self._session.add(profile)
        self._session.flush()
        return profile

    def get(self, profile_id: str, include_deleted: bool = False) -> ProfileModel | None:
        statement = (
            select(ProfileModel)
            .options(selectinload(ProfileModel.tags))
            .where(ProfileModel.id == profile_id)
        )
        if not include_deleted:
            statement = statement.where(ProfileModel.deleted_at.is_(None))
        return self._session.scalar(statement)

    def list_profiles(
        self,
        include_deleted: bool = False,
        limit: int = 100,
    ) -> list[ProfileModel]:
        statement = (
            select(ProfileModel)
            .options(selectinload(ProfileModel.tags))
            .order_by(ProfileModel.created_at.desc())
            .limit(limit)
        )
        if not include_deleted:
            statement = statement.where(ProfileModel.deleted_at.is_(None))
        return list(self._session.scalars(statement))

    def update(self, profile: ProfileModel, payload: ProfileUpdate) -> ProfileModel:
        update_data = payload.model_dump(exclude_unset=True)
        tags = update_data.pop("tags", None)
        for key, value in update_data.items():
            setattr(profile, key, value)
        if tags is not None:
            profile.tags = [
                ProfileTagModel(tag=tag) for tag in self._normalize_tags(cast(list[str], tags))
            ]
        profile.updated_at = utc_now()
        self._session.flush()
        return profile

    def soft_delete(self, profile: ProfileModel) -> None:
        timestamp = utc_now()
        profile.deleted_at = timestamp
        profile.updated_at = timestamp
        self._session.flush()

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        return sorted({tag.strip() for tag in tags if tag.strip()})


class ChartCacheRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, profile_id: str, settings_hash: str) -> ChartCacheModel | None:
        statement = select(ChartCacheModel).where(
            ChartCacheModel.profile_id == profile_id,
            ChartCacheModel.settings_hash == settings_hash,
        )
        return self._session.scalar(statement)

    def upsert(
        self,
        profile_id: str,
        settings_hash: str,
        chart_json: dict[str, object],
    ) -> ChartCacheModel:
        cached = self.get(profile_id, settings_hash)
        if cached is not None:
            cached.chart_json = chart_json
            cached.updated_at = utc_now()
            self._session.flush()
            return cached
        cached = ChartCacheModel(
            profile_id=profile_id,
            settings_hash=settings_hash,
            chart_json=chart_json,
        )
        self._session.add(cached)
        self._session.flush()
        return cached

    def clear_for_profile(self, profile_id: str) -> int:
        statement = delete(ChartCacheModel).where(ChartCacheModel.profile_id == profile_id)
        result = self._session.execute(statement)
        return int(cast(Any, result).rowcount or 0)


def iso_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds") + "Z"
