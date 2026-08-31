"""LiveKit ``AgentTask`` implementing AloSM's native booking happy path."""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from typing import Literal

from livekit.agents import AgentTask, RunContext, StopResponse, ToolError, function_tool, llm
from pydantic import BaseModel, ConfigDict

from src.voice_agent.persistence import (
    EphemeralVoiceStateStore,
    VoiceStateConflictError,
    VoiceStateStore,
)
from src.voice_agent.session_data import (
    AloSMSessionData,
    BookingDraft,
    BookingResult,
    BookingTarget,
    PlaceCandidate,
    QuoteSnapshot,
    VehicleType,
    vehicle_spoken_label,
)
from src.voice_agent.state_sync import publish_booking_state
from src.voice_agent.tools import (
    BookingToolsService,
    HandoffToolsService,
    PlaceToolsService,
    QuoteToolsService,
)
from src.voice_agent.transcript_rewrite import TranscriptRewriter, rewrite_livekit_user_turn

logger = logging.getLogger(__name__)

_LOW_CONFIDENCE_TRUSTED_PLACE_PROVIDERS = frozenset(
    {"local_gazetteer", "local_landmark_mock", "local_landmark_mock_exact"}
)


class BookingOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["created", "abandoned", "needs_handoff"]
    message: str
    booking: BookingResult | None = None
    reason: str | None = None


