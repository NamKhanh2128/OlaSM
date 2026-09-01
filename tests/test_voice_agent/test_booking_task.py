import json
import unicodedata
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from livekit.agents import StopResponse, llm

from src.voice_agent.agent import AloSMAgent
from src.voice_agent.persistence import EphemeralVoiceStateStore
from src.voice_agent.session_data import AloSMSessionData, HandoffState, PlaceCandidate, QuoteSnapshot
from src.voice_agent.tasks import booking as booking_module
from src.voice_agent.tasks.booking import (
    BookingTask,
    can_auto_select_place,
    extract_complete_route,
    extract_explicit_booking_change,
    extract_vehicle_type,
    grounded_named_place_selection,
    grounded_ordinal_selection,
    grounded_vehicle_selection,
    is_explicit_confirmation,
    requires_location_clarification,
    seed_complete_booking_turn,
)
from src.voice_agent.tools import PlaceToolsService


class _CancellationService:
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


class _QuoteService:
    async def estimate(self, **_: object) -> QuoteSnapshot:
        return QuoteSnapshot(
            quote_id="quote-regression",
            pickup_place_id="pickup",
            destination_place_id="destination",
            vehicle_type="CAR_4",
            fare_amount=95_180,
            currency="VND",
            distance_km=20.0,
            eta_minutes=16,
            expires_at="2099-01-01T00:00:00+00:00",
            estimated=True,
        )


def test_agent_exposes_native_booking_entrypoint_and_authoritative_status_tool() -> None:
    assert {tool.id for tool in AloSMAgent().tools} == {
        "start_booking",
        "request_handoff",
        "cancel_booking",
        "get_booking_status",
        "search_knowledge",
        "get_vehicle_options",
    }


class _SpeechHandle:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def add_done_callback(self, callback: object) -> None:
        self._callbacks.append(callback)

    def finish(self) -> None:
        for callback in self._callbacks:
            callback(self)  # type: ignore[operator]


class _AudioControl:
    def __init__(self) -> None:
        self.enabled: list[bool] = []

    def set_audio_enabled(self, enabled: bool) -> None:
        self.enabled.append(enabled)


class _HandoffSession:
    def __init__(self, userdata: AloSMSessionData) -> None:
        self.userdata = userdata
        self.input = _AudioControl()
        self.output = _AudioControl()
        self.speech = _SpeechHandle()
        self.acknowledgements: list[tuple[str, bool]] = []

    def say(self, text: str, *, allow_interruptions: bool) -> _SpeechHandle:
        self.acknowledgements.append((text, allow_interruptions))
        return self.speech


def test_handoff_wait_mutes_ai_after_exactly_one_acknowledgement() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    session = _HandoffSession(userdata)
    agent = AloSMAgent(session_data=userdata)
    agent._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    agent._enter_handoff_wait()
    agent._enter_handoff_wait()

    assert session.input.enabled == [False]
    assert session.acknowledgements == [
        ("Tôi đã chuyển yêu cầu của bạn đến tổng đài viên. Vui lòng chờ trong giây lát.", False)
    ]
    assert session.output.enabled == []
    session.speech.finish()
    assert session.output.enabled == [False]


@pytest.mark.asyncio
async def test_handoff_wait_rejects_later_customer_turns_without_llm_reply() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
        handoff=HandoffState(handoff_id="handoff", status="pending", reason_code="USER_REQUEST"),
    )
    agent = AloSMAgent(session_data=userdata)

    with pytest.raises(StopResponse):
        await agent.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Tôi muốn nói thêm"]),
        )


@pytest.mark.asyncio
async def test_parent_agent_seeds_complete_first_booking_turn_before_task_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    session = _HandoffSession(userdata)
    published: list[dict[str, object]] = []

    async def capture_state(_: object) -> bool:
        published.append(userdata.booking_draft.public_state())
        return True

    monkeypatch.setattr("src.voice_agent.agent.publish_booking_state", capture_state)
    agent = AloSMAgent(session_data=userdata)
    agent._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Cho tôi xe 4 chỗ đi từ VinUni tới Hồ Gươm."]),
    )

    expected = {
        "pickup": "needs_clarification",
        "destination": "needs_clarification",
        "vehicle_type": "resolved",
    }
    assert userdata.booking_draft.slot_statuses() == expected
    assert published[-1]["slot_statuses"] == expected

