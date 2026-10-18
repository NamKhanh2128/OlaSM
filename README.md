# OlaSM Voice Core

> **Trợ lý giọng nói tích hợp trong ứng dụng Green SM** — điều khiển toàn bộ app mobile Green SM bằng giọng nói, từ mở màn hình đến xác nhận booking.

OlaSM không phải là một ứng dụng đặt xe độc lập. Đây là **lớp voice assistant nằm bên trong app Green SM của VinGroup**, cho phép người dùng điều khiển mọi chức năng của Green SM chỉ bằng lời nói — không cần chạm màn hình.

---

## Định vị sản phẩm

| Câu hỏi | Câu trả lời |
|---|---|
| OlaSM là gì? | Voice control layer tích hợp vào app Green SM |
| Green SM là gì? | App gọi xe điện VinGroup — nguồn dữ liệu, booking và thanh toán chính thức |
| OlaSM tự làm gì? | Nhận giọng nói → hiểu ý định → tạo typed action → chuyển Green SM thực thi |
| OlaSM không làm gì? | Không tự tạo booking, không tự tính giá, không lưu dữ liệu thanh toán |
| Sản phẩm người dùng là gì? | Nút microphone trong app Green SM → nói → xong |

---

## Luồng trải nghiệm mục tiêu

```
Người dùng mở Green SM
       ↓
Bấm nút microphone
       ↓
Nói: "Đặt Green SM Car từ Vincom Bà Triệu đến sân bay Nội Bài"
       ↓
OlaSM Voice Core nhận tiếng → hiểu intent → hỏi bổ sung nếu cần
       ↓
Green SM trả về địa điểm, giá, phương thức thanh toán
       ↓
Người dùng xác nhận bằng giọng nói
       ↓
Green SM tạo chuyến → mở màn hình tracking
```

---

## Phạm vi MVP (Phase 1)

- 🎙 **Kênh**: push-to-talk (bấm để nói), tiếng Việt
- 🚗 **Dịch vụ**: Green SM Car / Mini
- 📍 **Điểm đón**: lấy tự động từ vị trí hiện tại của app
- 🗣 **Điểm đến**: nói tự nhiên
- 💳 **Thanh toán**: chọn bằng giọng nói từ danh sách app trả về
- ✅ **Xác nhận**: người dùng xác nhận rõ ràng trước khi booking
- 🔄 **Fallback**: chuyển sang text hoặc thao tác tay bất kỳ lúc nào

---

## Kiến trúc tổng quan

```
Green SM Mobile App (iOS / Android)
  └── Voice Assistant UI  ←  OlaSM Mobile SDK
        └── OlaSM Voice Gateway (backend)
              ├── Voice Session (LiveKit WebRTC)
              ├── STT  →  LLM  →  TTS
              ├── Dialog State Machine
              ├── AppContext / AppAction contracts
              └── Typed Action Dispatcher
                    └── Green SM Official APIs
                          ├── Place / Address
                          ├── Quote / Pricing
                          ├── Booking / Trip
                          ├── Trip Status / ETA
                          ├── Payment / Promotion
                          └── Support / Handoff
```

---

## Typed action contract

Mỗi lượt, OlaSM chỉ được phát ra danh sách `AppAction` có kiểu dữ liệu tường minh:

| Action Kind | Mô tả | Risk Level |
|---|---|---|
| `NAVIGATE` | Chuyển màn hình trong Green SM | SAFE_NAVIGATION |
| `GO_BACK` | Quay lại màn hình trước | SAFE_NAVIGATION |
| `READ_SCREEN` | Đọc nội dung màn hình hiện tại | SAFE_NAVIGATION |
| `SET_FIELD` | Điền trường được quảng bá bởi host | USER_CONFIRMATION |
| `SELECT_OPTION` | Chọn option trong danh sách | USER_CONFIRMATION |
| `SUBMIT` | Gửi action có side effect — bắt buộc xác nhận | APP_CONFIRMATION |
| `OPEN_HELP` | Mở màn hình hỗ trợ | SAFE_NAVIGATION |
| `REQUEST_OPEN_APP` | Yêu cầu OS mở lại app | OS_MANAGED |
| `END_ASSISTANT` | Dừng voice, giải phóng microphone | SAFE_NAVIGATION |

**OlaSM không bao giờ tự tạo booking, tự thanh toán hay force-quit app.** Mọi side effect đều qua xác nhận của Green SM hoặc biometric.

---

## Quyền riêng tư và an toàn

- Microphone chỉ bật khi người dùng bấm nút
- Không nghe nền, không wake word trong MVP
- Raw audio không lưu mặc định
- Transcript được ẩn danh và giới hạn thời gian lưu
- Thông tin thẻ/OTP không bao giờ đi vào LLM
- Mọi action có side effect yêu cầu xác nhận tường minh

---

## Cấu trúc project

| Thư mục | Nội dung |
|---|---|
| `src/agents/contracts/` | Typed contracts: AppContext, AppAction, AppScreen |
| `src/agents/core/` | LLM agent, guardrails, mobile instructions |
| `src/voice_agent/` | LiveKit session, app-control tools, state sync |
| `src/backend/` | FastAPI routes, session service, schemas |
| `src/frontend/` | Web test harness (không phải sản phẩm) |
| `docs/` | Architecture, PRD, tiến trình POC |
| `tests/` | Unit + integration tests |
| `eval_cases/` | Reproducible eval scenarios |

---

## Lộ trình phát triển

| Phase | Mục tiêu | Trạng thái |
|---|---|---|
| **Phase 0** | Chốt API/SDK chính thức với team Green SM | EXTERNAL_BLOCKED |
| **Phase 1 (MVP)** | Voice-to-book cho Green SM Car | IN_PROGRESS |
| **Phase 2** | Trợ lý trong chuyến: tracking, hủy, hỗ trợ | ROADMAP |
| **Phase 3** | Mở rộng: Bike, Express, Food, đặt hộ | ROADMAP |

---

## Lưu ý quan trọng

> **Web frontend hiện tại chỉ là test harness nội bộ.** Sản phẩm thật là mobile SDK tích hợp vào app Green SM.

> **GSMSandboxClient và mock data** chỉ dùng cho test. Không được dùng để tuyên bố đã tích hợp Green SM thật.

> **"Đóng app"** không phải tính năng của OlaSM. iOS/Android không cho app tự force-quit. Lệnh "thoát" sẽ dừng voice assistant và giải phóng microphone — việc đóng/mở app là của OS.

---

## Môi trường phát triển

```bash
# Cài đặt dependencies
uv sync

# Chạy backend (test harness)
uv run uvicorn src.backend.main:app --reload

# Chạy LiveKit voice worker
uv run python -m src.voice_agent.server

# Test
uv run pytest -q
uv run ruff check src tests
```

Biến môi trường cần thiết: xem `.env.example`.

---

## 👥 Phân công công việc (Khánh & Phương)

Chi tiết phân chia 50% - 50% khối lượng công việc kỹ thuật giữa **Khánh** (Lead Mobile & Edge AI) và **Phương** (Lead Backend & DevOps): xem tại [docs/PHAN_CONG_CONG_VIEC.md](docs/PHAN_CONG_CONG_VIEC.md).

---

*OlaSM Voice Core — phát triển trong khuôn khổ VRIC × GSM Smart City, Nhóm 4: Mobility Assistant*
