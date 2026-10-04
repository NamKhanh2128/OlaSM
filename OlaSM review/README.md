# OlaSM — Gói nhận xét cuối trước Demo Day

- Cutoff: **03/09/2026**.
- Technical baseline: `origin/main@74c6a06dda9ba506c9b57dbec09ca88858281e75`.
- Last Gate: **25 case — PASS 7, FAIL 9, FLAKY 0, BLOCKED 9, NOT_RUN 0**.

## Nên đọc theo thứ tự

1. [AI20K_DEMO_DAY_EVALUATION.md](AI20K_DEMO_DAY_EVALUATION.md): nhận xét thực trạng và những gì cần bổ sung; evidence kỹ thuật chỉ lấy từ `origin/main`, live E2E được ghi riêng là bằng chứng quan sát bổ trợ.
2. [e2e/LATEST_CONSOLIDATED_RESULTS.md](e2e/LATEST_CONSOLIDATED_RESULTS.md): verdict Last Gate mới nhất theo từng stable ID.
3. [e2e/FAIL_REGRESSION_20260902-144231.md](e2e/FAIL_REGRESSION_20260902-144231.md): chi tiết các case từng FAIL, actual behavior và evidence.
4. [e2e/BLOCKER_COMPLETION_20260902-225202.md](e2e/BLOCKER_COMPLETION_20260902-225202.md): chi tiết các case blocker đã cố chạy lại.
5. [e2e/FULL_TEST_CATALOG.md](e2e/FULL_TEST_CATALOG.md): mô tả đầy đủ persona, behavior, bước test và oracle.
6. `historical_review/`: review/evidence các vòng trước để đối chiếu lịch sử.

## Cách hiểu kết quả

- `PASS`: behavior quan sát được đáp ứng oracle.
- `FAIL`: behavior quan sát được vi phạm business/safety/AI oracle; không cần HTTP error mới tính FAIL.
- `FLAKY`: cùng intent cho kết quả pass/fail không ổn định.
- `BLOCKED`: thiếu điều kiện để tới oracle; team cần cung cấp fixture/control/account hoặc sửa bootstrap rồi retest.
- Các chuỗi synthetic có hình thức giống credential đã được redacted trong bản ZIP; bản gốc của evidence trong workspace không bị sửa.
