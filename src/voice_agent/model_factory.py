"""Factories for LiveKit-native model instances shared by worker and evals."""

from __future__ import annotations

import os

from livekit.agents import inference, stt, tts

from src.voice_agent.config import LiveKitVoiceSettings


def build_llm(settings: LiveKitVoiceSettings):
    """Build an LLM through a supported LiveKit provider integration."""

    if settings.livekit_llm_provider == "openai":
        try:
            from livekit.plugins import openai
        except ImportError as exc:  # pragma: no cover - depends on optional plugin
            raise RuntimeError("LIVEKIT_LLM_PROVIDER=openai requires the livekit-plugins-openai package.") from exc
        # The repository currently pins OpenAI SDK 2.20 through aider-chat.
        # Plugin 1.5's Responses event schema is no longer compatible with the
        # current OpenAI wire response, while Chat Completions remains supported
        # and preserves LiveKit function-tool behavior.
        return openai.LLM(
            model=settings.livekit_llm_model,
            api_key=settings.openai_api_key.get_secret_value(),
            # Booking tools mutate one revisioned business document. LiveKit's
            # documented serial tool loop prevents independent calls from racing
            # the optimistic state revision.
            parallel_tool_calls=False,
        )

    return inference.LLM(
        model=settings.livekit_llm_model,
        api_key=settings.livekit_api_key.get_secret_value(),
        api_secret=settings.livekit_api_secret.get_secret_value(),
        extra_kwargs={"parallel_tool_calls": False},
    )


def build_tts(settings: LiveKitVoiceSettings):
    """Build TTS through LiveKit Inference or its official OpenAI plugin."""

    if settings.livekit_tts_provider == "openai":
        try:
            from livekit.plugins import openai
        except ImportError as exc:  # pragma: no cover - depends on optional plugin
            raise RuntimeError("LIVEKIT_TTS_PROVIDER=openai requires the livekit-plugins-openai package.") from exc
        return openai.TTS(
            model=settings.livekit_tts_model,
            voice=settings.livekit_tts_voice,
            api_key=settings.openai_api_key.get_secret_value(),
            instructions="Nói tiếng Việt tự nhiên, rõ ràng, thân thiện và với âm lượng ổn định.",
        )

    if settings.livekit_tts_provider == "google":
        try:
            from google.cloud import texttospeech
            from livekit.plugins import google
        except ImportError as exc:
            raise RuntimeError("LIVEKIT_TTS_PROVIDER=google requires the livekit-plugins-google package.") from exc

        def build_google_tts(model: str, voice: str):
            return google.TTS(
                language=settings.livekit_tts_language,
                voice_name=voice,
                model_name=model,
                audio_encoding=(
                    texttospeech.AudioEncoding.LINEAR16 if model == "chirp_3" else texttospeech.AudioEncoding.PCM
                ),
            )

        primary = build_google_tts(settings.livekit_tts_model, settings.livekit_tts_voice)
        fallback_model = settings.livekit_google_tts_fallback_model
        fallback_voice = settings.livekit_google_tts_fallback_voice
        if (
            settings.livekit_tts_model == "chirp_3"
            or not fallback_model
            or not fallback_voice
            or (settings.livekit_tts_model, settings.livekit_tts_voice) == (fallback_model, fallback_voice)
        ):
            return primary
        return tts.FallbackAdapter(
            [primary, build_google_tts(fallback_model, fallback_voice)],
            max_retry_per_tts=settings.livekit_tts_max_retries,
        )

    return inference.TTS(
        model=settings.livekit_tts_model,
        voice=settings.livekit_tts_voice,
        language=settings.livekit_tts_language,
        api_key=settings.livekit_api_key.get_secret_value(),
        api_secret=settings.livekit_api_secret.get_secret_value(),
    )


def tts_voice_map(settings: LiveKitVoiceSettings) -> dict[str, str]:
    voices = {settings.livekit_tts_model: settings.livekit_tts_voice}
    if settings.livekit_tts_provider == "google" and settings.livekit_tts_model != "chirp_3":
        fallback_model = settings.livekit_google_tts_fallback_model
        fallback_voice = settings.livekit_google_tts_fallback_voice
        if fallback_model and fallback_voice:
            voices[fallback_model] = fallback_voice
    return voices


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
