"""Mobile-specific LiveKit token endpoint for the Flutter client.

This endpoint is streamlined for the mobile wake-word and push-to-talk flows
where a full web session lifecycle is not required. The mobile client sends a
device_id to get fresh LiveKit credentials immediately.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from livekit import api

from src.backend.schemas.mobile import MobileTokenRequestDTO, MobileTokenResponseDTO
from src.voice_agent.config import LiveKitVoiceSettings, get_livekit_voice_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["mobile"])


def _issue_mobile_token(
    settings: LiveKitVoiceSettings,
    *,
    device_id: str,
    user_id: str | None = None,
    trigger_source: str = "push_to_talk",
) -> tuple[str, str, str]:
    """Issue a least-privilege LiveKit token for a mobile device.

    Returns (server_url, participant_token, room_name).
    """
    settings.require_configured()

    # Use device_id as the primary identity when no auth is present.
    effective_user = user_id or f"mobile-{device_id}"
    call_instance = str(uuid.uuid4())
    room_digest = hashlib.sha256(
        f"{effective_user}:{call_instance}".encode()
    ).hexdigest()[:24]
    identity_digest = hashlib.sha256(effective_user.encode()).hexdigest()[:20]
    room_name = f"olasm-m-{room_digest}"
    participant_identity = f"customer-m-{identity_digest}"

    metadata = json.dumps(
        {
            "schema_version": "1",
            "app_session_id": call_instance,
            "client_type": "mobile_flutter",
            "trigger_source": trigger_source,
        },
        separators=(",", ":"),
    )

    token = (
        api.AccessToken(
            settings.livekit_api_key.get_secret_value(),
            settings.livekit_api_secret.get_secret_value(),
        )
        .with_identity(participant_identity)
        .with_name("Khách hàng OlaSM Mobile")
        .with_metadata(metadata)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_update_own_metadata=False,
            )
        )
        .with_room_config(
            api.RoomConfiguration(
                agents=[
                    api.RoomAgentDispatch(
                        agent_name=settings.livekit_agent_name,
                        metadata=metadata,
                    )
                ]
            )
        )
        .with_ttl(timedelta(seconds=settings.livekit_token_ttl_seconds))
    )
    return settings.livekit_url, token.to_jwt(), room_name


@router.post(
    "/voice-token",
    response_model=MobileTokenResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Issue LiveKit credentials for the Flutter mobile client",
)
async def create_mobile_voice_token(
    request: MobileTokenRequestDTO,
) -> MobileTokenResponseDTO:
    """Return LiveKit connection details for the mobile voice session.

    Called by the Flutter app when:
    - The wake word "Hey OlaSM" is detected on-device
    - The user taps the push-to-talk microphone button

    The endpoint validates the device_id, issues a short-lived JWT with
    the correct room/agent configuration, and returns everything the
    Flutter client needs to connect and start streaming audio.
    """
    settings = get_livekit_voice_settings()
    errors = settings.configuration_errors()
    if errors:
        logger.error("LiveKit not configured for mobile token: %s", errors)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit chưa được cấu hình sẵn sàng cho mobile",
        )

    # Optional: resolve auth_token to a user_id if Green SM auth is integrated
    user_id: str | None = None
    if request.auth_token:
        try:
            from src.backend.api.routes.auth import service as auth_service

            user = await auth_service.get_user_for_token_durable(request.auth_token)
            if user is not None:
                user_id = str(user["user_id"])
        except Exception:
            logger.warning(
                "Mobile auth token resolution failed device=%s",
                request.device_id,
            )

    try:
        server_url, participant_token, room_name = _issue_mobile_token(
            settings,
            device_id=request.device_id,
            user_id=user_id,
            trigger_source=request.trigger_source,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit chưa được cấu hình sẵn sàng",
        ) from exc

    logger.info(
        "mobile_token_issued device=%s trigger=%s room=%s",
        request.device_id[:8],
        request.trigger_source,
        room_name,
    )

    return MobileTokenResponseDTO(
        server_url=server_url,
        participant_token=participant_token,
        room_name=room_name,
        agent_name=settings.livekit_agent_name,
        token_ttl_seconds=settings.livekit_token_ttl_seconds,
    )
