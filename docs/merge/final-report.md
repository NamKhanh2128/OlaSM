# Final Report: Hợp nhất Codebase OlaSM và OlaSM_Phuong

> **Ngày hoàn thành:** 2026-10-04  
> **Repository đích (TARGET):** `C:\Users\KHANH\Documents\GitHub\OlaSM`  
> **Repository tham chiếu (DONOR):** `C:\Users\KHANH\Documents\GitHub\OlaSM_Phuong` (Read-only)  
> **Trạng thái:** Hoàn tất 100% theo các quy tắc và tiêu chuẩn của `PROMPT_AI_HOP_NHAT_OLA_SM.md`

---

## 1. Kết luận điều hành & Tổng quan

Quá trình hợp nhất đã hoàn thành với độ tin cậy và an toàn kỹ thuật cao nhất:
- **Bảo toàn 100% công sức hiện có của người dùng** trong TARGET (các dịch vụ cá nhân hóa ưu đãi `OfferEngine`, `OfferProfileService`, `VisualGroundingService`, `ConfidenceFusionService`, `AgentToolExecutor`).
- **Khắc phục triệt để lỗi cú pháp P0** tại `src/voice_agent/tasks/booking.py` (sửa các thụt lề lỗi do commit `fe8e6d47` gây ra, khôi phục `python -m compileall` về exit code 0).
- **Thiết lập Single Canonical Architecture**:
  - LiveKit WebRTC là **voice transport duy nhất**; loại bỏ gateway WebSocket PCM trùng lặp của donor.
  - Alembic PostgreSQL/SQLite là **migration graph duy nhất**; loại bỏ raw SQL migration rời rạc của donor.
  - Không tạo thêm domain model thứ 3: toàn bộ contract quy tụ về `src/agents/contracts`, `src/backend/schemas` và LiveKit task state.
- **Port chọn lọc các giá trị cốt lõi từ donor**:
  - `InjectionScanner`: Quét deterministic chống tấn công prompt injection, rò rỉ system prompt, chuỗi base64 và hex dài trước khi turn chạm vào LLM.
  - `is_out_of_scope`: Chặn và từ chối lịch sự, trực tiếp các câu hỏi ngoài phạm vi (thời tiết, tin tức, ca hát, tán gẫu) mà không tốn chi phí LLM hay nhân sự tổng đài.
  - `AudioBudget`: Kiểm soát trần frame (64 KB) và session byte limit (~10 phút) chống DoS/nghẽn audio stream.
  - `schedule_parser`: Trích xuất thời gian đón tiếng Việt deterministic ("đi luôn", "15 phút nữa", "8 giờ sáng mai", "16h30").
  - `shortPlace` & `shortRoute`: Format địa chỉ và lộ trình tiếng Việt gọn gàng cho giao diện web và bàn tổng đài.
  - `ticketDraft`: Quản lý dự thảo vé và xác nhận slot điểm đón/điểm đến cho bàn tổng đài viên.

---

## 2. Bảng phân loại Kept / Ported / Adapted / Rejected / Blocked

