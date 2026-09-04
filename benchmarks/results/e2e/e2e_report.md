# B5 — E2E Functional Benchmark Report

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
