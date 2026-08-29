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
    BookingResult,
    BookingTarget,
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
    ) -> None:
        self._places = places or PlaceToolsService()
        self._quotes = quotes or QuoteToolsService()
        self._bookings = bookings or BookingToolsService()
        self._state_store = state_store or EphemeralVoiceStateStore()
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

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
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

        Nếu có nhiều candidate, không tự chọn hoặc suy đoán: đọc các lựa chọn
        và gọi select_place bằng place_id sau khi khách chọn. Nếu không tìm
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
            return json.dumps(
                {
                    "target": target,
                    "auto_selected": True,
                    "place_id": selected.place_id,
                    "display_name": selected.display_name,
                    "quote_refreshed": refreshed_quote is not None,
                    "instruction": (
                        "Đã cập nhật và tính lại báo giá; đọc giá mới, không dùng giá cũ."
                        if refreshed_quote is not None
                        else "Đã tự chọn exact match duy nhất; tiếp tục trường còn thiếu, không hỏi lại."
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
                "instruction": "Hỏi khách chọn/xác nhận một candidate trước khi gọi select_place.",
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
        target_label = "điểm đón" if target == "pickup" else "điểm đến"
        suffix = " Đã tính lại báo giá mới." if refreshed_quote is not None else ""
        return f"Đã xác nhận {target_label}: {selected.display_name}, {selected.address}.{suffix}"

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
        suffix = " Đã tính lại báo giá mới." if refreshed_quote is not None else ""
        return f"Đã chọn {vehicle_spoken_label(vehicle_type)}.{suffix}"

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
        try:
            self._draft(context).confirm()
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
