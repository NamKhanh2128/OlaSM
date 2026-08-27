# 🚀 DEPLOYMENT GUIDE - AloSM Voice

## 📌 OVERVIEW

Dự án: **AloSM Voice** - Hệ thống đặt xe với Voice AI Agent (LiveKit integration)
- **Backend**: FastAPI + SQLite + LiveKit
- **Frontend**: React + Vite + LiveKit Client
- **Voice Agent**: LiveKit Agents với ElevenLabs STT/TTS, OpenAI LLM
- **VPS**: Ubuntu 24.04 LTS (Singapore) - IP: 149.28.131.104

---

## 🎯 BẮT ĐẦU NGAY

### **➡️ ĐỌC FILE NÀY TRƯỚC: [START-HERE.md](./START-HERE.md)**

File này chứa:
- Quick start guide
- Link đến tất cả tài liệu
- TL;DR deployment steps

### **Sau đó đọc theo thứ tự:**

1. **[CHECKLIST.md](./CHECKLIST.md)** - Step-by-step checklist ✅
2. **[FINAL-DEPLOY.md](./FINAL-DEPLOY.md)** - Chi tiết deployment 📖
3. **[DEPLOYMENT-SUMMARY.md](./DEPLOYMENT-SUMMARY.md)** - Technical deep dive 🔧

---

## 📚 TÀI LIỆU

### Documentation Files:

| File | Mô tả | Khi nào dùng |
|------|-------|--------------|
| **[START-HERE.md](./START-HERE.md)** | Điểm bắt đầu, tổng quan | Đọc đầu tiên ⭐ |
| **[CHECKLIST.md](./CHECKLIST.md)** | Checklist từng bước | Deploy thực tế ✅ |
| **[FINAL-DEPLOY.md](./FINAL-DEPLOY.md)** | Hướng dẫn chi tiết | Cần hiểu rõ hơn 📖 |
| **[DEPLOYMENT-SUMMARY.md](./DEPLOYMENT-SUMMARY.md)** | Tóm tắt kỹ thuật | Debug/maintenance 🔧 |
| **[DEPLOY-VPS-FINAL.sh](./DEPLOY-VPS-FINAL.sh)** | Script tự động | Chạy trên VPS 🤖 |
| **[COMMIT-MESSAGE.txt](./COMMIT-MESSAGE.txt)** | Git commit message | Tham khảo commit 📝 |

---

## ⚡ QUICK START

### 1. Upload code lên VPS

**Git (Khuyên dùng):**
```bash
git add .
git commit -m "Fix deployment"
git push
```

Trên VPS:
```bash
ssh root@149.28.131.104
cd /root/P-160
git pull
```

### 2. Deploy

```bash
cd /root/P-160
docker compose -f docker-compose.prod.yml down -v
rm -rf ./data
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d
sleep 20
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

### 3. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/bookings
# Open browser: http://149.28.131.104
```

---

## ✅ ISSUES FIXED

### 1. Uvicorn Permission Denied ✅
**Error:** `/usr/local/bin/python3.11: can't open file '/root/.local/bin/uvicorn': Permission denied`

**Fix:** 
- Dockerfile dùng `pip install --user`
- Added `ENV PATH=/root/.local/bin:$PATH`
- CMD: `python -m uvicorn`

### 2. SQLite Database Unable to Open ✅
**Error:** `sqlalchemy.exc.OperationalError: unable to open database file`

**Fix:**
- DATABASE_URL: `sqlite+aiosqlite:////app/data/app.db` (4 slashes)
- Docker volume thay vì bind mount
- Container run as root

### 3. Policy Catalog Not Found ✅
**Error:** `RuntimeError: policy catalog not found: /app/data/policies/catalog.json`

**Fix:**
- Tách static config ra khỏi `/app/data/`
- `data/policies/` → `/app/config/policies/` (trong image)
- `data/pricing/` → `/app/config/pricing/`
- `data/gazetteer/` → `/app/config/gazetteer/`
- Updated Python code paths

