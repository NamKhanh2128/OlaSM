"""The single AloSM agent used by the LiveKit-native runtime."""

import json
import logging
from typing import Any, Literal

from livekit.agents import Agent, StopResponse, function_tool, llm

from src.backend.services.knowledge_service import KnowledgeService
from src.backend.services.pricing_service import PricingService
from src.voice_agent.persistence import EphemeralVoiceStateStore, VoiceStateConflictError, VoiceStateStore
from src.voice_agent.safety import SafetyClassifier
from src.voice_agent.session_data import (
    AloSMSessionData,
    HandoffState,
    PostBookingSupportState,
    post_booking_menu_message,
)
from src.voice_agent.state_sync import publish_booking_state
from src.voice_agent.tasks import BookingTask
from src.voice_agent.tasks.booking import seed_complete_booking_turn
from src.voice_agent.tools.bookings import BookingToolsService
from src.voice_agent.tools.handoffs import HandoffToolsService
from src.voice_agent.tools.places import PlaceToolsService
from src.voice_agent.transcript_rewrite import TranscriptRewriter, rewrite_livekit_user_turn

logger = logging.getLogger(__name__)


class AloSMAgent(Agent):
    """Single call-level persona; scoped business flows run as AgentTasks."""

    def __init__(
        self,
        *,
        state_store: VoiceStateStore | None = None,
        session_data: AloSMSessionData | None = None,
        knowledge_service: KnowledgeService | None = None,
        pricing_service: PricingService | None = None,
        bookings: BookingToolsService | None = None,
        places: PlaceToolsService | None = None,
        handoffs: HandoffToolsService | None = None,
        safety_classifier: SafetyClassifier | None = None,
        transcript_rewriter: TranscriptRewriter | None = None,
    ) -> None:
        self._state_store = state_store or EphemeralVoiceStateStore()
        self._session_data = session_data
        self._safety_classifier = safety_classifier or SafetyClassifier()
        self._handoffs = handoffs or HandoffToolsService(safety_classifier=self._safety_classifier)
        self._bookings = bookings or BookingToolsService()
        self._places = places or PlaceToolsService()
        self._transcript_rewriter = transcript_rewriter
        self._handoff_wait_started = False
        # These catalogs are local, validated and cached.  They are injected so
        # the LiveKit process can preload them once instead of reading files on
        # every call or every turn.
        self._knowledge_service = knowledge_service or KnowledgeService()
        self._pricing_service = pricing_service or PricingService()
        recovered_context = ""
        if session_data is not None and session_data.recovered:
            recovered_context = (
                " Trạng thái nghiệp vụ đã khôi phục từ hệ thống: "
                f"{session_data.booking_draft.conversation_summary()}. "
                "Dùng trạng thái này khi khách hỏi lại hoặc muốn tiếp tục; không nói rằng không có lịch sử."
            )
        super().__init__(
            instructions=(
                "Bạn là tổng đài viên giọng nói AloSM nói tiếng Việt. "
                "Trả lời tự nhiên, lịch sự và ngắn gọn, thường không quá hai câu. "
                "Luôn dùng từ ngữ phù hợp để đọc thành tiếng: gọi khách là bạn hoặc quý khách; "
                "không dùng dấu gạch chéo, chữ viết tắt hay mã enum trong câu trả lời. "
                "Khi khách muốn đặt xe, phải gọi start_booking và để BookingTask thu thập, "
                "xác nhận, báo giá và tạo booking demo. Không tự bịa địa chỉ, giá, ETA hoặc mã chuyến. "
                "Mọi câu hỏi về trạng thái đặt xe, đặt thành công hay mã chuyến đều phải gọi "
                "get_booking_status trước khi trả lời. Chỉ được nói đã đặt thành công khi kết quả tool "
                "có booking_id; nếu booking_id là null thì phải nói chuyến chưa được tạo. "
                "Sau khi chuyến đã tạo, cung cấp đúng menu hỗ trợ trong kết quả BookingTask. "
                "Nếu khách chọn một, hãy hỏi nội dung cần gửi rồi gọi send_driver_request; không tự bịa yêu cầu. "
                "Nếu khách chọn hai, hỏi khách muốn mô phỏng theo dõi sau bao nhiêu phút rồi gọi track_booking. "
                "Nếu khách chọn ba, gọi cancel_booking với quy trình xác nhận hủy hiện có. "
                "Nếu khách nói không cần hỗ trợ thêm, kết thúc hoặc dừng cuộc gọi, gọi finish_customer_service "
                "để giao diện hiện đánh giá; không tự kết thúc phiên đăng nhập. "
                "Khi khách yêu cầu gặp tổng đài viên thật, gọi request_handoff; sau đó không trả lời thêm vì hệ thống sẽ chờ người thật vào phòng. "
                "Khi khách yêu cầu hủy chuyến đã tạo, gọi cancel_booking với confirmation_decision=request. Tool sẽ phát tín hiệu để giao diện hiển thị nút xác nhận. Sau khi khách chọn hoặc nói xác nhận, gọi lại cancel_booking với confirmation_decision=confirm; nếu khách từ chối, dùng confirmation_decision=decline. Chỉ được nói đã hủy khi tool trả về cancelled=true. Nếu khách dừng một booking draft chưa tạo chuyến, BookingTask sẽ trả về trạng thái abandoned. "
                "Khi khách hỏi chính sách, hành lý, phí hoặc điều kiện dịch vụ, gọi search_knowledge; "
                "khi khách hỏi các loại xe, gọi get_vehicle_options. Chỉ đọc thông tin mà tool trả về, "
                "kèm nguồn hoặc phiên bản khi phù hợp; không tự bịa hoặc dùng RAG cho báo giá một lộ trình. "
                "Ngoài các capability trên, nói rõ nếu năng lực chưa được tích hợp." + recovered_context
            )
        )

    @function_tool()
    async def start_booking(self) -> str:
        """Bắt đầu hoặc tiếp tục quy trình đặt xe trong cuộc gọi hiện tại.

        Gọi khi khách muốn đặt xe hoặc tiếp tục booking draft dang dở. Tool
        chuyển quyền tạm thời cho BookingTask để thu thập địa điểm, loại xe,
        báo giá, xác nhận và tạo chuyến.

        Không gọi để kiểm tra trạng thái chuyến, hỏi danh sách loại xe, hỏi
        chính sách, hủy chuyến đã tạo hoặc yêu cầu gặp tổng đài viên. Không tự
        suy đoán đã đặt thành công; chỉ thông báo thành công khi kết quả có
        booking_id. Nếu task trả về abandoned, thông báo rằng yêu cầu đã dừng
        và không có chuyến mới.
        """
        if self._session_data is not None and self._session_data.handoff is not None:
            if self._session_data.handoff.status in {"pending", "accepted", "connected"}:
                return "Đang chờ tổng đài viên nhận cuộc gọi; không được tiếp tục đặt xe."
        if self._session_data is not None:
            existing_booking = self._session_data.booking_draft.booking
            if existing_booking is not None and existing_booking.status != "CANCELLED":
                if self._session_data.post_booking_support is None:
                    self._session_data.post_booking_support = PostBookingSupportState.for_booking(existing_booking)
                    await self._state_store.save(self._session_data)
                return post_booking_menu_message(
                    existing_booking.booking_id,
                    existing_booking.estimated_fare,
                    existing_booking.currency,
                )
        # LiveKit recommends carrying conversation history into a task while
        # excluding the parent instructions, so the focused task prompt remains
        # small and authoritative.
        task_context = self.chat_ctx.copy(exclude_instructions=True)
        outcome = await BookingTask(
            chat_ctx=task_context,
            state_store=self._state_store,
            handoff_handler=self._create_handoff,
            session_data=self._session_data,
            transcript_rewriter=self._transcript_rewriter,
        )
        if outcome.status == "needs_handoff":
            current = self._session_data.handoff if self._session_data is not None else None
            if current is not None and current.status in {"pending", "accepted", "connected"}:
                self._enter_handoff_wait()
                raise StopResponse()
            handoff_result = await self._create_handoff(outcome.reason or outcome.message)
            if self._handoff_is_active(handoff_result):
                self._enter_handoff_wait()
                raise StopResponse()
            return handoff_result
        return outcome.message

    @staticmethod
    def _handoff_is_active(response: str) -> bool:
        try:
            status = str(json.loads(response).get("status") or "")
        except json.JSONDecodeError:
            return False
        return status in {"pending", "accepted", "connected"}

    def _enter_handoff_wait(
        self,
        *,
        acknowledgement_text: str | None = None,
        acknowledgement_handle: Any | None = None,
    ) -> None:
        """Keep the Room alive for the operator while making the AI quiescent."""

        if self._handoff_wait_started:
            return
        self._handoff_wait_started = True
        self.session.input.set_audio_enabled(False)
        acknowledgement = acknowledgement_handle or self.session.say(
            acknowledgement_text or "Tôi đã chuyển yêu cầu của bạn đến tổng đài viên. Vui lòng chờ trong giây lát.",
            allow_interruptions=False,
        )
        acknowledgement.add_done_callback(lambda _: self.session.output.set_audio_enabled(False))

    async def _create_handoff(self, reason: str) -> str:
        if self._session_data is None:
            return json.dumps(
                {"status": "failed", "message": "Chưa có phiên để chuyển tổng đài viên."},
                ensure_ascii=False,
            )
        current = self._session_data.handoff
        if current is not None and current.status in {"pending", "accepted", "connected"}:
            return json.dumps(
                {"status": current.status, "handoff_id": current.handoff_id},
                ensure_ascii=False,
            )
        room = getattr(getattr(self.session, "room_io", None), "room", None)
        room_name = getattr(room, "name", None)
        logger.info("handoff_create_started session=%s", self._session_data.app_session_id)
        try:
            record = await self._handoffs.create(self._session_data, reason=reason, room_name=room_name)
            self._session_data.handoff_requested = True
            self._session_data.handoff = HandoffState(
                handoff_id=str(record["handoff_id"]),
                status="pending",
                reason_code=str(record.get("reason_code") or "USER_REQUEST"),
                room_name=str(record.get("room_name") or room_name or "") or None,
            )
            self._session_data.record_failure(
                "HANDOFF_REQUIRED",
                "Yêu cầu đã được chuyển tới tổng đài viên.",
                retryable=False,
                fallback_action="handoff",
            )
            await self._state_store.save(self._session_data)
            await publish_booking_state(self.session)
            logger.info(
                "handoff_created session=%s handoff_id=%s status=pending",
                self._session_data.app_session_id,
                record["handoff_id"],
            )
            return json.dumps(
                {
                    "status": "pending",
                    "handoff_id": record["handoff_id"],
                    "instruction": "Đã tạo yêu cầu. Hãy báo khách chờ tổng đài viên nhận cuộc gọi.",
                },
                ensure_ascii=False,
            )
        except Exception:
            logger.exception("failed to create top-level human handoff session=%s", self._session_data.app_session_id)
            self._session_data.record_failure(
                "HANDOFF_REQUIRED",
                "Chưa thể tạo yêu cầu chuyển tổng đài viên.",
                retryable=True,
                fallback_action="retry",
            )
            await publish_booking_state(self.session)
            return json.dumps(
                {"status": "failed", "message": "Chưa thể tạo yêu cầu chuyển tổng đài viên."},
                ensure_ascii=False,
            )

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        if self._session_data is not None:
            await rewrite_livekit_user_turn(
                rewriter=self._transcript_rewriter,
                userdata=self._session_data,
                turn_ctx=turn_ctx,
                new_message=new_message,
            )

        # Stop this turn before the LLM can add a second AI reply after a handoff.
        current = self._session_data.handoff if self._session_data is not None else None
        if current is not None and current.status in {"pending", "accepted", "connected"}:
            raise StopResponse()

        # The parent sees the first booking utterance before BookingTask owns the
        # conversation. Seed every explicit slot now so one user turn produces
        # one coherent red/yellow/green state projection in the UI.
        userdata = self._session_data
        if userdata is not None and seed_complete_booking_turn(
            userdata.booking_draft,
            self._places,
            new_message.text_content or "",
        ):
            userdata.clear_failure()
            logger.info(
                "Parent booking turn seeded session=%s statuses=%s labels=%s",
                userdata.app_session_id,
                userdata.booking_draft.slot_statuses(),
                userdata.booking_draft.slot_labels(),
            )
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
        user_text = new_message.text_content or ""
        if self._safety_classifier.assess(user_text).is_emergency:
            safety_acknowledgement = self.session.say(
                self._safety_classifier.emergency_guidance(),
                allow_interruptions=False,
            )
            result = await self._create_handoff(user_text)
            if self._handoff_is_active(result):
                self._enter_handoff_wait(acknowledgement_handle=safety_acknowledgement)
            raise StopResponse()

    @function_tool()
    async def request_handoff(self, reason: str) -> str:
        """Tạo yêu cầu chuyển cuộc gọi tới tổng đài viên thật.

        Chỉ gọi khi khách yêu cầu rõ ràng gặp người thật, tổng đài viên, nhân
        viên hỗ trợ, operator hoặc yêu cầu chuyển máy. Đây là capability của
        AloSMAgent; BookingTask chỉ trả về needs_handoff để Supervisor xử lý.

        Không gọi cho câu hỏi mà tool khác có thể xử lý và không dùng để thay
        thế việc hỏi lại booking còn thiếu nếu khách chưa yêu cầu người thật.

        Args:
            reason: Lý do ngắn gọn, trung thực, có thể dùng nguyên văn yêu cầu
                của khách; không thêm suy đoán nhạy cảm.

        Returns:
            JSON chứa status và handoff_id khi tạo thành công, hoặc status
            failed nếu chưa thể tạo. Với status pending, hệ thống sẽ báo khách
            chờ tổng đài viên và AI không tiếp tục hội thoại đặt xe.
        """
        result = await self._create_handoff(reason)
        if self._handoff_is_active(result):
            self._enter_handoff_wait()
            raise StopResponse()
        return result

    @function_tool()
    async def cancel_booking(
        self,
        reason: str,
        confirmation_decision: Literal["request", "confirm", "decline"] = "request",
    ) -> str:
        """Yêu cầu xác nhận hoặc thực hiện hủy một chuyến đã được tạo.

        Chỉ dùng cho chuyến có booking_id trong cuộc gọi hiện tại. Không dùng
        để dừng booking draft chưa tạo chuyến; BookingTask sẽ trả về
        abandoned.

        Luồng gồm hai bước: lần đầu gọi với request để yêu cầu xác nhận; chỉ
        gọi lại với confirm sau khi khách xác nhận rõ ràng bằng lời nói hoặc
        nút trên giao diện. Nếu khách từ chối, dùng decline. Không gọi confirm
        cho câu hỏi về giá, đồng ý thông tin khác, “đúng rồi”, “ừ” hoặc quyết
        định hủy còn mơ hồ.

        Args:
            reason: Lý do hủy do khách cung cấp, viết ngắn gọn; không tự bịa.
            confirmation_decision: request để bắt đầu hoặc tiếp tục hỏi,
                confirm chỉ sau xác nhận hủy rõ ràng, hoặc decline khi khách từ
                chối.

        Returns:
            JSON chứa cancelled, confirmation_required, booking_id và
            instruction tiếp theo. Chỉ khi cancelled=true mới được nói chuyến
            đã hủy thành công.
        """

        if self._session_data is None or self._session_data.booking_draft.booking is None:
            return json.dumps(
                {"cancelled": False, "confirmation_required": False, "instruction": "Không có chuyến đã tạo để hủy."},
                ensure_ascii=False,
            )

        draft = self._session_data.booking_draft
        booking = draft.booking
        assert booking is not None
        if booking.status == "CANCELLED":
            return json.dumps(
                {
                    "cancelled": False,
                    "already_cancelled": True,
                    "booking_id": booking.booking_id,
                    "instruction": "Chuyến này đã được hủy trước đó.",
                },
                ensure_ascii=False,
            )

        pending = draft.cancellation_confirmation_booking_id == booking.booking_id
        if not pending:
            draft.request_cancellation_confirmation()
            await self._state_store.save(self._session_data)
            await publish_booking_state(self.session)
            return json.dumps(
                {
                    "cancelled": False,
                    "confirmation_required": True,
                    "booking_id": booking.booking_id,
                    "instruction": "Chưa hủy chuyến. Hãy hỏi khách xác nhận bằng lời nói hoặc nút xác nhận trên giao diện.",
                },
                ensure_ascii=False,
            )

        if confirmation_decision == "decline":
            draft.clear_cancellation_confirmation()
            await self._state_store.save(self._session_data)
            await publish_booking_state(self.session)
            return json.dumps(
                {
                    "cancelled": False,
                    "confirmation_required": False,
                    "booking_id": booking.booking_id,
                    "instruction": "Khách đã từ chối hủy; giữ nguyên chuyến.",
                },
                ensure_ascii=False,
            )

        if confirmation_decision != "confirm":
            return json.dumps(
                {
                    "cancelled": False,
                    "confirmation_required": True,
                    "booking_id": booking.booking_id,
                    "instruction": "Chưa có xác nhận hủy. Hãy tiếp tục hỏi hoặc chờ khách bấm nút xác nhận.",
                },
                ensure_ascii=False,
            )

        try:
            cancelled = await self._bookings.cancel(
                booking_id=booking.booking_id,
                user_id=self._session_data.user_id,
                app_session_id=self._session_data.app_session_id,
            )
        except Exception:
            logger.exception("failed to cancel booking id=%s", booking.booking_id)
            return json.dumps(
                {"cancelled": False, "booking_id": booking.booking_id, "instruction": "Hủy chuyến chưa thành công."},
                ensure_ascii=False,
            )
        if cancelled is None:
            return json.dumps(
                {
                    "cancelled": False,
                    "booking_id": booking.booking_id,
                    "instruction": "Không tìm thấy chuyến thuộc phiên này.",
                },
                ensure_ascii=False,
            )
        support = self._session_data.post_booking_support or PostBookingSupportState.for_booking(cancelled)
        support.request_restart()
        self._session_data.post_booking_support = support
        self._session_data.lifecycle_status = "cancelled"
        draft.mark_booking_cancelled(cancelled)
        await self._state_store.save(self._session_data)
        await publish_booking_state(self.session)
        return json.dumps(
            {
                "cancelled": True,
                "booking_id": cancelled.booking_id,
                "status": cancelled.status,
                "instruction": "Thông báo ngắn gọn rằng chuyến đã được hủy thành công.",
            },
            ensure_ascii=False,
        )

    def _active_post_booking_support(self) -> PostBookingSupportState | None:
        if self._session_data is None:
            return None
        booking = self._session_data.booking_draft.booking
        support = self._session_data.post_booking_support
        if booking is None or booking.status == "CANCELLED":
            return None
        if support is None:
            support = PostBookingSupportState.for_booking(booking)
            self._session_data.post_booking_support = support
        if support.booking_id != booking.booking_id:
            return None
        return support

    async def _save_and_publish_support(self) -> None:
        if self._session_data is None:
            return
        await self._state_store.save(self._session_data)
        await publish_booking_state(self.session)

    @function_tool()
    async def send_driver_request(self, request: str) -> str:
        """Mock việc chuyển một yêu cầu bổ sung cho tài xế của chuyến vừa đặt.

        Chỉ gọi sau khi khách đã chọn mục một và đã nói rõ nội dung yêu cầu.
        Không dùng câu menu, số thứ tự hoặc suy đoán làm nội dung. Dịch vụ demo
        chỉ ghi nhận yêu cầu trong state của phiên và trả biên nhận thành công.

        Args:
            request: Nội dung nguyên ý khách muốn gửi tài xế, ngắn gọn, tối đa
                240 ký tự; không thêm thông tin khách chưa nói.
        """
        support = self._active_post_booking_support()
        if support is None:
            return json.dumps(
                {"sent": False, "instruction": "Không có chuyến đang hoạt động để gửi yêu cầu."},
                ensure_ascii=False,
            )
        try:
            support.record_driver_request(request)
        except ValueError as exc:
            return json.dumps({"sent": False, "error": str(exc)}, ensure_ascii=False)
        await self._save_and_publish_support()
        return json.dumps(
            {
                "sent": True,
                "booking_id": support.booking_id,
                "request": support.last_driver_request,
                "instruction": "Xác nhận yêu cầu đã được gửi thành công cho tài xế, rồi hỏi khách có cần hỗ trợ thêm không.",
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def track_booking(self, minutes: int) -> str:
        """Mô phỏng hành trình tài xế sau số phút do khách lựa chọn.

        Chỉ gọi sau khi khách chọn mục hai và cung cấp số phút từ một đến ba
        mươi. Mỗi lần gọi giảm ETA và khoảng cách so với snapshot trước đó;
        tuyệt đối không tự tạo dữ liệu theo dõi ngoài kết quả tool.

        Args:
            minutes: Số phút khách muốn tua tiến hành trình mock, từ 1 đến 30.
        """
        support = self._active_post_booking_support()
        if support is None:
            return json.dumps(
                {"tracked": False, "instruction": "Không có chuyến đang hoạt động để theo dõi."},
                ensure_ascii=False,
            )
        try:
            support.advance_tracking(minutes)
        except ValueError as exc:
            return json.dumps({"tracked": False, "error": str(exc)}, ensure_ascii=False)
        await self._save_and_publish_support()
        arrived = support.eta_minutes == 0
        return json.dumps(
            {
                "tracked": True,
                "booking_id": support.booking_id,
                "elapsed_minutes": support.elapsed_minutes,
                "eta_minutes": support.eta_minutes,
                "distance_to_pickup_km": support.distance_to_pickup_km,
                "arrived": arrived,
                "instruction": (
                    "Thông báo tài xế đã đến điểm đón và hỏi khách có cần hỗ trợ thêm không."
                    if arrived
                    else "Đọc đúng ETA và khoảng cách còn lại, rồi hỏi khách có muốn theo dõi tiếp không."
                ),
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def finish_customer_service(self) -> str:
        """Kết thúc hỗ trợ hậu đặt xe và yêu cầu giao diện hiển thị đánh giá.

        Gọi khi khách nói không cần hỗ trợ thêm, muốn kết thúc hoặc dừng cuộc
        gọi sau khi đã đặt thành công. Tool không đăng xuất và không xóa tài
        khoản; nó chỉ phát trạng thái mở popup đánh giá.
        """
        support = self._active_post_booking_support()
        if support is None:
            return json.dumps(
                {"rating_requested": False, "instruction": "Không có chuyến hoàn tất để đánh giá."},
                ensure_ascii=False,
            )
        support.request_rating()
        await self._save_and_publish_support()
        return json.dumps(
            {
                "rating_requested": True,
                "booking_id": support.booking_id,
                "instruction": "Cảm ơn khách và nói rằng bảng đánh giá đang hiển thị trên màn hình.",
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def get_booking_status(self) -> str:
        """Đọc trạng thái booking chính thức của cuộc gọi hiện tại.

        Bắt buộc gọi tool này trước khi trả lời khách rằng chuyến đã được tạo,
        đã bị hủy, hoặc trước khi đọc booking_id. Chỉ dựa trên các trường trong
        kết quả tool; không suy đoán từ việc khách đã nhận báo giá, đã nói xác
        nhận, hoặc một tool khác đã chạy.

        Đây là tool chỉ đọc: không tạo chuyến, không hủy chuyến, không sửa
        booking draft và không tạo booking_id. Nếu booking_id là null, phải
        nói rõ rằng chuyến chưa được tạo. Nếu booking đã CANCELLED, không được
        nói chuyến đặt thành công.

        Returns:
            JSON chứa created, booking_id, booking_status,
            confirmation_status, handoff_status, summary và instruction. Làm
            theo instruction trong kết quả khi thông báo trạng thái cho khách.
        """
        if self._session_data is None:
            return json.dumps(
                {
                    "created": False,
                    "booking_id": None,
                    "instruction": "Không có trạng thái phiên; không được nói chuyến đã được tạo.",
                },
                ensure_ascii=False,
            )

        draft = self._session_data.booking_draft
        booking = draft.booking
        return json.dumps(
            {
                "created": booking is not None,
                "booking_id": booking.booking_id if booking else None,
                "booking_status": booking.status if booking else None,
                "confirmation_status": draft.confirmation_status,
                "handoff_status": self._session_data.handoff.status if self._session_data.handoff else None,
                "summary": draft.conversation_summary(),
                "instruction": (
                    "Thông báo chuyến đã được hủy; không được nói đặt thành công."
                    if booking is not None and booking.status == "CANCELLED"
                    else (
                        "Chỉ thông báo đặt thành công và đọc booking_id ở trên."
                        if booking is not None
                        else "Chuyến chưa được tạo; không được phát sinh hoặc suy đoán mã chuyến."
                    )
                ),
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def search_knowledge(self, query: str, top_k: int = 3) -> str:
        """Tra cứu chính sách và câu hỏi thường gặp đã được phê duyệt.

        Gọi khi khách hỏi về chính sách AloSM, hành lý, phụ phí, điều kiện sử
        dụng hoặc thông tin dịch vụ không gắn với một lộ trình cụ thể. Đây là
        tra cứu cục bộ, chỉ đọc, trên policy catalog có phiên bản. Chỉ trả lời
        dựa trên results mà tool cung cấp và nói rõ khi không có kết quả phù
        hợp.

        Không dùng tool này để tính giá hoặc ETA cho một lộ trình, kiểm tra
        trạng thái booking, trả lời dữ liệu thời gian thực, hoặc thay đổi
        booking state. Không tự bịa chính sách khi catalog không có kết quả.

        Args:
            query: Câu hỏi hoặc chủ đề chính sách cần tra cứu, viết ngắn gọn và
                giữ các điều kiện quan trọng mà khách đã nêu.
            top_k: Số kết quả tối đa cần lấy; truyền số nguyên từ 1 đến 3. Mặc
                định là 3 và không cần tăng quá giới hạn này.

        Returns:
            JSON chứa found, catalog_version, results với content, source,
            citation_id, score và effective_at, cùng instruction về cách trả
            lời. Chỉ đọc nội dung phù hợp trong results.
        """
        normalized_query = query.strip()
        if not normalized_query:
            return json.dumps(
                {"found": False, "results": [], "reason": "EMPTY_QUERY"},
                ensure_ascii=False,
            )
        bounded_top_k = max(1, min(int(top_k), 3))
        results = await self._knowledge_service.retrieve(normalized_query, top_k=bounded_top_k)
        catalog_version = self._knowledge_service.retriever.catalog.catalog_version
        return json.dumps(
            {
                "found": bool(results),
                "catalog_version": catalog_version,
                "results": [
                    {
                        "content": item["content"],
                        "source": item["source"],
                        "citation_id": item["citation_id"],
                        "score": item["score"],
                        "effective_at": (
                            item["effective_at"].isoformat()
                            if hasattr(item["effective_at"], "isoformat")
                            else item["effective_at"]
                        ),
                    }
                    for item in results
                ],
                "instruction": (
                    "Chỉ trả lời dựa trên results và nói rõ khi không có kết quả."
                    if results
                    else (
                        "Hãy nói rõ: Dạ, hiện tại tôi chưa tìm thấy thông tin chính sách đã được xác minh "
                        "cho yêu cầu này trong hệ thống. Nếu cần hỗ trợ thêm, hãy liên hệ tổng đài viên; "
                        "không được suy đoán hoặc tự tạo chính sách."
                    )
                ),
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def get_vehicle_options(self) -> str:
        """Liệt kê các loại xe và sức chứa hành lý trong pricing catalog.

        Gọi khi khách hỏi AloSM có những loại xe nào, mỗi loại chở được bao
        nhiêu người hoặc bao nhiêu hành lý. Đây là tra cứu catalog chỉ đọc; đọc
        tên hiển thị, sức chứa và hành lý từ kết quả, không tự bổ sung thông tin
        ngoài catalog.

        Tool này không tính giá cho lộ trình, không chọn hoặc cập nhật loại xe
        trong booking draft, không tạo booking và không thay thế
        BookingTask.estimate_fare. Khi khách muốn đặt hoặc đổi loại xe, tiếp
        tục quy trình đặt xe bằng start_booking.

        Returns:
            JSON chứa catalog_version, region, pricing_status, currency và
            options. Mỗi option có vehicle_type, display_name, capacity và
            luggage_capacity. Không đọc mã vehicle_type cho khách nếu không cần.
        """
        catalog = self._pricing_service.catalog
        return json.dumps(
            {
                "catalog_version": catalog.version,
                "region": catalog.region,
                "pricing_status": catalog.status,
                "currency": catalog.currency,
                "options": [
                    {
                        "vehicle_type": vehicle_type,
                        "display_name": vehicle.display_name,
                        "capacity": vehicle.capacity,
                        "luggage_capacity": vehicle.luggage_capacity,
                    }
                    for vehicle_type, vehicle in catalog.vehicles.items()
                ],
                "instruction": (
                    "Đọc display_name, sức chứa và hành lý; không đọc mã vehicle_type. "
                    "Muốn biết giá cho một lộ trình thì phải bắt đầu quy trình đặt xe."
                ),
            },
            ensure_ascii=False,
        )
