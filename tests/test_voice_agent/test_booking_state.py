import pytest

from src.voice_agent.session_data import (
    BookingDraft,
    BookingResult,
    PlaceCandidate,
    QuoteSnapshot,
    vehicle_spoken_label,
)
from src.voice_agent.tools import BookingToolsService, QuoteToolsService


def _place(place_id: str, name: str) -> PlaceCandidate:
    return PlaceCandidate(
        place_id=place_id,
        display_name=name,
        address=name,
        provider="test",
        city="Hà Nội",
    )


def _quoted_draft() -> BookingDraft:
    draft = BookingDraft()
    pickup = _place("place_pickup", "VinUni")
    destination = _place("place_destination", "Hồ Gươm")
    draft.set_candidates("pickup", "VinUni", [pickup])
    draft.select_place("pickup", pickup.place_id)
    draft.set_candidates("destination", "Hồ Gươm", [destination])
    draft.select_place("destination", destination.place_id)
    draft.set_vehicle_type("CAR_4")
    draft.set_quote(
        QuoteSnapshot(
            quote_id="quote_test",
            pickup_place_id=pickup.place_id,
            destination_place_id=destination.place_id,
            vehicle_type="CAR_4",
            fare_amount=100_000,
            currency="VND",
            distance_km=10,
            eta_minutes=25,
            expires_at="2099-01-01T00:00:00+00:00",
        )
    )
    return draft


class FakeQuoteService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def issue_quote(self, **payload: object) -> dict[str, object]:
        self.calls.append(payload)
        return {
            "quote_id": "quote_durable",
            "pickup_place_id": payload["pickup_place_id"],
            "destination_place_id": payload["destination_place_id"],
            "vehicle_type": payload["vehicle_type"],
            "fare_amount": 100_000,
            "currency": "VND",
            "distance_km": 10,
            "eta_minutes": 25,
            "expires_at": "2099-01-01T00:00:00+00:00",
            "estimated": True,
        }


