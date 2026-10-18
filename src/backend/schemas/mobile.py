"""Contracts for the mobile Flutter client token endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MobileTokenRequestDTO(BaseModel):
    """Request from the Flutter mobile app for LiveKit connection details.

    The mobile client sends this when either:
    - The wake word triggers and a LiveKit room is needed immediately
    - The user taps the push-to-talk microphone button

    Unlike the web flow, mobile clients carry their own auth token
    and don't need an existing web session to start a voice call.
    """

    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Stable device identifier (UUID recommended)",
    )
    auth_token: str | None = Field(
        default=None,
        description="Optional bearer token from Green SM auth; allows identity binding",
    )
    trigger_source: str = Field(
        default="push_to_talk",
        pattern=r"^(wake_word|push_to_talk)$",
        description="How the voice session was initiated",
    )
    wake_word_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Detection confidence if triggered by wake word",
    )


class MobileTokenResponseDTO(BaseModel):
    """Connection details returned to the Flutter mobile client."""

    server_url: str
    participant_token: str
    room_name: str
    agent_name: str
    token_ttl_seconds: int