class _RequoteService:
    async def estimate(self, *, draft: object, **_: object) -> QuoteSnapshot:
        assert getattr(draft, "pickup") is not None
        assert getattr(draft, "destination") is not None
        assert getattr(draft, "vehicle_type") is not None
        return QuoteSnapshot(
            quote_id="quote-refreshed",
            pickup_place_id=draft.pickup.place_id,
            destination_place_id=draft.destination.place_id,
            vehicle_type=draft.vehicle_type,
            fare_amount=120_000,
            currency="VND",
            distance_km=24.0,
            eta_minutes=22,
            expires_at="2099-01-01T00:00:00+00:00",
            estimated=True,
        )


@pytest.mark.asyncio
async def test_agent_rag_tool_returns_versioned_policy_citation() -> None:
    result = await AloSMAgent().search_knowledge("Tôi muốn yêu cầu hoàn tiền")

    assert '"found": true' in result
    assert '"catalog_version": "2026-08-16"' in result
    assert '"citation_id": "policy-refund"' in result


@pytest.mark.asyncio
async def test_agent_rag_tool_explains_when_policy_is_not_verified() -> None:
    result = await AloSMAgent().search_knowledge("Chính sách hoàn tiền 100% khi trời mưa")

    assert '"found": false' in result
    assert "chưa tìm thấy thông tin chính sách đã được xác minh" in result
    assert "tổng đài viên" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "citation"),
    [
        ("Sau khi xác nhận giá, giá có được tự ý thay đổi không?", "policy-price-change"),
        ("Chính sách hủy chuyến và phí hủy là gì?", "policy-cancellation"),
    ],
)
async def test_livekit_faq_tool_keeps_natural_policy_questions_grounded(
    question: str,
    citation: str,
) -> None:
    result = await AloSMAgent().search_knowledge(question)

    assert f'"citation_id": "{citation}"' in result


@pytest.mark.asyncio
async def test_agent_vehicle_options_tool_reads_pricing_catalog_without_quote() -> None:
    result = await AloSMAgent().get_vehicle_options()

    assert '"pricing_status": "DEMO"' in result
    assert '"display_name": "AloSM Car 4 chỗ"' in result
    assert '"luggage_capacity":' in result
    assert '"fare_amount"' not in result


@pytest.mark.asyncio
async def test_parent_booking_status_never_invents_a_booking_id() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )

    status = await AloSMAgent(session_data=userdata).get_booking_status()

    assert '"created": false' in status
    assert '"booking_id": null' in status
    assert "Chuyến chưa được tạo" in status


@pytest.mark.asyncio
async def test_repeated_booking_request_does_not_reenter_completed_booking() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    userdata.booking_draft.booking = booking_module.BookingResult(
        booking_id="book-existing",
        status="SEARCHING_DRIVER",
        estimated_fare=100_000,
        currency="VND",
        eta_minutes=15,
    )
    agent = AloSMAgent(session_data=userdata)

    result = await AloSMAgent.start_booking._func(agent)

    assert "book-existing" in result
    assert "đã được đặt thành công" in result


@pytest.mark.asyncio
async def test_cancel_booking_uses_llm_decision_before_backend_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    userdata.booking_draft.booking = booking_module.BookingResult(
        booking_id="book-1",
        status="SEARCHING_DRIVER",
        estimated_fare=100_000,
        currency="VND",
        eta_minutes=25,
    )
    backend = _CancellationService()
    agent = AloSMAgent(session_data=userdata, bookings=booking_module.BookingToolsService(backend))
    agent._activity = SimpleNamespace(session=SimpleNamespace(userdata=userdata))  # type: ignore[assignment]
    monkeypatch.setattr("src.voice_agent.agent.publish_booking_state", _noop_publish)

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Tôi muốn hủy chuyến"]),
    )
    first = await agent.cancel_booking("Khách yêu cầu hủy chuyến", confirmation_decision="request")

    assert backend.calls == []
    assert "xác nhận" in first.lower()
    assert userdata.booking_draft.cancellation_confirmation_booking_id == "book-1"

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Ừ"]),
    )
    ambiguous = await agent.cancel_booking("Khách trả lời không rõ", confirmation_decision="request")
    assert backend.calls == []
    assert '"confirmation_required": true' in ambiguous

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Không hủy"]),
    )
    declined = await agent.cancel_booking("Khách từ chối", confirmation_decision="decline")
    assert '"cancelled": false' in declined
    assert userdata.booking_draft.cancellation_confirmation_booking_id is None
    assert backend.calls == []

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Tôi vẫn muốn hủy"]),
    )
    await agent.cancel_booking("Khách yêu cầu lại", confirmation_decision="request")

    await agent.on_user_turn_completed(
        llm.ChatContext.empty(),
        llm.ChatMessage(role="user", content=["Có, hủy chuyến này"]),
    )
    second = await agent.cancel_booking("Khách xác nhận hủy chuyến", confirmation_decision="confirm")

    assert backend.calls == [("book-1", "session:cancel_booking:book-1", "user")]
    assert '"cancelled": true' in second


