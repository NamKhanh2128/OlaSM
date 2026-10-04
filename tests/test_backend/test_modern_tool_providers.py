"""Unit tests for modern, high-efficiency tool providers (Goong Maps & Mapbox).

Validates:
1. GoongProvider for Vietnamese address geocoding, live traffic routing, and health checks.
2. MapboxProvider for high-SLA enterprise geocoding and directions.
3. Provider factory resolution for 'goong' and 'mapbox'.
"""
from __future__ import annotations

import pytest

from src.backend.config import Settings
from src.backend.maps.contracts import PlaceCandidate, RouteResult, TrafficDataStatus
from src.backend.maps.providers.factory import get_geocoding_provider, get_routing_provider
from src.backend.maps.providers.goong import GoongProvider
from src.backend.maps.providers.mapbox import MapboxProvider


@pytest.mark.asyncio
async def test_goong_provider_vietnamese_geocoding():
    provider = GoongProvider(api_key="goong_mock_test_key")

    # Search landmark
    results = await provider.search("Vincom Bà Triệu", limit=3)
    assert len(results) >= 1
    candidate = results[0]
    assert isinstance(candidate, PlaceCandidate)
    assert "Vincom" in candidate.formatted_address
    assert candidate.latitude > 20.0
    assert candidate.longitude > 105.0


@pytest.mark.asyncio
async def test_goong_provider_reverse_geocode():
    provider = GoongProvider(api_key="goong_mock_test_key")
    res = await provider.reverse(21.0285, 105.8542)
    assert res is not None
    assert "Hà Nội" in res.formatted_address
    assert res.latitude == 21.0285


@pytest.mark.asyncio
async def test_goong_provider_live_traffic_routing():
    provider = GoongProvider(api_key="goong_mock_test_key")
    route = await provider.route(21.0285, 105.8542, 21.0116, 105.8498, profile="driving")
    assert isinstance(route, RouteResult)
    assert route.distance_meters > 0
    assert route.duration_seconds > 0
    assert route.traffic_status == TrafficDataStatus.LIVE_TRAFFIC


@pytest.mark.asyncio
async def test_mapbox_provider_geocoding_and_routing():
    provider = MapboxProvider(access_token="mapbox_mock_test_token")

    # Search
    results = await provider.search("Hồ Gươm", limit=2)
    assert len(results) >= 1
    assert "Việt Nam" in results[0].formatted_address

    # Route
    route = await provider.route(21.0285, 105.8542, 21.0074, 105.8286)
    assert route.distance_meters > 0
    assert route.duration_seconds > 0
    assert route.traffic_status == TrafficDataStatus.LIVE_TRAFFIC


def test_maps_factory_supports_goong_and_mapbox():
    # Goong geocoding
    s_goong = Settings(geocoding_provider="goong", routing_provider="goong", maps_api_key="test_key")
    geo_goong = get_geocoding_provider(s_goong)
    assert isinstance(geo_goong, GoongProvider)
    route_goong = get_routing_provider(s_goong)
    assert isinstance(route_goong, GoongProvider)

    # Mapbox geocoding
    s_mapbox = Settings(geocoding_provider="mapbox", routing_provider="mapbox", maps_api_key="test_token")
    geo_mapbox = get_geocoding_provider(s_mapbox)
    assert isinstance(geo_mapbox, MapboxProvider)
    route_mapbox = get_routing_provider(s_mapbox)
    assert isinstance(route_mapbox, MapboxProvider)
