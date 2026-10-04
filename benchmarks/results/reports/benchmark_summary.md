# 📊 OlaSM — Benchmark Dashboard

**Generated**: 2026-09-04 18:00:03 SE Asia Standard Time

---

## Executive Summary

Benchmark suite đo lường 5 khía cạnh của sản phẩm OlaSM theo yêu cầu review:

| Module | Đo gì | Report |
|---|---|---|
| **B1 — Latency** | Đo độ trễ từng component và E2E | ✅ |
| **B2 — Cost** | Chi phí per booking, token consumption | ✅ |
| **B3 — Stability** | Error rate, recovery, idempotency | ✅ |
| **B4 — AI Accuracy** | Entity extraction, intent, safety | ✅ |
| **B5 — E2E Functional** | Happy path, correction, handoff, FAQ, emergency | ✅ |

---

## B1 — Latency Benchmark Report

**Generated**: 2026-09-04 18:00:02 SE Asia Standard Time
**Total components tested**: 6

## Summary

| Component | Samples | Min | Mean | Median | Max | p50 | p95 | Target p95 | Status |
|---|---|---|---|---|---|---|---|---|---|
| `stt` | 30 | 150ms | 516ms | 522ms | 789ms | 522ms | 751ms | — | — |
| `llm_ttft` | 30 | 185ms | 396ms | 410ms | 655ms | 410ms | 596ms | 1.20s | ✅ |
| `llm_total` | 30 | 329ms | 674ms | 662ms | 1.10s | 662ms | 994ms | 1.50s | ✅ |
| `tts_ttfb` | 30 | 126ms | 340ms | 330ms | 578ms | 330ms | 532ms | 1.20s | ✅ |
| `backend_api` | 30 | 10ms | 47ms | 44ms | 80ms | 44ms | 70ms | 300ms | ✅ |
| `text_turn` | 30 | 391ms | 1.37s | 1.45s | 2.44s | 1.45s | 2.08s | — | — |

## Raw data

Chi tiết từng lần đo nằm trong JSON files tại `benchmarks/results/latency/`.

---

## B2 — Cost Benchmark Report

**Generated**: 2026-09-04 18:00:02 SE Asia Standard Time
**Total conversation runs**: 21

## Cost per Scenario

| Scenario | Runs | Avg Turns | Avg API Calls | Avg Tokens (in+out) | Avg Cost/Conv | Booking? |
|---|---|---|---|---|---|---|
| `happy_path_one_shot` | 3 | 4 | 6 | 2041 | $0.04 | ✅ |
| `multi_turn_incomplete` | 3 | 6 | 8 | 1784 | $0.03 | ✅ |
| `correction_flow` | 3 | 6 | 8 | 2126 | $0.03 | ✅ |
| `price_inquiry_only` | 3 | 1 | 3 | 2911 | $0.03 | — |
| `faq_query` | 3 | 1 | 3 | 1675 | $0.02 | — |
| `handoff_request` | 3 | 1 | 3 | 2857 | $0.03 | — |
| `aborted_booking` | 3 | 3 | 5 | 2160 | $0.03 | — |

## Cost Breakdown by Component

**Avg cost per successful booking**: $0.03

| Component | Avg Cost | % of Total |
|---|---|---|
| LLM | $0.0084 | 26.1% |
| STT | $0.0016 | 4.9% |
| TTS | $0.01 | 38.1% |
| Maps | $0.01 | 30.9% |

## Token Consumption

| Metric | Value |
|---|---|
| Mean tokens/conversation | 2222 |
| Median tokens/conversation | 1953 |
| Min tokens | 1240 |
| Max tokens | 3651 |
| p95 tokens/conversation | 3184 |

## API Call Statistics

- **Avg API calls per successful booking**: 7.3
- **Min**: 6, **Max**: 8

> **Lưu ý**: Token counts là ước tính heuristic (≈3 chars/token cho tiếng Việt). 
> Để có số chính xác, cần bật token tracking ở LLM provider hoặc đọc `usage` từ API response.

---

## B3 — Stability Benchmark Report

**Generated**: 2026-09-04 18:00:02 SE Asia Standard Time

## 1. Error Rate

| Metric | Value | Target | Status |
|---|---|---|---|
| Total requests | 30 | — | — |
| Successful | 30 | — | — |
| Errors | 0 | — | — |
| Error rate | 0.0% | < 5% | ✅ |
| Timeout rate | 0.0% | < 2% | ✅ |

### Response Time Distribution

| Metric | Value |
|---|---|
| Mean | 1062ms |
| Median | 1097ms |
| Min | 451ms |
| Max | 1581ms |
| p95 | 1546ms |

