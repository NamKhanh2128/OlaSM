# PROMPT CHO AI: Khánh, voice agent và backend demo Green SM

> Cách dùng: mở repo OlaSM ở thư mục gốc, đưa toàn bộ file này cho AI coding agent. Có thể chạy lại nhiều lần: AI tự tiếp tục từ phase chưa xong, nhận biết bằng commit `feat(agent): K<số> ...` trên nhánh `feat/greensm-demo-agent` và bằng trạng thái các mục trong `mustdoKhanh.md`.

---

## 1. Vai trò và mục tiêu

Bạn là kỹ sư Python phụ trách phần **voice agent và backend** của demo trợ lý giọng nói đặt xe Green SM. Người chịu trách nhiệm là Khánh.

Hoàn thiện toàn bộ phần việc sau trong `docs/PLAN_DEMO_GREENSM_VOICE.md`: Workstream C (mục 7), Workstream D (mục 8), cấu hình STT và TTS (mục 8A), phía backend và agent của hợp đồng dữ liệu (mục 10).

Kết quả cuối: worker chạy với `VOICE_AGENT_PROFILE=greensm_demo`. App Flutter của Phương kết nối vào. Người dùng nói "Đặt Green SM Car từ Vincom Bà Triệu đến sân bay Nội Bài", agent đọc lại chuyến đi, và khi người dùng đồng ý thì agent gọi RPC để app mở màn xác nhận của Green SM.

---

## 2. Đọc trước khi code (bắt buộc, theo thứ tự)

1. `docs/PLAN_DEMO_GREENSM_VOICE.md`: mục 0, 1, 2.1, 2.3, 2.4, 2.5, 3, 4, 7, 8, 8A, 9, 10, 11, 13, 14. Mục 14 chưa có câu trả lời của người dùng, nên dùng mặc định của plan: xưng "trợ lý Green SM", không nói giá. Đổi mặc định phải do người sửa.
2. `mustdoKhanh.md`: việc người đang làm. Không làm thay, không thêm mục trùng.
3. `mustdo.md` ở thư mục gốc: việc hạ tầng chung (migration PostgreSQL...). Profile demo không dùng DB nên các mục đó không chặn demo. Không làm, không thêm mục trùng.
4. Code hiện có:
   - `src/voice_agent/`: `server.py`, `agent.py`, `session_data.py`, `state_sync.py`, `model_factory.py`, `config.py`, `persistence.py`, `observability.py`, `tts_text.py`, `place_query_validator.py`, `tasks/booking.py`, `tools/places.py`
   - `src/backend/`: `api/routes/mobile.py`, `schemas/mobile.py`, `maps/contracts.py`, `maps/providers/goong.py`, `maps/service_area.py`, `config.py`
   - `data/gazetteer/*.json`
   - `scripts/benchmark_livekit_asr.py`, `scripts/aggregate_livekit_evaluation.py`, `scripts/livekit_room_smoke.py`
   - `tests/test_voice_agent/`, `tests/test_api/test_mobile_routes.py`, `tests/test_scripts/test_livekit_asr_benchmark.py`, `tests/test_scripts/test_livekit_evaluation.py`, `tests/integration/test_openai_understanding.py` (mẫu test gọi provider thật)
   - `ruff.toml`, `pytest.ini`, `.gitignore`, `.env.example`
5. API LiveKit Agents đang cài là 1.6.8. Khi dùng hàm nào của `livekit.agents` hoặc `livekit.rtc`, đọc source trong `.venv/Lib/site-packages/livekit/` để lấy đúng chữ ký. Không đoán API. Các điểm đã kiểm trên 1.6.8 ngày 19/10/2026 được ghi ở từng phase; sau K8 phải kiểm lại.

---

## 3. Phạm vi sở hữu

**Được sửa:**

- `src/voice_agent/` và các phần của `src/backend/` liên quan tới token mobile, Goong, danh mục dịch vụ (gồm `src/backend/config.py` khi cần trường cấu hình mới)
- `data/gazetteer/`, `data/greensm_demo_services.json` (mới), `.gitignore` (chỉ thêm ngoại lệ cho file này)
- Các script nêu tên trong prompt này, test tương ứng trong `tests/`
- `.env.example`. Trong `.env` cục bộ chỉ được sửa các dòng không bí mật nêu ở phase K1
- `pyproject.toml`, `uv.lock` chỉ ở phase K8
- `mustdoKhanh.md`

**Không được sửa:** `olasm_mobile/` (của Phương), `docs/` (gồm plan và các prompt), `mustdoPhuong.md`, `mustdo.md`, `src/frontend/`, các luồng OlaSM cũ ngoài chỗ cần để chọn profile. Test cũ chỉ được sửa khi chữ ký hàm của chính nó đổi theo prompt này, và phải nêu trong báo cáo.

**Giữ hành vi mặc định:** không đặt `VOICE_AGENT_PROFILE` thì worker chạy như cũ. `build_agent_session`, `prepare_process`, `_handle_text_input`, mặc định của mọi trường `livekit_*` hiện có và toàn bộ test cũ không đổi, và test cũ vẫn xanh khi `.env` cục bộ đã có `VOICE_AGENT_PROFILE=greensm_demo`.

**File mới được phép tạo** (ngoài danh sách này thì không tạo, ngoại trừ `__init__.py` của package mới):

```text
src/voice_agent/greensm_demo/{state,services,templates,keyterms,resolver,fastpath,agent,handoff,session,polyline}.py
src/backend/maps/providers/goong_places.py
data/greensm_demo_services.json
data/gazetteer/greensm_demo_places.json
scripts/build_demo_gazetteer.py
scripts/bench_demo_llm.py
tests/test_voice_agent/test_model_factory.py
tests/test_voice_agent/test_greensm_*.py
tests/test_voice_agent/golden/greensm_fastpath.json
tests/test_backend/test_goong_places.py
tests/test_scripts/test_build_demo_gazetteer.py
```

---

## 4. Nguyên tắc bắt buộc

1. **Không mock, không bịa dữ liệu.**
   - Không viết mock, fake, stub thay cho Goong, LiveKit, Green SM hay bất kỳ dịch vụ thật nào. Không dùng `MagicMock`, `AsyncMock`, `patch`, `httpx.MockTransport` hay server giả trong code và test mới. Khoá và secret giữ chỗ chỉ được dùng để dựng đối tượng offline (ví dụ `inference.STT`), không gọi mạng.
   - Không sinh toạ độ, giá, quãng đường, thời gian từ trí nhớ hay từ hash.
   - Không giữ fallback âm thầm sang dữ liệu giả. Không dùng và không sửa `GoongProvider` cũ: nhánh mock và endpoint `/geocode` của nó phục vụ luồng OlaSM cũ.
   - Lỗi dịch vụ phải hiện ra thành `failure` đúng hợp đồng ở mục 5. Lỗi provider STT, LLM, TTS của session cũng vậy (mã `PROVIDER_UNAVAILABLE`).
   - Không bị coi là dữ liệu bịa: danh mục 4 dịch vụ do plan nêu, tên và alias POI lấy từ các nguồn nêu ở K3, câu nói mẫu (template), 40 câu thử của K5.