async def _noop_publish(*_: object) -> None:
    return None


def test_recovered_booking_is_available_to_the_parent_agent_without_full_history() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
        recovered=True,
    )
    pickup = PlaceCandidate(
        place_id="my-dinh",
        display_name="Bến xe Mỹ Đình",
        address="Bến xe Mỹ Đình",
        provider="test",
    )
    userdata.booking_draft.set_candidates("pickup", "Mỹ Đình", [pickup])
    userdata.booking_draft.select_place("pickup", pickup.place_id)

    instructions = AloSMAgent(session_data=userdata).instructions

    assert "điểm đón Bến xe Mỹ Đình" in instructions
    assert "không có lịch sử" in instructions
    assert "pickup_candidates" not in instructions


@pytest.mark.asyncio
async def test_booking_task_uses_native_function_tools() -> None:
    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="Đặt xe từ VinUni đến Hồ Gươm")
    task = BookingTask(chat_ctx=chat_ctx)
    tool_names = {tool.id for tool in task.tools}

    assert tool_names == {
        "confirm_booking",
        "create_booking",
        "estimate_fare",
        "request_handoff",
        "mark_vehicle_needs_clarification",
        "search_place",
        "select_place",
        "set_vehicle_type",
    }
    assert task.chat_ctx.messages()[-1].text_content == "Đặt xe từ VinUni đến Hồ Gươm"


@pytest.mark.asyncio
async def test_estimate_fare_atomically_starts_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    pickup = PlaceCandidate(
        place_id="pickup",
        display_name="Cổng chính VinUni",
        address="Đường San Hô, Gia Lâm, Hà Nội",
        provider="test",
    )
    destination = PlaceCandidate(
        place_id="destination",
        display_name="Bưu điện Hà Nội",
        address="Đinh Tiên Hoàng, Hoàn Kiếm, Hà Nội",
        provider="test",
    )
    draft = userdata.booking_draft
    draft.set_candidates("pickup", "VinUni", [pickup])
    draft.select_place("pickup", pickup.place_id)
    draft.set_candidates("destination", "Bưu điện Hà Nội", [destination])
    draft.select_place("destination", destination.place_id)
    draft.set_vehicle_type("CAR_4")
    task = BookingTask(quotes=_QuoteService(), state_store=EphemeralVoiceStateStore())

    async def _publish(_: object) -> None:
        return None

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)
    context = SimpleNamespace(userdata=userdata, session=object(), disallow_interruptions=lambda: None)

    result = await BookingTask.estimate_fare._func(task, context)

    assert draft.confirmation_status == "awaiting"
    assert draft.confirmation_fingerprint == draft.quote.fingerprint
    assert "Hãy hỏi xác nhận rõ ràng" in result


