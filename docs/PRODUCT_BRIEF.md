# OlaSM Voice Core — Product Brief

**Cập nhật:** 2026-10-13  
**Trạng thái:** Active — hướng mới (Green SM Voice Control Layer)

---

## 1. Tầm nhìn sản phẩm

OlaSM là **lớp voice assistant tích hợp bên trong app mobile Green SM của VinGroup**.

Người dùng không cần tải thêm app, không cần mở website. Họ chỉ cần bấm nút microphone trong app Green SM đang dùng hàng ngày → nói yêu cầu bằng tiếng Việt tự nhiên → OlaSM hiểu → Green SM thực thi.

**Green SM là nền tảng gốc.** OlaSM không xây lại bản đồ, giá cước, thanh toán hay tracking — tất cả đều lấy từ Green SM.

---

## 2. Vấn đề cần giải quyết

Green SM hiện có đầy đủ tính năng nhưng yêu cầu người dùng biết thao tác màn hình. Điều này tạo ra rào cản với:

| Nhóm người dùng | Rào cản hiện tại |
|---|---|
| Người lớn tuổi, ít quen công nghệ | Không dùng được app, phải nhờ người khác |
| Người bận tay (đang mang hành lý, bế con) | Không thuận tiện chạm màn hình |
| Người trong tình huống cần tốc độ | App có nhiều bước thao tác |
| Người dùng có vấn đề về thị lực hoặc vận động | UI hiện tại chưa được tối ưu cho accessibility |

**Problem Statement:**  
Làm thế nào để người dùng Green SM có thể thực hiện mọi thao tác — từ đặt xe, xem trạng thái chuyến, đến xem khuyến mãi — chỉ bằng giọng nói, mà không cần chạm màn hình?

---

## 3. Định vị sản phẩm

| Khía cạnh | Mô tả |
|---|---|
| **Tên sản phẩm người dùng** | Trợ lý giọng nói Green SM |
| **Tên kỹ thuật** | OlaSM Voice Core |
| **Nền tảng** | Tích hợp vào app mobile Green SM (iOS / Android) |
| **Kênh tương tác** | Push-to-talk (bấm để nói) → Phase 2: always-on với wake word |
| **Ngôn ngữ MVP** | Tiếng Việt |
| **Nguồn dữ liệu** | Green SM chính thức (API) — OlaSM không có database nghiệp vụ riêng |

---

## 4. Người dùng mục tiêu

### Primary Persona — Người dùng cần voice
- Người lớn tuổi quen gọi hotline, chưa quen app
- Người bận tay hoặc đang di chuyển
- Người có nhu cầu accessibility cao

*Kịch bản điển hình:* Đang đi trong siêu thị, tay xách đồ, nói "Đặt xe về nhà" → Green SM xử lý và báo lại bằng giọng.

### Secondary Persona — Người dùng power user
- Muốn thao tác nhanh hơn bằng voice shortcut
- Thường xuyên dùng Green SM, muốn trải nghiệm hands-free

### Vai trò hệ thống
- **Mobile host (Green SM app):** thực thi action, cung cấp AppContext mỗi lượt
- **OlaSM Voice Core:** nhận giọng nói, hiểu intent, tạo typed action list
- **Tổng đài viên:** nhận handoff khi voice không xử lý được, kèm context đầy đủ

---

## 5. Phạm vi tính năng

### MVP (Phase 1) — Green SM Car
- Bấm mic → nói điểm đến → resolve địa điểm → lấy quote Green SM → đọc lại → xác nhận → tạo booking → mở tracking
- Hỗ trợ: Green SM Car, Green SM Mini
- Thanh toán: chọn từ danh sách app trả về
- Khuyến mãi: áp từ danh sách app trả về
- Fallback: chuyển text hoặc thao tác tay bất kỳ lúc nào

### Phase 2 — Trợ lý trong chuyến
- "Tài xế đang ở đâu?", "Bao lâu nữa tới?"
- "Đọc thông tin xe và tài xế"
- "Hủy chuyến" (với xác nhận biometric)
- "Tôi cần hỗ trợ" → handoff kèm context

### Phase 3 — Mở rộng dịch vụ
- Green SM Bike, Express, Food
- Đặt hộ (với kiểm soát danh tính riêng)
- Liên Tỉnh, đa điểm, theo lịch

---

## 6. Nguyên tắc thiết kế

1. **Green SM là nguồn sự thật duy nhất** — OlaSM không tự tính giá, không tự tạo booking
2. **Typed action only** — model chỉ được phát action trong allowlist; không emit code hay URL
3. **Xác nhận tường minh trước side effect** — booking, hủy, thanh toán luôn cần user confirm
4. **Fallback về text/UI bất kỳ lúc nào** — voice là lớp bổ sung, không thay thế hoàn toàn
5. **Microphone theo yêu cầu** — không nghe nền trong MVP
6. **Không đoán mò địa điểm** — khi mơ hồ, hỏi lại người dùng

---

## 7. Những gì OlaSM không làm

- ❌ Không xây app đặt xe riêng cạnh Green SM
- ❌ Không lưu dữ liệu booking riêng (không phải source of truth)
- ❌ Không tự tính giá hay tạo mock driver
- ❌ Không reverse-engineer app Green SM
- ❌ Không force-quit app trên iOS/Android
- ❌ Không nhận thông tin thẻ/OTP qua voice và đưa vào LLM

---

## 8. Phụ thuộc quan trọng (EXTERNAL_BLOCKED)

Toàn bộ Phase 1 phụ thuộc vào việc có được từ team Green SM:
- API xác thực người dùng
- API tìm kiếm địa điểm (Place / Address)
- API báo giá (Quote / Pricing)
- API tạo/hủy booking
- API trạng thái chuyến và ETA
- API khuyến mãi/thanh toán
- API hỗ trợ và handoff
- Sandbox, test account, webhook
- Xác nhận công nghệ app mobile: native iOS/Android, Flutter hay React Native

---

## 9. Lộ trình

| Phase | Mô tả | Điều kiện tiên quyết |
|---|---|---|
| **Phase 0** | Chốt API/SDK với team Green SM | Business agreement |
| **Phase 1** | MVP: voice-to-book cho Green SM Car | Green SM APIs |
| **Phase 2** | Trợ lý trong chuyến đi | Phase 1 stable |
| **Phase 3** | Mở rộng dịch vụ | Phase 2 stable |

---

## 10. Thành phần giữ lại từ codebase cũ

| Thành phần | Hướng mới |
|---|---|
| Voice pipeline, LiveKit, state machine | Giữ — là backend voice service |
| Booking confirmation, idempotency | Giữ — áp dụng cho typed action |
| Transcript redaction, guardrails | Giữ và tăng cường |
| React web frontend | Chỉ dùng làm test harness nội bộ |
| Auth, bản đồ, pricing riêng của OlaSM | Dừng phát triển |
| GSMSandboxClient | Chỉ dùng test; thay bằng adapter API chính thức |
| Mock fare, mock driver, random ETA | Loại khỏi mọi demo tích hợp thật |

---

*OlaSM Voice Core — VRIC × GSM Smart City, Nhóm 4: Mobility Assistant*
