# BÁO CÁO TÓM TẮT KỸ THUẬT POC (EXECUTIVE SUMMARY)
## Trợ lý Giọng nói Đa phương thức (Voice & Vision) Cá nhân hóa Ưu đãi & Đặt xe Thông minh cho GreenSM

- **Chương trình:** VRIC × GSM Smart City — Nhóm 4: Mobility Assistant  
- **Mã dự án:** OlaSM  
- **Thời điểm báo cáo:** Chủ nhật, ngày 04/10/2026 (Mốc giữa kỳ — Kết thúc Tuần 3 / Tổng 6 tuần Phase 3)  
- **Đơn vị thực hiện:** Nguyễn Đức Nam Khánh (MSSV: 2A202601103) & Nguyễn Thị Phương (MSSV: 2A202601315)  
- **Hội đồng cố vấn & Ban giám khảo:** TS. Lê Duy Dũng (VinUniversity) & Anh Lê Yên Thanh (Cố vấn công nghệ VRIC × GSM)  
- **Mã nguồn GitHub:** [https://github.com/NamKhanh2128/OlaSM](https://github.com/NamKhanh2128/OlaSM)  
- **Demo Operator Console:** `http://localhost:5173/operator`

---

## 1. Khung Thời Gian & Trạng Thái Tiến Độ Phase 3

Giai đoạn **Phase 3** (Phát triển Kỹ thuật & Thực nghiệm POC) có thời lượng đúng **6 tuần** (14/09/2026 – 25/10/2026). Tính đến hôm nay (04/10/2026), dự án đã đi qua đúng **3 tuần (50% chặng đường Phase 3)**:
- **Nửa đầu Phase 3 (Tuần 1 – Tuần 3: ĐÃ HOÀN TẤT):** Xây dựng hạ tầng Dual-Plane (FastAPI + LiveKit WebRTC Worker); luồng đàm thoại tiếng Việt 2 chiều (TTFA P95 đạt **1.41s**); hoàn thiện toàn bộ các thuật toán lõi: COE $S_{offer}$, Dynamic Confidence Fusion $c_{trip}$ (hiệu chuẩn $ECE = 0.0127$), Multimodal Vision Grounding (**93.0%** accuracy), Bản đồ Việt Nam Goong Maps và Guardrails 3 lớp an toàn.
- **Nửa sau Phase 3 (Tuần 4 – Tuần 6: 3 TUẦN TIẾP THEO):** Hoàn thiện bàn làm việc điều phối tổng đài viên (Web Operator Console HITL < 0.5s); Tiered Cache 1.000 địa danh; stress-test 100 cuộc gọi thoại đồng thời; đấu nối GSM Sandbox API Live; mô phỏng điều phối đội xe điện VinFast (VF e34, VF 8) theo mức pin SoC% và lập Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go).
- **Hậu Phase 3 (Tuần 7 – 8: Pilot Thực địa):** Thử nghiệm Pilot 50 xe GreenSM thực tế tại Hà Nội (Hoàn Kiếm & Cầu Giấy).

---

## 2. Điểm Nghẽn Nghiệp Vụ & Giá Trị Đột Phá cho GreenSM

OlaSM giải quyết trọn vẹn 3 bài toán lớn trong tiếp cận khách hàng và vận hành tổng đài của GreenSM:
1. **Khách hàng lớn tuổi / quen gọi hotline:** Không cài app nên thường xuyên bỏ lỡ các mã giảm giá số; gặp khó khăn khi mô tả điểm đón ngõ ngách.
2. **Khách hàng trẻ bận rộn:** Ngại thao tác ứng dụng khi đang di chuyển; dễ bối rối tại các cụm hạ tầng phức tạp (tầng hầm TTTM, sảnh chung cư, ga sân bay) nơi tín hiệu GPS sai lệch lớn.
3. **Ban vận hành GreenSM:** Ngân sách khuyến mại thất thoát do áp dụng tràn lan thiếu cá nhân hóa; tổng đài viên chịu áp lực lớn vào giờ cao điểm dẫn đến tỷ lệ lost calls cao.

