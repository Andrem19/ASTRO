"""SQLAlchemy persistence models."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def uuid_string() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.utcnow()


class ProfileModel(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time] = mapped_column(Time, nullable=False)
    birth_place: Mapped[str | None] = mapped_column(String(512))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    timezone: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    tags: Mapped[list[ProfileTagModel]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chart_cache: Mapped[list[ChartCacheModel]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProfileTagModel(Base):
    __tablename__ = "profile_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    profile: Mapped[ProfileModel] = relationship(back_populates="tags")


class ChartCacheModel(Base):
    __tablename__ = "chart_cache"
    __table_args__ = (UniqueConstraint("profile_id", "settings_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    settings_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chart_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    profile: Mapped[ProfileModel] = relationship(back_populates="chart_cache")
