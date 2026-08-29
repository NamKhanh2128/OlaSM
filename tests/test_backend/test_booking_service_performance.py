from __future__ import annotations

from typing import Any

import pytest

from src.backend.services.booking_service import BookingService


class _QuoteVerifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def verify_quote(self, quote: dict[str, Any]) -> None:
        self.calls.append(quote)


class _SingleRoundTripRepository:
    def __init__(self) -> None:
        self.get_quote_called = False
        self.verifier: Any = None

    async def get_quote(self, _quote_id: str) -> dict[str, object] | None:
        self.get_quote_called = True
        raise AssertionError("create_booking_from_quote must not prefetch the quote")

    async def create_booking_from_quote(self, **kwargs: object) -> dict[str, object]:
        self.verifier = kwargs.pop("quote_verifier")
        assert kwargs["quote_id"] == "quote_1"
        quote = {
            "quote_id": "quote_1",
            "user_id": "user_1",
            "session_id": "session_1",
            "pickup_place_id": "pickup_1",
            "destination_place_id": "destination_1",
            "vehicle_type": "CAR_4",
            "route_snapshot": {"duration_seconds": 600},
            "pricing_snapshot": {"pricing_version": "test"},
            "fare_amount": 100000,
            "currency": "VND",
            "context_hash": "hash",
            "signature": "signature",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "promotion_snapshot": {},
        }
        await self.verifier(quote)
        return {
            "booking_id": "booking_1",
            "status": "SEARCHING_DRIVER",
            "quoted_fare_amount": 100000,
            "currency": "VND",
            "eta_minutes": 10,
        }


@pytest.mark.asyncio
async def test_create_booking_verifies_locked_quote_without_prefetching() -> None:
    repository = _SingleRoundTripRepository()
    verifier = _QuoteVerifier()
    service = BookingService(repository=repository, quote_service=verifier)

    result = await service.create_booking_from_quote(
        {
            "quote_id": "quote_1",
            "session_id": "session_1",
            "user_id": "user_1",
            "idempotency_key": "idempotency_1",
            "pickup_place_id": "pickup_1",
            "destination_place_id": "destination_1",
            "vehicle_type": "CAR_4",
        }
    )

    assert result["booking_id"] == "booking_1"
    assert repository.get_quote_called is False
    assert verifier.calls and verifier.calls[0]["quote_id"] == "quote_1"
