# Feature Matrix: OlaSM & OlaSM_Phuong Integration

Date: 2026-10-04  
Target Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM`  
Donor Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM_Phuong`

---

## 1. Core Feature & Architectural Mapping

| Domain / Feature | TARGET (OlaSM) Implementation | DONOR (OlaSM_Phuong) Implementation | Canonical Owner & Contract | Test Coverage & Status |
|---|---|---|---|---|
| **Voice Transport** | LiveKit WebRTC AgentServer (`src/voice_agent/server.py`) | Custom WebSocket PCM Gateway (`src/viola_api/ws`) | **TARGET**: LiveKit WebRTC is canonical. Gateway from DONOR rejected as duplicate runtime. | Tests in `tests/test_voice_agent/`. **Active**. |
| **Conversation State** | `AgentState` (`src/agents/contracts/state.py`), `BookingDraft` (`src/voice_agent/tasks/booking.py`) | `ConversationMachine` (`src/viola_conversation/machine.py`) | **TARGET**: `AgentState` & `BookingDraft`. Port slot validation & schedule parser from DONOR. | Unit tests in `tests/test_agent_core/`. **Active**. |
| **Address Candidate Selection** | `SearchPlaceParams`, `can_auto_select_place` (`src/voice_agent/tasks/booking.py`) | Explicit ordinal / candidate disambiguation (`src/viola_domain/booking_guard.py`) | **TARGET adapted**: Ambiguous candidates require user confirmation; auto-select only on exact match. | Tests in `tests/test_voice_agent/test_place_query_validator.py`. **Active**. |
| **Vehicle & Fare Quote** | `PricingService`, `VehicleType`, `estimate_fare` (`src/backend/services/pricing_catalog.py`) | `FareQuote`, vehicle type models (`src/viola_domain/models.py`) | **TARGET**: `PricingService` with multi-tier vehicle catalog and authoritative quotes. | Tests in `tests/unit/test_pricing_service.py`. **Active**. |
| **Booking Creation & Idempotency** | `BookingService.create`, `AgentGuardrails` idempotency check | `booking_guard.py` invariants | **TARGET**: Server-side UUID, idempotency key required, backend authoritative result before TTS. | Tests in `tests/test_agent_core/test_guardrails.py`. **Active**. |
| **Handoff & Operator Desk** | `HandoffService`, `HandoffTicket`, LiveKit Operator Room | Queue seat model, ticket draft, operator chat UI | **TARGET backend + DONOR UI**: Persistent ticket in DB, LiveKit room for voice, adapted web-v2 operator UI. | Backend tests in `tests/test_handoff/`. **Active**. |
| **Auth & Session Management** | JWT auth, session tracking, OTP/2FA (`src/backend/routes/auth.py`, `sessions.py`) | Simplified bearer token | **TARGET**: Full RBAC, session store, redis/db persistence canonical. | Tests in `tests/test_backend/test_auth.py`. **Active**. |
| **Persistence & Migrations** | Alembic revision chain (`migrations/versions/`), SQLAlchemy asyncpg | Raw SQL scripts (`migrations/001..011.sql`), direct asyncpg | **TARGET**: Alembic is canonical. DONOR schemas mapped into reversible Alembic revisions. | Alembic migration check. **Active**. |
| **Security & Guardrails** | PII redaction (`redact_pii`), state safety gates, reconciliation | `InjectionScanner`, `is_out_of_scope`, `AudioBudget` | **TARGET + DONOR**: Integrate injection scan and scope guard as pre-LLM gates in TARGET guardrails. | Tests in `tests/test_security/` & `tests/test_agent_core/`. **Active**. |
| **Frontend Map & UI** | React 19, LiveKit React components | React 19, MapLibre GL, Candidate Picker, Fake simulator | **TARGET + DONOR**: Keep TARGET routing and LiveKit hooks; incorporate MapLibre route preview & ticket drawer. | Frontend unit tests (`vitest run`). **Active**. |

---

## 2. Boundary Mapping & Contracts

### 2.1 Voice Transport Contract
- **Interface**: LiveKit Room with WebRTC audio track.
- **Client**: `livekit-client` + `@livekit/components-react`.
- **Worker**: `livekit-agents` Worker listening to room connect events.
- **Invariant**: Barge-in immediately triggers `session.interrupt()` and cancels outgoing TTS synthesis.

### 2.2 AgentState & Conversation State Contract
- **Owner**: `src/agents/contracts/state.py` (`AgentState`).
- **Slot Invariants**:
  - `pickup`: Resolved `PlaceInfo` with valid `place_id`, `lat`, `lng`, `display_name`.
  - `destination`: Resolved `PlaceInfo` with valid `place_id`, `lat`, `lng`, `display_name`.
  - `vehicle_type`: Enum (`CAR_4`, `CAR_7`, `BIKE`).
  - `confirmation`: Enum (`UNCONFIRMED`, `CONFIRMING`, `CONFIRMED`, `REJECTED`).
- **State Transition Rule**: Any change to `pickup`, `destination`, or `vehicle_type` invalidates existing `fare_quote` and resets `confirmation` to `UNCONFIRMED`.

### 2.3 Address Disambiguation Contract
- **Owner**: `src/backend/services/maps_service.py` & `src/voice_agent/tasks/booking.py`.
- **Resolution**:
  - Exact match (`score >= 0.95` or single candidate) -> Auto-selected with spoken slot confirmation.
  - Multiple candidates (`count >= 2`) -> Emits candidate list; prompts user to choose ordinal ("số 1", "số 2") or clarify name.
  - Zero candidates -> Spoken failure prompt with fallback to retry or operator handoff.

### 2.4 Vehicle, Fare, & Booking Contract
- **Owner**: `src/backend/services/pricing_service.py` & `src/backend/services/booking_service.py`.
- **Authoritative Flow**:
  1. `estimate_fare`: Calculates distance, duration, base fare, surge multiplier, dynamic discounts, and returns `fare_estimate_id` with 5-minute expiry.
  2. `create_booking`: Must receive `fare_estimate_id`, matching `pickup_place_id`, `destination_place_id`, and `idempotency_key`.
  3. Spoken TTS "Đặt chuyến thành công" is strictly disallowed until `create_booking` returns HTTP 201 with confirmed `booking_id`.

### 2.5 Handoff & Operator Contract
- **Owner**: `src/backend/services/handoff_service.py` & `src/backend/models/handoff.py`.
- **Payload**:
  - `session_id`, `user_id`, `reason` (enum: `SAFETY_VIOLATION`, `UNRESOLVED_DISAMBIGUATION`, `SYSTEM_ERROR`, `USER_REQUESTED`), `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `context`: Redacted conversation transcript, collected slots, last error code.
  - LiveKit Operator room credentials issued via `/api/v1/handoff/{ticket_id}/token`.

### 2.6 Persistence Contract
- **Canonical Engine**: PostgreSQL (production) / SQLite (tests) managed via Alembic.
- **Rule**: No schema alterations occur at application startup. All changes are versioned, reversible migrations.
