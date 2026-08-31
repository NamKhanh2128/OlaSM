from datetime import UTC, datetime

import pytest

from src.backend.repositories.handoff_repository import HandoffRepository
from src.backend.services.handoff_service import HandoffService


def test_handoff_service_persists_lists_and_accepts_real_record():
    service = HandoffService(HandoffRepository())
    created = service.create_handoff(
        {
            "session_id": "sess-1",
            "reason": "Emergency",
            "reason_code": "EMERGENCY",
            "summary": "Customer needs immediate help",
            "priority": 100,
            "severity": "CRITICAL",
            "queue": "SAFETY_OPERATOR",
            "requires_immediate_transfer": True,
        }
    )

    pending = service.list_handoffs("pending")
    assert [item["handoff_id"] for item in pending] == [created["handoff_id"]]
    assert pending[0]["reason_code"] == "EMERGENCY"

    accepted = service.accept_handoff(created["handoff_id"], "operator-1")
    assert accepted["status"] == "accepted"
    assert accepted["operator_id"] == "operator-1"
    assert service.list_handoffs("pending") == []
    assert service.list_handoffs("accepted")[0]["handoff_id"] == created["handoff_id"]


def test_accept_unknown_handoff_is_rejected():
    service = HandoffService(HandoffRepository())

    with pytest.raises(KeyError):
        service.accept_handoff("handoff-missing")


def test_handoff_service_redacts_operator_payload_before_storage():
    service = HandoffService(HandoffRepository())
    private_address = "PRIVATE_ADDRESS_MARKER"
    private_query = "PRIVATE_QUERY_MARKER"
    private_reason = "PRIVATE_REASON_MARKER"

    created = service.create_handoff(
        {
            "session_id": "sess-private",
            "reason": private_reason,
            "reason_code": "USER_REQUEST",
            "summary": f"Lý do: {private_reason}",
            "priority": 60,
            "pending_action": private_reason,
            "severity": private_reason,
            "queue": private_reason,
            "context_snapshot": {
                "schema_version": "1",
                "summary": f"điểm đón {private_query}",
                "booking_state": {
                    "schema_version": "1",
                    "revision": 2,
                    "pickup": {
                        "place_id": "pickup",
                        "display_name": "Public pickup",
                        "address": private_address,
                        "provider": "test",
                        "city": "Hà Nội",
                    },
                    "destination": {
                        "place_id": "destination",
                        "display_name": "Public destination",
                        "address": private_address,
                        "provider": "test",
                    },
                    "vehicle_type": "CAR_4",
                    "quote": None,
                    "confirmation_status": "not_requested",
                    "cancellation_confirmation_pending": False,
                    "booking": None,
                },
                "last_failure": {
                    "code": "HANDOFF_REQUIRED",
                    "message": private_reason,
                    "retryable": False,
                    "fallback_action": "handoff",
                },
            },
        }
    )

    serialized = str(created)
    assert private_address not in serialized
    assert private_query not in serialized
    assert private_reason not in serialized
    assert created["reason"] == "Khách yêu cầu gặp tổng đài viên"
    assert created["pending_action"] is None
    assert created["severity"] == "NORMAL"
    assert created["queue"] == "GENERAL_OPERATOR"
    context = created["context_snapshot"]
    assert context["booking_state"]["pickup"] == {
        "place_id": "pickup",
        "display_name": "Public pickup",
        "provider": "test",
    }
    assert context["booking_state"]["destination"] == {
        "place_id": "destination",
        "display_name": "Public destination",
        "provider": "test",
    }


def test_handoff_service_redacts_legacy_record_when_reading():
    repository = HandoffRepository()
    repository.create(
        {
            "handoff_id": "handoff-legacy",
            "session_id": "sess-legacy",
            "reason": "PRIVATE_REASON_MARKER",
            "reason_code": "USER_REQUEST",
            "summary": "PRIVATE_SUMMARY_MARKER",
            "priority": 60,
            "severity": "NORMAL",
            "queue": "GENERAL_OPERATOR",
            "requires_immediate_transfer": False,
            "status": "pending",
            "context_snapshot": {
                "schema_version": "1",
                "summary": "PRIVATE_QUERY_MARKER",
                "booking_state": {
                    "pickup": {
                        "place_id": "pickup",
                        "display_name": "Public pickup",
                        "address": "PRIVATE_ADDRESS_MARKER",
                        "provider": "test",
                    },
                },
                "last_failure": {"message": "PRIVATE_FAILURE_MARKER"},
            },
        }
    )

    listed = HandoffService(repository).list_handoffs("pending")

    serialized = str(listed[0])
    assert "PRIVATE_REASON_MARKER" not in serialized
    assert "PRIVATE_SUMMARY_MARKER" not in serialized
    assert "PRIVATE_QUERY_MARKER" not in serialized
    assert "PRIVATE_ADDRESS_MARKER" not in serialized
    assert "PRIVATE_FAILURE_MARKER" not in serialized


def test_pending_queue_is_sorted_by_priority():
    service = HandoffService(HandoffRepository())
    service.create_handoff({"session_id": "low", "reason": "low", "summary": "low", "priority": 10})
    service.create_handoff({"session_id": "high", "reason": "high", "summary": "high", "priority": 90})

    assert [item["session_id"] for item in service.list_handoffs("pending")] == ["high", "low"]


def test_pending_queue_is_sorted_newest_first_within_same_priority():
    service = HandoffService(HandoffRepository())
    older = service.create_handoff({"session_id": "older", "reason": "older", "summary": "older", "priority": 50})
    newer = service.create_handoff({"session_id": "newer", "reason": "newer", "summary": "newer", "priority": 50})
    service._repository.update(older["handoff_id"], {"created_at": datetime(2026, 8, 31, 9, 0, tzinfo=UTC)})
    service._repository.update(newer["handoff_id"], {"created_at": datetime(2026, 8, 31, 10, 0, tzinfo=UTC)})

    assert [item["session_id"] for item in service.list_handoffs("pending")] == ["newer", "older"]
