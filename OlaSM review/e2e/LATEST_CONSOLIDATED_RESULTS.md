# P-160 — Kết quả E2E Last Gate hợp nhất

- Cutoff: `2026-09-03`.
- Source pin: `origin/main@74c6a06dda9ba506c9b57dbec09ca88858281e75`.
- Cách hợp nhất: lấy verdict trong blocker-completion làm kết quả mới hơn khi một stable ID xuất hiện ở cả hai run; các ID còn lại lấy từ fail-regression.
- Phạm vi này là **Last Gate queue**, không thay thế catalog đầy đủ nằm tại `FULL_TEST_CATALOG.md`.
- `BLOCKED` nghĩa là chưa tới được oracle do thiếu precondition/fixture/quyền điều khiển sau khi đã thử bề mặt user-facing; không được hiểu là PASS hoặc FAIL.

## Tổng

- **25 stable ID**.
- **PASS 7 · FAIL 9 · FLAKY 0 · BLOCKED 9 · NOT_RUN 0 · INVALID 0**.

## Verdict theo stable ID

| Stable ID | Verdict | Nguồn verdict mới nhất |
|---|---|---|
| `P160-F1-AI-007` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-AI-009` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-AI-010` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-AI-901` | **FAIL** | [Chi tiết và evidence](FAIL_REGRESSION_20260902-144231.md) |
| `P160-F1-AI-902` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-AI-903` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-EDGE-005` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-EDGE-008` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-HAPPY-001` | **FAIL** | [Chi tiết và evidence](FAIL_REGRESSION_20260902-144231.md) |
| `P160-F1-UNHAPPY-004` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F1-UNHAPPY-006` | **FAIL** | [Chi tiết và evidence](FAIL_REGRESSION_20260902-144231.md) |
| `P160-F2-EDGE-003` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F2-HAPPY-001` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F2-UNHAPPY-002` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-AI-003` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-AI-904` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-AI-905` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-HAPPY-001` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-HAPPY-002` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F3-UNHAPPY-004` | **PASS** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F9-AI-906` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F9-HAPPY-001` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F9-READINESS-003` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-F9-UNHAPPY-002` | **FAIL** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
| `P160-XFLOW-001` | **BLOCKED** | [Chi tiết và evidence](BLOCKER_COMPLETION_20260902-225202.md) |
