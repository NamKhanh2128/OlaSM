import asyncio
import logging

import pytest
from livekit.agents import AgentSession

from src.voice_agent.config import LiveKitVoiceSettings
from src.voice_agent.model_factory import build_tts
from src.voice_agent.server import (
    _configure_worker_console_logging,
    _connect_room_early,
    build_agent_session,
    prepare_process,
    request_initial_greeting,
    restore_session_data,
)
from src.voice_agent.session_data import AloSMSessionData


def _settings(**overrides: object) -> LiveKitVoiceSettings:
    values: dict[str, object] = {
        "livekit_url": "wss://alosm.test.livekit.cloud",
        "livekit_api_key": "api-key",
        "livekit_api_secret": "test-api-secret-with-at-least-32-bytes",
        "livekit_stt_provider": "livekit",
        "livekit_stt_model": "deepgram/nova-3",
        "livekit_stt_language": "multi",
        "livekit_turn_detection": "vad",
        "livekit_llm_model": "google/gemma-4-31b-it",
        "livekit_tts_provider": "livekit",
        "livekit_tts_model": "cartesia/sonic-3",
        "livekit_tts_voice": "test-voice",
    }
    values.update(overrides)
    return LiveKitVoiceSettings(_env_file=None, **values)


def test_worker_console_logging_mutes_sdk_debug_noise() -> None:
    logger_names = ("grpc", "grpc._cython.cygrpc", "livekit.agents", "src.voice_agent.observability")
    previous_levels = {name: logging.getLogger(name).level for name in logger_names}

    try:
        _configure_worker_console_logging()

        assert logging.getLogger("grpc").level == logging.WARNING
        assert logging.getLogger("grpc._cython.cygrpc").level == logging.WARNING
        assert logging.getLogger("livekit.agents").level == logging.WARNING
        assert logging.getLogger("src.voice_agent.observability").level == logging.INFO
    finally:
        for logger_name, level in previous_levels.items():
            logging.getLogger(logger_name).setLevel(level)


@pytest.mark.asyncio
async def test_connect_room_early_awaits_connection_before_session_setup() -> None:
    class Context:
        def __init__(self) -> None:
            self.connect_calls = 0

        async def connect(self) -> None:
            self.connect_calls += 1

    context = Context()

    duration_ms = await _connect_room_early(context)  # type: ignore[arg-type]

    assert context.connect_calls == 1
    assert duration_ms >= 0


@pytest.mark.asyncio
async def test_build_agent_session_uses_livekit_native_pipeline() -> None:
    session = build_agent_session(_settings())

    assert isinstance(session, AgentSession)
    assert session.userdata.booking_draft.public_state()["confirmation_status"] == "not_requested"
    assert session.options.endpointing["mode"] == "fixed"
    assert session.options.turn_handling["turn_detection"] == "vad"
    assert session.stt.model == "deepgram/nova-3"
    assert session.options.endpointing["min_delay"] == 0.25
    assert session.options.endpointing["max_delay"] == 1.0
    assert session.options.interruption["mode"] == "vad"
    assert session.options.interruption["min_duration"] == 0.5
    assert session.options.interruption["min_words"] == 0
    assert session.options.preemptive_generation["enabled"] is False
    assert session.options.transcription_timeout == 5.0
    assert session._conn_options.tts_conn_options.timeout == 30.0
    assert session._conn_options.tts_conn_options.max_retry == 1
    assert session._conn_options.tts_conn_options.retry_interval == 0.5


@pytest.mark.asyncio
async def test_adaptive_interruption_requires_explicit_configuration() -> None:
    session = build_agent_session(_settings(livekit_interruption_mode="adaptive"))

    assert session.options.interruption["mode"] == "adaptive"


@pytest.mark.asyncio
async def test_build_agent_session_can_use_openai_plugin_without_changing_voice_pipeline() -> None:
    session = build_agent_session(
        _settings(
            livekit_llm_provider="openai",
            livekit_llm_model="gpt-4.1-mini",
            openai_api_key="test-openai-key",
        )
    )

    assert isinstance(session, AgentSession)
    assert session.llm.model == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_build_agent_session_can_use_openai_tts_plugin() -> None:
    session = build_agent_session(
        _settings(
            livekit_tts_provider="openai",
            livekit_tts_model="gpt-4o-mini-tts",
            livekit_tts_voice="ash",
            openai_api_key="test-openai-key",
        )
    )

    assert isinstance(session, AgentSession)
    assert session.tts.model == "gpt-4o-mini-tts"


def test_build_google_tts_uses_the_native_google_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.cloud import texttospeech
    from livekit.plugins import google

    constructed: dict[str, object] = {}
    fake_tts = object()

    def build_google_tts(**kwargs: object) -> object:
        constructed.update(kwargs)
        return fake_tts

    monkeypatch.setattr(google, "TTS", build_google_tts)

    assert (
        build_tts(
            _settings(
                livekit_tts_provider="google",
                livekit_tts_model="chirp_3",
                livekit_tts_voice="vi-VN-Chirp3-HD-Autonoe",
                livekit_tts_language="vi-VN",
            )
        )
        is fake_tts
    )
    assert constructed == {
        "language": "vi-VN",
        "voice_name": "vi-VN-Chirp3-HD-Autonoe",
        "model_name": "chirp_3",
        "audio_encoding": texttospeech.AudioEncoding.LINEAR16,
    }


