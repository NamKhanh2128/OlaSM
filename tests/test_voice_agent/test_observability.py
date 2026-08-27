import json
import logging
from pathlib import Path

import pytest
from livekit.agents import (
    ConversationItemAddedEvent,
    ToolCallEnded,
    ToolCallStarted,
    ToolExecutionUpdatedEvent,
    UserInputTranscribedEvent,
    UserTranscriptionTimeoutEvent,
    llm,
)
from livekit.agents.metrics import TTSMetrics
from livekit.agents.metrics.base import Metadata

from src.voice_agent.observability import LiveKitSessionObserver, SessionEventLog
from src.voice_agent.session_data import AloSMSessionData


def _userdata(call_id: str = "call/livekit:1") -> AloSMSessionData:
    return AloSMSessionData(
        app_session_id="session-livekit",
        call_id=call_id,
        user_id="user",
        participant_identity="participant",
    )


def _read_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.asyncio
async def test_jsonl_observability_redacts_transcripts_by_default(tmp_path: Path) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=False,
        directory=tmp_path,
        userdata=_userdata(),
        room_name="room-1",
    )
    observer = LiveKitSessionObserver(
        event_log,
        tts_voices={"gemini-2.5-flash-tts": "Kore", "chirp_3": "vi-VN-Chirp3-HD-Autonoe"},
    )
    await event_log.start()

    observer.record(
        UserInputTranscribedEvent(
            transcript="đón tôi ở địa chỉ riêng tư",
            is_final=True,
            language="vi",
        )
    )
    observer.record(
        ConversationItemAddedEvent(
            item=llm.ChatMessage(
                role="user",
                content=["đón tôi ở địa chỉ riêng tư"],
                transcript_confidence=0.71,
                metrics={"transcription_delay": 0.2, "end_of_turn_delay": 0.8},
            )
        )
    )
    await event_log.close("test")

    raw = event_log.path.read_text(encoding="utf-8")
    events = _read_events(event_log.path)
    transcript_event = next(event for event in events if event["event"] == "user_input_transcribed")
    message_event = next(event for event in events if event["event"] == "conversation_item_added")

    assert "địa chỉ riêng tư" not in raw
    assert transcript_event["transcript_length"] == len("đón tôi ở địa chỉ riêng tư")
    assert "transcript" not in transcript_event
    assert message_event["transcript_confidence"] == 0.71
    assert message_event["metrics"] == {"transcription_delay": 0.2, "end_of_turn_delay": 0.8}
    assert event_log.path.name == "call_livekit_1.jsonl"


@pytest.mark.asyncio
async def test_console_log_keeps_turn_debugging_and_hides_usage_spam(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=False,
        directory=tmp_path,
        userdata=_userdata("call-console"),
        room_name="room-console",
    )
    await event_log.start()
    caplog.set_level(logging.DEBUG, logger="src.voice_agent.observability")
    caplog.clear()

    event_log.emit("session_usage_updated", model_usage=[{"type": "stt_usage"}])
    event_log.emit("user_state_changed", old_state="speaking", new_state="listening")
    event_log.emit("agent_state_changed", old_state="thinking", new_state="speaking")
    event_log.emit(
        "user_input_transcribed",
        is_final=True,
        language="vi",
        transcript_length=8,
    )
    await event_log.close("test")

    records = [record for record in caplog.records if "[voice:call-console]" in record.message]
    transcript_record = next(record for record in records if "ASR final" in record.message)
    assert not any("session_usage_updated" in record.message for record in records)
    assert not any(
        "user_state_changed" in record.message or "agent_state_changed" in record.message for record in records
    )
    assert transcript_record.levelno == logging.INFO
    assert any(event["event"] == "session_usage_updated" for event in _read_events(event_log.path))


@pytest.mark.asyncio
async def test_console_log_labels_asr_tool_and_tts_with_safe_fields(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=True,
        directory=tmp_path,
        userdata=_userdata("call-readable-console"),
        room_name="room-console",
    )
    observer = LiveKitSessionObserver(
        event_log,
        tts_voices={"gemini-2.5-flash-tts": "Kore", "chirp_3": "vi-VN-Chirp3-HD-Autonoe"},
    )
    await event_log.start()
    caplog.set_level(logging.INFO, logger="src.voice_agent.observability")
    caplog.clear()

    observer.record(UserInputTranscribedEvent(transcript="đón ở quận 1", is_final=True, language="vi"))
    call = llm.FunctionCall(
        call_id="tool-console",
        name="search_place",
        arguments='{"query":"địa chỉ riêng tư","target":"pickup"}',
    )
    observer.record(ToolExecutionUpdatedEvent(update=ToolCallStarted(function_call=call)))
    observer.record(
        ToolExecutionUpdatedEvent(
            update=ToolCallEnded(
                id="tool-console",
                call_id="tool-console",
                status="done",
                message="Đã tìm thấy địa điểm riêng tư.",
            )
        )
    )
    event_log.emit("conversation_item_added", role="assistant", text="Tôi đã tìm thấy địa điểm.")
    event_log.emit("speech_created", source="agent", speech_id="speech-1")
    observer.record_tts_metrics(
        TTSMetrics(
            timestamp=1.0,
            request_id="request-1",
            speech_id="speech-1",
            ttfb=0.23,
            duration=0.9,
            audio_duration=0.7,
            cancelled=False,
            characters_count=18,
            label="google",
            streamed=True,
            metadata=Metadata(model_name="chirp_3", model_provider="Google Cloud Platform"),
        )
    )
    await event_log.close("test")

    messages = [record.message for record in caplog.records if "[voice:call-readable-console]" in record.message]
    assert any("USER ASR final lang=vi text='đón ở quận 1'" in message for message in messages)
    assert any(
        "TOOL started name=search_place call_id=tool-console trigger='đón ở quận 1'" in message
        and 'input=\'{"query":"địa chỉ riêng tư","target":"pickup"}\'' in message
        for message in messages
    )
    assert any(
        "TOOL done name=search_place call_id=tool-console" in message
        and "result='Đã tìm thấy địa điểm riêng tư.'" in message
        and "duration_ms=" in message
        for message in messages
    )
    assert any("BOT LLM response text='Tôi đã tìm thấy địa điểm.'" in message for message in messages)
    assert any("BOT TTS queued source=agent speech_id=speech-1" in message for message in messages)
    assert any(
        "BOT TTS played speech_id=speech-1 provider=Google Cloud Platform model=chirp_3 "
        "voice=vi-VN-Chirp3-HD-Autonoe ttfb_ms=230.0 audio_ms=700.0" in message
        for message in messages
    )


