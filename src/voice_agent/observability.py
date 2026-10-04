"""Privacy-gated JSONL observability for one native LiveKit AgentSession."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from livekit.agents import AgentSession, llm
from livekit.agents.metrics import LLMMetrics, RealtimeModelMetrics, STTMetrics, TTSMetrics, VADMetrics
from pydantic import BaseModel

from src.voice_agent.session_data import AloSMSessionData, OlaSMSessionData

logger = logging.getLogger(__name__)

_EVENT_NAMES = (
    "user_state_changed",
    "agent_state_changed",
    "user_input_transcribed",
    "user_transcription_timeout",
    "conversation_item_added",
    "agent_false_interruption",
    "overlapping_speech",
    "function_tools_executed",
    "session_usage_updated",
    "speech_created",
    "tool_execution_updated",
    "error",
    "close",
)
_SAFE_METRIC_FIELDS = (
    "started_speaking_at",
    "stopped_speaking_at",
    "transcription_delay",
    "end_of_turn_delay",
    "on_user_turn_completed_delay",
    "llm_node_ttft",
    "tts_node_ttfb",
    "playback_latency",
    "e2e_latency",
)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return (cleaned or "unknown-call")[:96]


def _iso_timestamp(epoch_seconds: float | None = None) -> str:
    timestamp = epoch_seconds if epoch_seconds is not None else time.time()
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat(timespec="milliseconds")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return str(value)


def _safe_metrics(metrics: dict[str, Any]) -> dict[str, object]:
    return {field: _json_safe(metrics[field]) for field in _SAFE_METRIC_FIELDS if metrics.get(field) is not None}


_MAX_DEBUG_TOOL_TEXT = 500


def _debug_text(value: str) -> str:
    """Keep diagnostic payloads readable without dropping the call signal."""

    compact = " ".join(value.split())
    return compact if len(compact) <= _MAX_DEBUG_TOOL_TEXT else compact[:_MAX_DEBUG_TOOL_TEXT] + "…"


def _tool_argument_keys(arguments: object) -> tuple[str, ...]:
    """Expose only parameter names; tool values can contain customer data."""

    if not isinstance(arguments, str):
        return ()
    try:
        decoded = json.loads(arguments)
    except json.JSONDecodeError:
        return ("invalid_json",)
    if not isinstance(decoded, dict):
        return ("non_object",)
    return tuple(sorted(str(key) for key in decoded))


def _console_message(event_name: str, payload: dict[str, Any]) -> str:
    """Format the few call-path events an operator needs on the terminal."""

    if event_name == "user_input_transcribed":
        stage = "final" if payload.get("is_final") else "partial"
        language = payload.get("language") or "unknown"
        text = payload.get("transcript")
        detail = f" text={text!r}" if isinstance(text, str) else f" chars={payload.get('transcript_length', 0)}"
        return f"USER ASR {stage} lang={language}{detail}"

    if event_name == "tool_execution_updated":
        status = payload.get("status") or "unknown"
        tool_name = payload.get("tool_name") or "unknown"
        parts = [f"TOOL {status}", f"name={tool_name}"]
        if call_id := payload.get("call_id"):
            parts.append(f"call_id={call_id}")
        if trigger_transcript := payload.get("trigger_transcript"):
            parts.append(f"trigger={trigger_transcript!r}")
        if arguments := payload.get("arguments"):
            parts.append(f"input={arguments!r}")
        elif argument_keys := payload.get("argument_keys"):
            argument_names = ",".join(str(key) for key in argument_keys)
            parts.append(f"args={argument_names}")
        if (duration_ms := payload.get("duration_ms")) is not None:
            parts.append(f"duration_ms={duration_ms}")
        if result := payload.get("result"):
            parts.append(f"result={result!r}")
        elif message_length := payload.get("message_length"):
            parts.append(f"message_chars={message_length}")
        return " ".join(parts)

    if event_name == "conversation_item_added" and payload.get("role") == "user":
        text = payload.get("text")
        detail = f" transcript={text!r}" if isinstance(text, str) else f" chars={payload.get('text_length', 0)}"
        confidence = payload.get("transcript_confidence")
        confidence_detail = f" confidence={confidence}" if confidence is not None else ""
        return f"USER TURN{detail}{confidence_detail}"

    if event_name == "conversation_item_added" and payload.get("role") == "assistant":
        text = payload.get("text")
        detail = f" text={text!r}" if isinstance(text, str) else f" chars={payload.get('text_length', 0)}"
        return f"BOT LLM response{detail}"

    if event_name == "user_transcription_timeout":
        return f"ASR timeout speech_duration={payload.get('speech_duration')}"

    if event_name == "error":
        return (
            f"ERROR source={payload.get('source_type') or 'unknown'} "
            f"provider={payload.get('provider') or 'unknown'} "
            f"model={payload.get('model') or 'unknown'} "
            f"type={payload.get('error_type') or 'unknown'}"
        )

    if event_name == "speech_created":
        source = payload.get("source") or "unknown"
        speech_id = payload.get("speech_id") or "unknown"
        return f"BOT TTS queued source={source} speech_id={speech_id}"

    if event_name == "tts_audio_played":
        return (
            f"BOT TTS played speech_id={payload.get('speech_id') or 'unknown'} "
            f"provider={payload.get('provider') or 'unknown'} "
            f"model={payload.get('model') or 'unknown'} "
            f"voice={payload.get('voice') or 'unknown'} "
            f"ttfb_ms={payload.get('ttfb_ms')} "
            f"audio_ms={payload.get('audio_duration_ms')}"
        )

    if event_name == "room_audio_track":
        return (
            f"AUDIO {payload.get('action') or 'unknown'} "
            f"direction={payload.get('direction') or 'unknown'} "
            f"owner={payload.get('owner_identity') or 'unknown'} "
            f"track={payload.get('track_sid') or 'unknown'} "
            f"name={payload.get('track_name') or 'unknown'}"
        )

    terminal_fields = []
    for key in ("old_state", "new_state", "is_final", "role", "status", "resumed"):
        if key in payload:
            terminal_fields.append(f"{key}={payload[key]}")
    if isinstance(payload.get("transcript"), str):
        terminal_fields.append(f"transcript={payload['transcript']!r}")
    suffix = " " + " ".join(terminal_fields) if terminal_fields else ""
    return f"{event_name}{suffix}"


def _should_log_to_console(event_name: str, payload: dict[str, Any]) -> bool:
    return (
        (event_name == "user_input_transcribed" and payload.get("is_final") is True)
        or (
            event_name == "tool_execution_updated"
            and payload.get("update_type") in {"tool_call_started", "tool_call_updated", "tool_call_ended"}
        )
        or event_name
        in {
            "speech_created",
            "tts_audio_played",
            "room_audio_track",
            "error",
            "user_transcription_timeout",
        }
        or (event_name == "conversation_item_added" and payload.get("role") in {"user", "assistant"})
    )


class SessionEventLog:
    """Append crash-tolerant JSON lines without changing the media pipeline."""

    def __init__(
        self,
        *,
        enabled: bool,
        include_transcripts: bool,
        directory: Path,
        userdata: OlaSMSessionData,
        room_name: str,
    ) -> None:
        self.enabled = enabled
        self.include_transcripts = include_transcripts
        self.directory = directory
        self.userdata = userdata
        self.room_name = room_name
        self.path = directory / f"{_safe_filename(userdata.call_id)}.jsonl"
        self._started_monotonic = time.monotonic()
        self._queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=1000)
        self._writer_task: asyncio.Task[None] | None = None
        self._accepting = False

    async def start(self) -> None:
        if not self.enabled or self._writer_task is not None:
            return
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._accepting = True
            self._writer_task = asyncio.create_task(
                self._write_loop(),
                name=f"livekit-jsonl-{_safe_filename(self.userdata.call_id)}",
            )
            self.emit(
                "event_log_started",
                include_transcripts=self.include_transcripts,
                log_path=str(self.path),
            )
        except Exception:
            self._accepting = False
            self.enabled = False
            logger.exception("failed to start LiveKit JSONL event log")

    def emit(
        self,
        event_name: str,
        *,
        event_created_at: float | None = None,
        **fields: object,
    ) -> None:
        if not self.enabled or not self._accepting:
            return
        payload = {
            "schema_version": "1",
            "timestamp": _iso_timestamp(event_created_at),
            "elapsed_ms": round((time.monotonic() - self._started_monotonic) * 1000, 3),
            "event": event_name,
            "app_session_id": self.userdata.app_session_id,
            "call_id": self.userdata.call_id,
            "room_name": self.room_name,
            **{key: _json_safe(value) for key, value in fields.items()},
        }
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        try:
            self._queue.put_nowait(line)
        except asyncio.QueueFull:
            logger.warning("LiveKit JSONL event queue full", extra={"call_id": self.userdata.call_id})
            return

        if not _should_log_to_console(event_name, payload):
            return

        console_message = _console_message(event_name, payload)
        console_level = logging.WARNING if event_name in {"error", "user_transcription_timeout"} else logging.INFO
        logger.log(console_level, "[voice:%s] %s", self.userdata.call_id, console_message)

    async def close(self, reason: str = "") -> None:
        if not self.enabled or self._writer_task is None or not self._accepting:
            return
        self.emit("event_log_stopping", reason=reason or None)
        self._accepting = False
        await self._queue.put(None)
        try:
            await self._writer_task
        finally:
            self._writer_task = None

    async def _write_loop(self) -> None:
        try:
            with self.path.open("a", encoding="utf-8", buffering=1) as stream:
                while True:
                    line = await self._queue.get()
                    if line is None:
                        return
                    stream.write(line + "\n")
                    stream.flush()
        except Exception:
            logger.exception("LiveKit JSONL event writer failed", extra={"path": str(self.path)})


class LiveKitSessionObserver:
    """Translate public LiveKit session events into a stable, redacted schema."""

    def __init__(
        self,
        event_log: SessionEventLog,
        *,
        tts_voices: dict[str, str] | None = None,
    ) -> None:
        self.event_log = event_log
        self._tts_voices = tts_voices or {}
        self._tool_started_at: dict[str, float] = {}
        self._tool_names: dict[str, str] = {}
        self._last_user_transcript: str | None = None

    def register(self, session: AgentSession[OlaSMSessionData]) -> None:
        for event_name in _EVENT_NAMES:
            session.on(event_name, self.record)
        for model in (session.stt, session.llm, session.tts, session.vad):
            if model is not None:
                model.on("metrics_collected", self.record_model_metrics)

    def record(self, event: Any) -> None:
        event_name = str(getattr(event, "type", type(event).__name__))
        created_at = getattr(event, "created_at", None)
        fields = self._event_fields(event_name, event)
        self.event_log.emit(event_name, event_created_at=created_at, **fields)
        self._record_safe_event(event_name, fields, created_at=created_at)

    def _record_observation(self, **kwargs: Any) -> None:
        from src.backend.observability.langfuse_client import record_langfuse_observation

        record_langfuse_observation(
            **kwargs,
            session_id=self.event_log.userdata.app_session_id,
            user_id=self.event_log.userdata.user_id,
            call_id=self.event_log.userdata.call_id,
        )

    def record_model_metrics(self, metrics: object) -> None:
        """Export only numeric/provider metadata from LiveKit model metrics."""

        if isinstance(metrics, TTSMetrics):
            self.record_tts_metrics(metrics)
            return

        metadata = getattr(metrics, "metadata", None)
        model = metadata.model_name if metadata is not None else None
        provider = metadata.model_provider if metadata is not None else None
        if isinstance(metrics, LLMMetrics):
            usage = {
                "input": max(metrics.prompt_tokens - metrics.prompt_cached_tokens, 0),
                "cache_read_input_tokens": metrics.prompt_cached_tokens,
                "output": metrics.completion_tokens,
                "total": metrics.total_tokens,
            }
            attributes = {
                "duration_ms": round(metrics.duration * 1000, 3),
                "ttft_ms": round(metrics.ttft * 1000, 3),
                "cancelled": metrics.cancelled,
                "tokens_per_second": metrics.tokens_per_second,
                "label": metrics.label,
            }
            event_name = "livekit_llm"
        elif isinstance(metrics, RealtimeModelMetrics):
            usage = {
                "input": metrics.input_tokens,
                "output": metrics.output_tokens,
                "total": metrics.total_tokens,
            }
            attributes = {
                "duration_ms": round(metrics.duration * 1000, 3),
                "session_duration_ms": round(metrics.session_duration * 1000, 3),
                "ttft_ms": round(metrics.ttft * 1000, 3),
                "cancelled": metrics.cancelled,
                "tokens_per_second": metrics.tokens_per_second,
                "label": metrics.label,
            }
            event_name = "livekit_realtime_model"
        elif isinstance(metrics, STTMetrics):
            usage = {
                "audio_seconds": metrics.audio_duration,
                "input": metrics.input_tokens,
                "output": metrics.output_tokens,
            }
            attributes = {
                "duration_ms": round(metrics.duration * 1000, 3),
                "audio_duration_ms": round(metrics.audio_duration * 1000, 3),
                "streamed": metrics.streamed,
                "connection_reused": metrics.connection_reused,
                "label": metrics.label,
            }
            event_name = "livekit_stt"
        elif isinstance(metrics, VADMetrics):
            self._record_observation(
                name="livekit_vad",
                observation_type="span",
                attributes={
                    "idle_time_ms": round(metrics.idle_time * 1000, 3),
                    "inference_duration_ms": round(metrics.inference_duration_total * 1000, 3),
                    "inference_count": metrics.inference_count,
                    "label": metrics.label,
                },
                end_timestamp=metrics.timestamp,
                duration_seconds=metrics.inference_duration_total,
            )
            return
        else:
            return

        self._record_observation(
            name=event_name,
            observation_type="generation",
            model=model,
            provider=provider,
            usage_details=usage,
            attributes=attributes,
            end_timestamp=metrics.timestamp,
            duration_seconds=metrics.duration,
        )

    def record_tts_metrics(self, metrics: TTSMetrics) -> None:
        metadata = metrics.metadata
        model = metadata.model_name if metadata is not None else None
        self.event_log.emit(
            "tts_audio_played",
            event_created_at=metrics.timestamp,
            speech_id=metrics.speech_id,
            provider=metadata.model_provider if metadata is not None else None,
            model=model,
            voice=self._tts_voices.get(model or ""),
            ttfb_ms=round(metrics.ttfb * 1000, 3),
            audio_duration_ms=round(metrics.audio_duration * 1000, 3),
            characters_count=metrics.characters_count,
            cancelled=metrics.cancelled,
        )
        metadata = metrics.metadata
        self._record_observation(
            name="livekit_tts",
            observation_type="generation",
            model=metadata.model_name if metadata is not None else None,
            provider=metadata.model_provider if metadata is not None else None,
            usage_details={
                "characters": metrics.characters_count,
                "audio_seconds": metrics.audio_duration,
                "input": metrics.input_tokens,
                "output": metrics.output_tokens,
            },
            attributes={
                "duration_ms": round(metrics.duration * 1000, 3),
                "ttfb_ms": round(metrics.ttfb * 1000, 3),
                "audio_duration_ms": round(metrics.audio_duration * 1000, 3),
                "cancelled": metrics.cancelled,
                "streamed": metrics.streamed,
                "label": metrics.label,
            },
            end_timestamp=metrics.timestamp,
            duration_seconds=metrics.duration,
        )

    def _record_safe_event(self, event_name: str, fields: dict[str, object], *, created_at: float | None) -> None:
        if event_name == "conversation_item_added":
            raw_metrics = fields.get("metrics")
            if not isinstance(raw_metrics, dict) or not raw_metrics:
                return
            metrics = {
                key: round(float(value) * 1000, 3)
                for key, value in raw_metrics.items()
                if key in _SAFE_METRIC_FIELDS and isinstance(value, int | float)
            }
            if metrics:
                self._record_observation(
                    name="livekit_turn_latency",
                    observation_type="span",
                    attributes=metrics,
                    end_timestamp=created_at,
                    duration_seconds=max(metrics.values()) / 1000,
                )
            return

        if event_name == "tool_execution_updated" and fields.get("duration_ms") is not None:
            duration_ms = float(fields["duration_ms"])
            self._record_observation(
                name="livekit_tool",
                observation_type="tool",
                attributes={
                    "duration_ms": duration_ms,
                    "tool_name": str(fields.get("tool_name") or "unknown"),
                    "status": str(fields.get("status") or "unknown"),
                },
                end_timestamp=created_at,
                duration_seconds=duration_ms / 1000,
            )
            return

        if event_name in {"error", "user_transcription_timeout"}:
            self._record_observation(
                name=f"livekit_{event_name}",
                observation_type="event",
                attributes={
                    key: value
                    for key, value in fields.items()
                    if key in {"provider", "model", "error_type", "speech_duration"}
                    and isinstance(value, str | int | float | bool)
                },
                end_timestamp=created_at,
            )

    def _event_fields(self, event_name: str, event: Any) -> dict[str, object]:
        if event_name in {"agent_state_changed", "user_state_changed"}:
            return {"old_state": event.old_state, "new_state": event.new_state}

        if event_name == "user_input_transcribed":
            if event.is_final:
                self._last_user_transcript = event.transcript
            fields: dict[str, object] = {
                "is_final": event.is_final,
                "item_id": event.item_id,
                "language": event.language,
                "transcript_length": len(event.transcript),
            }
            if self.event_log.include_transcripts:
                fields["transcript"] = event.transcript
            return fields

        if event_name == "user_transcription_timeout":
            return {
                "speech_duration": event.speech_duration,
                "vad_speech_started_at": event.vad_speech_started_at,
            }

        if event_name == "conversation_item_added":
            item = event.item
            if not isinstance(item, llm.ChatMessage):
                return {"item_type": getattr(item, "type", type(item).__name__)}
            text = item.text_content or ""
            fields = {
                "item_type": item.type,
                "item_id": item.id,
                "role": item.role,
                "interrupted": item.interrupted,
                "transcript_confidence": item.transcript_confidence,
                "text_length": len(text),
                "metrics": _safe_metrics(item.metrics),
            }
            if self.event_log.include_transcripts:
                fields["text"] = text
            return fields

        if event_name == "speech_created":
            handle = event.speech_handle
            return {
                "speech_id": handle.id,
                "source": event.source,
                "user_initiated": event.user_initiated,
                "allow_interruptions": handle.allow_interruptions,
            }

        if event_name == "agent_false_interruption":
            return {"resumed": event.resumed}

        if event_name == "overlapping_speech":
            return {
                "is_interruption": event.is_interruption,
                "overlap_started_at": event.overlap_started_at,
                "detection_delay": event.detection_delay,
                "prediction_duration": event.prediction_duration,
                "probability": event.probability,
                "num_requests": event.num_requests,
            }

        if event_name == "tool_execution_updated":
            return self._tool_update_fields(event.update)

        if event_name == "function_tools_executed":
            tools = []
            for call, output in event.zipped():
                tools.append(
                    {
                        "call_id": call.call_id,
                        "name": call.name,
                        "status": "missing_output" if output is None else ("error" if output.is_error else "done"),
                    }
                )
            return {"tools": tools}

        if event_name == "session_usage_updated":
            return {"model_usage": _json_safe(event.usage.model_usage)}

        if event_name == "error":
            source = event.source
            return {
                "source_type": type(source).__name__,
                "provider": getattr(source, "provider", None),
                "model": getattr(source, "model", None),
                "error_type": type(event.error).__name__,
            }

        if event_name == "close":
            return {
                "reason": event.reason,
                "error_type": type(event.error).__name__ if event.error is not None else None,
            }

        return {}

    def _tool_update_fields(self, update: Any) -> dict[str, object]:
        update_type = str(update.type)
        if update_type == "tool_call_started":
            call = update.function_call
            self._tool_started_at[call.call_id] = time.monotonic()
            self._tool_names[call.call_id] = call.name
            fields: dict[str, object] = {
                "update_type": update_type,
                "status": "started",
                "call_id": call.call_id,
                "tool_name": call.name,
                "argument_keys": _tool_argument_keys(call.arguments),
            }
            if self.event_log.include_transcripts:
                fields["trigger_transcript"] = _debug_text(self._last_user_transcript or "") or None
                fields["arguments"] = _debug_text(call.arguments)
            return fields

        call_id = str(getattr(update, "call_id", ""))
        fields: dict[str, object] = {
            "update_type": update_type,
            "status": getattr(update, "status", update_type),
            "call_id": call_id or None,
            "tool_name": self._tool_names.get(call_id),
        }
        if update_type in {"tool_call_updated", "tool_call_ended"}:
            message = getattr(update, "message", None)
            if isinstance(message, str):
                fields["message_length"] = len(message)
                if self.event_log.include_transcripts:
                    fields["result"] = _debug_text(message)
        if update_type == "tool_call_ended" and call_id in self._tool_started_at:
            fields["duration_ms"] = round(
                (time.monotonic() - self._tool_started_at.pop(call_id)) * 1000,
                3,
            )
            self._tool_names.pop(call_id, None)
        if update_type == "tool_reply_updated":
            fields = {
                "update_type": update_type,
                "status": update.status,
                "speech_id": update.speech_id,
                "update_count": len(update.update_ids),
            }
        return fields
