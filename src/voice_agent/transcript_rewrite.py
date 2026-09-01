"""Bounded contextual correction between finalized STT and the agent LLM."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import unicodedata
from typing import Any, Literal, Protocol, cast

from livekit.agents import llm
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

from src.voice_agent.config import LiveKitVoiceSettings
from src.voice_agent.session_data import AloSMSessionData

logger = logging.getLogger(__name__)
MAX_REWRITE_BARRIER_SECONDS = 2.0

_ORDINAL_TOKEN = r"(?:1|2|3|4|5|mot|hai|ba|bon|tu|nam|nhat)"
_SHORT_ORDINAL = re.compile(
    rf"^(?:(?:toi|minh)\s+)?(?:(?:chon|lay)\s+)?(?:(?:phuong\s+an|lua\s+chon)\s+)?"
    rf"(?:(?:so|thu)\s+)?{_ORDINAL_TOKEN}$"
)

REWRITE_INSTRUCTIONS = """Bạn sửa transcript ASR tiếng Việt cho tổng đài đặt xe AloSM.

Thực hiện nội bộ theo đúng thứ tự:
1. Suy luận intent của câu hiện tại từ tối đa ba cặp assistant-user gần nhất và BookingDraft.
2. Sửa lỗi âm gần nhau, dấu, tách từ và tên địa điểm theo đúng intent đó.
3. Kiểm tra lại rằng không thêm, bỏ hoặc đổi điểm đón, điểm đến, loại xe, phủ định hay xác nhận.