class FakeBookingService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create_booking_from_quote(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(payload)
        return {
            "booking_id": "book_durable",
            "status": "SEARCHING_DRIVER",
            "quoted_fare_amount": 100_000,
            "currency": "VND",
            "eta_minutes": 25,
        }


class FakeCancellationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def cancel_booking_durable(
        self, booking_id: str, idempotency_key: str, user_id: str | None = None
    ) -> dict[str, object] | None:
        assert user_id is not None
        self.calls.append((booking_id, idempotency_key, user_id))
        return {
            "booking_id": booking_id,
            "status": "CANCELLED",
            "estimated_fare": 100_000,
            "currency": "VND",
            "eta_minutes": 25,
        }


def test_candidate_must_come_from_current_search_result() -> None:
    draft = BookingDraft()
    draft.set_candidates("pickup", "VinUni", [_place("place_1", "VinUni")])

    with pytest.raises(ValueError, match="PLACE_CANDIDATE_NOT_IN_CURRENT_SEARCH"):
        draft.select_place("pickup", "invented-place-id")


@pytest.mark.parametrize("correction", ["pickup", "destination", "vehicle"])
def test_every_booking_correction_invalidates_quote_confirmation_and_booking(
    correction: str,
) -> None:
    draft = _quoted_draft()
    draft.request_confirmation()
    draft.confirm()
    booking = BookingResult(
        booking_id="book_test",
        status="SEARCHING_DRIVER",
        estimated_fare=100_000,
        currency="VND",
        eta_minutes=25,
    )
    draft.set_booking(booking)

    if correction == "pickup":
        replacement = _place("place_pickup_new", "Cổng chính VinUni")
        draft.set_candidates("pickup", replacement.display_name, [replacement])
        draft.select_place("pickup", replacement.place_id)
    elif correction == "destination":
        replacement = _place("place_destination_new", "Bệnh viện Bạch Mai")
        draft.set_candidates("destination", replacement.display_name, [replacement])
        draft.select_place("destination", replacement.place_id)
    else:
        draft.set_vehicle_type("CAR_7")

    assert draft.quote is None
    assert draft.confirmation_status == "not_requested"
    assert draft.confirmation_fingerprint is None
    assert draft.booking is None


@pytest.mark.asyncio
async def test_booking_requires_explicit_confirmed_state() -> None:
    draft = _quoted_draft()
    draft.request_confirmation()

    with pytest.raises(ValueError, match="EXPLICIT_CONFIRMATION_REQUIRED"):
        await BookingToolsService(FakeBookingService()).create(
            user_id="user-1",
            app_session_id="session-1",
            draft=draft,
        )


@pytest.mark.asyncio
async def test_durable_booking_uses_stable_idempotency_key_for_same_session_and_quote() -> None:
    draft = _quoted_draft()
    draft.request_confirmation()
    draft.confirm()
    backend = FakeBookingService()
    service = BookingToolsService(backend)

    first = await service.create(user_id="user-1", app_session_id="session-1", draft=draft)
    second = await service.create(user_id="user-1", app_session_id="session-1", draft=draft)

    assert first == second
    assert first.booking_id == "book_durable"
    assert backend.calls[0]["idempotency_key"] == backend.calls[1]["idempotency_key"]
    assert backend.calls[0]["quote_id"] == "quote_test"


@pytest.mark.asyncio
async def test_durable_cancellation_uses_stable_booking_scoped_idempotency_key() -> None:
    backend = FakeCancellationService()
    service = BookingToolsService(backend)

    first = await service.cancel(booking_id="book_durable", user_id="user-1", app_session_id="session-1")
    second = await service.cancel(booking_id="book_durable", user_id="user-1", app_session_id="session-1")

    assert first == second
    assert first is not None and first.status == "CANCELLED"
    assert backend.calls == [
        ("book_durable", "session-1:cancel_booking:book_durable", "user-1"),
        ("book_durable", "session-1:cancel_booking:book_durable", "user-1"),
    ]


def test_cancelled_booking_is_reflected_in_compact_conversation_summary() -> None:
    draft = _quoted_draft()
    booking = BookingResult(
        booking_id="book_durable",
        status="SEARCHING_DRIVER",
        estimated_fare=100_000,
        currency="VND",
        eta_minutes=25,
    )
    draft.request_confirmation()
    draft.confirm()
    draft.set_booking(booking)
    draft.mark_booking_cancelled(booking.model_copy(update={"status": "CANCELLED"}))

    assert "chuyến mã book_durable đã hủy" in draft.conversation_summary()

@pytest.mark.asyncio
async def test_quote_tool_uses_existing_durable_quote_service() -> None:
    draft = _quoted_draft()
    draft.quote = None
    backend = FakeQuoteService()

    quote = await QuoteToolsService(backend).estimate(
        user_id="user-1",
        app_session_id="session-1",
        draft=draft,
    )

    assert quote.quote_id == "quote_durable"
    assert backend.calls == [
        {
            "user_id": "user-1",
            "session_id": "session-1",
            "pickup_place_id": "place_pickup",
            "destination_place_id": "place_destination",
            "vehicle_type": "CAR_4",
        }
    ]


def test_public_state_excludes_queries_and_candidate_lists() -> None:
    draft = _quoted_draft()

    public = draft.public_state()

    assert "pickup_query" not in public
    assert "destination_query" not in public
    assert "pickup_candidates" not in public
    assert public["pickup"]["display_name"] == "VinUni"  # type: ignore[index]


def test_public_state_exposes_only_safe_pending_clarification_fields() -> None:
    draft = BookingDraft()
    candidates = [_place("first", "Cổng chính VinUni"), _place("second", "Cổng phụ VinUni")]
    draft.set_candidates("pickup", "VinUni", candidates)

    public = draft.public_state()
    clarification = public["pending_place_clarification"]

    assert clarification["clarification_id"].startswith("pickup:")  # type: ignore[index]
    assert clarification["target"] == "pickup"  # type: ignore[index]
    assert clarification["query"] == "VinUni"  # type: ignore[index]
    assert clarification["selected_index"] is None  # type: ignore[index]
    assert clarification["options"] == [  # type: ignore[index]
        {"index": 1, "display_name": "Cổng chính VinUni", "subtitle": "Cổng chính VinUni"},
        {"index": 2, "display_name": "Cổng phụ VinUni", "subtitle": "Cổng phụ VinUni"},
    ]
    assert "place_id" not in str(clarification)

    draft.select_place("pickup", "second")
    assert draft.public_state()["pending_place_clarification"] is None


def test_pickup_destination_and_vehicle_lists_have_independent_state() -> None:
    draft = BookingDraft()
    pickup = [_place("pickup-main", "Cổng chính VinUni"), _place("pickup-side", "Cổng phụ VinUni")]
    destination = [_place("aeon", "AEON Mall Long Biên"), _place("bridge", "Cầu Long Biên")]
    draft.set_candidates("pickup", "VinUni", pickup)
    draft.select_place("pickup", "pickup-side")
    draft.set_candidates("destination", "Long Biên", destination)

    clarifications = draft.public_state()["clarifications"]

    assert clarifications["pickup"]["selected_index"] == 2  # type: ignore[index]
    assert [option["display_name"] for option in clarifications["pickup"]["options"]] == [  # type: ignore[index]
        "Cổng chính VinUni",
        "Cổng phụ VinUni",
    ]
    assert [option["display_name"] for option in clarifications["destination"]["options"]] == [  # type: ignore[index]
        "AEON Mall Long Biên",
        "Cầu Long Biên",
    ]
    assert [option["value"] for option in clarifications["vehicle_type"]["options"]] == [  # type: ignore[index]
        "MOTORBIKE",
        "CAR_4",
        "CAR_7",
        "LUXURY",
    ]

    draft.set_vehicle_type("CAR_4")
    assert draft.public_state()["clarifications"]["vehicle_type"] is None  # type: ignore[index]


def test_conversation_summary_is_compact_and_uses_spoken_vehicle_label() -> None:
    draft = _quoted_draft()

    summary = draft.conversation_summary()

    assert "điểm đón VinUni" in summary
    assert "điểm đến Hồ Gươm" in summary
    assert "xe ô tô bốn chỗ" in summary
    assert "CAR_4" not in summary
    assert vehicle_spoken_label("MOTORBIKE") == "xe máy"