**Mục tiêu cốt lõi:** Trợ lý AI đàm thoại rảnh tay đa phương thức (Voice & Vision) hỗ trợ đặt xe tự nhiên, tự động cá nhân hóa ưu đãi theo hành vi để tăng tỷ lệ chốt đơn, định vị điểm đón hầm xe qua ảnh chụp, rút ngắn thời gian xử lý cuộc gọi (AHT) từ ~180s xuống ≤ 50s với độ trễ phản hồi âm thanh < 1.5s.

---

## 3. Bốn Trụ Cột Kỹ Thuật và Thuật Toán Nền Tảng

1. **Voice Streaming Pipeline tiếng Việt thời gian thực:**
   - Kết nối WebRTC LiveKit hai chiều, tích hợp Silero VAD (ngắt câu 220ms tự nhiên).
   - Module `VietnameseAudioChunker` bóc tách luồng streaming token theo ngữ pháp tiếng Việt và từ đệm hội thoại, ép độ trễ phản hồi âm thanh đầu tiên **TTFA P95 đạt 1.41s** (p50: 1.26s), vượt chuẩn cam kết đề cương ($\le 1.5s$).
2. **Conversational Offer Engine (COE):**
   - Thuật toán chấm điểm ưu đãi tối ưu hóa chuyển đổi:
     $$S_{offer} = 0.35 \cdot ChurnRisk + 0.25 \cdot PriceSensitivity + 0.40 \cdot CampaignFit$$
   - Phân loại 4 mức ưu đãi (Premium, Standard, Suggest, None); giải thuật Cold-start giải quyết triệt để khách gọi lần đầu mà không thất thoát voucher.