def test_build_google_gemini_tts_uses_pcm_and_chirp_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from google.cloud import texttospeech
    from livekit.agents import tts
    from livekit.plugins import google

    constructed: list[dict[str, object]] = []

    class FakeTTS:
        num_channels = 1
        sample_rate = 24000
        capabilities = SimpleNamespace(streaming=True, aligned_transcript=False)

        def on(self, *_: object) -> None:
            return None

    def build_google_tts(**kwargs: object) -> FakeTTS:
        constructed.append(kwargs)
        return FakeTTS()

    monkeypatch.setattr(google, "TTS", build_google_tts)

    built_tts = build_tts(
        _settings(
            livekit_tts_provider="google",
            livekit_tts_model="gemini-2.5-flash-tts",
            livekit_tts_voice="Kore",
            livekit_tts_language="vi-VN",
        )
    )

    assert isinstance(built_tts, tts.FallbackAdapter)
    assert built_tts._max_retry_per_tts == 1
    assert constructed == [
        {
            "language": "vi-VN",
            "voice_name": "Kore",
            "model_name": "gemini-2.5-flash-tts",
            "audio_encoding": texttospeech.AudioEncoding.PCM,
        },
        {
            "language": "vi-VN",
            "voice_name": "vi-VN-Chirp3-HD-Autonoe",
            "model_name": "chirp_3",
            "audio_encoding": texttospeech.AudioEncoding.LINEAR16,
        },
    ]


def test_build_agent_session_fails_closed_before_worker_start() -> None:
    with pytest.raises(ValueError, match="LIVEKIT_STT_MODEL_REQUIRED"):
        build_agent_session(_settings(livekit_stt_model=""))


def test_livekit_process_setup_prewarms_native_models_and_state_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Process:
        userdata: dict[str, object] = {}

    warmed_vad = object()
    warmed_stt = object()
    monkeypatch.setattr("src.voice_agent.server.inference.VAD", lambda **_: warmed_vad)
    monkeypatch.setattr("src.voice_agent.server.build_stt", lambda _: warmed_stt)

    prepare_process(Process())  # type: ignore[arg-type]

    assert Process.userdata["alosm_process_store_ready"] is True
    assert Process.userdata["alosm_voice_state_store"] is not None
    assert Process.userdata["alosm_prewarmed_vad"] is warmed_vad
    assert Process.userdata["alosm_prewarmed_stt"] is warmed_stt
    assert Process.userdata["alosm_prewarmed_knowledge"] is not None
    assert Process.userdata["alosm_prewarmed_pricing"] is not None


def test_new_call_greeting_uses_native_say_without_llm() -> None:
    class Session:
        userdata = AloSMSessionData(
            app_session_id="session",
            call_id="call",
            user_id="user",
            participant_identity="participant",
        )

        def __init__(self) -> None:
            self.said: list[tuple[str, bool]] = []
            self.generated = False

        def say(self, text: str, *, allow_interruptions: bool) -> None:
            self.said.append((text, allow_interruptions))

        def generate_reply(self, **_: object) -> None:
            self.generated = True

    session = Session()

    request_initial_greeting(session, recovered=False)  # type: ignore[arg-type]

    assert session.said == [
        (
            "Chào bạn, tôi là tổng đài viên AloSM. Bạn vui lòng cho biết yêu cầu đặt xe của mình nhé?",
            True,
        )
    ]
    assert session.generated is False


@pytest.mark.asyncio
async def test_new_session_restore_does_not_write_empty_state_on_startup() -> None:
    class EmptyStore:
        async def restore(self, userdata) -> bool:  # type: ignore[no-untyped-def]
            return False

        async def save(self, userdata) -> None:  # type: ignore[no-untyped-def]
            raise AssertionError("empty state must not add a second startup round-trip")

    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )

    recovered = await restore_session_data(userdata, EmptyStore(), timeout_seconds=1)  # type: ignore[arg-type]

    assert recovered is False
    assert userdata.persistence_enabled is True


@pytest.mark.asyncio
async def test_state_restore_timeout_falls_back_without_blocking_voice_session() -> None:
    class HangingStore:
        async def restore(self, userdata) -> bool:  # type: ignore[no-untyped-def]
            await asyncio.Event().wait()
            return False

        async def save(self, userdata) -> None:  # type: ignore[no-untyped-def]
            raise AssertionError("save must not run after restore timeout")

    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )

    recovered = await restore_session_data(
        userdata,
        HangingStore(),  # type: ignore[arg-type]
        timeout_seconds=0.001,
    )

    assert recovered is False
    assert userdata.persistence_enabled is False
    assert userdata.last_failure is not None
    assert userdata.last_failure.code == "SESSION_RECOVERY_FAILED"