@pytest.mark.asyncio
async def test_duplicate_confirmation_is_idempotent_before_booking_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    pickup = PlaceCandidate(
        place_id="pickup",
        display_name="Cổng chính VinUni",
        address="Đường San Hô, Gia Lâm, Hà Nội",
        provider="test",
    )
    destination = PlaceCandidate(
        place_id="destination",
        display_name="Bưu điện Hà Nội",
        address="Đinh Tiên Hoàng, Hoàn Kiếm, Hà Nội",
        provider="test",
    )
    draft = userdata.booking_draft
    draft.set_candidates("pickup", "VinUni", [pickup])
    draft.select_place("pickup", pickup.place_id)
    draft.set_candidates("destination", "Bưu điện Hà Nội", [destination])
    draft.select_place("destination", destination.place_id)
    draft.set_vehicle_type("CAR_4")
    draft.set_quote(
        QuoteSnapshot(
            quote_id="quote-regression",
            pickup_place_id=pickup.place_id,
            destination_place_id=destination.place_id,
            vehicle_type="CAR_4",
            fare_amount=95_180,
            currency="VND",
            distance_km=20.0,
            eta_minutes=16,
            expires_at="2099-01-01T00:00:00+00:00",
            estimated=True,
        )
    )
    draft.request_confirmation()

    async def _publish(_: object) -> None:
        return None

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)
    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="Tôi xác nhận đặt chuyến này.")
    task = BookingTask(
        chat_ctx=chat_ctx,
        state_store=EphemeralVoiceStateStore(),
    )
    context = SimpleNamespace(
        userdata=userdata,
        session=object(),
        disallow_interruptions=lambda: None,
    )

    first = await BookingTask.confirm_booking._func(task, context)

    second_chat_ctx = llm.ChatContext.empty()
    second_chat_ctx.add_message(role="user", content="Tôi xác nhận lại, cứ đặt chuyến này nhé.")
    second_task = BookingTask(
        chat_ctx=second_chat_ctx,
        state_store=EphemeralVoiceStateStore(),
    )
    second = await BookingTask.confirm_booking._func(second_task, context)

    assert first == "Khách đã xác nhận rõ ràng; có thể gọi create_booking."
    assert second == first
    assert draft.confirmation_status == "confirmed"
    assert draft.quote is not None
    assert draft.quote.quote_id == "quote-regression"
    assert draft.booking is None


@pytest.mark.asyncio
async def test_location_change_refreshes_existing_quote_and_interrupts_stale_preamble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    draft = userdata.booking_draft
    pickup = PlaceCandidate(
        place_id="pickup",
        display_name="Cổng chính VinUni",
        address="VinUni",
        provider="test",
    )
    old_destination = PlaceCandidate(
        place_id="old-destination",
        display_name="Hồ Gươm",
        address="Hồ Gươm",
        provider="test",
    )
    draft.set_candidates("pickup", "VinUni", [pickup])
    draft.select_place("pickup", pickup.place_id)
    draft.set_candidates("destination", "Hồ Gươm", [old_destination])
    draft.select_place("destination", old_destination.place_id)
    draft.set_vehicle_type("MOTORBIKE")
    draft.set_quote(
        QuoteSnapshot(
            quote_id="quote-old",
            pickup_place_id=pickup.place_id,
            destination_place_id=old_destination.place_id,
            vehicle_type="MOTORBIKE",
            fare_amount=80_000,
            currency="VND",
            distance_km=10.0,
            eta_minutes=12,
            expires_at="2099-01-01T00:00:00+00:00",
            estimated=True,
        )
    )
    draft.request_confirmation()

    interrupted: list[bool] = []

    class _Session:
        async def interrupt(self) -> None:
            interrupted.append(True)

    async def _publish(_: object) -> None:
        return None

    @asynccontextmanager
    async def _filler(*_: object, **__: object):
        yield

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)
    task = BookingTask(quotes=_RequoteService(), state_store=EphemeralVoiceStateStore())
    context = SimpleNamespace(
        userdata=userdata,
        session=_Session(),
        disallow_interruptions=lambda: None,
        with_filler=_filler,
    )

    await BookingTask.search_place._func(
        task,
        context,
        target="destination",
        query="Đại học Bách khoa Hà Nội",
    )

    assert interrupted == [True]
    assert draft.quote is not None
    assert draft.quote.quote_id == "quote-refreshed"
    assert draft.confirmation_status == "awaiting"


def test_terminal_task_tools_follow_livekit_complete_without_narrating_inside_task() -> None:
    for tool in (BookingTask.create_booking,):
        assert tool.__annotations__["return"] in {None, type(None), "None"}


def test_explicit_confirmation_rejects_negative_or_ambiguous_text() -> None:
    assert is_explicit_confirmation("Tôi xác nhận đặt chuyến này") is True
    assert is_explicit_confirmation("Đúng rồi, đặt xe đi") is True
    assert is_explicit_confirmation("Không đúng, sửa điểm đến") is False
    assert is_explicit_confirmation("Ừ") is False


def test_booking_abandonment_requires_an_explicit_request() -> None:
    assert booking_module.is_booking_abandonment_request("Thôi không đặt nữa") is True
    assert booking_module.is_booking_abandonment_request("Đổi xe đi") is False
    assert booking_module.is_booking_abandonment_request("Ừ") is False


