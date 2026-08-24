"""Durable booking boundary for the LiveKit booking task."""

from __future__ import annotations

from typing import Protocol

from src.backend.services.booking_service import BookingService
from src.voice_agent.session_data import BookingDraft, BookingResult


class DurableBookingCreator(Protocol):
    async def create_booking_from_quote(self, payload: dict[str, object]) -> dict[str, object]: ...


class DurableBookingCanceller(Protocol):
    async def cancel_booking_durable(
        self, booking_id: str, idempotency_key: str, user_id: str | None = None
    ) -> dict[str, object] | None: ...


class BookingToolsService:
    """Adapt a confirmed LiveKit draft to the existing durable BookingService."""

    def __init__(self, booking_service: DurableBookingCreator | DurableBookingCanceller | None = None) -> None:
        self._booking_service = booking_service or BookingService()

    async def create(
        self,
        *,
        user_id: str,
        app_session_id: str,
        draft: BookingDraft,
    ) -> BookingResult:
        quote = draft.require_creatable()
        idempotency_key = f"{app_session_id}:create_booking:{quote.fingerprint}"
        assert draft.pickup is not None and draft.destination is not None
        result = await self._booking_service.create_booking_from_quote(
            {
                "quote_id": quote.quote_id,
                "fare_estimate_id": quote.quote_id,
                "idempotency_key": idempotency_key,
                "session_id": app_session_id,
                "user_id": user_id,
                "pickup_place_id": quote.pickup_place_id,
                "destination_place_id": quote.destination_place_id,
                "vehicle_type": quote.vehicle_type,
                "pickup": draft.pickup.model_dump(mode="json"),
                "destination": draft.destination.model_dump(mode="json"),
            }
        )
        return BookingResult(
            booking_id=str(result["booking_id"]),
            status=str(result["status"]),
            estimated_fare=int(result.get("quoted_fare_amount") or result.get("estimated_fare") or quote.fare_amount),
            currency=str(result.get("currency") or quote.currency),
            eta_minutes=int(result.get("eta_minutes") or quote.eta_minutes),
        )

    async def cancel(
        self, *, booking_id: str, user_id: str, app_session_id: str
    ) -> BookingResult | None:
        idempotency_key = f"{app_session_id}:cancel_booking:{booking_id}"
        cancel_booking_durable = getattr(self._booking_service, "cancel_booking_durable", None)
        if not callable(cancel_booking_durable):
            raise TypeError("booking service does not support durable cancellation")
        result = await cancel_booking_durable(booking_id, idempotency_key, user_id)
        if result is None:
            return None
        return BookingResult(
            booking_id=str(result["booking_id"]),
            status=str(result["status"]),
            estimated_fare=int(result.get("quoted_fare_amount") or result.get("estimated_fare") or 0),
            currency=str(result.get("currency") or "VND"),
            eta_minutes=int(result.get("eta_minutes") or 0),
        )
