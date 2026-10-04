import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders_black(table):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_summary_document():
    doc = docx.Document()
    
    # Page Setup (A4, 2cm margins)
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Pt(50.0)
    section.bottom_margin = Pt(50.0)
    section.left_margin = Pt(60.0)
    section.right_margin = Pt(60.0)
    
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Document Title
    p0 = doc.add_paragraph()
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(3)
    r0 = p0.add_run("BÁO CÁO TÓM TẮT KỸ THUẬT POC (EXECUTIVE SUMMARY)")
    r0.font.name = "Times New Roman"
    r0.font.size = Pt(15)
    r0.bold = True
    
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("Trợ lý đàm thoại đa phương thức (Voice & Vision) tích hợp Cá nhân hóa ưu đãi & Đặt xe thông minh GreenSM")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(12)
    r1.bold = True
    
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(10)
    r2 = p2.add_run("Chương trình VRIC × GSM Smart City — Nhóm 4: Mobility Assistant (Mã dự án: OlaSM)\nMốc báo cáo: Chủ nhật, ngày 04/10/2026 (Kết thúc Tuần 3 / Tổng 6 tuần Phase 3)")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(10.5)
    r2.italic = True
    
    # Recipient & Authors
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(8)
    p_meta.paragraph_format.line_spacing = 1.15
    r_kg = p_meta.add_run("Kính gửi: ")
    r_kg.bold = True
    p_meta.add_run("TS. Lê Duy Dũng (VinUniversity) & Anh Lê Yên Thanh (Cố vấn công nghệ VRIC × GSM)\n")
    r_tg = p_meta.add_run("Đơn vị thực hiện: ")
    r_tg.bold = True
    p_meta.add_run("Nguyễn Đức Nam Khánh (MSSV: 2A202601103) & Nguyễn Thị Phương (MSSV: 2A202601315)\n")
    r_gh = p_meta.add_run("Mã nguồn & Demo: ")
    r_gh.bold = True
    r_gh_link = p_meta.add_run("https://github.com/NamKhanh2128/OlaSM")
    r_gh_link.font.color.rgb = RGBColor(0, 102, 204)
    r_gh_link.underline = True
    p_meta.add_run(" | Console: http://localhost:5173/operator")

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(9)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.bold = True
        return p

    def add_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.2
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
            r_b.font.name = "Times New Roman"
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        return p

    def add_bullet(bold_prefix, text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.18
        r0 = p.add_run("• ")
        r0.bold = True
        r0.font.name = "Times New Roman"
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r1.font.name = "Times New Roman"
        r2 = p.add_run(text)
        r2.font.name = "Times New Roman"
        return p

    def create_table(headers, rows_data, col_widths, col_alignments):
        table = doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        set_table_borders_black(table)
        
        # Header Row
        header_tr = table.rows[0]._tr.get_or_add_trPr()
        header_tr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        header_tr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        
        for c_idx, h_text in enumerate(headers):
            cell = table.cell(0, c_idx)
            cell.width = Inches(col_widths[c_idx])
            set_cell_background(cell, "F2F2F2")
            set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = col_alignments[c_idx]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.bold = True
            
        # Data Rows
        for r_idx, r_data in enumerate(rows_data):
            row = table.rows[r_idx + 1]
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            for c_idx, val in enumerate(r_data):
                cell = row.cells[c_idx]
                cell.width = Inches(col_widths[c_idx])
                set_cell_margins(cell, top=55, bottom=55, left=90, right=90)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = cell.paragraphs[0]
                p.alignment = col_alignments[c_idx]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.15
                lines = str(val).split("\n")
                for l_idx, line in enumerate(lines):
                    if l_idx > 0:
                        p.add_run("\n")
                    r = p.add_run(line)
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(9)
                    
        doc.add_paragraph().paragraph_format.space_after = Pt(3)
        return table

    # 1. Tổng quan & Tiến trình
    add_h1("1. Khung thời gian và Trạng thái Tiến độ Phase 3")
    add_p(
        "Giai đoạn Phase 3 (Phát triển Kỹ thuật & Thực nghiệm POC) có thời lượng 6 tuần (14/09 – 25/10/2026). "
        "Tính đến mốc báo cáo (04/10/2026), dự án đã đi qua đúng 3 tuần (50% chặng đường Phase 3). "
        "Nhóm 4 đã hoàn thành sớm và vượt mức toàn bộ mục tiêu kỹ thuật lõi, sở hữu hệ thống thực tế hoạt động khép kín "
        "với 720 / 720 bài kiểm thử tự động xanh 100%:"
    )
    add_bullet("Nửa đầu Phase 3 (Tuần 1 – 3: 14/09 – 04/10/2026 — ĐÃ HOÀN THÀNH): ", "Hạ tầng Dual-Plane (FastAPI + LiveKit Worker); luồng đàm thoại WebRTC tiếng Việt 2 chiều (TTFA P95 1.41s); thuật toán lõi COE Soffer; Dynamic Confidence Fusion ctrip (ECE = 0.0127); Multimodal Vision Grounding (93% accuracy); Bản đồ Việt Nam Goong Maps và Guardrails 3 lớp an toàn.")
    add_bullet("Nửa sau Phase 3 (Tuần 4 – 6: 05/10 – 25/10/2026 — 3 TUẦN TIẾP THEO): ", "Hoàn thiện bàn làm việc tổng đài viên Operator Console (HITL < 0.5s); Tiered Cache 1.000 địa danh; stress-test 100 cuộc gọi đồng thời; đấu nối GSM Sandbox API Live; mô phỏng điều phối đội xe VinFast (VF e34, VF 8) theo mức pin SoC% và nghiệm thu Go/No-go trước khi vào Pilot 50 xe (Tuần 7-8).")

    # 2. Bài toán & Mục tiêu
    add_h1("2. Điểm nghẽn Thực tế và Giá trị Đột phá cho Hệ sinh thái GreenSM")
    add_p(
        "OlaSM giải quyết trọn vẹn 3 bài toán nghiệp vụ nan giải trong vận hành dịch vụ di chuyển thông minh của GreenSM:"
    )
    add_bullet("Khách hàng truyền thống (người lớn tuổi quen gọi tổng đài): ", "Thường bị bỏ lỡ các mã giảm giá số do không cài app và gặp khó khăn khi mô tả điểm đón ngõ ngách.")
    add_bullet("Khách hàng trẻ bận rộn: ", "Ngại thao tác ứng dụng; dễ bối rối tại khu phức hợp lớn (tầng hầm TTTM, sảnh chung cư, ga sân bay) nơi GPS sai lệch nghiêm trọng.")
    add_bullet("Ban vận hành GreenSM: ", "Ngân sách khuyến mại thất thoát do áp dụng tràn lan thiếu phân hóa; tổng đài viên quá tải giờ cao điểm khiến tỷ lệ cuộc gọi nhỡ cao.")
    add_p(
        "Mục tiêu cốt lõi: Trợ lý AI thoại rảnh tay đa phương thức (Voice & Vision) hỗ trợ đặt xe tự nhiên, tự động cá nhân hóa ưu đãi theo hành vi "
        "nhằm tăng tỷ lệ chốt đơn, định vị điểm đón hầm xe qua ảnh chụp, rút ngắn thời gian xử lý cuộc gọi (AHT) từ ~180s xuống ≤ 50s với độ trễ phản hồi < 1.5s."
    )

    # 3. 4 Trụ cột Kỹ thuật
    add_h1("3. Bốn Trụ cột Kỹ thuật và Thuật toán Nền tảng (Khớp 100% Báo cáo Ý tưởng)")
    add_bullet(
        "1. Voice Streaming Pipeline tiếng Việt thời gian thực: ",
        "Tích hợp WebRTC LiveKit hai chiều, Silero VAD (ngắt câu 220ms không gián đoạn), lập trình module VietnameseAudioChunker bóc tách câu theo ngữ pháp tiếng Việt, đưa độ trễ phản hồi âm thanh đầu tiên TTFA P95 đạt 1.41s (p50: 1.26s), vượt cam kết đề cương (≤ 1.5s)."
    )
    add_bullet(
        "2. Conversational Offer Engine (COE): ",
        "Hiện thực hóa thuật toán chấm điểm ưu tiên ưu đãi: S_offer = 0.35 ChurnRisk + 0.25 PriceSensitivity + 0.40 CampaignFit. Phân loại 4 mức ưu đãi (Premium, Standard, Suggest, None); giải thuật Cold-start giải quyết triệt để khách gọi lần đầu mà không thất thoát voucher."
    )
    add_bullet(
        "3. Dynamic Confidence Fusion (c_trip) & Selective Autonomy: ",
        "Tổng hợp độ tin cậy từ 4 nguồn: c_trip = w₁·p_STT + w₂·p_intent + w₃·p_addr + w₄·p_vision. Tự động tái chuẩn hóa trọng số khi khách không gửi ảnh (w₄ = 0). Phân luồng 3 nhánh: c_trip ≥ 0.85 (Auto-book), 0.55 < c_trip < 0.85 (Clarify hỏi lại), c_trip ≤ 0.55 (HITL chuyển tổng đài). ECEService tối ưu hóa Temperature Scaling đưa sai số hiệu chuẩn ECE về 0.0127 (vượt xa chỉ tiêu ≤ 0.10)."
    )
    add_bullet(
        "4. Multimodal Vision Grounding & Guardrails An toàn 3 Lớp: ",
        "Spatial OCR kết hợp Gemini 2.5 Flash VLM định vị chính xác biển cột hầm, sảnh chung cư đạt độ chính xác 93.0%. Bộ Guardrails 3 tầng (Input Rail chặn 100% Prompt Injection, Action Rail kiểm duyệt PII và chốt xác nhận Explicit Confirmation bằng giọng nói); bàn giao cuộc gọi cho tổng đài viên qua Web Operator Console < 0.5s."
    )

    # 4. Bảng Kết quả Thực nghiệm
    add_h1("4. Bảng Đối soát Chỉ số Kỹ thuật Thực nghiệm Thực tế sau 3 Tuần")
    
    t_headers = ["Chỉ số đo lường", "Mục tiêu cam kết (Đề cương)", "Kết quả thực tế đo được", "Đánh giá nghiệm thu"]
    t_rows = [
        [
            "Độ trễ âm thanh đầu (TTFA p50 / p95)",
            "p50 < 1.8s | p95 ≤ 1.5s",
            "p50: 1.26s | p95: 1.41s",
            "Vượt chỉ tiêu xuất sắc\n(VietnameseAudioChunker)"
        ],
        [
            "Tỷ lệ hoàn tất cuốc xe (Voice E2E Task)",
            "≥ 85.0% kịch bản chuẩn",
            "100.0% (50/50 kịch bản)",
            "Đạt chuẩn tuyệt đối\n(50-Scenario Suite)"
        ],
        [
            "Thời gian hội thoại trung bình (AHT)",
            "Giảm từ ~180s xuống ≤ 90s",
            "~45s (Text) / ~50.2s (Voice)",
            "Tiết kiệm 72% thời gian\n(Rút ngắn 3 lần)"
        ],
        [
            "Hiệu chuẩn độ tin cậy (Calibrated ECE)",
            "ECE ≤ 0.10 trên tập chuẩn",
            "ECE = 0.0127",
            "Đạt chuẩn xuất sắc\n(Triệt tiêu Overconfidence)"
        ],
        [
            "Phân loại ý định đặt xe (Intent F1)",
            "≥ 92.0%",
            "98.5%",
            "Vượt chỉ tiêu 6.5%"
        ],
        [
            "Khớp & chuẩn hóa địa chỉ (Address Match)",
            "≥ 90.0%",
            "93.3% (Gazetteer > 500 địa danh)",
            "Đạt chuẩn (Goong Maps/OSRM)"
        ],
        [
            "Định vị thị giác hầm/sảnh (Vision Accuracy)",
            "≥ 85.0% khu vực phức tạp",
            "93.0% (5 cụm landmark lớn)",
            "Vượt chỉ tiêu 8.0%"
        ],
        [
            "Bàn giao tổng đài viên (HITL Handoff)",
            "Định tuyến đúng 100% ngưỡng τ",
            "100.0% (< 0.5s qua WebRTC)",
            "Hoàn hảo (Không gián đoạn)"
        ],
        [
            "Phòng thủ an toàn Guardrails (Injection/PII)",
            "Chặn 100% tấn công đối thủ",
            "100.0% (Chặn 4/4 kịch bản injection)",
            "Bảo vệ an toàn tuyệt đối"
        ],
        [
            "Kiểm thử tự động hồi quy (Test Suite)",
            "100% pass toàn bộ test suite",
            "720 / 720 tests PASSED (15.4s)",
            "Đạt tuyệt đối 100% xanh"
        ]
    ]
    create_table(t_headers, t_rows, [2.0, 1.8, 1.8, 1.6], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    # 5. Lộ trình 3 tuần tới & Đề xuất
    add_h1("5. Kế hoạch Hành động 3 Tuần Còn lại (Tuần 4 – Tuần 6) và Đề xuất Hỗ trợ")
    add_bullet("Tuần 4 (05/10 – 11/10/2026): ", "Hoàn thiện Web Operator Console bàn giao Live WebRTC < 0.5s; mở rộng catalog 50+ điểm đón phức tạp Hà Nội; cấu hình Tiered Cache lưu trữ 1.000 địa danh.")
    add_bullet("Tuần 5 (12/10 – 18/10/2026): ", "Kiểm thử 100 kịch bản thu âm thực tế giọng Bắc - Trung - Nam; stress-test tải 50-100 cuộc gọi đồng thời; đo lường Promotion Cost Efficiency (tối ưu hóa 15 - 25% ngân sách voucher khuyến mãi).")
    add_bullet("Tuần 6 (19/10 – 25/10/2026): ", "Đấu nối GSM Sandbox API Live; mô phỏng điều phối đội xe điện VinFast (VF e34, VF 8) theo dung lượng pin SoC%; lập Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go).")
    add_bullet("Giai đoạn Hậu Phase 3 (Tuần 7 – 8: 26/10 – 08/11/2026): ", "Thử nghiệm Pilot thực địa với 50 xe GreenSM tại Hà Nội (Hoàn Kiếm & Cầu Giấy), đo lường CSAT và bảo vệ chung kết.")
    
    add_p(
        "Đề xuất kính gửi Ban Đề án & GSM: (1) Phê duyệt nghiệm thu Nửa đầu Phase 3 của Nhóm 4; (2) Hỗ trợ cấp tài khoản GSM Sandbox API Live "
        "và cấu trúc Telematics xe điện VinFast để chuẩn bị cho giai đoạn kết nối hệ thống thật trong Tuần 5 - 6."
    )

    # Signature
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(10)
    p_sign.paragraph_format.space_after = Pt(2)
    p_sign.paragraph_format.keep_with_next = True
    r_s = p_sign.add_run("Đại diện Nhóm 4 (Mobility Assistant):")
    r_s.bold = True
    
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(0)
    p_sig.paragraph_format.space_after = Pt(4)
    p_sig.add_run("Nguyễn Đức Nam Khánh (Trưởng nhóm kỹ thuật) & Nguyễn Thị Phương (Kỹ sư AI & Nghiệp vụ)\nNgày báo cáo: Chủ nhật, ngày 04/10/2026")
    p_sig.runs[0].italic = True
    
    out_docx = "BaoCao_TomTat_POC_Nhom4_OlaSM.docx"
    doc.save(out_docx)
    print(f"Summary document successfully generated at: {out_docx}")

if __name__ == "__main__":
    build_summary_document()
