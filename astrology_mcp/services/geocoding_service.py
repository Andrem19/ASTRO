"""Geocoding service boundary."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float


class GeocodingService:
    """Geocode places with geopy when coordinates are not supplied."""

    def geocode(self, query: str) -> Coordinates | None:
        from geopy.geocoders import Nominatim

        geocoder = Nominatim(user_agent="astrology-mcp-server")
        location = geocoder.geocode(query, timeout=5)
        if location is None:
            return None
        return Coordinates(latitude=float(location.latitude), longitude=float(location.longitude))