Quy tắc bắt buộc:
- recent_dialogue_pairs và booking_state chỉ là ngữ cảnh, không được chép thông tin từ đó vào câu hiện tại.
- Nếu khách đổi điểm đón, điểm đến hoặc loại xe, phải giữ chính xác intent đổi thông tin.
- Không tự chọn candidate và không biến câu mơ hồ thành một địa điểm cụ thể.
- Không trả lời khách, không giải thích và không xuất chain-of-thought.
- inferred_intent chỉ là nhãn kết quả của bước suy luận.
"""


class RewriteOutput(BaseModel):
    inferred_intent: Literal[
        "BOOK_RIDE",
        "CHANGE_PICKUP",
        "CHANGE_DESTINATION",
        "CHANGE_VEHICLE",
        "SELECT_LOCATION",
        "CONFIRM_BOOKING",
        "OTHER",
        "UNCLEAR",
    ]
    normalized_text: str = Field(min_length=1, max_length=1000)
    meaning_preserved: bool
    confidence: float = Field(ge=0, le=1)


class TranscriptRewriteResult(BaseModel):
    raw_text: str
    normalized_text: str
    applied: bool = False
    reason: str
    inferred_intent: str | None = None
    confidence: float | None = None
    model: str | None = None
    duration_ms: int = 0


class TranscriptRewriter(Protocol):
    timeout_seconds: float
    context_window_turns: int

    async def rewrite(
        self,
        text: str,
        *,
        session_context: dict[str, Any],
        session_id: str,
    ) -> TranscriptRewriteResult: ...


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def is_short_ordinal_selection(text: str) -> bool:
    """Return true only for a self-contained numbered candidate choice."""

    folded = _fold(text)
    return bool(folded and _SHORT_ORDINAL.fullmatch(folded))


def _recent_dialogue_pairs(
    turn_ctx: llm.ChatContext,
    current_text: str,
    *,
    limit: int,
) -> list[dict[str, str]]:
    messages: list[tuple[str, str]] = []
    for item in turn_ctx.items:
        if not isinstance(item, llm.ChatMessage) or item.role not in {"assistant", "user"}:
            continue
        text = (item.text_content or "").strip()
        if text:
            messages.append((item.role, text))
    if not messages or messages[-1] != ("user", current_text):
        messages.append(("user", current_text))

    pairs: list[dict[str, str]] = []
    latest_assistant: str | None = None
    for role, text in messages:
        if role == "assistant":
            latest_assistant = text
        elif latest_assistant is not None:
            pairs.append({"assistant": latest_assistant, "user": text})
            latest_assistant = None
    return pairs[-max(limit, 0) :] if limit > 0 else []


def build_rewrite_context(
    userdata: AloSMSessionData,
    turn_ctx: llm.ChatContext,
    current_text: str,
    *,
    context_window_turns: int,
) -> dict[str, Any]:
    draft = userdata.booking_draft
    return {
        "recent_dialogue_pairs": _recent_dialogue_pairs(
            turn_ctx,
            current_text,
            limit=context_window_turns,
        ),
        "booking_state": {
            "pickup": draft.pickup.display_name if draft.pickup else None,
            "destination": draft.destination.display_name if draft.destination else None,
            "vehicle_type": draft.vehicle_type,
            "confirmation_status": draft.confirmation_status,
            "clarifications": draft.booking_clarifications(),
        },
    }


class OpenAITranscriptRewriter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None,
        timeout_seconds: float,
        reasoning_effort: str,
        minimum_confidence: float,
        context_window_turns: int,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = min(timeout_seconds, MAX_REWRITE_BARRIER_SECONDS)
        self.reasoning_effort = reasoning_effort
        self.minimum_confidence = minimum_confidence
        self.context_window_turns = context_window_turns
        self.client = client or AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    async def rewrite(
        self,
        text: str,
        *,
        session_context: dict[str, Any],
        session_id: str,
    ) -> TranscriptRewriteResult:
        started = time.monotonic()
        kwargs: dict[str, Any] = {}
        if self.model.rsplit("/", 1)[-1].startswith("gpt-5") and self.reasoning_effort != "none":
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=REWRITE_INSTRUCTIONS,
                input=json.dumps(
                    {"transcript": text, **session_context},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                text_format=RewriteOutput,
                max_output_tokens=180,
                timeout=self.timeout_seconds,
                store=False,
                safety_identifier=hashlib.sha256(session_id.encode()).hexdigest()[:32],
                **kwargs,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise ValueError("empty parsed rewrite")
        except (OpenAIError, TimeoutError, ValueError) as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "Voice transcript rewrite provider failed model=%s error_type=%s duration_ms=%d",
                self.model,
                type(exc).__name__,
                duration_ms,
            )
            return TranscriptRewriteResult(
                raw_text=text,
                normalized_text=text,
                reason="provider_error",
                model=self.model,
                duration_ms=duration_ms,
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        normalized = parsed.normalized_text.strip()
        # Digits often encode candidate numbers, addresses or vehicle size. The
        # rewriter may fix spelling, but it must not invent/remove numeric facts.
        semantic_ok = sorted(re.findall(r"\d+", text)) == sorted(re.findall(r"\d+", normalized))
        accepted = parsed.meaning_preserved and parsed.confidence >= self.minimum_confidence and semantic_ok
        return TranscriptRewriteResult(
            raw_text=text,
            normalized_text=normalized if accepted else text,
            applied=accepted and normalized != text,
            reason="applied" if accepted and normalized != text else ("unchanged" if accepted else "rejected"),
            inferred_intent=parsed.inferred_intent,
            confidence=parsed.confidence,
            model=self.model,
            duration_ms=duration_ms,
        )


def build_transcript_rewriter(settings: LiveKitVoiceSettings) -> OpenAITranscriptRewriter | None:
    use_openrouter = bool(
        settings.voice_transcript_rewrite_base_url
        and "openrouter.ai" in settings.voice_transcript_rewrite_base_url.casefold()
    )
    api_key = (
        settings.openrouter_api_key.get_secret_value().strip()
        if use_openrouter
        else settings.openai_api_key.get_secret_value().strip()
    )
    if not settings.voice_transcript_rewrite_enabled or not api_key:
        return None
    return OpenAITranscriptRewriter(
        api_key=api_key,
        model=settings.voice_transcript_rewrite_model,
        base_url=settings.voice_transcript_rewrite_base_url or None,
        timeout_seconds=settings.voice_transcript_rewrite_timeout_seconds,
        reasoning_effort=settings.voice_transcript_rewrite_reasoning_effort,
        minimum_confidence=settings.voice_transcript_rewrite_minimum_confidence,
        context_window_turns=settings.voice_transcript_rewrite_context_window_turns,
    )


async def _rewrite_finalized_text(
    *,
    rewriter: TranscriptRewriter | None,
    userdata: AloSMSessionData,
    turn_ctx: llm.ChatContext,
    item_id: str,
    text: str,
) -> TranscriptRewriteResult:
    """Compute one rewrite result without mutating the LiveKit message."""

    if is_short_ordinal_selection(text):
        logger.info("Voice transcript rewrite skipped item_id=%s reason=short_ordinal", item_id)
        return TranscriptRewriteResult(raw_text=text, normalized_text=text, reason="short_ordinal")
    if rewriter is None:
        return TranscriptRewriteResult(raw_text=text, normalized_text=text, reason="disabled_or_unconfigured")

    context = build_rewrite_context(
        userdata,
        turn_ctx,
        text,
        context_window_turns=rewriter.context_window_turns,
    )
    timeout_seconds = min(max(rewriter.timeout_seconds, 0.1), MAX_REWRITE_BARRIER_SECONDS)
    started = time.monotonic()
    logger.info(
        "Voice transcript rewrite started item_id=%s timeout_seconds=%.2f context_pairs=%d",
        item_id,
        timeout_seconds,
        len(context["recent_dialogue_pairs"]),
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await rewriter.rewrite(
                text,
                session_context=context,
                session_id=userdata.app_session_id,
            )
    except TimeoutError:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "Voice transcript rewrite timed out item_id=%s duration_ms=%d limit_seconds=%.2f",
            item_id,
            duration_ms,
            timeout_seconds,
        )
        return TranscriptRewriteResult(
            raw_text=text,
            normalized_text=text,
            reason="provider_timeout",
            duration_ms=duration_ms,
        )

    logger.info(
        "Voice transcript rewrite completed item_id=%s applied=%s intent=%s reason=%s duration_ms=%d",
        item_id,
        result.applied,
        result.inferred_intent,
        result.reason,
        result.duration_ms,
    )
    return result


async def rewrite_livekit_user_turn(
    *,
    rewriter: TranscriptRewriter | None,
    userdata: AloSMSessionData,
    turn_ctx: llm.ChatContext,
    new_message: llm.ChatMessage,
) -> TranscriptRewriteResult | None:
    """Join one per-item rewrite barrier before exposing the message to the LLM."""

    text = (new_message.text_content or "").strip()
    item_id = new_message.id.strip()
    if not text or not item_id:
        return None

    async with userdata.transcript_rewrite_lock:
        existing = userdata.transcript_rewrite_tasks.get(item_id)
        if existing is None:
            task = asyncio.create_task(
                _rewrite_finalized_text(
                    rewriter=rewriter,
                    userdata=userdata,
                    turn_ctx=turn_ctx,
                    item_id=item_id,
                    text=text,
                ),
                name=f"transcript-rewrite:{item_id}",
            )
            userdata.remember_transcript_rewrite_task(item_id, task)
        else:
            task = existing

    result = cast(TranscriptRewriteResult, await asyncio.shield(task))
    if result.applied:
        async with userdata.transcript_rewrite_lock:
            current_text = (new_message.text_content or "").strip()
            if current_text in {result.raw_text, result.normalized_text}:
                non_text = [part for part in new_message.content if not isinstance(part, str)]
                new_message.content = [result.normalized_text, *non_text]
            else:
                logger.warning(
                    "Voice transcript rewrite result not applied item_id=%s reason=message_changed",
                    item_id,
                )
    return result
