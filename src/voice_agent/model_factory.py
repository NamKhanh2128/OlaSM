"""Factories for LiveKit-native model instances shared by worker and evals."""

from __future__ import annotations

import os

from livekit.agents import inference, stt

from src.voice_agent.config import LiveKitVoiceSettings


def build_stt(settings: LiveKitVoiceSettings) -> stt.STT:
    """Build the configured STT using the selected provider's own credentials."""

    if settings.livekit_stt_provider == "elevenlabs":
        try:
            from livekit.plugins import elevenlabs
        except ImportError as exc:  # pragma: no cover - depends on optional plugin
            raise RuntimeError(
                "LIVEKIT_STT_PROVIDER=elevenlabs requires the livekit-plugins-elevenlabs package."
            ) from exc
        return elevenlabs.STT(
            api_key=settings.eleven_api_key.get_secret_value(),
            model=settings.livekit_stt_model,
            language_code=settings.livekit_stt_language,
            server_vad={
                "vad_silence_threshold_secs": (settings.livekit_stt_server_vad_silence_threshold_seconds),
                "vad_threshold": settings.livekit_stt_server_vad_threshold,
                "min_speech_duration_ms": settings.livekit_stt_server_vad_min_speech_duration_ms,
                "min_silence_duration_ms": settings.livekit_stt_server_vad_min_silence_duration_ms,
            },
        )

    if settings.livekit_stt_provider == "google":
        try:
            from livekit.plugins import google
        except ImportError as exc:  # pragma: no cover - depends on optional plugin
            raise RuntimeError("LIVEKIT_STT_PROVIDER=google requires the livekit-plugins-google package.") from exc
        # BaseSettings reads .env without exporting values process-wide. Google
        # ADC uses this official variable to resolve the Speech v2 recognizer.
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.google_cloud_project
        return google.STT(
            model=settings.livekit_stt_model,
            languages=settings.livekit_stt_language,
            location=settings.google_stt_location,
            spoken_punctuation=False,
        )

    return inference.STT(
        model=settings.livekit_stt_model,
        language=settings.livekit_stt_language,
        api_key=settings.livekit_api_key.get_secret_value(),
        api_secret=settings.livekit_api_secret.get_secret_value(),
    )
