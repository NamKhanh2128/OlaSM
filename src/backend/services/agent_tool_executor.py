from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from src.agents.schemas import ToolCall, ToolName, ToolResult, ToolStatus
from src.agents.state import AgentState
from src.backend.config import get_settings
from src.backend.services.booking_service import BookingService
from src.backend.services.confidence_fusion_service import (
    ConfidenceFusionService,
    MultimodalConfidenceInputs,
)
from src.backend.services.knowledge_service import KnowledgeService
from src.backend.services.offer_engine import BookingContext, OfferEngine, Promotion
from src.backend.services.offer_profile_service import OfferProfileService, UserOfferProfile
from src.backend.services.place_search_service import PlaceSearchService
from src.backend.services.pricing_service import PricingService
from src.backend.services.quote_service import QuoteService
from src.backend.services.trip_service import TripService
from src.backend.services.visual_grounding_service import VisualGroundingService

logger = logging.getLogger(__name__)


class AgentToolExecutor:
    """Thực thi các tool mà Core Agent (nhánh feature/agentic-ai) gọi tới — xem
    src/agents/docs/BACKEND_INTEGRATION.md §6 (bảng tool_name -> backend integration).
    Mỗi nhánh dưới đây gọi 1 service thật (PlaceSearchService/PricingService/
    BookingService/TripService/KnowledgeService), không còn trả dữ liệu hardcode như
    bản MVP trước (giá cước cố định 85.000đ mọi chuyến, FAQ luôn 2 câu giống nhau,
    trạng thái chuyến luôn "Đang đến điểm đón")."""

    def __init__(
        self,
        place_search: PlaceSearchService | None = None,
        pricing: PricingService | None = None,
        booking_service: BookingService | None = None,
        trip_service: TripService | None = None,
        knowledge_service: KnowledgeService | None = None,
        offer_profile_service: OfferProfileService | None = None,
        offer_engine: OfferEngine | None = None,
        confidence_fusion_service: ConfidenceFusionService | None = None,
        visual_grounding_service: VisualGroundingService | None = None,
    ) -> None:
        self._place_search = place_search or PlaceSearchService()
        self._pricing = pricing or PricingService()
        self._quotes = QuoteService(pricing=self._pricing)
        self._durable = get_settings().app_env != "test"
        self._booking_service = booking_service or BookingService()
        self._trip_service = trip_service or TripService()
        self._knowledge_service = knowledge_service or KnowledgeService()
        self._offer_profile_svc = offer_profile_service or OfferProfileService()
        self._offer_engine = offer_engine or OfferEngine()
        self._confidence_fusion = confidence_fusion_service or ConfidenceFusionService()
        self._visual_grounding = visual_grounding_service or VisualGroundingService()

    async def execute(
        self,
        tool_call: ToolCall,
        *,
        session_id: str,
        user_id: str | None,
        agent_state: AgentState,
    ) -> ToolResult:
        try:
            data = await self._dispatch(tool_call, session_id=session_id, user_id=user_id, agent_state=agent_state)
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolStatus.SUCCESS,
                data=data,
            )
        except Exception as exc:
            logger.warning("Tool %s failed for session %s: %s", tool_call.tool_name, session_id, exc)
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolStatus.ERROR,
                data={},
                error=str(exc)[:500],
                error_code="EXECUTOR_ERROR",
                retryable=True,
            )

    async def _dispatch(
        self,
        tool_call: ToolCall,
        *,
        session_id: str,
        user_id: str | None,
        agent_state: AgentState,
    ) -> dict[str, object]:
        params = tool_call.params

        if tool_call.tool_name is ToolName.SEARCH_PLACE:
            query = str(params["query"])
            return {"candidates": self._place_search.search(query)}

        if tool_call.tool_name is ToolName.GET_VEHICLE_OPTIONS:
            if user_id is None:
                raise ValueError("AUTHENTICATED_USER_REQUIRED_FOR_QUOTE")
            return {
                "options": await self._quotes.vehicle_options(
                    user_id=user_id,
                    session_id=session_id,
                    pickup_place_id=str(params["pickup_place_id"]),
                    destination_place_id=str(params["destination_place_id"]),
                    passenger_count=int(params["passenger_count"]),
                    luggage_count=params.get("luggage_count"),
                )
            }

        if tool_call.tool_name is ToolName.ESTIMATE_FARE:
            if user_id is None:
                raise ValueError("AUTHENTICATED_USER_REQUIRED_FOR_QUOTE")
            return await self._quotes.issue_quote(
                user_id=user_id,
                session_id=session_id,
                pickup_place_id=str(params["pickup_place_id"]),
                destination_place_id=str(params["destination_place_id"]),
                vehicle_type=str(params["vehicle_type"]),
            )

        if tool_call.tool_name is ToolName.CREATE_BOOKING:
            return await self._create_booking(params, session_id=session_id, user_id=user_id, agent_state=agent_state)

        if tool_call.tool_name is ToolName.CANCEL_BOOKING:
            booking_id = str(params["booking_id"])
            cancelled = (
                self._booking_service.cancel_booking(booking_id, str(params["idempotency_key"]))
                if not self._durable
                else await self._booking_service.cancel_booking_durable(
                    booking_id, str(params["idempotency_key"]), user_id
                )
            )
            if cancelled is None:
                raise ValueError(f"Không tìm thấy booking để huỷ: {booking_id}")
            return {"booking_id": booking_id, "status": str(cancelled["status"])}

        if tool_call.tool_name is ToolName.LOOKUP_TRIP:
            return await self._lookup_trip(params, user_id=user_id)

        if tool_call.tool_name is ToolName.RETRIEVE_KNOWLEDGE:
            query = str(params["query"])
            documents = await self._knowledge_service.retrieve(query)
            return {"documents": documents}

        if tool_call.tool_name is ToolName.CREATE_HANDOFF:
            reason = str(params.get("reason", ""))
            reason_code = str(params.get("reason_code", "UNABLE_TO_CONTINUE"))
            logger.info("Handoff requested for session %s: %s (code=%s)", session_id, reason, reason_code)

            # Đóng gói ngữ cảnh bàn giao < 0.5s theo chuẩn GSM Mobility Assistant (Báo cáo Mục 3, 4.3, 6)
            b = agent_state.collected_data.booking if agent_state and agent_state.collected_data else None
            context_summary = {
                "session_id": session_id,
                "reason": reason,
                "reason_code": reason_code,
                "pickup": b.pickup.display_name if b and b.pickup else None,
                "destination": b.destination.display_name if b and b.destination else None,
                "vehicle_type": b.vehicle_type if b else None,
                "estimated_fare": b.estimated_fare_amount if b else None,
                "c_trip": b.c_trip if b else None,
                "autonomy_decision": b.autonomy_decision if b else None,
                "s_offer": b.s_offer if b else None,
                "applied_promotion": b.promotion_code if b else None,
                "visual_grounding": b.visual_grounding_result if b else None,
            }
            return {
                "handoff_id": f"handoff_{uuid4().hex[:8]}",
                "status": "pending",
                "context_snapshot": context_summary,
                "handover_sla_seconds": 0.5,
            }

        if tool_call.tool_name is ToolName.GET_PERSONALIZED_OFFER:
            return await self._get_personalized_offer(
                params,
                session_id=session_id,
                user_id=user_id,
                agent_state=agent_state,
            )

        if tool_call.tool_name is ToolName.GROUND_PICKUP_IMAGE:
            return await self._ground_pickup_image(
                params,
                session_id=session_id,
                agent_state=agent_state,
            )

        if tool_call.tool_name is ToolName.EVALUATE_TRIP_CONFIDENCE:
            return await self._evaluate_trip_confidence(
                params,
                session_id=session_id,
                agent_state=agent_state,
            )

        raise ValueError(f"Unsupported tool: {tool_call.tool_name}")

    async def _create_booking(
        self,
        params: dict[str, object],
        *,
        session_id: str,
        user_id: str | None,
        agent_state: AgentState,
    ) -> dict[str, object]:
        if user_id is None:
            raise ValueError("AUTHENTICATED_USER_REQUIRED_FOR_BOOKING")
        if not self._durable:
            vehicle_type = str(params["vehicle_type"])
            fare = self._pricing.estimate_fare(
                pickup_place_id=str(params["pickup_place_id"]),
                destination_place_id=str(params["destination_place_id"]),
                vehicle_type=vehicle_type,
            )
            if str(params["fare_estimate_id"]) != str(fare["estimate_id"]):
                raise ValueError("Fare estimate does not match the confirmed route and vehicle")
            result = self._booking_service.create_booking(
                {
                    "idempotency_key": params["idempotency_key"],
                    "estimated_fare": fare["fare_amount"],
                    "user_id": user_id,
                    "pickup": None,
                    "destination": None,
                    "vehicle_type": vehicle_type,
                }
            )
            return {
                "booking_id": str(result["booking_id"]),
                "status": "CONFIRMED",
                "eta_minutes": fare.get("eta_minutes"),
                "fare_amount": result.get("estimated_fare"),
                "currency": "VND",
            }
        booking_state = agent_state.collected_data.get("booking", {})
        pickup = booking_state.get("pickup") if isinstance(booking_state, dict) else None
        destination = booking_state.get("destination") if isinstance(booking_state, dict) else None
        booking = await self._booking_service.create_booking_from_quote(
            {
                "quote_id": params["fare_estimate_id"],
                "fare_estimate_id": params["fare_estimate_id"],
                "idempotency_key": params["idempotency_key"],
                "session_id": session_id,
                "user_id": user_id,
                "pickup_place_id": params["pickup_place_id"],
                "destination_place_id": params["destination_place_id"],
                "vehicle_type": params["vehicle_type"],
                "pickup": pickup,
                "destination": destination,
            }
        )
        return {
            "booking_id": str(booking["booking_id"]),
            "status": str(booking["status"]),
            "eta_minutes": booking.get("eta_minutes"),
            "fare_amount": booking.get("quoted_fare_amount"),
            "currency": booking.get("currency", "VND"),
            "quote_id": booking.get("quote_id"),
        }

    async def _lookup_trip(self, params: dict[str, object], *, user_id: str | None) -> dict[str, object]:
        booking_id = params.get("booking_id")
        if booking_id:
            booking = (
                self._booking_service.get_booking(str(booking_id))
                if not self._durable
                else await self._booking_service.get_booking_durable(str(booking_id))
            )
            if booking is None or (user_id is not None and booking.get("user_id") != user_id):
                return {"found": False}
            live = (
                self._trip_service.get_status_for_booking(str(booking_id))
                if not self._durable
                else await self._trip_service.get_status_for_booking_durable(str(booking_id))
            )
            return {
                "found": True,
                "booking_id": str(booking_id),
                "status": str(live["status"]),
                "eta_minutes": live.get("eta_minutes"),
            }

        phone_number = params.get("phone_number")
        if phone_number:
            if self._durable and user_id is not None:
                all_bookings = await self._booking_service.list_bookings_for_user_durable(user_id)
                matches = [item for item in all_bookings if item.get("status") not in {"CANCELLED", "COMPLETED"}][:5]
            else:
                matches = self._booking_service.find_active_bookings_for_phone(str(phone_number))
            if not matches:
                return {"found": False}
            trips = []
            for booking in matches:
                live = (
                    self._trip_service.get_status_for_booking(str(booking["booking_id"]))
                    if not self._durable
                    else await self._trip_service.get_status_for_booking_durable(str(booking["booking_id"]))
                )
                pickup = booking.get("pickup")
                destination = booking.get("destination")
                trips.append(
                    {
                        "booking_id": str(booking["booking_id"]),
                        "status": str(live["status"]),
                        "eta_minutes": live.get("eta_minutes"),
                        "pickup_label": pickup.get("display_name") if isinstance(pickup, dict) else None,
                        "destination_label": destination.get("display_name") if isinstance(destination, dict) else None,
                    }
                )
            return {"found": True, "trips": trips}

        return {"found": False}

    async def _get_personalized_offer(
        self,
        params: dict[str, object],
        *,
        session_id: str,
        user_id: str | None,
        agent_state: AgentState,
    ) -> dict[str, object]:
        """Đánh giá và trả về best offer cho booking hiện tại.

        Quy trình:
        1. Load UserOfferProfile từ DB (hoặc cold-start nếu user mới)
        2. Build BookingContext từ agent_state + params
        3. Load active promotions từ DB (hoặc demo seed)
        4. Chạy OfferEngine.evaluate()
        5. Trả JSON: {"offer": <BestOffer dict> | null}

        Cold-start user (total_rides=0) → c_offer < 0.20 → {"offer": null}
        → Agent không mention offer → tránh lãng phí budget.
        """
        if user_id is None:
            return {"offer": None, "reason": "UNAUTHENTICATED"}

        # ── 1. Load / build profile ─────────────────────────────────────────
        profile = self._load_offer_profile(user_id)

        # ── 2. Build BookingContext ─────────────────────────────────────────
        booking_state = agent_state.collected_data.get("booking", {}) if agent_state else {}
        if not isinstance(booking_state, dict):
            booking_state = {}

        fare_estimate_id = str(params.get("fare_estimate_id", ""))
        vehicle_type = str(params.get("vehicle_type", ""))

        # Lấy estimated_fare từ booking state
        estimated_fare_vnd = int(booking_state.get("estimated_fare_amount") or 0)

        # Route hash: dùng để detect "new route" incentive
        pickup = booking_state.get("pickup") or {}
        destination = booking_state.get("destination") or {}
        pickup_place_id = pickup.get("place_id", "") if isinstance(pickup, dict) else ""
        destination_place_id = destination.get("place_id", "") if isinstance(destination, dict) else ""
        import hashlib as _hashlib
        route_hash = _hashlib.sha256(
            f"{pickup_place_id}:{destination_place_id}".encode()
        ).hexdigest()[:16]

        now = datetime.now(UTC)
        # Convert to Vietnam time (UTC+7) for hour_of_day
        hour_of_day = (now.hour + 7) % 24
        day_of_week = now.weekday()  # 0=Monday

        context = BookingContext(
            user_id=user_id,
            session_id=session_id,
            vehicle_type=vehicle_type,
            estimated_fare_vnd=estimated_fare_vnd,
            pickup_zone=pickup.get("zone_id") if isinstance(pickup, dict) else None,
            destination_zone=destination.get("zone_id") if isinstance(destination, dict) else None,
            route_hash=route_hash,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
        )

        # ── 3. Load active promotions ───────────────────────────────────────
        promotions = self._load_active_promotions(user_id=user_id)

        # ── 4. Evaluate ─────────────────────────────────────────────────────
        best = self._offer_engine.evaluate(profile, context, promotions)

        if best is None:
            logger.info("offer.none user=%s session=%s", user_id, session_id)
            return {"offer": None}

        logger.info(
            "offer.returned user=%s promo=%s tier=%s score=%.4f discount=%d",
            user_id,
            best.promotion_code,
            best.offer_tier,
            best.c_offer,
            best.discount_amount_vnd,
        )
        score_val = best.s_offer or best.c_offer
        return {
            "offer": {
                "promotion_id": best.promotion_id,
                "promotion_code": best.promotion_code,
                "title": best.title,
                "offer_tier": best.offer_tier,
                "s_offer": score_val,
                "c_offer": score_val,
                "alpha": best.alpha,
                "beta": best.beta,
                "gamma": best.gamma,
                "discount_type": best.discount_type,
                "discount_value": best.discount_value,
                "discount_amount_vnd": best.discount_amount_vnd,
                "final_fare_vnd": best.final_fare_vnd,
                "max_discount_vnd": best.max_discount_vnd,
                "speech_suggestion": best.speech_suggestion,
                "allocation_hash": best.allocation_hash,
                "snapshot": best.to_snapshot(),
            }
        }

    async def _ground_pickup_image(
        self,
        params: dict[str, object],
        *,
        session_id: str,
        agent_state: AgentState,
    ) -> dict[str, object]:
        """Phân tích ảnh điểm đón bằng Multimodal VLM + Spatial OCR (Báo cáo Mục 1, 4.1)."""
        image_url = str(params["image_url"]) if "image_url" in params else None
        image_base64 = str(params["image_base64"]) if "image_base64" in params else None
        text_hint = str(params.get("text_hint") or "")

        result = self._visual_grounding.ground_image(
            image_url=image_url,
            image_base64=image_base64,
            text_hint=text_hint,
        )
        return result.to_dict()

    async def _evaluate_trip_confidence(
        self,
        params: dict[str, object],
        *,
        session_id: str,
        agent_state: AgentState,
    ) -> dict[str, object]:
        """Tính Dynamic Confidence Fusion c_trip và định tuyến Selective Autonomy (Báo cáo Mục 4.3)."""
        p_stt = float(params.get("p_stt", 0.90))
        p_intent = float(params.get("p_intent", 0.95))
        p_addr = float(params.get("p_addr", 0.90))
        p_vision = float(params["p_vision"]) if params.get("p_vision") is not None else None

        inputs = MultimodalConfidenceInputs(
            p_stt=p_stt,
            p_intent=p_intent,
            p_addr=p_addr,
            p_vision=p_vision,
        )
        result = self._confidence_fusion.evaluate(inputs)
        return result.to_dict()

    def _load_offer_profile(self, user_id: str) -> UserOfferProfile:
        """Load behavioral profile từ DB; trả cold-start profile nếu chưa có.

        TODO (Week 3): Thay bằng repository call thật khi bảng user_offer_profiles
        đã được migrate và worker đã populate.
        """
        # Demo: tất cả user đều cold-start → OfferEngine tự quyết dựa trên c_offer
        profile = self._offer_profile_svc.build_cold_start_profile(user_id)
        return profile

    def _load_active_promotions(self, *, user_id: str) -> list[Promotion]:
        """Load promotions active từ DB.

        TODO (Week 2): Thay bằng repository call thật khi bảng promotions
        đã được migrate và seeded.

        Hiện tại trả demo seed với 3 loại promotion để test end-to-end flow.
        """
        from datetime import timedelta

        now = datetime.now(UTC)
        return [
            # P1: STANDARD offer cho giờ cao điểm — chỉ active nếu profile đủ score
            Promotion(
                id="promo_demo_peak",
                code="PEAK20K",
                title="Ưu đãi giờ cao điểm",
                discount_type="FIXED_VND",
                discount_value=20_000,
                max_discount_vnd=None,
                min_fare_vnd=30_000,
                target_tiers=None,           # Mọi tier
                valid_vehicle_types=["CAR_4", "CAR_7"],
                valid_hours=[7, 8, 17, 18, 19, 20],
                valid_zones=None,
                new_route_only=False,
                campaign_priority=60,
                remaining_budget_vnd=5_000_000,
                usage_per_user=3,
                current_user_usage=0,
            ),
            # P2: PREMIUM offer cho churn-risk user — discount lớn hơn
            Promotion(
                id="promo_demo_retention",
                code="BACKLẠI30",
                title="Chào mừng bạn quay lại",
                discount_type="PERCENT",
                discount_value=15,           # 15%
                max_discount_vnd=30_000,
                min_fare_vnd=20_000,
                target_tiers=None,
                valid_vehicle_types=None,
                valid_hours=None,
                valid_zones=None,
                new_route_only=False,
                campaign_priority=85,        # Cao → premium candidate
                remaining_budget_vnd=10_000_000,
                usage_per_user=1,
                current_user_usage=0,
            ),
            # P3: SUGGEST offer cho tuyến mới
            Promotion(
                id="promo_demo_newroute",
                code="TUYENMOI10",
                title="Khám phá tuyến mới",
                discount_type="FIXED_VND",
                discount_value=10_000,
                max_discount_vnd=None,
                min_fare_vnd=25_000,
                target_tiers=None,
                valid_vehicle_types=None,
                valid_hours=None,
                valid_zones=None,
                new_route_only=True,         # Chỉ dùng cho tuyến chưa đi
                campaign_priority=40,
                remaining_budget_vnd=3_000_000,
                usage_per_user=2,
                current_user_usage=0,
            ),
        ]
