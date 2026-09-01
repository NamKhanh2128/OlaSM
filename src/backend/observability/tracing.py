"""Request tracing helpers — Server-Timing + X-Request-Id."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id  # type: ignore[attr-defined]
        request.state.timings = {}  # type: ignore[attr-defined]
        request.state._t0 = start  # type: ignore[attr-defined]
        response: Response = await call_next(request)
        total_ms = (time.perf_counter() - start) * 1000
        timings: dict[str, float] = getattr(request.state, "timings", {})  # type: ignore[attr-defined]
        parts = [f"total;dur={total_ms:.2f}"]
        for key, val in timings.items():
            parts.append(f"{key};dur={val:.2f}")
        response.headers["X-Request-Id"] = request_id
        response.headers["Server-Timing"] = ", ".join(parts)
        return response


@contextmanager
def trace_span(request: Request | None, name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        if request is not None and hasattr(request.state, "timings"):
            dur = (time.perf_counter() - start) * 1000
            request.state.timings[name] = dur  # type: ignore[attr-defined]


def record_timing(request: Request | None, name: str, duration_ms: float) -> None:
    if request is not None and hasattr(request.state, "timings"):
        request.state.timings[name] = duration_ms  # type: ignore[attr-defined]