2. **Việc cần người thì ghi vào `mustdoKhanh.md`.** Khi gặp việc AI không tự làm được, viết code đầy đủ tới sát ranh giới đó, rồi thêm một mục theo mẫu ở mục 7. Ví dụ: thiếu key, cần thiết bị thật, cần thu âm giọng thật, cần người nghe đánh giá, cần tài khoản LiveKit Cloud, cần quyết định nghiệp vụ. Không đánh dấu xong thay người, không sửa hay xoá mục người đã ghi.
3. **Test tự động chỉ cho logic thuần**, dùng dữ liệu thật trong repo hoặc ví dụ đúng hợp đồng: parser tiếng Việt, quy tắc chọn địa điểm, template câu nói, model state, payload RPC, parse response Goong, cache TTL/LRU (đồng hồ truyền vào), mã hoá polyline, sinh keyterm, `build_stt` và `build_tts` trên đối tượng inference thật, DTO và metadata token.
   - Test cấu hình dùng `_env_file=None`. Không test nào được phụ thuộc `.env` cục bộ.
   - Dữ liệu mẫu response Goong lấy từ tài liệu chính thức của Goong hoặc từ response thật khi đã có key, ghi nguồn trong test. Mẫu polyline lấy từ ví dụ chính thức của Google Encoded Polyline.
   - Không viết test giả lập tích hợp để chứng minh luồng chạy được. Tích hợp thật được kiểm bằng lệnh chạy thật. Chưa chạy được thì ghi mustdo kèm lệnh. Ngoại lệ duy nhất: 15 hội thoại ở K4, gọi dịch vụ thật và gắn `pytest.mark.provider` theo mẫu của `tests/integration/test_openai_understanding.py`.
   - Test cũ trong `tests/test_api/test_mobile_routes.py` dùng `patch` và `MagicMock` (có từ trước, giữ nguyên). Case mới không patch `_issue_mobile_token`.
4. **Không làm ngoài plan.** Không thêm tính năng, tài liệu, báo cáo, refactor lan man. Không tạo file `.md` nào ngoài `mustdoKhanh.md`. Ngoài phạm vi: khử nhiễu BVC (C8), A/B `turn_detection="stt"`, wake word, UI, tính giá hoặc ETA, tạo booking thật, ghi DB.
5. **Chất lượng:**
   - Type hint đầy đủ, `from __future__ import annotations`, docstring và comment theo ngôn ngữ và mật độ của file xung quanh. Cấu hình ruff ở `ruff.toml` (py311, dòng 120).
   - Baseline đo ngày 19/10/2026 trên `main`: `uv run pytest -q` được 722 pass, 1 fail, 3 skip; `uv run ruff check src tests` có sẵn 46 lỗi ở 28 file. Vì vậy tiêu chí là **không tệ hơn baseline**: số test đỏ không tăng, tổng lỗi ruff không tăng, mọi file mới tạo phải sạch ruff hoàn toàn. Không chạy `ruff --fix` hay `ruff format` trên file ngoài phạm vi. Test đỏ sẵn có chỉ ghi lại trong báo cáo, không sửa.
   - Không để code chết, code bị comment, TODO không có mục mustdo tương ứng.
6. **Bí mật:**
   - Không in, không log, không commit giá trị key, `participant_token`, toạ độ hay transcript của người dùng. Không dùng `cat`, `Get-Content`, `grep` hay `Select-String` in nội dung `.env`. Chỉ ghi tên biến và giá trị không bí mật vào `.env.example`, các key để trống.
   - Lỡ in ra một giá trị bí mật thì dừng, báo người dùng để xoay khoá, không nhắc lại giá trị đó trong báo cáo.
7. **Git:** làm trên nhánh `feat/greensm-demo-agent` tạo từ `main`. Commit sau mỗi phase đạt tiêu chí, message `feat(agent): K<số> <mô tả ngắn>`. Chỉ `git add` đúng đường dẫn thuộc phạm vi, không dùng `git add -A` hay `git add .`: working tree có file chưa theo dõi của người khác (`docs/`, `mustdoPhuong.md`, `olasm_mobile/android/.gradle/`). Không push khi người dùng chưa yêu cầu.

---

## 5. Hợp đồng dữ liệu chung

Khối này giống hệt trong prompt của Phương. Không tự đổi tên trường, giá trị enum hay topic. Cần đổi thì dừng phần đó và thêm mục vào mustdo để hai người thống nhất.

**5.1 Token** `POST /api/v1/mobile/voice-token`

- Request: `{"device_id": str 8-128 ký tự, "trigger_source": "push_to_talk" | "wake_word" | "prefetch", "location": {"lat": float, "lng": float, "accuracy_m": float} | null, "screen": "HOME" | "ROUTE"}`
- Response `201`: `{"server_url", "participant_token", "room_name", "agent_name", "token_ttl_seconds"}`
- Mỗi token gắn một room mới và chỉ dùng một lần. Backend đưa `location` và `screen` vào dispatch metadata, `schema_version` là `"2"`.

**5.2 Booking state, agent gửi app**

Data packet reliable, topic `greensm.booking_state.v2`, JSON UTF-8, tối đa 10 KB. Gửi sau mỗi thay đổi, trước khi agent nói.

```json
{
  "schema": "greensm.booking_state.v2",
  "revision": 7,
  "stage": "ready_to_confirm",
  "pickup": {"status": "resolved", "source": "current_location", "name": "Vị trí hiện tại",
             "address": "12 Chùa Bộc, Đống Đa, Hà Nội", "lat": 21.007412, "lng": 105.828613},
  "destination": {"status": "resolved", "source": "gazetteer", "name": "Sân bay Nội Bài - Ga T1",
                  "address": "Sóc Sơn, Hà Nội", "lat": 21.218716, "lng": 105.804176},
  "service": {"status": "resolved", "id": "GSM_CAR", "label": "Green SM Car", "defaulted": true},
  "candidates": null,
  "route": {"distance_m": 27450, "duration_s": 2580, "polyline": "<encoded polyline>", "provider": "goong"},
  "failure": null
}
```

Toạ độ trong ví dụ chỉ minh hoạ định dạng, không được dùng làm dữ liệu.

- `stage`: `collecting` | `disambiguating` | `ready_to_confirm` | `handing_off` | `handed_off` | `abandoned`.
- `Place`: `{"status", "source": "current_location" | "gazetteer" | "goong" | null, "name", "address", "lat", "lng"}`. `lat`, `lng` chỉ có giá trị khi `status` là `resolved`. Thiếu hẳn thì gửi `{"status": "missing", ...null}`.
- `SlotStatus`: `missing` | `needs_clarification` | `resolved`.
- `ServiceId`: `GSM_BIKE` | `GSM_MINI` | `GSM_CAR` | `GSM_PREMIUM`.
- `candidates` khi mơ hồ: `{"target": "pickup" | "destination", "query": str, "options": [{"index": int từ 1, "name": str, "subtitle": str, "distance_km": float | null}]}`, tối đa 5 option.
- `route`: `{"distance_m": int, "duration_s": int, "polyline": str, "provider": "goong"}`. `polyline` là encoded polyline chuẩn Google, precision 5.
- `failure`: `{"code", "message": str tiếng Việt hiển thị được, "retryable": bool}`. `code`: `PLACE_NOT_FOUND` | `ASR_LOW_CONFIDENCE` | `OUT_OF_SERVICE_AREA` | `ROUTE_UNAVAILABLE` | `PROVIDER_UNAVAILABLE` | `HANDOFF_FAILED`.
- `revision` tăng dần. App bỏ mọi gói có `revision` nhỏ hơn hoặc bằng gói đang giữ.

