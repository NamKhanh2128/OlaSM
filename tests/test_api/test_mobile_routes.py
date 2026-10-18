import pytest
from unittest.mock import patch, MagicMock

from src.main import app
from src.voice_agent.config import LiveKitVoiceSettings


@pytest.fixture
def mock_configured_livekit():
    mock_settings = MagicMock(spec=LiveKitVoiceSettings)
    mock_settings.configuration_errors.return_value = []
    mock_settings.livekit_url = "wss://test-livekit.olasm.vn"
    mock_settings.livekit_agent_name = "olasm-voice-agent"
    mock_settings.livekit_token_ttl_seconds = 900
    mock_settings.require_configured.return_value = None

    with patch(
        "src.backend.api.routes.mobile.get_livekit_voice_settings",
        return_value=mock_settings,
    ), patch(
        "src.backend.api.routes.mobile._issue_mobile_token",
        return_value=(
            "wss://test-livekit.olasm.vn",
            "mocked.jwt.token",
            "olasm-m-testroom123",
        ),
    ):
        yield mock_settings


@pytest.mark.asyncio
async def test_mobile_token_push_to_talk(client, mock_configured_livekit):
    """Test mobile voice token issuance via push-to-talk button."""
    response = await client.post(
        "/api/v1/mobile/voice-token",
        json={
            "device_id": "test-device-uuid-12345678",
            "trigger_source": "push_to_talk",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["server_url"] == "wss://test-livekit.olasm.vn"
    assert data["participant_token"] == "mocked.jwt.token"
    assert data["room_name"] == "olasm-m-testroom123"
    assert data["agent_name"] == "olasm-voice-agent"
    assert data["token_ttl_seconds"] == 900


@pytest.mark.asyncio
async def test_mobile_token_wake_word(client, mock_configured_livekit):
    """Test mobile voice token issuance via wake word trigger with confidence score."""
    response = await client.post(
        "/api/v1/mobile/voice-token",
        json={
            "device_id": "test-device-uuid-87654321",
            "trigger_source": "wake_word",
            "wake_word_confidence": 0.89,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["participant_token"] == "mocked.jwt.token"
    assert data["server_url"] == "wss://test-livekit.olasm.vn"


@pytest.mark.asyncio
async def test_mobile_token_invalid_device_id(client, mock_configured_livekit):
    """Test rejection when device_id is too short."""
    response = await client.post(
        "/api/v1/mobile/voice-token",
        json={
            "device_id": "short",  # min_length is 8
            "trigger_source": "push_to_talk",
        },
    )
    assert response.status_code == 422
