# Chỉ mục tài liệu AloSM Voice

Cập nhật: **2026-08-27** · Trạng thái: CURRENT.

## Đọc theo thứ tự

1. [README.md](../README.md) — setup, chạy local và các lệnh kiểm tra.
2. [LIVEKIT_TEAM_SETUP.md](LIVEKIT_TEAM_SETUP.md) — chạy voice worker và troubleshooting.
3. [PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md) — trạng thái runtime và external blockers.
4. [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md), [PRD_AloSM_Voice.md](PRD_AloSM_Voice.md) — product requirements.
5. [architecture_diagram.md](architecture_diagram.md) — system design hiện hành.
6. [evaluation.md](evaluation.md) — reproducible evaluation và review evidence.
7. [verification/release-readiness.md](verification/release-readiness.md) — readiness/evidence.
8. [../mustdo.md](../mustdo.md) — việc bắt buộc cần owner/hạ tầng.

Scope mentor gốc được giữ tại [GSM-08_VOICE_AGENT_SCOPE.md](GSM-08_VOICE_AGENT_SCOPE.md).

## Tài liệu hiện hành

| Nhóm | Tài liệu |
|---|---|
| Product | [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md), [PRD_AloSM_Voice.md](PRD_AloSM_Voice.md) |
| Architecture | [architecture_diagram.md](architecture_diagram.md), [PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md) |
| LiveKit runtime | [LIVEKIT_TEAM_SETUP.md](LIVEKIT_TEAM_SETUP.md) |
| Evaluation | [evaluation.md](evaluation.md), [verification/README.md](verification/README.md), [verification/release-readiness.md](verification/release-readiness.md), [eval_cases/README.md](../eval_cases/README.md) |
| AI/voice evidence | [voice-ai/README.md](voice-ai/README.md), [voice-ai/tts-output-live-report.json](voice-ai/tts-output-live-report.json) |
| Agent | [src/agents/README.md](../src/agents/README.md), [src/agents/docs/](../src/agents/docs/) |
| Backend | [src/backend/README.md](../src/backend/README.md) |
| Frontend | [src/frontend/README.md](../src/frontend/README.md), [src/frontend/docs/](../src/frontend/docs/) |
| Data | [data/README.md](../data/README.md), [data/catalog.json](../data/catalog.json) |
| Performance/Policy | [performance/latency-remediation-plan.md](performance/latency-remediation-plan.md), [policies/policy-integration-plan.md](policies/policy-integration-plan.md) |
| Team history | [journal.md](journal.md), [worklog.md](worklog.md) |

## Reference tách biệt

`docs/guide/` và `specification_documents/` chỉ chứa tài liệu khóa học/template tham khảo,
không phải runtime status hoặc contract của AloSM. `presentation/` là khu vực deliverable trình bày.
Proposal/prompt/TODO đã bị implementation hoặc `mustdo.md` thay thế được loại khỏi
cây hiện hành; dùng Git history khi cần truy vết.

Mọi thay đổi runtime phải cập nhật contract/status liên quan trong cùng PR. Không tạo progress diary
hoặc duplicate TODO; blocker ngoài repository chỉ ghi tại `mustdo.md`.
