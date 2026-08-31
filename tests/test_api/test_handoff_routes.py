import pytest

from src.backend.repositories.handoff_repository import get_handoff_repository
from src.backend.services.auth_service import AuthService


async def _login(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0901234567", "password": "Password123!"},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_handoff_routes_require_auth_and_operator_role(client):
    unauthenticated = await client.get("/api/v1/handoffs")
    assert unauthenticated.status_code == 401

    login = await _login(client)
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = await client.post(
        "/api/v1/handoffs",
        headers=headers,
        json={
            "session_id": login["session_id"],
            "reason": "Customer requested support",
            "reason_code": "USER_REQUEST",
            "summary": "Safe summary",
        },
    )
    assert created.status_code == 201

    forbidden = await client.get("/api/v1/handoffs", headers=headers)
    assert forbidden.status_code == 403

    AuthService.users["0901234567"]["role"] = "OPERATOR"
    try:
        pending = await client.get("/api/v1/handoffs", headers=headers)
        assert pending.status_code == 200
        handoff_id = created.json()["handoff_id"]
        assert any(item["handoff_id"] == handoff_id for item in pending.json())

        accepted = await client.post(f"/api/v1/handoffs/{handoff_id}/accept", headers=headers)
        assert accepted.status_code == 200
        assert accepted.json()["operator_id"] == "usr_demo"
    finally:
        AuthService.users["0901234567"]["role"] = "CUSTOMER"


@pytest.mark.asyncio
async def test_customer_cannot_create_handoff_for_another_session(client):
    login = await _login(client)
    response = await client.post(
        "/api/v1/handoffs",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={
            "session_id": "sess-other",
            "reason": "Invalid ownership",
            "summary": "Safe summary",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operator_api_masks_sensitive_legacy_handoff_context(client):
    login = await _login(client)
    access_token = login["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    AuthService.users["0901234567"]["role"] = "OPERATOR"
    handoff_id = "handoff_api_legacy_privacy"
    repository = get_handoff_repository()
    repository.create(
        {
            "handoff_id": handoff_id,
            "session_id": login["session_id"],
            "reason": "PRIVATE_REASON_MARKER",
            "reason_code": "USER_REQUEST",
            "summary": "PRIVATE_SUMMARY_MARKER",
            "priority": 50,
            "severity": "NORMAL",
            "queue": "GENERAL_OPERATOR",
            "requires_immediate_transfer": False,
            "status": "pending",
            "created_at": "2026-08-31T00:00:00+00:00",
            "context_snapshot": {
                "summary": "PRIVATE_QUERY_MARKER",
                "booking_state": {
                    "pickup": {
                        "place_id": "pickup",
                        "display_name": "Public pickup",
                        "address": "PRIVATE_ADDRESS_MARKER",
                        "provider": "test",
                    }
                },
            },
        }
    )

    try:
        response = await client.get("/api/v1/handoffs", headers=headers)

        assert response.status_code == 200
        item = next(item for item in response.json() if item["handoff_id"] == handoff_id)
        serialized = str(item)
        assert "PRIVATE_REASON_MARKER" not in serialized
        assert "PRIVATE_SUMMARY_MARKER" not in serialized
        assert "PRIVATE_QUERY_MARKER" not in serialized
        assert "PRIVATE_ADDRESS_MARKER" not in serialized
        assert item["reason"] == "Khách yêu cầu gặp tổng đài viên"
        assert item["context_snapshot"]["booking_state"]["pickup"] == {
            "place_id": "pickup",
            "display_name": "Public pickup",
            "provider": "test",
        }
    finally:
        AuthService.users["0901234567"]["role"] = "CUSTOMER"
