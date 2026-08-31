"""Privacy projection for handoff records exposed to operators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_SAFE_PLACE_PROVIDERS = frozenset(
    {
        "local_gazetteer",
        "local_gazetteer_fuzzy",
        "local_landmark_mock",
        "local_landmark_mock_exact",
        "test",
    }
)
_SAFE_REASON_LABELS = {
    "EMERGENCY": "Yêu cầu hỗ trợ khẩn cấp",
    "USER_REQUEST": "Khách yêu cầu gặp tổng đài viên",
    "ACTIVE_TRIP_NO_SHOW": "Sự cố chuyến đang hoạt động",
    "PAYMENT_DISPUTE": "Vấn đề thanh toán",
    "LOW_CONFIDENCE": "Nhận diện giọng nói không rõ",
    "PROVIDER_FAILURE": "Lỗi nhà cung cấp",
    "UNABLE_TO_CONTINUE": "Yêu cầu cần tổng đài viên hỗ trợ",
    "SAFETY_RISK": "Rủi ro an toàn",
    "COMPLAINT": "Khiếu nại của khách hàng",
    "LOST_ITEM": "Sự cố thất lạc đồ",
    "LOW_STT_CONFIDENCE": "Nhận diện giọng nói không rõ",
    "RETRY_LIMIT": "Quá số lần thử",
    "CRITICAL_TOOL_ERROR": "Lỗi xử lý yêu cầu",
    "SIDE_EFFECT_RECONCILIATION": "Cần đối soát thao tác",
    "MODEL_UNAVAILABLE": "Dịch vụ AI tạm thời không khả dụng",
    "POLICY_BLOCK": "Yêu cầu bị chặn theo chính sách",
    "PRIVACY_REQUEST": "Yêu cầu về quyền riêng tư",
    "LEGAL_REQUEST": "Yêu cầu hỗ trợ pháp lý",
}
_SAFE_REASON_CODES = frozenset(_SAFE_REASON_LABELS)
_SAFE_SEVERITIES = frozenset({"NORMAL", "HIGH", "CRITICAL"})
_SAFE_QUEUES = frozenset(
    {
        "GENERAL_OPERATOR",
        "SAFETY_OPERATOR",
        "SPECIALIST_OPERATOR",
        "PRIVACY_OPERATOR",
        "CUSTOMER_CARE_OPERATOR",
        "OPERATIONS_OPERATOR",
    }
)
_SAFE_PENDING_ACTIONS = frozenset({"CONTINUE_BOOKING"})
_SAFE_STATUSES = frozenset({"pending", "accepted", "connected", "resolved", "failed"})
_SAFE_VEHICLES = frozenset({"MOTORBIKE", "CAR_4", "CAR_7", "LUXURY"})
_SAFE_CONFIRMATION_STATUSES = frozenset({"not_requested", "awaiting", "confirmed"})
_SAFE_FAILURE_CODES = frozenset(
    {
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
    }
)
_SAFE_FALLBACK_ACTIONS = frozenset({"repeat_or_text", "retry", "handoff", "none"})
_SAFE_PAYLOAD_KEYS = frozenset(
    {
        "session_id",
        "pending_action",
        "priority",
        "severity",
        "queue",
        "requires_immediate_transfer",
        "room_name",
    }
)
_SAFE_RECORD_KEYS = _SAFE_PAYLOAD_KEYS | {
    "handoff_id",
    "status",
    "created_at",
    "accepted_at",
    "connected_at",
    "resolved_at",
    "operator_id",
}


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_choice(value: object, allowed: frozenset[str], default: str | None) -> str | None:
    return value if isinstance(value, str) and value in allowed else default


def _safe_reason_code(value: object) -> str:
    code = str(value or "UNABLE_TO_CONTINUE")
    return code if code in _SAFE_REASON_CODES else "UNABLE_TO_CONTINUE"


def _safe_place(value: object) -> dict[str, str] | None:
    raw = _mapping(value)
    if raw is None:
        return None

    provider_value = raw.get("provider")
    provider = provider_value.strip() if isinstance(provider_value, str) and provider_value.strip() else "unknown"
    place_id = raw.get("place_id")
    if not isinstance(place_id, str) or not place_id.strip():
        return None

    display_value = raw.get("display_name")
    if provider in _SAFE_PLACE_PROVIDERS and isinstance(display_value, str) and display_value.strip():
        display_name = display_value.strip()
    else:
        display_name = "Địa điểm đã xác nhận"

    return {
        "place_id": place_id,
        "display_name": display_name,
        "provider": provider if provider in _SAFE_PLACE_PROVIDERS else "external",
    }


def _safe_quote(value: object) -> dict[str, Any] | None:
    raw = _mapping(value)
    if raw is None:
        return None

    quote_id = raw.get("quote_id")
    if not isinstance(quote_id, str) or not quote_id.strip():
        return None

    return {
        "quote_id": quote_id,
        "fare_amount": max(0, _safe_int(raw.get("fare_amount"))),
        "currency": str(raw.get("currency") or "VND"),
        "distance_km": max(0.0, _safe_float(raw.get("distance_km"))),
        "eta_minutes": max(0, _safe_int(raw.get("eta_minutes"))),
        "estimated": bool(raw.get("estimated", True)),
    }


def _safe_booking(value: object) -> dict[str, Any] | None:
    raw = _mapping(value)
    if raw is None:
        return None

    booking_id = raw.get("booking_id")
    if not isinstance(booking_id, str) or not booking_id.strip():
        return None

    return {
        "booking_id": booking_id,
        "status": str(raw.get("status") or "UNKNOWN"),
        "estimated_fare": max(0, _safe_int(raw.get("estimated_fare"))),
        "currency": str(raw.get("currency") or "VND"),
        "eta_minutes": max(0, _safe_int(raw.get("eta_minutes"))),
    }


def _safe_failure(value: object) -> dict[str, Any] | None:
    raw = _mapping(value)
    if raw is None:
        return None

    code_value = raw.get("code")
    code = code_value if isinstance(code_value, str) else ""
    fallback_value = raw.get("fallback_action")
    fallback = fallback_value if isinstance(fallback_value, str) else ""
    return {
        "code": code if code in _SAFE_FAILURE_CODES else "HANDOFF_REQUIRED",
        "retryable": bool(raw.get("retryable", True)),
        "fallback_action": fallback if fallback in _SAFE_FALLBACK_ACTIONS else "handoff",
    }


def _safe_booking_state(value: object) -> dict[str, Any]:
    raw = _mapping(value) or {}
    vehicle_value = raw.get("vehicle_type")
    vehicle_type = vehicle_value if isinstance(vehicle_value, str) else ""
    confirmation_value = raw.get("confirmation_status")
    confirmation_status = confirmation_value if isinstance(confirmation_value, str) else ""
    return {
        "schema_version": "1",
        "revision": max(0, _safe_int(raw.get("revision"))),
        "pickup": _safe_place(raw.get("pickup")),
        "destination": _safe_place(raw.get("destination")),
        "vehicle_type": vehicle_type if vehicle_type in _SAFE_VEHICLES else None,
        "quote": _safe_quote(raw.get("quote")),
        "confirmation_status": (
            confirmation_status if confirmation_status in _SAFE_CONFIRMATION_STATUSES else "not_requested"
        ),
        "cancellation_confirmation_pending": bool(raw.get("cancellation_confirmation_pending", False)),
        "booking": _safe_booking(raw.get("booking")),
    }


def _safe_context_summary(state: Mapping[str, Any]) -> str:
    parts: list[str] = []
    pickup = state.get("pickup")
    destination = state.get("destination")
    if isinstance(pickup, Mapping):
        parts.append(f"điểm đón {pickup['display_name']}")
    else:
        parts.append("điểm đón chưa xác nhận")
    if isinstance(destination, Mapping):
        parts.append(f"điểm đến {destination['display_name']}")
    else:
        parts.append("điểm đến chưa xác nhận")

    vehicle_labels = {
        "MOTORBIKE": "xe máy",
        "CAR_4": "xe ô tô bốn chỗ",
        "CAR_7": "xe ô tô bảy chỗ",
        "LUXURY": "xe cao cấp",
    }
    vehicle = state.get("vehicle_type")
    if vehicle in vehicle_labels:
        parts.append(f"loại xe {vehicle_labels[vehicle]}")

    quote = state.get("quote")
    if isinstance(quote, Mapping):
        parts.append(f"báo giá {quote['fare_amount']} {quote['currency']}")
    if state.get("booking") is not None:
        parts.append("đã tạo chuyến")
    elif state.get("confirmation_status") == "awaiting":
        parts.append("đang chờ khách xác nhận đặt chuyến")
    return "; ".join(parts)


def _sanitize(source: Mapping[str, object], *, record: bool) -> dict[str, object]:
    allowed_keys = _SAFE_RECORD_KEYS if record else _SAFE_PAYLOAD_KEYS
    safe = {key: source[key] for key in allowed_keys if key in source}
    safe["pending_action"] = _safe_choice(source.get("pending_action"), _SAFE_PENDING_ACTIONS, None)
    safe["severity"] = _safe_choice(source.get("severity"), _SAFE_SEVERITIES, "NORMAL")
    safe["queue"] = _safe_choice(source.get("queue"), _SAFE_QUEUES, "GENERAL_OPERATOR")
    if record:
        safe["status"] = _safe_choice(source.get("status"), _SAFE_STATUSES, "pending")
    safe["priority"] = min(100, max(0, _safe_int(source.get("priority"), 50)))
    safe["requires_immediate_transfer"] = bool(source.get("requires_immediate_transfer", False))

    reason_code = _safe_reason_code(source.get("reason_code"))
    reason_label = _SAFE_REASON_LABELS[reason_code]
    raw_context = _mapping(source.get("context_snapshot"))
    if raw_context is None:
        safe_context = None
        context_summary = ""
    else:
        booking_state = _safe_booking_state(raw_context.get("booking_state"))
        context_summary = _safe_context_summary(booking_state)
        safe_context = {
            "schema_version": "1",
            "summary": context_summary,
            "booking_state": booking_state,
            "last_failure": _safe_failure(raw_context.get("last_failure")),
        }

    safe["reason"] = reason_label
    safe["reason_code"] = reason_code
    safe["summary"] = f"{reason_label}; {context_summary}" if context_summary else reason_label
    safe["context_snapshot"] = safe_context
    return safe


def sanitize_handoff_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return _sanitize(payload, record=False)


def sanitize_handoff_record(record: Mapping[str, object]) -> dict[str, object]:
    return _sanitize(record, record=True)
