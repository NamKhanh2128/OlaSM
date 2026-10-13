"""
Script tạo/cập nhật các file báo cáo DOCX theo hướng mới:
OlaSM Voice Core = Voice assistant tích hợp vào app mobile Green SM.
Chạy: python scripts/update_bao_cao_docs.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).parent.parent


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _doc() -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    return doc


def _heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _para(doc: Document, text: str, bold: bool = False, italic: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic


def _table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for run in hdr[i].paragraphs[0].runs:
            run.bold = True
    for r_idx, row in enumerate(rows):
        cells = table.rows[r_idx + 1].cells
        for c_idx, cell_text in enumerate(row):
            cells[c_idx].text = cell_text


def _hr(doc: Document) -> None:
    doc.add_paragraph("─" * 60)


# ─────────────────────────────────────────────
# 1. BaoCao_YTuong_Nhom4_OlaSM.docx
# ─────────────────────────────────────────────

def make_y_tuong() -> None:
    doc = _doc()
    _heading(doc, "Báo Cáo Ý Tưởng — OlaSM Voice Core")
    _para(doc, "Nhóm 4: Mobility Assistant | VRIC × GSM Smart City")
    _para(doc, "Thành viên: Nguyễn Đức Nam Khánh (2A202601103) & Nguyễn Thị Phương (2A202601315)")
    _para(doc, "Cố vấn: TS. Lê Duy Dũng (VinUniversity) & Anh Lê Yên Thanh (VRIC × GSM)")
    _hr(doc)

    _heading(doc, "1. Ý Tưởng Cốt Lõi", level=2)
    _para(doc,
        "OlaSM Voice Core là trợ lý giọng nói tích hợp bên trong ứng dụng mobile Green SM của VinGroup. "
        "Người dùng chỉ cần bấm nút microphone trong Green SM → nói yêu cầu bằng tiếng Việt tự nhiên → "
        "OlaSM hiểu và điều khiển app → Green SM thực thi. Không cần tải thêm app, không cần mở website."
    )
    _para(doc,
        "Green SM đã có đầy đủ tính năng: đặt xe Car/Mini/Bike, Food, Express, theo dõi chuyến, thanh toán. "
        "Rào cản duy nhất là người dùng phải biết thao tác màn hình. OlaSM phá bỏ rào cản đó."
    )

    _heading(doc, "2. Vấn Đề Cần Giải Quyết", level=2)
    _table(doc,
        ["Nhóm người dùng", "Rào cản hiện tại"],
        [
            ["Người lớn tuổi, ít quen công nghệ", "Không dùng được app, phải nhờ người khác"],
            ["Người bận tay (đang mang hành lý, bế con)", "Không thuận tiện chạm màn hình"],
            ["Người trong tình huống cần tốc độ", "App có nhiều bước thao tác"],
            ["Người có vấn đề về thị lực hoặc vận động", "UI chưa tối ưu cho accessibility"],
        ]
    )

    _heading(doc, "3. Giải Pháp Đề Xuất", level=2)
    _para(doc, "Voice control layer tích hợp vào Green SM mobile, hoạt động theo giao thức:")
    _para(doc, "Bước 1: Người dùng bấm nút microphone trong Green SM")
    _para(doc, "Bước 2: OlaSM nhận giọng nói → STT → LLM hiểu intent → hỏi lại nếu chưa rõ")
    _para(doc, "Bước 3: OlaSM tạo danh sách AppAction typed → Green SM thực thi")
    _para(doc, "Bước 4: Green SM trả kết quả → OlaSM đọc lại bằng TTS")
    _para(doc, "Bước 5: Người dùng xác nhận → Green SM hoàn thành booking/action")

    _heading(doc, "4. Typed Action Contract", level=2)
    _para(doc,
        "OlaSM chỉ được phát action trong allowlist. Không emit code, URL hay thao tác tự do. "
        "Mọi side effect (đặt xe, hủy, thanh toán) đều yêu cầu xác nhận tường minh."
    )
    _table(doc,
        ["Action", "Mô tả", "Risk Level"],
        [
            ["NAVIGATE", "Chuyển màn hình trong Green SM", "SAFE_NAVIGATION"],
            ["GO_BACK", "Quay lại màn hình trước", "SAFE_NAVIGATION"],
            ["READ_SCREEN", "Đọc nội dung màn hình", "SAFE_NAVIGATION"],
            ["SET_FIELD", "Điền trường được quảng bá", "USER_CONFIRMATION"],
            ["SELECT_OPTION", "Chọn option trong danh sách", "USER_CONFIRMATION"],
            ["SUBMIT", "Gửi action có side effect", "APP_CONFIRMATION"],
            ["OPEN_HELP", "Mở màn hình hỗ trợ", "SAFE_NAVIGATION"],
            ["REQUEST_OPEN_APP", "Yêu cầu OS mở lại app", "OS_MANAGED"],
            ["END_ASSISTANT", "Dừng voice, giải phóng mic", "SAFE_NAVIGATION"],
        ]
    )

    _heading(doc, "5. Phạm Vi MVP (Phase 1)", level=2)
    _para(doc, "- Kênh: push-to-talk (bấm để nói), tiếng Việt")
    _para(doc, "- Dịch vụ: Green SM Car / Green SM Mini")
    _para(doc, "- Điểm đón: lấy tự động từ vị trí hiện tại của app")
    _para(doc, "- Điểm đến: nói tự nhiên → OlaSM resolve")
    _para(doc, "- Thanh toán: chọn từ danh sách app trả về")
    _para(doc, "- Fallback: chuyển text hoặc thao tác tay bất kỳ lúc nào")
    _para(doc, "- 'Đóng app' = dừng voice + giải phóng microphone (iOS/Android không cho force-quit)")

    _heading(doc, "6. Những Gì OlaSM Không Làm", level=2)
    _para(doc, "- Không xây app đặt xe riêng cạnh Green SM")
    _para(doc, "- Không lưu dữ liệu booking riêng (không phải source of truth)")
    _para(doc, "- Không tự tính giá hay tạo mock driver")
    _para(doc, "- Không reverse-engineer app Green SM")
    _para(doc, "- Không force-quit app trên iOS/Android")
    _para(doc, "- Không nhận thông tin thẻ/OTP qua voice và đưa vào LLM")

    _heading(doc, "7. Lộ Trình", level=2)
    _table(doc,
        ["Phase", "Mục tiêu", "Trạng thái"],
        [
            ["Phase 0", "Chốt API/SDK với team Green SM", "EXTERNAL_BLOCKED"],
            ["Phase 1 (MVP)", "Voice-to-book cho Green SM Car", "IN_PROGRESS"],
            ["Phase 2", "Trợ lý trong chuyến: tracking, hủy, hỗ trợ", "ROADMAP"],
            ["Phase 3", "Mở rộng: Bike, Express, Food, đặt hộ", "ROADMAP"],
        ]
    )

    out = ROOT / "BaoCao_YTuong_Nhom4_OlaSM.docx"
    doc.save(str(out))
    print(f"✓ {out.name}")


# ─────────────────────────────────────────────
# 2. BaoCao_TomTat_POC_Nhom4_OlaSM.docx
# ─────────────────────────────────────────────

def make_tom_tat() -> None:
    doc = _doc()
    _heading(doc, "Báo Cáo Tóm Tắt POC — OlaSM Voice Core")
    _para(doc, "Trợ lý Giọng nói Điều khiển App Mobile Green SM")
    _para(doc, "Nhóm 4 | VRIC × GSM Smart City | 13/10/2026")
    _para(doc, "Nguyễn Đức Nam Khánh (2A202601103) & Nguyễn Thị Phương (2A202601315)")
    _hr(doc)

    _heading(doc, "⚠️ PIVOT SẢN PHẨM (2026-10-13)", level=2)
    _para(doc,
        "OlaSM không còn là web app đặt xe độc lập. "
        "OlaSM là lớp voice assistant tích hợp bên trong app mobile Green SM của VinGroup. "
        "Người dùng bấm microphone trong Green SM → nói → OlaSM xử lý → Green SM thực thi. "
        "Green SM là nguồn dữ liệu, booking và thanh toán chính thức duy nhất.",
        bold=True
    )

    _heading(doc, "1. Tóm Tắt Executive", level=2)
    _para(doc,
        "OlaSM Voice Core giải quyết bài toán: người dùng Green SM không cần chạm màn hình để thực hiện "
        "bất kỳ thao tác nào trong app. Đây là tính năng voice assistant tích hợp — không phải app mới."
    )

    _heading(doc, "2. Tiến Độ Phase 3 (Sau Pivot)", level=2)
    _table(doc,
        ["Giai đoạn", "Nội dung", "Trạng thái"],
        [
            ["Tuần 1–3", "Voice pipeline, dialog state, guardrails, STT/LLM/TTS (TTFA P95 = 1.41s)", "HOÀN TẤT"],
            ["Pivot Tuần 4", "Typed AppAction contract, AppContext, 8 app-control tools, LiveKit state sync", "HOÀN TẤT"],
            ["Tuần 5–6", "Green SM API integration, mobile SDK adapter, E2E test", "BLOCKED/ROADMAP"],
        ]
    )

    _heading(doc, "3. Kiến Trúc Hệ Thống", level=2)
    _para(doc, "Green SM Mobile App → Voice Assistant UI ← OlaSM Mobile SDK")
    _para(doc, "  └── OlaSM Voice Gateway")
    _para(doc, "        ├── LiveKit WebRTC (real-time audio)")
    _para(doc, "        ├── STT → LLM → TTS pipeline")
    _para(doc, "        ├── Dialog State Machine")
    _para(doc, "        ├── AppContext validator")
    _para(doc, "        ├── AppAction dispatcher (typed, allowlisted)")
    _para(doc, "        └── Guardrails (3 lớp)")
    _para(doc, "              └── Green SM Official APIs")
    _para(doc, "                    (Place, Quote, Booking, Trip, Payment, Support)")

    _heading(doc, "4. Các Trụ Cột Kỹ Thuật", level=2)

    _heading(doc, "4.1 Voice Streaming Pipeline (Giữ lại)", level=3)
    _para(doc, "- LiveKit WebRTC hai chiều, Silero VAD, VietnameseAudioChunker")
    _para(doc, "- TTFA P95 = 1.41s (vượt chuẩn ≤ 1.5s)")

    _heading(doc, "4.2 Typed AppAction Contract (Mới)", level=3)
    _para(doc, "- 9 action kinds: NAVIGATE, GO_BACK, READ_SCREEN, SET_FIELD, SELECT_OPTION, SUBMIT, OPEN_HELP, REQUEST_OPEN_APP, END_ASSISTANT")
    _para(doc, "- 5 risk levels từ SAFE_NAVIGATION đến BIOMETRIC_REQUIRED")
    _para(doc, "- Model chỉ được phát action trong allowlist — không emit code hay URL")

    _heading(doc, "4.3 Guardrails 3 Lớp (Mở rộng)", level=3)
    _para(doc, "- Input Rail: chặn 100% prompt injection")
    _para(doc, "- App Action Rail: validate AppContext, kiểm tra capability_allowed")
    _para(doc, "- Output Rail: xác nhận explicit confirmation trước mọi side effect")

    _heading(doc, "4.4 AppContext ↔ AppActionResult Protocol (Mới)", level=3)
    _para(doc, "- Mobile host gửi AppContext (màn hình, available_actions, screen_summary) mỗi lượt")
    _para(doc, "- OlaSM trả AppAction list có TTL → mobile thực thi → trả AppActionResult")
    _para(doc, "- LiveKit data channel publish trên topic 'olasm.app_control.v1'")

    _heading(doc, "5. Chỉ Số Kỹ Thuật", level=2)
    _table(doc,
        ["Chỉ số", "Mục tiêu", "Kết quả", "Đánh giá"],
        [
            ["TTFA P95", "≤ 1.5s", "1.41s", "Vượt chỉ tiêu"],
            ["Typed AppAction contract", "Implemented", "Implemented", "Đạt"],
            ["Guardrail app action validation", "Implemented", "Implemented", "Đạt"],
            ["Green SM API integration", "Phase 1 target", "EXTERNAL_BLOCKED", "Cần chốt với GSM"],
            ["Mobile SDK", "Phase 1 target", "EXTERNAL_BLOCKED", "Phụ thuộc công nghệ GSM"],
        ]
    )

    _heading(doc, "6. Điều Kiện Tiên Quyết từ Green SM", level=2)
    _para(doc, "Để hoàn thành Phase 1, cần làm việc với team Green SM để có:")
    _para(doc, "- API xác thực người dùng")
    _para(doc, "- API tìm kiếm địa điểm (Place / Address)")
    _para(doc, "- API báo giá (Quote / Pricing)")
    _para(doc, "- API tạo/hủy booking")
    _para(doc, "- API trạng thái chuyến và ETA")
    _para(doc, "- API khuyến mãi và thanh toán")
    _para(doc, "- Sandbox, test account và webhook")
    _para(doc, "- Xác nhận công nghệ app: native iOS/Android, Flutter hay React Native", bold=True)

    out = ROOT / "BaoCao_TomTat_POC_Nhom4_OlaSM.docx"
    doc.save(str(out))
    print(f"✓ {out.name}")


# ─────────────────────────────────────────────
# 3. BaoCao_KyThuat_POC_Nhom4_OlaSM.docx (updated)
# ─────────────────────────────────────────────

def make_ky_thuat_updated() -> None:
    doc = _doc()
    _heading(doc, "Báo Cáo Kỹ Thuật POC — OlaSM Voice Core")
    _para(doc, "Trợ lý Giọng nói Điều khiển App Mobile Green SM của VinGroup")
    _para(doc, "Phiên bản: 2.0 (Sau Pivot 2026-10-13)")
    _para(doc, "Nhóm 4 | VRIC × GSM Smart City")
    _para(doc, "Nguyễn Đức Nam Khánh (2A202601103) & Nguyễn Thị Phương (2A202601315)")
    _hr(doc)

    _heading(doc, "1. Tổng Quan Sản Phẩm", level=2)
    _para(doc,
        "OlaSM Voice Core là lớp voice assistant tích hợp bên trong app mobile Green SM. "
        "Người dùng bấm nút microphone trong Green SM → nói yêu cầu → OlaSM xử lý và điều khiển app → "
        "Green SM thực thi. Green SM là nguồn sự thật duy nhất cho giá cước, booking, thanh toán và trạng thái chuyến."
    )

    _heading(doc, "2. Kiến Trúc Hệ Thống", level=2)
    _para(doc, "Kiến trúc tổng quan:")
    _para(doc, "Green SM Mobile App (iOS / Android)")
    _para(doc, "  └── Voice Assistant UI ← OlaSM Mobile SDK")
    _para(doc, "        └── OlaSM Voice Gateway (FastAPI backend)")
    _para(doc, "              ├── LiveKit WebRTC Session")
    _para(doc, "              ├── STT (Deepgram Nova-3) → LLM (OpenAI) → TTS (Gemini Kore)")
    _para(doc, "              ├── Dialog State Machine")
    _para(doc, "              ├── AppContext Validator")
    _para(doc, "              ├── AppAction Dispatcher (typed, allowlisted)")
    _para(doc, "              └── Guardrails 3 lớp")
    _para(doc, "                    └── Green SM Official APIs")

    _heading(doc, "3. AppContext ↔ AppAction Protocol", level=2)
    _para(doc,
        "Mỗi lượt hội thoại, mobile host gửi AppContext (bounded, validated) mô tả màn hình hiện tại. "
        "OlaSM xử lý và trả về danh sách AppAction typed. Mobile thực thi và gửi lại AppActionResult."
    )

    _heading(doc, "3.1 AppContext — Dữ liệu mobile host gửi vào", level=3)
    _table(doc,
        ["Field", "Type", "Mô tả"],
        [
            ["schema_version", "Literal['1']", "Phiên bản schema"],
            ["app", "Literal['GREEN_SM']", "Định danh app host"],
            ["screen", "AppScreen", "Màn hình hiện tại"],
            ["service", "str | None", "Dịch vụ đang chọn (Car, Bike...)"],
            ["platform", "IOS | ANDROID | UNKNOWN", "Nền tảng mobile"],
            ["foreground", "bool", "App có đang foreground không"],
            ["available_actions", "list[str]", "Danh sách action host cho phép"],
            ["screen_summary", "str | None", "Tóm tắt ngữ nghĩa màn hình"],
            ["screen_state", "dict", "Dữ liệu hiện tại (không có secret)"],
            ["last_action_result", "AppActionResult | None", "Kết quả action lượt trước"],
        ]
    )

    _heading(doc, "3.2 AppAction — Lệnh OlaSM trả về", level=3)
    _table(doc,
        ["Kind", "Mô tả", "Risk", "Cần confirm?"],
        [
            ["NAVIGATE", "Chuyển đến màn hình Green SM", "SAFE_NAVIGATION", "Không"],
            ["GO_BACK", "Quay lại màn hình trước", "SAFE_NAVIGATION", "Không"],
            ["READ_SCREEN", "Đọc nội dung màn hình", "SAFE_NAVIGATION", "Không"],
            ["SET_FIELD", "Điền trường được quảng bá bởi host", "USER_CONFIRMATION", "Không"],
            ["SELECT_OPTION", "Chọn option trong danh sách", "USER_CONFIRMATION", "Không"],
            ["SUBMIT", "Gửi action có side effect (đặt xe, hủy...)", "APP_CONFIRMATION", "Bắt buộc"],
            ["OPEN_HELP", "Mở màn hình hỗ trợ Green SM", "SAFE_NAVIGATION", "Không"],
            ["REQUEST_OPEN_APP", "Yêu cầu OS mở lại Green SM", "OS_MANAGED", "Không"],
            ["END_ASSISTANT", "Dừng voice, giải phóng microphone", "SAFE_NAVIGATION", "Không"],
        ]
    )

    _heading(doc, "4. Guardrails 3 Lớp", level=2)

    _heading(doc, "4.1 Input Rail", level=3)
    _para(doc, "- Phát hiện và chặn 100% prompt injection")
    _para(doc, "- Kiểm tra độ tin cậy STT (stt_confidence)")
    _para(doc, "- Giới hạn độ dài transcript và loại bỏ PII")

    _heading(doc, "4.2 App Action Rail (Mới)", level=3)
    _para(doc, "- Validate AppContext từ mobile host")
    _para(doc, "- Kiểm tra capability_allowed: action phải nằm trong available_actions")
    _para(doc, "- Từ chối action khi app không foreground (ngoại trừ REQUEST_OPEN_APP)")
    _para(doc, "- Bắt buộc confirmation_required và risk ≠ SAFE_NAVIGATION cho SUBMIT")
    _para(doc, "- Kiểm tra unique action_id trong mỗi lượt")

    _heading(doc, "4.3 Output Rail", level=3)
    _para(doc, "- Không cho phép side effect mà không có xác nhận tường minh")
    _para(doc, "- Không đưa thông tin thẻ, OTP, password vào LLM")
    _para(doc, "- Session control: ENDED phải kèm END_ASSISTANT action")

    _heading(doc, "5. Voice Pipeline Kỹ Thuật", level=2)
    _table(doc,
        ["Thành phần", "Công nghệ", "Chỉ số"],
        [
            ["Transport", "LiveKit WebRTC", "Real-time, bidirectional"],
            ["VAD", "Silero VAD", "Ngắt câu 220ms tự nhiên"],
            ["STT", "Deepgram Nova-3", "Tiếng Việt, streaming"],
            ["LLM", "OpenAI (GPT-4 class)", "Tool calling, typed output"],
            ["TTS", "Gemini Kore / Chirp 3 HD fallback", "TTFA P95 = 1.41s"],
            ["State Sync", "LiveKit data channel", "Topic: olasm.app_control.v1"],
        ]
    )

    _heading(doc, "6. Bảo Mật và Quyền Riêng Tư", level=2)
    _para(doc, "- Microphone chỉ bật khi người dùng bấm nút (push-to-talk trong MVP)")
    _para(doc, "- Không nghe nền, không wake word trong MVP")
    _para(doc, "- Raw audio không lưu mặc định")
    _para(doc, "- Transcript được ẩn danh và giới hạn thời gian lưu")
    _para(doc, "- Thông tin thẻ/OTP không bao giờ đi vào LLM")
    _para(doc, "- Screen_state không được chứa secret keys (validated tại AppContext)")
    _para(doc, "- Tuân thủ chính sách quyền riêng tư của Green SM (greensm.com/terms-policies/privacy-notice)")

    _heading(doc, "7. Trạng Thái Codebase", level=2)
    _table(doc,
        ["Thành phần", "File", "Trạng thái"],
        [
            ["Typed AppAction contract", "src/agents/contracts/app_control.py", "IMPLEMENTED"],
            ["AppContext/AppAction trong schemas", "src/agents/contracts/schemas.py", "IMPLEMENTED"],
            ["Mobile instructions", "src/agents/core/mobile_instructions.py", "IMPLEMENTED"],
            ["App-control guardrails", "src/agents/core/guardrails.py", "IMPLEMENTED"],
            ["8 app-control function tools", "src/voice_agent/agent.py", "IMPLEMENTED"],
            ["LiveKit app-control state sync", "src/voice_agent/state_sync.py", "IMPLEMENTED"],
            ["Session schemas (MOBILE_VOICE)", "src/backend/schemas/session.py", "IMPLEMENTED"],
            ["Frontend TS types", "src/frontend/src/features/livekit/contracts.ts", "IMPLEMENTED"],
            ["Green SM API adapter", "src/integrations/gsm_adapter.py", "EXTERNAL_BLOCKED"],
            ["Mobile SDK", "mobile/ (tbd)", "EXTERNAL_BLOCKED"],
        ]
    )

    _heading(doc, "8. Điều Kiện Tiên Quyết (EXTERNAL_BLOCKED)", level=2)
    _para(doc, "Cần làm việc với team Green SM để có:")
    _para(doc, "1. API xác thực người dùng")
    _para(doc, "2. API Place / Address lookup")
    _para(doc, "3. API Quote / Pricing")
    _para(doc, "4. API Booking (tạo, hủy)")
    _para(doc, "5. API Trip Status / ETA / Driver info")
    _para(doc, "6. API Payment / Promotion")
    _para(doc, "7. API Support / Handoff")
    _para(doc, "8. Sandbox, test account và webhook")
    _para(doc, "9. Xác nhận công nghệ app mobile: native iOS/Android, Flutter hay React Native", bold=True)

    _heading(doc, "9. Lộ Trình", level=2)
    _table(doc,
        ["Phase", "Mục tiêu", "Điều kiện", "Trạng thái"],
        [
            ["Phase 0", "Chốt API/SDK với Green SM", "Business agreement", "EXTERNAL_BLOCKED"],
            ["Phase 1 MVP", "Voice-to-book Green SM Car: nói → resolve → quote → confirm → booking → tracking", "Green SM APIs", "IN_PROGRESS"],
            ["Phase 2", "Trợ lý trong chuyến: tracking, hủy, handoff", "Phase 1 stable", "ROADMAP"],
            ["Phase 3", "Mở rộng: Bike, Express, Food, đặt hộ", "Phase 2 stable", "ROADMAP"],
        ]
    )

    out = ROOT / "BaoCao_KyThuat_POC_Nhom4_OlaSM_updated.docx"
    doc.save(str(out))
    print(f"✓ {out.name}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Đang tạo các file báo cáo DOCX...")
    make_y_tuong()
    make_tom_tat()
    make_ky_thuat_updated()
    print("\nHoàn tất. Các file đã được ghi vào thư mục gốc của project.")
    print("Lưu ý: BaoCao_KyThuat_POC_Nhom4_OlaSM.docx và các file PDF")
    print("cần render lại thủ công hoặc dùng LibreOffice nếu muốn xuất PDF.")