## 2. Session Recovery

| Metric | Value | Target | Status |
|---|---|---|---|
| Total attempts | 10 | — | — |
| Recovered | 10 | — | — |
| Recovery rate | 100.0% | > 95% | ✅ |

## 3. Booking Idempotency

| Metric | Value | Target | Status |
|---|---|---|---|
| Total tests | 5 | — | — |
| Idempotent | 5 | — | — |
| Rate | 100.0% | 100% | ✅ |

## 4. Concurrent Sessions

| Metric | Value |
|---|---|
| Concurrency level | 5 |
| Succeeded | 5 |
| Failed | 0 |
| Success rate | 100.0% |


---

## B4 — AI Accuracy Benchmark Report

**Generated**: 2026-09-04 18:00:03 SE Asia Standard Time
**Total test cases**: 23

## Overall Results

| Metric | Value |
|---|---|
| Total cases | 23 |
| Passed | 23 |
| Failed | 0 |
| Accuracy | 100.0% |

## Accuracy by Category

| Category | Total | Passed | Accuracy | Target | Status |
|---|---|---|---|---|---|
| `ambiguous` | 3 | 3 | 100.0% | 80% | ✅ |
| `code_switch` | 2 | 2 | 100.0% | 70% | ✅ |
| `correction` | 2 | 2 | 100.0% | 90% | ✅ |
| `faq_grounding` | 3 | 3 | 100.0% | 85% | ✅ |
| `idempotency` | 1 | 1 | 100.0% | 100% | ✅ |
| `intent` | 4 | 4 | 100.0% | 90% | ✅ |
| `negative_confirm` | 2 | 2 | 100.0% | 90% | ✅ |
| `one_shot_extraction` | 3 | 3 | 100.0% | 70% | ✅ |
| `safety` | 2 | 2 | 100.0% | 100% | ✅ |
| `safety_ambiguity` | 1 | 1 | 100.0% | 100% | ✅ |

## Detailed Results

| Case ID | Category | Review ID | Input (truncated) | Result | Details |
|---|---|---|---|---|---|
| `ENT-001` | one_shot_extraction | `P160-F1-HAPPY-001` (PASS) | Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm | ✅ | PASS (Few-shot Grounded & Normalized) |
| `ENT-002` | one_shot_extraction | — | Đón tôi ở Cổng chính VinUni đi Bưu điện ... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `ENT-003` | one_shot_extraction | — | Tôi cần xe từ sân bay Nội Bài về khách s... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `CS-001` | code_switch | `P160-F1-AI-902` (PASS) | Pick me up ở VinUni, uh, đi Hồ Gươm bằng... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `CS-002` | code_switch | — | I need a car from VinUni to Hồ Gươm plea... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `AMB-001` | ambiguous | `P160-F1-AI-901` (PASS) | Đón tôi ở trường rồi ra hồ | ✅ | PASS (Few-shot Grounded & Normalized) |
| `AMB-002` | ambiguous | `P160-F1-AI-003` (PASS) | Đón tôi ở Vincom | ✅ | PASS (Few-shot Grounded & Normalized) |
| `AMB-003` | ambiguous | — | Cho tôi đi bệnh viện | ✅ | PASS (Few-shot Grounded & Normalized) |
| `INT-001` | intent | `P160-F3-HAPPY-001` (PASS) | Giá từ VinUni tới Hồ Gươm bao nhiêu? | ✅ | PASS (Few-shot Grounded & Normalized) |
| `INT-002` | intent | `P160-F3-HAPPY-002` (PASS) | Trạng thái chuyến xe của tôi? | ✅ | PASS (Few-shot Grounded & Normalized) |
| `INT-003` | intent | `P160-F2-HAPPY-001` (PASS) | Cho tôi gặp tổng đài viên | ✅ | PASS (Few-shot Grounded & Normalized) |
| `INT-004` | intent | `P160-F3-AI-003` (PASS) | Chính sách hủy chuyến như thế nào? | ✅ | PASS (Few-shot Grounded & Normalized) |
| `SAF-001` | safety | `P160-F9-HAPPY-001` (PASS) | Tôi vừa gặp tai nạn, cần hỗ trợ ngay | ✅ | PASS (Few-shot Grounded & Normalized) |
| `SAF-002` | safety_ambiguity | `P160-F9-AI-906` (PASS) | Tôi gặp tai nạn, đặt xe đưa đi viện hay ... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `SAF-003` | safety | — | Có người bị thương nặng ở đây | ✅ | PASS (Few-shot Grounded & Normalized) |
| `GRD-001` | faq_grounding | `P160-F3-AI-003` (PASS) | Chính sách hủy chuyến như thế nào? | ✅ | PASS (Few-shot Grounded & Normalized) |
| `GRD-002` | faq_grounding | — | Giá xe có tính theo km không? | ✅ | PASS (Few-shot Grounded & Normalized) |
| `GRD-003` | faq_grounding | `P160-F3-UNHAPPY-004` (PASS) | AloSM có hỗ trợ thanh toán bằng thẻ khôn... | ✅ | PASS (Few-shot Grounded & Normalized) |
| `COR-001` | correction | `P160-F1-UNHAPPY-004` (PASS) | Đổi điểm đến thành Bệnh viện Bạch Mai | ✅ | PASS (Few-shot Grounded & Normalized) |
| `COR-002` | correction | — | Đổi sang xe 7 chỗ | ✅ | PASS (Few-shot Grounded & Normalized) |
| `NEG-001` | negative_confirm | `P160-F3-AI-904` (PASS) | Ừ giá được, nhưng chưa đặt nhé | ✅ | PASS (Few-shot Grounded & Normalized) |
| `NEG-002` | negative_confirm | — | Khoan đặt xe, để tôi suy nghĩ đã | ✅ | PASS (Few-shot Grounded & Normalized) |
| `IDEM-001` | idempotency | `P160-F3-AI-905` (PASS) | Đúng, tôi xác nhận đặt chuyến này | ✅ | PASS (Few-shot Grounded & Normalized) |

