# Developer setup — AloSM Voice Agent

Tài liệu này là đường chạy nhanh cho thành viên mới trên nhánh
`feature/agentic-ai`. Runtime hiện có ba phần: FastAPI business plane, LiveKit
voice worker và React frontend.

## 1. Chuẩn bị máy

Cài các phiên bản sau:

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js và npm
- FFmpeg/FFprobe để xử lý audio local
- Git

Voice smoke test còn cần credential của các provider. Backend-only test không cần
các credential này.

## 2. Cài source và dependency

```bash
git clone <repository-url>
cd P-160
git switch feature/agentic-ai

uv sync
cp .env.example .env

cd src/frontend
npm ci
cd ../..
```

Không commit `.env`, `logs/`, `.ai-log/` hoặc bất kỳ provider key nào.

## 3. Chọn profile trong `.env`

### Profile A — backend/frontend smoke nhanh

Giữ các giá trị mặc định trong `.env`, sau đó đổi:

```env
APP_ENV=test
AGENT_LLM_ENABLED=false
DATABASE_URL=sqlite:///./data/app.db
VITE_API_URL=http://localhost:8000
```

Profile này dùng adapter memory cho các flow test, không chứng minh persistence
sau khi restart. Tài khoản demo:

```text
Phone:    0901234567
Password: Password123!
```

Không cần chạy Alembic cho profile này.

### Profile B — development có persistence

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/app.db
DATABASE_URL_MIGRATIONS=
QUOTE_SIGNING_KEY=<chuoi-ngau-nhien-it-nhat-32-ky-tu>
FIELD_ENCRYPTION_KEY=<chuoi-ngau-nhien-khac-it-nhat-32-ky-tu>
```

Sinh secret local:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Với database mới hoàn toàn, migration SQLite hiện còn limitation lịch sử ở các
revision durable cũ. Nếu `uv run alembic upgrade head` lỗi, dùng database
PostgreSQL/Supabase dev của team theo [`database_supabase.md`](database_supabase.md)
thay vì tự sửa schema hoặc stamp revision.

```bash
uv run alembic upgrade head
```

Runtime PostgreSQL và connection chạy migration phải dùng URL phù hợp; không dùng
transaction pooler cho Alembic. Xem chi tiết pooler tại
[`database_supabase.md`](database_supabase.md).

### Bật Core Agent text (tuỳ chọn)

Mặc định Core Agent dùng deterministic fallback để teammate có thể chạy backend mà
không cần gọi LLM. Muốn test chat/booking bằng model thật, chọn đúng một provider:

```env
AGENT_LLM_ENABLED=true
AGENT_LLM_BASE_URL=https://openrouter.ai/api/v1
AGENT_LLM_MODEL=openai/gpt-5.6-luna-pro
OPENROUTER_API_KEY=<key>
```

Hoặc dùng OpenAI trực tiếp:

```env
AGENT_LLM_ENABLED=true
AGENT_LLM_BASE_URL=https://api.openai.com/v1
AGENT_LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=<key>
```

### Bật voice realtime

Voice worker cần các biến sau. `LIVEKIT_URL` phải là URL WebSocket `wss://`, không
phải URL dashboard `https://`. Ba biến LiveKit phải thuộc cùng một project.

```env
LIVEKIT_URL=wss://<project>.livekit.cloud
LIVEKIT_API_KEY=<livekit-api-key>
LIVEKIT_API_SECRET=<livekit-api-secret>
LIVEKIT_AGENT_NAME=alosm-voice

LIVEKIT_STT_PROVIDER=elevenlabs
LIVEKIT_STT_MODEL=scribe_v2_realtime
LIVEKIT_STT_LANGUAGE=vi
ELEVEN_API_KEY=<elevenlabs-api-key>

LIVEKIT_LLM_PROVIDER=openai
LIVEKIT_LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=<openai-key>
```

