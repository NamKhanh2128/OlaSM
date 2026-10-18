# 👥 BẢNG PHÂN CÔNG CÔNG VIỆC DỰ ÁN OLASM MOBILE & LIVEKIT WAKEWORD
## (WORK BREAKDOWN & TEAM ALLOCATION: KHÁNH & PHƯƠNG)

> **Dự án**: Trợ lý giọng nói rảnh tay đặt xe OlaSM (Flutter Native & LiveKit WakeWord Low-Latency)  
> **Phiên bản phân công**: 1.0 (Production Release)  
> **Nguyên tắc phân chia**: Cân bằng chính xác **50% - 50%** khối lượng công việc theo năng lực chuyên môn:  
> - **Khánh**: Phụ trách toàn bộ **Tầng Thiết Bị Di Động & AI Cục Bộ (Client Tier & Edge AI)**  
> - **Phương**: Phụ trách toàn bộ **Tầng Máy Chủ, LiveKit Cloud, Tối Ưu Âm Thanh & Vận Hành (Cloud Tier, Voice Agent & DevOps)**  

---

## 📊 MA TRẬN TỔNG QUAN PHÂN CHIA KHỐI LƯỢNG (50% - 50%)

```
╔═════════════════════════════════════════════╦═════════════════════════════════════════════╗
║            📱 KHÁNH (50%)                   ║             ☁️ PHƯƠNG (50%)                 ║
║  Lead Mobile Engineering & Edge AI          ║  Lead Backend, LiveKit Cloud & DevOps       ║
╠═════════════════════════════════════════════╬═════════════════════════════════════════════╣
║ 1. Flutter Mobile App Architecture & UI/UX  ║ 1. FastAPI Mobile Token & Auth Service      ║
║ 2. Native Android/iOS WakeWord Plugins      ║ 2. LiveKit Agent Worker & Audio Pipeline    ║
║ 3. On-Device ONNX Runtime (NNAPI & CoreML)  ║ 3. Maps Geocoding, Routing & Pricing Engine ║
║ 4. Circular Pre-roll Ring Buffer 500ms      ║ 4. Pre-connect Audio Buffer Integration     ║
║ 5. Android Foreground Service (Always-On)   ║ 5. Human Operator Handoff Web Console       ║
║ 6. Huấn luyện Model "Hey OlaSM" INT8        ║ 6. Kiểm thử E2E, Latency Sub-350ms & CI/CD  ║
╚═════════════════════════════════════════════╩═════════════════════════════════════════════╝
```

---

## 📱 CHI TIẾT CÔNG VIỆC CỦA KHÁNH (CLIENT TIER & EDGE AI)

### 1. Phạm vi phụ trách (Owner Scope)
* **Thư mục mã nguồn chính**:
  * `olasm_mobile/` (Ứng dụng Flutter di động Android & iOS)
  * `olasm_mobile/android/` (Native Kotlin audio engine)
  * `olasm_mobile/ios/` (Native Swift CoreML engine)
  * `configs/hey_olasm_vietnamese.yaml` (Cấu hình dataset tiếng Việt)
  * `scripts/train_export_wakeword.py` (Pipeline huấn luyện và xuất ONNX)

### 2. Danh mục đầu việc cụ thể

