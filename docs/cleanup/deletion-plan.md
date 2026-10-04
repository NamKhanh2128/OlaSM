# Controlled Deletion & Archive Plan

- **Thời điểm lập kế hoạch:** 2026-10-04T16:27:45+07:00
- **Nguyên tắc an toàn:** Không dùng lệnh xóa hàng loạt; thực hiện từng bước có kiểm tra biên dịch và test.

---

## 1. Pha 2: Dọn dẹp Generated / Cache Allowlist

### 1.1 Danh sách mục xử lý

1. `.pytest_cache/`: Thư mục cache của pytest.
2. `.ruff_cache/`: Thư mục cache của ruff.
3. `.coverage`: Tệp dữ liệu coverage tạm.
4. `asr_server/`: Thư mục rỗng (chỉ chứa `__pycache__` cũ).
5. `src/voice/`: Thư mục rỗng (chỉ chứa `__pycache__` cũ).
6. `tests/test_voice/`: Thư mục rỗng (chỉ chứa `__pycache__` cũ).
7. `data/skills/`: Thư mục copy thừa (untracked & ignored).

### 1.2 Lệnh thực thi an toàn
Chỉ xóa đích danh từng thư mục/tệp cụ thể qua PowerShell:
```powershell
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .ruff_cache
Remove-Item -Force -ErrorAction SilentlyContinue .coverage
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue asr_server
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue src\voice
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue tests\test_voice
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue data\skills
```

### 1.3 Kiểm tra xác thực sau Pha 2
- `python -m compileall -q src tests scripts` -> Exit code 0.
- `pytest --collect-only -q` -> 703 tests collected.

---

## 2. Pha 3: Xử lý Root main.py & Lưu trữ Deployment Scripts

### 2.1 Xóa Root `main.py`
- Xác nhận: Không còn bất kỳ import nào. Entrypoint là `src/main.py`.
- Thao tác: Xóa file `main.py` tại thư mục gốc.
- Rollback: `git restore main.py`.

### 2.2 Tạo Runbook Quy chuẩn & Lưu trữ Deployment Scripts cũ
- Tạo `docs/deployment/runbook.md` tổng hợp hướng dẫn triển khai canonical (LiveKit + FastAPI + React).
- Tạo thư mục `docs/archive/deployment/` kèm `README.md` chỉ mục.
- Di chuyển các file deployment phân tán tại root vào `docs/archive/deployment/`:
  - `FINAL-DEPLOY.md`
  - `DEPLOY-FIX.md`
  - `DEPLOYMENT-SUMMARY.md`
  - `README-DEPLOYMENT.md`
  - `deploy_mustdo.md`
  - `final-deploy.sh`
  - `fix-deploy.sh`
  - `quick-fix.sh`
  - `vps-fix-database.sh`
  - `fix-voice-worker.sh`
  - `deploy-fixed.sh`
  - `DEPLOY-VPS-FINAL.sh`
- Cập nhật liên kết trong `START-HERE.md` để trỏ tới `docs/deployment/runbook.md` và thư mục archive.

---

## 3. Pha 4 & 5: Verification & Hoàn tất

- Chạy toàn bộ Verification Gates theo mục H của prompt.
- Ghi nhận báo cáo tại `docs/cleanup/verification.md`, `docs/cleanup/rollback.md` và `docs/cleanup/final-report.md`.
