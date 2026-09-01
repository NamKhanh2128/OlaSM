"""Privacy-safe OpenTelemetry export to Langfuse.

The module owns one tracer provider per process. It deliberately avoids the
legacy Langfuse SDK so backend and LiveKit spans share the same OpenTelemetry
context and dependency contract.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from typing import Any

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode

logger = logging.getLogger(__name__)

_provider: TracerProvider | None = None
_initialized = False
_initialization_lock = Lock()
_correlation_attributes: ContextVar[dict[str, str]] = ContextVar(
    "langfuse_correlation_attributes",
    default={},
)


class _CorrelationSpanProcessor(SpanProcessor):
    """Copy per-job privacy-safe correlation fields onto every new span."""

    def on_start(self, span: Any, parent_context: Any | None = None) -> None:
        del parent_context
        for key, value in _correlation_attributes.get().items():
            span.set_attribute(key, value)

    def on_end(self, span: Any) -> None:
        del span

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        del timeout_millis
        return True


@dataclass(frozen=True)
class LangfuseTracingConfig:
    """Credential-safe values required to create one OTLP exporter."""

    enabled: bool
    public_key: str
    secret_key: str
    host: str
    environment: str
    service_name: str


def privacy_hash(value: str | None, *, length: int = 16) -> str | None:
    """Return a stable correlation key without exposing the source value."""

    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def privacy_fingerprint(value: str | None) -> str:
    """Represent potentially sensitive content using only length and digest."""

    text = value or ""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]};length:{len(text)}"


def _otlp_endpoint(host: str) -> str:
    return f"{host.rstrip('/')}/api/public/otel/v1/traces"


def _otlp_headers(public_key: str, secret_key: str) -> dict[str, str]:
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode("ascii")
    return {
        "Authorization": f"Basic {auth}",
        "x-langfuse-ingestion-version": "4",
    }


def configure_langfuse_tracing(config: LangfuseTracingConfig) -> TracerProvider | None:
    """Initialize one non-blocking OTLP exporter, or remain a safe no-op."""

    global _initialized, _provider
    with _initialization_lock:
        if _initialized:
            return _provider
        _initialized = True
        if not config.enabled:
            return None
        if not config.public_key.strip() or not config.secret_key.strip():
            logger.warning("Langfuse tracing disabled: missing credentials")
            return None
        if not config.host.startswith(("https://", "http://")):
            logger.warning("Langfuse tracing disabled: invalid host")
            return None

        try:
            exporter = OTLPSpanExporter(
                endpoint=_otlp_endpoint(config.host),
                headers=_otlp_headers(config.public_key, config.secret_key),
            )
            provider = TracerProvider(
                resource=Resource.create(
                    {
                        "service.name": config.service_name,
                        "deployment.environment.name": config.environment,
                    }
                )
            )
            provider.add_span_processor(_CorrelationSpanProcessor())
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _provider = provider
            logger.info(
                "Langfuse OTLP tracing ready service=%s environment=%s",
                config.service_name,
                config.environment,
            )
        except Exception as exc:
            logger.warning("Langfuse tracing initialization failed error_type=%s", type(exc).__name__)
            _provider = None
        return _provider


def get_langfuse_tracer(name: str = "alosm") -> Any | None:
    provider = _provider
    return provider.get_tracer(name) if provider is not None else None


def get_langfuse_provider() -> TracerProvider | None:
    return _provider


def activate_langfuse_context(
    *,
    session_id: str | None,
    user_id: str | None,
    call_id: str | None,
) -> None:
    """Bind one LiveKit job's hashed identifiers to its async task context."""

    attributes: dict[str, str] = {}
    if session_hash := privacy_hash(session_id):
        attributes["langfuse.session.id"] = session_hash
    if user_hash := privacy_hash(user_id):
        attributes["langfuse.user.id"] = user_hash
    if call_hash := privacy_hash(call_id):
        attributes["langfuse.trace.metadata.call_id"] = call_hash
    _correlation_attributes.set(attributes)


