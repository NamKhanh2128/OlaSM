# Inventory: OlaSM (TARGET) vs OlaSM_Phuong (DONOR)

Date: 2026-10-04
Target Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM`
Donor Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM_Phuong`

---

## 1. Environment & Runtime Inventory

| Tool / Runtime | TARGET (OlaSM) | DONOR (OlaSM_Phuong) | Merge Decision |
|---|---|---|---|
| **Python** | 3.13.11 | >= 3.11 | Python 3.13 canonical |
| **Node.js** | v24.9.0 | v22 / v24 | Node v24 canonical |
| **npm** | 11.6.0 | npm / pnpm | npm canonical |
| **Package Manager** | `uv` 0.11.13 + `pip` | `uv` / setuptools | `uv` / pyproject.toml |
| **Frontend Framework**| React 19.2.8 + Vite 8.2.0 | React 19.2.0 + Vite 8.0.0 | React 19 + Vite 8 canonical |

---

## 2. TARGET Repository (OlaSM) Inventory

### 2.1 Modules & Structure
- `src/backend/`:
  - `main.py`: FastAPI entrypoint, router configuration, middleware (CORS, RequestContext, ExceptionHandler).
  - `config.py`: Pydantic settings for DB, LiveKit, JWT, Redis, Gemini, ElevenLabs.
  - `routes/`: Auth (`/api/v1/auth`), Sessions (`/api/v1/sessions`), Bookings (`/api/v1/bookings`), Quotes (`/api/v1/quotes`), Places (`/api/v1/places`), Handoff (`/api/v1/handoff`), Policy (`/api/v1/policy`), Profile (`/api/v1/profile`).
  - `services/`: `AgentToolExecutor`, `BookingService`, `PricingService`, `MapsService`, `HandoffService`, `OfferEngine`, `OfferProfileService`, `VisualGroundingService`, `ConfidenceFusionService`.
  - `repositories/`: Database abstraction with SQLAlchemy async sessions (`BookingRepository`, `UserRepository`, `SessionRepository`, `HandoffRepository`).
  - `schemas/`: Pydantic schemas for all API payloads and domain boundaries.
  - `models/`: SQLAlchemy ORM models (`User`, `Session`, `Booking`, `HandoffTicket`, `UserOfferProfile`, `Promotion`).
  - `database.py`: Async engine and session factory (`create_async_engine`, SQLite test / PostgreSQL prod).
  - `observability/`: Logging, tracing, and metrics instrumentation.
  - `privacy/`: Deterministic PII redactor (`redact_phone`, `redact_booking_id`, `redact_sensitive_text`).

- `src/agents/`:
  - `contracts/`: Typed interfaces (`AgentInput`, `AgentAction`, `AgentState`, `ToolCall`, `ToolResult`, `WorkflowType`, `ConfirmationStatus`).
  - `core/`:
    - `agent.py`: `ModelDrivenAgent`, tool loop, retry/turn limits.
    - `booking/`: `BookingState`, draft mutation, candidate selection.
    - `guardrails.py`: `AgentGuardrails` (state validation, side-effect controls, PII redaction, idempotency enforcement).
    - `handoff.py`: Handoff trigger, severity evaluation, context redaction.
    - `instructions.py`: System prompt construction and business policies.
    - `tools.py`: Tool definitions and schema models.
  - `tools/`: Tool registry and execution lifecycle.

- `src/voice_agent/`:
  - `server.py`: LiveKit Worker entry point (`AgentServer`), session setup, prewarming, STT/TTS pipeline.
  - `tasks/booking.py`: `BookingTask`, real-time speech event loop, barge-in detection, filler utterances, slot updates, state synchronization.
  - `tasks/tracking.py`: `TrackingTask` for ride lookup and ETA updates.
  - `tasks/support.py`: Post-booking support, complaints, FAQ.
  - `state/`: Voice session state persistence, reconnection recovery, optimistic locking.
  - `speech/`: Speech processing, numeric rewrite guards, Vietnamese currency formatting.

- `src/frontend/`:
  - React 19 + TypeScript + Vite 8 + TailwindCSS v4.
  - LiveKit integration (`@livekit/components-react`, `livekit-client`).
  - Pages/Features: Auth, Ride Booking, Trip Tracking, Voice Session, Operator Desk, Settings/2FA.

- `migrations/`:
  - Alembic migration environment (`env.py`, `alembic.ini`).
  - Sequential revision history (`0001_initial` through `coe_001_offer_tables`).

- `tests/`:
  - 632 collected tests covering backend services, agent core, voice agent tasks, persistence, and pricing.

---

## 3. DONOR Repository (OlaSM_Phuong) Inventory

### 3.1 Modules & Structure
- `src/viola_api/`:
  - FastAPI application, configuration, REST routes.
  - `ws/gateway.py`: WebSocket server receiving raw 16kHz PCM audio, streaming STT/TTS events.
- `src/viola_conversation/`:
  - `machine.py`: Deterministic state machine (`ConversationMachine`) managing explicit booking phases.
  - `policy.py`: Intent classification (`BOOKING`, `FARE_QUOTE`, `STATUS`, `UNKNOWN`).
  - `schedule.py`: Vietnamese natural language schedule parser.
- `src/viola_domain/`:
  - `models.py`: Value objects for places, quotes, vehicle types, rides.
  - `booking_guard.py`: Validation rules for booking creation.
  - `tools.py`: In-memory tool implementations.
- `src/viola_guardrails/`:
  - `input.py`: `AudioBudget` (frame size cap and session byte limit).
  - `llm.py`: `InjectionScanner` (regular expressions for prompt injection, base64, hex detection).
  - `scope.py`: Out-of-scope intent guard (weather, news, small talk refusal).
- `src/viola_providers/`:
  - `base.py`, `registry.py`: Provider interface and plugin registry.
  - `fakes.py`: In-memory fake STT, TTS, LLM, and Geocoder providers.
  - `blaze_stt.py`: Vietnamese Blaze STT client.
  - `geocoder.py`: Integration with Goong / GoGoDuk geocoders.
- `src/viola_persistence/`:
  - Direct `asyncpg` pool, raw SQL queries, repositories.
- `web-v2/`:
  - React 19 + Vite 8 + MapLibre GL.
  - Customer interface with MapLibre route preview, place candidate selector.
  - Operator console with live ticket queue and chat.
  - Fake voice client simulator (`dev:fake`).
- `docs/specs/`:
  - 11 comprehensive specification documents (01-11) covering PRD, architecture, threat model, testing matrix.
- `eval/`:
  - Evaluation runner, attack scenario generator, benchmark reports.
- `tests/`:
  - 1038 unit, contract, and security test cases.

---

## 4. Entry Points Comparison

| Functionality | TARGET Entry Point | DONOR Entry Point | Canonical Entry Point |
|---|---|---|---|
| **API Server** | `src.backend.main:app` | `viola_api.main:app` | `src.backend.main:app` |
| **Voice Worker** | `src.voice_agent.server:run_worker` | `viola_api.ws.gateway:voice_ws` | `src.voice_agent.server:run_worker` (LiveKit WebRTC) |
| **Frontend** | `src/frontend` (`npm run dev`) | `web-v2` (`npm run dev`) | `src/frontend` with integrated web-v2 components |
| **Database Migrations** | `alembic upgrade head` | `scripts/migrate.py` (raw SQL) | `alembic upgrade head` |
