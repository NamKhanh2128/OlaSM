# 🚀 BẮT ĐẦU TỪ ĐÂY

## 📄 TÀI LIỆU QUAN TRỌNG

Tôi đã tạo sẵn 4 files hướng dẫn chi tiết:

1. **📋 [CHECKLIST.md](./CHECKLIST.md)** ⭐ **BẮT ĐẦU TỪ ĐÂY**
   - Checklist từng bước để deploy
   - Đơn giản, dễ follow
   - **ĐỌC FILE NÀY TRƯỚC**

2. **📖 [FINAL-DEPLOY.md](./FINAL-DEPLOY.md)**
   - Hướng dẫn deploy chi tiết đầy đủ
   - Giải thích từng bước
   - Troubleshooting guide

3. **📚 [DEPLOYMENT-SUMMARY.md](./DEPLOYMENT-SUMMARY.md)**
   - Tổng hợp kỹ thuật về tất cả fixes
   - Giải thích tại sao cần fix
   - Chi tiết các thay đổi trong code

4. **🤖 [DEPLOY-VPS-FINAL.sh](./DEPLOY-VPS-FINAL.sh)**
   - Script tự động deploy
   - Upload lên VPS và chạy

---

## ⚡ DEPLOY NHANH (TL;DR)

### Bước 1: Upload code lên VPS

**Option A: Dùng Git (Khuyên dùng)**
```bash
# Trên Windows
git add .
git commit -m "Fix deployment"
git push

# Trên VPS
ssh root@149.28.131.104
cd /root/P-160
git pull
```

**Option B: Dùng SCP**
```powershell
# Trên Windows PowerShell
cd C:\Users\Admin\Desktop\P-160
scp Dockerfile root@149.28.131.104:/root/P-160/
scp docker-compose.prod.yml root@149.28.131.104:/root/P-160/
scp .env.production root@149.28.131.104:/root/P-160/
scp src/backend/services/policy_service.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/pricing_catalog.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/place_search_service.py root@149.28.131.104:/root/P-160/src/backend/services/
```

### Bước 2: Deploy trên VPS

```bash
# SSH vào VPS
ssh root@149.28.131.104

# Deploy
cd /root/P-160
docker compose -f docker-compose.prod.yml down -v
rm -rf ./data
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d

# Đợi và check
sleep 20
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

### Bước 3: Kiểm tra

```bash
# Test API
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/bookings

# Test frontend
# Mở browser: http://149.28.131.104
```

---

## ✅ CÁC VẤN ĐỀ ĐÃ FIX

1. ✅ **Uvicorn permission denied** → Fixed Dockerfile
2. ✅ **Database unable to open** → Fixed volume mount + DATABASE_URL
3. ✅ **Policy catalog not found** → Tách config ra khỏi data/

---

## 📦 FILES ĐÃ THAY ĐỔI

### Quan trọng (phải upload lên VPS):
- `Dockerfile` ✅
- `docker-compose.prod.yml` ✅
- `.env.production` ✅
- `src/backend/services/policy_service.py` ✅
- `src/backend/services/pricing_catalog.py` ✅
- `src/backend/services/place_search_service.py` ✅

### Documentation (tham khảo):
- `CHECKLIST.md`
- `FINAL-DEPLOY.md`
- `DEPLOYMENT-SUMMARY.md`
- `DEPLOY-VPS-FINAL.sh`
- `START-HERE.md` (file này)

---

## 🎯 NEXT STEPS

1. **Upload files** lên VPS (dùng Git hoặc SCP)
2. **Đọc CHECKLIST.md** và làm theo từng bước
3. **Deploy** theo hướng dẫn
4. **Test** endpoints và frontend
5. **Nếu có lỗi**, xem troubleshooting trong FINAL-DEPLOY.md

---

## 🆘 CẦN TRỢ GIÚP?

Nếu gặp lỗi sau khi deploy, gửi output của:

```bash
# Logs
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# File structure
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/

# Services status
docker compose -f docker-compose.prod.yml ps
```

---

## 📞 VPS INFO

- **IP:** 149.28.131.104
- **User:** root
- **Project Path:** /root/P-160
- **Frontend URL:** http://149.28.131.104
- **Backend URL:** http://149.28.131.104:8000

---

## 🎉 CHÚC BẠN DEPLOY THÀNH CÔNG!

Hãy bắt đầu từ **[CHECKLIST.md](./CHECKLIST.md)** nhé! 🚀
