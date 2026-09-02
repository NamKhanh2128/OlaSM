"""Typed per-call business state for the LiveKit-native AloSM agent."""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from src.voice_agent.place_query_validator import is_valid_place_query

BookingTarget = Literal["pickup", "destination"]
BookingField = Literal["pickup", "destination", "vehicle_type"]
BookingSlotStatus = Literal["missing", "needs_clarification", "resolved"]
VehicleType = Literal["MOTORBIKE", "CAR_4", "CAR_7", "LUXURY"]
ConfirmationStatus = Literal["not_requested", "awaiting", "confirmed"]
PostBookingStage = Literal["menu", "driver_request_sent", "tracking", "rating_requested", "restart_requested"]
FailureCode = Literal[
    "ASR_LOW_CONFIDENCE",
    "STT_UNAVAILABLE",
    "LLM_UNAVAILABLE",
    "TTS_UNAVAILABLE",
    "PLACE_NOT_FOUND",
    "QUOTE_UNAVAILABLE",
    "BOOKING_RESULT_UNKNOWN",
    "SESSION_RECOVERY_FAILED",
    "STATE_CONFLICT",
    "HANDOFF_REQUIRED",
]
FallbackAction = Literal["repeat_or_text", "retry", "handoff", "none"]
SessionLifecycle = Literal["active", "completed", "cancelled"]

VEHICLE_TYPE_ORDER: tuple[VehicleType, ...] = (
    "MOTORBIKE",
    "CAR_4",
    "CAR_7",
    "LUXURY",
)

_VEHICLE_SPOKEN_LABELS: dict[VehicleType, str] = {
    "MOTORBIKE": "xe máy",
    "CAR_4": "xe ô tô bốn chỗ",
    "CAR_7": "xe ô tô bảy chỗ",
    "LUXURY": "xe cao cấp",
}
_VEHICLE_OPTION_DETAILS: dict[VehicleType, str] = {
    "MOTORBIKE": "Tối đa một hành khách",
    "CAR_4": "Tối đa bốn hành khách",
    "CAR_7": "Tối đa bảy hành khách",
    "LUXURY": "Dòng xe cao cấp",
}


def vehicle_spoken_label(vehicle_type: VehicleType | None) -> str | None:
    """Return a Vietnamese label suitable for TTS, never a domain enum."""

    return _VEHICLE_SPOKEN_LABELS.get(vehicle_type) if vehicle_type else None


def post_booking_menu_message(booking_id: str) -> str:
    """Return the single authoritative post-booking customer-service prompt."""

    return (
        f"Chuyến xe {booking_id} đã được đặt thành công. "
        "Tôi có thể hỗ trợ bạn: 1. Chuyển yêu cầu thêm cho tài xế, "
        "2. Theo dõi hành trình chuyến xe, "
        "3. Hủy chuyến xe và đặt lại chuyến mới. "
        "Bạn có cần tôi hỗ trợ gì thêm không hay kết thúc cuộc gọi ở đây?"
    )


class PlaceCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    place_id: str
    display_name: str
    address: str
    provider: str
    city: str | None = None


class QuoteSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    quote_id: str
    pickup_place_id: str
    destination_place_id: str
    vehicle_type: VehicleType
    fare_amount: int = Field(ge=0)
    currency: str = "VND"
    distance_km: float = Field(ge=0)
    eta_minutes: int = Field(ge=0)
    expires_at: str
    estimated: bool = True

    @property
    def fingerprint(self) -> str:
        raw = ":".join(
            (
                self.quote_id,
                self.pickup_place_id,
                self.destination_place_id,
                self.vehicle_type,
                str(self.fare_amount),
            )
        )
        return hashlib.sha256(raw.encode()).hexdigest()


class BookingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    booking_id: str
    status: str
    estimated_fare: int = Field(ge=0)
    currency: str = "VND"
    eta_minutes: int = Field(ge=0)


class VoiceFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: FailureCode
    message: str
    retryable: bool = True
    fallback_action: FallbackAction = "retry"


class HandoffState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    handoff_id: str
    status: Literal["pending", "accepted", "connected", "resolved", "failed"] = "pending"
    reason_code: str
    operator_id: str | None = None
    room_name: str | None = None