def test_complete_turn_seeds_both_ambiguous_places_and_resolved_vehicle() -> None:
    draft = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    ).booking_draft
    message = "Cho tôi một xe bốn chỗ đi từ VinUni tới Hồ Gươm."

    assert extract_complete_route(message) == ("VinUni", "Hồ Gươm")
    assert extract_vehicle_type(message) == "CAR_4"
    assert seed_complete_booking_turn(draft, PlaceToolsService(), message) is True
    assert draft.slot_statuses() == {
        "pickup": "needs_clarification",
        "destination": "needs_clarification",
        "vehicle_type": "resolved",
    }
    assert draft.slot_labels() == {
        "pickup": "VinUni",
        "destination": "Hồ Gươm",
        "vehicle_type": "xe ô tô bốn chỗ",
    }
    assert draft.pending_candidate_target == "pickup"


def test_complete_route_parser_ignores_short_spoken_fillers() -> None:
    message = "Cho tôi xe bốn chỗ, ờ, đi từ, ừm, VinUni tới Hồ Gươm."

    assert extract_complete_route(message) == ("VinUni", "Hồ Gươm")
    assert extract_vehicle_type(message) == "CAR_4"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("À, đổi điểm đến là Hồ Tây", ("destination", "Hồ Tây")),
        ("Sửa giúp tôi điểm đón thành Times City", ("pickup", "Times City")),
        ("Điểm đến chuyển sang Long Biên", ("destination", "Long Biên")),
        ("Đổi loại xe sang xe bảy chỗ", ("vehicle_type", "xe bảy chỗ")),
        (
            "Tôi chọn số 2 nhưng đổi điểm đến thành Hồ Gươm",
            ("destination", "Hồ Gươm"),
        ),
    ],
)
def test_explicit_booking_change_parser_prioritizes_replacement_intent(
    message: str,
    expected: tuple[str, str],
) -> None:
    assert extract_explicit_booking_change(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("ĐỔI ĐIỂM ĐÓN SANG TIMES CITY", ("pickup", "TIMES CITY")),
        ("Đổi\tđiểm\u00a0đến   thành Hồ Tây", ("destination", "Hồ Tây")),
        (
            unicodedata.normalize("NFD", "Đổi nơi đón sang VinUni"),
            ("pickup", "VinUni"),
        ),
    ],
)
def test_explicit_booking_change_normalizes_unicode_case_and_whitespace(
    message: str,
    expected: tuple[str, str],
) -> None:
    assert extract_explicit_booking_change(message) == expected


def test_explicit_booking_change_unknown_field_mapping_fails_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(booking_module, "_CHANGE_FIELD_TARGETS", {})

    assert extract_explicit_booking_change("Đổi điểm đón sang Times City") is None


@pytest.mark.asyncio
async def test_destination_barge_in_interrupts_pickup_prompt_and_focuses_new_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    draft = userdata.booking_draft
    seed_complete_booking_turn(
        draft,
        PlaceToolsService(),
        "Cho tôi xe 4 chỗ đi từ VinUni tới Hồ Gươm.",
    )
    original_pickup_candidates = list(draft.pickup_candidates)

    class _BargeInSession:
        def __init__(self) -> None:
            self.userdata = userdata
            self.events: list[tuple[str, object]] = []

        async def interrupt(self, *, force: bool = False) -> None:
            self.events.append(("interrupt", force))

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            self.events.append(("say", (text, allow_interruptions)))

    session = _BargeInSession()
    task = BookingTask(session_data=userdata, state_store=EphemeralVoiceStateStore())
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    async def capture_publish(_: object) -> bool:
        session.events.append(("publish", draft.public_state()))
        return True

    monkeypatch.setattr(booking_module, "publish_booking_state", capture_publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(
                role="user",
                content=["Tôi chọn số 2 nhưng đổi điểm đến thành Long Biên"],
            ),
        )

    assert session.events[0] == ("interrupt", True)
    assert draft.pickup is None
    assert draft.pickup_query == "VinUni"
    assert draft.pickup_candidates == original_pickup_candidates
    assert draft.destination is None
    assert draft.destination_query == "Long Biên"
    assert draft.destination_candidates
    assert draft.pending_candidate_target == "destination"
    response, allow_interruptions = session.events[-1][1]  # type: ignore[misc]
    assert allow_interruptions is True
    assert response.startswith("Đã cập nhật điểm đến thành Long Biên.")
    assert "cho điểm đến" in response
    assert "số thứ tự" in response
    assert "liên quan đến VinUni cho điểm đón" not in response