**5.3 RPC mở Green SM, agent gọi app**

Method `greensm.open_confirmation`, gọi tới participant của khách, `response_timeout` 5 s.

- Payload: `{"trip_ref": str, "service_id": ServiceId, "pickup": {"name", "address", "lat", "lng"}, "destination": {"name", "address", "lat", "lng"}, "route": {"distance_m", "duration_s"} | null}`
- App trả `{"opened": true}` hoặc `{"opened": false, "reason": "NOT_INSTALLED" | "LAUNCH_FAILED" | "INVALID_PAYLOAD" | "DEEPLINK_NOT_CONFIGURED"}`.

**5.4 App gửi agent:** chữ nhập tay gửi bằng `session.sendText(text)`. Chạm dòng thứ N trong danh sách lựa chọn gửi đúng chuỗi `chọn số N`.

**5.5 Mã dịch vụ trong deeplink** chỉ nằm trong cấu hình app `olasm_mobile/assets/config/greensm_deeplink.json`. Agent chỉ biết `ServiceId`.

---

## 6. Các phase

Làm theo thứ tự. Mỗi phase chỉ xong khi đạt tiêu chí. Phần bị chặn bởi người thì ghi mustdo rồi làm tiếp phần không bị chặn.

### K0. Kiểm tra đầu vào

