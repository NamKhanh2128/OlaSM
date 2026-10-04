# Cleanup Baseline Status

- **Thời điểm ghi nhận:** 2026-10-04T16:25:00+07:00
- **Git Commit HEAD:** `fe8e6d47175bd3efb8324194f42d9a7a41a9b582`
- **Branch:** `main` (tracking `origin/main`)
- **Repository Root:** `C:\Users\KHANH\Documents\GitHub\OlaSM`

---

## 1. Lệnh kiểm tra đã thực thi

```powershell
git rev-parse HEAD
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
git status --ignored --short
```

---

## 2. Kết quả `git status --short --branch`

```text
## main...origin/main
 M src/agents/contracts/schemas.py
 M src/agents/core/booking/state.py
 M src/agents/core/guardrails.py
 M src/agents/core/instructions.py
 M src/agents/core/tools.py
 M src/agents/core/turn_policy.py
 M src/backend/services/agent_tool_executor.py
 M src/frontend/src/features/livekit/tokenSource.test.ts
 M src/frontend/src/pages/Operator/OperatorPage.tsx
 M src/voice_agent/tasks/booking.py
?? BaoCao_KyThuat_POC_Nhom4_OlaSM.docx
?? BaoCao_YTuong_Nhom4_OlaSM.docx
?? docs/AloSM_SECURITY_AND_GUARDRAILS_SPEC.md
?? docs/MERGE_ANALYSIS_OlaSM_OlaSM_Phuong.md
?? docs/PROJECT_CLEANUP_AUDIT.md
?? docs/PROMPT_AI_CLEANUP_OLA_SM.md
?? docs/PROMPT_AI_HOP_NHAT_OLA_SM.md
?? docs/merge/
?? migrations/versions/coe_001_offer_tables.py
?? scripts/generate_poc_docx.py
?? scripts/generate_poc_docx_clean.py
?? src/backend/services/confidence_fusion_service.py
?? src/backend/services/offer_engine.py
?? src/backend/services/offer_profile_service.py
?? src/backend/services/schedule_parser.py
?? src/backend/services/visual_grounding_service.py
?? src/frontend/src/features/operator/addressFormat.ts
?? src/frontend/src/features/operator/ticketDraft.ts
?? tests/test_audit_and_formulas_verification.py
?? tests/test_ported_donor_guardrails_and_schedule.py
?? ~$oCao_KyThuat_POC_Nhom4_OlaSM.docx
```

---

## 3. Kết quả `git diff --stat`

```text
 src/agents/contracts/schemas.py                    |   3 +
 src/agents/core/booking/state.py                   |  24 ++
 src/agents/core/guardrails.py                      | 174 +++++++++++-
 src/agents/core/instructions.py                    |  25 ++
 src/agents/core/tools.py                           |  40 +++
 src/agents/core/turn_policy.py                     |  33 ++-
 src/backend/services/agent_tool_executor.py        | 292 ++++++++++++++++++++-
 .../src/features/livekit/tokenSource.test.ts       |   2 +-
 src/frontend/src/pages/Operator/OperatorPage.tsx   |  43 ++-
 src/voice_agent/tasks/booking.py                   |  62 ++---
 10 files changed, 656 insertions(+), 42 deletions(-)
```

---

## 4. Phân loại trạng thái tệp ban đầu

| Phân loại | Số lượng | Danh sách tiêu biểu |
|---|---|---|
| **Tracked & Modified** | 10 | `src/backend/services/agent_tool_executor.py`, `src/voice_agent/tasks/booking.py`, `src/agents/core/guardrails.py`, etc. |
| **Untracked (New features & docs)** | 23 | `docs/merge/`, `docs/PROJECT_CLEANUP_AUDIT.md`, `src/backend/services/offer_engine.py`, `src/backend/services/schedule_parser.py`, etc. |
| **Ignored (Cache / Local / Env)** | 40+ | `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `asr_server/`, `src/voice/`, `.env`, `data/app.db`, etc. |

Tất cả các file modified và untracked ban đầu được bảo vệ nghiêm ngặt theo quy định `PROTECTED_UNTIL_EXPLICIT_CONFIRMATION`.