@pytest.mark.asyncio
async def test_unknown_destination_barge_in_does_not_resume_old_pickup_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    draft = userdata.booking_draft
    seed_complete_booking_turn(
        draft,
        PlaceToolsService(),
        "Cho tôi xe 4 chỗ đi từ VinUni tới Hồ Gươm.",
    )

    class _BargeInSession:
        def __init__(self) -> None:
            self.userdata = userdata
            self.replies: list[str] = []

        async def interrupt(self, *, force: bool = False) -> None:
            assert force is True

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            assert allow_interruptions is True
            self.replies.append(text)

    session = _BargeInSession()
    task = BookingTask(session_data=userdata, state_store=EphemeralVoiceStateStore())
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    async def ignore_publish(_: object) -> bool:
        return True

    monkeypatch.setattr(booking_module, "publish_booking_state", ignore_publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["À, đổi điểm đến là Hồ Khương"]),
        )

    assert draft.slot_status("destination") == "needs_clarification"
    assert draft.slot_labels()["destination"] == "Hồ Khương"
    assert draft.destination_candidates == []
    assert draft.pending_candidate_target == "destination"
    assert userdata.last_failure is not None
    assert userdata.last_failure.code == "PLACE_NOT_FOUND"
    assert session.replies == [
        "Đã cập nhật điểm đến thành Hồ Khương. Chưa tìm thấy địa điểm phù hợp. "
        "Bạn vui lòng nói lại điểm đến hoặc nhập tên khác."
    ]
    assert "VinUni" not in session.replies[0]


@pytest.mark.asyncio
async def test_vehicle_barge_in_changes_vehicle_then_returns_to_pending_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    draft = userdata.booking_draft
    seed_complete_booking_turn(
        draft,
        PlaceToolsService(),
        "Cho tôi xe 4 chỗ đi từ VinUni tới Hồ Gươm.",
    )

    class _BargeInSession:
        def __init__(self) -> None:
            self.userdata = userdata
            self.interrupted = False
            self.replies: list[str] = []

        async def interrupt(self, *, force: bool = False) -> None:
            self.interrupted = force

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            assert allow_interruptions is True
            self.replies.append(text)

    session = _BargeInSession()
    task = BookingTask(session_data=userdata, state_store=EphemeralVoiceStateStore())
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    async def ignore_publish(_: object) -> bool:
        return True

    monkeypatch.setattr(booking_module, "publish_booking_state", ignore_publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Đổi loại xe sang xe bảy chỗ"]),
        )

    assert session.interrupted is True
    assert draft.vehicle_type == "CAR_7"
    assert draft.pending_candidate_target == "pickup"
    assert session.replies[0].startswith("Đã đổi loại xe thành xe ô tô bảy chỗ.")
    assert "liên quan đến VinUni cho điểm đón" in session.replies[0]


def test_native_transcript_confidence_only_blocks_low_confidence_audio() -> None:
    audio = llm.ChatMessage(
        role="user",
        content=["VinUni"],
        transcript_confidence=0.4,
    )
    text = llm.ChatMessage(role="user", content=["VinUni"])

    assert requires_location_clarification(audio, 0.65) is True
    assert requires_location_clarification(text, 0.65) is False
    assert requires_location_clarification(audio, 0.65, PlaceToolsService().search("Đại học Ếch Khoa Hà Nội")) is True


@pytest.mark.asyncio
async def test_known_place_candidates_bypass_low_confidence_transcript_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="Tôi muốn đặt xe từ VinUni")
    chat_ctx.items[-1].transcript_confidence = 0.4
    task = BookingTask(chat_ctx=chat_ctx, state_store=EphemeralVoiceStateStore())

    async def _publish(_: object) -> None:
        return None

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)
    context = SimpleNamespace(userdata=userdata, session=object(), disallow_interruptions=lambda: None)

    result = await BookingTask.search_place._func(task, context, target="pickup", query="VinUni")
    payload = json.loads(result)

    assert "ASR_LOW_CONFIDENCE" not in result
    assert "Cổng chính VinUni" in result
    assert userdata.booking_draft.pickup is None
    assert len(userdata.booking_draft.pickup_candidates) == 3
    assert payload["spoken_prompt"] == (
        "Đã tìm thấy 3 địa điểm liên quan đến VinUni cho điểm đón trong dữ liệu. "
        "Vui lòng chọn theo số thứ tự được liệt kê bên dưới."
    )
    assert "không đọc tên hay địa chỉ" in payload["instruction"]