STT gọi trực tiếp đến ElevenLabs bằng key của bạn; LiveKit chỉ giữ Room/WebRTC,
không proxy STT qua LiveKit Cloud. Không đặt bất kỳ key nào trong biến `VITE_*` vì
các biến đó được bundle vào trình duyệt.

Voice demo hiện để `MAPS_PROVIDER` trống: địa điểm lấy từ catalog approved local và
giá là deterministic demo. Nominatim/OSRM localhost chỉ có tác dụng khi teammate
tự chạy các service map tương ứng; đây chưa phải routing hoặc giá theo quãng đường
thật.

## 4. Chạy ứng dụng

Mở ba terminal tại thư mục repo:

```bash
# Terminal 1 — FastAPI
make livekit-backend
```

```bash
# Terminal 2 — LiveKit AgentServer/AgentSession worker
make livekit-worker
```

```bash
# Terminal 3 — React/Vite
make livekit-frontend
```

Mở `http://localhost:5173`. Kiểm tra backend trước tại
`http://localhost:8000/health`. Chỉ chạy một worker có tên `alosm-voice` cho mỗi
LiveKit project dùng để test.

Nếu chỉ cần backend/frontend, bỏ qua Terminal 2. Nếu worker khởi động lâu, đây là
cold start của process/provider LiveKit; xem log worker thay vì mở thêm worker thứ
hai.

## 5. Voice smoke test

1. Đăng ký hoặc đăng nhập trên frontend.
2. Mở AloSM Assistant và cấp quyền microphone.
3. Thử happy path:

   ```text
   Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm.
   Tôi chọn Cổng chính VinUni.
   Tôi chọn Bưu điện Hà Nội.
   Đúng, tôi xác nhận đặt chuyến này.
   ```

4. Thử sửa thông tin: `Không, tôi muốn sửa điểm đến.`
5. Thử handoff bằng cách yêu cầu gặp tổng đài viên.

Để xem event JSONL khi debug turn detection/STT:

```bash
LIVEKIT_DEBUG_EVENT_LOG=true \
LIVEKIT_DEBUG_TRANSCRIPTS=true \
make livekit-worker
```

Transcript mặc định tắt. Chỉ bật debug transcript cho phiên đã được phép; logger
không ghi raw audio, token hay credential.

## 6. AI logs (tuỳ chọn)

Nếu được cấp key ingest, điền vào `.env`:

```env
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=<instructor-key>
AI_LOG_DIR=.ai-log
```

Cài pre-push hook:

```bash
bash scripts/setup_hooks.sh
```

Hoặc Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

Gửi batch đang chờ thủ công:

```bash
uv run python scripts/submit_log.py
```

Luồng log có redaction và giữ queue local khi network/auth thất bại. Chi tiết tại
[`AI_LOGS.md`](AI_LOGS.md).

## 7. Kiểm tra trước khi gửi thay đổi

```bash
uv run pytest -q
uv run ruff check src tests eval_cases

cd src/frontend
npm run lint
npm run build
```

## 8. Lỗi thường gặp

- `Failed to fetch`: backend chưa chạy hoặc `VITE_API_URL` không trỏ tới
  `http://localhost:8000`; kiểm tra `/health` và `CORS_ORIGINS`.
- `Agent did not join the room`: kiểm tra worker còn chạy, tên agent đúng và
  `LIVEKIT_URL`/key/secret cùng project; không chạy nhiều worker trùng tên.
- ElevenLabs STT không khởi tạo: kiểm tra `ELEVEN_API_KEY`, `LIVEKIT_STT_PROVIDER=elevenlabs` và `LIVEKIT_STT_MODEL=scribe_v2_realtime`.
- Không có account sau khi restart: đang dùng `APP_ENV=test`, dữ liệu là memory;
  dùng account đăng ký trong DB dev hoặc chuyển sang PostgreSQL cho persistence.
- Không thấy giá thay đổi theo đường đi: đây là giới hạn hiện tại; demo chưa có
  routing map thật và giá chưa tính theo khoảng cách thực.