class PostBookingSupportState(BaseModel):
    """Durable, user-safe state for assistance after a booking is created."""

    model_config = ConfigDict(extra="forbid")

    booking_id: str
    stage: PostBookingStage = "menu"
    last_driver_request: str | None = Field(default=None, max_length=240)
    driver_request_count: int = Field(default=0, ge=0)
    eta_minutes: int = Field(ge=0)
    distance_to_pickup_km: float = Field(ge=0)
    elapsed_minutes: int = Field(default=0, ge=0)

    @classmethod
    def for_booking(cls, booking: BookingResult) -> PostBookingSupportState:
        return cls(
            booking_id=booking.booking_id,
            eta_minutes=booking.eta_minutes,
            distance_to_pickup_km=round(max(booking.eta_minutes * 0.35, 0.0), 1),
        )

    def record_driver_request(self, request: str) -> None:
        normalized = " ".join(request.split()).strip(" ,.!?;:")
        if not normalized:
            raise ValueError("DRIVER_REQUEST_REQUIRED")
        if len(normalized) > 240:
            raise ValueError("DRIVER_REQUEST_TOO_LONG")
        self.last_driver_request = normalized
        self.driver_request_count += 1
        self.stage = "driver_request_sent"

    def advance_tracking(self, minutes: int) -> None:
        if minutes < 1 or minutes > 30:
            raise ValueError("TRACKING_INTERVAL_OUT_OF_RANGE")
        elapsed = min(minutes, self.eta_minutes)
        self.eta_minutes = max(self.eta_minutes - elapsed, 0)
        self.distance_to_pickup_km = round(max(self.distance_to_pickup_km - elapsed * 0.35, 0.0), 1)
        self.elapsed_minutes += elapsed
        self.stage = "tracking"

    def request_rating(self) -> None:
        self.stage = "rating_requested"

    def request_restart(self) -> None:
        self.stage = "restart_requested"


