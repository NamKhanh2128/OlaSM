# P-160 AloSM — Benchmark Suite

## Tổng quan

Bộ benchmark đo lường 5 khía cạnh của sản phẩm AloSM:

| Module | Đo gì | Thời gian | Cost |
|---|---|---|---|
| **B1 — Latency** | STT/LLM/TTS/Tool/E2E latency | 10-30 phút | Cần API calls |
| **B2 — Cost** | Token usage, cost per booking | 15-30 phút | Cần API calls |
| **B3 — Stability** | Error rate, recovery, idempotency | 15-30 phút | Cần API calls |
| **B4 — AI Accuracy** | Entity extraction, intent, safety | 10-20 phút | Cần API calls |
| **B5 — E2E Functional** | Booking, correction, handoff, FAQ | 10-20 phút | Cần API calls |

## Yêu cầu

- Python 3.12+, `uv`
- Backend server đang chạy (`uv run uvicorn src.main:app`)
- `.env` đã cấu hình API keys
- `httpx` (đã có trong requirements)

## Chạy benchmark

### Dry-run (không cần server/API, dùng dữ liệu synthetic)

```bash
# Chạy tất cả benchmarks với dữ liệu giả
uv run python -m benchmarks.run_all --dry-run

# Chạy từng module
uv run python -m benchmarks.latency.run_latency_bench --dry-run
uv run python -m benchmarks.cost.run_cost_bench --dry-run
uv run python -m benchmarks.stability.run_stability_bench --dry-run
uv run python -m benchmarks.ai_accuracy.run_accuracy_bench --dry-run
uv run python -m benchmarks.e2e.run_e2e_bench --dry-run
```

### Chạy thực (cần backend server đang chạy)

```bash
# Bước 1: Khởi động backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Bước 2: Chạy benchmark (terminal khác)
uv run python -m benchmarks.run_all --samples 20

# Hoặc chạy từng module:
uv run python -m benchmarks.latency.run_latency_bench --samples 30
uv run python -m benchmarks.cost.run_cost_bench --samples 5
uv run python -m benchmarks.stability.run_stability_bench --samples 20 --concurrency 5
uv run python -m benchmarks.ai_accuracy.run_accuracy_bench
uv run python -m benchmarks.e2e.run_e2e_bench
```

### Chạy trên staging

```bash
VITE_API_URL=https://staging.alosm.nairyuuu.site uv run python -m benchmarks.run_all --samples 10
```

### Chỉ tạo report tổng hợp (sau khi đã chạy benchmark)

```bash
uv run python -m benchmarks.report_generator
```

## Output

Kết quả nằm trong `benchmarks/results/`:

```
benchmarks/results/
├── latency/
│   ├── latency_report.md          # Report markdown
│   └── latency-*.json             # Raw data per component
├── cost/
│   ├── cost_report.md
│   └── cost-raw-*.json
├── stability/
│   ├── stability_report.md
│   └── stability-raw-*.json
├── ai_accuracy/
│   ├── accuracy_report.md
│   └── accuracy-raw-*.json
├── e2e/
│   ├── e2e_report.md
│   └── e2e-raw-*.json
└── reports/
    └── benchmark_summary.md       # Dashboard tổng hợp
```

## Lưu ý quan trọng

1. **Sample size**: Dưới 20 samples chỉ ghi min/max/mean, KHÔNG tính p95 (theo hướng dẫn mentor)
2. **Cost**: Mỗi lần chạy benchmark tiêu tốn API credits. Dùng `--dry-run` để test pipeline
3. **Staging**: Benchmark trên staging có thể chậm hơn local do network latency
4. **Token estimates**: Token counts là ước tính heuristic. Bật token tracking ở provider để có số chính xác
