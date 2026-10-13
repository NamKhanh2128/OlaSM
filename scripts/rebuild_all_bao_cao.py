# -*- coding: utf-8 -*-
"""
Tạo lại toàn bộ bộ báo cáo OlaSM Voice Core theo hướng mới:
Voice assistant layer tích hợp vào app mobile Green SM của VinGroup.

Phong cách: học thuật-kỹ thuật Việt Nam, giống báo cáo gốc BaoCao_KyThuat.
Chạy: python scripts/rebuild_all_bao_cao.py
"""

from __future__ import annotations
import io
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────────────────────────
# Hằng số chung
# ─────────────────────────────────────────────────────────────────
FONT_BODY = "Times New Roman"
SIZE_BODY = Pt(12)
SIZE_H1   = Pt(13)   # heading chính (bold, same font)
SIZE_H2   = Pt(12)   # subheading (bold inline)
SIZE_FORMULA = Pt(11)
SIZE_SMALL   = Pt(10.5)

PROGRAM   = "VRIC × GSM Smart City — Nhóm 4: Mobility Assistant"
MEMBERS   = "Nguyễn Đức Nam Khánh (MSSV: 2A202601103) & Nguyễn Thị Phương (MSSV: 2A202601315)"
ADVISORS  = "TS. Lê Duy Dũng (VinUniversity) & Anh Lê Yên Thanh (Chuyên gia công nghệ VRIC × GSM)"
DATE_REPORT = "Thứ Hai, ngày 13/10/2026"
DATE_NOTE   = "(Cập nhật sau Pivot — Tuần 4, Phase 3: 14/09/2026 – 25/10/2026)"
GITHUB    = "https://github.com/NamKhanh2128/OlaSM"

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _new_doc() -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width  = Cm(21)
    sec.page_height = Cm(29.7)
    sec.top_margin    = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin   = Cm(3.0)
    sec.right_margin  = Cm(2.0)
    # Normal style
    n = doc.styles["Normal"]
    n.font.name = FONT_BODY
    n.font.size = SIZE_BODY
    n.paragraph_format.space_after = Pt(4)
    n.paragraph_format.line_spacing = Pt(18)
    return doc


def _p(doc: Document,
       text: str = "",
       bold: bool = False,
       italic: bool = False,
       size: Pt | None = None,
       align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY,
       space_before: Pt | None = None,
       space_after: Pt | None = None) -> None:
    para = doc.add_paragraph()
    para.alignment = align
    if space_before is not None:
        para.paragraph_format.space_before = space_before
    if space_after is not None:
        para.paragraph_format.space_after = space_after
    if text:
        run = para.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.name = FONT_BODY
        run.font.size = size or SIZE_BODY
    return para


def _p_mixed(doc: Document,
             parts: list[tuple[str, bool, bool, Pt | None]],
             align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY,
             space_before: Pt | None = None,
             space_after:  Pt | None = None) -> None:
    """parts = list of (text, bold, italic, size|None)"""
    para = doc.add_paragraph()
    para.alignment = align
    if space_before is not None:
        para.paragraph_format.space_before = space_before
    if space_after is not None:
        para.paragraph_format.space_after = space_after
    for text, bold, italic, size in parts:
        run = para.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.name = FONT_BODY
        run.font.size = size or SIZE_BODY
    return para


def _h(doc: Document, text: str, level: int = 1) -> None:
    size = SIZE_H1 if level == 1 else SIZE_BODY
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.space_before = Pt(10 if level == 1 else 6)
    para.paragraph_format.space_after  = Pt(4)
    run = para.add_run(text)
    run.bold = True
    run.font.name = FONT_BODY
    run.font.size = size


def _formula(doc: Document, text: str) -> None:
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(4)
    para.paragraph_format.space_after  = Pt(4)
    run = para.add_run(text)
    run.bold = True
    run.font.name = FONT_BODY
    run.font.size = SIZE_FORMULA


def _formula_note(doc: Document, text: str) -> None:
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(text)
    run.font.name = FONT_BODY
    run.font.size = SIZE_SMALL
    run.italic = True


def _table(doc: Document,
           headers: list[str],
           rows:    list[list[str]],
           col_widths: list[Cm] | None = None) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    # header row
    hcells = table.rows[0].cells
    for i, h in enumerate(headers):
        hcells[i].text = h
        para = hcells[i].paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.name = FONT_BODY
            run.font.size = SIZE_SMALL
    # data rows
    for ri, row in enumerate(rows):
        dcells = table.rows[ri + 1].cells
        for ci, val in enumerate(row):
            dcells[ci].text = val
            para = dcells[ci].paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                run.font.name = FONT_BODY
                run.font.size = SIZE_SMALL
    # column widths
    if col_widths:
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                if ci < len(col_widths):
                    cell.width = col_widths[ci]


def _divider(doc: Document) -> None:
    _p(doc, "─" * 68, size=Pt(8), align=WD_ALIGN_PARAGRAPH.CENTER)


# ─────────────────────────────────────────────────────────────────
# 1. BaoCao_YTuong_Nhom4_OlaSM.docx
#    Báo cáo ý tưởng — định nghĩa vấn đề, giải pháp, hướng phát triển
# ─────────────────────────────────────────────────────────────────

