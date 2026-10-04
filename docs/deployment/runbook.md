# 🚀 OlaSM Production Deployment Runbook

Tài liệu chuẩn hóa quy trình triển khai môi trường production cho hệ thống **OlaSM (GSM Voice Agent)**.

---

## 1. Kiến Trúc & Container Topology

Hệ thống được đóng gói và vận hành qua `docker-compose.prod.yml` gồm 3 container chính:

```mermaid
graph TD
    Client[Browser / Voice Client] -->|HTTP / HTTPS:80| Frontend[Frontend Nginx SPA]
    Client -->|WebSocket / WebRTC| LiveKit[LiveKit Cloud / Self-hosted]
    Frontend -->|Reverse Proxy /api| Backend[FastAPI Backend :8000]
    Backend -->|Postgres / Supabase| DB[(PostgreSQL Database)]
    Backend -->|Cache / Sessions| Redis[(Redis)]
    VoiceWorker[LiveKit Voice Worker] -->|RTC Agent Session| LiveKit
    VoiceWorker -->|Internal API / DB| Backend
```

| Service | Container Name | Image / Build Context | Port | Health Check |
|---|---|---|---|---|
| **backend** | `backend` | `./Dockerfile` | `8000:8000` | `GET http://localhost:8000/health` (30s interval) |
| **voice-worker** | `voice-worker` | `./Dockerfile` (`python -m src.voice_agent.server dev`) | Worker Mode (No HTTP port) | Phụ thuộc `backend: service_healthy` |
| **frontend** | `frontend` | `./src/frontend/Dockerfile` | `80:80` | Nginx HTTP response 200/304 |

---

## 2. Yêu Cầu Tiền Trình Khai (Prerequisites)

- **Hệ điều hành:** Linux (Ubuntu 22.04 LTS khuyến nghị) hoặc Docker-enabled host.
- **Tài nguyên tối thiểu:** 2 vCPU, 4GB RAM, 20GB Disk.
- **Phần mềm bắt buộc:**
  - Docker Engine >= 24.0.0
  - Docker Compose Plugin >= 2.20.0
  - Git >= 2.34.0
- **Network / Firewalls:**
  - Inbound Port 80 / 443 (HTTP/HTTPS)
  - Inbound Port 8000 (Backend API - có thể giới hạn internal qua Nginx)
  - Outbound internet access cho các API dịch vụ: OpenAI, LiveKit Cloud, DeepSeek, Google Gemini.

---

## 3. Cấu Hình Môi Trường (`.env.production`)

Tạo file `.env.production` tại thư mục gốc repository dựa trên mẫu:

```env
# --- Server Environment ---
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=change-this-to-a-very-secure-random-string

# --- Database & Cache ---
DATABASE_URL=postgresql://user:password@db-host:5432/olasm_db
REDIS_URL=redis://redis-host:6379/0

# --- LiveKit WebRTC Configuration ---
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxx
LIVEKIT_API_SECRET=SECRETxxxxxxxxx
LIVEKIT_STT_PROVIDER=livekit
LIVEKIT_STT_MODEL=deepgram/nova-3
LIVEKIT_STT_LANGUAGE=multi
LIVEKIT_TURN_DETECTION=vad

# --- LLM Providers ---
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# --- Voice & TTS ---
ELEVENLABS_API_KEY=...
VIET_TTS_URL=http://localhost:5002/synthesize
```

---

## 4. Quy Trình Triển Khai (Deployment Procedures)

### 4.1 Triển Khai Lần Đầu (Initial Deployment)

```bash
# 1. Clone repository
git clone https://github.com/YourRepo/OlaSM.git /app/olasm
cd /app/olasm

# 2. Tạo file cấu hình môi trường
cp .env.example .env.production
nano .env.production  # Điền đầy đủ API keys & DB URLs

# 3. Chạy migrations cơ sở dữ liệu
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 4. Build và khởi động toàn bộ services
docker compose -f docker-compose.prod.yml up -d --build

# 5. Kiểm tra trạng thái containers
docker compose -f docker-compose.prod.yml ps
```

### 4.2 Cập Nhật Phiên Bản (Rolling Update / CD)

```bash
cd /app/olasm

# 1. Pull code mới nhất
git pull origin main

# 2. Chạy migration nếu có schema mới
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 3. Build lại image không cache và restart
docker compose -f docker-compose.prod.yml up -d --build --no-deps backend voice-worker frontend

# 4. Dọn dẹp images cũ
docker image prune -f
```

---

## 5. Kiểm Tra Hoạt Động (Health Checks & Smoke Tests)

1. **Backend Health Check:**
   ```bash
   curl -i http://localhost:8000/health
   # Kỳ vọng trả về: HTTP 200 OK {"status": "ok", ...}
   ```
2. **API Documentation:**
   ```bash
   curl -I http://localhost:8000/docs
   # Kỳ vọng: HTTP 200 OK
   ```
3. **Voice Worker Status:**
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=50 voice-worker
   # Kỳ vọng: Worker kết nối thành công tới LiveKit Cloud ("connected to room / worker registered")
   ```
4. **Frontend Check:**
   ```bash
   curl -I http://localhost/
   # Kỳ vọng: HTTP 200 OK từ Nginx
   ```

---

## 6. Vận Hành & Khắc Phục Sự Cố (Troubleshooting)

### Lệnh Vận Hành Thường Dùng:

```bash
# Xem log realtime theo service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f voice-worker
docker compose -f docker-compose.prod.yml logs -f frontend

# Khởi động lại service cụ thể
docker compose -f docker-compose.prod.yml restart voice-worker

# Dừng toàn bộ hệ thống
docker compose -f docker-compose.prod.yml down
```

### Các Lỗi Phổ Biến & Cách Xử Lý:

1. **Backend Healthcheck Unhealthy:**
   - Kiểm tra log: `docker compose -f docker-compose.prod.yml logs backend`.
   - Nguyên nhân thường gặp: `DATABASE_URL` không kết nối được hoặc timeout mạng đến Supabase/PostgreSQL.
2. **Voice Worker Thoát Với Mã Lỗi:**
   - Worker là RTC client, phụ thuộc vào kết nối tới LiveKit Cloud.
   - Kiểm tra `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
   - Đảm bảo `LIVEKIT_TURN_DETECTION=vad` và model STT chính xác (`deepgram/nova-3`).
3. **CORS / Frontend Không Gọi Được Backend:**
   - Đảm bảo biến `VITE_API_BASE_URL` trong frontend trỏ đúng domain hoặc Nginx proxy `/api` sang backend cổng 8000.
