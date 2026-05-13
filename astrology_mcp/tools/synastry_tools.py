"""Synastry MCP tool wrappers."""

from astrology_mcp.config import get_settings
from astrology_mcp.domain.models import BirthData, SynastryCalculationSettings
from astrology_mcp.logging import log_tool_call
from astrology_mcp.services.synastry_service import SynastryService


def _service() -> SynastryService:
    return SynastryService(get_settings())


@log_tool_call("calculate_synastry")
def calculate_synastry(
    person_a: dict[str, object],
    person_b: dict[str, object],
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    synastry_settings = SynastryCalculationSettings.model_validate(settings or {})
    birth_a = BirthData.model_validate({**person_a, "settings": synastry_settings.model_dump()})
    birth_b = BirthData.model_validate({**person_b, "settings": synastry_settings.model_dump()})
    return _service().calculate_synastry(birth_a, birth_b, synastry_settings)


@log_tool_call("calculate_profile_synastry")
def calculate_profile_synastry(
    profile_id_a: str,
    profile_id_b: str,
    settings: dict[str, object] | None = None,
    use_cache: bool = True,
) -> dict[str, object]:
    synastry_settings = SynastryCalculationSettings.model_validate(settings or {})
    return _service().calculate_profile_synastry(
        profile_id_a,
        profile_id_b,
        synastry_settings,
        use_cache=use_cache,
    )


@log_tool_call("calculate_relationship_summary")
def calculate_relationship_summary(synastry: dict[str, object]) -> dict[str, object]:
    return _service().calculate_relationship_summary(synastry)


@log_tool_call("generate_synastry_chart_svg")
def generate_synastry_chart_svg(
    person_a: dict[str, object] | None = None,
    person_b: dict[str, object] | None = None,
    profile_id_a: str | None = None,
    profile_id_b: str | None = None,
    settings: dict[str, object] | None = None,
) -> dict[str, object]:
    service = _service()
    synastry_settings = SynastryCalculationSettings.model_validate(settings or {})
    if profile_id_a and profile_id_b:
        synastry = service.calculate_profile_synastry(
            profile_id_a,
            profile_id_b,
            synastry_settings,
            use_cache=True,
        )
    elif person_a and person_b:
        birth_a = BirthData.model_validate({**person_a, "settings": synastry_settings.model_dump()})
        birth_b = BirthData.model_validate({**person_b, "settings": synastry_settings.model_dump()})
        synastry = service.calculate_synastry(birth_a, birth_b, synastry_settings)
    else:
        raise ValueError("Provide either person_a/person_b or profile_id_a/profile_id_b")
    return service.generate_synastry_chart_svg(synastry)
