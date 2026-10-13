# 🚀 BẮT ĐẦU VỚI OLASM VOICE CORE

Hướng dẫn khởi động và hiểu cấu trúc **OlaSM Voice Core** — trợ lý giọng nói tích hợp vào app mobile Green SM.

---

## 🎯 SẢN PHẨM LÀ GÌ?

OlaSM **không phải** là một web app đặt xe độc lập.

OlaSM là **lớp voice assistant nằm bên trong app Green SM của VinGroup**. Người dùng bấm nút microphone trong Green SM → nói → OlaSM hiểu → Green SM thực thi.

---

## 📄 TÀI LIỆU CHÍNH THỨC

1. **📋 [docs/PRD_OlaSM_Voice.md](./docs/PRD_OlaSM_Voice.md)** — Product Requirements Document (đã cập nhật theo hướng voice control layer)

2. **🏗 [docs/architecture_diagram.md](./docs/architecture_diagram.md)** — Kiến trúc hệ thống: Green SM app → OlaSM Voice Gateway → Green SM APIs

3. **🛡️ [docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md](./docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md)** — Guardrails 3 lớp + typed action contract

4. **📊 [docs/PRODUCT_BRIEF.md](./docs/PRODUCT_BRIEF.md)** — Định vị sản phẩm và lộ trình

5. **🗺 [docs/TIEN_TRINH_POC_CHUAN.md](./docs/TIEN_TRINH_POC_CHUAN.md)** — Tiến trình POC 6 tuần

---

## ⚡ KHỞI ĐỘNG TEST HARNESS (WEB)

Web frontend chỉ là **test harness nội bộ**, không phải sản phẩm thật.

```bash
# Cài đặt
uv sync

# Backend (port 8000)
uv run uvicorn src.backend.main:app --reload

# LiveKit voice worker
uv run python -m src.voice_agent.server

# Frontend test harness (port 5173)
cd src/frontend && npm install && npm run dev
```

Hoặc dùng script:
```powershell
.\start-dev.bat
```

---

## 🔑 BIẾN MÔI TRƯỜNG QUAN TRỌNG

```env
# LLM cho voice agent
OPENAI_API_KEY=...

# LiveKit (voice realtime)
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Database (local dev dùng SQLite)
DATABASE_URL=sqlite:///./data/app.db
```

Xem đầy đủ tại `.env.example`.

---

## 🧪 KIỂM THỬ HỆ THỐNG

```powershell
# Chạy toàn bộ test suite
uv run pytest -q

# Lint
uv run ruff check src tests

# Frontend
cd src/frontend && npm run lint && npm run build
```

---

## 📦 CẤU TRÚC QUAN TRỌNG

```
src/
  agents/contracts/      ← AppContext, AppAction, AppScreen (typed contract)
  agents/core/           ← LLM agent, guardrails, mobile instructions
  voice_agent/           ← LiveKit session, app-control tools
  backend/               ← FastAPI API, session service
  frontend/              ← Test harness nội bộ (KHÔNG phải sản phẩm)
docs/
  PRD_OlaSM_Voice.md     ← Đặc tả yêu cầu
  architecture_diagram.md← Kiến trúc hệ thống
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

> **GSMSandboxClient** chỉ dùng cho unit test. Không được dùng để demo tích hợp Green SM thật.

> **"Đóng app"** = dừng voice + giải phóng microphone. iOS/Android không cho app tự force-quit.

> Sản phẩm thật là **mobile SDK** tích hợp vào app Green SM — cần chốt API chính thức với team Green SM trước.

---

*OlaSM Voice Core — VRIC × GSM Smart City, Nhóm 4*
