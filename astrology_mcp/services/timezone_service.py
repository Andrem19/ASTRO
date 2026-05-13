"""Timezone lookup service boundary."""

from timezonefinder import TimezoneFinder


class TimezoneService:
    """Resolve an IANA timezone from coordinates."""

    def __init__(self) -> None:
        self._finder = TimezoneFinder()

    def get_timezone(self, latitude: float, longitude: float) -> str | None:
        return self._finder.timezone_at(lat=latitude, lng=longitude)
