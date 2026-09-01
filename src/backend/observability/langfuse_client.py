"""Langfuse client singleton — no-op when disabled or misconfigured."""

from __future__ import annotations

import hashlib
import logging
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_client: Any | None = None
_initialized = False


def _redact(text: str, limit: int = 200) -> str:
    if not text:
        return ""
    truncated = text[:limit]
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    return f"{truncated} [hash:{digest} redacted:{len(text) > limit}]"


def get_langfuse() -> Any | None:
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    try:
        from src.backend.config import get_settings

        settings = get_settings()
        if not settings.langfuse_enabled:
            return None
        if not settings.langfuse_secret_key or not settings.langfuse_public_key:
            logger.info("langfuse disabled: missing keys")
            return None
        from langfuse import Langfuse

        _client = Langfuse(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_host,
        )
        try:
            _client.auth_check()
        except Exception as exc:
            logger.warning("langfuse auth_check failed: %s", exc)
        return _client
    except Exception as exc:
        logger.warning("langfuse init failed: %s", exc)
        return None


def flush_langfuse() -> None:
    client = _client
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:
        logger.warning("langfuse flush failed: %s", exc)


def reset_langfuse_for_tests() -> None:
    global _client, _initialized
    _client = None
    _initialized = False


@contextmanager
def langfuse_generation(
    *,
    name: str,
    model: str,
    session_id: str | None = None,
    user_id: str | None = None,
    turn_id: str | None = None,
    prompt_preview: str = "",
):
    client = get_langfuse()
    if client is None:
        yield None
        return
    trace = None
    generation = None
    start = time.perf_counter()
    try:
        trace_kwargs: dict[str, Any] = {"name": name}
        if session_id:
            trace_kwargs["session_id"] = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        if user_id:
            trace_kwargs["user_id"] = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        if turn_id:
            trace_kwargs["id"] = hashlib.sha256(turn_id.encode()).hexdigest()[:16]
        trace = client.trace(**trace_kwargs)
        generation = trace.generation(
            name=name,
            model=model,
            input=_redact(prompt_preview),
            metadata={"turn_id": turn_id} if turn_id else {},
        )
        yield generation
        latency_ms = (time.perf_counter() - start) * 1000
        if generation is not None:
            try:
                generation.update(metadata={"latency_ms": round(latency_ms, 2)})
            except Exception:
                pass
    except Exception as exc:
        logger.warning("langfuse_generation failed: %s", exc)
        yield None
    finally:
        try:
            if generation is not None:
                generation.end()
        except Exception:
            pass
