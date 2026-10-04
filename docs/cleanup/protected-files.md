# Protected Files Manifest

- **Thời điểm ghi nhận:** 2026-10-04T16:25:00+07:00
- **Nguyên tắc:** Mọi file trong danh sách này là **PROTECTED_UNTIL_EXPLICIT_CONFIRMATION**. Tuyệt đối không xóa, không format ghi đè, không revert hay clean.

---

## 1. Modified Tracked Files (Thay đổi của người dùng & tính năng đang phát triển)

| Đường dẫn tệp | Mục đích / Vai trò | Trạng thái bảo vệ |
|---|---|---|
| `src/agents/contracts/schemas.py` | Bổ sung schemas cho tính năng offer engine | **PROTECTED** |
| `src/agents/core/booking/state.py` | Mở rộng trạng thái booking cho offer context | **PROTECTED** |
| `src/agents/core/guardrails.py` | Tích hợp InjectionScanner, is_out_of_scope, AudioBudget từ donor | **PROTECTED** |
| `src/agents/core/instructions.py` | Bổ sung chính sách chỉ dẫn cho ưu đãi và xác nhận | **PROTECTED** |
| `src/agents/core/tools.py` | Bổ sung định nghĩa tool cá nhân hóa ưu đãi | **PROTECTED** |
| `src/agents/core/turn_policy.py` | Tích hợp deterministic pre-LLM injection & scope guards | **PROTECTED** |
| `src/backend/services/agent_tool_executor.py` | Triển khai logic xử lý tool ưu đãi, grounding, fusion | **PROTECTED** |
| `src/frontend/src/features/livekit/tokenSource.test.ts` | Test token LiveKit frontend | **PROTECTED** |
| `src/frontend/src/pages/Operator/OperatorPage.tsx` | Nâng cấp giao diện operator với route badges và ticket draft | **PROTECTED** |
| `src/voice_agent/tasks/booking.py` | Sửa thụt lề P0 và đồng bộ trạng thái giọng nói | **PROTECTED** |

---

## 2. Untracked Files (Tính năng mới, Báo cáo & Tài liệu dự án)

| Đường dẫn tệp | Mục đích / Vai trò | Trạng thái bảo vệ |
|---|---|---|
| `BaoCao_KyThuat_POC_Nhom4_OlaSM.docx` | Báo cáo kỹ thuật POC nhóm 4 | **PROTECTED** |
| `BaoCao_YTuong_Nhom4_OlaSM.docx` | Báo cáo ý tưởng ban đầu nhóm 4 | **PROTECTED** |
| `docs/OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md` | Đặc tả bảo mật 3 lớp và threat model | **PROTECTED** |
| `docs/merge/decision-log.md` | Bản ghi quyết định kiến trúc merge (ADR) | **PROTECTED** |
| `docs/merge/feature-matrix.md` | Ma trận tính năng merge | **PROTECTED** |
| `docs/merge/final-report.md` | Báo cáo hoàn tất hợp nhất codebase | **PROTECTED** |
| `docs/merge/inventory.md` | Kiểm kê hai repository | **PROTECTED** |
| `docs/merge/risk-register.md` | Sổ đăng ký rủi ro merge | **PROTECTED** |
| `migrations/versions/coe_001_offer_tables.py` | Migration Alembic cho bảng ưu đãi COE | **PROTECTED** |
| `scripts/generate_poc_docx.py` | Script tạo docx báo cáo kỹ thuật | **PROTECTED** |
| `scripts/generate_poc_docx_clean.py` | Script tạo docx sạch | **PROTECTED** |
| `src/backend/services/confidence_fusion_service.py` | Service kết hợp độ tin cậy đa phương thức | **PROTECTED** |
| `src/backend/services/offer_engine.py` | Service gợi ý mã khuyến mãi cá nhân hóa | **PROTECTED** |
| `src/backend/services/offer_profile_service.py` | Service hồ sơ hành vi người dùng | **PROTECTED** |
| `src/backend/services/schedule_parser.py` | Service phân tích lịch trình tiếng Việt (ported) | **PROTECTED** |
| `src/backend/services/visual_grounding_service.py` | Service nhận diện địa điểm bằng thị giác | **PROTECTED** |
| `src/frontend/src/features/operator/addressFormat.ts` | Tiện ích định dạng địa chỉ tiếng Việt cho UI (ported) | **PROTECTED** |
| `src/frontend/src/features/operator/ticketDraft.ts` | Mô hình quản lý phiếu cho tổng đài viên (ported) | **PROTECTED** |
| `tests/test_audit_and_formulas_verification.py` | Bộ test kiểm chứng công thức kỹ thuật | **PROTECTED** |
| `tests/test_ported_donor_guardrails_and_schedule.py` | 71 test kiểm chứng guardrails & schedule parser | **PROTECTED** |
| `~$oCao_KyThuat_POC_Nhom4_OlaSM.docx` | Lock file tạm của Word khi mở file docx | **PROTECTED / LOCK FILE** |

---

## 3. Quy tắc hành xử bắt buộc

1. Tuyệt đối **không chạy** các lệnh xóa hàng loạt như `git clean -fd`, `git reset --hard`.
2. Không thực hiện bất kỳ thao tác xóa hoặc ghi đè nào đối với các file trên.
3. Khi dọn dẹp cache hoặc generated files, chỉ xóa đích danh các đường dẫn trong danh mục Allowlist đã được xác thực an toàn.