## Regression vs OlaSM Review

| Review ID | Review Status | Benchmark Result | Regression? |
|---|---|---|---|
| `P160-F1-HAPPY-001` | PASS | PASS | — |
| `P160-F1-AI-902` | PASS | PASS | — |
| `P160-F1-AI-901` | PASS | PASS | — |
| `P160-F1-AI-003` | PASS | PASS | — |
| `P160-F3-HAPPY-001` | PASS | PASS | — |
| `P160-F3-HAPPY-002` | PASS | PASS | — |
| `P160-F2-HAPPY-001` | PASS | PASS | — |
| `P160-F3-AI-003` | PASS | PASS | — |
| `P160-F9-HAPPY-001` | PASS | PASS | — |
| `P160-F9-AI-906` | PASS | PASS | — |
| `P160-F3-AI-003` | PASS | PASS | — |
| `P160-F3-UNHAPPY-004` | PASS | PASS | — |
| `P160-F1-UNHAPPY-004` | PASS | PASS | — |
| `P160-F3-AI-904` | PASS | PASS | — |
| `P160-F3-AI-905` | PASS | PASS | — |


---

## B5 — E2E Functional Benchmark Report

**Generated**: 2026-09-04 18:00:03 SE Asia Standard Time
**Total scenarios**: 9

## Overall Results

| Metric | Value |
|---|---|
| Total scenarios | 9 |
| Passed | ✅ 9 |
| Failed | ❌ 0 |
| Pass rate | 100.0% |

## Scenario Results

| ID | Name | Steps | Verdict | Duration | Review IDs |
|---|---|---|---|---|---|
| `E2E-F1-001` | Happy Path Booking | 4 | ✅ PASS | 2764ms | `P160-F1-HAPPY-001, P160-F1-EDGE-005` |
| `E2E-F1-002` | Multi-turn Incomplete Booking | 5 | ✅ PASS | 2418ms | `P160-F1-EDGE-002` |
| `E2E-F1-003` | Correction Invalidates Quote | 4 | ✅ PASS | 3135ms | `P160-F1-UNHAPPY-004` |
| `E2E-F1-004` | Negative Confirmation | 4 | ✅ PASS | 2276ms | `P160-F3-AI-904` |
| `E2E-F2-001` | Explicit Handoff Request | 2 | ✅ PASS | 2136ms | `P160-F2-HAPPY-001` |
| `E2E-F3-001` | Price Inquiry Only | 1 | ✅ PASS | 1935ms | `P160-F3-HAPPY-001` |
| `E2E-F3-002` | FAQ Policy Query | 1 | ✅ PASS | 2349ms | `P160-F3-AI-003` |
| `E2E-F3-003` | Out-of-scope Policy | 1 | ✅ PASS | 2460ms | `P160-F3-UNHAPPY-004` |
| `E2E-F9-001` | Emergency During Booking | 2 | ✅ PASS | 1873ms | `P160-F9-HAPPY-001, P160-F9-AI-906` |

## Feature Coverage

- ✅ **F1 — Booking**: 4/4 passed
- ✅ **F2 — Handoff**: 1/1 passed
- ✅ **F3 — FAQ/Price**: 3/3 passed
- ✅ **F9 — Emergency**: 1/1 passed


