# AloSM — Evaluation evidence

Cập nhật: **2026-08-27** · Branch: `feature/agentic-ai`.

Tài liệu này là entrypoint cho evidence có thể tái chạy của bản code hiện tại. Các
số liệu live/provider chưa có corpus và sign-off thì không được trình bày như số đo
production.

## 1. Lệnh tái chạy

Từ repository root:

```bash
uv sync
uv run pytest -q
uv run ruff check src tests scripts eval_cases
uv run python -m eval_cases.run_agent_workflow_evals
cd src/frontend && npm ci && npm run lint && npm run build
```

Full non-live suite hiện chạy với SQLite/in-memory test boundary, không cần API key:

- `459 passed, 3 skipped`;
- Ruff pass trên source, tests, scripts và eval cases;
- frontend lint/build pass; build vẫn có cảnh báo bundle lớn cần tối ưu sau.

## 2. Workflow evidence

Bộ [agent workflow evals](../eval_cases/README.md) chạy Core Agent, typed state,
guardrails, `SessionService` và backend tool executor thật ở chế độ deterministic,
không gọi mạng. Sáu case hiện hành:

| Case | Điều được kiểm chứng |
|---|---|
| `AGENT-001` | Đặt xe từ VinUni đến Hồ Gươm, chọn candidate, báo giá, xác nhận, tạo booking |
| `AGENT-002` | Đổi điểm đón sau khi từ chối summary; quote cũ bị hủy, route và quote mới được tạo |
| `AGENT-003` | Đổi điểm đến sau khi từ chối summary; giữ điểm đón và loại xe |
| `AGENT-004` | Đổi loại xe; chỉ gọi lại fare estimate cần thiết |
| `AGENT-005` | Câu hỏi ngoài phạm vi không làm phát sinh booking side effect |
| `AGENT-006` | Yêu cầu gặp người thật tạo handoff và giữ context an toàn |

Artifact chi tiết được sinh tại [eval_cases/agent_workflow_eval_summary.json](../eval_cases/agent_workflow_eval_summary.json) và các file JSON trong [eval_cases/results/](../eval_cases/results/).

## 3. Test boundary quan trọng

- Place search dùng gazetteer trong `data/gazetteer/`, có fallback static cho Docker;
  fuzzy/multiple match không tự chọn im lặng.
- Pricing dùng catalog versioned trong `data/pricing/`; quote có ID, expiry và
  kiểm tra ownership/context trước create.
- Confirmation là explicit; `create_booking` chỉ chạy sau state confirmed và có
  idempotency key.
- Đổi pickup, destination hoặc vehicle làm quote/confirmation cũ mất hiệu lực.
- Handoff, low-confidence ASR, provider failure và unknown side effect có fallback
  theo contract thay vì tự bịa kết quả.

## 4. Voice/LiveKit evidence

Runtime voice nằm tại [voice-ai/README.md](voice-ai/README.md) và
[voice-ai/voice-runtime-architecture.md](voice-ai/voice-runtime-architecture.md).
Pipeline hiện hành là:

```text
LiveKit Room/WebRTC
  -> AgentServer + AgentSession
  -> Silero VAD / endpointing
  -> LiveKit Inference STT (Deepgram Nova-3, multi)
  -> AloSM Agent + typed booking tools
  -> OpenAI LLM / function tools
  -> Google Gemini Flash TTS (Kore, vi-VN)
  -> Google Chirp 3 HD fallback
```

Debug JSONL và transcript chỉ được ghi khi bật opt-in trong `.env`; mặc định không
lưu raw audio hoặc raw transcript. LiveKit Cloud/provider quota, browser microphone,
reconnect, device matrix và human listening vẫn là release gates; xem
[verification/release-readiness.md](verification/release-readiness.md).

## 5. Review handoff

Source of truth: [PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md).
System design: [architecture_diagram.md](architecture_diagram.md).
Product requirements vẫn giữ format và feature roadmap ban đầu tại
[PRD_AloSM_Voice.md](PRD_AloSM_Voice.md), đồng thời đánh dấu rõ những thay đổi đã
triển khai và phần chưa có provider thật.