| Mã việc | Tên đầu mục công việc | Mô tả kỹ thuật & Trách nhiệm thực thi | Đầu ra nghiệm thu |
|:---|:---|:---|:---|
| **K-01** | **Flutter UI & Clean Architecture** | Xây dựng giao diện Dark Mode chuẩn thẩm mỹ: Orb Visualizer sóng âm, bảng Live Transcript song song, Thẻ lộ trình xe Realtime Vector Map (`BookingMapWidget`), Thẻ thông tin cuốc xe (`BookingCardWidget`). Quản lý state tập trung qua Riverpod StateNotifier. | Màn hình `voice_interaction_screen.dart` chạy mượt 60fps, tự động đổi trạng thái theo giọng nói. |
| **K-02** | **Android Native Engine (Kotlin)** | Phát triển `OnnxWakeEngine.kt` chạy mô hình ONNX INT8 qua **NNAPI (NPU/DSP hardware)**. Trích xuất log-Mel spectrogram (`MelFeatureExtractor.kt`), xử lý AudioFocus và quản lý vòng đời microphone. | Thời gian suy luận từ khóa trên Android đạt **10-15ms**, không gây gián đoạn luồng WebRTC. |
| **K-03** | **iOS Native Engine (Swift)** | Phát triển `CoreMLOnnxRunner.swift` tối ưu hóa trên **Apple Neural Engine (ANE)**. Tính toán ma trận âm thanh qua Accelerate / vDSP (`MelFeatureExtractorSwift.swift`). | Thời gian suy luận từ khóa trên iOS đạt **5-8ms**, tích hợp mượt với AVAudioEngine. |
| **K-04** | **Pre-roll Ring Buffer 500ms** | Cài đặt bộ đệm vòng tròn (Circular Buffer) 500ms âm thanh PCM 16kHz Mono lưu trên RAM native. Tự động trích xuất và chuyển tiếp lên tầng Flutter ngay khi Wake Word kích hoạt để gửi qua WebRTC. | Người dùng nói liền mạch không cần chờ chuông reo; 0% mất âm tiết đầu tiên của câu lệnh. |
| **K-05** | **Android Foreground Service** | Hiện thực `WakeWordService.kt` kèm persistent notification và quyền `FOREGROUND_SERVICE_MICROPHONE`. Cho phép gọi "Hey OlaSM" ngay cả khi khóa màn hình hoặc mở ứng dụng khác. | App tự động thức giấc và kết nối cuộc gọi khi tắt màn hình; kiểm soát hao pin < 1.2%/giờ. |
| **K-06** | **Huấn luyện Mô hình "Hey OlaSM"** | Chạy quy trình tổng hợp 25.000 mẫu âm thanh tiếng Việt 3 miền Bắc - Nam - Trung; áp dụng RIR phòng/cabin xe và tiếng ồn giao thông; huấn luyện mạng Conv-Attention và xuất file `hey_olasm_int8.onnx`. | File mô hình `hey_olasm_int8.onnx` dung lượng **< 250KB**, Recall > 88%, FPPH < 0.05. |
| **K-07** | **Thiết bị ngoại vi & Bluetooth** | Xử lý Bluetooth SCO (tai nghe xe máy, Carplay/Android Auto), tự động chuyển loa ngoài/tai nghe và tắt màn hình khi áp tai qua cảm biến tiệm cận. | Nghe gọi rõ ràng khi đội mũ bảo hiểm đeo tai nghe không dây hoặc cắm màn hình xe hơi. |

---

## ☁️ CHI TIẾT CÔNG VIỆC CỦA PHƯƠNG (CLOUD TIER, BACKEND & DEVOPS)

### 1. Phạm vi phụ trách (Owner Scope)
* **Thư mục mã nguồn chính**:
  * `src/backend/` (FastAPI backend, DB asyncpg, Redis cache)
  * `src/voice_agent/` (LiveKit AgentServer worker Python)
  * `tests/` (Hệ thống kiểm thử tự động)
  * `docker-compose*.yml`, `Caddyfile`, `Dockerfile` (Hạ tầng triển khai)

### 2. Danh mục đầu việc cụ thể

