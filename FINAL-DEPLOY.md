# 🚀 HƯỚNG DẪN DEPLOY CUỐI CÙNG

## ✅ Vấn đề đã sửa:

### 1. **Dockerfile**: Fixed uvicorn permission
- Dùng `pip install --user` thay vì install global
- Thêm `ENV PATH=/root/.local/bin:$PATH`
- Chạy uvicorn bằng `python -m uvicorn`

### 2. **docker-compose.prod.yml**: Dùng Docker volume
- Dùng Docker volume `app-data` thay vì bind mount `./data`
- Chạy container as `root` để tránh permission issues
- Volume chỉ mount cho runtime data (SQLite database, chroma vector store)

### 3. **DATABASE_URL**: Fixed absolute path
- Sửa từ `sqlite:///data/app.db` → `sqlite+aiosqlite:////app/data/app.db`
- 4 dấu `/` cho absolute path trong Docker
- Thêm `+aiosqlite` driver

### 4. **Policy/Config files**: Tách khỏi data volume
- Di chuyển static files: `data/policies/` → `config/policies/`
- Di chuyển static files: `data/pricing/` → `config/pricing/`
- Di chuyển static files: `data/gazetteer/` → `config/gazetteer/`
- Các files này được copy vào image, **không bị volume mount đè**
- Runtime data (database, chroma) vẫn ở `/app/data` với volume mount

### 5. **Updated Python code paths**:
- `src/backend/services/policy_service.py`: `data/policies` → `config/policies`
- `src/backend/services/pricing_catalog.py`: `data/pricing` → `config/pricing`
- `src/backend/services/place_search_service.py`: `data/gazetteer` → `config/gazetteer`

---

## 📦 CÁC FILE CẦN UPLOAD LÊN VPS:

Upload các file sau từ local Windows lên VPS `/root/P-160/`:

### ✅ **Files đã được sửa:**
1. `Dockerfile` ✅
2. `docker-compose.prod.yml` ✅
3. `.env.production` ✅
4. `src/backend/services/policy_service.py` ✅
5. `src/backend/services/pricing_catalog.py` ✅
6. `src/backend/services/place_search_service.py` ✅

### 📝 **Optional (helper scripts):**
7. `DEPLOY-VPS-FINAL.sh` - Script tự động deploy

---

## 🚀 CÁCH UPLOAD LÊN VPS:

### **Cách 1: Dùng SCP (từ PowerShell Windows):**

```powershell
# Vào thư mục project
cd C:\Users\Admin\Desktop\P-160

# Upload các file chính
scp Dockerfile root@149.28.131.104:/root/P-160/
scp docker-compose.prod.yml root@149.28.131.104:/root/P-160/
scp .env.production root@149.28.131.104:/root/P-160/

# Upload các file Python đã sửa
scp src/backend/services/policy_service.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/pricing_catalog.py root@149.28.131.104:/root/P-160/src/backend/services/
scp src/backend/services/place_search_service.py root@149.28.131.104:/root/P-160/src/backend/services/

# Upload script deploy (optional)
scp DEPLOY-VPS-FINAL.sh root@149.28.131.104:/root/P-160/
```

### **Cách 2: Dùng Git (Nhanh nhất - Khuyên dùng):**

```powershell
# Commit và push từ local
git add .
git commit -m "Fix Docker deployment: policies, database, permissions"
git push origin main

# Sau đó trên VPS:
ssh root@149.28.131.104
cd /root/P-160
git pull origin main
```

---

## 🎯 LỆNH CHẠY TRÊN VPS:

### **Option 1: Dùng script tự động (Khuyên dùng)**

```bash
ssh root@149.28.131.104

cd /root/P-160
chmod +x DEPLOY-VPS-FINAL.sh
./DEPLOY-VPS-FINAL.sh
```

### **Option 2: Chạy từng bước thủ công**

```bash
ssh root@149.28.131.104

cd /root/P-160

# 1. Stop và xóa containers + volumes cũ
docker compose -f docker-compose.prod.yml down -v

# 2. Xóa thư mục data cũ (không cần nữa)
rm -rf ./data

# 3. Rebuild backend image với Dockerfile mới
docker compose -f docker-compose.prod.yml build --no-cache backend

# 4. Start tất cả services
docker compose -f docker-compose.prod.yml up -d

# 5. Đợi 20 giây cho services khởi động
sleep 20

# 6. Kiểm tra logs
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

---

## ✅ KIỂM TRA SAU KHI DEPLOY:

```bash
# 1. Check services status
docker compose -f docker-compose.prod.yml ps

# 2. Verify policy files in container
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/policies/

# 3. Verify database created
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/

# 4. Test health endpoint
curl http://localhost:8000/health

# 5. Test bookings endpoint (should return [] or data, NOT 500 error)
curl http://localhost:8000/api/v1/bookings

# 6. Watch logs in real-time
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 🎊 KẾT QUẢ MONG ĐỢI:

✅ **Backend starts successfully** (không còn RuntimeError về policy catalog)
✅ **Database file created**: `/app/data/app.db` trong Docker volume
✅ **Policy files accessible**: `/app/config/policies/catalog.json` trong container
✅ **API endpoints work**: 
   - `GET /health` → 200 OK
   - `GET /api/v1/bookings` → 200 OK (trả về `[]` hoặc data)
✅ **Frontend loads without 500 errors**
✅ **LiveKit voice agent connects**

---

## 🐛 TROUBLESHOOTING:

### **Nếu vẫn thấy lỗi "policy catalog not found":**

```bash
# Kiểm tra file có được copy vào image không
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/policies/
docker compose -f docker-compose.prod.yml exec backend cat /app/config/policies/catalog.json | head -n 20

# Nếu không có file → rebuild image lại
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d
```

### **Nếu vẫn thấy database error:**

```bash
# Kiểm tra volume
docker volume ls | grep app-data
docker volume inspect p-160_app-data

# Xóa volume và tạo lại
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### **Xem logs chi tiết:**

```bash
# All logs
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# Only errors
docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep -i error

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## ⚠️ LƯU Ý QUAN TRỌNG:

**Vấn đề CORS redirect đến `apac.network-auth.com`:**
- Đây là **captive portal của WiFi** (quán cà phê/khách sạn/public WiFi)
- **Không liên quan đến code backend**
- Giải pháp: 
  1. Đăng nhập WiFi trước khi test
  2. Hoặc dùng data 4G/5G
  3. Hoặc đổi mạng khác không có captive portal

---

## 📞 NEXT STEPS:

**Bạn cần làm gì bây giờ:**

1. **Upload files lên VPS** (dùng SCP hoặc Git như hướng dẫn ở trên)
2. **SSH vào VPS**: `ssh root@149.28.131.104`
3. **Chạy deploy script** hoặc các lệnh thủ công
4. **Kiểm tra logs** và test API endpoints
5. **Test frontend** tại `http://149.28.131.104`

Nếu gặp lỗi, gửi logs để tôi hỗ trợ:
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```