def make_y_tuong() -> None:
    doc = _new_doc()

    # ── Tiêu đề ──
    _p(doc, "BÁO CÁO Ý TƯỞNG — DỰ ÁN OlaSM VOICE CORE",
       bold=True, size=Pt(14), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _p(doc, "Trợ lý Giọng nói Điều khiển Toàn bộ App Mobile Green SM của VinGroup",
       bold=False, size=Pt(12), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _divider(doc)
    _p(doc, f"Chương trình: {PROGRAM}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Thành viên nhóm: {MEMBERS}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Hội đồng cố vấn & Ban giám khảo: {ADVISORS}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Thời điểm báo cáo: {DATE_REPORT} {DATE_NOTE}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Mã nguồn: {GITHUB}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _divider(doc)

    # ── 1. Bối cảnh và vấn đề ──
    _h(doc, "1. Bối cảnh và Vấn đề cần giải quyết")

    _p(doc, "1.1. Tổng quan về Green SM và hệ sinh thái dịch vụ", bold=True, size=SIZE_H2)
    _p(doc,
       "Green SM (Green and Smart Mobility) là ứng dụng gọi xe điện của VinGroup, "
       "vận hành bởi GSM Green and Smart Mobility JSC. Tính đến thời điểm báo cáo, "
       "ứng dụng cung cấp một hệ sinh thái dịch vụ vận tải toàn diện, bao gồm: "
       "Green SM Car (xe 4–7 chỗ), Green SM Mini, Green SM Premium, Green SM Limo, "
       "Green SM Airport, Green SM Tour, Green SM Liên Tỉnh, Green SM Bike, "
       "Green SM Food, Green SM Express, và Green SM Van. Mỗi dịch vụ được tích hợp "
       "hoàn chỉnh với hệ thống định vị, báo giá thời gian thực, theo dõi chuyến, "
       "điều phối tài xế, thanh toán đa kênh, khuyến mãi cá nhân hóa và hỗ trợ khách hàng. "
       "Nền tảng kỹ thuật của Green SM do VinGroup sở hữu và vận hành toàn bộ.")

    _p(doc, "1.2. Điểm nghẽn tiếp cận — Rào cản giao diện màn hình", bold=True, size=SIZE_H2)
    _p(doc,
       "Dù có hệ sinh thái dịch vụ phong phú, Green SM đang phải đối mặt với một rào cản "
       "cơ bản: toàn bộ luồng thao tác yêu cầu người dùng tương tác qua màn hình cảm ứng. "
       "Điều này tạo ra ba nhóm vấn đề rõ ràng trong thực tế vận hành:")

    _p_mixed(doc, [
        ("• Người dùng lớn tuổi và ít quen công nghệ: ", True, False, None),
        ("Đây là nhóm khách hàng truyền thống có thói quen gọi điện để đặt xe. "
         "Việc điều hướng qua nhiều bước thao tác trong app — chọn dịch vụ, nhập địa chỉ, "
         "chọn thanh toán, xác nhận — đặt ra ngưỡng kỹ năng số quá cao so với khả năng của nhóm này. "
         "Kết quả là họ bỏ cuộc, nhờ người thân hoặc quay lại gọi hotline, dẫn đến chi phí vận hành "
         "tổng đài tăng và tỷ lệ chuyển đổi trực tuyến thấp.", False, False, None),
    ])

    _p_mixed(doc, [
        ("• Người dùng bận tay trong bối cảnh di chuyển: ", True, False, None),
        ("Hành khách đang mang hành lý, bế trẻ nhỏ, đứng tại điểm trung chuyển hoặc trong "
         "môi trường có tín hiệu yếu không thể thao tác màn hình thuận tiện. "
         "Đây là tình huống xảy ra thường xuyên tại sân bay, bến xe và các trung tâm thương mại "
         "— những địa điểm có lưu lượng đặt xe cao nhất của Green SM.", False, False, None),
    ])

    _p_mixed(doc, [
        ("• Người dùng có nhu cầu tiếp cận đặc biệt: ", True, False, None),
        ("Người khiếm thị, người có vấn đề vận động tinh hoặc người dùng gặp khó khăn "
         "khi đọc văn bản nhỏ trên màn hình di động là nhóm hiện không có kênh thay thế "
         "hiệu quả trong hệ sinh thái Green SM.", False, False, None),
    ])

    _p(doc, "1.3. Phát biểu bài toán", bold=True, size=SIZE_H2)
    _p(doc,
       "Làm thế nào để người dùng Green SM có thể thực hiện toàn bộ chu trình tương tác "
       "với ứng dụng — từ mở màn hình, chọn dịch vụ, nhập điểm đến, xem giá, áp dụng "
       "khuyến mãi, xác nhận đặt xe, theo dõi chuyến, đến yêu cầu hỗ trợ — chỉ bằng "
       "ngôn ngữ nói tiếng Việt tự nhiên, mà không yêu cầu thao tác màn hình ở bất kỳ "
       "bước nào trong luồng chính?")

    # ── 2. Đề xuất giải pháp ──
    _h(doc, "2. Đề xuất Giải pháp — OlaSM Voice Core")

    _p(doc, "2.1. Định vị sản phẩm", bold=True, size=SIZE_H2)
    _p(doc,
       "OlaSM Voice Core không phải là một ứng dụng đặt xe độc lập, không phải một "
       "chatbot web riêng biệt, và không phải một hệ thống thay thế Green SM. "
       "OlaSM Voice Core là một lớp trợ lý giọng nói (voice assistant layer) "
       "tích hợp trực tiếp bên trong ứng dụng mobile Green SM, hoạt động như một "
       "cơ chế điều khiển bổ sung song song với giao diện màn hình hiện có.")
    _p(doc,
       "Người dùng mở Green SM như bình thường, bấm nút microphone được tích hợp "
       "vào giao diện app, nói yêu cầu bằng tiếng Việt tự nhiên, và OlaSM Voice Core "
       "dịch ngôn ngữ nói thành các lệnh điều khiển có cấu trúc (typed actions) "
       "để Green SM thực thi. Green SM vẫn là nền tảng gốc — nguồn sự thật duy nhất "
       "cho toàn bộ dữ liệu giá, tài xế, booking, thanh toán và trạng thái chuyến.")

    _p(doc, "2.2. Nguyên tắc kiến trúc cốt lõi", bold=True, size=SIZE_H2)

    _p_mixed(doc, [
        ("Nguyên tắc 1 — Green SM là nguồn sự thật duy nhất: ", True, False, None),
        ("OlaSM không duy trì bất kỳ database nghiệp vụ nào song song với Green SM. "
         "Không có bản sao giá, không có danh sách tài xế nội bộ, không có logic "
         "tính giá riêng. Tất cả dữ liệu được truy vấn qua API chính thức của Green SM "
         "mỗi khi người dùng cần, đảm bảo tính nhất quán tuyệt đối.", False, False, None),
    ])

    _p_mixed(doc, [
        ("Nguyên tắc 2 — Typed Action Contract: ", True, False, None),
        ("Model ngôn ngữ tuyệt đối không được phép tự động thực thi thao tác ngoài "
         "danh sách lệnh được định nghĩa sẵn (allowlist). Mỗi lượt hội thoại, "
         "OlaSM chỉ được trả về một danh sách AppAction có kiểu dữ liệu tường minh "
         "để mobile host thực thi. Không emit code, không emit URL, không tự điều hướng "
         "ngoài phạm vi được Green SM mobile host quảng bá (advertise).", False, False, None),
    ])

    _p_mixed(doc, [
        ("Nguyên tắc 3 — Xác nhận tường minh trước side effect: ", True, False, None),
        ("Mọi hành động có ảnh hưởng thực đến dữ liệu hoặc tài chính — đặt xe, hủy chuyến, "
         "thanh toán, xóa tài khoản — đều phải trải qua bước xác nhận rõ ràng của người dùng "
         "thông qua giao diện Green SM, không phải qua giọng nói đơn thuần. "
         "Hệ thống biometric của thiết bị được kích hoạt cho các thao tác nhạy cảm nhất.", False, False, None),
    ])

    _p_mixed(doc, [
        ("Nguyên tắc 4 — Microphone theo yêu cầu, không nghe nền: ", True, False, None),
        ("Trong phiên bản MVP, microphone chỉ được bật khi người dùng chủ động bấm nút "
         "push-to-talk. Không có cơ chế wake word hay nghe nền liên tục. "
         "Đây là quyết định thiết kế xuất phát từ yêu cầu quyền riêng tư trong chính sách "
         "dữ liệu của Green SM và quy định PDPA/GDPR áp dụng tại Việt Nam.", False, False, None),
    ])

    _p(doc, "2.3. Luồng hoạt động end-to-end", bold=True, size=SIZE_H2)
    _p(doc, "Luồng tương tác đầy đủ cho kịch bản đặt xe (Happy Path):")

    for step in [
        ("Bước 1", "Người dùng mở ứng dụng Green SM, điều hướng tự nhiên đến màn hình đặt xe "
                   "hoặc nói 'Đặt xe' ngay từ màn hình chính."),
        ("Bước 2", "Người dùng bấm và giữ nút microphone (push-to-talk). "
                   "OlaSM Voice Core nhận luồng âm thanh qua WebRTC LiveKit."),
        ("Bước 3", "Silero VAD phát hiện điểm dừng tự nhiên (220ms silence). "
                   "Deepgram Nova-3 chuyển đổi tiếng Việt thành văn bản với độ trễ P95 = 1.41s."),
        ("Bước 4", "LLM Agent phân tích intent, trích xuất điểm đến, loại dịch vụ, "
                   "phương thức thanh toán. Nếu thông tin chưa đủ, Agent hỏi lại "
                   "bằng giọng nói (TTS)."),
        ("Bước 5", "OlaSM gửi AppAction NAVIGATE → CAR_BOOKING đến mobile host. "
                   "Mobile host chuyển màn hình, điền điểm đến vào form (SET_FIELD), "
                   "gọi Green SM Place API để resolve địa chỉ."),
        ("Bước 6", "Green SM trả về danh sách điểm đến gợi ý, giá cước và ETA. "
                   "OlaSM đọc kết quả bằng TTS: 'Từ vị trí của bạn đến Sân bay Nội Bài, "
                   "khoảng 35 phút, giá 280.000 đồng. Bạn có muốn xác nhận không?'"),
        ("Bước 7", "Người dùng xác nhận bằng giọng nói hoặc bấm nút. "
                   "OlaSM gửi AppAction SUBMIT → confirm_booking (risk = APP_CONFIRMATION). "
                   "Mobile host hiển thị dialog xác nhận cuối cùng."),
        ("Bước 8", "Người dùng xác nhận trên giao diện Green SM. "
                   "Green SM tạo booking, mở màn hình tracking. "
                   "OlaSM đọc: 'Đã đặt xe thành công. Tài xế sẽ đến trong khoảng 5 phút.'"),
    ]:
        _p_mixed(doc, [
            (f"• {step[0]}: ", True, False, None),
            (step[1], False, False, None),
        ])

    # ── 3. Phạm vi MVP ──
    _h(doc, "3. Phạm vi MVP (Phase 1) và Lộ trình mở rộng")

    _p(doc, "3.1. Phạm vi MVP — Green SM Car & Mini", bold=True, size=SIZE_H2)
    _p(doc,
       "MVP tập trung vào luồng đặt xe một điểm đến cho Green SM Car và Green SM Mini, "
       "là hai dịch vụ có lưu lượng cao nhất và luồng thao tác đủ đơn giản để chứng minh "
       "khái niệm trong điều kiện POC. Phạm vi cụ thể:")

    _table(doc,
        ["Hạng mục", "Mô tả chi tiết trong MVP"],
        [
            ["Kênh tương tác", "Push-to-talk (bấm để nói). Tiếng Việt. Chưa hỗ trợ wake word hay nghe liên tục."],
            ["Dịch vụ hỗ trợ", "Green SM Car và Green SM Mini. Các dịch vụ khác đưa vào Phase 2–3."],
            ["Điểm đón", "Lấy tự động từ GPS hiện tại của app. Không cần người dùng nói điểm đón."],
            ["Điểm đến", "Nhận qua giọng nói tự nhiên. Resolve qua Green SM Place API. Hỏi lại khi mơ hồ."],
            ["Loại xe", "Người dùng chọn bằng giọng nói từ danh sách Green SM trả về."],
            ["Thanh toán", "Chọn từ danh sách phương thức thanh toán Green SM trả về. Không xử lý thẻ qua voice."],
            ["Khuyến mãi", "Áp từ danh sách ưu đãi Green SM trả về. Không tự tính giá."],
            ["Xác nhận", "Người dùng xác nhận bằng giọng ('Có') hoặc bấm nút trên giao diện."],
            ["Fallback", "Chuyển sang thao tác tay hoặc text bất kỳ lúc nào, không mất trạng thái."],
            ["'Đóng app'", "Dừng voice + giải phóng microphone. iOS/Android không hỗ trợ force-quit từ app."],
        ],
        col_widths=[Cm(4.5), Cm(11)]
    )

    _p(doc, "3.2. Những gì OlaSM Voice Core không làm trong MVP", bold=True, size=SIZE_H2)
    _p(doc,
       "Nhằm đảm bảo tính an toàn, tránh hiểu nhầm về phạm vi và duy trì niềm tin của người dùng, "
       "nhóm xác định rõ các hành vi ngoài phạm vi:")
    for item in [
        "Không tự tạo booking mà không có xác nhận tường minh từ người dùng qua giao diện Green SM.",
        "Không tự tính giá hay tạo mock ETA — tất cả phải lấy từ Green SM API thật.",
        "Không nhận thông tin số thẻ, OTP, mật khẩu qua giọng nói và truyền vào LLM.",
        "Không reverse-engineer hay tự động hóa thao tác giao diện Green SM ngoài SDK/API chính thức.",
        "Không duy trì cơ sở dữ liệu đặt xe riêng song song với Green SM.",
        "Không xây dựng tính năng định vị bản đồ hay tính toán lộ trình độc lập — chức năng này thuộc Green SM.",
        "Không tự phán đoán địa điểm mơ hồ — khi không chắc chắn, luôn hỏi lại người dùng.",
    ]:
        _p_mixed(doc, [("• ", True, False, None), (item, False, False, None)])

    _p(doc, "3.3. Lộ trình phát triển sau MVP", bold=True, size=SIZE_H2)
    _table(doc,
        ["Phase", "Mục tiêu trọng tâm", "Điều kiện tiên quyết", "Trạng thái"],
        [
            ["Phase 0",
             "Chốt hợp đồng API/SDK chính thức với team Green SM. Xác nhận công nghệ app mobile (native iOS/Android, Flutter hay React Native).",
             "Business agreement với GSM",
             "EXTERNAL_BLOCKED"],
            ["Phase 1 — MVP",
             "Luồng voice-to-book hoàn chỉnh cho Green SM Car: nói điểm đến → resolve địa chỉ → lấy quote Green SM → đọc lại → xác nhận → tạo booking → mở tracking.",
             "Green SM Place, Quote, Booking APIs + Mobile SDK",
             "IN_PROGRESS"],
            ["Phase 2",
             "Trợ lý trong chuyến đi: hỏi vị trí tài xế, ETA, đọc thông tin xe, yêu cầu hủy (biometric), chuyển tổng đài kèm context.",
             "Phase 1 stable + Trip/Driver API",
             "ROADMAP"],
            ["Phase 3",
             "Mở rộng sang Green SM Bike, Express, đặt hộ (với kiểm soát danh tính riêng), Green SM Food, Liên Tỉnh, đa điểm.",
             "Phase 2 stable + từng service API",
             "ROADMAP"],
        ],
        col_widths=[Cm(2.2), Cm(7), Cm(4), Cm(2.5)]
    )

    # ── 4. Typed Action Contract ──
    _h(doc, "4. Typed Action Contract — Giao thức điều khiển App")

    _p(doc,
       "Mỗi lượt hội thoại, mobile host Green SM gửi một đối tượng AppContext mô tả "
       "trạng thái hiện tại của màn hình (màn hình đang hiển thị, danh sách thao tác được "
       "phép trong lượt này, tóm tắt ngữ nghĩa màn hình). OlaSM trả về một danh sách "
       "AppAction có kiểu dữ liệu tường minh và thời gian hiệu lực (TTL). "
       "Mobile host thực thi, sau đó gửi lại AppActionResult để agent biết kết quả.")

    _table(doc,
        ["Action Kind", "Mô tả hành vi", "Risk Level", "Cần xác nhận"],
        [
            ["NAVIGATE", "Điều hướng đến một màn hình Green SM cụ thể (đã được host quảng bá).", "SAFE_NAVIGATION", "Không"],
            ["GO_BACK", "Quay lại màn hình trước trong navigation stack.", "SAFE_NAVIGATION", "Không"],
            ["READ_SCREEN", "Đọc tóm tắt nội dung màn hình hiện tại do host cung cấp.", "SAFE_NAVIGATION", "Không"],
            ["SET_FIELD", "Điền giá trị vào một trường form được host quảng bá rõ ràng.", "USER_CONFIRMATION", "Không (tự động)"],
            ["SELECT_OPTION", "Chọn một option trong danh sách được host quảng bá.", "USER_CONFIRMATION", "Không (tự động)"],
            ["SUBMIT", "Gửi thao tác có side effect (đặt xe, hủy, xác nhận thanh toán). Bắt buộc qua dialog xác nhận Green SM.", "APP_CONFIRMATION", "Bắt buộc qua UI"],
            ["OPEN_HELP", "Mở màn hình hỗ trợ hoặc tổng đài Green SM.", "SAFE_NAVIGATION", "Không"],
            ["REQUEST_OPEN_APP", "Yêu cầu hệ điều hành đưa app Green SM lên foreground.", "OS_MANAGED", "Tùy OS"],
            ["END_ASSISTANT", "Dừng phiên voice, giải phóng microphone. Không đóng app.", "SAFE_NAVIGATION", "Không"],
        ],
        col_widths=[Cm(3.3), Cm(7), Cm(3), Cm(2.2)]
    )

    _p(doc,
       "Guardrail kiểm tra: mỗi AppAction trong danh sách trả về đều phải "
       "nằm trong available_actions mà mobile host quảng bá trong AppContext lượt đó. "
       "Bất kỳ action nào không được host quảng bá sẽ bị từ chối bởi lớp guardrail "
       "phía backend trước khi trả về client, bất kể model có yêu cầu thực thi hay không.")

    # ── 5. Quyền riêng tư ──
    _h(doc, "5. Quyền Riêng tư và An toàn Dữ liệu")

    _p(doc,
       "Green SM đã công bố chính sách xử lý dữ liệu tại "
       "greensm.com/terms-policies/privacy-notice, bao gồm dữ liệu vị trí, "
       "thông tin liên hệ, lịch sử sử dụng và dữ liệu liên quan đến AI. "
       "OlaSM Voice Core tuân thủ toàn bộ chính sách này và bổ sung thêm "
       "các ràng buộc kỹ thuật sau:")

    for req in [
        "Microphone chỉ được bật khi người dùng thực hiện thao tác push-to-talk chủ động. Không có cơ chế nghe nền hay wake word trong MVP.",
        "Raw audio không được lưu trữ theo mặc định. Transcript được ẩn danh hóa và có thời hạn lưu giới hạn.",
        "Thông tin thẻ thanh toán, mã OTP, mật khẩu không được truyền vào pipeline LLM dưới bất kỳ hình thức nào.",
        "Trường screen_state trong AppContext không được chứa secret keys hoặc thông tin xác thực — được validate phía backend.",
        "Mọi hành động có side effect đều yêu cầu xác nhận tường minh qua giao diện Green SM, không qua giọng nói đơn thuần.",
        "Người dùng có thể ngắt phiên voice và chuyển sang thao tác thủ công bất kỳ lúc nào mà không mất trạng thái.",
    ]:
        _p_mixed(doc, [("• ", True, False, None), (req, False, False, None)])

    # ── 6. Phân công ──
    _h(doc, "6. Phân công Nhóm và Đóng góp")

    _table(doc,
        ["Thành viên", "Vai trò", "Phần việc chính"],
        [
            ["Nguyễn Đức Nam Khánh\nMSSV: 2A202601103",
             "Trưởng nhóm kỹ thuật\nHạ tầng & Backend",
             "• Kiến trúc hệ thống tổng thể: AppContext/AppAction contract\n"
             "• Voice pipeline: LiveKit WebRTC, VietnameseAudioChunker\n"
             "• Typed action contract và guardrail validation\n"
             "• 8 app-control function tools trong voice agent\n"
             "• LiveKit data channel state sync (olasm.app_control.v1)"],
            ["Nguyễn Thị Phương\nMSSV: 2A202601315",
             "Kỹ sư AI & Nghiệp vụ\nDialog & Product",
             "• Dialog state machine và intent extraction cho luồng Green SM\n"
             "• Mobile system instructions và LLM prompt engineering\n"
             "• Thiết kế luồng người dùng và kịch bản edge case\n"
             "• Tài liệu sản phẩm và báo cáo kỹ thuật\n"
             "• Eval cases cho voice-to-book workflow"],
        ],
        col_widths=[Cm(3.8), Cm(4), Cm(7.7)]
    )

    # ── 7. Kết luận ──
    _h(doc, "7. Kết luận")

    _p(doc,
       "Bài toán OlaSM giải quyết không phải là tạo ra một ứng dụng đặt xe mới — "
       "Green SM đã làm tốt việc đó. Bài toán là loại bỏ rào cản giao diện màn hình "
       "cho những người dùng không thể hoặc không muốn thao tác trực tiếp. "
       "Giải pháp đúng đắn là tích hợp sâu vào Green SM, không tạo ra song song cạnh tranh.")

    _p(doc,
       "Việc tiếp cận thông qua typed action contract và AppContext protocol "
       "đảm bảo rằng ngay cả khi model ngôn ngữ mắc lỗi suy luận, "
       "hậu quả được giới hạn trong phạm vi action đã được host Green SM cho phép. "
       "Đây là thiết kế an toàn theo nguyên tắc least-privilege — "
       "không có đường tắt nào để model tự động thực thi ngoài guardrail.")

    _p(doc,
       "Để triển khai Phase 1, điều kiện cần và đủ duy nhất là "
       "có được API và SDK chính thức từ team Green SM. "
       "Toàn bộ kiến trúc kỹ thuật phía OlaSM đã sẵn sàng.")

    _divider(doc)
    _p(doc, "Đại diện nhóm báo cáo:", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, "Nguyễn Đức Nam Khánh — MSSV: 2A202601103 (Trưởng nhóm kỹ thuật)", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, "Nguyễn Thị Phương — MSSV: 2A202601315 (Kỹ sư AI & Nghiệp vụ)", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Nhóm dự án OlaSM — {PROGRAM}", align=WD_ALIGN_PARAGRAPH.LEFT)
    _p(doc, f"Ngày nộp: {DATE_REPORT}", align=WD_ALIGN_PARAGRAPH.LEFT)

    out = ROOT / "BaoCao_YTuong_Nhom4_OlaSM.docx"
    doc.save(str(out))
    print(f"[OK] {out.name}")


# ─────────────────────────────────────────────────────────────────
# 2. BaoCao_TomTat_POC_Nhom4_OlaSM.docx
#    Executive summary — tóm tắt toàn bộ POC cho hội đồng
# ─────────────────────────────────────────────────────────────────

def make_tom_tat() -> None:
    doc = _new_doc()

    _p(doc, "BÁO CÁO TÓM TẮT KỸ THUẬT POC",
       bold=True, size=Pt(14), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _p(doc, "Trợ lý Giọng nói Điều khiển Toàn bộ App Mobile Green SM — OlaSM Voice Core",
       bold=False, size=Pt(12), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _divider(doc)
    _p(doc, f"Chương trình: {PROGRAM}")
    _p(doc, f"Mã dự án: OlaSM Voice Core")
    _p(doc, f"Thời điểm báo cáo: {DATE_REPORT} {DATE_NOTE}")
    _p(doc, f"Nhóm thực hiện: {MEMBERS}")
    _p(doc, f"Hội đồng cố vấn & Ban giám khảo: {ADVISORS}")
    _p(doc, f"Mã nguồn: {GITHUB}")
    _divider(doc)

    _h(doc, "1. Khung Thời Gian và Trạng Thái Tiến Độ Phase 3")

    _p(doc, "1.1. Tổng quan tiến độ", bold=True, size=SIZE_H2)
    _p(doc,
       "Giai đoạn Phase 3 của chương trình VRIC × GSM Smart City có thời lượng "
       "6 tuần, từ ngày 14/09/2026 đến ngày 25/10/2026. Tính đến thời điểm báo cáo "
       "(Tuần 4, ngày 13/10/2026), nhóm đã đi qua 2 giai đoạn rõ ràng:")

    _p_mixed(doc, [
        ("• Tuần 1–3 (Nửa đầu Phase 3 — ĐÃ HOÀN TẤT): ", True, False, None),
        ("Xây dựng toàn bộ hạ tầng voice pipeline: LiveKit WebRTC hai chiều, "
         "Silero VAD, Deepgram Nova-3 STT, LLM agent với state machine, "
         "TTS Gemini Flash Kore với Chirp 3 HD fallback, guardrails 3 lớp, "
         "và VietnameseAudioChunker đạt TTFA P95 = 1.41s.", False, False, None),
    ])

    _p_mixed(doc, [
        ("• Tuần 4 (Pivot — ĐANG THỰC HIỆN): ", True, False, None),
        ("Sau khi nghiên cứu toàn diện hệ sinh thái Green SM và nhận ra rằng "
         "xây app đặt xe độc lập là sai hướng, nhóm đã thực hiện pivot toàn bộ sản phẩm. "
         "OlaSM Voice Core chuyển thành voice assistant layer tích hợp vào Green SM mobile. "
         "Typed AppAction contract, AppContext protocol, guardrail mở rộng và "
         "8 app-control function tools đã được triển khai hoàn chỉnh.", False, False, None),
    ])

    _p_mixed(doc, [
        ("• Tuần 5–6 và Hậu Phase 3 (KẾ HOẠCH): ", True, False, None),
        ("Kết nối Green SM APIs chính thức (hiện EXTERNAL_BLOCKED do chưa có hợp đồng API), "
         "xây dựng mobile SDK adapter phù hợp với công nghệ app Green SM, "
         "chạy end-to-end integration test, và demo trên test build Green SM.", False, False, None),
    ])

    _p(doc, "1.2. Lý do Pivot", bold=True, size=SIZE_H2)
    _p(doc,
       "Sau 3 tuần đầu, nhóm kết luận rằng xây dựng một ứng dụng gọi xe độc lập cạnh Green SM "
       "không mang lại giá trị và tạo ra sự cạnh tranh không cần thiết với nền tảng đã hoàn chỉnh. "
       "Người dùng Green SM không cần thêm một app khác — họ cần Green SM dễ dùng hơn. "
       "Giải pháp đúng là tích hợp voice vào Green SM, không phải thay thế nó. "
       "Toàn bộ hạ tầng kỹ thuật đã xây dựng trong 3 tuần đầu được giữ nguyên và tái sử dụng "
       "làm backend voice service cho kiến trúc mới.")

    _h(doc, "2. Định Vị Sản Phẩm Sau Pivot")

    _p(doc, "2.1. OlaSM Voice Core là gì?", bold=True, size=SIZE_H2)
    _p(doc,
       "OlaSM Voice Core là lớp trợ lý giọng nói tích hợp bên trong app mobile Green SM, "
       "cho phép người dùng điều khiển toàn bộ ứng dụng bằng tiếng Việt tự nhiên "
       "mà không cần chạm màn hình. Người dùng bấm nút microphone trong Green SM → "
       "nói yêu cầu → OlaSM hiểu intent và tạo typed action → Green SM thực thi → "
       "OlaSM đọc kết quả bằng giọng. Green SM là nguồn dữ liệu và thực thi duy nhất.")

    _p(doc, "2.2. Giá trị mang lại", bold=True, size=SIZE_H2)
    _table(doc,
        ["Nhóm người dùng", "Vấn đề hiện tại", "Giá trị OlaSM mang lại"],
        [
            ["Người lớn tuổi, quen gọi hotline",
             "Không dùng được app, phải nhờ người thân hoặc gọi hotline gây tốn chi phí vận hành tổng đài.",
             "Nói như gọi điện, Green SM thực thi. Không cần học thao tác app."],
            ["Người bận tay (hành lý, bế con, tại sân bay)",
             "Không thuận tiện cầm điện thoại và thao tác màn hình trong điều kiện di chuyển.",
             "Nói một câu, toàn bộ luồng đặt xe hoàn thành mà không cần chạm màn hình."],
            ["Người dùng cần tiếp cận đặc biệt",
             "UI hiện tại yêu cầu thị lực và vận động tinh để thao tác chính xác.",
             "Voice là kênh tương tác thay thế hoàn toàn, song song với giao diện hiện có."],
            ["Ban vận hành Green SM",
             "Chi phí tổng đài cao, tỷ lệ lost call giờ cao điểm, phụ thuộc nhân lực.",
             "Giảm tải tổng đài bằng cách tự phục vụ qua voice trong app — không cần hotline cho luồng đặt xe chuẩn."],
        ],
        col_widths=[Cm(3.5), Cm(5.5), Cm(6.5)]
    )

    _h(doc, "3. Bốn Trụ Cột Kỹ Thuật và Kết Quả Đo Lường")

    _p(doc, "3.1. Voice Streaming Pipeline tiếng Việt thời gian thực", bold=True, size=SIZE_H2)
    _p(doc,
       "Kết nối WebRTC LiveKit hai chiều với Silero VAD (phát hiện điểm dừng tự nhiên 220ms). "
       "Module VietnameseAudioChunker bóc tách luồng streaming token theo ngữ pháp tiếng Việt "
       "và từ đệm hội thoại, ép độ trễ phản hồi âm thanh đầu tiên xuống mức P95 = 1.41s. "
       "Đây là thành phần được giữ nguyên hoàn toàn sau pivot, tiếp tục đóng vai trò "
       "lớp transport cho voice assistant tích hợp Green SM.")

    _p(doc, "3.2. Typed AppAction Contract và AppContext Protocol (triển khai sau pivot)", bold=True, size=SIZE_H2)
    _p(doc,
       "Mỗi lượt hội thoại, mobile host Green SM gửi AppContext (bounded, validated bởi Pydantic) "
       "mô tả màn hình hiện tại, danh sách hành động được phép (available_actions) và "
       "tóm tắt ngữ nghĩa màn hình (screen_summary). OlaSM xử lý và trả về danh sách "
       "AppAction có kiểu dữ liệu tường minh với thời gian hiệu lực (expires_in_seconds). "
       "9 loại action được định nghĩa: NAVIGATE, GO_BACK, READ_SCREEN, SET_FIELD, "
       "SELECT_OPTION, SUBMIT, OPEN_HELP, REQUEST_OPEN_APP, END_ASSISTANT. "
       "Mobile host thực thi và gửi lại AppActionResult để agent biết kết quả. "
       "Trạng thái app-control được publish trên LiveKit data channel, topic olasm.app_control.v1.")

    _p(doc, "3.3. Guardrails An toàn 3 Lớp (mở rộng sau pivot)", bold=True, size=SIZE_H2)
    _p_mixed(doc, [
        ("• Input Rail: ", True, False, None),
        ("Phát hiện và chặn 100% prompt injection. Kiểm tra stt_confidence. "
         "Giới hạn độ dài transcript. Loại bỏ PII khỏi log.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• App Action Rail (mới sau pivot): ", True, False, None),
        ("Validate AppContext từ mobile host. Kiểm tra capability_allowed — "
         "action phải nằm trong available_actions của lượt đó. "
         "Từ chối action khi app không foreground (ngoại trừ REQUEST_OPEN_APP). "
         "Bắt buộc confirmation_required và risk ≠ SAFE_NAVIGATION cho SUBMIT.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Output Rail: ", True, False, None),
        ("Không cho phép side effect mà không có xác nhận tường minh. "
         "Không truyền thẻ/OTP/password vào LLM. "
         "Session control ENDED phải kèm END_ASSISTANT action.", False, False, None),
    ])

    _p(doc, "3.4. Dialog State Machine cho luồng Green SM", bold=True, size=SIZE_H2)
    _p(doc,
       "State machine quản lý toàn bộ ngữ cảnh hội thoại qua nhiều lượt, "
       "theo dõi màn hình hiện tại (từ AppContext), trạng thái form đang điền, "
       "quote đang chờ xác nhận, và kết quả action lượt trước (AppActionResult). "
       "Khi người dùng thay đổi yêu cầu giữa chừng (đổi điểm đến, đổi dịch vụ), "
       "state machine invalidate quote cũ và bắt đầu lại từ bước resolve địa chỉ. "
       "Không có trạng thái nào bị mất khi người dùng chuyển giữa voice và thao tác tay.")

    _h(doc, "4. Bảng Đối Soát Chỉ Số Kỹ Thuật")

    _table(doc,
        ["Hạng mục đo lường", "Mục tiêu", "Kết quả thực tế", "Đánh giá"],
        [
            ["Typed AppAction contract\n(NAVIGATE/GO_BACK/READ_SCREEN/SET_FIELD/SELECT_OPTION/SUBMIT/OPEN_HELP/REQUEST_OPEN_APP/END_ASSISTANT)",
             "Implemented + guardrail",
             "Implemented\n(src/agents/contracts/app_control.py)",
             "ĐẠT"],
            ["Guardrail App Action Rail\n(capability_allowed, foreground check, SUBMIT validation)",
             "Implemented",
             "Implemented\n(src/agents/core/guardrails.py)",
             "ĐẠT"],
            ["8 app-control function tools trong voice agent\n(navigate_app, go_back, read_current_screen, set_app_field,\nselect_app_option, submit_app_action, open_app_help, end_voice_assistant)",
             "Implemented",
             "Implemented\n(src/voice_agent/agent.py)",
             "ĐẠT"],
            ["LiveKit app-control state sync\ntopic: olasm.app_control.v1",
             "Implemented",
             "Implemented\n(src/voice_agent/state_sync.py)",
             "ĐẠT"],
            ["TTFA P95 (Voice pipeline tiếng Việt)",
             "≤ 1.5s",
             "1.41s (VietnameseAudioChunker)",
             "VƯỢT CHỈ TIÊU"],
            ["Tỷ lệ hoàn tất kịch bản voice (simulation suite)",
             "≥ 85.0%",
             "100.0% (50/50 kịch bản)",
             "ĐẠT CHUẨN TUYỆT ĐỐI"],
            ["Green SM API integration\n(Place, Quote, Booking, Trip, Payment, Support)",
             "Phase 1 target",
             "EXTERNAL_BLOCKED\n(chưa có hợp đồng API với GSM)",
             "CẦN CHỐT VỚI GSM"],
            ["Mobile SDK adapter\n(iOS / Android / Flutter / React Native)",
             "Phase 1 target",
             "EXTERNAL_BLOCKED\n(phụ thuộc công nghệ app GSM)",
             "CẦN XÁC NHẬN VỚI GSM"],
        ],
        col_widths=[Cm(5.5), Cm(2.8), Cm(4), Cm(3.2)]
    )

    _h(doc, "5. Điều Kiện Tiên Quyết từ Green SM (EXTERNAL_BLOCKED)")

    _p(doc,
       "Để hoàn thành Phase 1 và triển khai sản phẩm thực tế, nhóm cần làm việc "
       "trực tiếp với team Green SM để có được:")

    _table(doc,
        ["Hạng mục cần thiết", "Mục đích sử dụng trong hệ thống", "Mức độ ưu tiên"],
        [
            ["API xác thực người dùng (Authentication)", "Xác nhận identity người dùng khi khởi tạo voice session", "Cực kỳ cấp thiết — Phase 1"],
            ["API tìm kiếm địa điểm (Place / Address)", "Resolve địa điểm từ ngôn ngữ nói sang tọa độ/ID địa chỉ Green SM", "Cực kỳ cấp thiết — Phase 1"],
            ["API báo giá (Quote / Pricing)", "Truy vấn giá và ETA cho route người dùng yêu cầu", "Cực kỳ cấp thiết — Phase 1"],
            ["API tạo/hủy booking", "Thực thi đặt xe sau khi người dùng xác nhận", "Cực kỳ cấp thiết — Phase 1"],
            ["API trạng thái chuyến và thông tin tài xế", "Đọc vị trí tài xế, ETA, thông tin xe trong Phase 2", "Cấp thiết — Phase 2"],
            ["API khuyến mãi và thanh toán", "Áp dụng mã giảm giá, chọn phương thức thanh toán qua voice", "Cấp thiết — Phase 1–2"],
            ["API hỗ trợ và chuyển tổng đài", "Handoff kèm context khi voice không xử lý được", "Cấp thiết — Phase 1–2"],
            ["Sandbox, test account và webhook", "Kiểm thử end-to-end mà không ảnh hưởng production", "Cấp thiết — trước Phase 1"],
            ["Xác nhận công nghệ app mobile", "Xác định native iOS/Android, Flutter hay React Native để xây đúng SDK", "Cực kỳ cấp thiết — ngay bây giờ"],
        ],
        col_widths=[Cm(5), Cm(6), Cm(4.5)]
    )

    _h(doc, "6. Kết luận và Kiến nghị")

    _p(doc,
       "Pivot sang Green SM voice control layer là quyết định đúng đắn về chiến lược sản phẩm. "
       "Thay vì cạnh tranh với Green SM bằng một app mới, OlaSM tạo ra giá trị bổ sung "
       "trực tiếp trên nền tảng đã có hàng triệu người dùng. "
       "Toàn bộ hạ tầng kỹ thuật đã sẵn sàng — voice pipeline, typed action contract, "
       "guardrails và dialog state machine đều đã được triển khai và test.")

    _p(doc,
       "Nhóm 4 kính đề nghị TS. Lê Duy Dũng, Anh Lê Yên Thanh và Ban Đề án xem xét: "
       "(1) Xác nhận hướng pivot là đúng chiến lược sản phẩm; "
       "(2) Hỗ trợ kết nối nhóm với team kỹ thuật Green SM để chốt API/SDK chính thức; "
       "(3) Xác nhận công nghệ nền tảng app mobile Green SM (native, Flutter hay React Native) "
       "để nhóm xây đúng SDK adapter; "
       "(4) Phê duyệt tiếp tục Phase 1 MVP sau khi có API sandbox từ Green SM.")

    _divider(doc)
    _p(doc, "Đại diện nhóm báo cáo:", bold=True)
    _p(doc, "Nguyễn Đức Nam Khánh — MSSV: 2A202601103 (Trưởng nhóm kỹ thuật)")
    _p(doc, "Nguyễn Thị Phương — MSSV: 2A202601315 (Kỹ sư AI & Nghiệp vụ)")
    _p(doc, f"Nhóm dự án OlaSM — {PROGRAM}")
    _p(doc, f"Ngày nộp: {DATE_REPORT}")

    out = ROOT / "BaoCao_TomTat_POC_Nhom4_OlaSM.docx"
    doc.save(str(out))
    print(f"[OK] {out.name}")


# ─────────────────────────────────────────────────────────────────
# 3. BaoCao_KyThuat_POC_Nhom4_OlaSM_updated.docx
#    Báo cáo kỹ thuật chi tiết — kiến trúc, thuật toán, contract, kết quả
# ─────────────────────────────────────────────────────────────────

def make_ky_thuat() -> None:
    doc = _new_doc()

    _p(doc, "BÁO CÁO KỸ THUẬT POC CHI TIẾT",
       bold=True, size=Pt(14), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _p(doc, "OlaSM Voice Core — Trợ lý Giọng nói Điều khiển Toàn bộ App Mobile Green SM của VinGroup",
       bold=False, size=Pt(12), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _p(doc, "Phiên bản: 2.0 | Sau Pivot 2026-10-13",
       bold=False, size=Pt(11), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(2))
    _divider(doc)
    _p(doc, f"Chương trình: {PROGRAM}")
    _p(doc, f"Nhóm tác giả: {MEMBERS}")
    _p(doc, f"Hội đồng cố vấn & Ban giám khảo: {ADVISORS}")
    _p(doc, f"Thời điểm báo cáo: {DATE_REPORT} {DATE_NOTE}")
    _p(doc, f"Mã nguồn: {GITHUB}")
    _divider(doc)

    # ── 1. Tiến trình POC ──
    _h(doc, "1. Tổng Quan Tiến Trình POC và Quyết định Pivot")

    _p(doc, "1.1. Lịch sử Phase 3 — Nửa đầu (Tuần 1–3)", bold=True, size=SIZE_H2)
    _p(doc,
       "Trong ba tuần đầu của Phase 3, nhóm tập trung xây dựng hạ tầng kỹ thuật "
       "từ nền tảng: kiến trúc Dual-Plane (FastAPI control plane + LiveKit voice plane), "
       "luồng âm thanh WebRTC hai chiều tiếng Việt thời gian thực, "
       "các thuật toán lõi COE (Conversational Offer Engine), Dynamic Confidence Fusion, "
       "Guardrails 3 lớp và VietnameseAudioChunker. "
       "Kết quả cuối Tuần 3 đạt: TTFA P95 = 1.41s (vượt chuẩn ≤ 1.5s), "
       "tỷ lệ hoàn tất 50/50 kịch bản simulation = 100%.")

    _p(doc, "1.2. Quyết định Pivot (Tuần 4)", bold=True, size=SIZE_H2)
    _p(doc,
       "Sau khi nghiên cứu kỹ hệ sinh thái Green SM — ứng dụng mobile, API, "
       "chính sách dữ liệu và chiến lược vận hành của GSM — nhóm nhận ra rằng "
       "phát triển OlaSM như một ứng dụng gọi xe độc lập là không đúng hướng "
       "về mặt chiến lược sản phẩm lẫn kỹ thuật. Cụ thể:")

    _p_mixed(doc, [
        ("• Green SM đã có hệ sinh thái hoàn chỉnh: ", True, False, None),
        ("Bản đồ, định vị, báo giá, booking, theo dõi chuyến, thanh toán, "
         "khuyến mãi, tài xế và chính sách an toàn đều do GSM sở hữu và vận hành. "
         "Xây lại các thành phần này không tạo ra giá trị mà còn tạo ra "
         "sự không nhất quán dữ liệu nghiêm trọng.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Người dùng không cần thêm một app: ", True, False, None),
        ("Người dùng Green SM đã có ứng dụng quen thuộc. Yêu cầu họ cài thêm app "
         "OlaSM riêng biệt tạo ra rào cản cao hơn vấn đề cần giải quyết.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Tích hợp sâu mới tạo ra giá trị thực: ", True, False, None),
        ("Voice assistant có ý nghĩa thực sự khi nó điều khiển được "
         "chính ứng dụng mà người dùng đang dùng, không phải một app song song "
         "với dữ liệu giả lập.", False, False, None),
    ])

    _p(doc,
       "Quyết định pivot: OlaSM Voice Core trở thành lớp voice assistant "
       "tích hợp bên trong app mobile Green SM, điều khiển toàn bộ ứng dụng "
       "bằng giọng nói thông qua typed action contract. "
       "Tất cả hạ tầng kỹ thuật đã xây dựng trong Tuần 1–3 được giữ nguyên "
       "và tái sử dụng làm backend voice service.")

    _p(doc, "1.3. Lộ trình triển khai chi tiết", bold=True, size=SIZE_H2)
    _table(doc,
        ["Giai đoạn", "Thời gian", "Nội dung công việc", "Trạng thái"],
        [
            ["Tuần 1–3\n(Nửa đầu Phase 3)",
             "14/09–04/10/2026",
             "Kiến trúc Dual-Plane; LiveKit WebRTC; VAD; STT Deepgram Nova-3; LLM Agent; TTS Gemini Kore; VietnameseAudioChunker; COE; Dynamic Confidence Fusion; Guardrails 3 lớp",
             "ĐÃ HOÀN TẤT"],
            ["Tuần 4\n(Pivot)",
             "05/10–13/10/2026",
             "Typed AppAction contract; AppContext/AppActionResult protocol; 8 app-control function tools; App Action Rail guardrail; LiveKit state sync; Mobile instructions; Session schemas MOBILE_VOICE/MOBILE_TEXT",
             "ĐÃ HOÀN TẤT"],
            ["Tuần 5",
             "14/10–18/10/2026",
             "Green SM API adapter (EXTERNAL_BLOCKED chờ GSM); Mobile SDK adapter (phụ thuộc công nghệ app GSM); End-to-end integration test với sandbox",
             "KẾ HOẠCH"],
            ["Tuần 6",
             "19/10–25/10/2026",
             "Demo trên test build Green SM; stress test 100 voice session đồng thời; nghiệm thu Phase 3; Go/No-go decision",
             "KẾ HOẠCH"],
            ["Hậu Phase 3\n(Pilot)",
             "26/10–08/11/2026",
             "Thử nghiệm trên test build Green SM với người dùng thật; đo lường tỷ lệ hoàn tất, NPS và số lần fallback sang thao tác tay",
             "ROADMAP"],
        ],
        col_widths=[Cm(2.5), Cm(3), Cm(8), Cm(2)]
    )

    _p(doc, "1.4. Vướng mắc kỹ thuật cần hỗ trợ", bold=True, size=SIZE_H2)
    _p_mixed(doc, [
        ("• API/SDK chính thức từ Green SM (EXTERNAL_BLOCKED): ", True, False, None),
        ("Đây là điều kiện tiên quyết duy nhất để Phase 1 có thể hoàn thành. "
         "Nhóm cần: API xác thực người dùng, Place/Address API, Quote/Pricing API, "
         "Booking API, Trip Status API, Payment/Promotion API, Support/Handoff API, "
         "sandbox environment và test account. "
         "Toàn bộ adapter phía OlaSM đã được thiết kế sẵn sàng để kết nối.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Công nghệ nền tảng app mobile Green SM: ", True, False, None),
        ("Nhóm cần xác nhận Green SM mobile được xây bằng native iOS/Android, "
         "Flutter hay React Native để xây đúng mobile SDK adapter. "
         "LiveKit đã có SDK cho cả ba nền tảng.", False, False, None),
    ])

    # ── 2. Báo cáo kỹ thuật chi tiết ──
    _h(doc, "2. Báo Cáo Kỹ Thuật POC Chi Tiết")

    _p(doc, "2.1. Kiến trúc hệ thống tổng thể", bold=True, size=SIZE_H2)
    _p(doc,
       "Sau pivot, hệ thống OlaSM Voice Core được kiến trúc theo mô hình "
       "3 lớp phân định trách nhiệm rõ ràng:")

    _p_mixed(doc, [
        ("• Lớp 1 — Green SM Mobile App: ", True, False, None),
        ("App native iOS/Android/Flutter của VinGroup. Là mobile host — "
         "nơi người dùng tương tác, nơi Green SM API được gọi, "
         "nơi booking và thanh toán được thực thi. "
         "OlaSM không can thiệp vào business logic của lớp này.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Lớp 2 — OlaSM Voice Gateway: ", True, False, None),
        ("Backend service (FastAPI + LiveKit Worker) nhận luồng âm thanh từ mobile SDK, "
         "xử lý STT→LLM→TTS, quản lý dialog state, validate AppContext, "
         "và trả về AppAction list. Không gọi trực tiếp Green SM API — "
         "tất cả Green SM API calls được thực thi bởi mobile host sau khi nhận action.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Lớp 3 — Green SM APIs: ", True, False, None),
        ("Toàn bộ nguồn dữ liệu và nghiệp vụ: Place, Quote, Booking, Trip Status, "
         "Driver Info, Payment, Promotion, Support. OlaSM Voice Gateway không có đường "
         "kết nối trực tiếp đến các API này trong kiến trúc production — "
         "mobile host là người thực thi theo instruction của OlaSM.", False, False, None),
    ])

    _p(doc,
       "Sơ đồ luồng dữ liệu tổng thể (một lượt hội thoại):")
    _p(doc,
       "Mobile SDK → [Audio stream qua WebRTC LiveKit] → OlaSM Voice Gateway\n"
       "     → [AppContext từ mobile] → STT → LLM Agent → Guardrail → AppAction list\n"
       "     → [Publish olasm.app_control.v1 qua LiveKit data channel]\n"
       "     → Mobile SDK nhận AppAction → Mobile host thực thi → Green SM API\n"
       "     → AppActionResult → Mobile SDK → [gửi lại cho Agent lượt tiếp theo]",
       size=SIZE_SMALL, italic=True)

    _p(doc, "2.2. Voice Streaming Pipeline tiếng Việt", bold=True, size=SIZE_H2)
    _p(doc,
       "Pipeline xử lý âm thanh gồm 5 thành phần hoạt động theo chuỗi streaming:")

    _table(doc,
        ["Thành phần", "Công nghệ", "Chức năng", "Độ trễ đo được"],
        [
            ["Voice Activity Detection", "Silero VAD", "Phát hiện điểm dừng nói tự nhiên. Ngưỡng silence: 220ms.", "220ms"],
            ["Speech-to-Text", "Deepgram Nova-3 (streaming)", "Nhận diện và bóc băng tiếng Việt. Hỗ trợ accent Hà Nội và TP.HCM.", "310ms (p50)"],
            ["LLM Agent & State Policy", "OpenAI GPT-4 class (tool calling)", "Suy luận intent, trích xuất thực thể, quản lý dialog state, tạo AppAction list.", "450ms (p50)"],
            ["VietnameseAudioChunker", "Custom module", "Bóc tách luồng streaming token theo ngữ pháp tiếng Việt và từ đệm hội thoại. Đẩy buffer sang TTS ngay khi có cụm từ hoàn chỉnh.", "15ms"],
            ["Text-to-Speech", "Gemini Flash Kore (primary)\nChirp 3 HD (fallback)", "Tổng hợp audio cụm từ đầu tiên, trả về luồng WebRTC. Chirp 3 HD kích hoạt khi Gemini latency vượt ngưỡng.", "265ms (p50)"],
        ],
        col_widths=[Cm(3.8), Cm(3.5), Cm(5.5), Cm(2.7)]
    )

    _p(doc,
       "Tổng độ trễ Turn Latency p50 = 1.26s (VAD 220ms + STT 310ms + LLM 450ms + Chunker 15ms + TTS 265ms). "
       "TTFA P95 = 1.41s, vượt chuẩn cam kết ≤ 1.5s.")

    _p(doc, "2.3. Typed AppAction Contract", bold=True, size=SIZE_H2)
    _p(doc,
       "AppAction contract là giao thức giao tiếp giữa OlaSM Voice Gateway "
       "và mobile host Green SM. Được định nghĩa hoàn chỉnh tại "
       "src/agents/contracts/app_control.py bằng Pydantic với mode extra='forbid'.")

    _p(doc, "Cấu trúc AppContext — dữ liệu mobile host gửi vào mỗi lượt:", bold=True, size=SIZE_SMALL)
    _table(doc,
        ["Field", "Kiểu dữ liệu", "Ràng buộc", "Mô tả"],
        [
            ["schema_version", "Literal['1']", "Bắt buộc", "Phiên bản schema để phát hiện breaking change"],
            ["app", "Literal['GREEN_SM']", "Bắt buộc", "Định danh app host — chỉ GREEN_SM được chấp nhận"],
            ["screen", "AppScreen enum", "Bắt buộc", "Màn hình hiện tại (HOME/CAR_BOOKING/TRIP_TRACKING/...)"],
            ["platform", "IOS | ANDROID | UNKNOWN", "Bắt buộc", "Nền tảng mobile để chọn SDK phù hợp"],
            ["foreground", "bool", "Bắt buộc", "App có đang foreground không — ảnh hưởng đến action được phép"],
            ["available_actions", "list[str] ≤ 64", "Bắt buộc, unique", "Danh sách action host cho phép lượt này. Guardrail đối chiếu chặt."],
            ["screen_summary", "str | None ≤ 1000", "Tùy chọn", "Tóm tắt ngữ nghĩa màn hình để agent đọc cho người dùng"],
            ["screen_state", "dict", "Không chứa secret", "Dữ liệu form hiện tại. Validator từ chối bất kỳ key nào chứa 'password/token/secret/cvv/otp/card_number/access_key'"],
            ["last_action_result", "AppActionResult | None", "Tùy chọn", "Kết quả thực thi action lượt trước để agent điều chỉnh"],
        ],
        col_widths=[Cm(3.5), Cm(3.5), Cm(2.5), Cm(6)]
    )

    _p(doc, "Cấu trúc AppAction — lệnh OlaSM trả về:", bold=True, size=SIZE_SMALL)
    _table(doc,
        ["Kind", "Mô tả", "Risk Level", "Xác nhận"],
        [
            ["NAVIGATE", "Điều hướng đến màn hình Green SM (phải nằm trong available_actions)", "SAFE_NAVIGATION", "Không"],
            ["GO_BACK", "Quay lại màn hình trước trong navigation stack", "SAFE_NAVIGATION", "Không"],
            ["READ_SCREEN", "Đọc screen_summary do host cung cấp (không tự đọc DOM)", "SAFE_NAVIGATION", "Không"],
            ["SET_FIELD", "Điền giá trị vào trường form được host quảng bá rõ ràng (field:xxx)", "USER_CONFIRMATION", "Tự động"],
            ["SELECT_OPTION", "Chọn option trong danh sách được host quảng bá", "USER_CONFIRMATION", "Tự động"],
            ["SUBMIT", "Thao tác có side effect. Bắt buộc có confirmation_required=True và risk ≠ SAFE_NAVIGATION.", "APP_CONFIRMATION\nhoặc BIOMETRIC_REQUIRED", "Bắt buộc qua UI Green SM"],
            ["OPEN_HELP", "Mở màn hình hỗ trợ/tổng đài Green SM", "SAFE_NAVIGATION", "Không"],
            ["REQUEST_OPEN_APP", "Yêu cầu OS đưa Green SM lên foreground. Chỉ dùng khi foreground=false.", "OS_MANAGED", "Tùy OS"],
            ["END_ASSISTANT", "Dừng phiên voice, giải phóng microphone. Không force-quit app.", "SAFE_NAVIGATION", "Không"],
        ],
        col_widths=[Cm(3.5), Cm(6), Cm(3), Cm(2.5)]
    )

    _p(doc, "2.4. Guardrails An toàn — App Action Rail", bold=True, size=SIZE_H2)
    _p(doc,
       "Sau pivot, guardrail được mở rộng thêm App Action Rail "
       "(hàm _validate_app_actions trong src/agents/core/guardrails.py). "
       "Logic kiểm tra:")

    _p_mixed(doc, [
        ("• capability_allowed check: ", True, False, None),
        ("Với mỗi AppAction trong danh sách trả về, guardian map action kind "
         "sang capability string (NAVIGATE → 'navigate:SCREEN_NAME', "
         "SET_FIELD → 'field:field_name', SUBMIT → 'submit:target_name', v.v.) "
         "và kiểm tra capability string đó có nằm trong context.available_actions không. "
         "Action không được host quảng bá bị từ chối ngay lập tức, "
         "không phụ thuộc vào quyết định của model.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Foreground check: ", True, False, None),
        ("Nếu context.foreground = False (app đang background), "
         "chỉ REQUEST_OPEN_APP và END_ASSISTANT được phép. "
         "Mọi action khác bị từ chối với lý do 'foreground app context required'.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• SUBMIT validation: ", True, False, None),
        ("Action SUBMIT phải thỏa mãn đồng thời: confirmation_required = True "
         "và risk ≠ SAFE_NAVIGATION. Nếu model cố gắng bypass bằng cách "
         "đặt confirmation_required = False hoặc risk = SAFE_NAVIGATION, "
         "guardrail từ chối ngay.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Biometric targets: ", True, False, None),
        ("Các target action nhạy cảm cao (pay, payment, cancel_ride, delete_account, "
         "logout, change_security, change_phone) tự động được nâng risk level lên "
         "BIOMETRIC_REQUIRED. Session control chuyển sang BIOMETRIC_REQUIRED, "
         "kích hoạt Face ID/Touch ID trên thiết bị người dùng.", False, False, None),
    ])
    _p_mixed(doc, [
        ("• Unique action_id: ", True, False, None),
        ("Mỗi action_id trong một lượt phải duy nhất. "
         "Đây là cơ chế idempotency để tránh thực thi trùng khi mobile host "
         "retry sau network timeout.", False, False, None),
    ])

    _p(doc, "2.5. Thuật toán Confident Fusion và Dialog Policy (giữ lại từ Tuần 1–3)", bold=True, size=SIZE_H2)
    _p(doc,
       "Hệ thống tổng hợp độ tin cậy từ bốn nguồn độc lập để quyết định "
       "mức độ tự động của từng lượt:")
    _formula(doc, "c_trip = w₁ · p_STT + w₂ · p_intent + w₃ · p_addr + w₄ · p_screen")
    _formula_note(doc, "(hệ số chuẩn: w₁ = 0.30, w₂ = 0.25, w₃ = 0.25, w₄ = 0.20; sau pivot p_vision thay bằng p_screen)")

    _p(doc,
       "Trong đó: p_STT là điểm tin cậy của Deepgram STT; "
       "p_intent là điểm chắc chắn về intent từ LLM; "
       "p_addr là điểm resolve địa chỉ từ Green SM Place API; "
       "p_screen là điểm phù hợp giữa action yêu cầu và màn hình hiện tại từ AppContext.")

    _formula(doc, "c_trip ≥ τ_high : AUTO_ACTION   |   τ_low < c_trip < τ_high : CLARIFY   |   c_trip ≤ τ_low : HANDOFF")
    _formula_note(doc, "(ngưỡng: τ_high = 0.85, τ_low = 0.55)")

    _p(doc,
       "Khi p_screen = 0 (AppContext không có screen_summary), "
       "trọng số w₄ được phân bổ lại đều cho ba nguồn còn lại "
       "(Dynamic Weight Renormalization). "
       "Cơ chế này đảm bảo hệ thống hoạt động ổn định kể cả khi "
       "mobile host không cung cấp screen_summary.")

    _p(doc, "2.6. Kết quả thực nghiệm kỹ thuật tổng hợp", bold=True, size=SIZE_H2)
    _table(doc,
        ["Phân hệ kỹ thuật", "Kết quả thực nghiệm kỹ thuật sau Tuần 4", "Đánh giá nghiệm thu"],
        [
            ["Voice Streaming Pipeline\n(Tuần 1–3 — Giữ lại hoàn toàn)",
             "WebRTC LiveKit hai chiều, Silero VAD (220ms), Deepgram Nova-3 streaming, VietnameseAudioChunker. TTFA P95 = 1.41s. Turn Latency p50 = 1.26s.",
             "VƯỢT CHỈ TIÊU\n(P95 ≤ 1.5s ✓)"],
            ["Typed AppAction Contract\n(src/agents/contracts/app_control.py)",
             "Pydantic model với extra='forbid'. 9 action kinds, 5 risk levels, TTL, action_id unique constraint, secret key rejection trong screen_state.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["AppContext Validator\n(mỗi lượt hội thoại)",
             "Validate schema_version, app='GREEN_SM', screen enum, available_actions unique, screen_state không chứa secret keys.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["App Action Rail Guardrail\n(src/agents/core/guardrails.py)",
             "capability_allowed check, foreground check, SUBMIT validation, biometric targets, unique action_id enforcement.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["8 App-Control Function Tools\n(src/voice_agent/agent.py)",
             "navigate_app, go_back, read_current_screen, set_app_field, select_app_option, submit_app_action, open_app_help, end_voice_assistant, request_open_app.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["LiveKit App-Control State Sync\n(src/voice_agent/state_sync.py)",
             "publish_app_control_state() trên topic 'olasm.app_control.v1'. Publish sau mỗi lượt xử lý. AppControlState gồm screen, session_control, app_actions.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["Dialog State Machine cho Green SM\n(OlaSMSessionData mở rộng)",
             "Theo dõi app_context, pending_app_actions, app_session_control. clear_app_actions(), queue_app_action(), set_app_context() methods.",
             "HOÀN THÀNH\n(IMPLEMENTED ✓)"],
            ["Green SM API Integration\n(Place, Quote, Booking, Trip, Payment, Support)",
             "GSMSandboxClient (chỉ test). Adapter thật: EXTERNAL_BLOCKED — chưa có hợp đồng API với team Green SM.",
             "EXTERNAL_BLOCKED\n(chờ GSM APIs)"],
            ["Mobile SDK adapter\n(iOS / Android / Flutter / React Native)",
             "Chưa xây dựng. Phụ thuộc xác nhận công nghệ app Green SM.",
             "EXTERNAL_BLOCKED\n(chờ xác nhận GSM)"],
            ["Tỷ lệ hoàn tất kịch bản simulation\n(50-Scenario Suite)",
             "100.0% (50/50) với dữ liệu simulation. Cần chạy lại với Green SM sandbox khi có API.",
             "ĐẠT CHUẨN (simulation)\nCHỜ validation thật"],
        ],
        col_widths=[Cm(4.5), Cm(7.5), Cm(3.5)]
    )

    _h(doc, "3. Phân Bổ Công Việc và Kế Hoạch Triển Khai")

    _p(doc, "3.1. Phân công trong Tuần 4 (Pivot)", bold=True, size=SIZE_H2)
    _table(doc,
        ["Thành viên", "Vai trò trọng tâm", "Phần việc đã hoàn thành trong Tuần 4"],
        [
            ["Nguyễn Đức Nam Khánh\nMSSV: 2A202601103",
             "Hạ tầng & Backend\nContract & Guardrail",
             "• Thiết kế và triển khai AppContext/AppAction/AppScreen contract (Pydantic)\n"
             "• AppAction risk levels, TTL, action_id idempotency\n"
             "• App Action Rail guardrail: capability_allowed, foreground, SUBMIT, biometric targets\n"
             "• 8 app-control function tools trong voice agent (navigate, go_back, read_screen, set_field, select_option, submit, help, end, open_app)\n"
             "• LiveKit app-control state sync: publish_app_control_state, topic olasm.app_control.v1\n"
             "• OlaSMSessionData: app_context, pending_app_actions, app_session_control\n"
             "• Extend AgentInput/AgentAction với app_context, app_actions, session_control\n"
             "• TypeScript types: AppAction/AppControlState trong contracts.ts"],
            ["Nguyễn Thị Phương\nMSSV: 2A202601315",
             "AI & Dialog\nProduct & Docs",
             "• Mobile system instructions (mobile_instructions.py) — system prompt cho agent mới\n"
             "• Intent extraction mapping cho tất cả màn hình Green SM\n"
             "• Dialog state machine mở rộng cho luồng Green SM (navigate, fill form, submit, track)\n"
             "• Cập nhật eval cases cho voice-to-book workflow với AppAction validation\n"
             "• Cập nhật toàn bộ tài liệu: README, PRODUCT_BRIEF, PROJECT_SOURCE_OF_TRUTH, PRD v2.0\n"
             "• Báo cáo kỹ thuật, báo cáo ý tưởng, báo cáo tóm tắt (tài liệu này)"],
        ],
        col_widths=[Cm(3.8), Cm(3.5), Cm(8.2)]
    )

    _p(doc, "3.2. Kế hoạch chi tiết Tuần 5–6 và Hậu Phase 3", bold=True, size=SIZE_H2)
    _table(doc,
        ["Thành viên phụ trách", "Nội dung công việc trọng tâm", "Thời hạn", "Kết quả bàn giao"],
        [
            ["Nguyễn Đức Nam Khánh",
             "Kết nối Green SM Place/Quote/Booking APIs (sau khi có sandbox)\nXây mobile SDK adapter (iOS/Android/Flutter sau khi xác nhận công nghệ GSM)\nEnd-to-end integration test: voice → AppAction → Green SM API → AppActionResult",
             "18/10/2026\n(Tuần 5)",
             "GSM API adapter hoạt động\nMobile SDK demo\nE2E test report"],
            ["Nguyễn Thị Phương",
             "Chạy lại 50-Scenario Suite với Green SM sandbox APIs thật\nĐo lường TTFA, tỷ lệ resolve địa chỉ, fallback rate và handoff quality với dữ liệu thật\nChuẩn bị tài liệu nghiệm thu Phase 3 và báo cáo Go/No-go",
             "25/10/2026\n(Tuần 6)",
             "Eval report với dữ liệu thật\nBáo cáo nghiệm thu Phase 3\nGo/No-go decision"],
            ["Cả hai thành viên",
             "Demo trên test build Green SM với người dùng thật (5–10 người)\nStress test 100 voice session đồng thời\nPilot planning cho Hậu Phase 3",
             "25/10/2026\n(Tuần 6)",
             "Demo recording\nStress test report\nPilot plan"],
        ],
        col_widths=[Cm(3.5), Cm(7.5), Cm(2.3), Cm(2.7)]
    )

    _h(doc, "4. Kết Luận và Kiến Nghị")

    _p(doc,
       "OlaSM Voice Core sau pivot đã xác lập được kiến trúc kỹ thuật đúng đắn: "
       "voice assistant layer tích hợp vào Green SM mobile thông qua typed action contract, "
       "với guardrail chặt chẽ đảm bảo model không thể thực thi bất kỳ hành động nào "
       "ngoài những gì mobile host Green SM cho phép trong từng lượt hội thoại. "
       "Toàn bộ hạ tầng backend đã sẵn sàng: voice pipeline đạt TTFA P95 = 1.41s, "
       "typed contract implemented, guardrail implemented, 8 app-control tools implemented, "
       "LiveKit state sync implemented. Điều kiện duy nhất còn thiếu là API chính thức "
       "từ Green SM và xác nhận công nghệ app mobile.")

    _p(doc,
       "Nhóm 4 kính đề nghị TS. Lê Duy Dũng, Anh Lê Yên Thanh và Ban Đề án xem xét: "
       "(1) Xác nhận hướng pivot phù hợp chiến lược sản phẩm; "
       "(2) Hỗ trợ kết nối nhóm với team kỹ thuật Green SM để có API sandbox "
       "trước ngày 14/10/2026; "
       "(3) Xác nhận công nghệ nền tảng app mobile Green SM để nhóm xây đúng SDK; "
       "(4) Cân nhắc kéo dài thời hạn Phase 3 thêm 1–2 tuần nếu việc chốt API với GSM "
       "kéo dài hơn dự kiến, nhằm đảm bảo có ít nhất một end-to-end demo "
       "với Green SM sandbox trước khi nghiệm thu.")

    _divider(doc)
    _p(doc, "Đại diện nhóm báo cáo:", bold=True)
    _p(doc, "Nguyễn Đức Nam Khánh — MSSV: 2A202601103 (Trưởng nhóm kỹ thuật)")
    _p(doc, "Nguyễn Thị Phương — MSSV: 2A202601315 (Kỹ sư AI & Nghiệp vụ)")
    _p(doc, f"Nhóm dự án OlaSM — {PROGRAM}")
    _p(doc, f"Ngày nộp: {DATE_REPORT}")

    out = ROOT / "BaoCao_KyThuat_POC_Nhom4_OlaSM_updated.docx"
    doc.save(str(out))
    print(f"[OK] {out.name}")


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Đang tạo lại toàn bộ bộ báo cáo OlaSM Voice Core...")
    make_y_tuong()
    make_tom_tat()
    make_ky_thuat()
    print("\nHoàn tất. Ba file DOCX đã được ghi vào thư mục gốc:")
    print("  BaoCao_YTuong_Nhom4_OlaSM.docx")
    print("  BaoCao_TomTat_POC_Nhom4_OlaSM.docx")
    print("  BaoCao_KyThuat_POC_Nhom4_OlaSM_updated.docx")
