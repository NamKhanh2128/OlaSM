# Worklog — Agentic AI và LiveKit Voice

> Đây là bản ghi lịch sử triển khai, được tổng hợp từ Git/PR. Trạng thái runtime hiện hành vẫn được xác định bởi code, migration, test và [PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md).

## Phạm vi

- Nhánh: `feature/agentic-ai`
- PR chính: [#10 — Feature/agentic ai](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/10)
- PR merge vào `develop`: **24/08/2026**, merge commit `efce5ca`
- PR gồm **66 commit**, GitHub ghi nhận **720 file**, `+50,587 / -25,326` dòng.
- Sau khi PR merge, nhánh tiếp tục có ba commit hoàn thiện: `5fbd041`, `2030171`, `3b1fa9d`.

## Tóm tắt kết quả

PR đã chuyển voice runtime sang kiến trúc LiveKit-native và nối voice với cùng domain contract của text agent. Các phần chính đã được triển khai:

- Core Agent model-driven với typed state, tool loop, conversation history, contextual understanding, repair và interruption.
- Booking flow có tìm/chọn địa điểm, chọn loại xe, quote, explicit confirmation và idempotency.
- LiveKit Room + native `AgentServer`/`AgentSession`, frontend voice session và backend token/control plane.
- Cấu hình/factory cho STT, LLM, TTS; fallback khi provider lỗi hoặc timeout; text fallback khi voice không khả dụng.
- Handoff sang operator với queue, context, operator token và takeover cùng LiveKit Room.
- Durable voice/session state, optimistic revision, quote integrity và các migration liên quan.
- Approved policy/FAQ, pricing demo có version, gazetteer địa điểm và bộ script/evidence cho evaluation.
- Setup/runbook cho teammate, deployment, observability và privacy-aware debug logging.

## Timeline theo commit

| Thời điểm | Commit tiêu biểu | Nội dung đã thực hiện |
|---|---|---|
| 13/08 | [`c698899`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/c698899), [`47ebcb2`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/47ebcb2), [`58c9177`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/58c9177) | Định nghĩa history contract, lifecycle của turn, hiểu ngữ cảnh, sửa hội thoại và xử lý interruption; bổ sung test hardening. |
| 15–16/08 | [`86cfe2e`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/86cfe2e), [`8519dd5`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/8519dd5), [`0e9506b`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/0e9506b) | Chuyển sang model-driven tool architecture; tích hợp lại frontend voice popup/hands-free, persistence, quote integrity, maps, policy và các sửa lỗi ASR/UI/auth. |
| 18/08 | [`54a764e`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/54a764e) | Tạo baseline LiveKit-native: backend LiveKit routes/service, frontend room session, voice worker, booking tools, state persistence, migrations và smoke runner. |
| 19–20/08 | [`df0c1f3`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/df0c1f3), [`80c1d1a`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/80c1d1a) | Hardening voice backend, state recovery, handoff, observability, TTS text handling, latency plan và test suite cho server/config/persistence/booking. |
| 22/08 | [`83b685c`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/83b685c), [`0d3765f`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/0d3765f) | Cập nhật implementation theo runtime mới, loại bỏ đường chạy voice legacy khỏi happy path, thêm release/evaluation artifacts và chuẩn hóa setup teammate. |
| 24/08 | [`270e849`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/270e849) | Hoàn thiện handoff LiveKit, reconnect/session handling, state publish/restore, structured events, frontend call flow và tài liệu vận hành. Đây là commit cuối của PR #10. |

## Follow-up sau PR #10

Các commit dưới đây đang có trên `feature/agentic-ai` nhưng không nằm trong head của PR #10 tại thời điểm merge:

| Commit | Thay đổi |
|---|---|
| [`5fbd041`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/5fbd041) | Refactor model factory cho STT/LLM/TTS, giảm trách nhiệm của server và bổ sung test booking/observability. |
| [`2030171`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/2030171) | Bổ sung một lần xác nhận bằng nút bấm khi người dùng yêu cầu hủy chuyến; cập nhật session data, frontend contract và booking tests. |
| [`3b1fa9d`](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/commit/3b1fa9d) | Điều chỉnh ASR timeout trong `.env.example`. |

## Các luồng nghiệp vụ đã có

1. Người dùng đăng nhập, tạo/resume session và dùng text hoặc voice.
2. Agent thu thập pickup, destination và vehicle; địa điểm chưa resolve không được tự coi là hợp lệ.
3. Backend tạo quote có tính xác định; thay đổi địa điểm hoặc loại xe làm mất hiệu lực quote/confirmation cũ.
4. Chỉ confirmation rõ ràng mới cho phép tạo booking; retry dùng idempotency để tránh đặt trùng.
5. Người dùng có thể tra cứu/hủy booking theo cơ chế xác nhận.
6. Câu hỏi FAQ phải dựa trên policy/knowledge được phê duyệt; case ngoài phạm vi hoặc rủi ro cao có thể handoff.
7. Operator nhận case, vào cùng room và tiếp quản context; AI dừng audio khi takeover hợp lệ.

## Kiểm chứng và evidence

Các lệnh tái chạy được ghi trong [README.md](../README.md), [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md) và [PHASE4_RELEASE_RUNBOOK.md](PHASE4_RELEASE_RUNBOOK.md). PR đã bổ sung/cập nhật test cho voice agent, API/backend, script smoke/evaluation và frontend.

Trạng thái evidence đã commit:

- Workflow eval có **6 case**, trong đó **3 pass / 3 fail**; summary ghi `overall_status: failed` và `pytest_exit_code: 1` tại [agent_workflow_eval_summary.json](../eval_cases/agent_workflow_eval_summary.json).
- LiveKit Phase 4 product run có **9/10 attempt pass**; một attempt lỗi ở `quote_confirmation`. Business invariants ghi **1 violation**, vì vậy run chưa đạt release gate tại [report.md](../reports/voice-evaluation/phase4-product/phase4_run/report.md).
- GitHub checks của PR #10 tại thời điểm merge ghi nhận `backend: fail` và `frontend: fail`.

Các kết quả trên chứng minh đã có pipeline/evidence để kiểm thử, nhưng chưa đủ cơ sở gọi hệ thống là production-ready.

## Việc cần tiếp tục

- Điều tra và sửa lỗi `quote_confirmation`, sau đó chạy lại workflow eval và durable LiveKit smoke.
- Xác định nguyên nhân một business invariant violation; xác nhận không có booking thiếu confirmation hoặc duplicate booking.
- Chạy lại backend/frontend CI, full test, lint và build sau các follow-up commit.
- Hoàn tất browser/device matrix, reconnect, multi-tab, provider-failure và ASR benchmark có audio được consent.
- Hoàn thiện các tích hợp còn ngoài phạm vi demo: fleet/dispatch thật, payment/refund, CRM, emergency flow, SLA/load/soak và production monitoring.