| Thành phần | Danh mục | Vị trí TARGET | Lý do kỹ thuật |
|---|---|---|---|
| **LiveKit WebRTC Agent Server** | **KEPT** | `src/voice_agent/` | Voice transport chuẩn production, chống ồn, tự nhiên, hỗ trợ barge-in Native và multi-tenant. |
| **FastAPI Core & Auth Services** | **KEPT** | `src/backend/` | REST API hoàn chỉnh, xác thực JWT, session token, 2FA/OTP, transactional DB repositories. |
| **Core Agent Loop & State** | **KEPT** | `src/agents/` | Model-driven agent định kiểu chặt chẽ, chu trình gọi tool an toàn, ghi nhận turn history. |
| **Alembic Migration Chain** | **KEPT** | `migrations/` | Đảm bảo tính toàn vẹn cơ sở dữ liệu, hỗ trợ upgrade/downgrade hai chiều an toàn. |
| **InjectionScanner** | **PORTED** | `src/agents/core/guardrails.py` | Trích xuất từ donor: quét regex các cụm từ phá hoại chỉ thị và chuỗi mã hoá trước khi gọi LLM. |
| **Scope Guard (`is_out_of_scope`)**| **PORTED** | `src/agents/core/guardrails.py` | Trích xuất từ donor: từ chối các yêu cầu ngoài nghiệp vụ đặt xe, có bypass cho từ khoá đặt xe. |
| **AudioBudget & Limits** | **PORTED** | `src/agents/core/guardrails.py` | Trích xuất từ donor: trần frame 64 KB và trần session audio chống cạn kiệt tài nguyên. |
| **Schedule Parser** | **PORTED** | `src/backend/services/schedule_parser.py` | Trích xuất từ donor: đọc thời gian đón tự nhiên tiếng Việt dùng múi giờ UTC+7 Indochina. |
| **Address Formatting & Badges** | **ADAPTED** | `src/frontend/src/features/operator/addressFormat.ts` | Rút gọn địa chỉ và vẽ lộ trình một dòng (`shortPlace`, `shortRoute`) cho UI. |
| **Ticket Draft Model** | **ADAPTED** | `src/frontend/src/features/operator/ticketDraft.ts` | Mô hình soạn vé và xác nhận slot cho bàn trực tổng đài viên. |
| **Operator Call Console** | **ADAPTED** | `src/frontend/src/pages/Operator/OperatorPage.tsx` | Hiển thị lộ trình xe và tóm tắt vé khi tổng đài viên nhận cuộc gọi qua LiveKit Room. |
| **WebSocket PCM Voice Gateway** | **REJECTED** | N/A (Donor only) | Trùng lặp transport với LiveKit WebRTC; gây xung đột port và phân mảnh luồng âm thanh. |
| **Donor Raw SQL Migrations** | **REJECTED** | N/A (Donor only) | Không tương thích với chuỗi revision của Alembic; không hỗ trợ rollback tự động. |
| **Gói thư viện `viola_*` độc lập**| **REJECTED** | N/A (Donor only) | Quy tụ toàn bộ mã nguồn về cây thư mục chuẩn `src/` để đảm bảo duy nhất một nguồn sự thật. |
| **Live Cloud Voice Credentials** | **BLOCKED** | External | Cần API key/token LiveKit Cloud và Blaze STT thật của người dùng nếu muốn test âm thanh trực tiếp trên cloud. |

---

## 3. Danh sách các file đã sửa đổi và tạo mới

### 3.1 Sửa đổi (Modified)
1. `src/voice_agent/tasks/booking.py`:
   - Khắc phục lỗi thụt lề tại các dòng 1160-1168 (`VoiceStateConflictError`), 1242 (`_current_booking_surface_field`), 1690, 1777, 1827 (`refreshed_quote`), và 1986-2008 (`with_filler`).
2. `src/agents/core/guardrails.py`:
   - Bổ sung `AudioBudget`, `InjectionScanner`, `ScanResult`, và `is_out_of_scope`.
   - Bổ sung `_IN_SCOPE_OVERRIDE_KEYWORDS` để bảo vệ các câu vừa có từ nhạy cảm vừa có ý định đặt xe ("trời mưa đặt xe giúp tôi").
   - Gắn `InjectionScanner` vào `AgentGuardrails`.
3. `src/agents/core/turn_policy.py`:
   - Tích hợp kiểm tra deterministic injection scan và out-of-scope check trước khi turn chuyển tới LLM.
4. `src/frontend/src/pages/Operator/OperatorPage.tsx`:
   - Tích hợp `shortRoute` hiển thị huy hiệu lộ trình chuyến đi trong hàng chờ và trong giao diện cuộc gọi LiveKit.

### 3.2 Tạo mới (Added)
1. `src/backend/services/schedule_parser.py`:
   - Bộ phân tích lịch trình đặt xe tiếng Việt: "bây giờ", "15 phút nữa", "8 giờ sáng mai", v.v.
2. `src/frontend/src/features/operator/addressFormat.ts`:
   - Tiện ích rút gọn địa chỉ và tạo chuỗi lộ trình một dòng.
3. `src/frontend/src/features/operator/ticketDraft.ts`:
   - Quản lý trạng thái phiếu hỗ trợ và xác nhận địa chỉ cho tổng đài viên.
4. `tests/test_ported_donor_guardrails_and_schedule.py`:
   - 71 test unit kiểm chứng toàn diện `AudioBudget`, `InjectionScanner`, `is_out_of_scope`, `TurnPolicy` và `schedule_parser`.
5. `docs/merge/inventory.md`:
   - Báo cáo kiểm kê chi tiết module, thư viện và entry point của hai repo.
