"""Durable business-state boundary for the LiveKit AgentSession."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol

from src.backend.repositories.persistence_repository import PersistenceRepository
from src.voice_agent.session_data import AloSMSessionData, OlaSMSessionData

logger = logging.getLogger(__name__)


class VoiceStateConflictError(RuntimeError):
    """Another room already advanced the same application session."""


class VoiceStateStore(Protocol):
    async def restore(self, userdata: OlaSMSessionData) -> bool: ...

    async def save(self, userdata: OlaSMSessionData) -> None: ...


class VoiceStateRepository(Protocol):
    async def get_voice_agent_state(self, session_id: str) -> dict[str, object] | None: ...

    async def save_voice_agent_state(
        self,
        session_id: str,
        state: Mapping[str, object],
        *,
        expected_revision: int,
        terminal_updates: Mapping[str, object] | None = None,
    ) -> dict[str, object] | None: ...

    async def update_session(
        self,
        session_id: str,
        updates: Mapping[str, object],
        *,
        expected_version: int | None = None,
    ) -> dict[str, object] | None: ...


class DatabaseVoiceStateStore:
    def __init__(self, repository: VoiceStateRepository | None = None) -> None:
        self._repository = repository or PersistenceRepository()

    async def restore(self, userdata: OlaSMSessionData) -> bool:
        row = await self._repository.get_voice_agent_state(userdata.app_session_id)
        if row is None:
            userdata.persistence_enabled = False
            return False
        if row.get("status") not in {None, "ACTIVE"}:
            userdata.persistence_enabled = False
            return False
        state = row.get("state")
        if isinstance(state, dict):
            draft = state.get("booking_draft")
            draft = draft if isinstance(draft, dict) else {}
            if state.get("lifecycle_status") in {"completed", "cancelled"} or draft.get("booking"):
                userdata.persistence_enabled = False
                return False

        # The trusted session row, not client/job metadata, owns the account ID.
        userdata.user_id = str(row["user_id"])
        userdata.persistence_revision = int(row["revision"])
        if not isinstance(state, dict):
            return False
        userdata.restore(state, userdata.persistence_revision)
        return True

    async def save(self, userdata: OlaSMSessionData) -> None:
        if not userdata.persistence_enabled:
            return

        terminal_updates: dict[str, object] | None = None
        if userdata.lifecycle_status in {"completed", "cancelled"}:
            reason = "BOOKING_COMPLETED" if userdata.lifecycle_status == "completed" else "USER_CANCELLED"
            terminal_updates = {
                "status": "ENDED",
                "end_reason": reason,
                "ended_at": datetime.now(UTC),
            }
            booking = userdata.booking_draft.booking
            if booking is not None:
                terminal_updates.update(
                    booking_id=booking.booking_id,
                    booking_lifecycle_status="SUCCESS",
                    confirmation_status="confirmed",
                )

        state_started = time.perf_counter()
        try:
            result = await self._repository.save_voice_agent_state(
                userdata.app_session_id,
                userdata.durable_state(),
                expected_revision=userdata.persistence_revision,
                terminal_updates=terminal_updates,
            )
        except Exception:
            logger.info(
                "[PERF-VOICE] stage=state.save_voice_agent_state call_id=%s duration_ms=%.3f result=error",
                userdata.call_id,
                (time.perf_counter() - state_started) * 1000,
            )
            raise
        if result is None:
            logger.info(
                "[PERF-VOICE] stage=state.save_voice_agent_state call_id=%s duration_ms=%.3f result=conflict",
                userdata.call_id,
                (time.perf_counter() - state_started) * 1000,
            )
            raise VoiceStateConflictError("VOICE_STATE_CONFLICT")
        logger.info(
            "[PERF-VOICE] stage=state.save_voice_agent_state call_id=%s duration_ms=%.3f result=ok",
            userdata.call_id,
            (time.perf_counter() - state_started) * 1000,
        )
        userdata.persistence_revision = int(result["revision"])


class EphemeralVoiceStateStore:
    """No-op store used only by isolated unit/synthetic worker smoke sessions."""

    async def restore(self, userdata: OlaSMSessionData) -> bool:
        userdata.persistence_enabled = False
        return False

    async def save(self, userdata: OlaSMSessionData) -> None:
        return None
