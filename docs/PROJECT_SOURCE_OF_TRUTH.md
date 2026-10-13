# OlaSM Voice Core — Nguồn sự thật và trình tự hoàn thiện project

Cập nhật: **2026-10-13**. Tài liệu này là nguồn trạng thái toàn project theo hướng mới: OlaSM là voice assistant layer tích hợp vào app mobile Green SM.

---

## 1. Quy tắc nguồn sự thật

Khi hai nguồn mâu thuẫn, áp dụng thứ tự sau:

1. Code runtime + migration + test đang pass.
2. Contract hiện hành (`src/agents/contracts/`).
3. Tài liệu trạng thái hiện hành (file này + PRODUCT_BRIEF.md).
4. PRD/MVP cho yêu cầu sản phẩm chưa được triển khai.
5. Git history khi cần truy vết quyết định hoặc kế hoạch đã bị thay thế.

| Câu hỏi | Nguồn chuẩn |
|---|---|
| Sản phẩm hướng tới điều gì? | `docs/PRODUCT_BRIEF.md`, sau đó `docs/PRD_OlaSM_Voice.md` |
| Typed action contract là gì? | `src/agents/contracts/app_control.py` |
| Hệ thống hiện chạy thế nào? | code trong `src/`, migration và test |
| Voice runtime hiện tại | `docs/LIVEKIT_TEAM_SETUP.md` |
| Kiến trúc hệ thống | `docs/architecture_diagram.md` |
| Tiến trình POC | `docs/TIEN_TRINH_POC_CHUAN.md` |
| Việc AI/code không thể tự hoàn tất | `mustdo.md` |

---

## 2. Định vị sản phẩm (đã pivot)

**OlaSM không còn là ứng dụng đặt xe độc lập.**

OlaSM là **lớp voice control tích hợp vào app mobile Green SM**. Người dùng bấm nút microphone trong Green SM → nói → OlaSM xử lý → Green SM thực thi.

### Green SM là nguồn dữ liệu duy nhất cho:
- Giá cước và báo giá
- Tài xế, ETA và trạng thái chuyến
- Thanh toán và khuyến mãi
- Hủy chuyến và điều phối
- Chính sách, an toàn và hỗ trợ

### OlaSM chỉ làm:
- Nhận giọng nói từ microphone người dùng
- Hiểu ý định và trích xuất thông tin
- Hỏi lại khi thông tin chưa rõ
- Tạo danh sách `AppAction` typed để Green SM thực thi
- Đọc kết quả bằng giọng nói

---

## 3. Từ điển trạng thái thống nhất

Chỉ dùng các trạng thái sau trong tài liệu và báo cáo mới:

| Trạng thái | Nghĩa |
|---|---|
| `IMPLEMENTED` | Code và contract đã có, test phù hợp đã pass |
| `LIVE_VALIDATED` | Đã chạy qua provider/hạ tầng thật và có artifact kết quả |
| `DEMO` | Chạy được nhưng dùng dữ liệu tĩnh, deterministic hoặc process-memory |
| `STAGING_ONLY` | Có tích hợp thật nhưng chưa đủ SLA, privacy hoặc vận hành production |
| `EXTERNAL_BLOCKED` | Thiếu credential, dữ liệu business, consent, license hoặc hạ tầng |
| `RELEASE_GATED` | Code xong nhưng còn gate người thật/pháp lý/load/soak trước release |
| `HISTORICAL` | Chỉ ghi lại thiết kế hoặc tiến trình cũ |
| `DEPRECATED` | Không còn phù hợp với hướng sản phẩm mới; không phát triển thêm |

---

## 4. Kiến trúc hiện hành

```
Green SM Mobile App (iOS / Android)
  └── Voice Assistant UI ← OlaSM Mobile SDK
        └── OlaSM Voice Gateway
              ├── LiveKit WebRTC (real-time audio)
              ├── STT → LLM → TTS pipeline
              ├── Dialog State Machine
              ├── AppContext validator (nhận từ mobile host)
              ├── AppAction dispatcher (typed, allowlisted)
              └── Guardrails (3 lớp)
                    └── Green SM Official APIs
                          ├── Place / Address lookup
                          ├── Quote / Pricing
                          ├── Booking / Trip management
                          ├── Trip Status / ETA / Driver info
                          ├── Payment / Promotion
                          └── Support / Handoff
```

---

## 5. Trạng thái các thành phần

### Backend (src/)

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `agents/contracts/app_control.py` | `IMPLEMENTED` | Typed AppContext/AppAction/AppScreen contract |
| `agents/contracts/schemas.py` | `IMPLEMENTED` | Mở rộng với app_context, app_actions, session_control |
| `agents/core/mobile_instructions.py` | `IMPLEMENTED` | System instructions cho mobile voice agent |
| `agents/core/guardrails.py` | `IMPLEMENTED` | Thêm _validate_app_actions |
| `voice_agent/agent.py` | `IMPLEMENTED` | 8 app-control function tools mới |
| `voice_agent/state_sync.py` | `IMPLEMENTED` | Thêm publish_app_control_state trên LiveKit |
| `backend/schemas/session.py` | `IMPLEMENTED` | Thêm MOBILE_VOICE/TEXT channel, app_context, app_actions |
| `integrations/gsm_sandbox_client.py` | `DEMO` | Chỉ dùng test; không dùng cho demo tích hợp thật |

### Frontend (src/frontend/)

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| React web app | `DEMO` | Test harness nội bộ; không phải sản phẩm |
| LiveKit contracts.ts | `IMPLEMENTED` | Thêm AppAction/AppControlState types |

### Green SM Integration

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Green SM Place API | `EXTERNAL_BLOCKED` | Cần chốt với team GSM |
| Green SM Quote API | `EXTERNAL_BLOCKED` | Cần chốt với team GSM |
| Green SM Booking API | `EXTERNAL_BLOCKED` | Cần chốt với team GSM |
| Green SM Trip Status API | `EXTERNAL_BLOCKED` | Cần chốt với team GSM |
| Green SM Payment API | `EXTERNAL_BLOCKED` | Cần chốt với team GSM |
| Mobile SDK (iOS/Android) | `EXTERNAL_BLOCKED` | Phụ thuộc công nghệ app GSM |

---

## 6. Những gì đã DEPRECATED

| Thành phần | Lý do |
|---|---|
| Auth/bản đồ/pricing riêng của OlaSM | Green SM là nguồn sự thật duy nhất |
| Database booking riêng | Không dùng làm source of truth production |
| Web frontend như sản phẩm | Chỉ là test harness; sản phẩm thật là mobile SDK |
| Mock fare, mock driver, random ETA | Không được dùng trong bất kỳ demo tích hợp thật nào |
| Tư duy "OlaSM như app gọi xe độc lập" | Đã pivot sang voice control layer |

---

## 7. Thứ tự ưu tiên hoàn thiện

1. **[BLOCKED]** Chốt API/SDK chính thức với team Green SM
2. **[IN_PROGRESS]** Hoàn thiện typed action contract và guardrails
3. **[TODO]** Xây mobile SDK adapter (phụ thuộc công nghệ app GSM)
4. **[TODO]** Thay GSMSandboxClient bằng adapter API chính thức
5. **[TODO]** End-to-end test: voice → AppAction → Green SM API → response
6. **[TODO]** Tích hợp vào test build app Green SM
7. **[ROADMAP]** Phase 2: trợ lý trong chuyến đi
8. **[ROADMAP]** Phase 3: mở rộng sang Bike, Express, Food

---

*Xem `mustdo.md` cho danh sách việc AI/code không thể tự hoàn tất.*
