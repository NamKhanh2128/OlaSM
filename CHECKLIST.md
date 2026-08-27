# ✅ DEPLOYMENT CHECKLIST

## 📦 BƯỚC 1: UPLOAD FILES LÊN VPS

### Cách A: Dùng Git (Nhanh nhất - Khuyên dùng)

Trên Windows local:
```powershell
cd C:\Users\Admin\Desktop\P-160
git add .
git commit -m "Fix Docker deployment issues"
git push origin main
```

Trên VPS:
```bash
ssh root@149.28.131.104
cd /root/P-160
git pull origin main
```

### Cách B: Dùng SCP

Trên Windows PowerShell:
```powershell
cd C:\Users\Admin\Desktop\P-160

# Upload files chính
scp Dockerfile root@149.28.131.104:/root/P-160/
scp docker-compose.prod.yml root@149.28.131.104:/root/P-160/
scp .env.production root@149.28.131.104:/root/P-160/

# Upload Python files
scp src/backend/services/policy_service.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/pricing_catalog.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/place_search_service.py root@149.28.131.104:/root/P-160/src/backend/services/
```

---

## 🚀 BƯỚC 2: DEPLOY TRÊN VPS

SSH vào VPS:
```bash
ssh root@149.28.131.104
```

Chạy các lệnh sau:
```bash
cd /root/P-160

# 1. Stop containers cũ
docker compose -f docker-compose.prod.yml down -v

# 2. Xóa data cũ
rm -rf ./data

# 3. Rebuild backend
docker compose -f docker-compose.prod.yml build --no-cache backend

# 4. Start services
docker compose -f docker-compose.prod.yml up -d

# 5. Đợi 20 giây
sleep 20

# 6. Xem logs
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

---

## ✅ BƯỚC 3: KIỂM TRA

Chạy từng lệnh sau và check kết quả:

### 3.1. Check services running
```bash
docker compose -f docker-compose.prod.yml ps
```
**Mong đợi:** 3 containers running (backend, frontend, voice-worker)

### 3.2. Check policy files
```bash
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/policies/
```
**Mong đợi:** Thấy file `catalog.json`

### 3.3. Check database
```bash
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/
```
**Mong đợi:** Thấy file `app.db`

### 3.4. Test health endpoint
```bash
curl http://localhost:8000/health
```
**Mong đợi:** `{"status":"ok",...}`

### 3.5. Test bookings endpoint
```bash
curl http://localhost:8000/api/v1/bookings
```
**Mong đợi:** `[]` hoặc data (KHÔNG phải 500 error)

### 3.6. Test frontend
Mở browser: `http://149.28.131.104`
**Mong đợi:** Frontend load, không có lỗi 500

---

## 🎊 HOÀN THÀNH!

Nếu tất cả check đều PASS:
- ✅ Backend đang chạy
- ✅ Database đã tạo
- ✅ Policy files có sẵn
- ✅ API endpoints hoạt động
- ✅ Frontend load thành công

**🎉 Deployment thành công!**

---

## ❌ NẾU CÓ LỖI

### Lỗi: Policy catalog not found
```bash
# Check xem file có không
docker compose -f docker-compose.prod.yml exec backend cat /app/config/policies/catalog.json | head

# Nếu không có, rebuild lại
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d
```

### Lỗi: Database error
```bash
# Xóa volume và tạo lại
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### Xem logs chi tiết
```bash
# Xem 100 dòng logs cuối
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# Chỉ xem errors
docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep -i error

# Follow logs real-time
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 📞 CẦN TRỢ GIÚP?

Gửi output của:
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/
docker compose -f docker-compose.prod.yml ps
```
