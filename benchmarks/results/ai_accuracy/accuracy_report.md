# B4 — AI Accuracy Benchmark Report

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
| `GRD-003` | faq_grounding | `P160-F3-UNHAPPY-004` (PASS) | OlaSM có hỗ trợ thanh toán bằng thẻ khôn... | ✅ | PASS (Few-shot Grounded & Normalized) |
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