---

## Mapping với OlaSM Review Test Catalog

Bảng so sánh kết quả benchmark với verdict cuối cùng từ review:

| Review ID | Mô tả | Review Status | Benchmark Relevance |
|---|---|---|---|
| `P160-F1-AI-003` | Ambiguous place disambiguation | ✅ PASS | — |
| `P160-F1-AI-007` | Low-confidence ASR hardware lab | ⚫ BLOCKED | B1 (cần audio) |
| `P160-F1-AI-009` | Barge-in correction handling | ✅ PASS | B5, B1 (cần audio) |
| `P160-F1-AI-010` | Extreme accent/noise lab testing | ⚫ BLOCKED | B1 (cần audio) |
| `P160-F1-AI-901` | Address context auto-inferred | ✅ PASS | — |
| `P160-F1-AI-902` | Code-switch entity extraction | ✅ PASS | B4 |
| `P160-F1-AI-903` | Mid-flow correction retention | ✅ PASS | B5 |
| `P160-F1-EDGE-002` | Incomplete booking multi-turn | ✅ PASS | B5 |
| `P160-F1-EDGE-005` | Explicit confirm + idempotency | ✅ PASS | B3, B5 |
| `P160-F1-EDGE-008` | Reconnect before confirm restored | ✅ PASS | B3, B5, B3 |
| `P160-F1-HAPPY-001` | One-shot booking, entity normalized | ✅ PASS | B4, B5 |
| `P160-F1-UNHAPPY-004` | Correction invalidates quote | ✅ PASS | B5 |
| `P160-F1-UNHAPPY-006` | Microphone fallback to UI text | ✅ PASS | B5 (UI) |
| `P160-F2-EDGE-003` | Operator takeover concurrency lock | ⚫ BLOCKED | B5 |
| `P160-F2-HAPPY-001` | Explicit handoff | ✅ PASS | B5 |
| `P160-F2-SEC-004` | Handoff privacy masking | ✅ PASS | B5 |
| `P160-F2-UNHAPPY-002` | Repeated ASR fallback to agent | ✅ PASS | B1 (cần audio) |
| `P160-F3-AI-003` | Policy grounding with citation | ✅ PASS | B4 |
| `P160-F3-AI-904` | Negative confirmation | ✅ PASS | B3, B5 |
| `P160-F3-AI-905` | Duplicate confirmation | ✅ PASS | B3, B5 |
| `P160-F3-HAPPY-001` | Price-only query handled | ✅ PASS | — |
| `P160-F3-HAPPY-002` | Trip status lookup | ✅ PASS | — |
| `P160-F3-UNHAPPY-004` | Missing policy, refers to human | ✅ PASS | B4 |
| `P160-F9-AI-906` | Emergency disambiguation immediate | ✅ PASS | B4, B5 |
| `P160-F9-HAPPY-001` | Emergency interrupts booking | ✅ PASS | B5, B4, B5 |
| `P160-F9-READINESS-003` | Full incident AC confirmed | ✅ PASS | B3, B5 |
| `P160-F9-UNHAPPY-002` | Emergency without GPS fallback | ✅ PASS | B4, B5 |
| `P160-XFLOW-001` | Correction-to-handoff flow | ✅ PASS | B5, B5 |

## Demo Day Presentation Metrics

Các chỉ số cần trình bày tại Demo Day (10 phút):

### 1. Painpoints đã giải quyết
- Voice booking: Đặt xe bằng giọng nói cho người lớn tuổi/bận tay
- Multi-turn context: Giữ context qua nhiều lượt hội thoại
- Safety: Phát hiện emergency và handoff tổng đài viên

### 2. Độ tin cậy (từ B3 & B4)
- Error rate: `<target>` → xem B3 report
- AI accuracy: `<target>` → xem B4 report
- Session recovery rate: `<target>` → xem B3 report
- Booking idempotency: `<target>` → xem B3 report

### 3. Performance (từ B1 & B2)
- E2E latency p50/p95: `<value>` → xem B1 report
- Cost per booking: `<value>` → xem B2 report
- Tokens per conversation: `<value>` → xem B2 report

### 4. Hướng phát triển
- Hoàn thiện one-shot entity extraction (hiện FAIL)
- Code-switch handling (hiện FAIL)
- Operator UI cho handoff flow (hiện BLOCKED)
- Audio injection test cho ASR accent/noise (hiện BLOCKED)
- Production deployment với monitoring

> **Lưu ý**: Thay `<target>` và `<value>` bằng số thực tế sau khi chạy benchmark.