"""Provider factory — instantiate the configured geocoding/routing providers.

Reads from ``Settings`` to determine which provider implementation to use and
returns a configured instance. Supports Nominatim, OSRM, Goong Maps, and Mapbox.
"""
from __future__ import annotations

from src.backend.config import Settings, get_settings
from src.backend.maps.providers.base import GeocodingProvider, RoutingProvider
from src.backend.maps.providers.goong import GoongProvider
from src.backend.maps.providers.mapbox import MapboxProvider
from src.backend.maps.providers.nominatim import NominatimProvider
from src.backend.maps.providers.osrm import OSRMProvider


def get_geocoding_provider(settings: Settings | None = None) -> GeocodingProvider:
    """Return the configured geocoding provider instance."""
    s = settings or get_settings()
    provider_name = s.geocoding_provider.lower()

    if provider_name == "goong":
        return GoongProvider(
            api_key=s.maps_api_key or "goong_mock_api_key",
            base_url=s.maps_base_url or "https://rsapi.goong.io",
            timeout=s.map_request_timeout_seconds,
        )

    if provider_name == "mapbox":
        return MapboxProvider(
            access_token=s.maps_api_key or "mapbox_mock_token",
            base_url=s.maps_base_url or "https://api.mapbox.com",
            timeout=s.map_request_timeout_seconds,
        )

    if provider_name == "nominatim":
        return NominatimProvider(
            base_url=s.nominatim_base_url,
            timeout=s.map_request_timeout_seconds,
            country_code=s.map_country_code,
        )

    raise ValueError(f"Unknown geocoding provider: {provider_name}")


def get_routing_provider(settings: Settings | None = None) -> RoutingProvider:
    """Return the configured routing provider instance."""
    s = settings or get_settings()
    provider_name = s.routing_provider.lower()

    if provider_name == "goong":
        return GoongProvider(
            api_key=s.maps_api_key or "goong_mock_api_key",
            base_url=s.maps_base_url or "https://rsapi.goong.io",
            timeout=s.map_request_timeout_seconds,
        )

    if provider_name == "mapbox":
        return MapboxProvider(
            access_token=s.maps_api_key or "mapbox_mock_token",
            base_url=s.maps_base_url or "https://api.mapbox.com",
            timeout=s.map_request_timeout_seconds,
        )

    if provider_name == "osrm":
        return OSRMProvider(
            base_url=s.osrm_base_url,
            timeout=s.map_request_timeout_seconds,
            source_data_version=s.osm_data_version,
        )

    raise ValueError(f"Unknown routing provider: {provider_name}")
