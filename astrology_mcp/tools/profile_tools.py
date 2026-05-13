"""Profile MCP tool wrappers."""

from astrology_mcp.config import get_settings
from astrology_mcp.domain.models import ChartCalculationSettings, ProfileCreate, ProfileUpdate
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.profile_service import ProfileService


def _service() -> ProfileService:
    return ProfileService(get_settings())


@log_tool_call("create_profile")
def create_profile(
    name: str,
    birth_date: str,
    birth_time: str,
    external_id: str | None = None,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, str | None]:
    payload = ProfileCreate.model_validate(
        {
            "external_id": external_id,
            "name": name,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "tags": tags or [],
            "notes": notes,
        }
    )
    return _service().create_profile(payload)


@log_tool_call("get_profile")
def get_profile(
    profile_id: str,
    include_private_notes: bool = False,
    include_deleted: bool = False,
) -> dict[str, object]:
    return _service().get_profile(
        profile_id,
        include_private_notes=include_private_notes,
        include_deleted=include_deleted,
    ).model_dump()


@log_tool_call("get_profile_by_name")
def get_profile_by_name(
    name: str,
    include_private_notes: bool = False,
    include_deleted: bool = False,
    limit: int = 10,
) -> dict[str, object]:
    return _service().get_profile_by_name(
        name,
        include_private_notes=include_private_notes,
        include_deleted=include_deleted,
        limit=limit,
    )


@log_tool_call("list_profiles")
def list_profiles(include_deleted: bool = False, limit: int = 100) -> dict[str, object]:
    profiles = _service().list_profiles(include_deleted=include_deleted, limit=limit)
    return {"profiles": [profile.model_dump(exclude={"notes"}) for profile in profiles]}


@log_tool_call("update_profile")
def update_profile(profile_id: str, updates: dict[str, object]) -> dict[str, object]:
    payload = ProfileUpdate.model_validate(updates)
    return _service().update_profile(profile_id, payload).model_dump()


@log_tool_call("delete_profile")
def delete_profile(profile_id: str) -> dict[str, str]:
    return _service().delete_profile(profile_id)


@log_tool_call("calculate_profile_natal_chart")
def calculate_profile_natal_chart(
    profile_id: str,
    settings: dict[str, object] | None = None,
    use_cache: bool = True,
) -> dict[str, object]:
    chart_settings = ChartCalculationSettings.model_validate(settings or {})
    return _service().calculate_profile_natal_chart(
        profile_id,
        settings=chart_settings,
        use_cache=use_cache,
    )


@log_tool_call("clear_profile_chart_cache")
def clear_profile_chart_cache(profile_id: str) -> dict[str, int | str]:
    return _service().clear_profile_chart_cache(profile_id)
