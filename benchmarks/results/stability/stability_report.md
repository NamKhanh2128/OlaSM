# B3 — Stability Benchmark Report

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