@pytest.mark.asyncio
async def test_console_log_labels_authoritative_user_turn_transcript(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=True,
        directory=tmp_path,
        userdata=_userdata("call-user-turn"),
        room_name="room-console",
    )
    observer = LiveKitSessionObserver(event_log)
    await event_log.start()
    caplog.set_level(logging.INFO, logger="src.voice_agent.observability")
    caplog.clear()

    observer.record(
        ConversationItemAddedEvent(
            item=llm.ChatMessage(role="user", content=["đi đến Đại học Bách khoa Hà Nội"])
        )
    )
    await event_log.close("test")

    messages = [record.message for record in caplog.records if "[voice:call-user-turn]" in record.message]
    assert any("USER TURN transcript='đi đến Đại học Bách khoa Hà Nội'" in message for message in messages)

@pytest.mark.asyncio
async def test_jsonl_observability_can_explicitly_include_transcripts(tmp_path: Path) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=True,
        directory=tmp_path,
        userdata=_userdata("call-2"),
        room_name="room-2",
    )
    observer = LiveKitSessionObserver(
        event_log,
        tts_voices={"gemini-2.5-flash-tts": "Kore", "chirp_3": "vi-VN-Chirp3-HD-Autonoe"},
    )
    await event_log.start()
    observer.record(UserInputTranscribedEvent(transcript="đúng rồi", is_final=True))
    await event_log.close()

    event = next(item for item in _read_events(event_log.path) if item["event"] == "user_input_transcribed")
    assert event["transcript"] == "đúng rồi"


@pytest.mark.asyncio
async def test_jsonl_observability_records_native_transcription_timeout_without_audio(
    tmp_path: Path,
) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=False,
        directory=tmp_path,
        userdata=_userdata("call-timeout"),
        room_name="room-timeout",
    )
    observer = LiveKitSessionObserver(
        event_log,
        tts_voices={"gemini-2.5-flash-tts": "Kore", "chirp_3": "vi-VN-Chirp3-HD-Autonoe"},
    )
    await event_log.start()
    observer.record(
        UserTranscriptionTimeoutEvent(
            speech_duration=1.25,
            vad_speech_started_at=123.5,
        )
    )
    await event_log.close()

    event = next(item for item in _read_events(event_log.path) if item["event"] == "user_transcription_timeout")
    assert event["speech_duration"] == 1.25
    assert event["vad_speech_started_at"] == 123.5
    assert "transcript" not in event


@pytest.mark.asyncio
async def test_tool_logs_hide_arguments_and_outputs_without_transcript_debug(tmp_path: Path) -> None:
    event_log = SessionEventLog(
        enabled=True,
        include_transcripts=False,
        directory=tmp_path,
        userdata=_userdata("call-3"),
        room_name="room-3",
    )
    observer = LiveKitSessionObserver(
        event_log,
        tts_voices={"gemini-2.5-flash-tts": "Kore", "chirp_3": "vi-VN-Chirp3-HD-Autonoe"},
    )
    await event_log.start()
    observer.record(UserInputTranscribedEvent(transcript="địa chỉ bí mật", is_final=True))
    call = llm.FunctionCall(
        call_id="tool-1",
        name="search_place",
        arguments='{"query":"địa chỉ bí mật"}',
    )
    observer.record(ToolExecutionUpdatedEvent(update=ToolCallStarted(function_call=call)))
    observer.record(
        ToolExecutionUpdatedEvent(
            update=ToolCallEnded(
                id="tool-1",
                call_id="tool-1",
                status="done",
                message="provider payload bí mật",
            )
        )
    )
    await event_log.close()

    raw = event_log.path.read_text(encoding="utf-8")
    assert "search_place" in raw
    assert "địa chỉ bí mật" not in raw
    assert "provider payload bí mật" not in raw


@pytest.mark.asyncio
async def test_disabled_observability_does_not_create_a_file(tmp_path: Path) -> None:
    event_log = SessionEventLog(
        enabled=False,
        include_transcripts=False,
        directory=tmp_path,
        userdata=_userdata("call-4"),
        room_name="room-4",
    )

    await event_log.start()
    event_log.emit("should_not_exist")
    await event_log.close()

    assert not event_log.path.exists()
