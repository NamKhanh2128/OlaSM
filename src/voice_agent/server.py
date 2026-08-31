"""LiveKit AgentServer worker for the AloSM voice runtime."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable

from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    APIConnectOptions,
    JobContext,
    JobProcess,
    cli,
    inference,
    llm,
    stt,
    tts,
    vad,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.agents.voice.events import ErrorEvent
from livekit.agents.voice.room_io import AudioInputOptions, RoomOptions

from src.backend.services.handoff_service import HandoffService
from src.backend.services.knowledge_service import KnowledgeService
from src.backend.services.pricing_service import PricingService
from src.voice_agent.agent import AloSMAgent
from src.voice_agent.config import LiveKitVoiceSettings, get_livekit_voice_settings
from src.voice_agent.model_factory import build_llm, build_stt, build_tts, tts_voice_map
from src.voice_agent.observability import LiveKitSessionObserver, SessionEventLog
from src.voice_agent.persistence import DatabaseVoiceStateStore, VoiceStateStore
from src.voice_agent.session_data import AloSMSessionData, FailureCode, FallbackAction, HandoffState
from src.voice_agent.state_sync import publish_booking_state
from src.voice_agent.transcript_rewrite import build_transcript_rewriter
from src.voice_agent.tts_text import vietnamese_currency_tts_transform

logger = logging.getLogger(__name__)

_STATE_STORE_KEY = "alosm_voice_state_store"
_PROCESS_STORE_READY_KEY = "alosm_process_store_ready"
_PREWARMED_VAD_KEY = "alosm_prewarmed_vad"
_PREWARMED_STT_KEY = "alosm_prewarmed_stt"
_PREWARMED_KNOWLEDGE_KEY = "alosm_prewarmed_knowledge"
_PREWARMED_PRICING_KEY = "alosm_prewarmed_pricing"
_NOISY_WORKER_LOGGERS = ("grpc", "grpc._cython.cygrpc", "livekit.agents")


def _configure_worker_console_logging() -> None:
    """Keep the terminal focused on application voice events and real failures."""

    for logger_name in _NOISY_WORKER_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    for logger_name in (
        "src.voice_agent.observability",
        "src.voice_agent.persistence",
        "src.voice_agent.tasks.booking",
        "src.voice_agent.state_sync",
        "src.backend.services.booking_service",
    ):
        logging.getLogger(logger_name).setLevel(logging.INFO)


def register_room_audio_track_logging(ctx: JobContext, event_log: SessionEventLog) -> None:
    """Log each audio publication once so overlapping voices have an owner and SID."""

    room = ctx.room

    def emit_audio_track(action: str, direction: str, publication: object, participant: object) -> None:
        if getattr(publication, "kind", None) != rtc.TrackKind.KIND_AUDIO:
            return
        event_log.emit(
            "room_audio_track",
            action=action,
            direction=direction,
            owner_identity=getattr(participant, "identity", None),
            owner_sid=getattr(participant, "sid", None),
            track_sid=getattr(publication, "sid", None),
            track_name=getattr(publication, "name", None),
            muted=getattr(publication, "muted", None),
        )

    def on_local_track_published(publication: object, _: object) -> None:
        emit_audio_track("published", "outgoing", publication, room.local_participant)

    def on_local_track_unpublished(publication: object) -> None:
        emit_audio_track("unpublished", "outgoing", publication, room.local_participant)

    def on_track_published(publication: object, participant: object) -> None:
        emit_audio_track("published", "incoming", publication, participant)

    def on_track_unpublished(publication: object, participant: object) -> None:
        emit_audio_track("unpublished", "incoming", publication, participant)

    room.on("local_track_published", on_local_track_published)
    room.on("local_track_unpublished", on_local_track_unpublished)
    room.on("track_published", on_track_published)
    room.on("track_unpublished", on_track_unpublished)

    for publication in room.local_participant.track_publications.values():
        emit_audio_track("present", "outgoing", publication, room.local_participant)
    for participant in room.remote_participants.values():
        for publication in participant.track_publications.values():
            emit_audio_track("present", "incoming", publication, participant)


def build_agent_session(
    settings: LiveKitVoiceSettings,
    *,
    userdata: AloSMSessionData | None = None,
    vad_model: vad.VAD | None = None,
    stt_model: stt.STT | None = None,
) -> AgentSession[AloSMSessionData]:
    """Build the native cascaded pipeline without legacy orchestration adapters."""

    settings.require_configured()
    userdata = userdata or AloSMSessionData(
        app_session_id="local-smoke-session",
        call_id="local-smoke-call",
        user_id="local-smoke-user",
        participant_identity="local-smoke-participant",
        recording_enabled=settings.livekit_record_audio,
        critical_confidence_threshold=settings.livekit_critical_confidence_threshold,
    )
    return AgentSession(
        userdata=userdata,
        vad=vad_model if vad_model is not None else inference.VAD(model="silero"),
        stt=stt_model if stt_model is not None else build_stt(settings),
        llm=build_llm(settings),
        tts=build_tts(settings),
        conn_options=SessionConnectOptions(
            tts_conn_options=APIConnectOptions(
                max_retry=settings.livekit_tts_max_retries,
                retry_interval=settings.livekit_tts_retry_interval_seconds,
                timeout=settings.livekit_tts_timeout_seconds,
            )
        ),
        tts_text_transforms=[
            "filter_emoji",
            "filter_markdown",
            vietnamese_currency_tts_transform,
        ],
        transcription_timeout=settings.livekit_transcription_timeout_seconds,
        turn_handling={
            "turn_detection": settings.livekit_turn_detection,
            "endpointing": {
                "mode": settings.livekit_endpointing_mode,
                "min_delay": settings.livekit_endpointing_min_delay_seconds,
                "max_delay": settings.livekit_endpointing_max_delay_seconds,
            },
            "interruption": {
                "enabled": True,
                "mode": settings.livekit_interruption_mode,
                "min_duration": settings.livekit_interruption_min_duration_seconds,
                "min_words": settings.livekit_interruption_min_words,
                "false_interruption_timeout": 2.0,
                "resume_false_interruption": True,
            },
            # Booking tools can persist a quote and take several seconds.
            # Wait for their result before generating speech so an early
            # preemptive response cannot be cancelled and leave the turn silent.
            "preemptive_generation": {
                "enabled": False,
                "preemptive_tts": False,
            },
        },
    )


def build_session_data(ctx: JobContext, settings: LiveKitVoiceSettings) -> AloSMSessionData:
    """Build privacy-safe business userdata from trusted dispatch metadata."""

    try:
        metadata = json.loads(ctx.job.metadata or "{}")
    except (json.JSONDecodeError, TypeError):
        metadata = {}
    participant = getattr(ctx.job, "participant", None)
    participant_identity = str(getattr(participant, "identity", "") or "unknown-participant")
    app_session_id = str(metadata.get("app_session_id") or ctx.job.id)
    return AloSMSessionData(
        app_session_id=app_session_id,
        call_id=str(ctx.job.id),
        user_id=participant_identity,
        participant_identity=participant_identity,
        consent_granted=True,
        recording_enabled=settings.livekit_record_audio,
        critical_confidence_threshold=settings.livekit_critical_confidence_threshold,
    )


async def restore_session_data(
    userdata: AloSMSessionData,
    state_store: VoiceStateStore,
    *,
    timeout_seconds: float | None = None,
) -> bool:
    """Restore a draft before AgentSession starts, with an explicit safe fallback."""

    try:
        async with asyncio.timeout(timeout_seconds):
            recovered = await state_store.restore(userdata)
        return recovered
    except Exception:
        logger.exception("failed to restore LiveKit voice state")
        # A timed-out store is not safe for later writes in the same call. Keep
        # the conversation available in memory and avoid blocking every tool turn.
        userdata.persistence_enabled = False
        userdata.record_failure(
            "SESSION_RECOVERY_FAILED",
            "Không thể khôi phục phiên trước; cuộc gọi tiếp tục với trạng thái mới.",
            fallback_action="none",
        )
        return False


def _provider_failure(event: ErrorEvent) -> tuple[FailureCode, str, FallbackAction]:
    kind = f"{type(event.source).__name__} {type(event.error).__name__}".lower()
    if "stt" in kind:
        return "STT_UNAVAILABLE", "Nhận dạng giọng nói tạm thời lỗi.", "repeat_or_text"
    if "tts" in kind:
        return "TTS_UNAVAILABLE", "Phát giọng nói tạm thời lỗi; bạn có thể đọc tin nhắn.", "retry"
    return "LLM_UNAVAILABLE", "Tổng đài xử lý tạm thời lỗi.", "retry"


def register_provider_failure_sync(
    session: AgentSession[AloSMSessionData],
    state_store: VoiceStateStore,
) -> Callable[[], Awaitable[None]]:
    """Map native LiveKit provider errors to the public recovery contract."""

    failure_lock = asyncio.Lock()
    failure_tasks: set[asyncio.Task[None]] = set()

    async def persist_failure(event: ErrorEvent) -> None:
        # LiveKit already retries errors marked recoverable. Publishing those as
        # customer-facing failures makes a healthy retry look like an outage.
        if bool(getattr(event.error, "recoverable", False)):
            logger.info("LiveKit provider retry in progress source=%s", type(event.source).__name__)
            return

        # Follow LiveKit's documented continuation strategy. LLM/TTS instances
        # are recreated on the next turn; STT owns a long-lived stream and needs
        # the current Agent re-applied to restart it. Text input remains available
        # through RoomIO while the customer sees the typed fallback state.
        if isinstance(event.source, stt.STT):
            current_agent = session.current_agent
            if current_agent is not None:
                session.update_agent(current_agent)
            event.error.recoverable = True
        elif isinstance(event.source, (llm.LLM, tts.TTS)):
            event.error.recoverable = True

        async with failure_lock:
            code, message, fallback = _provider_failure(event)
            session.userdata.record_failure(code, message, fallback_action=fallback)
            try:
                await state_store.save(session.userdata)
            except Exception:
                logger.exception("failed to persist LiveKit provider failure")
            await publish_booking_state(session)

    @session.on("error")
    def on_error(event: ErrorEvent) -> None:
        task = asyncio.create_task(persist_failure(event))
        failure_tasks.add(task)
        task.add_done_callback(failure_tasks.discard)

    async def drain_failure_tasks() -> None:
        if failure_tasks:
            await asyncio.gather(*tuple(failure_tasks), return_exceptions=True)

    return drain_failure_tasks


_server_settings = get_livekit_voice_settings()
server = AgentServer(
    ws_url=_server_settings.livekit_url or None,
    api_key=_server_settings.livekit_api_key.get_secret_value() or None,
    api_secret=_server_settings.livekit_api_secret.get_secret_value() or None,
    num_idle_processes=_server_settings.livekit_num_idle_processes,
)


def prepare_process(proc: JobProcess) -> None:
    """Prewarm process-local model and state resources before job assignment."""

    # AgentServer 1.6.6 invokes setup_fnc synchronously before creating the job
    # event loop. Do not open asyncpg connections here: pooled asyncio connections
    # cannot be transferred to the different loop used by the RTC job.
    proc.userdata[_STATE_STORE_KEY] = DatabaseVoiceStateStore()
    # LiveKit keeps idle job processes warm specifically so model/plugin setup is
    # not paid after a participant is waiting. The ElevenLabs plugin validates
    # its direct API credentials synchronously; its streaming client is still
    # opened later on the RTC job's event loop.
    proc.userdata[_PREWARMED_VAD_KEY] = inference.VAD(model="silero")
    proc.userdata[_PREWARMED_STT_KEY] = build_stt(_server_settings)
    # Policy and pricing catalogs are local, validated and static for the
    # process lifetime. Load them during LiveKit prewarm so a FAQ turn never
    # adds file I/O or catalog validation latency to the first user request.
    proc.userdata[_PREWARMED_KNOWLEDGE_KEY] = KnowledgeService()
    proc.userdata[_PREWARMED_PRICING_KEY] = PricingService()
    proc.userdata[_PROCESS_STORE_READY_KEY] = True


server.setup_fnc = prepare_process


def _process_state_store(ctx: JobContext) -> DatabaseVoiceStateStore:
    state_store = ctx.proc.userdata.get(_STATE_STORE_KEY)
    return state_store if isinstance(state_store, DatabaseVoiceStateStore) else DatabaseVoiceStateStore()


def _process_vad(ctx: JobContext) -> vad.VAD | None:
    model = ctx.proc.userdata.get(_PREWARMED_VAD_KEY)
    return model if isinstance(model, vad.VAD) else None


def _process_stt(ctx: JobContext) -> stt.STT | None:
    model = ctx.proc.userdata.get(_PREWARMED_STT_KEY)
    return model if isinstance(model, stt.STT) else None


async def _connect_room_early(ctx: JobContext) -> float:
    """Join the assigned Room before any state restore or model/session setup."""

    started_at = time.monotonic()
    await ctx.connect()
    return round((time.monotonic() - started_at) * 1000, 3)


def _process_knowledge(ctx: JobContext) -> KnowledgeService | None:
    service = ctx.proc.userdata.get(_PREWARMED_KNOWLEDGE_KEY)
    return service if isinstance(service, KnowledgeService) else None


def _process_pricing(ctx: JobContext) -> PricingService | None:
    service = ctx.proc.userdata.get(_PREWARMED_PRICING_KEY)
    return service if isinstance(service, PricingService) else None


async def _timed_restore(
    userdata: AloSMSessionData,
    state_store: VoiceStateStore,
    timeout_seconds: float,
) -> tuple[bool, float]:
    started = time.monotonic()
    recovered = await restore_session_data(
        userdata,
        state_store,
        timeout_seconds=timeout_seconds,
    )
    return recovered, round((time.monotonic() - started) * 1000, 3)


def request_initial_greeting(
    session: AgentSession[AloSMSessionData],
    *,
    recovered: bool,
) -> None:
    """Schedule a native greeting without an unnecessary LLM turn for new calls."""

    if recovered:
        session.generate_reply(
            instructions=(
                "Nói ngắn gọn rằng đã khôi phục yêu cầu đặt xe trước đó. Tóm tắt đúng trạng thái này: "
                f"{session.userdata.booking_draft.conversation_summary()}. "
                "Sau đó hỏi khách có muốn tiếp tục không."
            ),
            allow_interruptions=True,
        )
        return

    session.say(
        "Chào bạn, tôi là tổng đài viên AloSM. Bạn vui lòng cho biết yêu cầu đặt xe của mình nhé?",
        allow_interruptions=True,
    )


def register_operator_takeover(
    session: AgentSession[AloSMSessionData],
    state_store: VoiceStateStore,
) -> Callable[[], Awaitable[None]]:
    """Stop the AI when an authenticated operator joins the active Room.

    The operator is a normal LiveKit participant with trusted metadata. The
    backend still owns role/acceptance checks; this hook only reacts to the
    participant that was allowed into the Room and hands media control over.
    """

    takeover_lock = asyncio.Lock()
    takeover_tasks: set[asyncio.Task[None]] = set()
    takeover_started = False

    async def takeover(participant: object) -> None:
        nonlocal takeover_started
        metadata_raw = str(getattr(participant, "metadata", "") or "")
        try:
            metadata = json.loads(metadata_raw)
        except (TypeError, json.JSONDecodeError):
            return
        if metadata.get("role") != "operator":
            return
        handoff_id = str(metadata.get("handoff_id") or "")
        operator_id = str(metadata.get("operator_id") or "")
        current = session.userdata.handoff
        if not handoff_id or not operator_id or current is None or current.handoff_id != handoff_id:
            return
        async with takeover_lock:
            if takeover_started:
                return
            takeover_started = True
            try:
                await HandoffService().connect_handoff_durable(handoff_id, operator_id)
            except Exception:
                logger.exception("failed to mark operator handoff connected id=%s", handoff_id)
            session.userdata.handoff = HandoffState(
                handoff_id=handoff_id,
                status="connected",
                reason_code=current.reason_code,
                operator_id=operator_id,
                room_name=current.room_name or session.room_io.room.name,
            )
            await state_store.save(session.userdata)
            await publish_booking_state(session)
            session.interrupt()
            session.input.set_audio_enabled(False)
            session.output.set_audio_enabled(False)
            # LiveKit keeps the customer and operator in the Room after the
            # agent session shuts down; this prevents the AI from hearing or
            # speaking over the human takeover.
            session.shutdown(drain=False)

    def on_participant_connected(participant: object) -> None:
        task = asyncio.create_task(takeover(participant))
        takeover_tasks.add(task)
        task.add_done_callback(takeover_tasks.discard)

    session.room_io.room.on("participant_connected", on_participant_connected)
    for participant in session.room_io.room.remote_participants.values():
        on_participant_connected(participant)

    async def drain() -> None:
        current_task = asyncio.current_task()
        pending = tuple(task for task in takeover_tasks if task is not current_task)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    return drain


@server.rtc_session(agent_name=get_livekit_voice_settings().livekit_agent_name)
async def alosm_voice_session(ctx: JobContext) -> None:
    """Run one LiveKit AgentSession for one Room call."""

    job_entry_at = time.time()
    room_connect_duration_ms = await _connect_room_early(ctx)

    settings = get_livekit_voice_settings()
    transcript_rewriter = build_transcript_rewriter(settings)
    if transcript_rewriter is None:
        rewrite_uses_openrouter = bool(
            settings.voice_transcript_rewrite_base_url
            and "openrouter.ai" in settings.voice_transcript_rewrite_base_url.casefold()
        )
        rewrite_key_configured = bool(
            (
                settings.openrouter_api_key.get_secret_value()
                if rewrite_uses_openrouter
                else settings.openai_api_key.get_secret_value()
            ).strip()
        )
        logger.warning(
            "Voice transcript rewrite unavailable enabled=%s key_configured=%s",
            settings.voice_transcript_rewrite_enabled,
            rewrite_key_configured,
        )
    else:
        logger.info(
            "Voice transcript rewrite ready model=%s reasoning=%s timeout_seconds=%.2f context_pairs=%d",
            transcript_rewriter.model,
            transcript_rewriter.reasoning_effort,
            transcript_rewriter.timeout_seconds,
            transcript_rewriter.context_window_turns,
        )
        ctx.add_shutdown_callback(transcript_rewriter.client.close)
    userdata = build_session_data(ctx, settings)
    event_log = SessionEventLog(
        enabled=settings.livekit_debug_event_log,
        include_transcripts=settings.livekit_debug_transcripts,
        directory=settings.livekit_debug_log_dir,
        userdata=userdata,
        room_name=ctx.room.name,
    )
    await event_log.start()
    ctx.add_shutdown_callback(event_log.close)
    event_log.emit(
        "worker_milestone",
        event_created_at=job_entry_at,
        milestone="job_entry",
    )
    event_log.emit(
        "worker_milestone",
        milestone="room_connected",
        duration_ms=room_connect_duration_ms,
    )

    state_store = _process_state_store(ctx)
    knowledge_service = _process_knowledge(ctx)
    pricing_service = _process_pricing(ctx)
    event_log.emit(
        "worker_milestone",
        milestone="process_setup_status",
        state_store_ready=bool(ctx.proc.userdata.get(_PROCESS_STORE_READY_KEY)),
        vad_prewarmed=_process_vad(ctx) is not None,
        stt_prewarmed=_process_stt(ctx) is not None,
        knowledge_prewarmed=knowledge_service is not None,
        pricing_prewarmed=pricing_service is not None,
    )
    restore_task = asyncio.create_task(
        _timed_restore(
            userdata,
            state_store,
            settings.livekit_state_restore_timeout_seconds,
        ),
        name=f"restore-voice-state-{userdata.call_id}",
    )
    # Let asyncpg begin checkout/query I/O, then construct the LiveKit pipeline
    # while that network operation is in flight. The Agent itself is created only
    # after restore completes, preserving its recovered-context instructions.
    await asyncio.sleep(0)
    session_build_started = time.monotonic()
    try:
        session = build_agent_session(
            settings,
            userdata=userdata,
            vad_model=_process_vad(ctx),
            stt_model=_process_stt(ctx),
        )
    except BaseException:
        restore_task.cancel()
        await asyncio.gather(restore_task, return_exceptions=True)
        raise
    event_log.emit(
        "worker_milestone",
        milestone="agent_session_built",
        duration_ms=round((time.monotonic() - session_build_started) * 1000, 3),
    )
    recovered, restore_duration_ms = await restore_task
    event_log.emit(
        "worker_milestone",
        milestone="state_restore_completed",
        duration_ms=restore_duration_ms,
        recovered=recovered,
        persistence_enabled=userdata.persistence_enabled,
    )
    drain_provider_failures = register_provider_failure_sync(session, state_store)
    ctx.add_shutdown_callback(drain_provider_failures)
    LiveKitSessionObserver(event_log, tts_voices=tts_voice_map(settings)).register(session)
    register_room_audio_track_logging(ctx, event_log)
    event_log.emit(
        "session_configured",
        stt_model=settings.livekit_stt_model,
        stt_language=settings.livekit_stt_language,
        llm_provider=settings.livekit_llm_provider,
        llm_model=settings.livekit_llm_model,
        tts_provider=settings.livekit_tts_provider,
        tts_model=settings.livekit_tts_model,
        tts_voice=settings.livekit_tts_voice,
        tts_language=settings.livekit_tts_language,
        turn_detection=settings.livekit_turn_detection,
        endpointing_mode=settings.livekit_endpointing_mode,
        endpointing_min_delay=settings.livekit_endpointing_min_delay_seconds,
        endpointing_max_delay=settings.livekit_endpointing_max_delay_seconds,
        interruption_mode=settings.livekit_interruption_mode,
        interruption_min_duration=settings.livekit_interruption_min_duration_seconds,
        interruption_min_words=settings.livekit_interruption_min_words,
        transcription_timeout=settings.livekit_transcription_timeout_seconds,
        policy_catalog_version=(
            knowledge_service.retriever.catalog.catalog_version if knowledge_service is not None else None
        ),
        pricing_catalog_version=pricing_service.catalog.version if pricing_service is not None else None,
    )
    session_start_started = time.monotonic()
    event_log.emit("worker_milestone", milestone="session_start_called")
    await session.start(
        room=ctx.room,
        agent=AloSMAgent(
            state_store=state_store,
            session_data=userdata,
            knowledge_service=knowledge_service,
            pricing_service=pricing_service,
            transcript_rewriter=transcript_rewriter,
        ),
        record=settings.livekit_record_audio,
        room_options=RoomOptions(
            text_input=True,
            audio_input=AudioInputOptions(
                # Native LiveKit input processing. Enhanced cancellation remains
                # opt-in because its plugin is separately metered and not installed.
                auto_gain_control=True,
                pre_connect_audio=True,
            ),
            close_on_disconnect=True,
            delete_room_on_close=settings.livekit_delete_room_on_close,
        ),
    )
    event_log.emit(
        "worker_milestone",
        milestone="session_started",
        duration_ms=round((time.monotonic() - session_start_started) * 1000, 3),
    )
    drain_operator_takeover = register_operator_takeover(session, state_store)
    ctx.add_shutdown_callback(drain_operator_takeover)
    await publish_booking_state(session)
    event_log.emit("worker_milestone", milestone="initial_state_published")
    request_initial_greeting(session, recovered=recovered)
    event_log.emit("worker_milestone", milestone="greeting_requested")


if __name__ == "__main__":
    _configure_worker_console_logging()
    cli.run_app(server)
