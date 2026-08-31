# Langfuse observability — LLM cost / latency

> Nhánh: `perf/langfuse-observability` (child của `develop`). Không log transcript thô/PII.

## Bật / tắt

```bash
# .env
LANGFUSE_ENABLED=true
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

- `LANGFUSE_ENABLED=false` (default) hoặc thiếu key → **no-op**, không crash, không block request.
- `Settings` ở `src/backend/config.py`, flush ở `src/backend/main.py:lifespan` shutdown.

## Trace model

```
trace(session_id hash) → generation(agent_llm_decide / transcript_rewrite / livekit_llm)
  input: sha256(preview) hoặc truncated 200 chars + [hash:... redacted]
  metadata: { latency_ms, turn_id, model }
  usage: { prompt_tokens, completion_tokens } → cost tự tính theo price table Langfuse
```

- `src/agents/core/model.py:OpenAIConversationModel.decide` đã bọc generation.
- Voice path (`src/voice_agent/transcript_rewrite.py`, `src/voice_agent/server.py`) kế thừa cùng helper `src/backend/observability/langfuse_client.py`.

## Dashboard

- Langfuse Cloud → Project → Traces: filter `name=agent_llm_decide`, group by `model`, xem `latency p50/p95`, `cost`.
- Không bật `LANGFUSE_ENABLED` trong CI — test mock `get_langfuse() -> None`.

## Rollback

Revert commit `feat(observability): integrate Langfuse...` hoặc set `LANGFUSE_ENABLED=false` + restart — không ảnh hưởng nhánh `perf/backend-tracing` / `perf/frontend-latency`.