@pytest.mark.asyncio
async def test_exact_place_tool_requires_acknowledgement_before_next_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    task = BookingTask(state_store=EphemeralVoiceStateStore())

    async def _publish(_: object) -> None:
        return None

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)
    context = SimpleNamespace(userdata=userdata, session=object(), disallow_interruptions=lambda: None)

    result = await BookingTask.search_place._func(
        task,
        context,
        target="pickup",
        query="Cổng phụ VinUni",
    )
    payload = json.loads(result)

    assert payload["auto_selected"] is True
    assert payload["spoken_prompt"].startswith("Đã chọn điểm đón là Cổng phụ VinUni.")
    assert "Vui lòng cho biết điểm đến" in payload["spoken_prompt"]
    assert "Đọc nguyên văn spoken_prompt" in payload["instruction"]


@pytest.mark.asyncio
async def test_task_entry_uses_seeded_query_label_instead_of_unclear_placeholder() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    seed_complete_booking_turn(
        userdata.booking_draft,
        PlaceToolsService(),
        "Cho tôi xe 4 chỗ đi từ VinUni tới Long Biên.",
    )
    session = _HandoffSession(userdata)
    task = BookingTask(session_data=userdata)
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    await task.on_enter()

    assert session.acknowledgements == [
        (
            "Đã tìm thấy 3 địa điểm liên quan đến VinUni cho điểm đón trong dữ liệu. "
            "Vui lòng chọn theo số thứ tự được liệt kê bên dưới.",
            True,
        )
    ]
    assert "chưa rõ" not in session.acknowledgements[0][0]


@pytest.mark.asyncio
async def test_pickup_ordinal_moves_directly_to_saved_destination_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    draft = userdata.booking_draft
    seed_complete_booking_turn(
        draft,
        PlaceToolsService(),
        "Cho tôi xe 4 chỗ đi từ VinUni tới Hồ Gươm.",
    )
    session = _HandoffSession(userdata)
    task = BookingTask(session_data=userdata, state_store=EphemeralVoiceStateStore())
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    async def ignore_publish(_: object) -> bool:
        return True

    monkeypatch.setattr(booking_module, "publish_booking_state", ignore_publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Tôi chọn số hai"]),
        )

    assert draft.pickup is not None
    assert draft.pickup.display_name == "Cổng phụ VinUni"
    assert draft.destination is None
    assert draft.destination_query == "Hồ Gươm"
    assert draft.destination_candidates
    assert draft.pending_candidate_target == "destination"
    assert session.acknowledgements == [
        (
            "Đã chọn điểm đón là Cổng phụ VinUni. "
            f"Đã tìm thấy {len(draft.destination_candidates)} địa điểm liên quan đến Hồ Gươm "
            "cho điểm đến trong dữ liệu. Vui lòng chọn theo số thứ tự được liệt kê bên dưới.",
            True,
        )
    ]


def test_short_ordinal_selects_from_active_candidate_list() -> None:
    draft = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    ).booking_draft
    candidates = PlaceToolsService().search("VinUni")
    draft.set_candidates("pickup", "VinUni", candidates)

    grounded = grounded_ordinal_selection(draft, "Tôi chọn số 2")

    assert grounded == ("pickup", candidates[1])
    assert grounded_ordinal_selection(draft, "Tôi chọn số 2 nhưng đổi điểm đến") is None


def test_named_correction_selects_new_candidate_and_respects_negation() -> None:
    draft = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    ).booking_draft
    candidates = PlaceToolsService().search("VinUni")
    draft.set_candidates("pickup", "VinUni", candidates)
    draft.select_place("pickup", candidates[0].place_id)

    grounded = grounded_named_place_selection(
        draft,
        "Cổng phụ chứ không phải cổng chính",
    )

    assert grounded == ("pickup", candidates[1])


def test_vehicle_selection_supports_catalog_number_and_explicit_change() -> None:
    draft = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    ).booking_draft

    assert grounded_vehicle_selection(draft, "Tôi chọn số 2") == "CAR_4"
    draft.set_vehicle_type("CAR_4")
    assert grounded_vehicle_selection(draft, "Đổi sang xe bảy chỗ") == "CAR_7"


