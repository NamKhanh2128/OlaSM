# 🚀 BẮT ĐẦU VỚI OLASM

Hướng dẫn khởi động nhanh và triển khai hệ thống **OlaSM (Voice AI Ride-Hailing Agent)**.

---

## 📄 TÀI LIỆU CHÍNH THỨC

1. **📖 [docs/deployment/runbook.md](./docs/deployment/runbook.md)** ⭐ **QUY TRÌNH DEPLOY CHUẨN HOÁ**
   - Hướng dẫn cấu hình Docker Compose cho toàn bộ cụm: `backend`, `voice-worker`, `frontend`
   - Cấu hình biến môi trường `.env.production` và LiveKit WebRTC
   - Healthcheck & troubleshooting

2. **📋 [docs/PRD_OlaSM_Voice.md](./docs/PRD_OlaSM_Voice.md)**
   - Đặc tả yêu cầu kỹ thuật & nghiệp vụ của hệ thống tổng đài giọng nói đặt xe

3. **🛡️ [docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md](./docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md)**
   - Đặc tả 3 lớp bảo vệ: Prompt Injection, Out-of-Scope, PII Redaction & Xác nhận đặt xe

---

## ⚡ KHỞI ĐỘNG VÀ TRIỂN KHAI

### Cách 1: Chạy Local Development

```powershell
# Chạy script khởi động toàn bộ môi trường dev (Backend + Worker + Frontend)
.\start-dev.bat
```

Hoặc qua `Makefile`:
```bash
make livekit-backend   # Khởi động FastAPI Backend (:8000)
make livekit-worker    # Khởi động LiveKit Voice Agent Worker
make livekit-frontend  # Khởi động React Web UI (:5173)
```

### Cách 2: Triển khai Production / VPS bằng Docker Compose

Toàn bộ các bản vá lỗi về quyền ghi cơ sở dữ liệu SQLite, định tuyến nạp catalog chính sách, và entrypoint container đã được tích hợp trực tiếp vào mã nguồn chính.

Triển khai tự động bằng script chuẩn duy nhất:
```bash
# Cấp quyền và chạy deploy tự động
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Hoặc chạy trực tiếp bằng Docker Compose:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Kiểm tra trạng thái container và health endpoint:
```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

---

## 🧪 KIỂM THỬ HỆ THỐNG

Chạy toàn bộ 694 automated tests:
```powershell
pytest tests/ -q
```