def record_langfuse_observation(
    *,
    name: str,
    observation_type: str,
    model: str | None = None,
    provider: str | None = None,
    usage_details: dict[str, int | float] | None = None,
    attributes: dict[str, str | bool | int | float] | None = None,
    end_timestamp: float | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Export one allowlisted metric observation without any content payload."""

    tracer = get_langfuse_tracer("alosm.livekit.metrics")
    if tracer is None:
        return
    span_attributes: dict[str, str | bool | int | float] = {
        "langfuse.trace.name": name,
        "langfuse.observation.type": observation_type,
    }
    if model:
        span_attributes["langfuse.observation.model.name"] = model
        span_attributes["gen_ai.request.model"] = model
    if provider:
        span_attributes["gen_ai.provider.name"] = provider
        span_attributes["langfuse.observation.metadata.provider"] = provider
    if usage_details:
        safe_usage = {
            key: value
            for key, value in usage_details.items()
            if isinstance(value, int | float) and value >= 0
        }
        if safe_usage:
            span_attributes["langfuse.observation.usage_details"] = json.dumps(
                safe_usage,
                separators=(",", ":"),
            )
            if input_tokens := safe_usage.get("input"):
                span_attributes["gen_ai.usage.input_tokens"] = input_tokens
            if output_tokens := safe_usage.get("output"):
                span_attributes["gen_ai.usage.output_tokens"] = output_tokens
    if attributes:
        span_attributes.update(
            {
                f"langfuse.observation.metadata.{key}": value
                for key, value in attributes.items()
                if isinstance(value, str | bool | int | float)
            }
        )

    end_time_ns = int(end_timestamp * 1_000_000_000) if end_timestamp is not None else None
    start_time_ns = (
        int(max(0.0, end_timestamp - max(duration_seconds or 0.0, 0.0)) * 1_000_000_000)
        if end_timestamp is not None
        else None
    )
    try:
        span = tracer.start_span(name, attributes=span_attributes, start_time=start_time_ns)
        span.end(end_time=end_time_ns)
    except Exception as exc:
        logger.warning("Langfuse metric observation skipped error_type=%s", type(exc).__name__)


@dataclass
class LangfuseGeneration:
    """Small OTEL generation adapter with an explicitly privacy-safe surface."""

    span: Span

    def set_usage(self, usage: Any) -> None:
        try:
            payload = usage if isinstance(usage, dict) else getattr(usage, "model_dump", lambda: {})()
            if not isinstance(payload, dict):
                return
            input_tokens = payload.get("prompt_tokens", payload.get("input_tokens"))
            output_tokens = payload.get("completion_tokens", payload.get("output_tokens"))
            total_tokens = payload.get("total_tokens")
            details = {
                key: int(value)
                for key, value in {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                }.items()
                if isinstance(value, int | float) and value >= 0
            }
            if not details:
                return
            self.span.set_attribute(
                "langfuse.observation.usage_details",
                json.dumps(details, separators=(",", ":")),
            )
            if "input" in details:
                self.span.set_attribute("gen_ai.usage.input_tokens", details["input"])
            if "output" in details:
                self.span.set_attribute("gen_ai.usage.output_tokens", details["output"])
        except Exception as exc:
            logger.warning("Langfuse usage mapping skipped error_type=%s", type(exc).__name__)

    def set_output(self, value: str | None, *, outcome: str, tool_name: str | None = None) -> None:
        self.span.set_attribute(
            "langfuse.observation.output",
            json.dumps({"fingerprint": privacy_fingerprint(value)}, separators=(",", ":")),
        )
        self.span.set_attribute("langfuse.observation.metadata.outcome", outcome)
        if tool_name:
            self.span.set_attribute("langfuse.observation.metadata.tool_name", tool_name)

    def set_error(self, error: BaseException) -> None:
        error_type = type(error).__name__
        self.span.set_attribute("langfuse.observation.level", "ERROR")
        self.span.set_attribute("langfuse.observation.status_message", error_type)
        self.span.set_attribute("langfuse.observation.metadata.error_type", error_type)
        self.span.set_status(Status(StatusCode.ERROR, error_type))


@contextmanager
def langfuse_generation(
    *,
    name: str,
    model: str,
    session_id: str | None = None,
    user_id: str | None = None,
    turn_id: str | None = None,
    prompt_preview: str = "",
) -> Iterator[LangfuseGeneration | None]:
    """Trace the real provider-call duration and propagate safe correlations."""

    tracer = get_langfuse_tracer("alosm.generations")
    if tracer is None:
        yield None
        return

    attributes: dict[str, str] = {
        "langfuse.trace.name": name,
        "langfuse.observation.type": "generation",
        "langfuse.observation.model.name": model,
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": model,
        "langfuse.observation.input": json.dumps(
            {"fingerprint": privacy_fingerprint(prompt_preview)},
            separators=(",", ":"),
        ),
    }
    if session_hash := privacy_hash(session_id):
        attributes["langfuse.session.id"] = session_hash
    if user_hash := privacy_hash(user_id):
        attributes["langfuse.user.id"] = user_hash
    if turn_hash := privacy_hash(turn_id):
        attributes["langfuse.observation.metadata.turn_id"] = turn_hash

    with tracer.start_as_current_span(name, attributes=attributes, record_exception=False) as span:
        generation = LangfuseGeneration(span)
        try:
            yield generation
        except BaseException as exc:
            generation.set_error(exc)
            raise


def flush_langfuse(timeout_seconds: float = 5.0) -> bool:
    provider = _provider
    if provider is None:
        return True
    try:
        return bool(provider.force_flush(timeout_millis=max(1, int(timeout_seconds * 1000))))
    except Exception as exc:
        logger.warning("Langfuse trace flush failed error_type=%s", type(exc).__name__)
        return False


def shutdown_langfuse(timeout_seconds: float = 5.0) -> None:
    provider = _provider
    if provider is None:
        return
    flush_langfuse(timeout_seconds)
    try:
        provider.shutdown()
    except Exception as exc:
        logger.warning("Langfuse tracer shutdown failed error_type=%s", type(exc).__name__)


def reset_langfuse_for_tests() -> None:
    global _initialized, _provider
    _provider = None
    _initialized = False