- `git switch -c feat/greensm-demo-agent` từ `main`. Nhánh đã có thì `git switch` sang rồi tiếp tục.
- Chạy `uv run pytest -q` và `uv run ruff check src tests`, ghi số pass, fail, số lỗi ruff thật làm baseline (lưu ngoài repo). Số đo ngày 19/10/2026 để đối chiếu: pytest 722 pass, 1 fail, 3 skip trong khoảng 30 s. Test đỏ là `tests/test_voice_agent/test_booking_task.py::test_agent_exposes_native_booking_entrypoint_and_authoritative_status_tool` (do tool app-control của `OlaSMAgent`, ngoài phạm vi). Ruff 46 lỗi, loại F401, I001, F841, UP037.
- Kiểm `.env` có đủ `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `MAPS_API_KEY` hay chưa. Chỉ in có hoặc không:

  ```powershell
  uv run python -c "from src.voice_agent.config import get_livekit_voice_settings as v; from src.backend.config import get_settings as b; s, m = v(), b(); print({'LIVEKIT_URL': bool(s.livekit_url), 'LIVEKIT_API_KEY': bool(s.livekit_api_key.get_secret_value()), 'LIVEKIT_API_SECRET': bool(s.livekit_api_secret.get_secret_value()), 'MAPS_API_KEY': bool(m.maps_api_key)})"
  ```

  Ngày 19/10/2026: ba biến LiveKit có, `MAPS_API_KEY` thiếu, nên phần chạy thật của K3 và K5 chờ mục K-H1.

### K1. Cấu hình pipeline theo mục 8A

- `src/voice_agent/config.py` (`LiveKitVoiceSettings`). Không đổi mặc định của trường đang có: test cũ khẳng định các mặc định đó, và `.env` cục bộ đang ghi đè nhiều trường (endpointing, interruption, num idle). Vì vậy thông số riêng của demo phải là trường mới:
  - `voice_agent_profile`: `olasm` (mặc định) hoặc `greensm_demo`
  - `livekit_stt_fallback_model`: mặc định `assemblyai/universal-3-5-pro`. `livekit_tts_fallback_model`: mặc định `cartesia/sonic-3.5`. Chuỗi rỗng là tắt dự phòng.
  - Nhóm `greensm_demo_*`, giới hạn giá trị theo trường `livekit_*` tương ứng, mặc định đúng mục C2 của plan: `endpointing_mode` `dynamic`, `endpointing_min_delay_seconds` 0,35, `endpointing_max_delay_seconds` 1,8, `interruption_min_duration_seconds` 0,4, `interruption_min_words` 0, `false_interruption_timeout_seconds` 1,5, `resume_false_interruption` bật, `preemptive_generation` bật, `preemptive_tts` tắt, `idle_prompt_seconds` 6, `num_idle_processes` 2.
  - Turn detection và chế độ ngắt lời của demo vẫn lấy từ `livekit_turn_detection` và `livekit_interruption_mode` có sẵn (đều mặc định `vad`).
  - `configuration_errors()`: khi profile là `greensm_demo`, thêm mã lỗi (cùng kiểu mã hiện có) nếu STT hoặc TTS không phải provider `livekit`, nếu `livekit_stt_language` khác `vi` (cấu hình `multi` đo chỉ đúng 15,9% địa danh), hoặc `max_delay` nhỏ hơn `min_delay`.
- `src/voice_agent/model_factory.py`, chỉ nhánh provider `livekit`, các nhánh khác giữ nguyên:
  - Gọi như cũ (`build_stt(settings)`, `build_tts(settings)`) phải cho kết quả y hệt hiện nay. Test cũ `test_livekit_process_setup_prewarms_native_models_and_state_store` monkeypatch `build_stt` bằng lambda một tham số, nên `prepare_process` không được đổi cách gọi.
  - `build_stt` nhận thêm tham số keyword, mặc định tắt: danh sách keyterm và cờ bật dự phòng. Keyterm vào `extra_kwargs` của model chính theo provider: `deepgram/*` dùng khoá `keyterm`, `assemblyai/*` dùng `keyterms_prompt`. Dự phòng là `{"model": <livekit_stt_fallback_model>, "extra_kwargs": <keyterm theo provider của nó>}`. Cờ dự phòng phải tắt được riêng, vì benchmark ở K7 phải đo đúng một model.
  - `build_tts` nhận thêm cờ bật dự phòng: `fallback=[{"model": <livekit_tts_fallback_model>, "voice": <livekit_tts_voice>}]`.
  - Đã kiểm trên 1.6.8: `inference.STT` và `inference.TTS` dựng được offline với `api_key`, `api_secret` không rỗng, đọc lại được qua `_opts.extra_kwargs` và `_opts.fallback`. `cartesia/sonic-3.6` chưa có trong `Literal` kiểu của 1.6.8 nhưng tham số nhận chuỗi tuỳ ý và đã đo chạy được ngày 19/10. Giữ nguyên, không "sửa" thành 3.5.
- `.env.example`: thêm biến mới (`VOICE_AGENT_PROFILE`, `LIVEKIT_STT_FALLBACK_MODEL`, `LIVEKIT_TTS_FALLBACK_MODEL`, nhóm `GREENSM_DEMO_*`, `GOONG_REQUEST_TIMEOUT_SECONDS`, `MAPS_*`, `GEOCODING_PROVIDER`, `ROUTING_PROVIDER`) ở dạng hoạt động với giá trị mặc định không bí mật, key để trống. Khối cấu hình mục 8A.4 của plan đặt ở dạng comment (`# KEY=value`) có tiêu đề riêng, vì khoá trùng với khối OlaSM phía trên; các dòng còn lại của khối cũ giữ nguyên.
- `.env` cục bộ: chỉ thay đúng các dòng sau, bằng công cụ sửa file (không in nội dung file); dòng chưa có thì thêm cuối file:

  ```env
  LIVEKIT_STT_PROVIDER=livekit
  LIVEKIT_STT_MODEL=deepgram/nova-3
  LIVEKIT_STT_LANGUAGE=vi
  LIVEKIT_TTS_PROVIDER=livekit
  LIVEKIT_TTS_MODEL=cartesia/sonic-3.6
  LIVEKIT_TTS_VOICE=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc
  LIVEKIT_TTS_LANGUAGE=vi
  LIVEKIT_LLM_PROVIDER=livekit
  LIVEKIT_LLM_MODEL=openai/gpt-4.1-mini
  VOICE_TRANSCRIPT_REWRITE_ENABLED=false
  VOICE_AGENT_PROFILE=greensm_demo
  ```

- Test: biến cấu hình mới và mã lỗi mới trong `tests/test_voice_agent/test_config.py`. `tests/test_voice_agent/test_model_factory.py` kiểm `build_stt`, `build_tts` trên đối tượng inference thật, không gọi mạng: khoá keyterm đúng theo provider, fallback kèm keyterm tương ứng, gọi như cũ thì `extra_kwargs` rỗng và không có fallback.
- **Tiêu chí:** sau khi sửa `.env`, `configuration_errors()` rỗng và endpoint token không còn 503 (hiện đang 503 do `OPENAI_API_KEY_REQUIRED_FOR_OPENAI_PROVIDER`). Kiểm, chỉ in mã trạng thái, dự kiến 201:

  ```powershell
  uv run python -c "from fastapi.testclient import TestClient; from src.main import app; print(TestClient(app).post('/api/v1/mobile/voice-token', json={'device_id': 'check-device-0001', 'trigger_source': 'push_to_talk'}).status_code)"
  ```

  Test không tệ hơn baseline. Nếu chạy được worker thật (`uv run python -m src.voice_agent.server dev`, lúc này vẫn là luồng cũ), chạy `uv run python -m scripts.livekit_room_smoke --runs 1` để xác nhận LiveKit Inference nhận cấu hình mới. Script này chờ topic `olasm.booking_state.v1` nên không dùng được cho profile demo. Chưa chạy được thì ghi mustdo kèm lệnh.

### K2. Profile `greensm_demo` trong worker (mục C1, C2)

- Package `src/voice_agent/greensm_demo/`:
  - `state.py`: `TripState` và hàm xuất dict đúng mục 5.2. Plan 2.5 gợi ý mở rộng `BookingDraft`, nhưng prompt này chọn state riêng và không sửa `BookingDraft`: `OlaSMSessionData` dùng `extra="forbid"`, `VehicleType` và `FailureCode` cố định, `durable_state()` ghi DB, nên mở rộng sẽ chạm luồng cũ và test cũ. Vì vậy cũng không cần ánh xạ ngược sang `VehicleType` (plan D6). Giữ ý tưởng của `BookingDraft`: trạng thái từng slot, `revision` tăng mỗi thay đổi, sửa slot thì huỷ phần phụ thuộc (route, danh sách lựa chọn cũ).
  - `services.py`: đọc `data/greensm_demo_services.json` (K3).
  - `templates.py`: câu nói theo quy tắc mục 4.3 của plan.
  - `agent.py`: `GreenSmDemoAgent`.
  - `handoff.py`: RPC ở phase K6.
  - `session.py`: hàm vào job của demo và hàm dựng `AgentSession` riêng cho demo. Userdata của session là kiểu riêng của demo, có `app_session_id`, `call_id`, `user_id` để dùng lại `SessionEventLog` và `LiveKitSessionObserver` (hai lớp chỉ đọc ba thuộc tính này). Không có state store: không restore, không save, không import `persistence`. Đây thay cho `EphemeralVoiceStateStore` ở plan C1, cùng mục đích.
- `src/voice_agent/server.py`: sau `_connect_room_early(ctx)`, nếu `voice_agent_profile` là `greensm_demo` thì chuyển cho hàm vào job của demo rồi `return`, nhánh còn lại giữ nguyên từng dòng. `prepare_process` không rẽ nhánh theo profile (VAD prewarm dùng chung). `AgentServer(num_idle_processes=...)` lấy `greensm_demo_num_idle_processes` khi profile là demo, `livekit_num_idle_processes` khi không.
- Việc của một job demo:
  - Không chào, không dùng transcript rewrite. Sau `greensm_demo_idle_prompt_seconds` (6 s) kể từ khi `session.start()` xong mà chưa có lời người dùng (chưa có `user_state_changed` sang `speaking`, chưa có transcript), nói đúng một lần "Bạn muốn đi đâu ạ?". Huỷ hẹn giờ khi khách bắt đầu nói hoặc phiên đóng.
  - Đọc `ctx.job.metadata` bằng một hàm thuần: `schema_version` `"2"` thì lấy `location` (kiểm vĩ độ, kinh độ, `accuracy_m`) và `screen` (mặc định `HOME`). Thiếu, hỏng hoặc phiên bản `"1"` thì coi như không có vị trí, không lỗi. Không log toạ độ.
  - Gọi `tts.prewarm()` ngay khi job bắt đầu, trên đúng instance TTS đưa vào `AgentSession`. Mở sẵn kết nối Goong bằng cách chạy nền Reverse Geocode của vị trí khách (việc này cần cho nhãn điểm đón, K3).
  - STT dựng riêng cho job bằng `build_stt` với keyterm và dự phòng (keyterm từ K3, trước đó để trống). LLM bằng `build_llm`. TTS bằng `build_tts` với dự phòng. VAD là `inference.VAD("silero")` đã prewarm của process, giữ `min_silence_duration` mặc định 0,25 s.
  - `turn_handling` ghép từ cấu hình K1, không hard-code: `turn_detection` từ `livekit_turn_detection`, endpointing và interruption và preemptive generation từ nhóm `greensm_demo_*`, `interruption.mode` từ `livekit_interruption_mode`. `conn_options` và `transcription_timeout` dùng lại trường `livekit_tts_*` và `livekit_transcription_timeout_seconds` như `build_agent_session`.
  - `RoomOptions`: giữ `audio_input` với `pre_connect_audio=True` như luồng cũ (app Flutter dùng `Session` API với pre-connect), `close_on_disconnect=True`, `delete_room_on_close` theo cấu hình, `text_input` trỏ vào đường chữ của demo (K4). Không đăng ký `_on_mobile_data_received`, đó là nhánh tự chế cũ.
  - `tts_text_transforms`: `filter_emoji`, `filter_markdown`, `vietnamese_currency_tts_transform` như hiện có. Quy tắc phiên âm "SM", số nhà, tên riêng tiếng Anh chỉ thêm khi có kết quả buổi nghe thử (K-H5), không đoán.
- **Tiêu chí:** test cũ của `test_server.py` xanh. Test mới (`tests/test_voice_agent/test_greensm_session.py`) cho hàm chọn profile và hàm parse metadata (có `location` hợp lệ, `location` sai miền, phiên bản `"1"`, JSON hỏng, thiếu `screen`).

### K3. Địa điểm, dịch vụ, lộ trình (mục D1 đến D6)

Thứ tự làm: danh mục dịch vụ, gazetteer, client Goong, keyterm, resolver, lộ trình.

- `data/greensm_demo_services.json`: 4 dịch vụ.
  - `GSM_BIKE` (Green SM Bike, vehicle Goong `bike`), `GSM_MINI` (Green SM Mini, `car`), `GSM_CAR` (Green SM Car, `car`, mặc định), `GSM_PREMIUM` (Green SM Premium, `car`).
  - Mỗi dịch vụ kèm cách nói của khách, ví dụ "xe máy", "ô tô", "taxi", "mini", "cao cấp", "premium". Không chứa mã deeplink.
  - `.gitignore` có `data/*` nên file này đang bị bỏ qua. Thêm `!data/greensm_demo_services.json` và kiểm bằng `git check-ignore -v data/greensm_demo_services.json` (không còn khớp) rồi `git status` thấy file.
- `src/backend/maps/providers/goong_places.py`, client Goong mới:
  - Các hàm AutoComplete, Place Detail, Reverse Geocode, Direction (`vehicle` theo dịch vụ).
  - AutoComplete theo tài liệu Goong: `input`, `location` (`lat,lng` của khách), `limit` (đặt 5, mặc định của Goong là 10), `radius` (**tính bằng km**, mặc định 50), `more_compound` để lấy địa chỉ theo đơn vị hành chính mới. Ưu tiên phiên bản trả địa chỉ theo đơn vị hành chính sau năm 2025. Tên endpoint, tham số, trường response của Place Detail, Geocode, Direction lấy theo tài liệu hiện hành của Goong (docs.goong.io/rest, có thể báo lỗi chứng chỉ với một số công cụ tải trang, khi đó dùng Goong API Playground). Ghi URL và ngày đọc tài liệu trong docstring.
  - Một `httpx.AsyncClient` dùng chung, keep-alive, tạo trong event loop của job (không mở kết nối trong `setup_fnc`), đóng bằng `ctx.add_shutdown_callback`. Thử lại 1 lần khi lỗi kết nối. Cache LRU có TTL 10 phút, khoá theo cụm đã chuẩn hoá cộng toạ độ làm tròn 3 chữ số, viết thành lớp thuần để test.
  - Timeout 1,5 s lấy từ trường mới `goong_request_timeout_seconds` (mặc định 1,5) trong `src/backend/config.py`. Không dùng `map_request_timeout_seconds`: `.env` đang đặt 5 s cho stack OSM cũ.
  - Đọc `maps_api_key`, `maps_base_url`, `geocoding_provider`, `routing_provider` từ `src/backend/config.py`. Hai provider phải là `goong`, key không được rỗng, nếu không thì ném lỗi cấu hình thuộc nhóm `PROVIDER_UNAVAILABLE`.
  - Không mock, không fallback. Dùng lại các lỗi trong `src/backend/maps/contracts.py` (`MapsDomainError` và lớp con, có `code`, `retryable`) và `validate_latitude`, `validate_longitude`. Ánh xạ sang `failure` ở mục 5.2: `PlaceNotFoundError` hoặc kết quả rỗng thành `PLACE_NOT_FOUND`; `MapProviderTimeoutError`, `MapProviderUnavailableError` thành `PROVIDER_UNAVAILABLE`; `RouteNotFoundError`, `RouteProviderUnavailableError` thành `ROUTE_UNAVAILABLE`; ngoài vùng phục vụ thành `OUT_OF_SERVICE_AREA`.
  - Polyline xuất đúng mục 5.2. Nếu định dạng của Goong khác encoded polyline precision 5 thì chuyển đổi trước khi publish.
- `data/gazetteer/greensm_demo_places.json` và `scripts/build_demo_gazetteer.py`:
  - 30 đến 50 POI. Tên và alias chỉ lấy từ: (1) danh sách gợi ý ở D1 của plan, (2) `canonical_name` và `asr_aliases` trong `hanoi_place_aliases.json`, (3) điểm đón trong `hanoi_landmark_pickup_points.json` (Hồ Gươm có 4 điểm gồm Bưu điện Hà Nội, VinUni có 3 cổng), (4) alias đo được ở D4 của plan ("Kangnam", "keo nam", "keng nam", "Charlotte Center", "lốt test center", "ĐH", "Time City"). Phải có đủ POI của kịch bản 1 đến 3 ở mục 4.2 của plan, gồm cả Vincom Nguyễn Chí Thanh, vì file alias cũ chưa có. File `landmark` cũ gắn nhãn `MOCK_VERIFIED_FROM_PUBLIC_SOURCES`, nên chỉ lấy tên và địa chỉ làm câu truy vấn, không lấy làm toạ độ.
  - Mỗi mục: `canonical_name`, `aliases`, `address`, `kind`, `query` (chuỗi gửi Goong), `lat`, `lng`, `place_id`, `source`, `fetched_at`, `verified`.
  - **Không tự điền toạ độ.** AI tạo file ở trạng thái hạt giống: `lat`, `lng`, `place_id`, `source`, `fetched_at` là `null`, `verified` là `false`. Script gọi Goong (AutoComplete rồi Place Detail) để điền các trường này và giữ `verified: false`. Script không bao giờ ghi đè mục đã `verified: true` hay toạ độ người đã sửa. Cần `MAPS_API_KEY` nên chạy script chờ K-H1.
  - Người kiểm điểm đón trên bản đồ rồi đặt `verified: true`, việc này đã có trong mustdo (K-H2). Agent chỉ dùng toạ độ của mục có `verified: true`. Tên và alias của mọi mục (kể cả chưa verified) được dùng cho keyterm.
- `src/voice_agent/greensm_demo/keyterms.py`: sinh danh sách keyterm từ tên chuẩn của gazetteer demo và nhãn dịch vụ ("Green SM", "Green SM Car", "Green SM Bike", "Green SM Mini", "Green SM Premium", "Xanh SM"), bỏ trùng. Không đưa alias ASR sai chính tả vào keyterm (sẽ củng cố lỗi). Ưu tiên: dịch vụ, POI của kịch bản, rồi POI còn lại. Nối vào STT của job demo (K2).
  - Giới hạn đã kiểm trên tài liệu chính thức ngày 19/10/2026: Deepgram cho tối đa **500 token tổng** mọi keyterm trong một request (vượt thì lỗi), AssemblyAI tối đa 100 keyterm, mỗi cụm tối đa 50 ký tự. Tiếng Việt có dấu tốn nhiều token, nên "100 cụm" ở plan 8A.4 là mức trần chứ không đảm bảo qua được Deepgram. Danh sách chung phải qua cả hai: tối đa 100 cụm, mỗi cụm tối đa 50 ký tự, tổng số token Deepgram dưới 500.
  - Kiểm bằng lệnh chạy thật: mở một phiên `inference.STT.stream()` với đúng danh sách và fallback, đẩy 1 s im lặng, xác nhận gateway không từ chối. Bị từ chối thì cắt từ cuối danh sách ưu tiên cho tới khi qua, rồi chừa khoảng 20% an toàn. Ghi số cụm chọn được vào báo cáo.
  - Chừa chỗ cho tối đa 5 cụm động ở K4.
- `src/voice_agent/greensm_demo/resolver.py` theo mục D3:
  - Thứ tự: gazetteer (mục `verified: true`, khớp đúng tên hoặc alias sau khi chuẩn hoá), sau đó Goong AutoComplete có bias GPS.
  - Xếp hạng bằng độ giống tên chính (rapidfuzz) nhân độ gần vị trí khách. Rõ ràng thì tự chọn (kết quả đầu khớp tên đúng và bỏ xa kết quả thứ hai), ngược lại trả 3 đến 5 candidates kèm `distance_km`. Các ngưỡng là hằng số đặt tên ở đầu file, có test, chỉnh bằng số đo (mục 11 của plan: 50 POI Hà Nội ngẫu nhiên, đúng trong top 3 từ 90%).
  - Lấy toạ độ cho lựa chọn bằng Place Detail.
  - Độ tin cậy ASR thấp (`transcript_confidence` dưới `livekit_critical_confidence_threshold`) và không khớp gazetteer thì trả `ASR_LOW_CONFIDENCE` và xin nói lại.
  - Kiểm vùng phục vụ bằng `ServiceAreaChecker(geojson_path=maps_service_area_path, service_area_id=maps_service_area_id)` khi `configured`. Chưa có polygon thì checker cho qua (fail-open), ghi log rõ một lần mỗi phiên. Việc cung cấp polygon đã có trong mustdo (K-H3).
  - Điểm đón mặc định là vị trí hiện tại, gắn nhãn bằng Reverse Geocode. Reverse Geocode lỗi thì `PROVIDER_UNAVAILABLE`, không bịa địa chỉ. Không có GPS thì hỏi khách "Bạn đang đứng ở đâu ạ?".
- Lộ trình: gọi Direction chạy nền khi đủ hai điểm. Có kết quả thì publish state thêm một lần. Kết quả có revision cũ hơn state hiện tại thì bỏ.
- Test (dữ liệu thật trong repo và mẫu chính thức): quy tắc tự chọn và xếp hạng trên tên và alias của gazetteer, chuẩn hoá alias ("Kangnam", "Charlotte Center", "ĐH"...), sinh keyterm (không trùng, ≤ 100 cụm, ≤ 50 ký tự, không chứa alias sai), parse response Goong từ mẫu chính thức, cache TTL/LRU, ánh xạ lỗi sang `failure`, schema file dịch vụ và gazetteer (script chỉ test phần thuần, không gọi Goong).
- **Tiêu chí:** `git status` thấy `data/greensm_demo_services.json`, file gazetteer ở trạng thái hạt giống không có toạ độ nào được điền, keyterm qua kiểm phiên STT thật, test xanh. Phần chạy script với Goong chờ K-H1, K-H2.

### K4. Fast path và hội thoại (mục C3, C4, 4.3)

- Hai đường vào cùng đi qua một hàm fast path trong `fastpath.py`: `GreenSmDemoAgent.on_user_turn_completed` và callback nhập chữ của demo. Đã kiểm trên 1.6.8: `session.generate_reply(user_input=...)` **không** gọi `on_user_turn_completed`, nên callback chữ phải tự gọi fast path trước, rồi mới `generate_reply` khi fast path không xử lý. Vì cùng lý do, `AgentSession.run()` của bộ công cụ test LiveKit bỏ qua fast path.
- Fast path gồm hàm thuần `interpret(text, state)` (chỉ phân tích, không I/O) và phần thực thi: cập nhật `TripState`, gọi resolver, publish state, `session.say(template)`, rồi trong `on_user_turn_completed` thì `raise StopResponse()`.
- Parser:
  - **Tái dùng bằng import** từ `src.voice_agent.tasks.booking` (hàm thuần theo chuỗi): `extract_complete_route`, `extract_labeled_booking_places`, `extract_explicit_booking_change` (trường `vehicle_type` trả về thì đổi sang dịch vụ), `is_booking_abandonment_request`, và `is_valid_place_query` từ `place_query_validator`.
  - **Viết mới trong `fastpath.py`**, vì hàm cũ nhận `BookingDraft`, trả `VehicleType` cũ (`MOTORBIKE`, `CAR_4`...) hoặc đòi câu xác nhận từ 4 từ: nhận diện đồng ý và phủ định, chọn theo số hoặc theo tên trên `TripState.candidates`, nhận diện dịch vụ theo cách nói trong `greensm_demo_services.json`, câu chỉ có điểm đến ("cho mình đi Vincom", "đặt xe đi Times City"), hàm chuẩn hoá bỏ dấu. Không import tên bắt đầu bằng `_` từ `booking.py`.
  - Thứ tự nhận diện theo plan C3: huỷ hoặc dừng, đồng ý hoặc phủ định, chọn theo số hoặc theo tên, sửa slot có nhãn, câu đủ tuyến, chỉ điểm đến, loại dịch vụ. Tách cụm dịch vụ khỏi câu trước khi tách tuyến, để "bằng Green SM Car" không dính vào tên địa điểm.
- Xác nhận: "đúng rồi", "ok", "đặt đi", "xác nhận" khi câu chỉ gồm từ đồng ý (cùng "dạ", "vâng", "ạ", "nhé"). Các dạng ASR nghe sai "đặc bi", "đặc biệt" chỉ được tính khi `stage` là `ready_to_confirm`. Chặn phủ định "không", "chưa", "khoan", "đợi đã", "thôi". Câu vừa đồng ý vừa đổi slot ("đúng rồi, đổi sang xe máy") xử lý như sửa slot, không mở Green SM. Ngoài `ready_to_confirm`, từ đồng ý không kích hoạt gì và chuyển sang đường LLM.
- "chọn số" mà thiếu số thì hỏi lại "Bạn chọn số mấy ạ?". "thôi không đặt nữa" thì chuyển `stage` sang `abandoned`, nói câu dừng ngắn, giữ phiên; khách nói tiếp một chuyến mới thì bắt đầu `TripState` mới, `revision` vẫn tăng.
- Câu nói: dịch vụ mặc định `GSM_CAR` với `defaulted: true`, đọc rõ trong câu xác nhận. Không nói giá; khách hỏi giá thì trả đúng "Giá chính xác sẽ hiện ở màn xác nhận của Green SM ạ." Không đọc số phút trừ khi khách hỏi; khi hỏi thì đọc từ `route.duration_s`, chưa có route thì nói chưa có và chỉ về màn xác nhận. Danh sách lựa chọn chỉ đọc số lượng, không đọc từng dòng.
- Từ khoá động (plan D4): khi `stage` là `disambiguating`, cập nhật keyterm của STT cho lượt kế tiếp bằng `session.update_options(keyterms=<tên các option>)`, rồi trả về `[]` khi rời trạng thái đó. Đã kiểm trên 1.6.8: cách này hợp nhất với keyterm tĩnh trong `extra_kwargs` và tự hoãn tới hết câu nếu khách đang nói (`stt._update_session_keyterms`). Nếu dùng `stt.update_options(extra={"keyterm": ...})` như plan viết thì phải truyền cả danh sách tĩnh, vì khoá `keyterm` bị thay cả mảng.
- Prefetch suy đoán: nghe sự kiện transcript interim (`user_input_transcribed`), tách cụm địa điểm sau "đến", "tới", "từ", "ở", gọi resolver chạy nền với debounce 150 ms và cache. Prefetch chỉ làm ấm cache, không sửa state.
- Mỗi phiên có một `asyncio.Lock` khi sửa state. Bỏ kết quả lookup có revision cũ.
- Đường LLM dự phòng:
  - Instructions tiếng Việt tối đa 200 từ: xưng trợ lý Green SM, nói ngắn, luôn dùng tool, không tự bịa địa điểm, giá, thời gian, đọc nguyên văn `spoken_prompt` do tool trả về.
  - 4 tool idempotent `update_trip`, `choose_option`, `confirm_and_open_greensm`, `cancel_trip`, mỗi tool trả `spoken_prompt`, đi qua cùng resolver và `TripState` với fast path. `parallel_tool_calls` tắt (đã có trong `build_llm`).
  - Preemptive generation bật. Đã kiểm trên 1.6.8: `_pipeline_reply_task_impl` đợi `speech_handle._wait_for_authorization()` rồi mới gọi `perform_tool_executions`, nên tool không chạy trước khi lượt được chốt. Lượt đi fast path (`StopResponse`) thì bản sinh trước bị bỏ.
- Optional, chỉ khi số đo K-H7 cho thấy TTFB câu cố định ("Bạn muốn đi đâu ạ?", câu chuyển sang Green SM) p50 trên 300 ms: dựng sẵn audio lúc prewarm rồi phát bằng `session.say(text, audio=...)`. Chưa có số đo thì ghi "chưa làm" vào báo cáo.
- Test (`tests/test_voice_agent/test_greensm_fastpath.py`, `test_greensm_templates.py`): bộ khoảng 60 câu tiếng Việt dạng golden JSON `tests/test_voice_agent/golden/greensm_fastpath.json`, mỗi mục gồm câu nói, state trước, intent mong đợi, state và `stage` sau, câu trả lời mong đợi. Test chạy trên hàm thuần, không gọi mạng. Có đủ: đủ tuyến, chỉ điểm đến, chọn số và chọn tên, thiếu số, sửa điểm, đổi dịch vụ, đồng ý, phủ định, "đặc bi", huỷ, hỏi giá, hỏi thời gian. Test template: mở đầu "Dạ", mỗi lượt tối đa một câu thông tin và một câu hỏi, không có số tiền.
- 15 hội thoại hành vi (plan mục 11: happy path, mơ hồ, sửa, ngắt lời, đổi dịch vụ, huỷ, không tìm thấy, ASR kém): `tests/test_voice_agent/test_greensm_conversations.py`, gắn `pytest.mark.provider` và `skipif` theo mẫu `tests/integration/test_openai_understanding.py` (opt-in bằng `RUN_GREENSM_PROVIDER=1`), chạy qua đúng hàm xử lý lượt của agent demo. Cần LiveKit key (LLM qua Inference) và Goong key. Chưa chạy được thì ghi mustdo kèm lệnh `RUN_GREENSM_PROVIDER=1 uv run pytest -m provider tests/test_voice_agent/test_greensm_conversations.py`.

### K5. Chọn model LLM bằng số đo (mục C4)

- `scripts/bench_demo_llm.py`: chạy thật qua LiveKit Inference, dùng đúng instructions và 4 tool của K4, trên khoảng 40 lượt nói tiếng Việt mà fast path không xử lý (đặt thẳng trong script, kèm tool và tham số mong đợi). Mỗi lượt chạy ít nhất 3 lần. Đo TTFT p50, p95 và độ đúng khi gọi tool (đúng tên tool và đúng tham số).
- Model cần so: `openai/gpt-4.1-mini`, `openai/gpt-4.1-nano`, một bản `google/gemini-*-flash-lite` (tên có trong `inference/llm.py`, ví dụ `google/gemini-3.1-flash-lite`), `google/gemma-4-31b-it`. Model không còn trên gateway thì bỏ qua và ghi lại. Model dòng GPT-5 là model suy luận, nếu chọn thì phải đặt mức suy luận thấp nhất.
- Chọn model nhanh nhất có độ đúng tool từ 95%. Ghi model chọn vào `.env.example` và `LIVEKIT_LLM_MODEL` trong `.env`.
- Thiếu key hoặc gateway lỗi thì ghi mustdo kèm lệnh chạy.

### K6. State v2, chuyển sang Green SM, token endpoint (mục C5, C6, 10)

- Publish topic `greensm.booking_state.v2` cho profile demo, theo mẫu `publish_booking_state` trong `state_sync.py` (`publish_data(payload, reliable=True, topic=...)`, bỏ qua êm khi room đã đóng). Profile demo không publish topic `olasm.booking_state.v1` hay `olasm.app_control.v1`.
  - Payload đo bằng số byte UTF-8 của JSON thật, tối đa 10 KB. Vượt thì giải mã polyline, giảm số điểm bằng Douglas-Peucker với dung sai tăng dần (giữ điểm đầu và cuối), mã hoá lại precision 5, cho tới khi vừa. Codec viết thuần Python trong `polyline.py`, không thêm dependency.
  - Lỗi provider của session (sự kiện `error` của `AgentSession`) thành `failure` mã `PROVIDER_UNAVAILABLE`, `retryable: true`, rồi publish. Theo mẫu `register_provider_failure_sync` trong `server.py`: lỗi STT thì `session.update_agent(session.current_agent)` để khởi động lại luồng STT, lỗi `recoverable` của LiveKit thì không báo cho khách.
- Chuyển sang Green SM theo mục C6:
  - Khi khách đồng ý, kiểm có điểm đón, điểm đến, dịch vụ. Route không bắt buộc: hợp đồng 5.3 cho phép `route: null`, và Green SM tự tính tuyến ở màn xác nhận. Direction còn đang chạy thì chờ tối đa theo timeout Goong, hết hạn hoặc lỗi thì gửi `route: null`.
  - Chuyển `stage` sang `handing_off`, publish, rồi `session.say(<câu chuyển>, allow_interruptions=False)` và gắn `add_done_callback`. Callback của `SpeechHandle` là hàm đồng bộ, nên tạo `asyncio.Task` giữ tham chiếu để gọi `perform_rpc`.
  - `perform_rpc(destination_identity=<identity của khách>, method="greensm.open_confirmation", payload=<json mục 5.3>, response_timeout=5)`. Identity lấy từ `session.room_io.linked_participant`, không lấy từ metadata. `trip_ref` dạng `gsmdemo_` cộng 8 ký tự hex ngẫu nhiên.
  - Phản hồi `{"opened": true}` thì `stage` thành `handed_off`, publish, đóng session.
  - Phản hồi `{"opened": false, "reason": ...}`, `RpcError` (timeout, `UNSUPPORTED_METHOD`, recipient disconnected...) hoặc phản hồi không đọc được: `failure` mã `HANDOFF_FAILED` với lý do tiếng Việt theo từng `reason`, `retryable: true`, `stage` quay về `ready_to_confirm` để khách thử lại, publish, rồi nói lý do. Phiên được giữ.
- Token endpoint theo mục 5.1:
  - `MobileTokenRequestDTO` thêm `location` (mặc định `null`; vĩ độ, kinh độ trong miền hợp lệ, `accuracy_m` không âm) và `screen` (`HOME` hoặc `ROUTE`, mặc định `HOME` để request cũ vẫn hợp lệ). `trigger_source` thêm giá trị `prefetch`. Giữ nguyên `auth_token` và `wake_word_confidence`.
  - Dispatch metadata (`RoomAgentDispatch.metadata`) có `schema_version` `"2"` gồm `app_session_id`, `client_type`, `trigger_source`, `location`, `screen`. Metadata của participant token giữ như cũ, không chứa toạ độ, vì mọi participant trong room đọc được. Không log toạ độ.
- Test: giữ test cũ của `tests/test_api/test_mobile_routes.py`, thêm case `location`, `prefetch`, `screen`, dữ liệu sai (vĩ độ ngoài miền, `screen` lạ). Kiểm dispatch metadata bằng cách gọi `_issue_mobile_token` thật với `LiveKitVoiceSettings(_env_file=None, ...)` rồi giải mã JWT, không patch. Test state v2 (đủ các `stage`, `candidates`, `failure`), polyline (ví dụ chính thức của Google, và co giãn để vừa 10 KB), payload RPC đúng hợp đồng, ánh xạ phản hồi RPC sang `failure`.

### K7. Đo lường (mục C7, 11)

- `observability.py`: khi bật `LIVEKIT_DEBUG_EVENT_LOG`, mỗi lượt của agent demo phát một event qua `SessionEventLog.emit` với `turn_path` (`fast` hoặc `llm`), `goong_ms`, `prefetch_hit`, kèm `speech_id` hoặc `item_id` để ghép với `e2e_latency` của `conversation_item_added` cùng lượt. `scripts/aggregate_livekit_evaluation.py` đọc được các trường này và in p50, p95 của `goong_ms`, và p50, p95 của `e2e_latency` tách theo `turn_path` (mục tiêu mục 1 của plan: fast path p50 từ 1,0 s trở xuống). Mở rộng `tests/test_scripts/test_livekit_evaluation.py`.
- Sửa `scripts/benchmark_livekit_asr.py` sang streaming thời gian thực, vì LiveKit Inference STT không có nhận dạng batch (`_recognize_impl` ném `NotImplementedError`):
  - Giữ nguyên định dạng manifest JSONL hiện có và tên file kết quả.
  - Mỗi case: dùng `model.stream()`, đẩy audio theo thời gian thực, sau đó 2,5 s im lặng.
  - Đo final latency từ lúc hết tiếng tới final transcript cuối (thay cho `recognition_duration_ms`, tăng `schema_version` của summary lên `"2"`), cùng WER, CER, tỷ lệ đúng địa danh như hiện có.
  - Tham số `--model` để chạy cả model chính lẫn model dự phòng. Luôn bật keyterm của demo (khoá theo provider của model), không bật fallback, ngôn ngữ lấy từ cấu hình.
  - Cập nhật `tests/test_scripts/test_livekit_asr_benchmark.py` cho phần tính toán và đọc manifest, giữ test cũ.
- Thu âm giọng thật, benchmark 20 phiên, chọn vùng chạy agent đã có trong mustdo (K-H4, K-H6, K-H7).

### K8. Tùy chọn: nâng livekit-agents lên 1.8.8

Chỉ làm khi K0 đến K7 đã xong và xanh. Đã kiểm trên PyPI ngày 19/10/2026: `livekit-agents` 1.8.8 phát hành 15/10/2026 và yêu cầu `openai>=3.19,<4`.

- Đưa `aider-chat` ra khỏi `pyproject.toml` (không có mã nào import nó, nó ghim `openai` 2.20; ai cần aider thì cài bằng `uv tool install`).
- Nâng `livekit-agents` lên 1.8.8 và từng plugin lên bản tương thích mà `uv` giải ra. `livekit-plugins-openai` đang ghim 1.5.0 vì lý do ghi ở comment trong `build_llm`, `livekit-plugins-google` ghim 1.6.6: kiểm lại từng cái. Chạy `uv lock`, `uv sync`, rồi toàn bộ test, và kiểm lại các điểm "đã kiểm trên 1.6.8" ở K1, K4.
- Từ 1.8.3 có `reply_required` trong kết quả tool: nếu nâng xong, thử dùng để bỏ vòng LLM thứ hai sau tool.
- Có test đỏ do nâng cấp mà không sửa gọn được trong phase này thì revert toàn bộ K8 và ghi lý do trong báo cáo.

---

## 7. Mẫu một mục trong `mustdoKhanh.md`

```markdown
## K-H<số>. <Tên việc>

- **Việc làm:** ...
- **Tại sao AI không làm được:** ...
- **Ở đâu:** file, dịch vụ, thiết bị
- **Thao tác:** từng bước, kèm lệnh chính xác
- **Kết quả mong đợi:** ...
- **Kiểm chứng:** lệnh hoặc cách xác nhận đã xong
- **Đang chặn:** phase hoặc việc code đang chờ mục này
```

Đánh số tiếp theo số lớn nhất đang có (ngày 19/10/2026 là K-H7, mục mới bắt đầu từ K-H8). Không sửa nội dung mục do người viết.

---

## 8. Định nghĩa hoàn thành

- K0 đến K7 đạt tiêu chí. Phần bị chặn có mục mustdo cụ thể.
- `uv run pytest -q` và `uv run ruff check src tests` không tệ hơn baseline ở mục 4.5, file mới sạch ruff.
- Code mới không có mock, fake, dữ liệu bịa hay fallback âm thầm.
- `git status` chỉ thêm các file trong danh sách "File mới được phép tạo" cùng phần sửa trong phạm vi ở mục 3.
- `git check-ignore` không còn khớp file dữ liệu mới.

## 9. Báo cáo cuối phiên

In ra ngắn gọn:

1. Bảng phase với trạng thái: xong, bị chặn bởi mục mustdo nào, hoặc chưa làm.
2. Các lệnh kiểm tra đã chạy và kết quả thật, gồm số pytest và ruff trước và sau so với baseline.
3. Mục mustdo mới thêm.
4. Quyết định đã chốt bằng số đo, ví dụ model LLM được chọn, số cụm keyterm qua được gateway.
5. Chỗ nào đã lệch với plan và lý do (ví dụ `TripState` thay vì mở rộng `BookingDraft`).
