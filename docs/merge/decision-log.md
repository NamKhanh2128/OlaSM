# Architectural Decision Log: Merging OlaSM & OlaSM_Phuong

Date: 2026-10-04  
Target Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM`  
Donor Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM_Phuong`

---

## 1. Summary of Decisions

| Item | Category | Target Location | Decision Rationale |
|---|---|---|---|
| **LiveKit WebRTC Agent Worker** | KEPT | `src/voice_agent/` | Production-grade WebRTC voice streaming, natural interruption, noise cancellation, multi-tenant room support. |
| **FastAPI Business & Auth API** | KEPT | `src/backend/` | Complete REST API with JWT, session tokens, OTP, user management, and transactional database services. |
| **Typed Core Agent Loop** | KEPT | `src/agents/` | Production model-driven agent with strictly typed schemas, tool validation, context history, and deterministic state. |
| **Alembic Migration Chain** | KEPT | `migrations/` | Version-controlled, reversible migration chain. Avoids data corruption and supports deployment rollbacks. |
| **InjectionScanner** | PORTED | `src/agents/core/guardrails.py` | Deterministic pre-LLM regex scanner from DONOR detecting prompt injection, base64, hex patterns, and system prompt leaks. |
| **Scope Guard (`is_out_of_scope`)** | PORTED | `src/agents/core/guardrails.py` | Deterministic refusal of off-topic queries (weather, news, songs) to prevent hallucination and preserve human operator capacity. |
| **AudioBudget & Turn Ceilings** | PORTED | `src/voice_agent/tasks/booking.py` | Frame and session byte limits preventing resource exhaustion / runaway streaming sessions. |
| **Schedule Natural Language Parser** | PORTED | `src/backend/services/schedule_parser.py` | Robust Vietnamese relative/absolute time parsing for ride scheduling ("sáng mai lúc 7 giờ", "chiều nay 5 rưỡi"). |
| **Attack Matrix & Security Tests** | PORTED | `tests/test_security/` | Comprehensive test cases from DONOR covering prompt injection, scope evasion, PII leakage, and replay attacks. |
| **MapLibre GL Route Visualizer** | ADAPTED | `src/frontend/src/features/maps/` | Visual route rendering adapted from web-v2 to work with OlaSM backend coordinates and MapLibre. |
| **Place Candidate Disambiguator** | ADAPTED | `src/frontend/src/features/booking/` | High-clarity candidate selection card adapted from web-v2 with ordinal badges and display address. |
| **Custom WebSocket PCM Gateway** | REJECTED | N/A (Donor only) | Duplicate transport incompatible with LiveKit WebRTC architecture. Would create split runtime and session conflicts. |
| **Donor Raw SQL Migrations** | REJECTED | N/A (Donor only) | Unmanaged SQL scripts lacking rollback capabilities and incompatible with existing Alembic revision history. |
| **Duplicate `viola_*` Top-Level Package** | REJECTED | N/A (Donor only) | Violates single source of truth; all imported donor logic must reside within canonical `src/` modules. |
| **Third-Party Live Cloud Credentials** | BLOCKED | Cloud Environment | External Blaze STT and live LiveKit cloud server require real API keys/tokens from user for live testing. |

---

## 2. Detailed Decision Records

### ADR-01: Canonical Voice Transport
- **Context**: TARGET uses LiveKit WebRTC (`src/voice_agent/server.py`), while DONOR uses a raw WebSocket PCM stream (`viola_api/ws/gateway.py`).
- **Decision**: Keep LiveKit as the sole voice transport.
- **Consequences**: Avoids maintaining two disparate audio pipelines. DONOR's audio frame limits (`AudioBudget`) are integrated into the LiveKit worker session guard.

### ADR-02: Pre-LLM Guardrail Integration
- **Context**: TARGET had PII redaction and post-action state verification, but lacked pre-LLM input sanitization against prompt injection and out-of-scope chit-chat.
- **Decision**: Port `InjectionScanner` and `is_out_of_scope` from DONOR directly into `src/agents/core/guardrails.py` as pre-flight checks before passing user text to LLM or task handlers.
- **Consequences**: Any prompt injection or off-topic query is intercepted with zero LLM inference cost and handled via safe refusal or operator handoff.

### ADR-03: Address Disambiguation & Booking Invariants
- **Context**: DONOR provides strict rules ensuring bookings cannot proceed with ambiguous or unconfirmed locations.
- **Decision**: Enforce strict invariants across both voice task and backend:
  1. A booking draft requires explicit user confirmation.
  2. Location updates immediately invalidate existing quotes.
  3. LLM cannot invent place coordinates; places must originate from authoritative maps lookup.
- **Consequences**: Complete elimination of hallucinated bookings or mismatched pricing.

### ADR-04: Frontend Enhancement
- **Context**: TARGET has a functional React 19 UI with LiveKit; DONOR has clean UI components in `web-v2` for candidate selection and MapLibre routing.
- **Decision**: Adapt web-v2 UI patterns into `src/frontend` using existing TailwindCSS tokens and TanStack Query API hooks.
- **Consequences**: Elevates user experience with interactive map routing and clear disambiguation without breaking API contracts.
