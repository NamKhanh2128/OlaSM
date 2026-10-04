import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from livekit.agents import llm

import src.voice_agent.transcript_rewrite as rewrite_module
from src.voice_agent.session_data import OlaSMSessionData
from src.voice_agent.transcript_rewrite import (
    OpenAITranscriptRewriter,
    RewriteOutput,
    TranscriptRewriteResult,
    _numeric_semantics_preserved,
    is_short_ordinal_selection,
    rewrite_livekit_user_turn,
)


def _userdata() -> OlaSMSessionData:
    return OlaSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )


class _Rewriter:
    timeout_seconds = 2.0
    context_window_turns = 3

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def rewrite(
        self,
        text: str,
        *,
        session_context: dict[str, Any],
        session_id: str,
        turn_id: str | None = None,
    ) -> TranscriptRewriteResult:
        self.calls.append(
            {
                "text": text,
                "context": session_context,
                "session_id": session_id,
                "turn_id": turn_id,
            }
        )
        return TranscriptRewriteResult(
            raw_text=text,
            normalized_text="Đổi điểm đón sang Hồ Gươm",
            applied=True,
            reason="applied",
            inferred_intent="CHANGE_PICKUP",
            confidence=0.99,
        )


class _HangingRewriter:
    timeout_seconds = 20.0
    context_window_turns = 3

    async def rewrite(self, *_: object, **__: object) -> TranscriptRewriteResult:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


class _BlockingRewriter(_Rewriter):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def rewrite(
        self,
        text: str,
        *,
        session_context: dict[str, Any],
        session_id: str,
        turn_id: str | None = None,
    ) -> TranscriptRewriteResult:
        self.calls.append(
            {
                "text": text,
                "context": session_context,
                "session_id": session_id,
                "turn_id": turn_id,
            }
        )
        self.started.set()
        await self.release.wait()
        return TranscriptRewriteResult(
            raw_text=text,
            normalized_text="Đổi điểm đón sang Hồ Gươm",
            applied=True,
            reason="applied",
            inferred_intent="CHANGE_PICKUP",
            confidence=0.99,
        )


class _ParsedResponseClient:
    def __init__(self, normalized_text: str) -> None:
        self.normalized_text = normalized_text
        self.responses = self

    async def parse(self, **_: object) -> object:
        return SimpleNamespace(
            output_parsed=RewriteOutput(
                inferred_intent="BOOK_RIDE",
                normalized_text=self.normalized_text,
                meaning_preserved=True,
                confidence=0.99,
            )
        )


def _openai_rewriter(normalized_text: str) -> OpenAITranscriptRewriter:
    return OpenAITranscriptRewriter(
        api_key="test-key",
        model="gpt-5-mini",
        base_url=None,
        timeout_seconds=2.0,
        reasoning_effort="low",
        minimum_confidence=0.85,
        context_window_turns=3,
        client=_ParsedResponseClient(normalized_text),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("text", ["2", "số 2", "tôi chọn số 2", "chọn thứ hai", "số bốn, số bốn"])
def test_short_ordinal_selection_is_deterministic(text: str) -> None:
    assert is_short_ordinal_selection(text) is True


@pytest.mark.parametrize(
    "text",
    ["tôi chọn số 2 nhưng đổi điểm đón", "đổi điểm đón", "điểm đến là số 2 đường Trần Phú"],
)
def test_long_or_change_response_is_not_bypassed(text: str) -> None:
    assert is_short_ordinal_selection(text) is False


@pytest.mark.asyncio
async def test_short_ordinal_skips_provider_but_change_uses_three_context_pairs() -> None:
    userdata = _userdata()
    rewriter = _Rewriter()
    short = llm.ChatMessage(role="user", content=["Tôi chọn số 2"])

    short_result = await rewrite_livekit_user_turn(
        rewriter=rewriter,
        userdata=userdata,
        turn_ctx=llm.ChatContext.empty(),
        new_message=short,
    )

    assert short_result is not None and short_result.reason == "short_ordinal"
    assert rewriter.calls == []

    context = llm.ChatContext.empty()
    for assistant, user in (
        ("Cặp cũ", "Nội dung cũ"),
        ("Bạn muốn đi đâu?", "VinUni"),
        ("Bạn chọn điểm nào?", "Số một"),
        ("Bạn muốn đổi gì?", "Điểm đón"),
    ):
        context.add_message(role="assistant", content=assistant)
        context.add_message(role="user", content=user)
    context.add_message(role="assistant", content="Bạn muốn đổi điểm đón thành đâu?")
    current = llm.ChatMessage(
        role="user",
        content=["Đổi điểm đón sang Hồ Gương"],
        transcript_confidence=0.37,
    )

    result = await rewrite_livekit_user_turn(
        rewriter=rewriter,
        userdata=userdata,
        turn_ctx=context,
        new_message=current,
    )

    assert result is not None and result.inferred_intent == "CHANGE_PICKUP"
    assert current.text_content == "Đổi điểm đón sang Hồ Gươm"
    assert rewriter.calls[0]["context"]["recent_dialogue_pairs"] == [
        {"assistant": "Bạn chọn điểm nào?", "user": "Số một"},
        {"assistant": "Bạn muốn đổi gì?", "user": "Điểm đón"},
        {"assistant": "Bạn muốn đổi điểm đón thành đâu?", "user": "Đổi điểm đón sang Hồ Gương"},
    ]
    assert rewriter.calls[0]["context"]["asr_confidence"] == 0.37


@pytest.mark.parametrize("raw", ["Nam", "Nam Phúc", "Năm Phúc", "số Nam"])
@pytest.mark.asyncio
async def test_tracking_minutes_context_recovers_five_before_short_ordinal_bypass(raw: str) -> None:
    context = llm.ChatContext.empty()
    context.add_message(role="assistant", content="Bạn muốn theo dõi chuyến xe sau bao nhiêu phút?")
    message = llm.ChatMessage(role="user", content=[raw])

    result = await rewrite_livekit_user_turn(
        rewriter=None,
        userdata=_userdata(),
        turn_ctx=context,
        new_message=message,
    )

    assert result is not None
    assert result.reason == "contextual_tracking_interval"
    assert result.inferred_intent == "TRACK_BOOKING"
    assert message.text_content == "5 phút"


@pytest.mark.asyncio
async def test_tracking_homophone_is_not_changed_outside_tracking_minutes_context() -> None:
    context = llm.ChatContext.empty()
    context.add_message(role="assistant", content="Bạn muốn gửi yêu cầu gì cho tài xế?")
    message = llm.ChatMessage(role="user", content=["Nam Phúc"])

    result = await rewrite_livekit_user_turn(
        rewriter=None,
        userdata=_userdata(),
        turn_ctx=context,
        new_message=message,
    )

    assert result is not None
    assert result.reason == "disabled_or_unconfigured"
    assert message.text_content == "Nam Phúc"


@pytest.mark.parametrize("normalized", ["1C muốn đặt xe", "1515 muốn đặt xe"])
@pytest.mark.asyncio
async def test_rewrite_rejects_numeric_tokens_not_present_in_raw_transcript(
    normalized: str,
) -> None:
    raw = "Cho tôi muốn đặt xe"

    result = await _openai_rewriter(normalized).rewrite(
        raw,
        session_context={"asr_confidence": 0.0},
        session_id="session",
    )

    assert result.applied is False
    assert result.normalized_text == raw
    assert result.reason == "numeric_semantics_rejected"


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("1C muốn đặt xe", "Cho tôi muốn đặt xe"),
        ("1515 muốn đặt xe", "Cho tôi muốn đặt xe"),
    ],
)
@pytest.mark.asyncio
async def test_rewrite_can_remove_bounded_low_confidence_numeric_asr_artifacts(
    raw: str,
    normalized: str,
) -> None:
    result = await _openai_rewriter(normalized).rewrite(
        raw,
        session_context={"asr_confidence": 0.0},
        session_id="session",
    )

    assert result.applied is True
    assert result.normalized_text == normalized
    assert result.reason == "applied"


