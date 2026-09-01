"""Privacy-safe OpenTelemetry export to Langfuse.

The module owns one tracer provider per process. It deliberately avoids the
legacy Langfuse SDK so backend and LiveKit spans share the same OpenTelemetry
context and dependency contract.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass
from threading import Lock
from typing import Any

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_provider: TracerProvider | None = None
_initialized = False
_initialization_lock = Lock()


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


def get_langfuse() -> None:
    """Temporary compatibility shim for the pre-OTLP Core Agent wrapper."""

    return None


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