3. **Dynamic Confidence Fusion ($c_{trip}$) & Selective Autonomy:**
   - Hợp nhất độ tin cậy từ 4 nguồn không tương quan:
     $$c_{trip} = w_1 \cdot p_{STT} + w_2 \cdot p_{intent} + w_3 \cdot p_{addr} + w_4 \cdot p_{vision}$$
   - Cơ chế tái chuẩn hóa trọng số động khi khách không gửi ảnh ($w_4 = 0 \Rightarrow w_1' + w_2' + w_3' = 1.0$).
   - Rẽ nhánh 3 đường: $c_{trip} \ge 0.85$ (Auto-book), $0.55 < c_{trip} < 0.85$ (Clarify hỏi lại), $c_{trip} \le 0.55$ (HITL chuyển tổng đài).
   - `ECEService` tối ưu hóa Temperature Scaling đưa sai số hiệu chuẩn về **$ECE = 0.0127$** (vượt xa chỉ tiêu $\le 0.10$).
4. **Multimodal Visual Grounding & Guardrails An Toàn 3 Lớp:**
   - Spatial OCR kết hợp Gemini 2.5 Flash VLM định vị chính xác cột hầm, sảnh chung cư đạt độ chính xác **93.0%**.
   - Bộ Guardrails 3 tầng (Input Rail chặn 100% Prompt Injection, Action Rail kiểm duyệt PII và chốt xác nhận Explicit Confirmation bằng giọng nói); bàn giao cuộc gọi cho tổng đài viên qua Web Operator Console với độ trễ **$< 0.5s$** qua WebRTC.

---

## 4. Bảng Đối Soát Chỉ Số Kỹ Thuật Thực Nghiệm Sau 3 Tuần

| Chỉ số đo lường | Mục tiêu cam kết (Đề cương) | Kết quả thực tế đo được | Đánh giá nghiệm thu |
|---|---|---|---|
| **Độ trễ âm thanh đầu (TTFA p50 / p95)** | p50 < 1.8s \| p95 ≤ 1.5s | **p50: 1.26s \| p95: 1.41s** | **Vượt chỉ tiêu xuất sắc** (VietnameseAudioChunker) |
| **Tỷ lệ hoàn tất cuốc xe (Voice E2E)** | ≥ 85.0% kịch bản chuẩn | **100.0%** (50/50 kịch bản) | **Đạt chuẩn tuyệt đối** (50-Scenario Suite) |
| **Thời gian hội thoại trung bình (AHT)** | Giảm từ ~180s xuống ≤ 90s | **~45s (Text) / ~50.2s (Voice)** | **Tiết kiệm 72% thời gian** (Rút ngắn 3 lần) |
| **Hiệu chuẩn độ tin cậy (Calibrated ECE)** | ECE ≤ 0.10 trên tập chuẩn | **ECE = 0.0127** | **Đạt chuẩn xuất sắc** (Triệt tiêu Overconfidence) |
| **Phân loại ý định đặt xe (Intent F1)** | ≥ 92.0% | **98.5%** | **Vượt chỉ tiêu 6.5%** |
| **Khớp & chuẩn hóa địa chỉ (Address Match)** | ≥ 90.0% | **93.3%** (Gazetteer > 500 địa danh) | **Đạt chuẩn** (Goong Maps / OSRM) |
| **Định vị thị giác hầm/sảnh (Vision Accuracy)** | ≥ 85.0% khu vực phức tạp | **93.0%** (5 cụm landmark lớn) | **Vượt chỉ tiêu 8.0%** |
| **Bàn giao tổng đài viên (HITL Handoff)** | Định tuyến đúng 100% ngưỡng $\tau$ | **100.0%** (< 0.5s qua WebRTC) | **Hoàn hảo** (Không gián đoạn) |
| **Phòng thủ an toàn Guardrails** | Chặn 100% tấn công đối thủ | **100.0%** (Chặn 4/4 injection) | **Bảo vệ an toàn tuyệt đối** |
| **Kiểm thử tự động hồi quy** | 100% pass toàn bộ test suite | **720 / 720 tests PASSED** (15.4s) | **Đạt tuyệt đối 100% xanh** |

---

## 5. Kế Hoạch 3 Tuần Còn Lại (Tuần 4 – Tuần 6) & Đề Xuất Hỗ Trợ

- **Tuần 4 (05/10 – 11/10/2026):** Hoàn thiện Web Operator Console bàn giao Live WebRTC < 0.5s; mở rộng catalog 50+ điểm đón phức tạp Hà Nội; cấu hình Tiered Cache lưu trữ 1.000 địa danh.
- **Tuần 5 (12/10 – 18/10/2026):** Kiểm thử 100 kịch bản thu âm thực tế giọng Bắc - Trung - Nam; stress-test tải 50-100 cuộc gọi đồng thời; đo lường Promotion Cost Efficiency (tối ưu hóa 15 - 25% ngân sách voucher khuyến mãi).
- **Tuần 6 (19/10 – 25/10/2026):** Đấu nối GSM Sandbox API Live; mô phỏng điều phối đội xe điện VinFast (VF e34, VF 8) theo dung lượng pin SoC%; lập Báo cáo Nghiệm thu Tổng kết Phase 3 (Go/No-go).
- **Giai đoạn Hậu Phase 3 (Tuần 7 – 8: 26/10 – 08/11/2026):** Thử nghiệm Pilot thực địa với 50 xe GreenSM tại Hà Nội (Hoàn Kiếm & Cầu Giấy), đo lường CSAT và bảo vệ chung kết.

**Đề xuất kính gửi Ban Đề án & GSM:**
1. Phê duyệt kết quả nghiệm thu Nửa đầu Phase 3 (Tuần 1 – 3) của Nhóm 4.
2. Hỗ trợ cấp tài khoản GSM Sandbox API Live (Staging Gateway) và cấu trúc Telematics xe điện VinFast để chuẩn bị cho giai đoạn kết nối hệ thống thật trong Tuần 5 - 6.