@pytest.mark.asyncio
async def test_short_ordinal_updates_slot_once_and_moves_to_next_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    candidates = PlaceToolsService().search("VinUni")
    userdata.booking_draft.set_candidates("pickup", "VinUni", candidates)

    class _Session:
        def __init__(self) -> None:
            self.userdata = userdata
            self.replies: list[str] = []

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            assert allow_interruptions is True
            self.replies.append(text)

    session = _Session()
    task = BookingTask(
        state_store=EphemeralVoiceStateStore(),
        session_data=userdata,
    )
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]
    published: list[str | None] = []

    async def _publish(current_session: object) -> None:
        published.append(current_session.userdata.booking_draft.pickup.display_name)

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Tôi chọn số 2"]),
        )

    assert userdata.booking_draft.pickup == candidates[1]
    assert userdata.booking_draft.pending_candidate_target is None
    assert published == [candidates[1].display_name]
    assert session.replies == [
        f"Đã chọn điểm đón là {candidates[1].display_name}. "
        "Vui lòng cho biết điểm đến. Nếu muốn đổi, bạn có thể nói lại."
    ]


@pytest.mark.asyncio
async def test_named_location_correction_acknowledges_change_before_next_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    candidates = PlaceToolsService().search("VinUni")
    userdata.booking_draft.set_candidates("pickup", "VinUni", candidates)
    userdata.booking_draft.select_place("pickup", candidates[0].place_id)

    class _Session:
        def __init__(self) -> None:
            self.userdata = userdata
            self.replies: list[str] = []

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            assert allow_interruptions is True
            self.replies.append(text)

    session = _Session()
    task = BookingTask(state_store=EphemeralVoiceStateStore(), session_data=userdata)
    task._activity = SimpleNamespace(session=session)  # type: ignore[assignment]

    async def _publish(_: object) -> None:
        return None

    monkeypatch.setattr(booking_module, "publish_booking_state", _publish)

    with pytest.raises(StopResponse):
        await task.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Cổng phụ chứ không phải cổng chính"]),
        )

    assert userdata.booking_draft.pickup == candidates[1]
    assert session.replies == [
        "Đã chọn điểm đón là Cổng phụ VinUni. "
        "Vui lòng cho biết điểm đến. Nếu muốn đổi, bạn có thể nói lại."
    ]


def test_place_tool_reuses_hanoi_gazetteer_without_echo_fallback() -> None:
    service = PlaceToolsService()

    assert service.search("VinUni")
    assert service.search("Trường Đại học Bách Khoa Hà Nội")[0].display_name == "Đại học Bách khoa Hà Nội"
    assert service.search("Đại học Ếch Khoa Hà Nội")[0].display_name == "Đại học Bách khoa Hà Nội"
    assert service.search("phố Hồ Hà Nội") == []
    assert service.search("một địa điểm hoàn toàn không tồn tại") == []


def test_only_unique_exact_or_alias_place_can_skip_clarification() -> None:
    service = PlaceToolsService()

    assert can_auto_select_place(service.search("Đại học Bách khoa Hà Nội")) is True
    assert can_auto_select_place(service.search("Cổng chính VinUni")) is True
    assert can_auto_select_place(service.search("Bưu điện Hà Nội")) is True
    assert can_auto_select_place(service.search("Đại học Ếch Khoa Hà Nội")) is False
    assert can_auto_select_place(service.search("VinUni")) is False
    assert can_auto_select_place(service.search("Hồ Gươm")) is False


@pytest.mark.asyncio
async def test_booking_task_handoff_tool_delegates_llm_reason_to_call_level_handler() -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    reasons: list[str] = []

    async def _handle_handoff(reason: str) -> str:
        reasons.append(reason)
        return '{"status":"pending","handoff_id":"handoff-test"}'

    task = BookingTask(handoff_handler=_handle_handoff)
    context = SimpleNamespace(
        userdata=userdata,
        session=object(),
        disallow_interruptions=lambda: None,
    )

    with pytest.raises(StopResponse):
        await BookingTask.request_handoff._func(task, context, "Kết nối tôi với người hỗ trợ về chuyến này")

    assert reasons == ["Kết nối tôi với người hỗ trợ về chuyến này"]