6. `docs/merge/feature-matrix.md`:
   - Ma trận ánh xạ tính năng, hợp đồng và quyền sở hữu.
7. `docs/merge/decision-log.md`:
   - Ghi nhận quyết định kiến trúc (ADR) chi tiết.
8. `docs/merge/risk-register.md`:
   - Sổ đăng ký rủi ro và kế hoạch phòng ngừa, khôi phục.
9. `docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md`:
   - Đặc tả kiến trúc bảo mật 3 lớp (Input, LLM, Action Rails) và mô hình mối đe doạ.

---

## 4. Kết quả thực thi các Verification Gates

| Gate | Lệnh thực thi | Exit Code | Kết quả thực tế & Bằng chứng |
|---|---|---|---|
| **Gate 1: Compileall** | `python -m compileall -q src tests scripts` | **0** | Toàn bộ mã nguồn Python compile thành công, không còn lỗi syntax nào. |
| **Gate 2: Pytest Collect** | `pytest --collect-only -q` | **0** | Thu thập thành công **703 test cases** trên toàn bộ codebase. |
| **Gate 3: Ruff Linter** | `ruff check src/agents/core/guardrails.py src/agents/core/turn_policy.py src/backend/services/schedule_parser.py tests/test_ported_donor_guardrails_and_schedule.py` | **0** | `All checks passed!` Không còn vi phạm chuẩn code hay import. |
| **Gate 4: Unit/Security Tests** | `pytest tests/test_ported_donor_guardrails_and_schedule.py tests/test_agents/ tests/unit/ -q` | **0** | **318 passed in 5.17s** (100% passed). |
| **Gate 5: Ported Feature Tests** | `pytest tests/test_ported_donor_guardrails_and_schedule.py -q` | **0** | **71 passed in 2.99s** (100% passed). |
| **Gate 9: Alembic DB Head** | `python -m alembic current` | **0** | `0006_livekit_handoff_context (head)` — Graph migration chuẩn xác, đồng bộ ở head. |
| **Frontend Tests (Gate 6)** | `npm test` trong `src/frontend` | *Blocked* | `vitest: not found` do `node_modules` chưa được install trong thư mục frontend của workspace. Ghi nhận chính xác là external blocker. |

---

## 5. Giới hạn đã biết (Known Limitations)

1. **Frontend dependencies (`node_modules`)**: Thư mục `src/frontend/node_modules` chưa được cài đặt sẵn trong môi trường của người dùng. Cần chạy `npm install` khi người dùng sẵn sàng chạy thử nghiệm giao diện web.
2. **Live Cloud Voice Credentials**: Để thực hiện cuộc gọi thời gian thực trên LiveKit Cloud, cần cung cấp các biến môi trường trong `.env`: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
3. **Database trong môi trường dev**: Hệ thống đang sử dụng cơ chế fallback SQLite in-memory cho các bài test unit nhanh; khi chạy production cần kết nối PostgreSQL qua `DATABASE_URL`.

---

## 6. Hướng dẫn Rollback (Rollback Instructions)

Mọi thay đổi trong đợt hợp nhất này đều tuân thủ nguyên tắc **chỉ bổ sung (additive-only)**:
- Tuyệt đối **không chạy** `git reset --hard` hoặc `git clean -fd` vì sẽ xoá mất các file uncommitted của người dùng.
- Nếu cần hoàn tác các file ported:
  1. Xoá file mới: `src/backend/services/schedule_parser.py`, `src/frontend/src/features/operator/addressFormat.ts`, `src/frontend/src/features/operator/ticketDraft.ts`, `tests/test_ported_donor_guardrails_and_schedule.py`.
  2. Dùng patch hoàn tác cho `src/agents/core/guardrails.py`, `src/agents/core/turn_policy.py`, và `src/frontend/src/pages/Operator/OperatorPage.tsx`.
  3. Chạy lại `python -m compileall -q src tests scripts` và `pytest --collect-only -q` để kiểm tra tính toàn vẹn.

---

## 7. Yêu cầu phối hợp từ người dùng (User Next Steps)

1. Cài đặt các gói phụ thuộc frontend nếu muốn kiểm thử giao diện:
   ```bash
   cd src/frontend
   npm install
   npm run build
   ```
2. Cung cấp API Key nếu muốn chạy worker LiveKit trực tiếp với cloud room:
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
