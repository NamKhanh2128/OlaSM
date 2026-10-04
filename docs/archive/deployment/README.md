# 📦 Deployment Standardization Note

Tất cả các lỗi và giải pháp triển khai VPS trước đây (ngày 31/08/2026) đã được **tích hợp trực tiếp và chính thức vào mã nguồn chính (Native Codebase)**:

1. **Khởi tạo Database SQLite tự động**:
   - Tích hợp tại: `src/backend/db/base.py` (hàm `get_engine`).
   - Tự động kiểm tra và tạo thư mục cha (`Path.mkdir(parents=True, exist_ok=True)`) khi khởi tạo engine SQLite. Loại bỏ hoàn toàn nhu cầu dùng script quyền `chmod 777` hay `mkdir data` thủ công.

2. **Cơ chế nạp Static Policy / Pricing Catalog linh hoạt**:
   - Tích hợp tại: `src/backend/services/policy_service.py`, `src/backend/services/pricing_catalog.py`, `src/backend/services/place_search_service.py`.
   - Cơ chế fallback linh hoạt giữa `data/` và `config/` giúp ứng dụng luôn tìm thấy file cấu hình ngay cả khi Docker mount volume.

3. **Chuẩn hóa Dockerfile & Makefile**:
   - Tích hợp tại: `Dockerfile` và `Makefile`.
   - Sửa triệt để entrypoint uvicorn thành `src.backend.main:app`.
   - Đầy đủ dependencies trong `requirements.txt` (bao gồm `rapidfuzz`, `aiosqlite`, `livekit-agents`...).

4. **Script triển khai tiêu chuẩn duy nhất**:
   - Script chính thức: `scripts/deploy.sh`.
   - Docker Compose chính thức: `docker-compose.prod.yml`.
   - Tài liệu vận hành duy nhất: `docs/deployment/runbook.md`.

Do toàn bộ giải pháp đã trở thành mã nguồn chuẩn, các script vá lỗi tạm thời (`quick-fix.sh`, `vps-fix-database.sh`, `final-deploy.sh`, `fix-voice-worker.sh`, v.v.) đã được dọn dẹp hoàn toàn khỏi dự án.
