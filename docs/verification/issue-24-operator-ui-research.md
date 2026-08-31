# Issue #24 research — operator login and UI verification

Date: **2026-08-31** · Local source revision: [`9028dc9`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/tree/9028dc9f6bc2a2658a025a04e1662901895af1b7)

## Executive finding

Issue [#24 — P160-F2-EDGE-003](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/issues/24) is an **open P0 blocker about the published operator demo account being rejected by the live login**, not a report that the operator queue screen is missing.

The current local tree does contain a role-gated operator page, handoff queue API client, accept flow, and LiveKit room takeover UI. The strongest local explanation for the issue is an **environment/account-provisioning gap**: durable login looks up the phone in the database, while the migration and container startup do not seed an operator. This is an inference from the code evidence; it is not proof of the contents of the live database.

The issue should remain open until the exact published account is tested against the live deployment and the complete login → queue → accept → LiveKit takeover path is verified there.

## 1. Issue scope — verified facts

The authenticated GitHub issue API and issue page report:

| Field | Value |
|---|---|
| Title | `[Bug] [P160-F2-EDGE-003] [P0] Tài khoản tổng đài viên demo không thể đăng nhập trên môi trường Live` |
| State | `OPEN` |
| Labels | `bug`, `P0-Blocker` |
| Test case | `P160-F2-EDGE-003` |
| Live URL | `https://alosm.nairyuuu.site/` |
| Reproduction | Open the Operator Portal on live, enter the supplied phone/password, and submit login |
| Expected result | Successful operator login and access to the support-request queue |
| Reference revision in the report | `origin/main` / `b7a3b5797d0145b2c5232ce96a2e8e933473417e` |
| Reported at | `2026-08-28T15:46:59+07:00` |
| Last issue update observed | `2026-08-31T06:06:27Z` |

The issue body does **not** identify the phone number or password. No issue comments were returned by the GitHub API. The credential must therefore be recovered from the approved demo handoff, not guessed from source or copied into this note.

Primary sources: [issue page](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/issues/24), [issue API](https://api.github.com/repos/AI20K-Build-Phase-Cohort-3/P-160/issues/24), and the [reported reference commit](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/b7a3b5797d0145b2c5232ce96a2e8e933473417e).

## 2. Operator UI present locally — verified facts

The current frontend is under `src/frontend`; the earlier root-level `frontend/` prototype is not present in the current tree.

Current implementation:

- [`OperatorPage.tsx`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/pages/Operator/OperatorPage.tsx) renders the operator queue and an active call view.
- The queue calls `GET /api/v1/handoffs?status=pending` and refreshes every three seconds.
- Each pending record displays reason code, queue, priority, severity and summary, with a `Nhận cuộc gọi` action.
- Accepting a record calls `POST /api/v1/handoffs/{handoff_id}/accept`, then requests an operator-scoped LiveKit token.
- The active view mounts `LiveKitRoom`, renders remote audio, allows microphone mute/unmute, displays the handoff summary/context, and resolves the handoff on `Kết thúc`.
- [`operator/api.ts`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/features/operator/api.ts) contains the queue, accept, operator-token and resolve client functions.
- [`router/index.tsx`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/app/router/index.tsx#L45-L68) exposes `/operator` behind both `RequireAuth` and `RequireRole` for `OPERATOR`/`ADMIN`.
- [`AppLayout.tsx`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/components/layout/AppLayout.tsx#L32-L43) redirects an operator away from customer routes and does not mount the customer voice popup for that role.
- [`LoginForm.tsx`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/features/auth/components/LoginForm.tsx#L23-L80) saves the returned role/token/session and navigates `OPERATOR`/`ADMIN` to `/operator`; it also supports the optional TOTP second step.

Historical comparison:

- Commit [`13b61d1`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/13b61d12728e4ab1686663a05d82328106bd4ac6) introduced the original `frontend/src/components/OperatorUI.tsx`. That version used hard-coded mock calls and `alert()`/TODO API stubs.
- The current `src/frontend` implementation is a later integrated version: it uses real typed API calls and real role/LiveKit boundaries. The historical mock component should not be used as evidence that issue #24 is fixed.

## 3. Connected backend and LiveKit paths — verified facts

### Login and authorization

1. The browser submits phone/password to `POST /api/v1/auth/login` through [`auth/api.ts`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/features/auth/api.ts#L45-L80).
2. In durable mode, [`AuthService.login_durable`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/backend/services/auth_service.py#L75-L89) queries `PersistenceRepository.user_by_phone`; a missing user or password mismatch returns the same `401` message.
3. A successful login issues a durable bearer token and a ride session. The frontend stores the token, user ID, role and session ID in browser local storage through [`storage.ts`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/frontend/src/features/auth/storage.ts#L27-L54).
4. The queue and handoff mutation endpoints enforce `OPERATOR` or `ADMIN` on the bearer identity in [`handoffs.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/backend/api/routes/handoffs.py#L12-L24).

### Handoff and operator token

1. `GET /api/v1/handoffs?status=pending` lists persisted pending handoffs.
2. `POST /api/v1/handoffs/{id}/accept` assigns the authenticated operator and changes the handoff to `accepted`.
3. `POST /api/v1/livekit/operator-token` checks the operator role, accepted status, matching `operator_id`, and non-empty room name before issuing a token. See [`livekit.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/backend/api/routes/livekit.py#L116-L149).
4. [`tokens.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/voice_agent/tokens.py#L80-L119) scopes the operator token to the handoff room and puts `role`, `operator_id` and `handoff_id` in trusted participant metadata.
5. When the worker sees that authenticated operator participant, [`server.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/voice_agent/server.py#L382-L443) marks the handoff connected, persists/publishes state, disables AI input/output and shuts down the agent session while leaving the customer and operator in the Room.

The intended path is therefore:

```text
Login → role/session token → pending handoff queue → accept → room-scoped operator token
      → same LiveKit Room → worker marks connected → AI audio disabled → human takeover
```

The repository's LiveKit setup documents the customer voice path and handoff boundary, while also recording that operator console/real transfer were historically incomplete; the current source now contains the operator console/token path, but release status remains staging-only. See [`LIVEKIT_TEAM_SETUP.md`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/docs/LIVEKIT_TEAM_SETUP.md#L35-L56) and [`release-readiness.md`](release-readiness.md).

## 4. Account provisioning comparison — verified facts

This is the key distinction for issue #24:

- The durable `users` model stores a unique phone, password hash and role; the default role is `CUSTOMER`. See [`models.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/src/backend/db/models.py#L40-L52).
- The initial migration creates the `users` table but does not insert an operator row. See [`0001_initial_schema.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/migrations/versions/0001_initial_schema.py#L22-L32).
- `scripts/seed_demo_operator.py` is an explicit, manually invoked development seed. It refuses to run when `APP_ENV=production`; it is not called by the image command, either Compose startup command, or the staging pull/recreate script. See [`seed_demo_operator.py`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/scripts/seed_demo_operator.py#L13-L52), [`Dockerfile`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/Dockerfile#L35-L40), [`docker-compose.staging.yml`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/docker-compose.staging.yml#L1-L43), and [`deploy-staging.sh`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/scripts/deploy-staging.sh#L55-L72).
- The repository README documents the in-memory customer demo account for `APP_ENV=test`, and explicitly says a new durable development database does not auto-seed it. See [`README.md`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/README.md#L43-L49) and [`LIVEKIT_TEAM_SETUP.md`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/docs/LIVEKIT_TEAM_SETUP.md#L226-L242).

### Inference

If the live deployment is using the durable database path and the published operator row was never provisioned there, the observed `401` is expected even though the local operator UI exists. This is the leading hypothesis, not a verified live diagnosis. The issue body does not provide enough information to determine whether the live failure is a missing row, wrong role, wrong password, stale database, or a different deployed revision.

## 5. Test evidence and gaps — verified facts

Executed locally without changing source or external state:

```text
uv run --no-sync pytest -q \\
  tests/test_api/test_routes.py \\
  tests/test_api/test_handoff_routes.py \\
  tests/test_api/test_livekit_routes.py \\
  tests/test_api/test_two_factor_auth.py
24 passed in 1.08s
```

What those tests prove:

- Basic login, session binding and optional TOTP login work in the test configuration.
- Handoff listing/accept authorization works in the test configuration.
- LiveKit customer token validation works in the test configuration.

The repository also has standalone operator-token service coverage in [test_livekit_service.py](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/tests/test_backend/test_livekit_service.py), but that test was not part of the focused command above and does not exercise the HTTP route or browser flow.

What they do not prove:

- `test_handoff_routes.py` logs in the in-memory demo customer and temporarily mutates that same record's role to `OPERATOR`; it does not log in a durable seeded operator.
- There is no test for the HTTP `POST /api/v1/livekit/operator-token` route.
- No frontend test files, browser E2E test, or issue-specific `P160-F2-EDGE-003` regression test were found.
- No test proves login → queue polling → accept → token → Room join → connected state → AI shutdown as one user-visible flow.
- No live request or live database query was performed in this investigation, so issue resolution on `alosm.nairyuuu.site` is unverified.

## 6. Recommended next checks

Prioritize these checks in the live environment with the approved demo account and owner authorization:

1. Confirm the exact published phone number from the test handoff. Do not put the password in GitHub issues, logs or this verification note.
2. Inspect the live database through an authorized read-only path: confirm the phone row exists, `role=OPERATOR`, the account is not disabled by a separate policy, and the database schema is current. Do not run the development seed script against production; it explicitly blocks that environment.
3. Submit one live login attempt and record only safe evidence: HTTP status, sanitized response code/message, returned role if successful, and whether `/api/v1/auth/me` succeeds. This distinguishes credential/account failure from frontend routing failure.
4. After login succeeds, create a controlled pending handoff and verify: queue visibility, single-operator accept, operator-token issuance, join to the customer’s exact LiveKit Room, handoff status `connected`, and AI audio stopping after takeover.
5. Add durable coverage for an operator login fixture and an HTTP operator-token route test. Add a browser E2E test for the P0 path, including wrong-role, missing-account, expired-token and reconnect/disconnect cases.
6. Decide the supported provisioning contract for live: an approved admin/operator-management path or an audited migration/runbook. A development-only seed command is not sufficient evidence for a live P0 account.

## Conclusion

The local operator UI is present and connected to real backend/LiveKit contracts. The issue’s acceptance expectation is narrower and more fundamental: the published operator can log in on live and see the queue. Local evidence currently supports the UI and service wiring, but not live account provisioning or the complete production/staging E2E flow. The next owner action is live account/database verification, followed by the controlled takeover drill and missing regression tests.

# Verification sources

- [GitHub issue #24](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/issues/24)
- [GitHub issue #24 API](https://api.github.com/repos/AI20K-Build-Phase-Cohort-3/P-160/issues/24)
- [Current local source revision](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/tree/9028dc9f6bc2a2658a025a04e1662901895af1b7)
- [Historical operator UI commit](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/13b61d12728e4ab1686663a05d82328106bd4ac6)
- [Project source of truth](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/blob/9028dc9f6bc2a2658a025a04e1662901895af1b7/docs/PROJECT_SOURCE_OF_TRUTH.md)
