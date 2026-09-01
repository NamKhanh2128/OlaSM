import json
from types import SimpleNamespace

import pytest
from livekit.agents.metrics import LLMMetrics, STTMetrics, TTSMetrics
from livekit.agents.metrics.base import Metadata
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

import src.backend.observability.langfuse_client as langfuse_module
from src.backend.observability.langfuse_client import (
    LangfuseTracingConfig,
    configure_langfuse_tracing,
    langfuse_generation,
    privacy_fingerprint,
    privacy_hash,
    record_langfuse_observation,
)
from src.voice_agent.observability import LiveKitSessionObserver, SessionEventLog
from src.voice_agent.session_data import AloSMSessionData


@pytest.fixture
def span_exporter(monkeypatch: pytest.MonkeyPatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(langfuse_module, "_provider", provider)
    monkeypatch.setattr(langfuse_module, "_initialized", True)
    langfuse_module._correlation_attributes.set({})
    yield exporter
    provider.shutdown()


def _userdata() -> AloSMSessionData:
    return AloSMSessionData(
        app_session_id="private-session",
        call_id="private-call",
        user_id="private-user",
        participant_identity="participant",
    )


def test_disabled_or_incomplete_configuration_remains_noop() -> None:
    langfuse_module.reset_langfuse_for_tests()
    disabled = LangfuseTracingConfig(False, "", "", "https://cloud.langfuse.com", "test", "service")
    assert configure_langfuse_tracing(disabled) is None

    langfuse_module.reset_langfuse_for_tests()
    missing_key = LangfuseTracingConfig(True, "pk", "", "https://cloud.langfuse.com", "test", "service")
    assert configure_langfuse_tracing(missing_key) is None
    langfuse_module.reset_langfuse_for_tests()


def test_generation_records_usage_duration_error_and_no_plaintext(span_exporter: InMemorySpanExporter) -> None:
    secret_prompt = "đón tôi tại địa chỉ bí mật"
    secret_output = "nội dung trả lời riêng tư"
    with langfuse_generation(
        name="agent_llm_decide",
        model="gpt-test",
        session_id="session-raw",
        user_id="user-raw",
        turn_id="turn-raw",
        prompt_preview=secret_prompt,
    ) as generation:
        assert generation is not None
        generation.set_usage(SimpleNamespace(model_dump=lambda: {"prompt_tokens": 12, "completion_tokens": 4}))
        generation.set_output(secret_output, outcome="message")

    with pytest.raises(RuntimeError, match="provider failed"):
        with langfuse_generation(name="transcript_rewrite", model="gpt-test"):
            raise RuntimeError("provider failed with private payload")

    spans = span_exporter.get_finished_spans()
    success = next(span for span in spans if span.name == "agent_llm_decide")
    failed = next(span for span in spans if span.name == "transcript_rewrite")
    attributes = dict(success.attributes or {})
    serialized = json.dumps(attributes, ensure_ascii=False)

    assert secret_prompt not in serialized
    assert secret_output not in serialized
    assert "session-raw" not in serialized
    assert attributes["langfuse.session.id"] == privacy_hash("session-raw")
    assert json.loads(attributes["langfuse.observation.usage_details"]) == {"input": 12, "output": 4}
    assert success.end_time is not None and success.start_time is not None and success.end_time >= success.start_time
    assert failed.status.status_code is StatusCode.ERROR
    assert failed.attributes["langfuse.observation.metadata.error_type"] == "RuntimeError"


def test_explicit_metric_duration_and_correlation_are_preserved(span_exporter: InMemorySpanExporter) -> None:
    record_langfuse_observation(
        name="livekit_llm",
        observation_type="generation",
        model="model-a",
        provider="provider-a",
        usage_details={"input": 15, "output": 5},
        attributes={"ttft_ms": 250.0},
        end_timestamp=100.0,
        duration_seconds=1.25,
        session_id="session-raw",
        user_id="user-raw",
        call_id="call-raw",
    )

    span = span_exporter.get_finished_spans()[0]
    attributes = dict(span.attributes or {})
    assert span.end_time - span.start_time == 1_250_000_000
    assert attributes["langfuse.session.id"] == privacy_hash("session-raw")
    assert attributes["langfuse.user.id"] == privacy_hash("user-raw")
    assert attributes["langfuse.trace.metadata.call_id"] == privacy_hash("call-raw")
    assert attributes["gen_ai.usage.input_tokens"] == 15
    assert attributes["gen_ai.usage.output_tokens"] == 5


def test_livekit_metrics_export_allowlist_without_transcript(
    span_exporter: InMemorySpanExporter,
    tmp_path,
) -> None:
    event_log = SessionEventLog(
        enabled=False,
        include_transcripts=True,
        directory=tmp_path,
        userdata=_userdata(),
        room_name="room-private",
    )
    observer = LiveKitSessionObserver(event_log)
    metadata = Metadata(model_name="model-a", model_provider="provider-a")

    observer.record_model_metrics(
        LLMMetrics(
            label="llm",
            request_id="request-private",
            timestamp=100.0,
            duration=1.0,
            ttft=0.2,
            cancelled=False,
            completion_tokens=4,
            prompt_tokens=12,
            prompt_cached_tokens=2,
            total_tokens=16,
            tokens_per_second=4.0,
            metadata=metadata,
        )
    )
    observer.record_model_metrics(
        STTMetrics(
            label="stt",
            request_id="request-private",
            timestamp=101.0,
            duration=0.8,
            audio_duration=2.5,
            input_tokens=0,
            output_tokens=0,
            streamed=True,
            metadata=metadata,
        )
    )
    observer.record_model_metrics(
        TTSMetrics(
            label="tts",
            request_id="request-private",
            timestamp=102.0,
            duration=0.6,
            ttfb=0.15,
            audio_duration=1.8,
            cancelled=False,
            characters_count=42,
            input_tokens=0,
            output_tokens=0,
            streamed=True,
            metadata=metadata,
        )
    )
    observer._record_safe_event(
        "conversation_item_added",
        {
            "text": "transcript tuyệt mật không được export",
            "metrics": {"llm_node_ttft": 0.2, "e2e_latency": 1.8},
        },
        created_at=103.0,
    )

    spans = span_exporter.get_finished_spans()
    assert {span.name for span in spans} == {
        "livekit_llm",
        "livekit_stt",
        "livekit_tts",
        "livekit_turn_latency",
    }
    serialized = json.dumps([dict(span.attributes or {}) for span in spans], ensure_ascii=False)
    assert "transcript tuyệt mật" not in serialized
    assert "request-private" not in serialized
    assert "private-session" not in serialized
    assert privacy_fingerprint("transcript tuyệt mật") != "transcript tuyệt mật"
    llm_span = next(span for span in spans if span.name == "livekit_llm")
    assert json.loads(llm_span.attributes["langfuse.observation.usage_details"]) == {
        "input": 10,
        "cache_read_input_tokens": 2,
        "output": 4,
        "total": 16,
    }