def _normalize_confirmation(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def is_explicit_confirmation(value: str) -> bool:
    normalized = _normalize_confirmation(value)
    negative_tokens = {"khong", "chua", "huy", "thoi"}
    if not normalized or negative_tokens.intersection(normalized.split()) or "dung dat" in normalized:
        return False
    affirmative_phrases = (
        "toi xac nhan",
        "xac nhan dat",
        "dong y dat",
        "dat chuyen nay",
        "dat xe di",
        "dung roi dat",
        "ok dat",
    )
    return any(phrase in normalized for phrase in affirmative_phrases)


def is_booking_abandonment_request(value: str) -> bool:
    """Recognize an explicit request to stop an unfinished booking draft."""

    normalized = _normalize_confirmation(value)
    return any(
        phrase in normalized
        for phrase in (
            "khong dat nua",
            "thoi khong dat",
            "dung dat nua",
            "bo dat xe",
            "huy yeu cau dat xe",
            "khong muon dat xe nua",
        )
    )


def requires_location_clarification(
    message: llm.ChatMessage | None,
    threshold: float,
    candidates: list[object] | None = None,
) -> bool:
    """Repeat only when low-confidence speech has no trusted location match.

    Scribe realtime can omit word logprobs and report zero confidence for an
    otherwise correct transcript. A canonical/alias gazetteer match is stronger
    evidence than that missing confidence signal; fuzzy matches remain blocked.
    """

    is_low_confidence = (
        message is not None and message.transcript_confidence is not None and message.transcript_confidence < threshold
    )
    has_trusted_candidate = any(
        getattr(candidate, "provider", None) in _LOW_CONFIDENCE_TRUSTED_PLACE_PROVIDERS
        for candidate in (candidates or [])
    )
    return is_low_confidence and not has_trusted_candidate


def can_auto_select_place(candidates: list[object]) -> bool:
    """Auto-select only one deterministic exact/alias gazetteer result.

    Fuzzy results and landmarks with multiple pickup points remain explicit
    clarification turns because a location is a booking-critical entity.
    """

    return len(candidates) == 1 and getattr(candidates[0], "provider", None) in {
        "local_gazetteer",
        "local_landmark_mock_exact",
    }


_CANDIDATE_NUMBER_TOKENS: dict[str, int] = {
    "1": 0,
    "mot": 0,
    "nhat": 0,
    "2": 1,
    "hai": 1,
    "3": 2,
    "ba": 2,
    "4": 3,
    "bon": 3,
    "tu": 3,
    "5": 4,
    "nam": 4,
}
_SHORT_CANDIDATE_SELECTION = re.compile(
    r"^(?:(?:toi|minh)\s+)?(?:(?:chon|lay)\s+)?(?:(?:phuong\s+an|lua\s+chon)\s+)?"
    r"(?:(?:so|thu)\s+)?(1|2|3|4|5|mot|hai|ba|bon|tu|nam|nhat)$"
)


def grounded_ordinal_selection(
    draft: BookingDraft,
    user_text: str,
) -> tuple[BookingTarget, PlaceCandidate] | None:
    """Resolve a short ordinal only against the active server-owned candidate list."""

    normalized = _normalize_confirmation(user_text)
    match = _SHORT_CANDIDATE_SELECTION.fullmatch(normalized)
    target = draft.pending_candidate_target
    if match is None or target is None:
        return None
    candidates = draft.pickup_candidates if target == "pickup" else draft.destination_candidates
    index = _CANDIDATE_NUMBER_TOKENS[match.group(1)]
    if index >= len(candidates):
        return None
    return target, candidates[index]


def _candidate_surfaces(draft: BookingDraft, target: BookingTarget, candidate: PlaceCandidate) -> set[str]:
    query = draft.pickup_query if target == "pickup" else draft.destination_query
    normalized_query = _normalize_confirmation(query or "")
    normalized_name = _normalize_confirmation(candidate.display_name)
    surfaces = {normalized_name, _normalize_confirmation(candidate.address)}
    if normalized_query and normalized_name.endswith(normalized_query):
        short_name = normalized_name[: -len(normalized_query)].strip()
        if short_name:
            surfaces.add(short_name)
    return {surface for surface in surfaces if len(surface) >= 3}


def _surface_is_negated(normalized_text: str, surface: str) -> bool:
    return bool(re.search(rf"\bkhong\s+(?:phai\s+)?(?:la\s+)?{re.escape(surface)}\b", normalized_text))


def grounded_named_place_selection(
    draft: BookingDraft,
    user_text: str,
) -> tuple[BookingTarget, PlaceCandidate] | None:
    """Match exactly one saved candidate name while respecting explicit negation."""

    normalized = _normalize_confirmation(user_text)
    matches: dict[tuple[BookingTarget, str], PlaceCandidate] = {}
    for target, candidates in (
        ("pickup", draft.pickup_candidates),
        ("destination", draft.destination_candidates),
    ):
        current = draft.pickup if target == "pickup" else draft.destination
        for candidate in candidates:
            surfaces = _candidate_surfaces(draft, target, candidate)
            if not any(surface in normalized and not _surface_is_negated(normalized, surface) for surface in surfaces):
                continue
            if current is not None and current.place_id == candidate.place_id and "chon" not in normalized:
                continue
            matches[(target, candidate.place_id)] = candidate
    if len(matches) != 1:
        return None
    (target, _), candidate = next(iter(matches.items()))
    return target, candidate


_VEHICLE_SURFACES: dict[VehicleType, tuple[str, ...]] = {
    "MOTORBIKE": ("xe may",),
    "CAR_4": ("xe 4 cho", "xe bon cho", "o to 4 cho", "o to bon cho"),
    "CAR_7": ("xe 7 cho", "xe bay cho", "o to 7 cho", "o to bay cho"),
    "LUXURY": ("xe cao cap", "xe sang"),
}


def grounded_vehicle_selection(draft: BookingDraft, user_text: str) -> VehicleType | None:
    """Resolve one explicit supported vehicle, including numbered vehicle choices."""

    normalized = _normalize_confirmation(user_text)
    ordinal = _SHORT_CANDIDATE_SELECTION.fullmatch(normalized)
    if ordinal is not None and draft.pending_candidate_target is None and draft.vehicle_type is None:
        index = _CANDIDATE_NUMBER_TOKENS[ordinal.group(1)]
        vehicle_types = list(_VEHICLE_SURFACES)
        return vehicle_types[index] if index < len(vehicle_types) else None

    matches = {
        vehicle_type
        for vehicle_type, surfaces in _VEHICLE_SURFACES.items()
        if any(surface in normalized and not _surface_is_negated(normalized, surface) for surface in surfaces)
    }
    if len(matches) != 1:
        return None
    selected = next(iter(matches))
    if draft.vehicle_type is not None and draft.vehicle_type == selected:
        return None
    return selected


def _target_label(target: BookingTarget) -> str:
    return "điểm đón" if target == "pickup" else "điểm đến"


def _selection_followup(draft: BookingDraft, target: BookingTarget, selected: PlaceCandidate) -> str | None:
    prefix = f"Đã chọn {_target_label(target)} là {selected.display_name}."
    if draft.pickup is None:
        return f"{prefix} Vui lòng cho biết điểm đón. Nếu muốn đổi, bạn có thể nói lại."
    if draft.destination is None:
        return f"{prefix} Vui lòng cho biết điểm đến. Nếu muốn đổi, bạn có thể nói lại."
    if draft.vehicle_type is None:
        return (
            f"{prefix} Vui lòng chọn loại xe theo số thứ tự được liệt kê bên dưới. "
            "Nếu muốn đổi, bạn có thể nói lại."
        )
    return None


def _vehicle_followup(draft: BookingDraft, vehicle_type: VehicleType) -> str | None:
    prefix = f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}."
    if draft.pickup is None:
        return f"{prefix} Vui lòng cho biết điểm đón. Nếu muốn đổi, bạn có thể nói lại."
    if draft.destination is None:
        return f"{prefix} Vui lòng cho biết điểm đến. Nếu muốn đổi, bạn có thể nói lại."
    return None


