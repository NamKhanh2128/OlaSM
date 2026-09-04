# B2 — Cost Benchmark Report

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