"""Bounded contextual correction between finalized STT and the agent LLM."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import unicodedata
from collections import Counter
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
_REPEATED_SHORT_ORDINAL = re.compile(
    rf"^(?:(?:toi|minh)\s+)?(?:(?:chon|lay)\s+)?(?:(?:phuong\s+an|lua\s+chon)\s+)?"
    rf"(?:(?:so|thu)\s+)?(?P<ordinal>{_ORDINAL_TOKEN})"
    rf"(?:\s+(?:(?:so|thu)\s+)?(?P=ordinal)){{1,4}}$"
)
_TRACKING_FIVE_MINUTES_ASR = re.compile(r"^(?:so\s+)?(?:nam|5)(?:\s+(?:phuc|phut))?$")

REWRITE_INSTRUCTIONS = """Bạn sửa transcript ASR tiếng Việt cho tổng đài đặt xe AloSM.

Thực hiện nội bộ theo đúng thứ tự:
1. Suy luận intent của câu hiện tại từ tối đa ba cặp assistant-user gần nhất và BookingDraft.
2. Sửa lỗi âm gần nhau, dấu, tách từ và tên địa điểm theo đúng intent đó.
3. Kiểm tra lại rằng không thêm, bỏ hoặc đổi điểm đón, điểm đến, loại xe, phủ định hay xác nhận.

Quy tắc bắt buộc:
- recent_dialogue_pairs và booking_state chỉ là ngữ cảnh, không được chép thông tin từ đó vào câu hiện tại.
- Nếu khách đổi điểm đón, điểm đến hoặc loại xe, phải giữ chính xác intent đổi thông tin.
- Không tự chọn candidate và không biến câu mơ hồ thành một địa điểm cụ thể.
- Không đổi từ/cụm từ thành chữ số hoặc mã chữ-số không có trong transcript gốc.
- Riêng khi câu hỏi gần nhất hỏi theo dõi chuyến xe sau bao nhiêu phút, cụm âm gần
  "Nam", "Năm Phúc" có thể mang nghĩa "5 phút"; không áp dụng cách sửa này ở ngữ cảnh khác.
- Có thể bỏ một mã chữ-số hoặc chuỗi số lặp rõ ràng do ASR sinh nhầm khi độ tin cậy ASR thấp
  và ngữ cảnh hội thoại chứng minh được cách sửa; không được bỏ số thứ tự, địa chỉ hoặc loại xe hợp lệ.
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
        "TRACK_BOOKING",
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
        turn_id: str | None = None,
    ) -> TranscriptRewriteResult: ...


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def is_short_ordinal_selection(text: str) -> bool:
    """Return true only for a self-contained numbered candidate choice."""

    folded = _fold(text)
    return bool(folded and (_SHORT_ORDINAL.fullmatch(folded) or _REPEATED_SHORT_ORDINAL.fullmatch(folded)))


def _contextual_tracking_interval(text: str, turn_ctx: llm.ChatContext) -> str | None:
    """Recover five minutes only when the immediately preceding prompt asks for it."""

    if not _TRACKING_FIVE_MINUTES_ASR.fullmatch(_fold(text)):
        return None
    latest_assistant = next(
        (
            (item.text_content or "").strip()
            for item in reversed(turn_ctx.items)
            if isinstance(item, llm.ChatMessage) and item.role == "assistant" and (item.text_content or "").strip()
        ),
        "",
    )
    folded_prompt = _fold(latest_assistant)
    asks_tracking_minutes = (
        "theo doi" in folded_prompt
        and "phut" in folded_prompt
        and any(marker in folded_prompt for marker in ("bao nhieu", "may phut", "sau"))
    )
    return "5 phút" if asks_tracking_minutes else None


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
    asr_confidence: float | None = None,
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
            "post_booking_support": (
                userdata.post_booking_support.model_dump(mode="json") if userdata.post_booking_support else None
            ),
        },
        "asr_confidence": asr_confidence,
    }


def _numeric_sequences(text: str) -> Counter[str]:
    return Counter(re.findall(r"\d+", text))


def _suspicious_asr_numeric_sequences(text: str) -> Counter[str]:
    """Identify bounded numeric artifacts that a low-confidence STT may emit."""

    suspicious: Counter[str] = Counter()
    tokens = re.findall(r"\w+", unicodedata.normalize("NFC", text), flags=re.UNICODE)
    for token in tokens:
        digit_sequences = re.findall(r"\d+", token)
        if digit_sequences and any(char.isalpha() for char in token):
            suspicious.update(digit_sequences)
            continue
        if token.isdigit() and len(token) >= 2 and len(token) % 2 == 0:
            midpoint = len(token) // 2
            if token[:midpoint] == token[midpoint:]:
                suspicious[token] += 1
    for previous, current in zip(tokens, tokens[1:], strict=False):
        if previous.isdigit() and previous == current:
            suspicious[previous] += 2
    return suspicious