class BookingDraft(BaseModel):
    """Mutable draft with deterministic dependent-field invalidation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    pickup_query: str | None = None
    pickup: PlaceCandidate | None = None
    pickup_candidates: list[PlaceCandidate] = Field(default_factory=list)
    destination_query: str | None = None
    destination: PlaceCandidate | None = None
    destination_candidates: list[PlaceCandidate] = Field(default_factory=list)
    pending_candidate_target: BookingTarget | None = None
    last_selected_candidate_target: BookingTarget | None = None
    last_selected_candidate_at: float | None = None
    pending_reselection_target: BookingTarget | None = None
    pending_reselection_place_id: str | None = None
    vehicle_query: str | None = None
    vehicle_type: VehicleType | None = None
    quote: QuoteSnapshot | None = None
    confirmation_status: ConfirmationStatus = "not_requested"
    confirmation_fingerprint: str | None = None
    cancellation_confirmation_booking_id: str | None = None
    booking: BookingResult | None = None
    revision: int = 0

    def _invalidate_quote_and_confirmation(self) -> None:
        self.quote = None
        self.confirmation_status = "not_requested"
        self.confirmation_fingerprint = None
        self.cancellation_confirmation_booking_id = None
        self.booking = None

    def _next_pending_candidate_target(self) -> BookingTarget | None:
        # A later candidate list must never skip an earlier unresolved slot.
        # Returning None when the first unresolved place has no candidates
        # makes the workflow ask for that value before accepting ordinals for a
        # destination list that may already have been prepared by a barge-in.
        if self.pickup is None:
            return "pickup" if self.pickup_candidates else None
        if self.destination is None:
            return "destination" if self.destination_candidates else None
        return None

    def _clear_pending_reselection(self) -> None:
        self.pending_reselection_target = None
        self.pending_reselection_place_id = None

    def set_candidates(
        self,
        target: BookingTarget,
        query: str,
        candidates: list[PlaceCandidate],
    ) -> None:
        if not is_valid_place_query(query):
            raise ValueError("PLACE_QUERY_INVALID")
        if target == "pickup":
            self.pickup_query = query
            self.pickup = None
            self.pickup_candidates = candidates
        else:
            self.destination_query = query
            self.destination = None
            self.destination_candidates = candidates
        self.pending_candidate_target = self._next_pending_candidate_target()
        self._invalidate_quote_and_confirmation()
        self._clear_pending_reselection()
        self.revision += 1

    def select_place(self, target: BookingTarget, place_id: str) -> PlaceCandidate:
        candidates = self.pickup_candidates if target == "pickup" else self.destination_candidates
        selected = next((candidate for candidate in candidates if candidate.place_id == place_id), None)
        if selected is None:
            raise ValueError("PLACE_CANDIDATE_NOT_IN_CURRENT_SEARCH")
        current = self.pickup if target == "pickup" else self.destination
        if current != selected:
            if target == "pickup":
                self.pickup = selected
            else:
                self.destination = selected
            self._invalidate_quote_and_confirmation()
            self.revision += 1
            self.last_selected_candidate_target = target
            self.last_selected_candidate_at = time.time()
            self._clear_pending_reselection()
        self.pending_candidate_target = self._next_pending_candidate_target()
        return selected

    def stage_candidate_reselection(self, target: BookingTarget, place_id: str) -> PlaceCandidate:
        """Hold one uncertain ordinal correction until the user confirms it."""

        candidates = self.pickup_candidates if target == "pickup" else self.destination_candidates
        selected = next((candidate for candidate in candidates if candidate.place_id == place_id), None)
        if selected is None:
            raise ValueError("PLACE_CANDIDATE_NOT_IN_CURRENT_SEARCH")
        self.pending_reselection_target = target
        self.pending_reselection_place_id = place_id
        self._invalidate_quote_and_confirmation()
        self.revision += 1
        return selected

    def confirm_candidate_reselection(self) -> tuple[BookingTarget, PlaceCandidate]:
        """Commit the candidate previously staged by an uncertain ordinal."""

        target = self.pending_reselection_target
        place_id = self.pending_reselection_place_id
        if target is None or place_id is None:
            raise ValueError("PLACE_RESELECTION_NOT_PENDING")
        return target, self.select_place(target, place_id)

    def reopen_candidate_selection(self, target: BookingTarget) -> None:
        """Return one selected place to clarification after an explicit mistake cue."""

        candidates = self.pickup_candidates if target == "pickup" else self.destination_candidates
        if not candidates:
            raise ValueError("PLACE_CANDIDATES_REQUIRED")
        if target == "pickup":
            self.pickup = None
        else:
            self.destination = None
        self.last_selected_candidate_target = target
        self.last_selected_candidate_at = time.time()
        self._clear_pending_reselection()
        self.pending_candidate_target = self._next_pending_candidate_target()
        self._invalidate_quote_and_confirmation()
        self.revision += 1

    def place_clarification(self, target: BookingTarget) -> dict[str, object] | None:
        """Return one target-owned candidate list without coupling it to the other slot."""

        candidates = self.pickup_candidates if target == "pickup" else self.destination_candidates
        selected = self.pickup if target == "pickup" else self.destination
        query = self.pickup_query if target == "pickup" else self.destination_query
        if not candidates:
            return None
        selected_index = next(
            (
                index
                for index, candidate in enumerate(candidates, start=1)
                if selected is not None and candidate.place_id == selected.place_id
            ),
            None,
        )
        fingerprint = hashlib.sha256("|".join(candidate.place_id for candidate in candidates).encode()).hexdigest()[:10]
        return {
            "clarification_id": f"{target}:{fingerprint}",
            "target": target,
            "query": query,
            "selected_index": selected_index,
            "options": [
                {
                    "index": index,
                    "display_name": candidate.display_name,
                    "subtitle": candidate.address,
                }
                for index, candidate in enumerate(candidates, start=1)
            ],
        }

    def pending_place_clarification(self) -> dict[str, object] | None:
        """Compatibility projection for clients that only understand one active list."""

        # Derive this projection instead of trusting persisted pointers from an
        # older worker version that allowed the most recently changed field to
        # jump the booking order.
        target = self._next_pending_candidate_target()
        return self.place_clarification(target) if target is not None else None

    def booking_clarifications(self) -> dict[str, object | None]:
        """Publish independent pickup, destination and vehicle choice objects."""

        vehicle_options: dict[str, object] | None = None
        if self.vehicle_type is None:
            vehicle_options = {
                "clarification_id": "vehicle_type:catalog-v1",
                "target": "vehicle_type",
                "query": self.vehicle_query,
                "selected_index": None,
                "options": [
                    {
                        "index": index,
                        "value": vehicle_type,
                        "display_name": _VEHICLE_SPOKEN_LABELS[vehicle_type].capitalize(),
                        "subtitle": _VEHICLE_OPTION_DETAILS[vehicle_type],
                    }
                    for index, vehicle_type in enumerate(VEHICLE_TYPE_ORDER, start=1)
                ],
            }
        return {
            "pickup": self.place_clarification("pickup"),
            "destination": self.place_clarification("destination"),
            "vehicle_type": vehicle_options,
        }

    def set_vehicle_type(self, vehicle_type: VehicleType) -> None:
        if self.vehicle_type != vehicle_type or self.vehicle_query is not None:
            self.vehicle_type = vehicle_type
            self.vehicle_query = None
            self.pending_candidate_target = self._next_pending_candidate_target()
            self._invalidate_quote_and_confirmation()
            self.revision += 1

    def mark_vehicle_needs_clarification(self, query: str) -> None:
        """Record a vehicle phrase that cannot yet map to one supported class."""

        normalized_query = " ".join(query.split())[:200]
        if not normalized_query:
            raise ValueError("VEHICLE_QUERY_REQUIRED")
        self.vehicle_query = normalized_query
        self.vehicle_type = None
        # A vehicle change cannot take ordinal ownership while pickup or
        # destination still needs clarification.
        self.pending_candidate_target = self._next_pending_candidate_target()
        self._invalidate_quote_and_confirmation()
        self.revision += 1

    def slot_status(self, field: BookingField) -> BookingSlotStatus:
        """Return the authoritative workflow/UI status for a required slot."""

        if field == "pickup":
            if self.pickup is not None:
                return "resolved"
            if self.pickup_query or self.pickup_candidates:
                return "needs_clarification"
            return "missing"
        if field == "destination":
            if self.destination is not None:
                return "resolved"
            if self.destination_query or self.destination_candidates:
                return "needs_clarification"
            return "missing"
        if self.vehicle_type is not None:
            return "resolved"
        if self.vehicle_query:
            return "needs_clarification"
        return "missing"

    def slot_statuses(self) -> dict[BookingField, BookingSlotStatus]:
        return {field: self.slot_status(field) for field in ("pickup", "destination", "vehicle_type")}

    def slot_labels(self) -> dict[BookingField, str | None]:
        """Expose the verified value or the user's unresolved phrase for each slot."""

        return {
            "pickup": self.pickup.display_name if self.pickup is not None else self.pickup_query,
            "destination": (self.destination.display_name if self.destination is not None else self.destination_query),
            "vehicle_type": vehicle_spoken_label(self.vehicle_type) or self.vehicle_query,
        }

    def next_required_field(self) -> BookingField | None:
        return next(
            (field for field in ("pickup", "destination", "vehicle_type") if self.slot_status(field) != "resolved"),
            None,
        )

    def all_required_slots_resolved(self) -> bool:
        return self.next_required_field() is None

    def set_quote(self, quote: QuoteSnapshot) -> None:
        if self.pickup is None or self.destination is None or self.vehicle_type is None:
            raise ValueError("BOOKING_CONTEXT_INCOMPLETE")
        expected = (self.pickup.place_id, self.destination.place_id, self.vehicle_type)
        actual = (quote.pickup_place_id, quote.destination_place_id, quote.vehicle_type)
        if actual != expected:
            raise ValueError("QUOTE_CONTEXT_MISMATCH")
        self.quote = quote
        self.confirmation_status = "not_requested"
        self.confirmation_fingerprint = None
        self.cancellation_confirmation_booking_id = None
        self.booking = None
        self.revision += 1

    def request_confirmation(self) -> None:
        if self.quote is None:
            raise ValueError("QUOTE_REQUIRED_BEFORE_CONFIRMATION")
        self.confirmation_status = "awaiting"
        self.confirmation_fingerprint = self.quote.fingerprint
        self.revision += 1

    def confirm(self) -> None:
        if self.quote is None or self.confirmation_status != "awaiting":
            raise ValueError("BOOKING_NOT_AWAITING_CONFIRMATION")
        if self.confirmation_fingerprint != self.quote.fingerprint:
            raise ValueError("BOOKING_CONTEXT_CHANGED")
        self.confirmation_status = "confirmed"
        self.revision += 1

    def quote_or_raise(self) -> QuoteSnapshot:
        if self.quote is None:
            raise ValueError("QUOTE_REQUIRED")
        return self.quote

    def require_creatable(self) -> QuoteSnapshot:
        quote = self.quote_or_raise()
        if self.confirmation_status != "confirmed":
            raise ValueError("EXPLICIT_CONFIRMATION_REQUIRED")
        if self.confirmation_fingerprint != quote.fingerprint:
            raise ValueError("BOOKING_CONTEXT_CHANGED")
        return quote

    def set_booking(self, booking: BookingResult) -> None:
        self.require_creatable()
        if self.booking is not None and self.booking.booking_id != booking.booking_id:
            raise ValueError("BOOKING_ALREADY_CREATED")
        self.booking = booking
        self.cancellation_confirmation_booking_id = None
        self.revision += 1

    def mark_booking_cancelled(self, booking: BookingResult) -> None:
        if self.booking is None or self.booking.booking_id != booking.booking_id:
            raise ValueError("BOOKING_NOT_FOUND_IN_DRAFT")
        if booking.status != "CANCELLED":
            raise ValueError("BOOKING_CANCEL_NOT_CONFIRMED")
        self.booking = booking
        self.cancellation_confirmation_booking_id = None
        self.revision += 1

    def request_cancellation_confirmation(self) -> None:
        if self.booking is None:
            raise ValueError("BOOKING_REQUIRED_BEFORE_CANCELLATION_CONFIRMATION")
        self.cancellation_confirmation_booking_id = self.booking.booking_id
        self.revision += 1

    def clear_cancellation_confirmation(self) -> None:
        if self.cancellation_confirmation_booking_id is not None:
            self.cancellation_confirmation_booking_id = None
            self.revision += 1

    def public_state(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "revision": self.revision,
            "pickup": self.pickup.model_dump() if self.pickup else None,
            "destination": self.destination.model_dump() if self.destination else None,
            "vehicle_type": self.vehicle_type,
            "quote": self.quote.model_dump() if self.quote else None,
            "confirmation_status": self.confirmation_status,
            "cancellation_confirmation_pending": self.cancellation_confirmation_booking_id is not None,
            "booking": self.booking.model_dump() if self.booking else None,
            "slot_statuses": self.slot_statuses(),
            "slot_labels": self.slot_labels(),
            "next_required_field": self.next_required_field(),
            "all_required_slots_resolved": self.all_required_slots_resolved(),
            "pending_place_clarification": self.pending_place_clarification(),
            "clarifications": self.booking_clarifications(),
        }

    def conversation_summary(self) -> str:
        """Return the minimum booking context needed by the conversational agent."""

        details: list[str] = []
        if self.pickup is not None:
            details.append(f"điểm đón {self.pickup.display_name}")
        elif self.pickup_query:
            details.append(f"điểm đón chưa xác nhận từ lời nói {self.pickup_query}")
        if self.destination is not None:
            details.append(f"điểm đến {self.destination.display_name}")
        elif self.destination_query:
            details.append(f"điểm đến chưa xác nhận từ lời nói {self.destination_query}")
        vehicle_label = vehicle_spoken_label(self.vehicle_type)
        if vehicle_label:
            details.append(f"loại xe {vehicle_label}")
        if self.booking is not None:
            if self.booking.status == "CANCELLED":
                details.append(f"chuyến mã {self.booking.booking_id} đã hủy")
            else:
                details.append(f"đã tạo chuyến mã {self.booking.booking_id}")
        elif self.confirmation_status == "confirmed":
            details.append("khách đã xác nhận và đang chờ tạo chuyến")
        elif self.confirmation_status == "awaiting":
            details.append("đang chờ khách xác nhận đặt chuyến")
        elif self.quote is not None:
            details.append("đã có báo giá nhưng chưa yêu cầu xác nhận")

        return "; ".join(details) if details else "chưa có thông tin đặt xe"


