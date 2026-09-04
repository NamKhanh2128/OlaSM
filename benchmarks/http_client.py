"""Shared HTTP client helper for benchmark scripts.

Provides an authenticated httpx.AsyncClient that reuses connections,
a login helper, and a session/message API wrapper so individual
benchmark modules do not duplicate boilerplate.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from benchmarks.config import APIConfig


@dataclass
class AuthTokens:
    access_token: str = ""
    user_id: str = ""
    obtained_at: float = 0.0


@dataclass
class APIResponse:
    """Wrap an httpx response with timing."""

    status_code: int = 0
    body: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    error: str = ""


class BenchmarkHTTPClient:
    """Thin async wrapper around httpx for benchmark use."""

    def __init__(self, config: APIConfig | None = None) -> None:
        self.config = config or APIConfig.from_env()
        self._client: httpx.AsyncClient | None = None
        self._auth: AuthTokens | None = None

    # -- lifecycle ----------------------------------------------------------

    async def __aenter__(self) -> "BenchmarkHTTPClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use 'async with BenchmarkHTTPClient()' to manage the client lifecycle")
        return self._client

    # -- auth ---------------------------------------------------------------

    async def login(self, phone: str | None = None, password: str | None = None) -> AuthTokens:
        """Log in and cache the bearer token."""
        resp = await self._timed_request(
            "POST",
            "/api/v1/auth/login",
            json={
                "phone": phone or self.config.demo_phone,
                "password": password or self.config.demo_password,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Login failed: {resp.status_code} — {resp.body}")
        self._auth = AuthTokens(
            access_token=resp.body.get("access_token", ""),
            user_id=resp.body.get("user_id", resp.body.get("id", "")),
            obtained_at=time.time(),
        )
        return self._auth

    @property
    def auth_headers(self) -> dict[str, str]:
        if not self._auth:
            raise RuntimeError("Call login() first")
        return {"Authorization": f"Bearer {self._auth.access_token}"}

    # -- session / message helpers -----------------------------------------

    async def create_session(self) -> str:
        """Create a new chat session and return its ID."""
        resp = await self._timed_request(
            "POST",
            "/api/v1/sessions",
            headers=self.auth_headers,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Create session failed: {resp.status_code} — {resp.body}")
        return resp.body.get("session_id", resp.body.get("id", ""))

    async def send_message(
        self,
        session_id: str,
        message: str,
        source: str = "TEXT",
    ) -> APIResponse:
        """Send a text message and return the full response with timing."""
        return await self._timed_request(
            "POST",
            f"/api/v1/sessions/{session_id}/messages",
            headers=self.auth_headers,
            json={"message": message, "source": source},
        )

    async def get_bookings(self) -> APIResponse:
        return await self._timed_request("GET", "/api/v1/bookings", headers=self.auth_headers)

    async def get_booking(self, booking_id: str) -> APIResponse:
        return await self._timed_request("GET", f"/api/v1/bookings/{booking_id}", headers=self.auth_headers)

    async def get_trips(self) -> APIResponse:
        return await self._timed_request("GET", "/api/v1/trips", headers=self.auth_headers)

    async def get_handoffs(self) -> APIResponse:
        return await self._timed_request("GET", "/api/v1/handoffs", headers=self.auth_headers)

    async def health_check(self) -> APIResponse:
        return await self._timed_request("GET", "/api/v1/health")

    # -- generic request with timing ----------------------------------------

    async def _timed_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: Any = None,
    ) -> APIResponse:
        t0 = time.perf_counter()
        try:
            resp = await self.client.request(method, url, headers=headers, json=json, content=data)
            elapsed = (time.perf_counter() - t0) * 1000
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:2000]}
            return APIResponse(status_code=resp.status_code, body=body, elapsed_ms=elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            return APIResponse(status_code=0, error=str(exc), elapsed_ms=elapsed)

    async def timed_get(self, url: str) -> APIResponse:
        return await self._timed_request("GET", url, headers=self.auth_headers)

    async def timed_post(self, url: str, *, json: dict[str, Any] | None = None) -> APIResponse:
        return await self._timed_request("POST", url, headers=self.auth_headers, json=json)
