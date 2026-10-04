# Rollback Procedures for Cleanup

- **Thời điểm:** 2026-10-04T16:27:50+07:00
- **Nguyên tắc an toàn:** Tuyệt đối không dùng `git reset --hard` hay `git clean -fd`. Mọi rollback phải có tính chọn lọc và có thể đảo ngược từng phần.

---

## 1. Rollback cho Root `main.py`
Nếu cần khôi phục lại file scaffold `main.py` tại root (hiện đang ở trạng thái staged delete):
```bash
git restore --staged main.py
git restore main.py
# Hoặc lệnh tương đương:
git checkout HEAD -- main.py
```

---

## 2. Rollback cho Thư mục Deployment Archive
Nếu cần đưa các script/tài liệu deployment từ `docs/archive/deployment/` về lại root:
```powershell
Move-Item docs/archive/deployment/*.sh .
Move-Item docs/archive/deployment/*.md .
# Lưu ý: Giữ lại README.md của archive nếu cần
```
Hoặc dùng git:
```bash
git mv docs/archive/deployment/<filename> ./<filename>
```

---

## 3. Khôi phục Cache & Generated Files
- Cache `.pytest_cache/`, `.ruff_cache/`, `__pycache__/` tự động được tái tạo khi chạy lệnh test/lint/compile.
- Không cần rollback thủ công cho cache.

---

## 4. Khôi phục Virtual Environment (nếu có yêu cầu cài lại)
- `.venv/` hiện đang được giữ nguyên 100%.
- Nếu cần tái tạo môi trường:
  ```bash
  uv venv --python 3.12 .venv
  uv sync
  ```
