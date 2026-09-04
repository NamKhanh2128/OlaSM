# B1 — Latency Benchmark Report

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