def _quote_confirmation_prompt(draft: BookingDraft, acknowledgement: str, quote: QuoteSnapshot) -> str:
    return (
        f"{acknowledgement} Bạn xác nhận chuyến xe đón tại {draft.pickup.display_name}, "
        f"đến {draft.destination.display_name}, đi bằng {vehicle_spoken_label(draft.vehicle_type)}, "
        f"giá dự kiến {quote.fare_amount} đồng và xe tới sau khoảng {quote.eta_minutes} phút chứ?"
    )


class BookingTask(AgentTask[BookingOutcome]):
    """Collect and validate one booking while preserving the single AloSM persona."""

    def __init__(
        self,
        *,
        chat_ctx: llm.ChatContext | None = None,
        places: PlaceToolsService | None = None,
        quotes: QuoteToolsService | None = None,
        bookings: BookingToolsService | None = None,
        state_store: VoiceStateStore | None = None,
        session_data: AloSMSessionData | None = None,
        transcript_rewriter: TranscriptRewriter | None = None,
    ) -> None:
        self._places = places or PlaceToolsService()
        self._quotes = quotes or QuoteToolsService()
        self._bookings = bookings or BookingToolsService()
        self._state_store = state_store or EphemeralVoiceStateStore()
        self._session_data = session_data
        self._transcript_rewriter = transcript_rewriter
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=(
                "Bạn vẫn là tổng đài viên AloSM, đang thực hiện đúng một yêu cầu đặt xe. "
                "Nói tiếng Việt tự nhiên, ngắn gọn và mỗi lượt chỉ hỏi một thông tin. "
                "Đây là nội dung đọc thành tiếng: gọi khách là bạn hoặc quý khách; không dùng dấu "
                "gạch chéo, chữ viết tắt, mã enum hoặc ký hiệu tiền tệ trong câu trả lời. "
                "Đọc MOTORBIKE là xe máy, CAR_4 là xe ô tô bốn chỗ, CAR_7 là xe ô tô bảy chỗ, "
                "LUXURY là xe cao cấp và VND là đồng. "
                "Phải dùng search_place cho lời người dùng nói về địa điểm; không tự tạo place_id. "
                "Chỉ dùng select_place với candidate_id có trong kết quả tìm kiếm hiện hành. "
                "Nếu search_place báo đã tự chọn một kết quả khớp duy nhất thì không hỏi xác nhận "
                "địa điểm đó lần nữa. Với kết quả mơ hồ, phải hỏi khách chọn candidate. "
                "Khi có nhiều candidate, chỉ nói số lượng kết quả và yêu cầu khách chọn số hiển thị bên dưới; "
                "tuyệt đối không đọc tên hoặc địa chỉ trong danh sách vì giao diện đã hiển thị chúng. "
                "Một lựa chọn theo số hợp lệ cập nhật slot ngay và không cần xác nhận candidate lần hai. "
                "Sau mọi thay đổi điểm đón, điểm đến hoặc loại xe, câu trả lời bắt buộc phải bắt đầu bằng "
                "'Đã chọn điểm đón là...', 'Đã chọn điểm đến là...' hoặc 'Đã chọn loại xe là...'; "
                "chỉ sau câu đó mới hỏi trường tiếp theo. Nếu chưa có loại xe, phải hỏi khách chọn loại xe "
                "theo số thứ tự được liệt kê bên dưới để giao diện hiện danh sách xe. "
                "Thu thập đủ điểm đón, điểm đến và loại xe rồi gọi estimate_fare. "
                "estimate_fare đồng thời khóa báo giá ở trạng thái chờ xác nhận; đọc lại đầy đủ "
                "thông tin mà tool trả về và không tự bỏ qua bước này. "
                "Chỉ gọi confirm_booking khi lượt nói mới nhất của khách xác nhận đặt chuyến rõ ràng. "
                "Chỉ gọi create_booking sau khi confirm_booking thành công. "
                "Nếu khách sửa điểm đón, điểm đến hoặc loại xe, gọi tool tương ứng; hệ thống sẽ "
                "tự xoá giá và xác nhận cũ. Không được tự bịa giá, ETA hoặc mã chuyến. "
                "Nếu tool báo ASR_LOW_CONFIDENCE thì yêu cầu khách nói lại hoặc nhập tay. "
                "Nếu khách yêu cầu gặp người thật, tổng đài viên thật, nhân viên thật, operator hoặc yêu cầu chuyển máy, "
                "hãy kết thúc task với trạng thái cần chuyển tổng đài viên; không tự tạo handoff trong task. "
                "Nếu khách nói rõ không muốn đặt xe nữa, hãy kết thúc task với trạng thái abandoned."
            ),
        )

    async def on_enter(self) -> None:
        current_state = self.session.userdata.booking_draft.conversation_summary()
        self.session.generate_reply(
            instructions=(
                f"Trạng thái booking hiện tại: {current_state}. "
                "Dựa trên yêu cầu đặt xe gần nhất của khách và trạng thái này, hãy gọi tool cần thiết ngay. "
                "Nếu yêu cầu chưa có đủ thông tin thì hỏi đúng một thông tin còn thiếu."
            )
        )

    @staticmethod
    def _draft(context: RunContext[AloSMSessionData]):
        return context.userdata.booking_draft

    def _latest_user_message(self) -> llm.ChatMessage | None:
        for item in reversed(self.chat_ctx.items):
            if getattr(item, "role", None) == "user":
                return item if isinstance(item, llm.ChatMessage) else None
        return None

    async def _respond_after_grounded_change(
        self,
        userdata: AloSMSessionData,
        *,
        acknowledgement: str,
        followup: str | None,
    ) -> None:
        """Persist one deterministic slot change and speak acknowledgement first."""

        draft = userdata.booking_draft
        response = followup
        if response is None and draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None:
            try:
                quote = await self._quotes.estimate(
                    user_id=userdata.user_id,
                    app_session_id=userdata.app_session_id,
                    draft=draft,
                )
                draft.set_quote(quote)
                draft.request_confirmation()
                response = _quote_confirmation_prompt(draft, acknowledgement, quote)
                userdata.clear_failure()
            except ValueError:
                userdata.record_failure(
                    "QUOTE_UNAVAILABLE",
                    "Chưa thể tính báo giá từ thông tin mới.",
                    fallback_action="retry",
                )
                response = f"{acknowledgement} Hiện chưa thể tính báo giá, bạn vui lòng thử lại."
        try:
            await self._state_store.save(userdata)
        except VoiceStateConflictError:
            userdata.record_failure(
                "STATE_CONFLICT",
                "Phiên này vừa được cập nhật ở kết nối khác.",
                retryable=False,
                fallback_action="handoff",
            )
            await publish_booking_state(self.session)
            raise StopResponse() from None
        await publish_booking_state(self.session)
        self.session.say(response or acknowledgement, allow_interruptions=True)
        raise StopResponse()

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        userdata = self._session_data or self.session.userdata
        await rewrite_livekit_user_turn(
            rewriter=self._transcript_rewriter,
            userdata=userdata,
            turn_ctx=turn_ctx,
            new_message=new_message,
        )

        grounded = grounded_ordinal_selection(
            userdata.booking_draft,
            new_message.text_content or "",
        ) or grounded_named_place_selection(
            userdata.booking_draft,
            new_message.text_content or "",
        )
        if grounded is not None:
            target, candidate = grounded
            selected = userdata.booking_draft.select_place(target, candidate.place_id)
            logger.info(
                "Booking candidate selected deterministically session=%s target=%s user_text=%r place_id=%s",
                userdata.app_session_id,
                target,
                new_message.text_content,
                selected.place_id,
            )
            followup = _selection_followup(userdata.booking_draft, target, selected)
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=f"Đã chọn {_target_label(target)} là {selected.display_name}.",
                followup=followup,
            )

        vehicle_type = grounded_vehicle_selection(userdata.booking_draft, new_message.text_content or "")
        if vehicle_type is not None:
            userdata.booking_draft.set_vehicle_type(vehicle_type)
            logger.info(
                "Booking vehicle selected deterministically session=%s user_text=%r vehicle_type=%s",
                userdata.app_session_id,
                new_message.text_content,
                vehicle_type,
            )
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}.",
                followup=_vehicle_followup(userdata.booking_draft, vehicle_type),
            )

        # Handoff and abandonment are task completions, not booking tools. The
        # supervisor owns call-level handoff and the result remains typed.
        current = self.session.userdata.handoff
        if current is not None and current.status in {"pending", "accepted", "connected"}:
            raise StopResponse()
        if HandoffToolsService.is_handoff_request(new_message.text_content or ""):
            outcome = BookingOutcome(
                status="needs_handoff",
                message="Khách yêu cầu chuyển tới tổng đài viên.",
                reason=new_message.text_content or "Khách yêu cầu gặp tổng đài viên.",
            )
            if not self.done():
                self.complete(outcome)
            raise StopResponse()
        if is_booking_abandonment_request(new_message.text_content or ""):
            outcome = BookingOutcome(
                status="abandoned",
                message="Đã dừng yêu cầu đặt xe.",
                reason=new_message.text_content or "Khách không muốn tiếp tục đặt xe.",
            )
            if not self.done():
                self.complete(outcome)
            raise StopResponse()

    async def _interrupt_stale_speech(self, context: RunContext[AloSMSessionData]) -> None:
        """Cancel pre-tool speech so stale quote/location text is never played."""

        try:
            await context.session.interrupt()
        except RuntimeError:
            # A tool can run after speech has already completed or during startup.
            return

    async def _refresh_quote_after_change(self, context: RunContext[AloSMSessionData]) -> QuoteSnapshot | None:
        """Re-issue a quote after a correction when all booking fields remain present."""

        draft = self._draft(context)
        if draft.pickup is None or draft.destination is None or draft.vehicle_type is None:
            return None
        async with context.with_filler(
            "Đang tính lại báo giá, bạn chờ một chút nhé.",
            delay=0.8,
        ):
            try:
                quote = await self._quotes.estimate(
                    user_id=context.userdata.user_id,
                    app_session_id=context.userdata.app_session_id,
                    draft=draft,
                )
                draft.set_quote(quote)
                draft.request_confirmation()
            except ValueError:
                context.userdata.record_failure(
                    "QUOTE_UNAVAILABLE",
                    "Chưa thể tính lại báo giá từ thông tin mới.",
                    fallback_action="retry",
                )
                await self._commit(context)
                return None
            context.userdata.clear_failure()
            await self._commit(context)
            return quote

    async def _commit(self, context: RunContext[AloSMSessionData]) -> None:
        commit_started = time.perf_counter()
        state_started = time.perf_counter()
        try:
            await self._state_store.save(context.userdata)
        except VoiceStateConflictError as exc:
            logger.info(
                "[PERF-VOICE] stage=task.commit.state_store call_id=%s duration_ms=%.3f result=conflict",
                context.userdata.call_id,
                (time.perf_counter() - state_started) * 1000,
            )
            context.userdata.record_failure(
                "STATE_CONFLICT",
                "Phiên này vừa được cập nhật ở kết nối khác.",
                retryable=False,
                fallback_action="handoff",
            )
            await publish_booking_state(context.session)
            raise ToolError("STATE_CONFLICT") from exc
        logger.info(
            "[PERF-VOICE] stage=task.commit.state_store call_id=%s duration_ms=%.3f result=ok",
            context.userdata.call_id,
            (time.perf_counter() - state_started) * 1000,
        )
        await publish_booking_state(context.session)
        logger.info(
            "[PERF-VOICE] stage=task.commit.total call_id=%s duration_ms=%.3f result=ok",
            context.userdata.call_id,
            (time.perf_counter() - commit_started) * 1000,
        )

    @function_tool()
    async def search_place(
        self,
        context: RunContext[AloSMSessionData],
        target: BookingTarget,
        query: str,
    ) -> str:
        """Tìm địa điểm trong gazetteer demo từ lời nói của khách.

        Gọi sau khi khách cung cấp hoặc sửa điểm đón hay điểm đến. Tool lưu
        candidates vào booking draft. Nếu có một exact match hoặc alias duy
        nhất đáng tin cậy, tool có thể tự chọn; nếu booking đã đủ thông tin,
        tool đồng thời tính lại báo giá và trả về báo giá mới.

        Nếu có nhiều candidate, không tự chọn hoặc suy đoán: giao diện sẽ liệt
        kê các lựa chọn theo chiều dọc; chỉ nói số lượng kết quả và yêu cầu khách
        chọn theo số thứ tự, không đọc toàn bộ danh sách. Sau khi khách chọn, gọi
        select_place bằng place_id. Nếu không tìm
        thấy hoặc transcript có độ tin cậy thấp, yêu cầu khách nói lại hoặc
        nhập địa điểm.

        Không dùng để tính giá cho lộ trình thiếu dữ liệu, chọn loại xe, hoặc
        dùng place_id không có trong kết quả tìm kiếm hiện tại.

        Args:
            target: Trường cần cập nhật; chỉ dùng pickup cho điểm đón hoặc
                destination cho điểm đến.
            query: Các từ về địa điểm khách thực sự vừa nói; không tự thêm
                thông tin khách chưa cung cấp.

        Returns:
            JSON chứa candidates hoặc auto_selected. Có thể kèm quote_refreshed
            và hướng dẫn đọc báo giá mới; tìm thấy địa điểm không có nghĩa là
            đã tạo chuyến.
        """
        context.disallow_interruptions()
        latest = self._latest_user_message()
        confidence = latest.transcript_confidence if latest is not None else None
        context.userdata.last_asr_confidence = confidence
        candidates = self._places.search(query)
        if requires_location_clarification(
            latest,
            context.userdata.critical_confidence_threshold,
            candidates,
        ):
            context.userdata.record_failure(
                "ASR_LOW_CONFIDENCE",
                "Tổng đài chưa nghe rõ địa điểm quan trọng.",
                fallback_action="repeat_or_text",
            )
            await self._commit(context)
            return "ASR_LOW_CONFIDENCE: Hãy yêu cầu khách nói lại địa điểm hoặc nhập tay."

        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        draft.set_candidates(target, query, candidates)
        if not candidates:
            context.userdata.record_failure(
                "PLACE_NOT_FOUND",
                "Không tìm thấy địa điểm phù hợp.",
                fallback_action="repeat_or_text",
            )
            await self._commit(context)
            return "Không tìm thấy địa điểm trong dữ liệu demo. Hãy hỏi khách tên địa điểm khác hoặc rõ hơn."
        if can_auto_select_place(candidates):
            selected = draft.select_place(target, candidates[0].place_id)
            refreshed_quote = (
                await self._refresh_quote_after_change(context)
                if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
                else None
            )
            if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None and refreshed_quote is None:
                return "Đã cập nhật địa điểm nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
            context.userdata.clear_failure()
            if refreshed_quote is None:
                await self._commit(context)
            acknowledgement = f"Đã chọn {_target_label(target)} là {selected.display_name}."
            spoken_prompt = (
                _quote_confirmation_prompt(draft, acknowledgement, refreshed_quote)
                if refreshed_quote is not None
                else _selection_followup(draft, target, selected) or acknowledgement
            )
            return json.dumps(
                {
                    "target": target,
                    "auto_selected": True,
                    "place_id": selected.place_id,
                    "display_name": selected.display_name,
                    "quote_refreshed": refreshed_quote is not None,
                    "spoken_prompt": spoken_prompt,
                    "instruction": (
                        "Đọc nguyên văn spoken_prompt, bắt đầu bằng xác nhận slot vừa chọn; "
                        "không bỏ qua xác nhận và không hỏi xác nhận candidate lần hai."
                    ),
                },
                ensure_ascii=False,
            )
        context.userdata.clear_failure()
        await self._commit(context)
        return json.dumps(
            {
                "target": target,
                "candidates": [candidate.model_dump() for candidate in candidates],
                "spoken_prompt": (
                    f"Đã tìm thấy {len(candidates)} địa điểm liên quan đến {query} trong dữ liệu. "
                    "Vui lòng chọn theo số thứ tự được liệt kê bên dưới."
                ),
                "instruction": (
                    "Đọc nguyên văn spoken_prompt; không đọc tên hay địa chỉ candidates. "
                    "Danh sách đã được gửi riêng tới giao diện."
                ),
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def select_place(
        self,
        context: RunContext[AloSMSessionData],
        target: BookingTarget,
        place_id: str,
    ) -> str:
        """Chọn và ghi nhận một candidate từ kết quả tìm kiếm hiện tại.

        Chỉ gọi sau khi search_place trả về nhiều candidate và khách đã chọn
        hoặc xác nhận một candidate. place_id phải lấy nguyên văn từ kết quả
        search_place gần nhất cho cùng target; không tự tạo, đoán, dịch hoặc
        dùng place_id cũ.

        Tool cập nhật booking draft. Khi pickup, destination và vehicle_type
        đã đủ, tool tự tính lại báo giá và làm mất hiệu lực báo giá cũ. Phải
        đọc giá mới, không dùng lại giá trước đó. Nếu chưa có candidate, gọi
        search_place trước.

        Args:
            target: Trường địa điểm cần chọn; chỉ dùng pickup hoặc destination.
            place_id: Mã chính xác do search_place trả về cho target hiện tại.

        Returns:
            Thông báo địa điểm đã chọn, có thể kèm báo giá mới. Tool không xác
            nhận khách đặt xe và không tạo booking.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        try:
            selected = draft.select_place(target, place_id)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        refreshed_quote = (
            await self._refresh_quote_after_change(context)
            if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
            else None
        )
        if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None and refreshed_quote is None:
            return "Đã xác nhận địa điểm nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
        context.userdata.clear_failure()
        if refreshed_quote is None:
            await self._commit(context)
        acknowledgement = f"Đã chọn {_target_label(target)} là {selected.display_name}."
        if refreshed_quote is not None:
            return _quote_confirmation_prompt(draft, acknowledgement, refreshed_quote)
        return _selection_followup(draft, target, selected) or acknowledgement

    @function_tool()
    async def set_vehicle_type(
        self,
        context: RunContext[AloSMSessionData],
        vehicle_type: VehicleType,
    ) -> str:
        """Cập nhật loại xe mà khách đã chọn trong booking draft.

        Chỉ gọi khi khách nói rõ loại xe thuộc danh mục được hỗ trợ. Nếu pickup
        và destination đã có, tool tính lại báo giá theo loại xe mới và làm mất
        hiệu lực báo giá cũ. Không tự đọc mã enum hoặc tự tính giá.

        Không gọi khi khách chỉ hỏi các loại xe; Supervisor sẽ gọi
        get_vehicle_options. Không tự chọn xe thay khách và không coi việc chọn
        xe là xác nhận đặt chuyến.

        Args:
            vehicle_type: Một trong MOTORBIKE, CAR_4, CAR_7 hoặc LUXURY; truyền
                đúng enum, không truyền tên hiển thị tự do.

        Returns:
            Thông báo loại xe đã chọn, có thể kèm báo giá mới hoặc hướng dẫn
            tiếp tục thu thập dữ liệu nếu chưa đủ điều kiện báo giá.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        draft.set_vehicle_type(vehicle_type)
        refreshed_quote = (
            await self._refresh_quote_after_change(context)
            if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
            else None
        )
        if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None and refreshed_quote is None:
            return "Đã cập nhật loại xe nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
        context.userdata.clear_failure()
        if refreshed_quote is None:
            await self._commit(context)
        acknowledgement = f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}."
        if refreshed_quote is not None:
            return _quote_confirmation_prompt(draft, acknowledgement, refreshed_quote)
        return _vehicle_followup(draft, vehicle_type) or acknowledgement

    @function_tool()
    async def estimate_fare(self, context: RunContext[AloSMSessionData]) -> str:
        """Tính báo giá cho booking draft đủ thông tin và yêu cầu xác nhận.

        Chỉ gọi khi draft có pickup, destination và vehicle_type hợp lệ. Tool
        tạo hoặc dùng lại báo giá phù hợp, chuyển draft sang awaiting
        confirmation, rồi trả về điểm đón, điểm đến, loại xe, giá và thời gian
        xe tới dự kiến.

        Không gọi khi còn thiếu trường; hãy dùng search_place, select_place
        hoặc set_vehicle_type. Không tự tính, làm tròn hay đoán giá/ETA. Báo
        giá không có nghĩa là chuyến đã tạo và không thay thế xác nhận rõ ràng.

        Returns:
            Hướng dẫn hỏi khách xác nhận cùng thông tin báo giá. Sau câu xác
            nhận mới của khách, gọi confirm_booking.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        if (
            draft.quote is not None
            and draft.confirmation_status == "awaiting"
            and draft.confirmation_fingerprint == draft.quote.fingerprint
        ):
            quote = draft.quote
            return (
                f"Hãy hỏi xác nhận rõ ràng: đón tại {draft.pickup.display_name}, "
                f"đến {draft.destination.display_name}, đi bằng {vehicle_spoken_label(draft.vehicle_type)}, "
                f"giá dự kiến {quote.fare_amount} đồng, "
                f"thời gian xe tới dự kiến {quote.eta_minutes} phút."
            )
        try:
            quote = await self._quotes.estimate(
                user_id=context.userdata.user_id,
                app_session_id=context.userdata.app_session_id,
                draft=draft,
            )
            draft.set_quote(quote)
            # Awaiting-confirmation is a business invariant, not an optional
            # second LLM tool choice. Keeping quote creation and confirmation
            # preparation atomic prevents a valid spoken confirmation from
            # failing when the model narrates the quote without calling another
            # tool first.
            draft.request_confirmation()
        except ValueError as exc:
            context.userdata.record_failure(
                "QUOTE_UNAVAILABLE",
                "Chưa thể tạo báo giá từ thông tin hiện tại.",
                fallback_action="retry",
            )
            await self._commit(context)
            raise ToolError(str(exc)) from exc
        context.userdata.clear_failure()
        await self._commit(context)
        return (
            f"Hãy hỏi xác nhận rõ ràng: đón tại {draft.pickup.display_name}, "
            f"đến {draft.destination.display_name}, đi bằng {vehicle_spoken_label(draft.vehicle_type)}, "
            f"giá dự kiến {quote.fare_amount} đồng, "
            f"thời gian xe tới dự kiến {quote.eta_minutes} phút."
        )

    @function_tool()
    async def confirm_booking(self, context: RunContext[AloSMSessionData]) -> str:
        """Ghi nhận xác nhận đặt chuyến rõ ràng từ câu mới nhất của khách.

        Chỉ gọi sau khi khách đã được báo đầy đủ thông tin và câu mới nhất xác
        nhận trực tiếp việc đặt xe, như “đặt xe đi” hoặc “tôi xác nhận”. Tool
        tự kiểm tra câu mới nhất và trạng thái báo giá trước khi ghi nhận.

        Không gọi cho câu hỏi về giá, đồng ý một địa điểm, “đúng rồi”, “ừ”
        hoặc sự đồng ý mơ hồ không nói rõ việc đặt chuyến. Tool này chỉ ghi
        nhận confirmation, chưa tạo booking. Nếu thành công, bắt buộc gọi
        create_booking.

        Returns:
            Thông báo xác nhận đã ghi nhận và hướng dẫn gọi create_booking.
            Nếu điều kiện chưa đúng, tool báo lỗi và không được coi booking đã
            xác nhận.
        """
        context.disallow_interruptions()
        latest = self._latest_user_message()
        latest_user_text = latest.text_content if latest is not None else ""
        if not is_explicit_confirmation(latest_user_text):
            raise ToolError("LATEST_USER_MESSAGE_IS_NOT_EXPLICIT_BOOKING_CONFIRMATION")
        draft = self._draft(context)
        existing_booking = draft.booking
        if existing_booking is not None and existing_booking.status != "CANCELLED":
            return (
                f"Chuyến xe đã được đặt thành công với mã {existing_booking.booking_id}. "
                "Không tạo thêm chuyến mới."
            )
        if draft.confirmation_status == "confirmed":
            if draft.quote is None or draft.confirmation_fingerprint != draft.quote.fingerprint:
                raise ToolError("BOOKING_CONTEXT_CHANGED")
            context.userdata.clear_failure()
            return "Khách đã xác nhận rõ ràng; có thể gọi create_booking."
        try:
            draft.confirm()
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        context.userdata.clear_failure()
        await self._commit(context)
        return "Khách đã xác nhận rõ ràng; có thể gọi create_booking."

    @function_tool(on_duplicate="confirm")
    async def create_booking(self, context: RunContext[AloSMSessionData]) -> None:
        """Tạo booking demo sau khi draft đã được xác nhận hợp lệ.

        Chỉ gọi sau khi confirm_booking thành công trong cùng quy trình và
        draft có pickup, destination, vehicle_type cùng báo giá hợp lệ. Đây là
        thao tác ghi dữ liệu cuối cùng: không gọi để xem trước giá, khi khách
        mới đồng ý mơ hồ, hoặc để lặp lại một kết quả không xác định.

        Tool idempotent theo cơ chế duplicate của LiveKit. Khi thành công,
        BookingTask hoàn tất với BookingOutcome status=created; kết quả trực
        tiếp là None và Supervisor nhận outcome chứa booking_id để thông báo.
        Nếu lỗi không xác định, không tự tạo chuyến lần nữa.

        Returns:
            Không trả nội dung hội thoại trực tiếp khi thành công; việc thông
            báo dựa trên BookingOutcome do task trả về.
        """
        # A confirmed write must finish deterministically even if the caller speaks
        # while this very short demo operation is being committed.
        context.disallow_interruptions()
        draft = self._draft(context)
        async with context.with_filler(
            "Đang hoàn tất đặt chuyến, bạn chờ một chút nhé.",
            delay=0.8,
        ):
            try:
                booking = await self._bookings.create(
                    user_id=context.userdata.user_id,
                    app_session_id=context.userdata.app_session_id,
                    draft=draft,
                )
                draft.set_booking(booking)
                context.userdata.lifecycle_status = "completed"
            except ValueError as exc:
                raise ToolError(str(exc)) from exc
            except Exception as exc:
                logger.exception("failed to create booking handoff session=%s", context.userdata.app_session_id)
                context.userdata.record_failure(
                    "BOOKING_RESULT_UNKNOWN",
                    "Chưa xác định được kết quả tạo chuyến; không tự động tạo lại.",
                    retryable=False,
                    fallback_action="handoff",
                )
                await self._commit(context)
                raise ToolError("BOOKING_RESULT_UNKNOWN") from exc
            context.userdata.clear_failure()
            await self._commit(context)
        outcome = BookingOutcome(
            status="created",
            booking=booking,
            message=f"Đặt chuyến thành công. Xe dự kiến tới sau {booking.eta_minutes} phút.",
        )
        if not self.done():
            self.complete(outcome)
        return None