class AloSMSessionData(BaseModel):
    """Business userdata owned by one LiveKit ``AgentSession``."""

    model_config = ConfigDict(extra="forbid")

    app_session_id: str
    call_id: str
    user_id: str
    participant_identity: str
    consent_granted: bool = True
    recording_enabled: bool = False
    booking_draft: BookingDraft = Field(default_factory=BookingDraft)
    last_asr_confidence: float | None = None
    handoff_requested: bool = False
    critical_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    persistence_revision: int = Field(default=0, ge=0)
    persistence_enabled: bool = True
    recovered: bool = False
    last_failure: VoiceFailure | None = None
    handoff: HandoffState | None = None
    lifecycle_status: SessionLifecycle = "active"
    post_booking_support: PostBookingSupportState | None = None

    _transcript_rewrite_lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _transcript_rewrite_tasks: dict[str, asyncio.Task[object]] = PrivateAttr(default_factory=dict)

    @property
    def transcript_rewrite_lock(self) -> asyncio.Lock:
        """Coordinate rewrite task creation and finalized-message updates."""

        return self._transcript_rewrite_lock

    @property
    def transcript_rewrite_tasks(self) -> dict[str, asyncio.Task[object]]:
        """Return the per-item rewrite barriers owned by this call session."""

        return self._transcript_rewrite_tasks

    def remember_transcript_rewrite_task(
        self,
        item_id: str,
        task: asyncio.Task[object],
        *,
        limit: int = 128,
    ) -> None:
        """Retain a bounded barrier so duplicate hooks join one rewrite result."""

        self._transcript_rewrite_tasks[item_id] = task
        while len(self._transcript_rewrite_tasks) > max(limit, 1):
            self._transcript_rewrite_tasks.pop(next(iter(self._transcript_rewrite_tasks)))

    def durable_state(self) -> dict[str, object]:
        """Return only resumable business state; never transcript or raw audio."""

        return {
            "schema_version": "1",
            "booking_draft": self.booking_draft.model_dump(mode="json"),
            "last_failure": (self.last_failure.model_dump(mode="json") if self.last_failure else None),
            "handoff": self.handoff.model_dump(mode="json") if self.handoff else None,
            "lifecycle_status": self.lifecycle_status,
            "post_booking_support": (
                self.post_booking_support.model_dump(mode="json") if self.post_booking_support else None
            ),
        }

    def restore(self, state: dict[str, object], revision: int) -> None:
        if state.get("schema_version") != "1":
            raise ValueError("VOICE_STATE_SCHEMA_UNSUPPORTED")
        self.booking_draft = BookingDraft.model_validate(state.get("booking_draft") or {})
        self.last_failure = VoiceFailure.model_validate(state["last_failure"]) if state.get("last_failure") else None
        self.handoff = HandoffState.model_validate(state["handoff"]) if state.get("handoff") else None
        self.handoff_requested = self.handoff is not None
        lifecycle = state.get("lifecycle_status") or "active"
        if lifecycle not in {"active", "completed", "cancelled"}:
            raise ValueError("VOICE_SESSION_LIFECYCLE_UNSUPPORTED")
        self.lifecycle_status = lifecycle
        self.post_booking_support = (
            PostBookingSupportState.model_validate(state["post_booking_support"])
            if state.get("post_booking_support") else None
        )
        self.persistence_revision = revision
        self.recovered = True

    def record_failure(
        self,
        code: FailureCode,
        message: str,
        *,
        retryable: bool = True,
        fallback_action: FallbackAction = "retry",
    ) -> None:
        self.last_failure = VoiceFailure(
            code=code,
            message=message,
            retryable=retryable,
            fallback_action=fallback_action,
        )

    def clear_failure(self) -> None:
        self.last_failure = None

    def public_state(self) -> dict[str, object]:
        return {
            **self.booking_draft.public_state(),
            "failure": self.last_failure.model_dump(mode="json") if self.last_failure else None,
            "handoff": self.handoff.model_dump(mode="json") if self.handoff else None,
            "recovered": self.recovered,
            "post_booking_support": (
                self.post_booking_support.model_dump(mode="json") if self.post_booking_support else None
            ),
        }
