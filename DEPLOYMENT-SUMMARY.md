# 📋 TÓM TẮT DEPLOYMENT FIX

## 🎯 MỤC TIÊU
Deploy backend + frontend + voice agent lên VPS với LiveKit integration

---

## ❌ CÁC LỖI ĐÃ GẶP VÀ CÁCH FIX

### 1. **Lỗi: Permission denied on uvicorn**
```
/usr/local/bin/python3.11: can't open file '/root/.local/bin/uvicorn': Permission denied
```

**Nguyên nhân:** Dockerfile cài packages sai cách, uvicorn không có quyền thực thi

**Fix:** 
- Dùng `pip install --user` trong build stage
- Copy `/root/.local` từ builder
- Thêm `ENV PATH=/root/.local/bin:$PATH`
- CMD dùng `python -m uvicorn` thay vì gọi trực tiếp

### 2. **Lỗi: Unable to open database file**
```
sqlalchemy.exc.OperationalError: unable to open database file
```

**Nguyên nhân:** 
- DATABASE_URL sai format (thiếu driver và absolute path)
- Bind mount `./data` trên VPS không có quyền ghi

**Fix:**
- Sửa DATABASE_URL: `sqlite+aiosqlite:////app/data/app.db` (4 dấu `/`)
- Dùng Docker volume thay vì bind mount
- Add `user: root` trong docker-compose

### 3. **Lỗi: Policy catalog not found**
```
RuntimeError: policy catalog not found: /app/data/policies/catalog.json
```

**Nguyên nhân:** 
- Static files (policies, pricing, gazetteer) nằm trong `/app/data/`
- Docker volume mount `/app/data` đè lên static files trong image

**Fix:**
- Di chuyển static files ra khỏi `/app/data/`
- Tạo thư mục `/app/config/` trong image
- Copy: `data/policies/` → `config/policies/`
- Copy: `data/pricing/` → `config/pricing/`
- Copy: `data/gazetteer/` → `config/gazetteer/`
- Update Python code paths trong 3 files:
  - `src/backend/services/policy_service.py`
  - `src/backend/services/pricing_catalog.py`
  - `src/backend/services/place_search_service.py`

---

## 📁 CẤU TRÚC THƯ MỤC SAU KHI FIX

### **Trong Docker Image:**
```
/app/
├── src/                          # Source code
├── config/                       # Static config files (trong image)
│   ├── policies/
│   │   └── catalog.json
│   ├── pricing/
│   │   └── hanoi_demo_2026-08-16.yaml
│   └── gazetteer/
│       ├── place_names.json
│       ├── hanoi_place_aliases.json
│       └── hanoi_landmark_pickup_points.json
├── data/                         # Runtime data (mounted as volume)
│   ├── app.db                    # SQLite database
│   └── chroma/                   # Vector store
└── requirements.txt
```

### **Docker Volume:**
```
p-160_app-data (Docker managed volume)
└── Chứa runtime data:
    ├── app.db
    └── chroma/
```

---

## 🔧 FILES ĐÃ THAY ĐỔI

### 1. **Dockerfile**
```dockerfile
# Stage 1: Build with --user flag
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Copy .local và set PATH
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy static config files to /app/config
RUN mkdir -p /app/config/policies && \
    cp -r /app/data/policies/* /app/config/policies/ && \
    cp -r /app/data/pricing /app/config/ && \
    cp -r /app/data/gazetteer /app/config/

# CMD with python -m uvicorn
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. **docker-compose.prod.yml**
```yaml
volumes:
  app-data:  # Docker managed volume

services:
  backend:
    volumes:
      - app-data:/app/data  # Volume mount instead of bind mount
    user: root              # Run as root
```

### 3. **.env.production**
```bash
# Fixed DATABASE_URL with driver and absolute path
DATABASE_URL=sqlite+aiosqlite:////app/data/app.db
```

### 4. **Python service files (3 files)**
- `src/backend/services/policy_service.py`: `data/policies` → `config/policies`
- `src/backend/services/pricing_catalog.py`: `data/pricing` → `config/pricing`
- `src/backend/services/place_search_service.py`: `data/gazetteer` → `config/gazetteer`

---

## 🚀 DEPLOYMENT STEPS

### **1. Upload files lên VPS**
```bash
# Option A: Dùng SCP
scp Dockerfile root@149.28.131.104:/root/P-160/
scp docker-compose.prod.yml root@149.28.131.104:/root/P-160/
scp .env.production root@149.28.131.104:/root/P-160/
scp src/backend/services/*.py root@149.28.131.104:/root/P-160/src/backend/services/

# Option B: Dùng Git (khuyên dùng)
git add .
git commit -m "Fix deployment"
git push
# Sau đó trên VPS: git pull
```

### **2. Deploy trên VPS**
```bash
ssh root@149.28.131.104
cd /root/P-160

# Stop old containers
docker compose -f docker-compose.prod.yml down -v

# Remove old data directory
rm -rf ./data

# Rebuild and start
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d

# Wait and check
sleep 20
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

### **3. Verify deployment**
```bash
# Check policy files
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/policies/

# Check database
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/

# Test APIs
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/bookings
```

---

## ✅ KẾT QUẢ MONG ĐỢI

1. ✅ Backend khởi động thành công (không có lỗi RuntimeError)
2. ✅ Database file `/app/data/app.db` được tạo trong Docker volume
3. ✅ Policy files accessible tại `/app/config/policies/catalog.json`
4. ✅ API `/health` trả về 200 OK
5. ✅ API `/api/v1/bookings` trả về 200 OK (không còn 500 error)
6. ✅ Frontend load thành công không có lỗi
7. ✅ Voice agent có thể kết nối LiveKit

---

## 📝 NOTES

### **Runtime Data vs Static Config**
- **Runtime data** (database, vector store): Trong Docker volume `/app/data`
- **Static config** (policies, pricing, gazetteer): Trong Docker image `/app/config`

### **Why Docker Volume?**
- Không phụ thuộc host filesystem permissions
- Docker tự quản lý
- Không bị SELinux/AppArmor chặn
- Dễ backup/restore

### **Why Separate config/ directory?**
- Static files không bị volume mount đè
- Clear separation: runtime data vs static config
- Dễ quản lý và debug

---

## 🆘 TROUBLESHOOTING

### **Nếu backend không start:**
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep -i error
```

### **Nếu thiếu policy files:**
```bash
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/
docker compose -f docker-compose.prod.yml build --no-cache backend
```

### **Nếu database lỗi:**
```bash
docker volume rm p-160_app-data
docker compose -f docker-compose.prod.yml up -d
```

---

## 📞 CONTACT

Để hỗ trợ, gửi:
1. Container logs: `docker compose logs backend`
2. File structure: `docker compose exec backend ls -la /app/config/`
3. Volume info: `docker volume inspect p-160_app-data`
