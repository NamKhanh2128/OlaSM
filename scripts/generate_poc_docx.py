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
    # PHẦN 1: CẬP NHẬT TIẾN ĐỘ POC (ĐÚNG DUNG LƯỢNG KHOẢNG 1/2 TRANG)
    # =========================================================================
    add_h1("1. Cập nhật tiến độ Phase 3 và Hoàn thiện sớm Tuần 4 - 5 (Progress Update)")
    
    add_h2("1.1. Mục tiêu và Kết quả đột phá so với kế hoạch Phase 3")
    add_p(
        "Nhận thức tầm quan trọng của giai đoạn nghiệm thu POC để làm căn cứ kết nối dữ liệu chuyên sâu với GreenSM, "
        "Nhóm 4 đã chủ động đẩy mạnh nghiên cứu, hoàn thành vượt mức mục tiêu Phase 3 và hiện thực hóa toàn bộ các "
        "hạng mục cốt lõi dự kiến cho Tuần 4 và Tuần 5 ngay trong phiên bản nộp hiện tại. Hệ thống đã đạt trạng thái "
        "vận hành đồng bộ toàn diện trên cả giao thức thoại WebRTC LiveKit, phân tích hình ảnh Gemini Multimodal Vision, "
        "cơ sở dữ liệu bền vững và client kết nối chuẩn GSM OpenAPI Sandbox:"
    )
    
    t1_headers = ["Hạng mục kiến trúc hoàn thiện", "Kết quả thực nghiệm kỹ thuật thực tế", "Đánh giá chất lượng"]
    t1_rows = [
        [
            "Conversational Offer Engine (COE) &\nOfferProfileRepository (Tuần 4)",
            "Hoàn thiện thuật toán chấm điểm Soffer; xây dựng OfferProfileRepository kết nối PostgreSQL Supabase; tích hợp giải thuật Cold-start giải quyết triệt để trường hợp người dùng mới gọi lần đầu.",
            "Hoàn thành xuất sắc\n(11/11 audit tests)"
        ],
        [
            "Dynamic Confidence Fusion (ctrip) &\nECEService Calibration (Tuần 5)",
            "Lập trình công thức ctrip có cơ chế tái chuẩn hóa động; định tuyến 3 nhánh (Auto-book / Clarify / Handoff); tích hợp ECEService tối ưu Temperature Scaling đạt ECE = 0.0127 (chỉ tiêu <= 0.10).",
            "Hoàn thành xuất sắc\n(Calibrated ECE <= 0.02)"
        ],
        [
            "Streaming Audio Chunker (Tuần 4)\n(VietnameseAudioChunker)",
            "Xây dựng bộ tách luồng âm thanh thông minh dựa trên dấu ngắt ngữ pháp tiếng Việt và từ đệm hội thoại; bảo vệ từ viết tắt/số điện thoại; ép độ trễ TTFA p50 xuống 1.26s và TTFA P95 xuống 1.41s (đạt chuẩn <= 1.5s).",
            "Vượt chỉ tiêu\n(TTFA P95 <= 1.41s)"
        ],
        [
            "GSM Sandbox OpenAPI Client (Tuần 5)\n(GSMSandboxClient)",
            "Xây dựng client kết nối GSM Dispatching chuẩn OpenAPI (Quote, Booking, Driver Status, Cancel); tích hợp đầy đủ thông số đội xe điện VinFast (VF e34, VF 5 Plus, VF 8) và mô phỏng tài xế thời gian thực.",
            "Hoàn thành xuất sắc\n(Mock & Live Gateway)"
        ],
        [
            "Gemini Multimodal Vision Grounding\n(GeminiVisionService)",
            "Mở rộng pipeline thị giác kết hợp Gemini 2.5 Flash Multimodal Vision và Spatial OCR; định vị chính xác cột hầm TTTM, sảnh chung cư và cửa đón sân bay, cung cấp điểm tin cậy p_vision vào ctrip.",
            "Hoàn thành xuất sắc\n(5 cụm landmark phức tạp)"
        ],
        [
            "Mô phỏng 50 kịch bản E2E &\nKiểm thử tự động hồi quy",
            "Chạy kiểm thử 50 kịch bản thực tế (đặt xe chuẩn, địa chỉ mơ hồ, định vị ảnh, tấn công Prompt Injection, nhiễu âm thanh); đạt 100% hoàn thành cuốc xe; test suite toàn hệ thống 704 / 704 tests xanh 100%.",
            "Đạt chuẩn tuyệt đối\n(704 / 704 tests PASSED)"
        ]
    ]
    create_table(t1_headers, t1_rows, [2.3, 3.5, 1.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])
    
    add_h2("1.2. Vướng mắc và Điểm nghẽn kỹ thuật còn tồn đọng")
    add_bullet(
        "Thiếu dữ liệu telemetry thực tế từ đội xe điện VinFast: ",
        "Hệ thống đã có mô hình phân bổ xe theo mức pin (SoC %) và vị trí GPS, nhưng hiện đang chạy trên mô phỏng. Cần kết nối dữ liệu telemetry thực tế từ GSM để tối ưu hóa quãng đường đón khách và trạm sạc V-GREEN."
    )
    add_bullet(
        "Môi trường hạ tầng tổng đài SIP Trunking viễn thông: ",
        "Hiện tại hệ thống hoạt động hoàn hảo trên WebRTC (Web/App Voice Call). Để triển khai trực tiếp vào số hotline tổng đài truyền thống 1900 của GreenSM, nhóm cần hỗ trợ hạ tầng SIP Trunking viễn thông (FreeSWITCH/Asterisk)."
    )
    add_bullet(
        "Dữ liệu phân khúc hội viên khách hàng thực tế: ",
        "Cần tập dữ liệu phân loại khách hàng thân thiết từ hệ sinh thái Vingroup (VinClub, Vinhomes, VinFast) để kiểm chứng mức độ co giãn nhu cầu và tối ưu ngân sách chiến dịch ưu đãi."
    )

    add_h2("1.3. Lộ trình nâng cao Phase 4 & Phase 5 (Tuần 6 - 8): Thử nghiệm Pilot thực địa")
    add_bullet(
        "Tuần 6 (19/10 - 25/10) — Tích hợp Telematics Xe điện VinFast: ",
        "Kết nối dữ liệu mức pin (SoC %) và trạng thái sạc từ xe VinFast VF e34/VF 8 qua GSM API Gateway; tự động ưu tiên điều phối xe có dung lượng pin tối ưu cho chuyến đi dài và gợi ý trạm sạc V-GREEN trên lộ trình."
    )
    add_bullet(
        "Tuần 7 (26/10 - 01/11) — On-device Edge Voice Agent trên Xe VinFast: ",
        "Đóng gói phiên bản SLM giọng nói siêu nhẹ chạy trực tiếp trên màn hình giải trí xe VinFast (Android Automotive OS); hỗ trợ tài xế nhận chuyến và xác nhận điểm đón khách bằng khẩu lệnh rảnh tay an toàn."
    )
    add_bullet(
        "Tuần 8 (02/11 - 08/11) — Thử nghiệm thực địa Pilot 50 Xe GreenSM tại Hà Nội: ",
        "Triển khai thử nghiệm có kiểm soát với 50 tài xế GreenSM tại 2 quận trọng điểm (Hoàn Kiếm và Cầu Giấy); đo lường mức độ hài lòng khách hàng (CSAT), thời gian đàm thoại thực tế và tỷ lệ giảm tải cuộc gọi tổng đài viên."
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
        "Để chuẩn bị cho giai đoạn thử nghiệm Pilot thực địa (Tuần 6 - 8), nhóm kính đề xuất GSM hỗ trợ cung cấp các hạng mục dữ liệu sau:"
    )
    
    t2_headers = ["Hạng mục dữ liệu yêu cầu", "Mục đích sử dụng trong hệ thống", "Định dạng / Quy cách yêu cầu", "Mức độ ưu tiên"]
    t2_rows = [
        [
            "Lịch sử chuyến xe ẩn danh\n(Trip Booking History)",
            "Huấn luyện và chuẩn hóa mô hình ChurnRisk và PriceSensitivity; đo lường độ co giãn nhu cầu theo phân khúc khách hàng.",
            "CSV / Parquet: [user_hash, time_slot, vehicle_type, est_fare, actual_fare, is_cancelled, promo_code]",
            "Cực kỳ cấp thiết\n(Tuần 6)"
        ],
        [
            "Danh mục chiến dịch ưu đãi\n(Promotion Catalog)",
            "Đấu nối trực tiếp vào CampaignFit scoring của COE; kiểm thử khả năng phân bổ ưu đãi linh hoạt theo thời gian thực.",
            "JSON / REST API: [promo_id, discount_type, value, min_fare, max_discount, target_user_tier, active_flag]",
            "Cực kỳ cấp thiết\n(Tuần 6)"
        ],
        [
            "Dữ liệu VinFast Telematics\n(SoC % & Charging Station)",
            "Định tuyến thông minh theo mức dung lượng pin xe điện và gợi ý trạm sạc V-GREEN trên lộ trình di chuyển của khách.",
            "JSON Stream / OpenAPI: [vehicle_vin, battery_pct, range_km, is_charging, current_gps]",
            "Ưu tiên cao\n(Tuần 6)"
        ],
        [
            "Ngữ liệu cuộc gọi mẫu viễn thông\n(Anonymized Audio Samples)",
            "Đo lường Word Error Rate (WER) thực tế trên đường truyền tổng đài; tinh chỉnh nhận dạng ngữ điệu và phương ngữ vùng miền.",
            "30-50 tệp WAV (đã che thông tin định danh PII), kèm văn bản bóc băng chuẩn.",
            "Ưu tiên cao\n(Tuần 7)"
        ],
        [
            "Tài khoản GSM Sandbox API Live\n(Booking, Fare & Dispatch)",
            "Kết nối kiểm thử luồng giao dịch khép kín từ lúc khách xác nhận giọng nói đến lúc sinh cuốc xe trên hệ sinh thái GSM thật.",
            "API Endpoint, API Key và tài liệu OpenAPI 3.0 cho môi trường Staging/Pilot.",
            "Cực kỳ cấp thiết\n(Tuần 6)"
        ]
    ]
    create_table(t2_headers, t2_rows, [1.8, 2.4, 2.0, 1.0], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_h2("2.3. Phương pháp nghiên cứu và Kiến trúc hệ thống")
    add_p(
        "Hệ thống OlaSM được kiến trúc theo mô hình Dual-Plane & 3 tầng phân định ranh giới chặt chẽ:"
    )
    add_bullet(
        "Tầng 1 - Đầu vào đa phương thức (Multimodal Ingestion): ",
        "Thu nhận luồng âm thanh 2 chiều qua WebRTC LiveKit, tích hợp bộ phát hiện tiếng nói Silero VAD (ngắt câu 250ms), đồng thời tiếp nhận hình ảnh điểm đón tải lên từ trình duyệt của khách hàng."
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
        "Hệ thống tính toán chỉ số ưu tiên ưu đãi Soffer để lựa chọn mã giảm giá có xác suất chốt đơn cao nhất và bảo toàn hiệu quả chương trình:",
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

    add_h2("2.4. Kết quả thực nghiệm và Đo lường chỉ số sau hoàn thiện")
    add_p(
        "Sau khi hoàn thiện trọn vẹn các module Tuần 4 và Tuần 5, toàn bộ hệ thống đã được kiểm thử trên bộ công cụ "
        "OlaSM Benchmark Suite, 50-Scenario Simulation Suite và bộ kiểm thử hồi quy toàn diện. "
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
            "704 / 704 tests PASSED\n(Thời gian chạy: 14.73s)",
            "Đạt tuyệt đối 100% xanh\n(Tăng thêm 10 bài test mới)"
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
    add_bullet("LLM Core Agent & State Policy (GPT-4.1-mini): ", "450ms — suy luận ngữ cảnh kết hợp streaming token.")
    add_bullet("Vietnamese Audio Chunker: ", "15ms — phát hiện dấu ngắt câu/mệnh đề và đẩy ngay buffer sang TTS.")
    add_bullet("Text-to-Speech (Gemini Flash TTS / Chirp): ", "265ms — tổng hợp audio cụm từ đầu tiên trả về luồng WebRTC LiveKit.")

    # =========================================================================
    # PHẦN 3: PHÂN BỔ CÔNG VIỆC VÀ KẾ HOẠCH TIẾP THEO
    # =========================================================================
    add_h1("3. Phân bổ công việc và Kế hoạch triển khai")
    
    add_h2("3.1. Danh sách thành viên và Phần việc đã hoàn thành trong POC")
    
    t4_headers = ["Họ và tên & MSSV", "Vai trò trọng tâm", "Phần việc cụ thể đã hoàn thành trong POC"]
    t4_rows = [
        [
            "Nguyễn Đức Nam Khánh\nMSSV: 2A202601103\n(Trưởng nhóm kỹ thuật)",
            "Hạ tầng hệ thống, Computer Vision, Voice Streaming & Client GSM",
            "• Thiết kế kiến trúc Dual-Plane (FastAPI + LiveKit WebRTC Worker).\n"
            "• Lập trình bộ tách cụm âm thanh tiếng Việt thời gian thực (VietnameseAudioChunker), ép TTFA P95 đạt 1.41s.\n"
            "• Hiện thực hóa Module Gemini Multimodal Vision Grounding (VLM + Spatial OCR).\n"
            "• Xây dựng GSMSandboxClient chuẩn OpenAPI tích hợp báo giá và điều xe điện VinFast.\n"
            "• Phát triển ECEService tối ưu hóa Temperature Scaling đưa ECE về 0.0127.\n"
            "• Thiết lập hạ tầng kiểm thử mô phỏng 50 kịch bản và xuất bản mã nguồn GitHub công khai."
        ],
        [
            "Nguyễn Thị Phương\nMSSV: 2A202601315\n(Thành viên kỹ thuật)",
            "Agentic AI Workflow, COE, Lưu trữ bền vững & Guardrails",
            "• Thiết kế và lập trình LangGraph State Machine luồng đàm thoại 6 bước hoàn chỉnh.\n"
            "• Xây dựng trọn vẹn Conversational Offer Engine (Soffer scoring, phân bổ ưu đãi).\n"
            "• Hiện thực hóa OfferProfileRepository kết nối PostgreSQL và giải thuật Cold-start khách mới.\n"
            "• Xây dựng bộ từ điển ASR Alias Gazetteer hơn 500 địa danh Hà Nội.\n"
            "• Lập trình bộ Guardrails an toàn 3 tầng và soạn thảo test suite đạt 704 / 704 tests xanh 100%."
        ]
    ]
    create_table(t4_headers, t4_rows, [2.0, 1.8, 3.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_h2("3.2. Phân công nhiệm vụ giai đoạn tiếp theo (Phase 4 & 5: Tuần 6 - 8)")
    
    t5_headers = ["Thành viên phụ trách", "Nội dung công việc trọng tâm", "Thời hạn hoàn thành", "Kết quả bàn giao"]
    t5_rows = [
        [
            "Nguyễn Đức Nam Khánh",
            "Tích hợp dữ liệu VinFast Telematics (SoC %, OBD-II) và thuật toán định tuyến theo trạm sạc V-GREEN.",
            "25/10/2026",
            "Module điều xe thông minh theo mức pin xe điện hoạt động trên Staging."
        ],
        [
            "Nguyễn Đức Nam Khánh",
            "Đóng gói On-device Edge Voice Agent chạy trên màn hình giải trí xe VinFast (Android Automotive OS).",
            "01/11/2026",
            "Bản build APK/SDK cho màn hình xe điện VinFast hỗ trợ đàm thoại rảnh tay."
        ],
        [
            "Nguyễn Thị Phương",
            "Kết nối hệ thống xác thực hội viên VinClub/Vingroup và phân hóa chính sách ưu đãi tự động.",
            "25/10/2026",
            "Module định danh hội viên VinClub tích hợp trực tiếp vào thuật toán COE."
        ],
        [
            "Nguyễn Thị Phương",
            "Xây dựng kịch bản kiểm thử thực địa và phối hợp đào tạo tổng đài viên điều phối HITL.",
            "01/11/2026",
            "Bộ tài liệu hướng dẫn vận hành bàn làm việc Operator Console cho nhân viên GSM."
        ],
        [
            "Cả nhóm (Nam Khánh & Phương)",
            "Triển khai thử nghiệm Pilot 50 xe GreenSM thực địa tại Hà Nội (Quận Hoàn Kiếm & Cầu Giấy), đo lường CSAT.",
            "08/11/2026",
            "Báo cáo nghiệm thu Pilot thực địa, dữ liệu đo lường CSAT và Slide bảo vệ chung kết."
        ]
    ]
    create_table(t5_headers, t5_rows, [1.6, 2.8, 1.1, 1.7], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])

    # =========================================================================
    # KẾT LUẬN VÀ KIẾN NGHỊ
    # =========================================================================
    add_h1("4. Kết luận và Kiến nghị")
    add_p(
        "Phiên bản POC hiện tại của OlaSM đã chứng minh trọn vẹn tính khả thi kỹ thuật vượt trội, độ tin cậy của thuật toán "
        "và tiềm năng ứng dụng thực tiễn to lớn đối với hệ sinh thái xe điện thông minh GreenSM. Bằng việc hoàn thành sớm "
        "toàn bộ các mục tiêu của Tuần 4 và Tuần 5, hệ thống đã sở hữu độ trễ phản hồi ấn tượng (TTFA P95 đạt 1.41s), "
        "thời gian đàm thoại rút ngắn 72%, độ hiệu chuẩn ECE đạt 0.0127 và bộ kiểm thử tự động 704 / 704 tests xanh tuyệt đối."
    )
    add_p(
        "Nhóm 4 kính đề nghị TS. Lê Duy Dũng, Anh Lê Yên Thanh và Ban Đề án xem xét: "
        "(1) Phê duyệt kết quả nghiệm thu POC của Nhóm 4; "
        "(2) Hỗ trợ kết nối chính thức với Ban Công nghệ GreenSM để mở quyền truy cập tài khoản GSM Sandbox API Live "
        "và chia sẻ dữ liệu thực tế nhằm chuẩn bị cho giai đoạn thử nghiệm Pilot thực địa tại Hà Nội."
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
