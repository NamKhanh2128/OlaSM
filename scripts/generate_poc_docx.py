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

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
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

def build_document():
    doc = docx.Document()
    
    # 1. Page Setup matching standard academic/project report (A4, 2cm margins)
    section = doc.sections[0]
    section.page_width = Inches(8.27)   # A4: 21.0 cm
    section.page_height = Inches(11.69) # A4: 29.7 cm
    section.top_margin = Pt(55.0)       # 1.94 cm
    section.bottom_margin = Pt(55.0)    # 1.94 cm
    section.left_margin = Pt(65.0)      # 2.29 cm
    section.right_margin = Pt(65.0)     # 2.29 cm
    
    # Normal Style: Times New Roman, 12pt, Black
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Header paragraphs
    p0 = doc.add_paragraph()
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(5)
    r0 = p0.add_run("BÁO CÁO CẬP NHẬT TIẾN ĐỘ VÀ BÁO CÁO KỸ THUẬT POC")
    r0.font.name = "Times New Roman"
    r0.font.size = Pt(16)
    r0.bold = True
    
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(3)
    r1 = p1.add_run("Trợ lý giọng nói đa phương thức (Voice & Vision) tích hợp\nCá nhân hóa ưu đãi & Đặt xe thông minh cho GreenSM")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(13)
    r1.bold = True
    
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(13)
    r2 = p2.add_run("Chương trình VRIC × GSM Smart City: Nhóm 4 - Mobility Assistant (Mã dự án: OlaSM)")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)
    r2.italic = True
    
    # Recipient & Authors section (matching BaoCao_YTuong_Nhom4_OlaSM.docx)
    p_kinhgui = doc.add_paragraph()
    p_kinhgui.paragraph_format.space_before = Pt(0)
    p_kinhgui.paragraph_format.space_after = Pt(2)
    r_kg = p_kinhgui.add_run("Kính gửi:")
    r_kg.font.name = "Times New Roman"
    r_kg.bold = True
    
    p_kg1 = doc.add_paragraph()
    p_kg1.paragraph_format.space_before = Pt(0)
    p_kg1.paragraph_format.space_after = Pt(3)
    p_kg1.paragraph_format.line_spacing = 1.25
    r_kg1_b = p_kg1.add_run("• ")
    r_kg1_b.bold = True
    r_kg1 = p_kg1.add_run("TS. Lê Duy Dũng — Trưởng Ban Giám Khảo & Điều phối Chương trình VRIC × GSM Smart City (VinUniversity)")
    r_kg1.font.name = "Times New Roman"
    
    p_kg2 = doc.add_paragraph()
    p_kg2.paragraph_format.space_before = Pt(0)
    p_kg2.paragraph_format.space_after = Pt(8)
    p_kg2.paragraph_format.line_spacing = 1.25
    r_kg2_b = p_kg2.add_run("• ")
    r_kg2_b.bold = True
    r_kg2 = p_kg2.add_run("Anh Lê Yên Thanh — Chuyên gia cố vấn công nghệ & Ban Tổ chức VRIC × GSM")
    r_kg2.font.name = "Times New Roman"
    
    p_tacgia = doc.add_paragraph()
    p_tacgia.paragraph_format.space_before = Pt(0)
    p_tacgia.paragraph_format.space_after = Pt(2)
    r_tg = p_tacgia.add_run("Đơn vị thực hiện báo cáo (Nhóm 4 - Mobility Assistant):")
    r_tg.font.name = "Times New Roman"
    r_tg.bold = True
    
    p_tg1 = doc.add_paragraph()
    p_tg1.paragraph_format.space_before = Pt(0)
    p_tg1.paragraph_format.space_after = Pt(2)
    p_tg1.paragraph_format.line_spacing = 1.25
    r_tg1 = p_tg1.add_run("1. Nguyễn Đức Nam Khánh — MSSV: 2A202601103 (Trưởng nhóm kỹ thuật, Phụ trách Hạ tầng, Streaming & Vision)")
    r_tg1.font.name = "Times New Roman"
    
    p_tg2 = doc.add_paragraph()
    p_tg2.paragraph_format.space_before = Pt(0)
    p_tg2.paragraph_format.space_after = Pt(8)
    p_tg2.paragraph_format.line_spacing = 1.25
    r_tg2 = p_tg2.add_run("2. Nguyễn Thị Phương — MSSV: 2A202601315 (Thành viên kỹ thuật, Phụ trách Workflow Agentic AI, COE & Guardrails)")
    r_tg2.font.name = "Times New Roman"
    
    p_links = doc.add_paragraph()
    p_links.paragraph_format.space_before = Pt(0)
    p_links.paragraph_format.space_after = Pt(12)
    p_links.paragraph_format.line_spacing = 1.25
    r_l1 = p_links.add_run("Mã nguồn công khai (Public GitHub): ")
    r_l1.bold = True
    r_l1.font.name = "Times New Roman"
    r_l2 = p_links.add_run("https://github.com/NamKhanh2128/OlaSM")
    r_l2.font.name = "Times New Roman"
    r_l2.font.color.rgb = RGBColor(0, 102, 204)
    r_l2.underline = True
    r_l3 = p_links.add_run(" | Demo Web Operator Console: ")
    r_l3.bold = True
    r_l3.font.name = "Times New Roman"
    r_l4 = p_links.add_run("http://localhost:5173/operator")
    r_l4.font.name = "Times New Roman"
    r_l4.italic = True
    
    # Helper functions
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(7)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(13)
        r.bold = True
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.bold = True
        r.italic = True
        return p

    def add_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.25
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
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.25
        
        r0 = p.add_run("• ")
        r0.bold = True
        r0.font.name = "Times New Roman"
        
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r1.font.name = "Times New Roman"
        
        r2 = p.add_run(text)
        r2.font.name = "Times New Roman"
        return p

    def add_formula(formula_text, sub_text=None):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(3) if sub_text else Pt(6)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(formula_text)
        r.font.name = "Cambria Math"
        r.font.size = Pt(11.5)
        r.bold = True
        r.italic = True
        
        if sub_text:
            p2 = doc.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2.paragraph_format.space_before = Pt(0)
            p2.paragraph_format.space_after = Pt(6)
            p2.paragraph_format.line_spacing = 1.15
            r2 = p2.add_run(sub_text)
            r2.font.name = "Cambria Math"
            r2.font.size = Pt(11)
            r2.italic = True

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
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            
            p = cell.paragraphs[0]
            p.alignment = col_alignments[c_idx]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10.5)
            r.bold = True
            
        # Data Rows
        for r_idx, r_data in enumerate(rows_data):
            row = table.rows[r_idx + 1]
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            
            for c_idx, val in enumerate(r_data):
                cell = row.cells[c_idx]
                cell.width = Inches(col_widths[c_idx])
                set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
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
                    r.font.size = Pt(10)
                    
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        return table

    # =========================================================================
    # PHẦN 1: CẬP NHẬT TIẾN ĐỘ PHASE 3 (NỬA CHẶNG ĐƯỜNG: TUẦN 1 - 3 / 6 TUẦN)
    # =========================================================================
    add_h1("1. Cập nhật tiến độ Phase 3: Đối soát Kế hoạch 6 Tuần và Kết quả Nửa chặng đường (Tuần 1 - 3)")
    
    add_h2("1.1. Khung thời gian và Mục tiêu Kỹ thuật Phase 3 (Tổng 6 Tuần: 14/09 – 25/10/2026)")
    add_p(
        "Theo đề cương chương trình VRIC × GSM Smart City, giai đoạn Phase 3 (Phát triển Kỹ thuật & Thực nghiệm POC) "
        "kéo dài đúng 6 tuần (từ ngày 14/09/2026 đến ngày 25/10/2026). Tính đến hôm nay (Chủ nhật, ngày 04/10/2026), "
        "dự án đã đi qua đúng 3 tuần (50% chặng đường Phase 3). Nửa đầu giai đoạn tập trung vào việc kiến tạo hạ tầng thoại "
        "thời gian thực và hiện thực hóa các thuật toán lõi phức tạp; nửa sau giai đoạn (Tuần 4 – Tuần 6) sẽ tập trung vào "
        "bàn làm việc điều phối tổng đài viên (HITL), kiểm thử tải lớn, đấu nối GSM Sandbox và nghiệm thu toàn diện Phase 3:"
    )
    add_bullet("Tuần 1 (14/09 – 20/09/2026 — Đã hoàn thành): ", "Khởi tạo kiến trúc Dual-Plane (FastAPI + LiveKit Worker); phân tích 3 điểm nghẽn nghiệp vụ tổng đài GreenSM; chuẩn hóa cơ sở dữ liệu bền vững (PostgreSQL / SQLite).")
    add_bullet("Tuần 2 (21/09 – 27/09/2026 — Đã hoàn thành): ", "Xây dựng luồng đàm thoại WebRTC LiveKit hai chiều; tích hợp Silero VAD (220ms); lập trình VietnameseAudioChunker ngắt ngữ pháp tiếng Việt (TTFA P95 đạt 1.41s); dựng LangGraph State Machine 6 bước và Guardrails an toàn 3 lớp.")
    add_bullet("Tuần 3 (28/09 – 04/10/2026 — Đã hoàn thành, Mốc báo cáo hiện tại): ", "Hoàn thành các thuật toán lõi then chốt: COE Soffer scoring; Dynamic Confidence Fusion ctrip (ECE = 0.0127); Multimodal Vision Grounding (Spatial OCR + Gemini VLM đạt 93% accuracy); tích hợp Goong Maps Việt Nam; Kiến trúc Ultra-Low-Cost siêu rẻ cho GreenSM mobile (~75 - 125 VNĐ/cuộc gọi); toàn bộ test suite đạt 720 / 720 tests xanh 100%.")
    add_bullet("Tuần 4 (05/10 – 11/10/2026 — Tuần tiếp theo): ", "Hoàn thiện bàn làm việc Web Operator Console (bàn giao HITL < 0.5s live WebRTC); mở rộng catalog 50+ điểm đón phức tạp Hà Nội; triển khai Tiered Cache 1.000 địa danh phổ biến.")
    add_bullet("Tuần 5 (12/10 – 18/10/2026 — 2 tuần tới): ", "Đánh giá chuyên sâu 100 kịch bản đàm thoại thực tế giọng 3 miền; stress-testing tải 50-100 cuộc gọi đồng thời; audit biên độ tiết kiệm ngân sách khuyến mãi của thuật toán COE.")
    add_bullet("Tuần 6 (19/10 – 25/10/2026 — Tuần về đích Phase 3): ", "Đấu nối GSM Sandbox API Live; mô phỏng điều phối đội xe điện VinFast (VF e34, VF 8) theo mức pin SoC%; đóng gói toàn diện sản phẩm POC; lập Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go).")
    add_bullet("Giai đoạn Hậu Phase 3 (Tuần 7 – 8: 26/10 – 08/11/2026 — Pilot Thực địa): ", "Thử nghiệm thực địa có kiểm soát với 50 tài xế xe điện GreenSM tại Quận Hoàn Kiếm và Cầu Giấy (Hà Nội); đo lường CSAT thực tế và bảo vệ chung kết.")

    add_h2("1.2. Kết quả đối soát kỹ thuật sau 3 tuần (Nửa chặng đường Phase 3)")
    add_p(
        "Nhờ phương pháp làm việc quyết liệt và khoa học, trong 3 tuần vừa qua, Nhóm 4 không chỉ hoàn thành 100% mục tiêu "
        "hạ tầng và streaming âm thanh mà còn hoàn thành sớm toàn bộ các bài toán thuật toán then chốt (COE, Confidence Fusion, "
        "Gemini Vision Grounding, Kiến trúc Siêu Rẻ). Hệ thống hiện vận hành mượt mà trên môi trường thử nghiệm với 720 / 720 tests xanh tuyệt đối:"
    )
    
    t1_headers = ["Phân hệ kỹ thuật", "Kết quả thực nghiệm kỹ thuật sau 3 tuần (14/09 – 04/10/2026)", "Đánh giá nghiệm thu"]
    t1_rows = [
        [
            "Voice Streaming Pipeline\n(Hoàn thành Tuần 2)",
            "WebRTC LiveKit hai chiều, Silero VAD (220ms), lập trình VietnameseAudioChunker ngắt ngữ pháp tiếng Việt; đo đạc thực tế TTFA p50: 1.26s, TTFA p95: 1.41s (vượt chỉ tiêu <= 1.5s).",
            "Hoàn thành xuất sắc\n(TTFA P95 <= 1.41s)"
        ],
        [
            "Conversational Offer Engine (COE)\n(Hoàn thành Tuần 3)",
            "Hoàn thành thuật toán tính điểm Soffer = 0.35 ChurnRisk + 0.25 PriceSensitivity + 0.40 CampaignFit; OfferProfileRepository kết nối PostgreSQL; giải thuật Cold-start giải quyết triệt để khách gọi lần đầu.",
            "Hoàn thành 100%\n(11/11 audit tests)"
        ],
        [
            "Dynamic Confidence Fusion (ctrip)\n(Hoàn thành Tuần 3)",
            "Lập trình công thức ctrip tái chuẩn hóa trọng số động khi thiếu ảnh; phân luồng 3 nhánh (Auto-book / Clarify / HITL); ECEService tối ưu Temperature Scaling đạt ECE = 0.0127 (chỉ tiêu <= 0.10).",
            "Hoàn thành xuất sắc\n(Calibrated ECE <= 0.02)"
        ],
        [
            "Multimodal Visual Grounding\n(Hoàn thành Tuần 3)",
            "Kết hợp Spatial OCR và Gemini 2.5 Flash Multimodal Vision; nhận diện chính xác cột hầm TTTM, sảnh chung cư và cửa đón sân bay, đạt độ chính xác 93.0% trên 5 cụm landmark phức tạp.",
            "Vượt chỉ tiêu 8.0%\n(Đạt 93.0% accuracy)"
        ],
        [
            "Bản đồ & Chuẩn hóa Địa danh VN\n(Hoàn thành Tuần 3)",
            "Xây dựng Gazetteer > 500 địa danh Hà Nội; tích hợp GoongMapsProvider và OSRM thay thế Mapbox, chuẩn hóa địa chỉ theo mô hình 2 cấp hành chính mới, đạt độ khớp 93.3%, tiết kiệm 80% chi phí.",
            "Hoàn thành 100%\n(Độ khớp 93.3%)"
        ],
        [
            "Kiến trúc Tối ưu Chi phí Siêu Rẻ\n(Hoàn thành Tuần 3)",
            "Triển khai phân tầng 4 lớp (Client Edge VAD -> Goong/OSRM -> GPT-4o-mini + Prompt Caching -> Streaming Chunker TTS); chi phí chỉ ~75 - 125 VNĐ / cuộc gọi (~0.003 - 0.005 USD), tiết kiệm ~92% chi phí.",
            "Đột phá kinh tế\n(Duy trì bền vững)"
        ],
        [
            "Kiểm thử Tự động & Guardrails\n(Xuyên suốt 3 tuần)",
            "Chạy mô phỏng 50 kịch bản E2E; kiểm thử an toàn 3 lớp chặn 100% Prompt Injection; test suite toàn dự án đạt 720 / 720 tests xanh 100% trong ~15.4 giây.",
            "Đạt chuẩn tuyệt đối\n(720 / 720 tests PASSED)"
        ]
    ]
    create_table(t1_headers, t1_rows, [2.2, 3.6, 1.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])
    
    add_h2("1.3. Vướng mắc và Điểm nghẽn kỹ thuật cần GSM & Hội đồng hỗ trợ trong 3 tuần còn lại")
    add_bullet(
        "Tài khoản GSM Sandbox API Live: ",
        "Hệ thống đã có client GSMSandboxClient chuẩn OpenAPI nhưng đang kết nối qua Mock Gateway. Để chuẩn bị nghiệm thu tại Tuần 6, nhóm cần Ban Công nghệ GSM cấp API Endpoint, API Key môi trường Sandbox/Staging để kiểm thử luồng giao dịch thật khép kín."
    )
    add_bullet(
        "Dữ liệu Telemetry thực tế từ đội xe điện VinFast: ",
        "Mô hình phân bổ xe theo mức pin (SoC %) và vị trí GPS hiện đang chạy trên mô phỏng. Cần kết nối luồng telemetry thực tế từ GSM/VinFast để chuẩn hóa thuật toán điều phối xe theo trạm sạc V-GREEN trong Tuần 6."
    )
    add_bullet(
        "Ngữ liệu cuộc gọi mẫu viễn thông ẩn danh: ",
        "Cần 30-50 đoạn ghi âm cuộc gọi tổng đài 1900 thực tế (đã che thông tin định danh cá nhân PII) kèm bóc băng chuẩn để đo lường Word Error Rate (WER) thực tế trên đường truyền viễn thông trong Tuần 5."
    )

    add_h2("1.4. Lộ trình triển khai chi tiết 3 Tuần còn lại của Phase 3 (Tuần 4 – Tuần 6: 05/10 – 25/10/2026)")
    add_bullet(
        "Tuần 4 (05/10 – 11/10/2026) — Operator Console Live WebRTC, Tiered Cache & Mở rộng Vision: ",
        "Hoàn thiện bàn làm việc Web Operator Console với độ trễ bàn giao cuộc gọi < 0.5s live WebRTC; mở rộng catalog điểm đón phức tạp lên 50+ địa điểm Hà Nội; triển khai bộ nhớ đệm Tiered Cache lưu 1.000 địa danh phổ biến."
    )
    add_bullet(
        "Tuần 5 (12/10 – 18/10/2026) — Đánh giá Chuyên sâu, Stress-Testing & Audit Chi phí Khuyến mại: ",
        "Chạy bộ kiểm thử 100 kịch bản thu âm thực tế (giọng Bắc, Trung, Nam có tạp âm); stress-test tải 50-100 cuộc gọi LiveKit WebRTC đồng thời; audit biên độ tiết kiệm ngân sách khuyến mãi của thuật toán COE."
    )
    add_bullet(
        "Tuần 6 (19/10 – 25/10/2026) — Đấu nối GSM Sandbox API, Mô phỏng Đội xe & Nghiệm thu Tổng kết Phase 3: ",
        "Đấu nối client GSMSandboxClient với Sandbox API của GSM; mô phỏng điều phối đội xe VinFast VF e34 và VF 8 theo mức pin SoC%; đóng gói toàn diện sản phẩm POC; lập Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go)."
    )
    add_bullet(
        "Giai đoạn Hậu Phase 3 (Tuần 7 – 8: 26/10 – 08/11/2026) — Thử nghiệm Thực địa Pilot 50 Xe GreenSM tại Hà Nội: ",
        "Triển khai thử nghiệm có kiểm soát với 50 tài xế xe điện GreenSM tại Quận Hoàn Kiếm và Cầu Giấy; đo lường tỷ lệ giảm cuộc gọi nhỡ (Lost calls), mức độ hài lòng khách hàng (CSAT) và bảo vệ chung kết."
    )

    # =========================================================================
    # PHẦN 2: BÁO CÁO KỸ THUẬT POC CHI TIẾT
    # =========================================================================
    add_h1("2. Báo cáo kỹ thuật POC chi tiết")
    
    add_h2("2.1. Đặt bài toán và Mục tiêu kỹ thuật")
    add_p(
        "Hệ thống OlaSM giải quyết trực diện 3 điểm đau cốt lõi trong quy trình tiếp cận khách hàng và vận hành tổng đài của GreenSM:"
    )
    add_bullet(
        "Khách hàng truyền thống (người lớn tuổi, quen gọi hotline): ",
        "Thường bỏ lỡ các mã giảm giá số do không sử dụng ứng dụng di động; gặp khó khăn khi mô tả vị trí đón ngõ ngách hoặc các điểm đón không có số nhà rõ ràng."
    )
    add_bullet(
        "Khách hàng trẻ bận rộn: ",
        "Ngại thao tác ứng dụng khi đang di chuyển; dễ bối rối tại các khu phức hợp lớn (tầng hầm trung tâm thương mại, sảnh chung cư, ga sân bay) nơi tín hiệu định vị GPS bị sai lệch nghiêm trọng."
    )
    add_bullet(
        "Ban vận hành GreenSM: ",
        "Ngân sách khuyến mại bị thất thoát do áp dụng tràn lan thiếu phân hóa; tổng đài viên chịu áp lực lớn vào giờ cao điểm dẫn đến tỷ lệ cuộc gọi nhỡ (lost calls) cao và chi phí nhân sự lớn."
    )
    add_p(
        "Mục tiêu kỹ thuật của OlaSM: Xây dựng một trợ lý AI đàm thoại đa phương thức (Voice & Vision) hỗ trợ đặt xe rảnh tay bằng tiếng Việt tự nhiên, "
        "tự động tối ưu hóa ưu đãi theo hành vi khách hàng nhằm tăng tỷ lệ chốt đơn, định vị chính xác điểm đón qua ảnh chụp thực tế "
        "với độ trễ phản hồi thời gian thực dưới 1.5s và thời gian đàm thoại (AHT) giảm từ 180s xuống dưới 60s."
    )

    add_h2("2.2. Dữ liệu đang sử dụng và Yêu cầu dữ liệu từ GSM")
    add_p("Các tập dữ liệu nội bộ nhóm đã xây dựng, chuẩn hóa và kiểm định thành công trong giai đoạn POC bao gồm:")
    add_bullet(
        "Gazetteer Hà Nội & ASR Alias Dictionary: ",
        "Hơn 500 địa danh, bệnh viện, trường đại học, khu đô thị lớn tại Hà Nội kèm bảng tra cứu phiên âm ASR hỗ trợ nhận diện các từ dễ nghe nhầm như 'Bình Yuni' -> VinUniversity, 'Hồ Cương' -> Hồ Gươm, 'Keng Nam' -> Keangnam Landmark 72."
    )
    add_bullet(
        "Complex Landmark Pickup Catalog: ",
        "Danh mục 18 tọa độ điểm đón chi tiết tại các cụm hạ tầng phức tạp: Cổng chính/Ký túc xá VinUni, Sảnh E1/E2 Times City, Trụ B3 hầm Vincom Bà Triệu, Cột 4 Ga quốc tế Tân Sơn Nhất, Cột 9 Ga T1 Nội Bài."
    )
    add_bullet(
        "Tập 50 kịch bản kiểm thử mô phỏng toàn diện (50-Scenario Simulation Suite): ",
        "30 kịch bản thoại chuẩn đa vùng miền, 8 kịch bản địa chỉ mơ hồ cần Clarify, 6 kịch bản định vị thị giác điểm đón phức tạp, 4 kịch bản tấn công Guardrails và 2 kịch bản môi trường nhiễu cực đoan."
    )
    
    add_p(
        "Để chuẩn bị cho giai đoạn kết nối sandbox và thử nghiệm Pilot thực địa, nhóm kính đề xuất GSM hỗ trợ cung cấp các hạng mục dữ liệu sau:"
    )
    
    t2_headers = ["Hạng mục dữ liệu yêu cầu", "Mục đích sử dụng trong hệ thống", "Định dạng / Quy cách yêu cầu", "Mức độ ưu tiên"]
    t2_rows = [
        [
            "Lịch sử chuyến xe ẩn danh\n(Trip Booking History)",
            "Huấn luyện và chuẩn hóa mô hình ChurnRisk và PriceSensitivity; đo lường độ co giãn nhu cầu theo phân khúc khách hàng.",
            "CSV / Parquet: [user_hash, time_slot, vehicle_type, est_fare, actual_fare, is_cancelled, promo_code]",
            "Cực kỳ cấp thiết\n(Tuần 2 - 3)"
        ],
        [
            "Danh mục chiến dịch ưu đãi\n(Promotion Catalog)",
            "Đấu nối trực tiếp vào CampaignFit scoring của COE; kiểm thử khả năng phân bổ ưu đãi linh hoạt theo thời gian thực.",
            "JSON / REST API: [promo_id, discount_type, value, min_fare, max_discount, target_user_tier, active_flag]",
            "Cực kỳ cấp thiết\n(Tuần 2)"
        ],
        [
            "Dữ liệu VinFast Telematics\n(SoC % & Charging Station)",
            "Định tuyến thông minh theo mức dung lượng pin xe điện và gợi ý trạm sạc V-GREEN trên lộ trình di chuyển của khách.",
            "JSON Stream / OpenAPI: [vehicle_vin, battery_pct, range_km, is_charging, current_gps]",
            "Ưu tiên cao\n(Tuần 3 - 4)"
        ],
        [
            "Ngữ liệu cuộc gọi mẫu viễn thông\n(Anonymized Audio Samples)",
            "Đo lường Word Error Rate (WER) thực tế trên đường truyền tổng đài; tinh chỉnh nhận dạng ngữ điệu và phương ngữ vùng miền.",
            "30-50 tệp WAV (đã che thông tin định danh PII), kèm văn bản bóc băng chuẩn.",
            "Ưu tiên cao\n(Tuần 3)"
        ],
        [
            "Tài khoản GSM Sandbox API Live\n(Booking, Fare & Dispatch)",
            "Kết nối kiểm thử luồng giao dịch khép kín từ lúc khách xác nhận giọng nói đến lúc sinh cuốc xe trên hệ sinh thái GSM thật.",
            "API Endpoint, API Key và tài liệu OpenAPI 3.0 cho môi trường Staging/Pilot.",
            "Cực kỳ cấp thiết\n(Tuần 3 - 5)"
        ]
    ]
    create_table(t2_headers, t2_rows, [1.8, 2.4, 2.0, 1.0], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_h2("2.3. Phương pháp nghiên cứu và Kiến trúc hệ thống")
    add_p(
        "Hệ thống OlaSM được kiến trúc theo mô hình Dual-Plane & 3 tầng phân định ranh giới chặt chẽ:"
    )
    add_bullet(
        "Tầng 1 - Đầu vào đa phương thức (Multimodal Ingestion): ",
        "Thu nhận luồng âm thanh 2 chiều qua WebRTC LiveKit, tích hợp bộ phát hiện tiếng nói Silero VAD (ngắt câu 220ms), đồng thời tiếp nhận hình ảnh điểm đón tải lên từ ứng dụng khách hàng."
    )
    add_bullet(
        "Tầng 2 - AI Core Service (The Brain): ",
        "Bao gồm chuỗi xử lý nhận dạng tiếng Việt Deepgram Nova-3, VietnameseAudioChunker tối ưu streaming, Agent điều phối LangGraph, dịch vụ phân bổ ưu đãi COE, dịch vụ hợp nhất độ tin cậy Confidence Fusion, Gemini Multimodal Vision Grounding và bộ Guardrails an toàn 3 tầng."
    )
    add_bullet(
        "Tầng 3 - Kênh người dùng & Tích hợp: ",
        "FastAPI Backend đóng vai trò Business Source of Truth, quản lý cơ sở dữ liệu PostgreSQL Supabase, bàn làm việc Operator Console cho nhân viên tổng đài và module GSMSandboxClient điều phối xe điện VinFast."
    )
    
    add_p("Chi tiết 3 công thức kỹ thuật nền tảng được hiện thực hóa chính xác theo Báo cáo Ý tưởng:")
    
    # Formula 1
    add_p(
        "Hệ thống tính toán chỉ số ưu đãi Soffer để lựa chọn mã giảm giá có xác suất chốt đơn cao nhất và bảo toàn hiệu quả chương trình:",
        bold_prefix="1. Thuật toán phân bổ ưu đãi hội thoại (Conversational Offer Engine): "
    )
    add_formula(
        "S_offer = α · ChurnRisk + β · PriceSensitivity + γ · CampaignFit",
        "(với hệ số chuẩn hóa: α = 0.35, β = 0.25, γ = 0.40)"
    )
    add_p(
        "Trong đó: ChurnRisk là xác suất khách hàng rời bỏ dịch vụ; PriceSensitivity là mức độ nhạy cảm về giá suy ra từ lịch sử cuốc xe; "
        "CampaignFit là độ phù hợp của mã ưu đãi với phân khúc người dùng. "
        "Dựa trên Soffer, AI phân loại mức ưu đãi: PREMIUM (>= 0.70), STANDARD (>= 0.45), SUGGEST (>= 0.20) hoặc không áp dụng nếu khách không nhạy cảm giá."
    )
    
    # Formula 2
    add_p(
        "Hệ thống tổng hợp độ tin cậy từ 4 nguồn không tương quan để đưa ra quyết định tự động hóa có chọn lọc:",
        bold_prefix="2. Cơ chế Dynamic Confidence Fusion & Selective Autonomy: "
    )
    add_formula(
        "c_trip = w₁ · p_STT + w₂ · p_intent + w₃ · p_addr + w₄ · p_vision"
    )
    add_formula(
        "c_trip ≥ τ_high : AUTO_BOOK   |   τ_low < c_trip < τ_high : CLARIFY   |   c_trip ≤ τ_low : HITL_HANDOFF",
        "(Ngưỡng chuẩn hóa: τ_high = 0.85, τ_low = 0.55)"
    )
    add_p(
        "Cơ chế tái chuẩn hóa trọng số động (Dynamic Weight Renormalization): Khi khách hàng không cung cấp ảnh, hệ thống tự động gán w₄ = 0 "
        "và tái chuẩn hóa w₁' + w₂' + w₃' = 1.0, bảo đảm điểm số phản ánh chính xác ngữ cảnh mà không bị suy hao giả tạo."
    )
    
    # Vision Grounding
    add_p(
        "Khi khách hàng gặp khó khăn mô tả điểm đón ngõ ngách hoặc hầm tòa nhà, ảnh chụp được đưa qua module GeminiVisionService. "
        "Hệ thống thực hiện Spatial OCR bóc tách biển báo, số hiệu cột trụ, kết hợp mô hình VLM Gemini 2.5 Flash để xác định điểm đón và trả về điểm tin cậy p_vision.",
        bold_prefix="3. Module Multimodal Visual Grounding: "
    )

    # Ultra-Low-Cost
    add_p(
        "Để đáp ứng yêu cầu vận hành quy mô lớn cho ứng dụng di động GreenSM với hàng triệu người dùng, nhóm đã lập trình kiến trúc "
        "phân tầng 4 lớp: (1) Silero VAD lọc khoảng lặng ngay tại Client; (2) Định tuyến địa chỉ ưu tiên Local Cache & Goong/OSRM "
        "giảm 80-84% chi phí bản đồ so với Google Maps/Mapbox; (3) Dynamic Prompt Caching kết hợp GPT-4o-mini / Gemini Flash giảm 92% "
        "chi phí token; (4) VietnameseAudioChunker chỉ tổng hợp audio cụm ngắn đầu tiên giúp giảm 78% chi phí TTS. "
        "Nhờ đó, tổng chi phí vận hành chỉ dao động từ 75 - 125 VNĐ / cuộc gọi (~0.003 - 0.005 USD), rẻ hơn 10 - 20 lần so với giải pháp thông thường "
        "và rẻ hơn 30 - 40 lần so với nhân sự tổng đài viên truyền thống.",
        bold_prefix="4. Kiến trúc Kỹ thuật Siêu Rẻ (Ultra-Low-Cost Architecture) cho App Mobile GreenSM: "
    )

    add_h2("2.4. Kết quả thực nghiệm và Đo lường chỉ số sau hoàn thiện")
    add_p(
        "Tại mốc Tuần 1, toàn bộ hệ thống đã được kiểm thử trên bộ công cụ "
        "OlaSM Benchmark Suite, 50-Scenario Simulation Suite và bộ kiểm thử hồi quy tự động. "
        "Dưới đây là bảng tổng hợp các chỉ số thực nghiệm kỹ thuật đo được thực tế:"
    )
    
    t3_headers = ["Chỉ số đo lường", "Mục tiêu cam kết (Đề cương)", "Kết quả thực tế đo được", "Đánh giá chất lượng"]
    t3_rows = [
        [
            "Độ trễ phản hồi âm thanh đầu\n(TTFA p50 / p95)",
            "p50 < 1.8s | p95 ≤ 1.5s",
            "p50: 1.26s | p95: 1.41s\n(Nhờ VietnameseAudioChunker)",
            "Vượt chỉ tiêu xuất sắc\n(P95 giảm mạnh từ 2.13s)"
        ],
        [
            "Tỷ lệ hoàn tất cuốc xe thành công\n(Voice E2E Task Completion)",
            "≥ 85.0% kịch bản chuẩn",
            "100.0% (50/50 kịch bản)\n(Simulation Suite kiểm chứng)",
            "Đạt chuẩn tuyệt đối\n(Hoàn tất trọn vẹn)"
        ],
        [
            "Thời gian hội thoại trung bình\n(Average Handle Time - AHT)",
            "Giảm từ ~180s xuống ≤ 90s",
            "~45s (Text) / ~50.2s (Voice)",
            "Tiết kiệm 72% thời gian\n(So với tổng đài viên)"
        ],
        [
            "Hiệu chỉnh độ tin cậy ECE\n(Expected Calibration Error)",
            "ECE ≤ 0.10 trên tập kiểm chuẩn",
            "ECE = 0.0127\n(Optimal Temperature Scaling)",
            "Đạt chuẩn xuất sắc\n(Triệt tiêu Overconfidence)"
        ],
        [
            "Độ chính xác phân loại ý định\n(Intent Classification F1)",
            "≥ 92.0%",
            "98.5%",
            "Vượt chỉ tiêu 6.5%"
        ],
        [
            "Khớp địa danh & Chuẩn hóa địa chỉ\n(Address Match Accuracy)",
            "≥ 90.0%",
            "93.3%",
            "Đạt chuẩn (Vượt 3.3%)"
        ],
        [
            "Độ chính xác định vị thị giác\n(Vision Grounding Accuracy)",
            "≥ 85.0% (khu vực phức tạp)",
            "93.0% (trên 5 cụm landmark)",
            "Đạt chuẩn xuất sắc"
        ],
        [
            "Tỷ lệ định tuyến chuyển người\n(HITL Handoff Routing)",
            "Định tuyến đúng 100% ngưỡng",
            "100.0% theo ngưỡng τ",
            "Hoàn hảo (< 0.5s bàn giao)"
        ],
        [
            "Phòng thủ an toàn Guardrails\n(Prompt Injection & Toxic Def)",
            "Chặn 100% tấn công đối thủ",
            "100.0% (4/4 kịch bản injection)",
            "Bảo vệ an toàn tuyệt đối"
        ],
        [
            "Kiểm thử tự động & Hồi quy\n(Automated Test Suite)",
            "100% pass toàn bộ test suites",
            "720 / 720 tests PASSED\n(Thời gian chạy: ~15.4s)",
            "Đạt tuyệt đối 100% xanh\n(Tăng thêm 26 bài test mới)"
        ],
        [
            "Kiểm tra công thức Blueprint\n(Audit Verification Suite)",
            "Khớp 100% tài liệu Báo cáo",
            "11 / 11 checks PASSED\n(Soffer, ctrip, Routing, Vision)",
            "Khớp chuẩn xác 100%"
        ]
    ]
    create_table(t3_headers, t3_rows, [2.0, 1.8, 1.8, 1.6], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_p("Phân rã thời gian xử lý trung bình trên một lượt đàm thoại (Tổng Turn Latency p50: 1.26s):")
    add_bullet("Voice Activity Detection (Silero VAD): ", "220ms — phát hiện điểm dừng nói tự nhiên của người dùng.")
    add_bullet("Speech-to-Text (Deepgram Nova-3 Streaming): ", "310ms — nhận diện và bóc băng âm thanh tiếng Việt theo thời gian thực.")
    add_bullet("LLM Core Agent & State Policy (GPT-4o-mini): ", "450ms — suy luận ngữ cảnh kết hợp streaming token.")
    add_bullet("Vietnamese Audio Chunker: ", "15ms — phát hiện dấu ngắt câu/mệnh đề và đẩy ngay buffer sang TTS.")
    add_bullet("Text-to-Speech (Gemini Flash TTS / Chirp): ", "265ms — tổng hợp audio cụm từ đầu tiên trả về luồng WebRTC LiveKit.")

    # =========================================================================
    # PHẦN 3: PHÂN BỔ CÔNG VIỆC VÀ KẾ HOẠCH TRIỂN KHAI
    # =========================================================================
    add_h1("3. Phân bổ công việc và Kế hoạch triển khai")
    
    add_h2("3.1. Danh sách thành viên và Phần việc đã hoàn thành tại Mốc Tuần 1")
    
    t4_headers = ["Họ và tên & MSSV", "Vai trò trọng tâm", "Phần việc cụ thể đã hoàn thành tại Mốc Tuần 1"]
    t4_rows = [
        [
            "Nguyễn Đức Nam Khánh\nMSSV: 2A202601103\n(Trưởng nhóm kỹ thuật)",
            "Hạ tầng hệ thống, Computer Vision, Voice Streaming & Client GSM",
            "• Thiết kế kiến trúc Dual-Plane (FastAPI + LiveKit WebRTC Worker).\n"
            "• Lập trình bộ tách cụm âm thanh tiếng Việt thời gian thực (VietnameseAudioChunker), ép TTFA P95 đạt 1.41s.\n"
            "• Hiện thực hóa Module Gemini Multimodal Vision Grounding (VLM + Spatial OCR).\n"
            "• Xây dựng GSMSandboxClient chuẩn OpenAPI tích hợp báo giá và điều xe điện VinFast.\n"
            "• Phát triển ECEService tối ưu hóa Temperature Scaling đưa ECE về 0.0127.\n"
            "• Thiết kế kiến trúc Ultra-Low-Cost tối ưu chi phí vận hành cho GreenSM Mobile App.\n"
            "• Thiết lập hạ tầng kiểm thử mô phỏng 50 kịch bản và xuất bản mã nguồn GitHub công khai."
        ],
        [
            "Nguyễn Thị Phương\nMSSV: 2A202601315\n(Thành viên kỹ thuật)",
            "Agentic AI Workflow, COE, Lưu trữ bền vững & Guardrails",
            "• Thiết kế và lập trình LangGraph State Machine luồng đàm thoại 6 bước hoàn chỉnh.\n"
            "• Xây dựng trọn vẹn Conversational Offer Engine (Soffer scoring, phân bổ ưu đãi).\n"
            "• Hiện thực hóa OfferProfileRepository kết nối PostgreSQL và giải thuật Cold-start khách mới.\n"
            "• Xây dựng bộ từ điển ASR Alias Gazetteer hơn 500 địa danh Hà Nội và Goong Maps Provider.\n"
            "• Lập trình bộ Guardrails an toàn 3 tầng và soạn thảo test suite đạt 720 / 720 tests xanh 100%."
        ]
    ]
    create_table(t4_headers, t4_rows, [2.0, 1.8, 3.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_h2("3.2. Phân công nhiệm vụ chi tiết 3 Tuần còn lại của Phase 3 (Tuần 4 – Tuần 6) và Pilot")
    
    t5_headers = ["Thành viên phụ trách", "Nội dung công việc trọng tâm", "Thời hạn hoàn thành", "Kết quả bàn giao"]
    t5_rows = [
        [
            "Nguyễn Thị Phương",
            "Hoàn thiện Goong Maps Provider, triển khai Tiered Cache 1.000 địa danh và tích hợp chính sách ưu đãi vào COE.",
            "11/10/2026 (Tuần 4)",
            "Module định vị Việt Nam siêu rẻ và bộ phân bổ ưu đãi theo phân khúc khách hàng."
        ],
        [
            "Nguyễn Đức Nam Khánh",
            "Mở rộng Vision Grounding lên 50+ điểm phức tạp; hoàn thiện bàn làm việc Web Operator Console tiếp nhận ca HITL qua WebRTC (< 0.5s).",
            "11/10/2026 (Tuần 4)",
            "Giao diện Operator Console Live WebRTC và catalog landmark chi tiết Hà Nội."
        ],
        [
            "Cả nhóm (Nam Khánh & Phương)",
            "Chạy stress-test 100 cuộc gọi thoại đồng thời, đánh giá toàn diện 100 kịch bản thực tế và kiểm chuẩn ECE.",
            "18/10/2026 (Tuần 5)",
            "Báo cáo Comprehensive Evaluation, biểu đồ ECE và phân tích ROI chi phí."
        ],
        [
            "Cả nhóm (Nam Khánh & Phương)",
            "Đấu nối GSM Sandbox API Live, hoàn thiện điều phối đội xe điện VinFast (VF e34, VF 8) theo mức pin SoC% và lập Báo cáo Nghiệm thu Tổng kết Phase 3.",
            "25/10/2026 (Tuần 6)",
            "Bản demo hoàn chỉnh end-to-end kết nối Sandbox GSM và Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go)."
        ],
        [
            "Cả nhóm (Nam Khánh & Phương)",
            "Triển khai thử nghiệm Pilot 50 xe GreenSM thực địa tại Hà Nội (Quận Hoàn Kiếm & Cầu Giấy), đo lường CSAT và bảo vệ chung kết.",
            "08/11/2026 (Tuần 7-8: Pilot)",
            "Báo cáo nghiệm thu Pilot thực địa, dữ liệu đo lường CSAT và Slide bảo vệ chung kết."
        ]
    ]
    create_table(t5_headers, t5_rows, [1.6, 2.8, 1.1, 1.7], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])

    # =========================================================================
    # KẾT LUẬN VÀ KIẾN NGHỊ
    # =========================================================================
    add_h1("4. Kết luận và Kiến nghị")
    add_p(
        "Phiên bản hiện tại của OlaSM đã chứng minh trọn vẹn tính khả thi kỹ thuật vượt trội, độ tin cậy của thuật toán "
        "và tiềm năng ứng dụng thực tiễn to lớn đối với hệ sinh thái xe điện thông minh GreenSM. Bằng việc hoàn thành xuất sắc "
        "toàn bộ các mục tiêu của Nửa đầu Phase 3 (Tuần 1 - 3), hệ thống đã sở hữu độ trễ phản hồi ấn tượng "
        "(TTFA P95 đạt 1.41s), thời gian đàm thoại rút ngắn 72%, độ hiệu chuẩn ECE đạt 0.0127, kiến trúc kỹ thuật siêu rẻ "
        "(~75 - 125 VNĐ / cuộc gọi) và bộ kiểm thử tự động 720 / 720 tests xanh tuyệt đối."
    )
    add_p(
        "Nhóm 4 kính đề nghị TS. Lê Duy Dũng, Anh Lê Yên Thanh và Ban Đề án xem xét: "
        "(1) Phê duyệt kết quả nghiệm thu Nửa đầu Phase 3 (Tuần 1 - 3) của Nhóm 4; "
        "(2) Hỗ trợ kết nối chính thức với Ban Công nghệ GreenSM để mở quyền truy cập tài khoản GSM Sandbox API Live "
        "và chia sẻ dữ liệu thực tế nhằm chuẩn bị cho việc nghiệm thu hoàn thiện tại Tuần 6 và giai đoạn thử nghiệm Pilot thực địa tại Hà Nội."
    )
    
    # Signatures
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(14)
    p_sign.paragraph_format.space_after = Pt(2)
    p_sign.paragraph_format.keep_with_next = True
    r_s = p_sign.add_run("Đại diện nhóm báo cáo:")
    r_s.bold = True
    
    p_sig1 = doc.add_paragraph()
    p_sig1.paragraph_format.space_before = Pt(0)
    p_sig1.paragraph_format.space_after = Pt(2)
    p_sig1.add_run("Nguyễn Đức Nam Khánh — MSSV: 2A202601103 (Trưởng nhóm kỹ thuật)")
    
    p_sig2 = doc.add_paragraph()
    p_sig2.paragraph_format.space_before = Pt(0)
    p_sig2.paragraph_format.space_after = Pt(4)
    p_sig2.add_run("Nguyễn Thị Phương — MSSV: 2A202601315 (Kỹ sư AI & Nghiệp vụ)")
    
    p_sig3 = doc.add_paragraph()
    p_sig3.paragraph_format.space_before = Pt(0)
    p_sig3.paragraph_format.space_after = Pt(12)
    r_s3 = p_sig3.add_run("Nhóm dự án OlaSM — VRIC × GSM Smart City (Nhóm 4: Mobility Assistant)\nNgày nộp: Chủ nhật, ngày 04/10/2026")
    r_s3.italic = True
    
    primary_path = "BaoCao_KyThuat_POC_Nhom4_OlaSM.docx"
    backup_path = "BaoCao_KyThuat_POC_Nhom4_OlaSM_updated.docx"
    try:
        doc.save(primary_path)
        print(f"Clean document successfully generated at: {primary_path}")
    except PermissionError:
        doc.save(backup_path)
        print(f"Primary file locked by Word. Successfully generated at: {backup_path}")

if __name__ == "__main__":
    build_document()
