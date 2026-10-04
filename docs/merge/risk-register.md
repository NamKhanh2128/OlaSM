# Risk Register: OlaSM & OlaSM_Phuong Integration

Date: 2026-10-04  
Target Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM`  
Donor Repository: `C:\Users\KHANH\Documents\GitHub\OlaSM_Phuong`

---

## 1. Risk Matrix

| Risk ID | Category | Description | Severity | Likelihood | Mitigation Strategy |
|---|---|---|---|---|---|
| **RSK-01** | Architecture | **Dual Voice Runtime Conflict**: Starting both LiveKit Worker and WebSocket PCM gateway simultaneously causes port collisions, session state desynchronization, and split operator queues. | High | Low | **Strict Rejection**: Do not port `viola_api/ws/gateway.py`. LiveKit WebRTC is the single source of truth for real-time audio. |
| **RSK-02** | Security / PII | **PII & Credential Leakage**: Copying donor files could accidentally expose hardcoded tokens, mock API keys, or raw phone numbers into logs or git history. | Critical | Low | **Safe Porting Protocol**: No `.env` files, databases, or mock configs copied. All new code paths pass through `redact_pii` and `redact_pii_data`. |
| **RSK-03** | Data Integrity | **Migration Graph Divergence**: Injecting raw SQL migrations from donor breaks Alembic revision linearity and causes migration failures on existing databases. | High | Low | **Single Migration Pipeline**: Donor schema additions (if needed) are packaged strictly as new reversible Alembic migrations. Zero raw SQL executed outside Alembic. |
| **RSK-04** | Worktree | **Overwriting User Uncommitted Changes**: TARGET repository has active modifications from user (e.g. `src/backend/services/agent_tool_executor.py`, offer engines). | Critical | Low | **Additive-Only Edits**: Never run `git reset --hard`, `git checkout --`, or `git clean`. Every edit preserves user work. |
| **RSK-05** | Security / LLM | **Direct Prompt Injection & System Prompt Leaks**: Adversarial callers embedding instructions to override system prompt or grant unauthorized discounts. | High | Medium | **Pre-LLM InjectionScanner**: Port DONOR's deterministic regex scanner to intercept prompt injection attempts prior to LLM invocation, routing directly to operator handoff. |
| **RSK-06** | Reliability | **State Stale / Race Conditions**: Concurrent booking mutations or speech barge-in creating duplicate rides. | High | Low | **Authoritative Idempotency & Optimistic Locking**: Maintain `BookingChangeToken`, `idempotency_key` on all booking requests, and lock generation checks. |

---

## 2. Rollback & Contingency Plan

If any ported feature causes regression or instability:
1. **No Destructive Git Commands**: Avoid `git reset --hard` or `git clean -fd`.
2. **Selective Patch Reversal**: Revert only the specific additive files or functions introduced during the merge.
3. **Rollback Verification Steps**:
   - Run `python -m compileall -q src tests scripts` to ensure zero compilation breaks.
   - Run `pytest --collect-only -q` to verify full test suite discovery.
   - Run targeted test suites (`pytest tests/test_voice_agent/`, `pytest tests/unit/`).
