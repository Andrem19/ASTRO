import os
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from astrology_mcp.config import Settings
from astrology_mcp.domain.models import ChartCalculationSettings, ProfileCreate, ProfileUpdate
from astrology_mcp.services.profile_service import ProfileService
from astrology_mcp.storage.database import create_database_engine, create_session_factory
from astrology_mcp.storage.models import Base, ChartCacheModel, ProfileTagModel


@pytest.fixture
def profile_service() -> ProfileService:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    return ProfileService(Settings(), session_factory=session_factory)


def _profile_payload(**overrides: Any) -> ProfileCreate:
    payload: dict[str, Any] = {
        "external_id": "client_123",
        "name": "Person A",
        "birth_date": "1990-05-17",
        "birth_time": "14:35:00",
        "birth_place": "London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
        "tags": ["client", "vip"],
        "notes": "Optional private notes",
    }
    payload.update(overrides)
    return ProfileCreate.model_validate(payload)


def _create_profile(service: ProfileService) -> str:
    created = service.create_profile(_profile_payload())
    profile_id = created["profile_id"]
    assert profile_id is not None
    return profile_id


def test_create_profile(profile_service: ProfileService) -> None:
    created = profile_service.create_profile(_profile_payload())

    assert created["external_id"] == "client_123"
    assert created["status"] == "created"
    assert created["profile_id"]


def test_get_profile_with_private_notes(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)

    profile = profile_service.get_profile(profile_id, include_private_notes=True)

    assert profile.id == profile_id
    assert profile.notes == "Optional private notes"
    assert profile.tags == ["client", "vip"]


def test_list_profiles_omits_notes(profile_service: ProfileService) -> None:
    _create_profile(profile_service)

    profiles = profile_service.list_profiles()

    assert len(profiles) == 1
    assert profiles[0].notes is None


def test_update_profile(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)

    updated = profile_service.update_profile(
        profile_id,
        ProfileUpdate.model_validate({"name": "Person B", "tags": ["updated"]}),
    )

    assert updated.name == "Person B"
    assert updated.tags == ["updated"]


def test_soft_delete(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)

    result = profile_service.delete_profile(profile_id)
    deleted = profile_service.get_profile(profile_id, include_deleted=True)

    assert result == {"profile_id": profile_id, "status": "deleted"}
    assert deleted.id == profile_id


def test_deleted_profile_is_hidden_from_normal_get(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)
    profile_service.delete_profile(profile_id)

    with pytest.raises(ValueError, match="Profile not found"):
        profile_service.get_profile(profile_id)


def test_calculate_chart_by_profile_id(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)

    chart = profile_service.calculate_profile_natal_chart(
        profile_id,
        ChartCalculationSettings(),
        use_cache=True,
    )

    assert chart["chart_type"] == "natal"
    assert chart["subject"]["name"] == "Person A"
    assert chart["cache"] == {
        "hit": False,
        "settings_hash": ProfileService.settings_hash(ChartCalculationSettings()),
    }


def test_profile_chart_cache(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)
    settings = ChartCalculationSettings()

    first = profile_service.calculate_profile_natal_chart(profile_id, settings, use_cache=True)
    second = profile_service.calculate_profile_natal_chart(profile_id, settings, use_cache=True)

    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert first["subject"] == second["subject"]


def test_clear_profile_chart_cache(profile_service: ProfileService) -> None:
    profile_id = _create_profile(profile_service)
    settings = ChartCalculationSettings()
    profile_service.calculate_profile_natal_chart(profile_id, settings, use_cache=True)

    result = profile_service.clear_profile_chart_cache(profile_id)
    next_chart = profile_service.calculate_profile_natal_chart(profile_id, settings, use_cache=True)

    assert result["cleared"] == 1
    assert next_chart["cache"]["hit"] is False


def test_invalid_profile_data() -> None:
    with pytest.raises(ValidationError, match="birth_date"):
        _profile_payload(birth_date="1990-17-05")


def test_alembic_migration_runs_inside_astro(tmp_path: Path) -> None:
    assert os.environ.get("CONDA_DEFAULT_ENV") == "astro"
    database_path = tmp_path / "profiles.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path}")

    command.upgrade(config, "head")

    inspector = inspect(create_engine(f"sqlite+pysqlite:///{database_path}"))
    assert {"profiles", "profile_tags", "chart_cache"} <= set(inspector.get_table_names())


def test_sqlite_database_file_is_created(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "astrology.sqlite3"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{database_path}",
        SQLITE_DB_PATH=str(database_path),
    )
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)

    assert database_path.exists()


def test_sqlite_tables_created(tmp_path: Path) -> None:
    database_path = tmp_path / "astrology.sqlite3"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{database_path}",
        SQLITE_DB_PATH=str(database_path),
    )
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)

    assert {"profiles", "profile_tags", "chart_cache"} <= set(inspect(engine).get_table_names())


def test_sqlite_foreign_keys_are_enforced(tmp_path: Path) -> None:
    database_path = tmp_path / "astrology.sqlite3"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{database_path}",
        SQLITE_DB_PATH=str(database_path),
    )
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(ProfileTagModel(profile_id="missing", tag="orphan"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_sqlite_chart_cache_persists_after_reconnect(tmp_path: Path) -> None:
    database_path = tmp_path / "astrology.sqlite3"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{database_path}",
        SQLITE_DB_PATH=str(database_path),
    )
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    service = ProfileService(Settings(), session_factory=session_factory)
    profile_id = _create_profile(service)

    with session_factory() as session:
        session.add(
            ChartCacheModel(
                profile_id=profile_id,
                settings_hash="hash",
                chart_json={"chart_type": "natal"},
            )
        )
        session.commit()

    reconnect_engine = create_database_engine(settings)
    reconnect_factory = create_session_factory(reconnect_engine)
    with reconnect_factory() as session:
        cached = session.query(ChartCacheModel).filter_by(profile_id=profile_id).one()
        assert cached.chart_json == {"chart_type": "natal"}


def test_sqlite_pragmas_are_enabled(tmp_path: Path) -> None:
    database_path = tmp_path / "astrology.sqlite3"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{database_path}",
        SQLITE_DB_PATH=str(database_path),
        SQLITE_BUSY_TIMEOUT_MS=7000,
    )
    engine = create_database_engine(settings)
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 7000
        assert str(connection.execute(text("PRAGMA journal_mode")).scalar_one()).lower() == "wal"