| Mã việc | Tên đầu mục công việc | Mô tả kỹ thuật & Trách nhiệm thực thi | Đầu ra nghiệm thu |
|:---|:---|:---|:---|
| **P-01** | **Mobile Voice Token API** | Phát triển và vận hành endpoint `/api/v1/mobile/voice-token`. Quản lý sinh JWT token truy cập LiveKit Room tốc độ cao với room configuration và dispatch metadata chuẩn. | Endpoint phản hồi **< 50ms**, kết nối đúng agent worker, có unit test đạt 100%. |
| **P-02** | **Xác thực Người dùng & Quản lý Session** | Cung cấp luồng đăng nhập nhanh bằng OTP điện thoại (`/api/v1/auth/otp-login`). Gắn kết thông tin định danh khách hàng (tên, số điện thoại) vào phiên thoại LiveKit. | Khách hàng chỉ đăng nhập 1 lần; AI gọi đúng tên khách và tự điền số điện thoại vào chuyến xe. |
| **P-03** | **LiveKit Voice Agent Worker** | Cấu hình và tối ưu hóa LiveKit `AgentServer` Python: tích hợp VAD (Silero) -> STT (Deepgram Nova-3) -> LLM (GPT-4.1-mini) -> TTS (Google Chirp3 / Cartesia). Quản lý prompt điều hướng đặt xe. | Agent phản hồi tự nhiên, hỗ trợ ngắt lời (Barge-in), thời gian trễ phản hồi (TTFT) < 600ms. |
| **P-04** | **Xử lý Pre-connect Audio Buffer** | Lắng nghe gói dữ liệu âm thanh đệm gửi qua DataChannel topic `lk.agent.pre-connect-audio-buffer` trên server. Nối các khung âm thanh này trực tiếp vào luồng STT của Deepgram. | Agent nghe trọn vẹn câu nói: *"Chở tôi đến..."* mà không bị mất chữ đầu; log xác thực nhận đủ frames. |
| **P-05** | **Tích hợp Bản đồ Geocoding & Bảng giá** | Kết nối API Geocoding (Goong Maps / Google Places / OSRM) trong `src/backend/services/maps/`. Tính khoảng cách đường bộ, thời gian di chuyển (ETA) và áp dụng biểu giá OlaSM/GreenSM. | AI đọc chính xác giá cước theo km thực tế và phát sinh lộ trình chuẩn lên DataChannel. |
| **P-06** | **Chuyển tiếp Tổng Đài Viên (Handoff)** | Quản lý quy trình Human Handoff: khi AI không giải quyết được hoặc khách yêu cầu gặp người thật, tự động phát sự kiện dispatch tới Dashboard tổng đài viên và bàn giao line gọi tức thì. | Chuyển line không rớt cuộc gọi; tổng đài viên nhận đầy đủ tóm tắt ngữ cảnh chuyến đi của khách. |
| **P-07** | **Đo lường Sub-350ms, QA & Đóng gói Cloud** | Thực hiện đo lường độ trễ toàn trình Sub-350ms qua `latency_telemetry`. Cấu hình Docker Compose Production, reverse proxy Caddy HTTPS/WSS và thiết lập quy trình build APK/AAB/IPA tự động. | Toàn bộ 30+ test cases pass 100%; hệ thống Docker chạy ổn định 24/7; file cài đặt release sẵn sàng. |

---

## 🔄 QUY TRÌNH PHỐI HỢP & GIAO TIẾP DỮ LIỆU (INTERFACE CONTRACT)

Để đảm bảo hai bạn làm việc độc lập mà vẫn ghép nối trơn tru, hợp đồng giao tiếp giữa Client (Khánh) và Backend (Phương) được chuẩn hóa:

1. **Giao tiếp Token**:
   * Client (Khánh) gọi `POST /api/v1/mobile/voice-token` với payload `{"device_id": "...", "trigger_source": "wake_word"}`.
   * Backend (Phương) trả về `{server_url, participant_token, room_name, agent_name, token_ttl_seconds}`.

2. **Giao tiếp Dữ liệu Realtime (DataChannel)**:
   * **Client -> Server**: Gửi các frames âm thanh pre-roll qua topic `lk.agent.pre-connect-audio-buffer`.
   * **Server -> Client**: Phát trạng thái đặt xe qua topic `olasm.booking_state.v1` với JSON schema:
     ```json
     {
       "pickup": {"display_name": "Vincom Đồng Khởi", "address": "Quận 1, TP.HCM"},
       "destination": {"display_name": "Sân bay Tân Sơn Nhất", "address": "Tân Bình, TP.HCM"},
       "vehicle_type": "CAR_4",
       "quote": {"fare_amount": 145000, "currency": "VND"},
       "confirmation_status": "confirmed"
     }
     ```
   * Client (Khánh) nhận gói này và tự động hiển thị thẻ giá + vẽ lộ trình xe trên bản đồ.

---

## 📅 LỊCH TRÌNH BÀN GIAO (MILESTONES)

* **Tuần 1**: Khánh hoàn tất UI Flutter + Native Audio Tap; Phương hoàn tất Mobile Token Endpoint & LiveKit Room Pre-warm.
* **Tuần 2**: Khánh huấn luyện xong mô hình `hey_olasm_int8.onnx` & Pre-roll Buffer; Phương hoàn tất Geocoding & Audio Buffer Listener trên Agent.
* **Tuần 3**: Hai bạn ghép nối E2E: Nói "Hey OlaSM" trên điện thoại -> Đặt xe thành công -> Hiển thị lộ trình và giá cước.
* **Tuần 4**: Kiểm thử độ trễ sub-350ms, kiểm tra pin, đóng gói APK/IPA và triển khai hạ tầng Cloud Production.