def _numeric_semantics_preserved(
    raw_text: str,
    normalized_text: str,
    *,
    asr_confidence: float | None,
) -> tuple[bool, str]:
    """Reject invented numbers while permitting narrowly bounded STT repairs."""

    raw = _numeric_sequences(raw_text)
    normalized = _numeric_sequences(normalized_text)
    if raw == normalized:
        return True, "unchanged"
    if normalized - raw:
        return False, "introduced_numeric_token"

    removed = raw - normalized
    low_confidence = asr_confidence is not None and asr_confidence <= 0.5
    suspicious = _suspicious_asr_numeric_sequences(raw_text)
    if low_confidence and not (removed - suspicious):
        return True, "removed_low_confidence_asr_artifact"
    return False, "removed_numeric_fact"


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
        turn_id: str | None = None,
    ) -> TranscriptRewriteResult:
        from src.backend.observability.langfuse_client import langfuse_generation

        started = time.monotonic()
        kwargs: dict[str, Any] = {}
        if self.model.rsplit("/", 1)[-1].startswith("gpt-5") and self.reasoning_effort != "none":
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        with langfuse_generation(
            name="transcript_rewrite",
            model=self.model,
            session_id=session_id,
            turn_id=turn_id,
            prompt_preview=text,
        ) as generation:
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
                if generation is not None:
                    generation.set_usage(getattr(response, "usage", None))
                parsed = response.output_parsed
                if parsed is None:
                    raise ValueError("empty parsed rewrite")
            except (OpenAIError, TimeoutError, ValueError) as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                if generation is not None:
                    generation.set_error(exc)
                    generation.set_output(text, outcome="provider_error")
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
            asr_confidence_value = session_context.get("asr_confidence")
            asr_confidence = (
                float(asr_confidence_value) if isinstance(asr_confidence_value, (int, float)) else None
            )
            semantic_ok, numeric_reason = _numeric_semantics_preserved(
                text,
                normalized,
                asr_confidence=asr_confidence,
            )
            if not semantic_ok:
                logger.warning(
                    "Voice transcript rewrite numeric guard rejected model=%s reason=%s "
                    "raw_numeric_count=%d normalized_numeric_count=%d asr_confidence=%s",
                    self.model,
                    numeric_reason,
                    sum(_numeric_sequences(text).values()),
                    sum(_numeric_sequences(normalized).values()),
                    asr_confidence,
                )
            elif numeric_reason == "removed_low_confidence_asr_artifact":
                logger.info(
                    "Voice transcript rewrite removed low-confidence numeric ASR artifact model=%s",
                    self.model,
                )
            accepted = parsed.meaning_preserved and parsed.confidence >= self.minimum_confidence and semantic_ok
            if accepted:
                reason = "applied" if normalized != text else "unchanged"
            elif not semantic_ok:
                reason = "numeric_semantics_rejected"
            else:
                reason = "rejected"
            normalized_result = normalized if accepted else text
            if generation is not None:
                generation.set_output(normalized_result, outcome=reason)
                generation.span.set_attribute(
                    "langfuse.observation.metadata.rewrite_confidence",
                    parsed.confidence,
                )
                generation.span.set_attribute(
                    "langfuse.observation.metadata.meaning_preserved",
                    parsed.meaning_preserved,
                )
            return TranscriptRewriteResult(
                raw_text=text,
                normalized_text=normalized_result,
                applied=accepted and normalized != text,
                reason=reason,
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
    asr_confidence: float | None,
) -> TranscriptRewriteResult:
    """Compute one rewrite result without mutating the LiveKit message."""

    tracking_interval = _contextual_tracking_interval(text, turn_ctx)
    if tracking_interval is not None:
        logger.info(
            "Voice transcript rewrite applied deterministic tracking interval item_id=%s raw=%s",
            item_id,
            text,
        )
        return TranscriptRewriteResult(
            raw_text=text,
            normalized_text=tracking_interval,
            applied=tracking_interval != text,
            reason="contextual_tracking_interval",
            inferred_intent="TRACK_BOOKING",
            confidence=1.0,
        )
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
        asr_confidence=asr_confidence,
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
                turn_id=item_id,
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
                    asr_confidence=new_message.transcript_confidence,
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