---

## 📦 FILES CHANGED

### Core Config (Phải upload):
```
✅ Dockerfile
✅ docker-compose.prod.yml
✅ .env.production
✅ src/backend/services/policy_service.py
✅ src/backend/services/pricing_catalog.py
✅ src/backend/services/place_search_service.py
```

### Documentation:
```
📄 START-HERE.md
📄 CHECKLIST.md
📄 FINAL-DEPLOY.md
📄 DEPLOYMENT-SUMMARY.md
📄 DEPLOY-VPS-FINAL.sh
📄 COMMIT-MESSAGE.txt
📄 README-DEPLOYMENT.md (this file)
```

---

## 🏗️ ARCHITECTURE

### Directory Structure (After Fix):

```
Docker Image (/app/)
├── config/                  # Static config (trong image, không mount)
│   ├── policies/
│   │   └── catalog.json
│   ├── pricing/
│   │   └── hanoi_demo_2026-08-16.yaml
│   └── gazetteer/
│       ├── place_names.json
│       └── ...
├── data/                    # Runtime data (Docker volume mount)
│   ├── app.db              # SQLite database
│   └── chroma/             # Vector store
└── src/                     # Source code
    └── ...
```

### Docker Volumes:

```
p-160_app-data (Docker managed volume)
└── /app/data in container
    ├── app.db
    └── chroma/
```

---

## 🔧 TECH STACK

### Backend:
- **Framework**: FastAPI 0.115+
- **Database**: SQLite (async via aiosqlite)
- **ORM**: SQLAlchemy 2.0 (async)
- **Voice**: LiveKit Agents + ElevenLabs + OpenAI

### Frontend:
- **Framework**: React + Vite
- **Voice UI**: LiveKit React Components
- **Deploy**: Nginx (port 80)

### Infrastructure:
- **Container**: Docker + Docker Compose
- **Web Server**: Nginx (frontend reverse proxy)
- **VPS**: Vultr Singapore - Ubuntu 24.04 LTS

---

## 🎊 SUCCESS CRITERIA

✅ Backend starts without errors  
✅ Database file created in Docker volume  
✅ Policy files accessible at `/app/config/policies/`  
✅ Health endpoint returns 200 OK  
✅ Bookings endpoint returns data (not 500)  
✅ Frontend loads successfully  
✅ Voice agent connects to LiveKit  

---

## 🆘 SUPPORT

### Get Help:

1. **Check logs:**
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=100 backend
   ```

2. **Check file structure:**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/
   docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/
   ```

3. **Check services:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

### Common Issues:

| Issue | Solution |
|-------|----------|
| Policy not found | Rebuild image: `docker compose build --no-cache backend` |
| Database error | Delete volume: `docker compose down -v` then up |
| Permission denied | Check Dockerfile has correct user setup |
| 500 on bookings | Check logs for actual error |

---

## 📞 VPS INFO

- **IP**: 149.28.131.104
- **User**: root
- **Project Path**: /root/P-160
- **Frontend URL**: http://149.28.131.104
- **Backend URL**: http://149.28.131.104:8000
- **LiveKit**: wss://alosm-4gr4lsjb.livekit.cloud

---

## 🎯 NEXT STEPS

1. ✅ Upload files lên VPS (Git hoặc SCP)
2. ✅ Deploy theo [CHECKLIST.md](./CHECKLIST.md)
3. ✅ Test endpoints và frontend
4. ✅ Monitor logs: `docker compose logs -f backend`

---

## 📝 NOTES

- Runtime data (database) và static config (policies) đã được tách riêng
- Docker volume cho data, files trong image cho config
- Đảm bảo không commit sensitive data (.env có trong .gitignore)
- Frontend có CORS config cho IP VPS

---

**Happy Deploying! 🚀**

Nếu cần hỗ trợ, bắt đầu từ [START-HERE.md](./START-HERE.md)
