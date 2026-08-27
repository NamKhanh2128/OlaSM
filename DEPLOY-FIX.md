# 🚀 Hướng dẫn Fix Lỗi Deploy trên VPS

## Lỗi hiện tại:
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

## Nguyên nhân:
- Thư mục `./data` trên VPS chưa tồn tại hoặc không có quyền ghi
- Container không thể tạo file SQLite database

## Cách fix (chạy trên VPS):

### Option 1: Chạy script tự động (Khuyên dùng)

```bash
cd /root/P-160

# Upload file Dockerfile và fix-deploy.sh mới lên server
# Sau đó chạy:

chmod +x fix-deploy.sh
./fix-deploy.sh
```

### Option 2: Chạy từng bước thủ công

```bash
cd /root/P-160

# 1. Tạo thư mục data với quyền đầy đủ
mkdir -p ./data
chmod -R 777 ./data

# 2. Pull Dockerfile mới từ local (hoặc copy nội dung mới)
# Đảm bảo Dockerfile có dòng: RUN mkdir -p /app/data && chmod -R 777 /app/data

# 3. Stop services
docker compose -f docker-compose.prod.yml down

# 4. Rebuild backend
docker compose -f docker-compose.prod.yml build --no-cache backend

# 5. Start lại
docker compose -f docker-compose.prod.yml up -d

# 6. Kiểm tra logs
docker compose -f docker-compose.prod.yml logs -f backend
```

## Kiểm tra sau khi fix:

```bash
# Check services running
docker compose -f docker-compose.prod.yml ps

# Check backend logs
docker compose -f docker-compose.prod.yml logs --tail=50 backend

# Check database file created
ls -la ./data/

# Test API
curl http://localhost:8000/health
```

## Kết quả mong đợi:

✅ Backend service running và healthy
✅ File `./data/app.db` được tạo thành công
✅ API endpoint `/health` trả về 200 OK
✅ Không còn lỗi "unable to open database file"
