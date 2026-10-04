# Reference Impact Analysis

- **Thời điểm phân tích:** 2026-10-04T16:27:30+07:00
- **Mục tiêu:** Kiểm tra mọi tác động tham chiếu (import graph, reference graph, link markdown, config) trước khi thực hiện dọn dẹp và lưu trữ.

---

## 1. Phân tích tác động của các mục Generated & Cache

| Đường dẫn dự kiến dọn | Tham chiếu mã nguồn | Tham chiếu cấu hình/CI | Tác động thực tế |
|---|---|---|---|
| `.pytest_cache/` | Không | Không | 0 rủi ro. Tự sinh lại khi chạy `pytest`. |
| `.ruff_cache/` | Không | Không | 0 rủi ro. Tự sinh lại khi chạy `ruff check`. |
| `.coverage` | Không | Không | 0 rủi ro. Tự sinh lại khi chạy coverage. |
| `asr_server/` (chỉ chứa `__pycache__`) | Không | Không | 0 rủi ro. Thư mục rỗng không có file mã nguồn nào. |
| `src/voice/` (chỉ chứa `__pycache__`) | Không | Không | 0 rủi ro. Toàn bộ voice runtime active nằm tại `src/voice_agent/`. |
| `tests/test_voice/` (chỉ chứa `__pycache__`) | Không | Không | 0 rủi ro. Test suite active nằm tại `tests/test_voice_agent/`. |
| `data/skills/` | Không | Không | 0 rủi ro. Bản copy thừa, Antigravity IDE đọc `.agents/skills`. |

---

## 2. Phân tích tác động của Root `main.py`

- **Nội dung:**
  ```python
  def main():
      print("Hello from p-160!")

  if __name__ == "__main__":
      main()
  ```
- **Kiểm tra Import Graph:**
  - `git grep "from main import"` -> Không tìm thấy.
  - `git grep "import main"` -> Không tìm thấy.
- **Kiểm tra Entrypoint:**
  - `pyproject.toml` -> Không định nghĩa console script tới `main:main`.
  - `Makefile` -> Sử dụng `uvicorn src.main:app` và `python -m src.voice_agent.server`.
  - `Dockerfile` -> Sử dụng `src.main:app`.
  - `docker-compose.yml` -> Sử dụng `src.main:app`.
- **Tác động:** Không có module nào phụ thuộc. Xóa an toàn. Rollback dễ dàng qua `git restore main.py`.

---

## 3. Phân tích tác động của việc Archive Deployment Scripts

- **Các tệp được lưu trữ:**
  - `FINAL-DEPLOY.md`, `DEPLOY-FIX.md`, `DEPLOYMENT-SUMMARY.md`, `README-DEPLOYMENT.md`, `deploy_mustdo.md`
  - `final-deploy.sh`, `fix-deploy.sh`, `quick-fix.sh`, `vps-fix-database.sh`, `fix-voice-worker.sh`, `deploy-fixed.sh`, `DEPLOY-VPS-FINAL.sh`
- **Thư mục đích:** `docs/archive/deployment/`
- **Các tệp tài liệu tham chiếu:**
  - `START-HERE.md`: Tham chiếu tới `FINAL-DEPLOY.md` và `DEPLOYMENT-SUMMARY.md`.
  - `CHECKLIST.md`: Tham chiếu quy trình deploy VPS.
- **Biện pháp cập nhật:**
  - Tạo runbook quy chuẩn tại `docs/deployment/runbook.md` tổng hợp hướng dẫn triển khai chuẩn.
  - Cập nhật các liên kết trong `START-HERE.md` trỏ về `docs/deployment/runbook.md` hoặc `docs/archive/deployment/`.
  - Tạo `docs/archive/deployment/README.md` giải thích nguồn gốc lịch sử của các script fix VPS.