def test_numeric_guard_never_removes_a_valid_vehicle_or_ordinal_number() -> None:
    assert _numeric_semantics_preserved(
        "Cho tôi xe 4 chỗ",
        "Cho tôi xe bốn chỗ",
        asr_confidence=0.0,
    ) == (False, "removed_numeric_fact")
    assert _numeric_semantics_preserved(
        "Tôi chọn số 1",
        "Tôi chọn số một",
        asr_confidence=0.0,
    ) == (False, "removed_numeric_fact")


@pytest.mark.asyncio
async def test_rewrite_barrier_is_capped_at_two_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rewrite_module, "MAX_REWRITE_BARRIER_SECONDS", 0.01)
    message = llm.ChatMessage(role="user", content=["Đổi điểm đón sang Hồ Gương"])

    result = await rewrite_livekit_user_turn(
        rewriter=_HangingRewriter(),
        userdata=_userdata(),
        turn_ctx=llm.ChatContext.empty(),
        new_message=message,
    )

    assert result is not None and result.reason == "provider_timeout"
    assert message.text_content == "Đổi điểm đón sang Hồ Gương"


@pytest.mark.asyncio
async def test_one_finalized_item_is_processed_once() -> None:
    userdata = _userdata()
    rewriter = _Rewriter()
    message = llm.ChatMessage(role="user", content=["Đổi điểm đón sang Hồ Gương"])

    first = await rewrite_livekit_user_turn(
        rewriter=rewriter,
        userdata=userdata,
        turn_ctx=llm.ChatContext.empty(),
        new_message=message,
    )
    second = await rewrite_livekit_user_turn(
        rewriter=rewriter,
        userdata=userdata,
        turn_ctx=llm.ChatContext.empty(),
        new_message=message,
    )

    assert first is not None
    assert second is first
    assert len(rewriter.calls) == 1


@pytest.mark.asyncio
async def test_concurrent_hooks_join_one_rewrite_before_mutating_messages() -> None:
    userdata = _userdata()
    rewriter = _BlockingRewriter()
    message_id = "item-shared"
    parent_message = llm.ChatMessage(
        id=message_id,
        role="user",
        content=["Đổi điểm đón sang Hồ Gương"],
    )
    task_message = llm.ChatMessage(
        id=message_id,
        role="user",
        content=["Đổi điểm đón sang Hồ Gương"],
    )

    parent_hook = asyncio.create_task(
        rewrite_livekit_user_turn(
            rewriter=rewriter,
            userdata=userdata,
            turn_ctx=llm.ChatContext.empty(),
            new_message=parent_message,
        )
    )
    await rewriter.started.wait()
    task_hook = asyncio.create_task(
        rewrite_livekit_user_turn(
            rewriter=rewriter,
            userdata=userdata,
            turn_ctx=llm.ChatContext.empty(),
            new_message=task_message,
        )
    )
    await asyncio.sleep(0)

    assert task_hook.done() is False
    assert parent_message.text_content == "Đổi điểm đón sang Hồ Gương"
    assert task_message.text_content == "Đổi điểm đón sang Hồ Gương"

    rewriter.release.set()
    parent_result, task_result = await asyncio.gather(parent_hook, task_hook)

    assert parent_result is task_result
    assert len(rewriter.calls) == 1
    assert parent_message.text_content == "Đổi điểm đón sang Hồ Gươm"
    assert task_message.text_content == "Đổi điểm đón sang Hồ Gươm"
