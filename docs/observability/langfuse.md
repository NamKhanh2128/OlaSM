# Langfuse observability

Langfuse nhận metric qua OTLP/HTTP. Backend và LiveKit worker dùng cùng schema,
nhưng chỉ gửi metadata đã allowlist; transcript, prompt, audio, tool arguments và
ID thô không được export.

## Cấu hình

```bash
LANGFUSE_ENABLED=true
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENVIRONMENT=development
LANGFUSE_FLUSH_TIMEOUT_SECONDS=5
```

Thiếu key hoặc `LANGFUSE_ENABLED=false` sẽ chuyển thành no-op. Backend flush ở
FastAPI lifespan; voice worker force-flush khi LiveKit job đóng.

## Metric được ghi nhận

| Observation | Dữ liệu |
| --- | --- |
| `agent_llm_decide` | model, input/output tokens, latency, tool/message outcome, error |
| `transcript_rewrite` | model, tokens, latency, confidence, rewrite reason, timeout/error |
| `livekit_llm` | model/provider, TTFT, duration, token usage, cache tokens |
| `livekit_stt` | model/provider, duration, audio duration, token usage |
| `livekit_tts` | model/provider, TTFB, duration, audio duration, characters/tokens |
| `livekit_vad` | inference duration/count, idle time |
| `livekit_turn_latency` | transcription, endpointing, LLM, TTS, playback và E2E latency |
| `livekit_tool` | tool name, status, duration |
| `livekit_error` | provider/model/error type, không có error message hay payload |

`session_id`, `user_id`, `call_id` và `turn_id` được SHA-256 trước khi gắn vào
span. Input/output LLM chỉ chứa fingerprint gồm hash và độ dài.

Langfuse tự tính LLM cost khi tên model khớp model definition và span có token
usage. STT/TTS có thêm `audio_seconds`/`characters`; nếu model definition mặc
định không có đơn giá tương ứng, cần cấu hình custom model price trong Langfuse.

## Dashboard và kiểm tra

Trong Langfuse, lọc theo observation name hoặc group theo model/provider để xem
latency p50/p95, token usage và cost. Dùng `langfuse.session.id` để gom các lượt
thuộc cùng phiên voice.

Regression tests không gọi Langfuse, LiveKit hay ElevenLabs API:

```bash
PYTEST_ADDOPTS='-p no:cacheprovider' .venv/bin/pytest -q \
  tests/test_backend/test_langfuse_observability.py \
  tests/test_voice_agent/test_observability.py \
  tests/test_voice_agent/test_transcript_rewrite.py
```

Tắt khẩn cấp bằng `LANGFUSE_ENABLED=false` và restart backend/worker. Luồng đặt
xe tiếp tục hoạt động vì telemetry luôn fail-open.
