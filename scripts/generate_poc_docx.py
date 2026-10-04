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
    p_kg1.add_run("Thầy Lê Duy Dũng (Viện Kỹ thuật & Khoa học Máy tính - VinUniversity)")
    
    p_kg2 = doc.add_paragraph()
    p_kg2.paragraph_format.space_before = Pt(0)
    p_kg2.paragraph_format.space_after = Pt(3)
    p_kg2.paragraph_format.line_spacing = 1.25
    r_kg2_b = p_kg2.add_run("• ")
    r_kg2_b.bold = True
    p_kg2.add_run("Anh Lê Yên Thanh - [VSF] Director of Public Transport")

    p_kg3 = doc.add_paragraph()
    p_kg3.paragraph_format.space_before = Pt(0)
    p_kg3.paragraph_format.space_after = Pt(4)
    p_kg3.paragraph_format.line_spacing = 1.25
    r_kg3_b = p_kg3.add_run("• ")
    r_kg3_b.bold = True
    p_kg3.add_run("Ban Quản trị Đề án Hợp tác VRIC × GSM Smart City")
    
    p_auth = doc.add_paragraph()
    p_auth.paragraph_format.space_before = Pt(2)
    p_auth.paragraph_format.space_after = Pt(4)
    p_auth.paragraph_format.line_spacing = 1.2
    r_auth_lbl = p_auth.add_run("Người báo cáo: ")
    r_auth_lbl.bold = True
    p_auth.add_run("Nhóm dự án OlaSM (Nhóm 4 - Mobility Assistant)\n")
    p_auth.add_run("Nguyễn Đức Nam Khánh (MSSV: 2A202601103) - Trưởng nhóm kỹ thuật\n")
    p_auth.add_run("Nguyễn Thị Phương (MSSV: 2A202601315) - Kỹ sư AI & Nghiệp vụ\n")
    p_auth.add_run("Mã nguồn dự án: https://github.com/NamKhanh2128/alosm-backend\n")
    p_auth.add_run("Thời điểm nộp: Chủ nhật, ngày 04/10/2026")
    
    p_intro = doc.add_paragraph()
    p_intro.paragraph_format.space_before = Pt(4)
    p_intro.paragraph_format.space_after = Pt(6)
    p_intro.paragraph_format.line_spacing = 1.2
    p_intro.add_run(
        "Thực hiện theo chỉ đạo sau buổi sync-up ngày 29/09/2026 của Ban Đề án và TS. Lê Duy Dũng, "
        "Nhóm 4 kính gửi báo cáo cập nhật tiến độ POC Phase 3 và báo cáo kỹ thuật chi tiết của hệ thống OlaSM. "
        "Báo cáo trình bày đầy đủ các kết quả thực nghiệm kỹ thuật đã đạt được so với mục tiêu đề cương, các vướng mắc kỹ thuật, "
        "nhu cầu dữ liệu phối hợp cụ thể từ GreenSM và kế hoạch phân công công việc giai đoạn tiếp theo."
    )
    
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
    add_h1("1. Cập nhật tiến độ Phase 3 (POC Progress Update)")
    
    add_h2("1.1. Mục tiêu và Kết quả so với kế hoạch Phase 3")
    add_p(
        "Mục tiêu Phase 3 theo lộ trình tập trung vào việc hiện thực hóa 3 module kỹ thuật cốt lõi: "
        "Conversational Offer Engine (COE), Dynamic Confidence Fusion và Multimodal Visual Grounding, "
        "kết hợp hoàn thiện luồng đàm thoại đặt xe end-to-end trên hạ tầng WebRTC LiveKit và bộ Guardrails an toàn 3 tầng. "
        "Dưới đây là bảng đối chiếu chi tiết giữa mục tiêu kế hoạch và kết quả thực nghiệm thực tế:"
    )
    
    t1_headers = ["Hạng mục mục tiêu Phase 3", "Kết quả thực nghiệm thực tế", "Đánh giá"]
    t1_rows = [
        [
            "Conversational Offer Engine (COE)\nCá nhân hóa ưu đãi theo hành vi",
            "Đã xây dựng mô hình tính điểm Soffer chuẩn hóa; tạo migration DB 3 bảng; tích hợp tool cho Agent; tự động gợi ý mã có xác suất chốt đơn cao nhất qua giọng nói.",
            "Đạt yêu cầu\n(11/11 tests audit)"
        ],
        [
            "Dynamic Confidence Fusion &\nSelective Autonomy",
            "Đã lập trình công thức ctrip với cơ chế tái chuẩn hóa trọng số động (khi không có ảnh); xây dựng bộ định tuyến 3 nhánh (tự động, hỏi lại, chuyển người); tích hợp hàm tính ECE.",
            "Đạt yêu cầu\n(Định tuyến chuẩn 100%)"
        ],
        [
            "Multimodal Visual Grounding\nĐịnh vị điểm đón qua ảnh chụp",
            "Đã xây dựng pipeline phân tích không gian (Spatial OCR + Landmark Catalog) cho 5 điểm đón phức tạp (Vincom B3, Tân Sơn Nhất, Nội Bài, Times City, Landmark 81).",
            "Đạt yêu cầu\n(Catalog 5 mẫu điểm đón)"
        ],
        [
            "Voice Agent Streaming Pipeline\n(STT -> LLM -> TTS)",
            "Hoàn thành luồng WebRTC LiveKit: Deepgram Nova-3 + GPT-4.1-mini + Gemini Flash TTS. Độ trễ trung vị p50 đạt 1.51s; độ trễ mạng đuôi P95 đạt 2.13s (mục tiêu đề cương <= 1.2s - 2.0s).",
            "Gần đạt\n(Cần tối ưu thêm P95)"
        ],
        [
            "Operator HITL Dashboard\nBàn giao tổng đài viên < 0.5s",
            "Backend đóng gói Context Snapshot tức thì (< 0.5s); giao diện bàn làm việc Operator Console kết nối WebRTC Room và WebSocket state sync để tiếp quản đàm thoại mượt mà.",
            "Đạt yêu cầu\n(Hoàn tất Backend & UI)"
        ],
        [
            "Kiểm soát an toàn 3 tầng\n(3-Layer Security Guardrails)",
            "Bộ quét regex chống prompt injection, bộ phân loại ranh giới nghiệp vụ (Out-of-Scope) và chốt chặn quyền thực thi Tool (Policy Gate) bảo đảm an toàn hệ thống.",
            "Đạt xuất sắc\n(Bảo vệ 100% ranh giới)"
        ]
    ]
    create_table(t1_headers, t1_rows, [2.2, 3.6, 1.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])
    
    add_h2("1.2. Vướng mắc và Điểm nghẽn kỹ thuật")
    add_bullet(
        "Thiếu dữ liệu hành vi người dùng thực tế: ",
        "Toàn bộ cấu trúc cơ sở dữ liệu và thuật toán chấm điểm ChurnRisk, PriceSensitivity đã hoàn thiện nhưng đang vận hành trên dữ liệu seed mô phỏng. Cần dữ liệu lịch sử chuyến thực tế từ GSM để kiểm chuẩn trọng số bằng mô hình học máy."
    )
    add_bullet(
        "Độ trễ phản hồi âm thanh đầu tiên (TTFA P95): ",
        "Chỉ số p50 đạt 1.51s đáp ứng tiêu chuẩn SLA (< 2.0s), nhưng p95 còn ở mức 2.13s do độ trễ khởi động tiến trình LiveKit và bộ tổng hợp giọng nói. Nhóm đang thử nghiệm cơ chế fast sentence chunking để giảm thêm 300-400ms."
    )
    add_bullet(
        "Visual Grounding chưa kết nối VLM multimodal thương mại: ",
        "Pipeline không gian đang vận hành bằng Spatial OCR rule-based kết hợp Gazetteer; chưa kết nối trực tiếp Gemini Vision API thực tế nhằm bảo đảm tốc độ phản hồi cực nhanh dưới 200ms trong môi trường thử nghiệm."
    )

    add_h2("1.3. Kế hoạch tiếp theo (Tuần 4 - 5)")
    add_bullet(
        "Tuần 4 (05/10 - 11/10): ",
        "Đấu nối OfferProfileRepository thực tế từ PostgreSQL Supabase; hoàn thiện giao diện Operator Console; áp dụng streaming partial TTS kéo P95 về dưới 1.5s; kiểm thử mở rộng độ chính xác gợi ý ưu đãi trên kịch bản hội thoại."
    )
    add_bullet(
        "Tuần 5 (12/10 - 18/10): ",
        "Kết nối cổng GSM Sandbox API (Booking, Fare, Promotion); chạy 20-30 ca thực nghiệm thực địa đa vùng miền; thu thập dữ liệu tính toán chỉ số hiệu chỉnh ECE thực tế; hoàn thiện báo cáo nghiệm thu Go/No-go."
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
        "với độ trễ phản hồi thời gian thực dưới 2.0s và thời gian đàm thoại (AHT) giảm từ 180s xuống dưới 90s."
    )

    add_h2("2.2. Dữ liệu đang sử dụng và Yêu cầu dữ liệu từ GSM")
    add_p("Các tập dữ liệu nội bộ nhóm đã xây dựng và kiểm định trong giai đoạn POC bao gồm:")
    add_bullet(
        "Gazetteer Hà Nội: ",
        "Hơn 500 địa danh, bệnh viện, trường đại học, khu đô thị lớn tại Hà Nội kèm bảng tra cứu phiên âm ASR (ASR Alias) hỗ trợ nhận diện các từ dễ nghe nhầm như 'Bình Yuni' -> VinUniversity, 'Hồ Cương' -> Hồ Gươm, 'Keng Nam' -> Keangnam."
    )
    add_bullet(
        "Landmark Pickup Points: ",
        "Danh mục 18 tọa độ điểm đón chi tiết tại các cụm hạ tầng phức tạp: Cổng chính/Ký túc xá VinUni, Sảnh E1/E2 Times City, Trụ B3 hầm Vincom Bà Triệu, Cột 4 Ga quốc tế Nội Bài."
    )
    add_bullet(
        "Tập kiểm thử Workflow Eval Cases: ",
        "Bộ dữ liệu 6 kịch bản hội thoại chuẩn hóa (Đặt xe nhanh, Đổi điểm đón, Đổi điểm đến, Đổi loại xe, Câu hỏi ngoài phạm vi, Chuyển giao tổng đài viên) cùng 23 trường hợp biên (Edge Cases)."
    )
    
    add_p(
        "Để chuẩn bị cho giai đoạn thử nghiệm thực tế (Pilot), nhóm kính đề xuất GSM hỗ trợ cung cấp các hạng mục dữ liệu cụ thể sau:"
    )
    
    t2_headers = ["Hạng mục dữ liệu yêu cầu", "Mục đích sử dụng trong hệ thống", "Định dạng / Quy cách yêu cầu", "Mức độ ưu tiên"]
    t2_rows = [
        [
            "Lịch sử chuyến xe ẩn danh\n(Trip Booking History)",
            "Huấn luyện và chuẩn hóa mô hình ChurnRisk và PriceSensitivity; đo lường độ co giãn nhu cầu theo phân khúc khách hàng.",
            "CSV / Parquet: [user_hash, time_slot, vehicle_type, est_fare, actual_fare, is_cancelled, promo_code]",
            "Cực kỳ cấp thiết\n(Tuần 4)"
        ],
        [
            "Danh mục chiến dịch ưu đãi\n(Promotion Catalog)",
            "Đấu nối trực tiếp vào CampaignFit scoring của COE; kiểm thử khả năng phân bổ ưu đãi linh hoạt theo thời gian thực.",
            "JSON / REST API: [promo_id, discount_type, value, min_fare, max_discount, target_user_tier, active_flag]",
            "Cực kỳ cấp thiết\n(Tuần 4)"
        ],
        [
            "Ngữ liệu cuộc gọi mẫu\n(Anonymized Audio Samples)",
            "Đo lường Word Error Rate (WER) thực tế trên đường truyền viễn thông; tinh chỉnh nhận dạng địa danh vùng miền.",
            "30-50 tệp WAV (đã che thông tin định danh PII cá nhân), kèm văn bản bóc băng chuẩn.",
            "Ưu tiên cao\n(Tuần 5)"
        ],
        [
            "Gazetteer TP.HCM & Đà Nẵng\n(Pickup Point POI Catalog)",
            "Mở rộng phạm vi hoạt động của trợ lý thoại sang hai thành phố trọng điểm của GreenSM.",
            "JSON / GeoJSON danh sách địa danh, tòa nhà, bệnh viện và tọa độ điểm đón trả xe thực tế.",
            "Ưu tiên cao\n(Tuần 5)"
        ],
        [
            "Tài khoản GSM Sandbox API\n(Booking, Fare & Dispatch)",
            "Kiểm thử tích hợp luồng giao dịch khép kín từ lúc khách xác nhận giọng nói đến lúc sinh cuốc xe trên hệ thống GSM.",
            "API Endpoint, API Key và tài liệu OpenAPI 3.0 cho môi trường Dev/Staging.",
            "Cực kỳ cấp thiết\n(Tuần 5)"
        ]
    ]
    create_table(t2_headers, t2_rows, [1.8, 2.4, 2.0, 1.0], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_h2("2.3. Phương pháp nghiên cứu và Kiến trúc hệ thống")
    add_p(
        "Hệ thống OlaSM được kiến trúc theo mô hình 3 tầng phân định ranh giới chặt chẽ:"
    )
    add_bullet(
        "Tầng 1 - Đầu vào đa phương thức (Multimodal Ingestion): ",
        "Thu nhận luồng âm thanh 2 chiều qua WebRTC LiveKit, tích hợp bộ phát hiện tiếng nói Silero VAD (ngắt câu 250ms), đồng thời tiếp nhận hình ảnh điểm đón tải lên từ trình duyệt của khách hàng."
    )
    add_bullet(
        "Tầng 2 - AI Core Service (The Brain): ",
        "Bao gồm chuỗi xử lý nhận dạng tiếng Việt Deepgram Nova-3, Agent điều phối LangGraph, dịch vụ phân bổ ưu đãi COE, dịch vụ hợp nhất độ tin cậy Confidence Fusion, bộ trích xuất không gian Visual Grounding và bộ Guardrails an toàn 3 tầng."
    )
    add_bullet(
        "Tầng 3 - Kênh người dùng & Tích hợp: ",
        "FastAPI Backend đóng vai trò Business Source of Truth, quản lý cơ sở dữ liệu PostgreSQL Supabase, bàn làm việc Operator Console cho nhân viên tổng đài và kết nối GSM Sandbox."
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
        "Trong đó: ChurnRisk là xác suất khách hàng rời bỏ dịch vụ nếu không chốt được chuyến; PriceSensitivity là mức độ nhạy cảm về giá suy ra từ lịch sử hủy chuyến; "
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
        "Khi khách hàng gặp khó khăn mô tả điểm đón ngõ ngách hoặc hầm tòa nhà, ảnh chụp được đưa qua module Visual Grounding. "
        "Hệ thống thực hiện Spatial OCR bóc tách biển báo, số hiệu cột trụ, kết hợp tra cứu tọa độ không gian trong Gazetteer để xác định điểm đón và trả về điểm tin cậy p_vision.",
        bold_prefix="3. Module Multimodal Visual Grounding: "
    )

    add_h2("2.4. Kết quả thực nghiệm và Đo lường chỉ số")
    add_p(
        "Toàn bộ hệ thống đã được kiểm thử trên bộ công cụ tự động OlaSM Benchmark Suite và bộ kiểm thử hồi quy toàn diện. "
        "Dưới đây là bảng tổng hợp các chỉ số thực nghiệm kỹ thuật đo được so với mục tiêu đề cương:"
    )
    
    t3_headers = ["Chỉ số đo lường", "Mục tiêu cam kết (Đề cương)", "Kết quả thực tế đo được", "Đánh giá chất lượng"]
    t3_rows = [
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
            "Thời gian hội thoại trung bình\n(Average Handle Time - AHT)",
            "Giảm từ ~180s xuống ≤ 90s",
            "~45s (Text) / ~68s (Voice)",
            "Đạt (Tiết kiệm 62% thời gian)"
        ],
        [
            "Độ trễ phản hồi âm thanh đầu\n(TTFA p50 / p95)",
            "p50 < 1.8s | p95 ≤ 1.2s - 2.0s",
            "p50: 1.51s | p95: 2.13s",
            "Gần đạt (p50 đạt, p95 vượt 0.13s)"
        ],
        [
            "Tỷ lệ hoàn tất cuốc xe thành công\n(Voice E2E Task Completion)",
            "≥ 85.0% kịch bản chuẩn",
            "91.2% (trên 50 cuộc gọi mô phỏng)",
            "Đạt chuẩn xuất sắc"
        ],
        [
            "Kiểm thử tự động & Hồi quy\n(Automated Test Suite)",
            "100% pass toàn bộ test suites",
            "694 / 694 tests PASSED\n(Thời gian chạy: 21.46s)",
            "Đạt tuyệt đối 100% xanh"
        ],
        [
            "Kiểm tra công thức Blueprint\n(Audit Verification Suite)",
            "Khớp 100% tài liệu Báo cáo",
            "11 / 11 checks PASSED\n(Soffer, ctrip, Routing, Vision)",
            "Khớp chuẩn xác 100%"
        ]
    ]
    create_table(t3_headers, t3_rows, [2.0, 1.8, 1.8, 1.6], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_p("Phân rã thời gian xử lý trung bình trên một lượt đàm thoại (Tổng Turn Latency p50: 1.51s):")
    add_bullet("Voice Activity Detection (Silero VAD): ", "250ms — phát hiện điểm dừng nói tự nhiên của người dùng.")
    add_bullet("Speech-to-Text (Deepgram Nova-3 Streaming): ", "320ms — nhận diện và bóc băng âm thanh tiếng Việt theo thời gian thực.")
    add_bullet("LLM Core Agent & State Policy (GPT-4.1-mini): ", "610ms — suy luận ngữ cảnh, kích hoạt Guardrails và chọn Tool nghiệp vụ.")
    add_bullet("Text-to-Speech (Gemini Flash TTS / Chirp): ", "330ms — tổng hợp audio câu đầu tiên trả về luồng WebRTC LiveKit.")

    add_h2("2.5. Hạn chế kỹ thuật hiện tại")
    add_bullet(
        "Độ trễ mạng đuôi TTFA P95: ",
        "Trung vị p50 đạt 1.51s rất tốt, tuy nhiên mốc p95 (2.13s) còn bị ảnh hưởng khi gặp hiện tượng cold-start hoặc đường truyền mạng chập chờn. Nhóm đang chuyển sang mô hình streaming partial audio để khắc phục triệt để."
    )
    add_bullet(
        "Phạm vi dữ liệu địa danh: ",
        "Hiện tại hệ thống được tối ưu hóa sâu nhất cho khu vực Hà Nội; dữ liệu khu vực TP.HCM và các tỉnh lân cận hiện mới dừng ở mức địa giới hành chính, cần bổ sung POI chi tiết."
    )
    add_bullet(
        "Mô hình hóa hành vi người dùng: ",
        "Các chỉ số ChurnRisk và PriceSensitivity hiện đang chạy trên mô hình heuristic giả lập; cần tập dữ liệu thực tế của GreenSM để chuyển dịch sang mô hình học máy Gradient Boosting."
    )

    # =========================================================================
    # PHẦN 3: PHÂN BỔ CÔNG VIỆC VÀ KẾ HOẠCH TIẾP THEO
    # =========================================================================
    add_h1("3. Phân bổ công việc và Kế hoạch triển khai")
    
    add_h2("3.1. Danh sách thành viên và Phần việc đã hoàn thành trong POC")
    
    t4_headers = ["Họ và tên & MSSV", "Vai trò trọng tâm", "Phần việc cụ thể đã đảm nhận trong POC"]
    t4_rows = [
        [
            "Nguyễn Đức Nam Khánh\nMSSV: 2A202601103\n(Trưởng nhóm kỹ thuật)",
            "Hạ tầng hệ thống, Computer Vision &\nVoice Streaming Pipeline",
            "• Thiết kế và dựng toàn bộ hạ tầng Dual-Plane (FastAPI + LiveKit WebRTC Worker).\n"
            "• Hiện thực hóa Module Multimodal Visual Grounding (Spatial OCR + Landmark matching).\n"
            "• Lập trình dịch vụ Dynamic Confidence Fusion (ctrip) và hàm kiểm chuẩn ECE.\n"
            "• Thiết lập hệ thống cơ sở dữ liệu bền vững (Alembic migrations) và Docker Staging.\n"
            "• Xây dựng bộ công cụ đo lường tự động (Benchmark Suite) kiểm soát độ trễ và chất lượng đàm thoại."
        ],
        [
            "Nguyễn Thị Phương\nMSSV: 2A202601315\n(Thành viên)",
            "Agentic AI Workflow, COE &\nBusiness Logic Engineering",
            "• Thiết kế và lập trình LangGraph State Machine cho luồng đàm thoại 6 bước hoàn chỉnh.\n"
            "• Xây dựng trọn vẹn Conversational Offer Engine (Soffer scoring, phân hạng ưu đãi).\n"
            "• Tinh chỉnh Prompt System Persona theo phong cách giao tiếp tổng đài GreenSM.\n"
            "• Xây dựng bộ từ điển ASR Alias Gazetteer hơn 500 địa danh Hà Nội.\n"
            "• Soạn thảo bộ 11 bài kiểm thử Blueprint Audit và chạy kiểm chứng 694 test cases toàn hệ thống."
        ]
    ]
    create_table(t4_headers, t4_rows, [2.0, 1.8, 3.4], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_h2("3.2. Phân công nhiệm vụ giai đoạn tiếp theo (Tuần 4 - 5)")
    
    t5_headers = ["Thành viên phụ trách", "Nội dung công việc trọng tâm", "Thời hạn hoàn thành", "Kết quả bàn giao"]
    t5_rows = [
        [
            "Nguyễn Đức Nam Khánh",
            "Tối ưu hóa Streaming Audio Pipeline: áp dụng Fast Sentence Chunking ép độ trễ TTFA P95 <= 1.5s.",
            "11/10/2026",
            "Bản cập nhật LiveKit Worker với TTFA P95 đạt chuẩn."
        ],
        [
            "Nguyễn Đức Nam Khánh",
            "Kết nối kiểm thử GSM Sandbox API (Booking, Fare, Dispatch) trên môi trường Staging.",
            "14/10/2026",
            "Module tích hợp API GSM hoạt động ổn định trên Staging."
        ],
        [
            "Nguyễn Thị Phương",
            "Đấu nối OfferProfileRepository với PostgreSQL Supabase; xây dựng cơ chế Cold-start người dùng mới.",
            "11/10/2026",
            "Dịch vụ Offer Engine lưu trữ trạng thái người dùng bền vững trên DB."
        ],
        [
            "Nguyễn Thị Phương",
            "Đo lường Offer Conversion Rate và độ chính xác phân bổ ưu đãi trên bộ 50 kịch bản cuộc gọi mô phỏng.",
            "15/10/2026",
            "Báo cáo định lượng về hiệu quả chuyển đổi và độ nhạy ưu đãi."
        ],
        [
            "Cả nhóm (Nam Khánh & Phương)",
            "Chạy thử nghiệm thực địa end-to-end (Voice + Visual Grounding + Handoff) và hoàn thiện Báo cáo Go/No-go.",
            "18/10/2026",
            "Tài liệu kỹ thuật hoàn chỉnh, Video demo thực tế và Slide trình bày chung kết."
        ]
    ]
    create_table(t5_headers, t5_rows, [1.6, 2.8, 1.1, 1.7], [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])

    # =========================================================================
    # KẾT LUẬN VÀ KIẾN NGHỊ
    # =========================================================================
    add_h1("4. Kết luận và Kiến nghị")
    add_p(
        "Phiên bản POC hiện tại của OlaSM đã chứng minh đầy đủ tính khả thi kỹ thuật, độ tin cậy của thuật toán và tiềm năng "
        "thực tiễn to lớn đối với hệ sinh thái xe điện thông minh GreenSM. Với thời gian đàm thoại rút ngắn 62%, kiến trúc chịu lỗi cao, "
        "bộ kiểm thử tự động 694 bài test xanh 100% và khả năng cá nhân hóa ưu đãi vượt trội, hệ thống sẵn sàng bước vào giai đoạn thử nghiệm Pilot."
    )
    add_p(
        "Nhóm 4 kính đề nghị Thầy Lê Duy Dũng, Anh Lê Yên Thanh và Ban Đề án xem xét: "
        "(1) Phê duyệt kết quả nghiệm thu POC Phase 3 của Nhóm 4; "
        "(2) Hỗ trợ kết nối với Ban Công nghệ GreenSM để mở quyền truy cập tài khoản GSM Sandbox API và tập dữ liệu mẫu phục vụ hoàn thiện sản phẩm."
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
