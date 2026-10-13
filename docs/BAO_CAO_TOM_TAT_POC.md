# BÁO CÁO TÓM TẮT KỸ THUẬT POC (EXECUTIVE SUMMARY)
## Trợ lý Giọng nói Điều khiển App Mobile Green SM

- **Chương trình:** VRIC × GSM Smart City — Nhóm 4: Mobility Assistant  
- **Mã dự án:** OlaSM Voice Core  
- **Thời điểm báo cáo:** Thứ Hai, ngày 13/10/2026 (Cập nhật sau khi pivot — Tuần 4 / Phase 3)  
- **Đơn vị thực hiện:** Nguyễn Đức Nam Khánh (MSSV: 2A202601103) & Nguyễn Thị Phương (MSSV: 2A202601315)  
- **Hội đồng cố vấn & Ban giám khảo:** TS. Lê Duy Dũng (VinUniversity) & Anh Lê Yên Thanh (Cố vấn công nghệ VRIC × GSM)  
- **Mã nguồn GitHub:** [https://github.com/NamKhanh2128/OlaSM](https://github.com/NamKhanh2128/OlaSM)

---

## ⚠️ PIVOT SẢN PHẨM (2026-10-13)

**OlaSM không còn là web app đặt xe độc lập.**

Sau khi nghiên cứu kỹ ứng dụng Green SM và hệ sinh thái VinGroup, nhóm quyết định pivot toàn bộ sản phẩm:

> **OlaSM Voice Core là lớp voice assistant tích hợp bên trong app mobile Green SM, cho phép người dùng điều khiển toàn bộ app bằng giọng nói — từ mở màn hình, đặt xe, đến xem trạng thái chuyến.**

**Green SM là nền tảng gốc và nguồn sự thật duy nhất** cho: giá cước, booking, tài xế, thanh toán, trạng thái chuyến và chính sách.

---

## 1. Khung Thời Gian & Trạng Thái Tiến Độ Phase 3 (Sau Pivot)

Giai đoạn **Phase 3** (Phát triển Kỹ thuật & Thực nghiệm POC) có thời lượng đúng **6 tuần** (14/09/2026 – 25/10/2026):

- **Tuần 1–3 (ĐÃ HOÀN TẤT — Hướng cũ):** Xây dựng hạ tầng voice pipeline (LiveKit WebRTC), dialog state machine, guardrails 3 lớp, typed contract, STT/LLM/TTS pipeline tiếng Việt. TTFA P95 đạt 1.41s.
- **Pivot Tuần 4 (HIỆN TẠI):** Chuyển toàn bộ sang Green SM voice control layer. Typed AppAction contract đã implemented. AppContext validator, guardrails mở rộng, 8 app-control function tools, LiveKit app-control state sync đã xong.
- **Tuần 5–6 (KẾ HOẠCH):** Kết nối với Green SM APIs chính thức (EXTERNAL_BLOCKED), xây mobile SDK adapter, end-to-end integration test, demo trên test build Green SM.

---

## 2. Định Vị Sản Phẩm Mới

### Vấn đề giải quyết

Green SM đã có đầy đủ tính năng nhưng yêu cầu thao tác màn hình. Điều này tạo rào cản với người dùng lớn tuổi, người bận tay, và những ai cần trải nghiệm hands-free.

**Mục tiêu cốt lõi:** Người dùng Green SM chỉ cần nói — không cần chạm màn hình — để thực hiện bất kỳ thao tác nào trong app.

### Luồng trải nghiệm

```
Người dùng mở Green SM
       ↓
Bấm nút microphone trong app
       ↓
Nói: "Đặt Green SM Car từ đây đến sân bay Nội Bài"
       ↓
OlaSM Voice Core hiểu intent → resolve địa điểm → hỏi bổ sung nếu cần
       ↓
Green SM trả về giá, tài xế available, phương thức thanh toán
       ↓
OlaSM đọc lại thông tin → người dùng xác nhận bằng giọng
       ↓
Green SM tạo chuyến → OlaSM mở màn hình tracking
```

---

## 3. Bốn Trụ Cột Kỹ Thuật Nền Tảng

### 1. Voice Streaming Pipeline tiếng Việt thời gian thực (GIỮ LẠI)
- Kết nối WebRTC LiveKit hai chiều, tích hợp Silero VAD (ngắt câu 220ms tự nhiên)
- Module `VietnameseAudioChunker` đạt TTFA P95 = **1.41s** (vượt chuẩn ≤ 1.5s)
- Fully preserved sau khi pivot — là lớp transport của voice assistant mới

### 2. Typed AppAction Contract (MỚI — SAU PIVOT)
- 9 action kinds: NAVIGATE, GO_BACK, READ_SCREEN, SET_FIELD, SELECT_OPTION, SUBMIT, OPEN_HELP, REQUEST_OPEN_APP, END_ASSISTANT
- 5 risk levels: SAFE_NAVIGATION, USER_CONFIRMATION, APP_CONFIRMATION, BIOMETRIC_REQUIRED, OS_MANAGED
- Model chỉ được phát action trong allowlist — không emit code, URL, hay thao tác tự do
- Mọi SUBMIT đều yêu cầu xác nhận tường minh từ mobile app

### 3. Guardrails 3 Lớp (MỞ RỘNG)
- Input Rail: chặn 100% prompt injection
- App Action Rail: validate AppContext, kiểm tra capability_allowed, từ chối action không được host quảng bá
- Output Rail: xác nhận explicit confirmation trước mọi side effect
- PII redaction, không đưa thông tin thẻ/OTP vào LLM

### 4. AppContext ↔ AppAction Protocol (MỚI — SAU PIVOT)
- Mobile host gửi AppContext (màn hình hiện tại, available_actions, screen_summary) mỗi lượt
- OlaSM trả về danh sách AppAction có TTL (expires_in_seconds)
- LiveKit data channel publish app-control state trên topic `olasm.app_control.v1`
- AppActionResult được gửi lại sau khi mobile thực thi để agent biết kết quả

---

## 4. Bảng Đối Soát Chỉ Số Kỹ Thuật

| Chỉ số đo lường | Mục tiêu | Kết quả | Đánh giá |
|---|---|---|---|
| **Độ trễ âm thanh đầu (TTFA P95)** | ≤ 1.5s | **1.41s** | **Vượt chỉ tiêu** |
| **Typed AppAction contract** | Implemented | **Implemented** | **Đạt** |
| **Guardrail app action validation** | Implemented | **Implemented** | **Đạt** |
| **Green SM API integration** | Phase 1 target | **EXTERNAL_BLOCKED** | **Cần chốt với team GSM** |
| **Mobile SDK** | Phase 1 target | **EXTERNAL_BLOCKED** | **Phụ thuộc công nghệ app GSM** |

---

## 5. Những Gì Giữ Lại, Thay Đổi và Dừng Lại

| Nhóm | Hướng mới |
|---|---|
| Voice pipeline, LiveKit, state machine | **GIỮ** — là backend voice service |
| Booking confirmation, idempotency | **GIỮ** — áp dụng cho typed action |
| Transcript redaction, guardrails | **GIỮ & MỞ RỘNG** |
| Typed AppAction contract | **MỚI** — cốt lõi của hướng mới |
| App-control function tools (8 tools) | **MỚI** — navigate, go_back, read_screen, set_field... |
| AppContext/AppActionResult protocol | **MỚI** — mobile host communication |
| React web frontend | **DEPRECATED** làm sản phẩm; chỉ còn là test harness |
| Auth/bản đồ/pricing riêng của OlaSM | **DỪNG** — Green SM là nguồn sự thật |
| GSMSandboxClient | **CHỈ TEST** — thay bằng adapter API chính thức |
| Mock fare, mock driver, random ETA | **LOẠI** khỏi mọi demo tích hợp thật |

---

## 6. Điều Kiện Tiên Quyết (EXTERNAL_BLOCKED)

Để hoàn thành Phase 1, cần làm việc trực tiếp với team Green SM để có:
- API xác thực người dùng
- API tìm kiếm địa điểm (Place / Address lookup)
- API báo giá (Quote / Pricing)
- API tạo/hủy booking
- API trạng thái chuyến và ETA
- API khuyến mãi và phương thức thanh toán
- API hỗ trợ và handoff
- Sandbox, test account và webhook
- **Xác nhận công nghệ app mobile: native iOS/Android, Flutter hay React Native**

---

## 7. Lộ Trình Tiếp Theo

| Phase | Mục tiêu | Trạng thái |
|---|---|---|
| **Phase 1 MVP** | Voice-to-book cho Green SM Car: nói điểm đến → resolve → quote → confirm → booking → tracking | IN_PROGRESS (blocked by GSM APIs) |
| **Phase 2** | Trợ lý trong chuyến: tracking, hủy, handoff với context | ROADMAP |
| **Phase 3** | Mở rộng: Bike, Express, Food, đặt hộ | ROADMAP |

---

*OlaSM Voice Core — VRIC × GSM Smart City, Nhóm 4: Mobility Assistant*  
*Báo cáo này phản ánh hướng phát triển sau pivot ngày 13/10/2026*
