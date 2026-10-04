"""Publish typed booking state over LiveKit's native reliable data channel."""

from __future__ import annotations

import json
import logging
import time

from livekit.agents import AgentSession

from src.voice_agent.session_data import OlaSMSessionData

BOOKING_STATE_TOPIC = "olasm.booking_state.v1"
LEGACY_BOOKING_STATE_TOPIC = "alosm.booking_state.v1"
logger = logging.getLogger(__name__)


async def publish_booking_state(session: AgentSession[OlaSMSessionData]) -> None:
    payload = json.dumps(
        session.userdata.public_state(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    call_id = getattr(session.userdata, "call_id", "unknown")
    started = time.perf_counter()
    result = "ok"
    try:
        await session.room_io.room.local_participant.publish_data(
            payload,
            reliable=True,
            topic=BOOKING_STATE_TOPIC,
        )
    except RuntimeError as exc:
        # LiveKit tears down RoomIO before late provider-failure callbacks run.
        # There is no recipient at that point, so this is an expected cleanup
        # race rather than an application error.
        if "room_io" in str(exc).lower() and "not started with a room" in str(exc).lower():
            result = "skipped_closed_session"
            logger.info("skipped LiveKit booking-state publish because the session is closed")
            return
        result = "error"
        logger.exception("failed to publish LiveKit booking state")
    except Exception:
        # The call can continue if a browser disconnects while a tool is completing.
        result = "error"
        logger.exception("failed to publish LiveKit booking state")
    finally:
        logger.info(
            "[PERF-VOICE] stage=publish_booking_state call_id=%s duration_ms=%.3f result=%s",
            call_id,
            (time.perf_counter() - started) * 1000,
            result,
        )
