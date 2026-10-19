# Plan demo: Trợ lý giọng nói đặt xe cho app Green SM (đến bước mở deeplink xác nhận)

> Phiên bản 1.1, ngày 19/10/2026. Người thực hiện: **Khánh** (Agent, Backend), **Phương** (Mobile, UI).
>
> Bản 1.1: chốt STT và TTS bằng số đo thật trên LiveKit Inference (mục 8A), thêm hướng wake word bằng livekit-wakeword (mục 8B), sửa thông số VAD.
>
> Phạm vi: một app Flutter demo có giao diện khớp app Green SM. Người dùng đặt xe hoàn toàn bằng giọng nói qua LiveKit. Luồng kết thúc khi app mở deeplink tới màn xác nhận đặt xe của app Green SM thật.
>
> Căn cứ: kiểm tra mã nguồn hiện tại, báo cáo đo latency ngày 21/08/2026 trong repo, tài liệu chính thức của LiveKit, Deepgram, Goong (nguồn ở mục 15).

---

## 0. Tóm tắt quyết định

| # | Quyết định | Lý do |
|---|---|---|
| 1 | Luồng chuẩn chỉ cần **2 lượt nói**: nói yêu cầu, nói "đúng rồi", app mở deeplink | Ít lượt nhất mà vẫn đọc lại đủ thông tin trước khi chuyển |
| 2 | Agent **không tạo booking, không tự tính giá**. Giá và xác nhận cuối do Green SM hiển thị sau deeplink | Quãng đường hiện là số giả sinh từ hash, nên giá và ETA agent đọc ra là bịa. Deeplink đã giao bước xác nhận cho Green SM |
| 3 | Địa điểm: gazetteer demo có toạ độ, sau đó Goong AutoComplete/Detail có bias theo GPS, cuối cùng là danh sách đánh số khi mơ hồ | Deeplink cần toạ độ thật. Gazetteer hiện chỉ có tên, không có toạ độ |
| 4 | STT **Deepgram Nova-3 khóa `vi` + keyterm**, dự phòng AssemblyAI Universal-3.5 Pro. TTS **Cartesia Sonic-3.6** có prewarm. Tất cả qua LiveKit Inference | Đo ngày 19/10/2026 trên 12 cấu hình STT và 7 model TTS: Nova-3 `vi` + keyterm ra final sau 483 ms, đúng 92% địa danh. Sonic-3.6 có TTFB 275 ms khi kết nối đã ấm (mục 8A) |
| 5 | Flutter dùng **`Session` API** của livekit_client 2.13.x: pre-connect audio, agent state, transcript chuẩn | Bản hiện tại tự chế pre-connect bằng data packet và agent bỏ qua gói này |
| 6 | **Fast path tất định** cho các lượt đặt xe chuẩn. LLM chỉ chạy khi câu nói nằm ngoài mẫu | Mỗi vòng LLM tốn 0,5 đến 1 s. Bộ parser tiếng Việt trong repo đã có sẵn |
| 7 | Bỏ DB restore, lời chào và DB write khỏi đường găng | Khởi động hiện mất khoảng 18 s, tool p95 là 5,5 s |
| 8 | UI đo token thiết kế từ **ảnh chụp app Green SM thật**, so pixel từng màn, khóa bằng golden test | Không đoán màu hay khoảng cách |
| 9 | Tạo **profile agent `greensm_demo`** riêng | Không phá luồng OlaSM, web harness và bộ test hiện có |
| 10 | Wake word "Green SM ơi" huấn luyện bằng **livekit-wakeword**, chỉ bật khi qua cổng nghiệm thu. Mặc định demo vẫn bấm mic | Thư viện rất tốt với tiếng Anh nhưng tự cảnh báo tiếng Việt kém hơn và chưa có bản Android. Engine Android hiện tại không chạy được (mục 8B) |

---

## 1. Mục tiêu và tiêu chí nghiệm thu

| Chỉ số | Hiện tại (đo 21/08/2026) | Mục tiêu demo |
|---|---|---|
| Bấm mic đến lúc thu âm | không có pre-connect thật | ≤ 100 ms (người dùng nói ngay, audio được đệm) |
| Bấm mic đến lúc agent nhận audio | khoảng 17,9 s mới tới lời chào | p50 ≤ 1,5 s |
| Hết câu nói đến lúc nghe tiếng agent (e2e) | p50 6,2 s, p90 15,8 s | p50 ≤ 1,2 s, p95 ≤ 2,0 s. Fast path p50 ≤ 1,0 s |
| End-of-turn delay | p50 1,9 s | p50 ≤ 0,6 s |
| LLM TTFT | p50 1,07 s | p50 ≤ 0,6 s, hoặc bỏ qua nhờ fast path |
| Thời gian tool | p50 0,84 s, p95 5,5 s | p50 ≤ 0,25 s, p95 ≤ 0,6 s |
| TTS TTFB | p50 262 ms | ≤ 300 ms khi kết nối đã ấm (Sonic-3.6 đo được 275 ms từ Hà Nội) |
| Số lượt nói, happy path | 4 đến 6 lượt, phải đọc câu "tôi xác nhận đặt xe" | 2 lượt |
| Nhận đúng địa điểm | gazetteer chỉ có tên | 100% với POI kịch bản, ≥ 90% đúng trong top 3 với 50 POI Hà Nội ngẫu nhiên |
| Deeplink | chưa có | Mở đúng màn xác nhận Green SM, toạ độ lệch ≤ 30 m, đúng dịch vụ |
| Ổn định | chưa đo | 10/10 lượt chạy liên tiếp trên máy demo, không can thiệp tay |
| UI | dark theme "OlaSM Voice" | Đạt checklist so pixel ở mục 5.5 cho từng màn |

---

## 2. Hiện trạng đã kiểm tra

### 2.1 Latency gần nhất và nguyên nhân

Nguồn: [report.md](../reports/voice-finalization-20260821-3calls/report.md), cấu hình chirp_2 + gpt-4.1-mini + cartesia/sonic-3, VAD, endpointing 0,8 đến 2,5 s.

| Triệu chứng | Nguyên nhân trong code | Hướng xử lý |
|---|---|---|
| Lời chào tới sau khoảng 17,9 s | Job khôi phục state từ DB trước khi start session ([server.py:579-608](../src/voice_agent/server.py#L579-L608)). Room mobile có `app_session_id` ngẫu nhiên nên lần nào cũng không tìm thấy gì, nhưng vẫn tốn khoảng 16,5 s | Profile demo dùng `EphemeralVoiceStateStore` ([persistence.py:126](../src/voice_agent/persistence.py#L126)) |
| End-of-turn p50 1,9 s | Chirp 2 trả final chậm, endpointing min 0,6 đến 0,8 s | Deepgram Nova-3 `vi` streaming, min_delay khoảng 0,35 s |
| e2e p50 6,2 s | Mỗi lượt đi qua 2 đến 3 vòng LLM: `start_booking`, rồi `search_place`, `estimate_fare`, `confirm_booking`, `create_booking` | Fast path tất định, gom còn 4 tool |
| Tool p95 5,5 s | Mỗi `_commit` chờ ghi DB, quote ghi DB | Bỏ DB khỏi đường găng, không còn quote |
| Có thể thêm tới 2 s mỗi lượt | Bước rewrite transcript bằng LLM chạy trước LLM chính ([transcript_rewrite.py:437-452](../src/voice_agent/transcript_rewrite.py#L437-L452)). Hiện chỉ tắt vì thiếu key | Tắt hẳn trong profile demo |
| TTS có thể treo lâu | `.env` đang dùng `gemini-2.5-flash-tts`, timeout 30 s | Cartesia Sonic-3.6 qua Inference |
| Preemptive generation tắt | [server.py:175-182](../src/voice_agent/server.py#L175-L182) | Bật cho lượt đi qua LLM |

### 2.2 App Flutter `olasm_mobile`

1. **Giao diện không giống Green SM.** Dark theme, orb, chữ "OlaSM Voice" ([app_theme.dart](../olasm_mobile/lib/core/theme/app_theme.dart), [voice_interaction_screen.dart](../olasm_mobile/lib/features/voice/presentation/screens/voice_interaction_screen.dart)). Không có màn Home, bản đồ, tìm điểm đến hay chọn dịch vụ. Bản đồ là đường bezier vẽ giả ([booking_map_widget.dart](../olasm_mobile/lib/features/voice/presentation/widgets/booking_map_widget.dart)).
2. **Pre-connect audio làm sai giao thức.** App gửi PCM qua `publishData` ([livekit_transport.dart:113-121](../olasm_mobile/lib/features/voice/data/livekit_transport.dart#L113-L121)), còn agent chỉ log số byte ([server.py:559-565](../src/voice_agent/server.py#L559-L565)). SDK chính thức đã có `PreConnectAudioBuffer`, bật mặc định trong `SessionOptions`.
3. **Wake word chưa dùng được.** File [hey_olasm_int8.onnx](../olasm_mobile/assets/models/hey_olasm_int8.onnx) chỉ 655 byte. Engine Android đưa 32 giá trị log-mel vào chỗ cần vector embedding 96 chiều nên lỗi ngay khung đầu, và thiếu hai model mel, embedding. Script huấn luyện chỉ xuất một mạng chưa huấn luyện. Hướng làm lại bằng livekit-wakeword ở mục 8B. Mặc định demo dùng bấm mic.
4. **Token warmup luôn lỗi 422.** App gửi `trigger_source` là `warmup`, `pool_replenish`, `auto_refresh` ([token_cache_manager.dart:65-70](../olasm_mobile/lib/core/network/token_cache_manager.dart#L65-L70)). Schema chỉ cho `wake_word` hoặc `push_to_talk` ([schemas/mobile.py:31-35](../src/backend/schemas/mobile.py#L31-L35)).
5. **Endpoint token đang trả 503 với `.env` hiện tại.** `LIVEKIT_LLM_PROVIDER=openai` nhưng `OPENAI_API_KEY` rỗng, nên `configuration_errors()` báo lỗi ([config.py:153-156](../src/voice_agent/config.py#L153-L156), [mobile.py:112-119](../src/backend/api/routes/mobile.py#L112-L119)).
6. **Trạng thái và transcript không chuẩn.** App dùng `TranscriptionEvent` kiểu cũ, đoán trạng thái agent từ transcript thay vì `lk.agent.state`, chưa nối `audioLevel`, `copyWith` không xoá được `errorMessage`, nút mute và loa chỉ là placeholder.
7. **Không hiển thị danh sách lựa chọn.** Prompt agent dặn chỉ đọc số lượng kết quả và bảo khách chọn số "hiển thị bên dưới" ([booking.py:1060-1061](../src/voice_agent/tasks/booking.py#L1060-L1061)), nhưng app không vẽ danh sách. Gặp địa điểm mơ hồ là luồng tắc.
8. **App-control là nhánh chết.** Agent publish `olasm.app_control.v1` nhưng app không nghe. `app_context` không bao giờ được set trong runtime LiveKit, nên mọi tool app-control luôn trả lỗi ([agent.py:725-731](../src/voice_agent/agent.py#L725-L731)).
9. **Chưa có deeplink và vị trí.** Không có `url_launcher`, không có `<queries>` trong AndroidManifest, không có `LSApplicationQueriesSchemes`. `PermissionGuard` có nhưng không dùng, nên điểm đón không lấy được vị trí hiện tại.

### 2.3 Voice agent

1. **Prompt và số tool quá lớn.** `OlaSMAgent` có khoảng 18 tool cùng instructions song ngữ dài ([agent.py:76-101](../src/voice_agent/agent.py#L76-L101)). `BookingTask` thêm 9 tool. Prompt dài làm tăng TTFT và tăng xác suất gọi nhầm tool.
2. **Xác nhận cứng nhắc.** Khách phải nói đúng câu "tôi xác nhận đặt xe", tối thiểu 4 từ ([booking.py:65](../src/voice_agent/tasks/booking.py#L65), [booking.py:1005-1011](../src/voice_agent/tasks/booking.py#L1005-L1011)). Với deeplink, bước này không còn là side effect nên chỉ cần một câu đồng ý tự nhiên.
3. **STT để `language=multi` gần như không nhận được tiếng Việt.** Đo ngày 19/10/2026, cấu hình này chỉ nhận đúng 15,9% địa danh, WER 0,885. Khóa `vi` kèm keyterm đưa lên 92,1% (mục 8A).
4. **Persona là "tổng đài viên OlaSM".** Trong app Green SM, nên xưng là trợ lý Green SM (xem câu hỏi ở mục 14).

### 2.4 Dữ liệu địa điểm và giá

1. **Gazetteer không có toạ độ.** [place_search_service.py:174-179](../src/backend/services/place_search_service.py#L174-L179). Không dựng được deeplink theo toạ độ, và chỉ phủ một nhóm nhỏ địa danh Hà Nội.
2. **Quãng đường là số giả.** `estimate_distance_km` sinh 1,2 đến 18 km từ hash của place_id ([pricing_service.py:17-20](../src/backend/services/pricing_service.py#L17-L20)). Giá và ETA agent đọc ra hiện tại là bịa.
3. **GoongProvider có sẵn nhưng không dùng được cho demo.** Nó gọi `/geocode` thay vì AutoComplete/Detail. Khi key sai, nó âm thầm trả dữ liệu mock, và câu hỏi lạ bị gán toạ độ Hồ Gươm ([goong.py:60-71](../src/backend/maps/providers/goong.py#L60-L71), [goong.py:242-253](../src/backend/maps/providers/goong.py#L242-L253)). Mỗi request tạo client HTTP mới, tốn thêm TLS handshake. Voice agent cũng không gọi tới nó.

### 2.5 Tài sản dùng lại được

- `BookingDraft`: máy trạng thái slot, tự huỷ phần phụ thuộc khi sửa, có revision ([session_data.py:190-563](../src/voice_agent/session_data.py#L190-L563)). Mở rộng thêm toạ độ và dịch vụ.
- Parser tiếng Việt tất định: `extract_complete_route`, `extract_labeled_booking_places`, `extract_vehicle_type`, nhận diện sửa điểm, chọn theo số thứ tự hoặc theo tên, nhận diện bỏ đặt ([booking.py](../src/voice_agent/tasks/booking.py)).
- Mẫu fast path đã có: `session.say(...)` rồi `raise StopResponse()` để bỏ qua LLM ([booking.py:1173-1174](../src/voice_agent/tasks/booking.py#L1173-L1174)).
- Alias ASR Hà Nội và các điểm đón của landmark ([data/gazetteer](../data/gazetteer)), chuẩn hoá số tiền cho TTS ([tts_text.py](../src/voice_agent/tts_text.py)).
- Hạ tầng đo: `SessionEventLog`, `LiveKitSessionObserver`, [aggregate_livekit_evaluation.py](../scripts/aggregate_livekit_evaluation.py), [benchmark_livekit_asr.py](../scripts/benchmark_livekit_asr.py), [livekit_room_smoke.py](../scripts/livekit_room_smoke.py). Lưu ý: `benchmark_livekit_asr.py` gọi nhận dạng batch nên không chạy được với LiveKit Inference, vốn chỉ hỗ trợ streaming.
- Cấp token mỗi cuộc một room, dispatch agent tường minh ([mobile.py](../src/backend/api/routes/mobile.py)).

---

## 3. Kiến trúc đích

```text
┌──────────── App Flutter demo (Android trước, iOS sau) ────────────┐
│ Home: bản đồ Goong, ô "điểm đến" có mic, lưới dịch vụ             │
│   bấm mic ─► Session.start()  (mic thu và đệm ngay, token lấy sẵn)│
│ Voice sheet: trạng thái agent, caption, chip slot                 │
│ Route: marker đón/đến, polyline, danh sách lựa chọn, dịch vụ      │
│   RPC greensm.open_confirmation ─► DeeplinkBuilder ─► url_launcher│
└───────────────┬───────────────────────────────────▲───────────────┘
                │ WebRTC Opus (audio), lk.transcription│ booking_state v2
                ▼                                    │ (reliable, có revision)
        LiveKit Cloud room ◄──────────────► Agent worker, profile greensm_demo
                                              ├─ STT  inference deepgram/nova-3, vi + keyterm
                                              ├─ VAD  silero (prewarm), endpointing ~0,35 s
                                              ├─ Fast path: parser + resolver ─► session.say
                                              ├─ LLM  (chỉ khi cần) model nhanh, 4 tool
                                              ├─ TTS  inference cartesia/sonic-3.6, vi, prewarm
                                              └─ Resolver: gazetteer demo ─► Goong AutoComplete/Detail
                                                           ─► Goong Direction (quãng đường, thời gian)
FastAPI: POST /api/v1/mobile/voice-token  (nhận GPS, nhét vào dispatch metadata)
```

Nguyên tắc:

1. **State do agent làm chủ, app chỉ render.** Mọi thay đổi slot đều publish `greensm.booking_state.v2` trước khi agent nói, nên bản đồ cập nhật cùng lúc với lời đọc.
2. **Hành động cần xác nhận kết quả thì dùng RPC.** Mở deeplink trả về ack hoặc lỗi để agent nói đúng tình huống.
3. **Không bịa dữ liệu.** Lỗi provider thì nói "chưa tìm thấy" và hỏi lại, không rơi về mock.
4. **Đường găng không có I/O chậm.** Không ghi DB, không gọi LLM phụ, lookup Goong được prefetch và cache.

---

## 4. Luồng màn hình và kịch bản thoại

### 4.1 Màn hình

| Màn | Nội dung | Tham chiếu Green SM | Vai trò voice |
|---|---|---|---|
| S0 Splash | Logo, xin quyền mic và vị trí | Splash app thật | Xin quyền sớm để pre-connect chạy ngay khi bấm |
| S1 Home | Bản đồ có vị trí hiện tại, ô nhập điểm đến có icon mic, lưới dịch vụ, địa điểm gần đây, thanh tab 4 mục | Trang gọi xe | Bấm mic hoặc ô tìm kiếm để bắt đầu |
| S2 Voice sheet | Bottom sheet nổi trên S1 hoặc S3: trạng thái nghe, nghĩ, nói; caption; 3 chip Điểm đón, Điểm đến, Dịch vụ | Không có ở app thật, thiết kế theo ngôn ngữ Green SM | Trung tâm tương tác |
| S3 Route | Marker đón và đến, polyline, quãng đường và thời gian, thẻ địa chỉ, danh sách lựa chọn đánh số khi mơ hồ, danh sách dịch vụ | Màn chọn điểm và chọn dịch vụ | Chọn bằng số, bằng tên, hoặc chạm |
| S4 Chuyển | "Đang mở Green SM..." trong 0,3 đến 0,6 s | Không có | Agent nói câu chuyển, app mở deeplink |
| App Green SM thật | Màn xác nhận đặt xe | Deeplink của bạn | Kết thúc demo |

Thanh tab và các mục không thuộc luồng (Hoạt động, Thanh toán, Tài khoản) chỉ dựng tĩnh để giống app, không cần chức năng.

### 4.2 Kịch bản demo

**Kịch bản 1, một câu đủ thông tin (2 lượt):**

```text
Khách : Đặt Green SM Car từ Vincom Bà Triệu đến sân bay Nội Bài
Agent : Dạ, từ Vincom Center Bà Triệu đến Sân bay Nội Bài, đi Green SM Car.
        Mình mở màn xác nhận nhé?            (bản đồ hiện tuyến đường, quãng đường, thời gian cùng lúc)
Khách : Ừ, đúng rồi
Agent : Dạ, mình mở Green SM để bạn xác nhận. (app mở deeplink)
```

**Kịch bản 2, điểm đón là vị trí hiện tại, điểm đến mơ hồ, đổi dịch vụ:**

```text
Khách : Cho mình đi Vincom
Agent : Mình thấy 3 Vincom gần bạn, bạn chọn số mấy ạ?   (S3 hiện danh sách 1-3 kèm khoảng cách)
Khách : Số hai
Agent : Dạ, từ vị trí hiện tại đến Vincom Nguyễn Chí Thanh, Green SM Car. Mình mở màn xác nhận nhé?
Khách : Đổi sang xe máy
Agent : Dạ, đổi sang Green SM Bike. Mình mở màn xác nhận nhé?
Khách : Ok
```

**Kịch bản 3, ngắt lời và sửa điểm:**

```text
Khách : Đi từ Hồ Gươm đến Times City
Agent : Hồ Gươm có 4 điểm đón, bạn chọn...
Khách : (ngắt lời) Bưu điện Hà Nội
Agent : Dạ, đón ở Bưu điện Hà Nội, đến Times City, Green SM Car. Mình mở màn xác nhận nhé?
Khách : À không, đến Lotte Center
Agent : Dạ, đổi điểm đến thành Lotte Center Hà Nội. Mình mở màn xác nhận nhé?
```

Luôn hỗ trợ thêm: "thôi không đặt nữa" để dừng, gõ chữ vào ô tìm kiếm làm đường dự phòng, câu hỏi lạ thì đi qua LLM.

### 4.3 Quy tắc hội thoại

- Mỗi lượt tối đa một câu thông tin và một câu hỏi, mở đầu bằng "Dạ" để TTS phát sớm.
- Thiếu điểm đón thì dùng vị trí hiện tại. Không có GPS thì hỏi "Bạn đang đứng ở đâu ạ?".
- Thiếu dịch vụ thì mặc định Green SM Car và đọc rõ trong câu xác nhận để khách đổi được (cấu hình được).
- Không đọc danh sách lựa chọn. Chỉ đọc số lượng, danh sách hiện trên màn hình.
- Câu đồng ý tự nhiên ("đúng rồi", "ok", "đặt đi", "xác nhận") là đủ để mở deeplink, vì Green SM mới là nơi xác nhận cuối. Giữ chặn phủ định ("không", "chưa", "khoan", "đợi đã").
- Không nói giá. Nếu khách hỏi giá: "Giá chính xác sẽ hiện ở màn xác nhận của Green SM ạ."
- Câu xác nhận không đọc số phút, để không phải chờ Goong Direction. Quãng đường và thời gian hiện trên bản đồ. Agent chỉ đọc thời gian khi khách hỏi.
- 6 s sau khi agent sẵn sàng mà khách chưa nói, agent hỏi "Bạn muốn đi đâu ạ?".

---

## 5. Workstream A: UI Flutter khớp Green SM (Phương)

### A1. Thu thập tham chiếu (ngày 1, nửa ngày)

1. Trên máy Android demo, cài bản Green SM mới nhất, quay màn hình bằng `adb shell screenrecord` và chụp từng bước: Home, nhập điểm đến, chọn điểm đón trên bản đồ, chọn dịch vụ, thanh toán và ưu đãi, xác nhận, màn mở từ deeplink. Cần ít nhất 12 ảnh.
2. Ghi lại độ phân giải và mật độ màn hình để quy đổi px sang dp. Ví dụ 1080×2400 ở 420 dpi thì dp = px / 2,625.
3. Đưa ảnh vào Figma, đo: màu (thương hiệu, chữ chính và phụ, nền, surface, divider, chấm điểm đón, ghim điểm đến), font (họ, cỡ, độ đậm, line height), bo góc, bóng, lưới khoảng cách, kích thước icon, nút, bottom sheet và tay nắm.
4. Xác định font của app thật. Nếu không dùng được bản quyền, chọn font gần nhất hiển thị tốt dấu tiếng Việt và ghi lại lý do.
5. Logo và icon dịch vụ: xin bộ asset chính thức qua đầu mối GSM của chương trình. Chưa có thì vẽ lại bản đơn giản, không trích từ APK.

### A2. Design system

- `lib/app/theme/gsm_tokens.dart`: `GsmColors`, `GsmText`, `GsmRadius`, `GsmSpace`, `GsmShadow`, toàn bộ lấy từ số đo ở A1. Theme sáng như app thật.
- Component: `GsmSearchBar` (có mic), `GsmServiceTile`, `GsmAddressRow` (chấm đón, ghim đến), `GsmBottomSheet` (snap points), `GsmPrimaryButton`, `GsmServiceOption`, `GsmCandidateTile` (số thứ tự, tên, địa chỉ phụ, khoảng cách), `GsmBottomNav`.
- Đặt tên app demo là "Green SM Voice (Demo)" với icon khác app thật, vì cả hai cùng nằm trên máy demo.

### A3. Màn hình

- S1 Home, S3 Route, S2 Voice sheet theo bảng ở mục 4.1. Voice sheet là overlay sống xuyên suốt S1 và S3, không phải route riêng.
- Bản đồ: `maplibre_gl` (0.24.x) với style vector của Goong `https://tiles.goong.io/assets/goong_map_web.json?api_key=<MAP_TILES_KEY>`. Map tiles key khác REST key. Marker tuỳ biến, polyline giải mã từ `overview_polyline`, `fitBounds` có padding chừa chỗ cho bottom sheet. Tải style ngay từ Splash.
- Điều hướng bằng `go_router`, chuyển cảnh 200 đến 300 ms theo đường cong của app thật.

### A4. UX của lớp giọng nói

- Bấm mic: rung nhẹ, sheet trượt lên trong 150 ms, hiện "Đang nghe..." ngay vì audio đã được đệm.
- Trạng thái lấy từ `session.agent.agentState`: `listening` (vòng sóng màu thương hiệu), `thinking` (ba chấm), `speaking` (waveform từ audio track của agent). Khi `isBuffering` vẫn hiện "Đang nghe".
- Caption: lời khách dạng interim màu xám, final màu đậm. Lời agent đồng bộ theo audio.
- Chip slot: đỏ khi thiếu, vàng khi cần làm rõ, xanh khi đã chốt, theo `status` trong state v2.
- Danh sách lựa chọn: chạm vào một dòng cũng chọn được, app gửi `session.sendText("chọn số 2")`.
- Âm báo ngắn khi bắt đầu và kết thúc nghe.

### A5. Kiểm soát chất lượng hình ảnh

- Mỗi màn: chụp app demo và app thật trên cùng một máy, chồng 50% trong Figma, sửa lệch.
- Checklist: màu đúng mã đo được, cỡ chữ lệch tối đa 1 sp, khoảng cách lệch tối đa 2 dp, bo góc đúng, vị trí icon đúng.
- Khóa bằng golden test (`matchesGoldenFile`) cho 5 màn chính.
- Hiệu năng: chạy profile mode, giữ 60 fps. Widget bản đồ chỉ `watch` phần route và marker bằng `select`, caption không làm bản đồ rebuild, animation bọc `RepaintBoundary`.

---

## 6. Workstream B: LiveKit client và deeplink trên Flutter (Phương)

### B1. Gói thư viện

- Nâng `livekit_client` lên `^2.13.1`. Thêm `livekit_components` nếu cần visualizer có sẵn.
- Thêm `maplibre_gl`, `geolocator`, `url_launcher`, `go_router`. Giữ `flutter_riverpod`, `dio`, `permission_handler`.
- Gỡ khỏi bản demo: plugin wake word Kotlin/Swift, `WakeWordService`, `onnxruntime-android` trong [build.gradle](../olasm_mobile/android/app/build.gradle). Giữ mã ở nhánh riêng.

### B2. Token lấy sẵn, mỗi phiên một room

- Lấy sẵn một token khi vào Home và ngay sau mỗi phiên kết thúc. Token dùng một lần, vì mỗi token gắn với một room mới.
- Request gửi kèm GPS: `{device_id, trigger_source: "push_to_talk", location: {lat, lng, accuracy_m}, screen: "HOME"}`.
- Token cũ hơn TTL trừ 60 s thì lấy lại. Pre-connect vẫn đệm mic trong lúc chờ.

### B3. Session

```dart
final session = sdk.Session.fromFixedTokenSource(
  sdk.LiteralTokenSource(serverUrl: creds.serverUrl, participantToken: creds.participantToken),
  options: sdk.SessionOptions(
    room: sdk.Room(roomOptions: const sdk.RoomOptions(enableVisualizer: true)),
    preConnectAudio: true,                         // mặc định true, ghi rõ để không ai tắt nhầm
    agentConnectTimeout: const Duration(seconds: 8), // mặc định 20 s, rút ngắn để báo lỗi sớm
  ),
);
await session.start();
// session.agent.agentState : idle | initializing | listening | thinking | speaking
// session.messages         : UserTranscript, AgentTranscript, tin nhắn chữ
// session.sendText(text)   : đường dự phòng gõ chữ
// session.end()            : kết thúc, nhả mic
```

Chữ ký hàm lấy theo tài liệu `Session` và starter app Flutter chính thức. Cần kiểm lại với bản 2.13.x lúc code.

### B4. Nhận booking state

- Nghe `DataReceivedEvent` topic `greensm.booking_state.v2`, parse sang model bất biến, bỏ gói có `revision` nhỏ hơn gói đang giữ.
- Chia provider Riverpod: `voiceSessionProvider` (vòng đời, agent state), `bookingStateProvider` (state v2), `transcriptProvider` (messages). Màn hình chuyển S1 sang S3 theo `stage`.

### B5. RPC mở Green SM

- Sau khi room kết nối, đăng ký `localParticipant.registerRpcMethod('greensm.open_confirmation', handler)`.
- Handler dựng URL bằng `GreenSmDeeplinkBuilder`, gọi `launchUrl(uri, mode: LaunchMode.externalNonBrowserApplication)`, trả về `{"opened": true}` hoặc `{"opened": false, "reason": "NOT_INSTALLED"}`.
- Mở thành công thì `session.end()`. Khi app quay lại foreground thì hiện Home sạch kèm thông báo nhỏ.

### B6. Deeplink builder

- Thuần Dart, có unit test, đọc template từ `assets/config/greensm_deeplink.json` (mục 10.4).
- Mã hoá UTF-8 cho tên tiếng Việt bằng `Uri.encodeQueryComponent`, toạ độ 6 chữ số thập phân, ánh xạ mã dịch vụ, có URL dự phòng khi chưa cài app.
- Android: thêm `<queries>` với scheme của Green SM trong [AndroidManifest.xml](../olasm_mobile/android/app/src/main/AndroidManifest.xml). iOS: thêm `LSApplicationQueriesSchemes` vào [Info.plist](../olasm_mobile/ios/Runner/Info.plist).
- Test tay trước khi code: `adb shell am start -a android.intent.action.VIEW -d "<URL mẫu>"`.

### B7. Âm thanh và quyền

- Xin quyền mic và vị trí ở Splash. Tài liệu LiveKit lưu ý pre-connect cần quyền mic có sẵn.
- Android bật loa ngoài (`Hardware.instance.setSpeakerphoneOn(true)`), nếu không tiếng agent sẽ ra loa thoại. iOS dùng `playAndRecord` kèm `defaultToSpeaker`.
- Giữ echo cancellation, noise suppression, auto gain mặc định của SDK.

### B8. Đo phía client

Ghi mốc thời gian: bấm mic, `session.start()` xong, `agent.isConnected`, lần đầu `speaking`, lúc mở deeplink. In ra log và gửi kèm báo cáo benchmark.

---

## 7. Workstream C: Voice agent profile `greensm_demo` (Khánh)

### C0. Sửa cấu hình và nâng cấp (ngày 1)

- `.env` cho demo: `LIVEKIT_STT_MODEL=deepgram/nova-3`, `LIVEKIT_STT_LANGUAGE=vi`. LLM qua LiveKit Inference (`LIVEKIT_LLM_PROVIDER=livekit`) để khỏi cần OpenAI key, hoặc điền `OPENAI_API_KEY`. `LIVEKIT_TTS_PROVIDER=livekit`, `LIVEKIT_TTS_MODEL=cartesia/sonic-3.6`, `LIVEKIT_TTS_VOICE=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc` (giọng tiếng Việt nhóm dùng từ tháng 8). `VOICE_TRANSCRIPT_REWRITE_ENABLED=false`. Cấu hình đầy đủ ở mục 8A.4.
- Tránh snapshot `cartesia/sonic-3-2025-10-27`, bản này bị gỡ ngày 20/10/2026.
- Kiểm tra endpoint token hết 503, chạy `scripts/livekit_room_smoke.py`.
- Nâng cấp tùy chọn, giới hạn 2 giờ: `livekit-agents` 1.6.8 lên 1.8.8 (bản ổn định ngày 15/10/2026), đồng bộ phiên bản các plugin. Từ 1.8.7 cần `openai>=3.19`, xung đột với `aider-chat` đang ghim openai 2.20 trong [pyproject.toml](../pyproject.toml). Phải đưa `aider-chat` ra khỏi dependency runtime. Test hỏng thì giữ 1.6.8, demo vẫn chạy được.

### C1. Khung profile

- Biến `VOICE_AGENT_PROFILE=greensm_demo`, chọn trong [server.py](../src/voice_agent/server.py) lúc bắt đầu job. Mã mới đặt trong `src/voice_agent/greensm_demo/`.
- Dùng `EphemeralVoiceStateStore`, không restore và không save DB.
- Không chào khi khách bấm mic, vì audio đệm có thể đã chứa câu nói. Chỉ nhắc sau 6 s im lặng.
- Đọc GPS và màn hiện tại từ `ctx.job.metadata` (backend nhét vào dispatch metadata), có ngay lúc job bắt đầu, không phải chờ.
- `num_idle_processes=2`. Prewarm VAD, resolver, gazetteer, danh sách keyterm, HTTP client của Goong.
- Gọi `tts.prewarm()` ngay khi job bắt đầu. Đo được kết nối TTS lần đầu tốn 1,1 đến 2,4 s, các câu sau chỉ còn khoảng 0,3 s.

### C2. Cấu hình pipeline

```python
session = AgentSession(
    userdata=userdata,
    vad=prewarmed_vad,  # inference.VAD("silero"), giữ mặc định min_silence_duration=0,25 s
    stt=inference.STT(model="deepgram/nova-3", language="vi",
                      extra_kwargs={"keyterm": KEYTERMS},
                      fallback=[{"model": "assemblyai/universal-3-5-pro",
                                 "extra_kwargs": {"keyterms_prompt": KEYTERMS}}]),
    llm=inference.LLM(model=DEMO_LLM_MODEL, extra_kwargs={"parallel_tool_calls": False}),
    tts=inference.TTS(model="cartesia/sonic-3.6", voice=VI_VOICE_ID, language="vi",
                      fallback=[{"model": "cartesia/sonic-3.5", "voice": VI_VOICE_ID}]),
    turn_handling={
        "turn_detection": "vad",  # turn detector của LiveKit chưa hỗ trợ tiếng Việt
        "endpointing": {"mode": "dynamic", "min_delay": 0.35, "max_delay": 1.8},
        "interruption": {"enabled": True, "mode": "vad", "min_duration": 0.4, "min_words": 0,
                         "false_interruption_timeout": 1.5, "resume_false_interruption": True},
        "preemptive_generation": {"enabled": True, "preemptive_tts": False},
    },
    tts_text_transforms=["filter_emoji", "filter_markdown", vietnamese_tts_transform],
)
```

- Ở chế độ VAD, độ trễ chốt lượt bằng giá trị lớn hơn giữa khoảng lặng VAD và `min_delay`, nên hai số phải chỉnh cùng nhau.
- Lượt chỉ được chốt khi đã có final transcript. Báo cáo tháng 8 cho thấy end-of-turn gần bằng transcription delay. Với Nova-3, final về sau khoảng 480 ms, nên độ trễ chốt lượt sẽ quanh 0,5 s. Hạ `min_delay` dưới 0,35 s không giúp thêm, muốn nhanh hơn phải giảm độ trễ của STT.
- Preemptive generation khởi chạy LLM ngay khi có final transcript. Lượt nào fast path xử lý (`StopResponse`) thì bản sinh trước bị bỏ, chỉ tốn một ít compute. Khi bật, phải kiểm chứng tool không chạy trước lúc lượt được chốt. Vì vậy mọi tool phải idempotent.
- Nếu VAD hay cắt lời khi khách ngập ngừng ("đến... ờ... Times City"), A/B thử `assemblyai/universal-3-5-pro` với `turn_detection="stt"`. Model này đúng địa danh nhiều nhất trong lần đo nhưng ra final chậm hơn Nova-3 khoảng 240 ms.
- `vietnamese_tts_transform`: chuẩn hoá số nhà, số phút, phát âm "SM", tên riêng tiếng Anh. Bổ sung sau buổi nghe thử.

### C3. Fast path tất định (phần quan trọng nhất cho latency)

Trong `on_user_turn_completed`, và cả đường nhập chữ `_handle_text_input`:

1. Chuẩn hoá: bỏ từ đệm, sửa lỗi ASR quen thuộc bằng bảng alias.
2. Nhận diện bằng parser có sẵn theo thứ tự: huỷ hoặc dừng, đồng ý hoặc phủ định, chọn theo số hoặc theo tên, sửa slot có nhãn, câu đủ tuyến, chỉ điểm đến, loại dịch vụ.
3. Nếu hiểu được trọn câu: cập nhật draft, gọi resolver (mục 8), publish state v2, `session.say(template)`, rồi `raise StopResponse()`. Lượt này không gọi LLM. Goong Direction chạy nền khi đủ hai điểm, không chặn câu nói. Có route thì publish state thêm một lần để app vẽ polyline.
4. Không hiểu được thì để LLM xử lý với 4 tool ở C4.
5. Prefetch suy đoán: nghe sự kiện `user_input_transcribed` khi transcript còn interim, tách cụm địa điểm sau "đến", "tới", "từ", "ở", rồi gọi Goong AutoComplete chạy nền (debounce 150 ms, cache theo cụm đã chuẩn hoá). Khi chốt lượt, kết quả thường đã có.
6. Câu cố định ("Bạn muốn đi đâu ạ?", câu chuyển sang Green SM) có thể tổng hợp sẵn lúc prewarm rồi phát bằng `session.say(text, audio=...)`, TTFB gần như bằng 0. Làm ở giai đoạn tối ưu.
7. Một `asyncio.Lock` cho mỗi phiên bao quanh việc sửa draft. Kết quả lookup cũ hơn revision hiện tại thì bỏ.

### C4. Đường LLM dự phòng

- Instructions tiếng Việt khoảng 200 từ: vai trò trợ lý Green SM, nói ngắn, luôn dùng tool, không tự bịa địa điểm, giá, thời gian, đọc nguyên văn `spoken_prompt` do tool trả về.
- 4 tool, đều idempotent: `update_trip(pickup?, destination?, service?)`, `choose_option(index)`, `confirm_and_open_greensm()`, `cancel_trip()`.
- So 3 đến 4 model trên LiveKit Inference bằng bộ 40 lượt nói tiếng Việt, đo TTFT p50/p95 và độ đúng khi gọi tool: `openai/gpt-4.1-mini` (đang dùng), `openai/gpt-4.1-nano`, một bản `google/gemini-*-flash-lite`, `google/gemma-4-31b-it` (LiveKit khuyến nghị cho voice). Chọn model nhanh nhất có độ đúng từ 95% trở lên. Model dòng GPT-5 là model suy luận, phải đặt mức suy luận thấp nhất.
- Từ 1.8.3 có `reply_required` trong kết quả tool. Nếu nâng cấp xong, kiểm tra để bỏ vòng LLM thứ hai sau tool.

### C5. Booking state v2

Publish bằng `publish_data(reliable=True, topic="greensm.booking_state.v2")` sau mỗi thay đổi, trước khi nói. Schema ở mục 10.1. Giữ payload dưới 10 KB, polyline nén bằng định dạng encoded polyline.

### C6. Chuyển sang Green SM

1. Khách đồng ý thì kiểm tra draft đủ điểm đón, điểm đến, dịch vụ và có route.
2. Chuyển `stage` sang `handing_off`, publish state.
3. `handle = session.say("Dạ, mình mở Green SM để bạn xác nhận.", allow_interruptions=False)`.
4. Trong `handle.add_done_callback(...)`, theo đúng mẫu ở [agent.py:174-178](../src/voice_agent/agent.py#L174-L178), gọi `room.local_participant.perform_rpc(destination_identity=<khách>, method="greensm.open_confirmation", payload=<json mục 10.2>, response_timeout=5)`.
5. Ack thành công thì `stage=handed_off`, đóng session. Thất bại thì nói lý do, ví dụ máy chưa cài Green SM, và giữ phiên để khách thử lại.

### C7. Đo lường

- Bật `LIVEKIT_DEBUG_EVENT_LOG=true` khi benchmark. Thêm trường `turn_path` (fast hoặc llm), `goong_ms`, `prefetch_hit` vào event log.
- Chạy `aggregate_livekit_evaluation.py` để ra p50/p95 theo từng stage, cùng cách đo với báo cáo tháng 8 để so sánh được.

### C8. Khử nhiễu cho hội trường (tùy chọn)

Thử noise cancellation BVC của LiveKit ở đầu vào agent nếu gói LiveKit cho phép. Đo lại độ đúng ASR khi bật và tắt.

---

## 8. Workstream D: Độ chính xác địa điểm và lộ trình (Khánh)

### D1. Gazetteer demo có toạ độ

- `data/gazetteer/greensm_demo_places.json`: 30 đến 50 POI dùng trong kịch bản và câu hỏi dự phòng. Mỗi mục có tên chuẩn, alias ASR, địa chỉ, lat/lng của **điểm đón thật** (đã kiểm trên bản đồ), loại POI.
- Gộp với [hanoi_place_aliases.json](../data/gazetteer/hanoi_place_aliases.json) và [hanoi_landmark_pickup_points.json](../data/gazetteer/hanoi_landmark_pickup_points.json), bổ sung toạ độ.
- Danh sách gợi ý: Vincom Bà Triệu, Vincom Nguyễn Chí Thanh, Vincom Royal City, Nội Bài T1 và T2, Times City, Lotte Center, Keangnam, các điểm quanh Hồ Gươm, các cổng VinUni, Ga Hà Nội, Bến xe Mỹ Đình, Đại học Bách khoa Hà Nội, Aeon Long Biên, Sân vận động Mỹ Đình.

### D2. Goong client mới

- `src/backend/maps/providers/goong_places.py`: AutoComplete (bias theo `location` của khách, giới hạn 5 kết quả), Place Detail (lấy toạ độ), Reverse geocode (gắn nhãn vị trí hiện tại), Direction (`vehicle` là `car` hoặc `bike` theo dịch vụ).
- Một `httpx.AsyncClient` dùng chung, bật keep-alive. Timeout 1,2 đến 1,5 s, thử lại 1 lần khi lỗi kết nối. Cache LRU có TTL 10 phút, khoá theo cụm đã chuẩn hoá cộng toạ độ làm tròn.
- **Không rơi về mock.** Lỗi thì ném lỗi rõ ràng để agent hỏi lại.
- Tên tham số lấy theo tài liệu Goong (Goong tương thích định dạng Google Places). Kiểm trên Goong playground trước khi code. Lưu ý định dạng địa chỉ sau đợt sắp xếp đơn vị hành chính năm 2025, nhãn hiển thị phải khớp cách Green SM hiển thị.

### D3. Quy tắc chọn địa điểm

1. Khớp đúng tên hoặc alias trong gazetteer thì tự chọn.
2. Kết quả Goong: chấm điểm bằng độ giống tên chính (rapidfuzz) nhân với độ gần vị trí khách. Tự chọn khi kết quả đầu khớp tên đúng và bỏ xa kết quả thứ hai. Ngược lại thì hiện 3 đến 5 lựa chọn kèm khoảng cách.
3. Độ tin cậy ASR thấp và không khớp gazetteer thì xin nói lại.
4. Khách không nói điểm đón thì dùng vị trí hiện tại, gắn nhãn bằng reverse geocode.
5. Ngoài vùng phục vụ Hà Nội ([service_area.py](../src/backend/maps/service_area.py)) thì báo rõ.

### D4. Keyterm cho STT

- Danh sách tĩnh: tên chuẩn trong gazetteer, tên dịch vụ ("Green SM", "Green SM Car", "Green SM Bike", "Green SM Premium", "Xanh SM"). Kiểm giới hạn số keyterm của Deepgram.
- Danh sách động: khi đang có danh sách lựa chọn, thêm tên các lựa chọn vào keyterm cho lượt kế tiếp bằng `stt.update_options(extra={"keyterm": [...]})`. Bản Inference áp dụng qua `session.update` và tự hoãn tới hết câu nếu khách đang nói.
- Số đo: keyterm nâng tỷ lệ đúng địa danh của Nova-3 từ 60,3% lên 92,1%, và số câu bị mất final từ 5,6% xuống 0%.
- Alias bổ sung từ lỗi đo được: "Kangnam", "keo nam", "keng nam" thành Keangnam. "Charlotte Center", "lốt test center" thành Lotte Center. "ĐH" thành Đại học. "Time City" thành Times City.

### D5. Lộ trình

Goong Direction trả `distance`, `duration`, `overview_polyline`. App hiện quãng đường, thời gian và vẽ polyline. Agent chỉ đọc thời gian khi khách hỏi. Không tính và không nói giá.

### D6. Danh mục dịch vụ

`data/greensm_demo_services.json`: mã nội bộ, tên hiển thị, cách nói của khách, `vehicle` của Goong. Mã dịch vụ trong deeplink chỉ nằm trong cấu hình app (mục 10.4). Ví dụ: "xe máy" là Green SM Bike, "ô tô", "taxi" là Green SM Car, "mini" là Green SM Mini, "cao cấp", "premium" là Green SM Premium. Danh sách cuối chốt theo app thật và spec deeplink. Giữ ánh xạ ngược sang `VehicleType` cũ để không vỡ test.

---

## 8A. Chọn model STT và TTS bằng số đo (19/10/2026)

### 8A.1 Cách đo

- Đo từ máy dev ở Hà Nội qua LiveKit Inference, livekit-agents 1.6.8, dùng key LiveKit của dự án.
- **TTS:** mỗi model đọc 6 câu của agent và 12 câu của khách. TTFB tính từ lúc gửi chữ tới khung audio đầu tiên. Câu đầu là lần "lạnh", phải mở websocket mới.
- **STT:** 12 câu đặt xe × 3 giọng tổng hợp (Cartesia, Inworld, xAI), tổng 36 câu. Audio được đẩy theo thời gian thực trên một stream liên tục như phiên thật, mỗi câu cách nhau 2,5 s im lặng.
  - Final latency: từ lúc hết tiếng tới final transcript cuối của câu. Đây là khoảng LiveKit phải chờ trước khi chốt lượt.
  - Địa danh đúng: tên riêng xuất hiện đúng cả dấu trong transcript.
- **Giới hạn:** giọng tổng hợp sạch hơn giọng người. Đo từ Việt Nam nên có cộng độ trễ mạng tới gateway. Kết quả dùng để xếp hạng, phải đo lại bằng giọng thật (mục 11).
- Harness đo dạng streaming (`tts_bench.py`, `stt_bench.py`) và dữ liệu thô hiện nằm ngoài repo, trên máy của Khánh.

### 8A.2 STT

| Cấu hình | Final p50 | Final p90 | WER | Địa danh đúng | Ghi chú |
|---|---|---|---|---|---|
| Deepgram Nova-3, `multi` (cấu hình `.env` hiện tại) | 477 ms | 541 ms | 0,885 | 15,9% | Gần như không nhận tiếng Việt |
| Deepgram Nova-3, `vi` | 478 ms | 537 ms | 0,222 | 60,3% | 5,6% câu mất final |
| **Deepgram Nova-3, `vi` + keyterm** | **483 ms** | **539 ms** | **0,095** | **92,1%** | Không mất câu nào |
| Deepgram Nova-3, `vi` + keyterm + `numerals` | 482 ms | 544 ms | 0,103 | 90,5% | Không cải thiện |
| Deepgram Nova-2, `vi` | 471 ms | 552 ms | 0,134 | 74,6% | Không có keyterm |
| **AssemblyAI Universal-3.5 Pro, `vi` + keyterm** | **725 ms** | **790 ms** | **0,091** | **96,8%** | Chính xác nhất, chậm hơn khoảng 240 ms |
| AssemblyAI u3-rt-pro, `vi` + keyterm, `min_latency` | 775 ms | 1.027 ms | 0,087 | 96,8% | |
| AssemblyAI Universal-3.5 Pro, nới tham số end-of-turn | 790 ms | 1.071 ms | 0,100 | 92,1% | Không nhanh hơn |
| AssemblyAI Universal-3.6 Pro, `vi` + keyterm | 748 ms | 864 ms | 0,121 | 85,7% | |
| Cartesia Ink-Whisper, `vi` | 577 ms | 666 ms | 0,316 | 57,1% | |
| Speechmatics Linden-1, `vi` + vocab | 932 ms | 1.054 ms | 0,141 | 85,7% | |
| xAI STT-2, `vi` | 1.425 ms | 1.813 ms | 0,133 | 69,8% | |
| Gemini 3.5 Transcribe Live, `vi` | 1.536 ms | 1.585 ms | 0,075 | 87,3% | Chậm, có lần nghe "Green SM Car" thành "GrabCar" |
| ElevenLabs Scribe v2 realtime, OpenAI GPT-Live Transcribe | lỗi | | | | Gateway không tạo được phiên |

Kết luận:

- **Chọn** `deepgram/nova-3`, `language="vi"`, có keyterm. Nhanh nhất nhóm, đúng 92,1% địa danh, không mất câu nào.
- **Dự phòng tự động** bằng tham số `fallback` của Inference sang `assemblyai/universal-3-5-pro` có keyterm. Model này đúng 96,8% địa danh nhưng chậm hơn khoảng 240 ms, nên chỉ chạy khi provider chính lỗi.
- **Chế độ chính xác:** nếu bộ giọng thật ở Ngày 8 cho thấy Nova-3 sai địa danh nhiều, đổi AssemblyAI thành model chính và chấp nhận chậm thêm khoảng 240 ms.
- **Không dùng** `multi`, Gemini Transcribe, xAI STT-2. Các cấu hình này sai nhiều hoặc ra final chậm hơn 1,4 s.
- Lỗi còn lại của Nova-3 đều là tên riêng nước ngoài hoặc chữ viết tắt, sửa ở tầng alias (mục D4).
- Câu "đặt đi" có lúc bị nghe thành "đặc bi" hoặc "đặc biệt". Khi `stage` là `ready_to_confirm`, so khớp câu đồng ý theo dạng bỏ dấu. Câu "chọn số" bị thiếu số thì hỏi lại số.

### 8A.3 TTS

| Model | TTFB lần đầu | TTFB ấm p50 | TTFB ấm max | Độ rõ, CER đọc lại bằng AssemblyAI / Deepgram |
|---|---|---|---|---|
| **Cartesia Sonic-3.6** | 1.439 ms | **275 ms** | 311 ms | 0,066 / 0,093 |
| Cartesia Sonic-3.5 | 1.486 ms | 292 ms | 305 ms | 0,040 / 0,211 |
| Cartesia Sonic-3 | 2.234 ms | 346 ms | 372 ms | 0,054 / 0,085 |
| Inworld TTS-2, giọng mặc định | 1.133 ms | 328 ms | 341 ms | 0,068 / 0,182 |
| xAI TTS-1, giọng mặc định | 1.512 ms | 360 ms | 417 ms | 0,047 / 0,163 |
| Gemini 3.8 Flash TTS | 2.377 ms | 954 ms | 1.012 ms | 0,061 / 0,122 |
| ElevenLabs Flash v2.5 | lỗi | | | Gateway báo không có model |

Độ rõ được tính bằng cách cho STT nghe lại 6 câu của agent rồi tính CER. Số câu ít nên cột này chỉ dùng để loại model đọc sai rõ ràng.

Kết luận:

- **Chọn** `cartesia/sonic-3.6` với giọng tiếng Việt `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`. TTFB ấm thấp nhất và độ rõ tốt.
- **Prewarm là bắt buộc.** Lần đầu mất 1,1 đến 2,4 s để mở websocket. Gọi `tts.prewarm()` ngay khi job bắt đầu, rồi kiểm tra TTFB câu nói đầu tiên trong log.
- **Dự phòng:** `fallback` sang `cartesia/sonic-3.5` cùng giọng. Muốn dự phòng khác provider thì thêm Inworld TTS-2 sau khi chọn được giọng tiếng Việt.
- **Không dùng** Gemini Flash TTS cho hội thoại, mỗi câu chờ gần 1 s.
- Độ tự nhiên vẫn phải chốt bằng tai. Hai người nghe file WAV của ba bản Sonic cùng giọng, nghe thêm 2 đến 3 giọng tiếng Việt khác của Cartesia.

### 8A.4 Cấu hình chốt

```env
LIVEKIT_STT_PROVIDER=livekit
LIVEKIT_STT_MODEL=deepgram/nova-3
LIVEKIT_STT_LANGUAGE=vi
LIVEKIT_TTS_PROVIDER=livekit
LIVEKIT_TTS_MODEL=cartesia/sonic-3.6
LIVEKIT_TTS_VOICE=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc
LIVEKIT_TTS_LANGUAGE=vi
VOICE_TRANSCRIPT_REWRITE_ENABLED=false
```

Keyterm và fallback chưa có biến cấu hình. Cần sửa `build_stt` và `build_tts` trong [model_factory.py](../src/voice_agent/model_factory.py) để truyền `extra_kwargs` và `fallback` như snippet ở C2. Danh sách keyterm sinh từ gazetteer demo cộng tên dịch vụ, tối đa 100 cụm.

---

## 8B. Wake word với livekit-wakeword (tùy chọn, có cổng nghiệm thu)

### 8B.1 Đánh giá thư viện

| Mục | Nội dung |
|---|---|
| Bản chất | Thư viện Apache-2.0 của LiveKit, kế thừa openWakeWord. Audio đi qua model mel và model embedding giọng nói của Google (đóng băng), tạo ma trận 16 × 96, rồi vào đầu phân loại Conv-Attention |
| Kết quả công bố | Trên tập "hey livekit" tiếng Anh: báo nhầm 0,08 lần mỗi giờ, recall 86,1%. openWakeWord trên cùng tập là 8,50 lần mỗi giờ và 68,6% |
| Tiếng Việt | Có, sinh dữ liệu bằng TTS VoxCPM. README cảnh báo model đa ngôn ngữ kém chính xác hơn tiếng Anh, vì embedding được huấn luyện bằng tiếng Anh. Khuyên dùng 50 đến 100 `voice_design_prompts` và tăng số mẫu |
| Nền tảng | Python (huấn luyện, suy luận), Rust crate (nhúng sẵn mel và embedding), Swift package cho iOS 16+. **Không có Android, Kotlin hay Flutter** |
| Đầu ra | ONNX, input `embeddings` (1, 16, 96), output `score`. Cửa sổ khoảng 2 s, ngưỡng mặc định 0,5, debounce 2 s |
| Tích hợp LiveKit | Ví dụ hello-wakeword chạy wake word trên thiết bị, phát chime rồi mới kết nối room. Không đề cập pre-connect audio |

### 8B.2 So với code hiện tại

- [hey_olasm_vietnamese.yaml](../configs/hey_olasm_vietnamese.yaml) dùng schema tự đặt, không khớp schema thật của thư viện (`model_name`, `target_phrases`, `n_samples`, `model.model_type`, `model.model_size`, `steps`, `target_fp_per_hour`, `tts_backend`). Phải viết lại theo file `configs/prod_voxcpm.yaml` của thư viện.
- [train_export_wakeword.py](../scripts/train_export_wakeword.py) chỉ dựng và xuất một mạng chưa huấn luyện, không có bước sinh dữ liệu, tăng cường hay huấn luyện. Thay bằng CLI `livekit-wakeword setup`, `run`, `eval`.
- Engine Android: [WakeWordPlugin.kt:161-162](../olasm_mobile/android/app/src/main/kotlin/com/olasm/mobile/wakeword/WakeWordPlugin.kt#L161-L162) đưa 32 giá trị log-mel của một khung vào [OnnxWakeEngine.kt:38-44](../olasm_mobile/android/app/src/main/kotlin/com/olasm/mobile/wakeword/OnnxWakeEngine.kt#L38-L44), nơi cần vector embedding 96 chiều. `System.arraycopy` chép 96 phần tử từ mảng 32 phần tử nên ném lỗi ngay. Engine cũng thiếu hai model mel và embedding. Không vá, làm lại theo 8B.4.
- Ngưỡng 0,68 đang hard-code trong app là ngưỡng tối ưu của model "hey livekit". Model mới phải chọn ngưỡng từ đường DET của chính nó.

### 8B.3 Huấn luyện

1. Cụm từ đề xuất: **"Green SM ơi"**. Dài 4 đến 5 âm tiết, gắn thương hiệu, ít trùng lời nói thường. Nghe thử mẫu VoxCPM sinh ra cho cả cách viết "Green SM ơi" và cách viết theo phát âm "grin ét em ơi", chọn cách cho ra giọng Việt đúng.
2. Cấu hình theo `prod_voxcpm.yaml`: `tts_backend: voxcpm`, `conv_attention` cỡ medium, 50.000 mẫu huấn luyện và 10.000 mẫu kiểm định, 50 đến 100 `voice_design_prompts` phủ giọng Bắc, Trung, Nam, nam và nữ, già và trẻ, nói nhanh và chậm.
3. Tự thêm câu âm tính, vì thư viện ghi rõ âm tính tự sinh thiên về tiếng Anh: "Green", "em ơi", "anh ơi", "xanh ơi", "Grab ơi", "Be ơi", "gọi xe", "xin chào", "ét em".
4. Chạy trên GPU đám mây bằng file SkyPilot mẫu của thư viện. Khởi chạy từ Ngày 2 để chạy nền.

### 8B.4 Tích hợp vào app

- **iOS:** dùng thẳng Swift package `LiveKitWakeWord` (`WakeWordListener`), bọc bằng method channel.
- **Android:** port đúng pipeline sang Kotlin trên ONNX Runtime Android, thư viện này đã có trong [build.gradle](../olasm_mobile/android/app/build.gradle). Pipeline gồm khung 80 ms, model mel, model embedding, cửa sổ 16 embedding, đầu phân loại.
  - Viết test đối chiếu: cùng một file WAV, điểm của bản Kotlin lệch tối đa 0,01 so với `WakeWordModel.predict` của Python.
  - Phương án dự phòng: gọi Rust crate qua FFI, vì crate đã nhúng sẵn mel và embedding.
- Chỉ nghe khi app demo ở foreground, không cần foreground service.
- Khi phát hiện: dừng engine và nhả `AudioRecord`, phát chime ngắn, gọi `session.start()` có pre-connect audio. Không mở hai luồng thu âm cùng lúc trên Android.
- Người dùng chờ chime rồi mới nói, giống ví dụ hello-wakeword. Nói liền một hơi "Green SM ơi đặt xe..." có thể mất vài âm tiết đầu, chấp nhận được cho demo.

### 8B.5 Cổng nghiệm thu (xong trước Ngày 9)

- Thu 200 lần nói "Green SM ơi" từ ít nhất 10 người, và ít nhất 3 giờ âm thanh nền tiếng Việt gồm hội thoại, TV, đường phố. Đo bằng `livekit-wakeword eval`, chọn ngưỡng từ đường DET.
- Đạt khi recall ≥ 85% trong phòng yên tĩnh và báo nhầm ≤ 0,5 lần mỗi giờ trên âm thanh nền tiếng Việt.
- Không đạt thì demo dùng bấm mic, wake word chỉ trình bày như một hướng kỹ thuật.

---

## 9. Kỹ thuật latency

### 9.1 Ngân sách theo stage (p50 mục tiêu)

| Stage | Mục tiêu | Cách đạt |
|---|---|---|
| Bấm mic đến thu âm | ≤ 100 ms | Pre-connect audio, quyền mic xin sẵn |
| Bấm mic đến agent nhận audio | ≤ 1,5 s | Token lấy sẵn, idle process, không DB, không chào |
| Hết câu đến chốt lượt | 0,50 đến 0,60 s | Chờ final của Nova-3 (đo 483 ms p50), VAD 0,25 s, `min_delay` 0,35 s |
| STT final | nằm trong bước trên | Deepgram Nova-3 `vi` + keyterm |
| Xử lý lượt, fast path | ≤ 50 ms cộng lookup | Parser, gazetteer, Goong đã prefetch |
| LLM TTFT, khi cần | ≤ 500 ms | Model nhanh, prompt ngắn, 4 tool, preemptive generation |
| Tool hoặc lookup | ≤ 250 ms | Bộ nhớ trong, cache, keep-alive |
| TTS TTFB | ≤ 300 ms | Cartesia Sonic-3.6 (đo 275 ms), prewarm, câu mở đầu ngắn |
| Mạng và jitter buffer | khoảng 100 đến 150 ms | LiveKit edge |
| **Tổng, fast path** | **khoảng 0,9 đến 1,0 s** | |
| **Tổng, đường LLM** | **khoảng 1,3 đến 1,6 s** | |

### 9.2 Chọn vị trí chạy agent (đo, không đoán)

- LiveKit khuyến nghị đặt agent gần chuỗi model STT, LLM, TTS. Chặng âm thanh từ người dùng tới agent đi trên mạng riêng của LiveKit nên chịu được khoảng cách xa.
- Agent deploy lên LiveKit Cloud chạy cùng trung tâm dữ liệu với LiveKit Inference. Vùng hiện có: `us-east`, `eu-central`, `ap-south` (Mumbai).
- Goong đặt server ở Việt Nam, nên mỗi lookup từ `us-east` mất thêm khoảng một vòng xuyên Thái Bình Dương. Prefetch và cache ở C3, D2 dùng để bù phần này.
- Quy trình: chạy 20 phiên kịch bản 1 và 2 từ Hà Nội với ba phương án: (a) LiveKit Cloud `us-east`, (b) LiveKit Cloud `ap-south`, (c) worker tự chạy trên VPS Singapore. Chọn phương án có e2e p50 và p95 tốt nhất.
- Gói Build miễn phí của LiveKit Cloud có thể khởi động nguội vài giây. Demo dùng worker tự chạy có idle process, hoặc gói trả phí.

### 9.3 Checklist cấu hình

- [ ] STT `deepgram/nova-3`, `language="vi"`, keyterm, fallback AssemblyAI Universal-3.5 Pro
- [ ] TTS `cartesia/sonic-3.6` giọng tiếng Việt, `tts.prewarm()`, đã nghe thử
- [ ] VAD `inference.VAD("silero")` prewarm, giữ `min_silence_duration` 0,25 s
- [ ] `endpointing` dynamic, `min_delay` 0,35 s, `max_delay` 1,8 s
- [ ] Interruption VAD, `min_duration` 0,4 s, `min_words` 0
- [ ] Preemptive generation bật
- [ ] Rewrite transcript tắt
- [ ] `EphemeralVoiceStateStore`, không chào khi bấm mic
- [ ] `num_idle_processes=2`, Goong client keep-alive
- [ ] Token lấy sẵn, `preConnectAudio: true`, quyền xin ở Splash

---

## 10. Hợp đồng dữ liệu

### 10.1 `greensm.booking_state.v2` (agent gửi app)

```json
{
  "schema": "greensm.booking_state.v2",
  "revision": 7,
  "stage": "ready_to_confirm",
  "pickup": {"status": "resolved", "source": "current_location", "name": "Vị trí hiện tại",
             "address": "12 Chùa Bộc, Đống Đa, Hà Nội", "lat": 21.007412, "lng": 105.828613},
  "destination": {"status": "resolved", "source": "gazetteer", "name": "Sân bay Nội Bài - Ga T1",
                  "address": "Sóc Sơn, Hà Nội", "lat": 21.218716, "lng": 105.804176},
  "service": {"status": "resolved", "id": "GSM_CAR", "label": "Green SM Car", "defaulted": true},
  "candidates": null,
  "route": {"distance_m": 27450, "duration_s": 2580, "polyline": "<encoded>", "provider": "goong"},
  "failure": null
}
```

- `stage`: `collecting`, `disambiguating`, `ready_to_confirm`, `handing_off`, `handed_off`, `abandoned`.
- `candidates` khi mơ hồ: `{"target": "destination", "query": "vincom", "options": [{"index": 1, "name": "...", "subtitle": "...", "distance_km": 1.2}]}`.
- Toạ độ trong ví dụ chỉ để minh hoạ định dạng.

### 10.2 RPC `greensm.open_confirmation` (agent gọi app)

```json
{"trip_ref": "gsmdemo_7f3a", "service_id": "GSM_CAR",
 "pickup": {"name": "...", "address": "...", "lat": 21.007412, "lng": 105.828613},
 "destination": {"name": "...", "address": "...", "lat": 21.218716, "lng": 105.804176},
 "route": {"distance_m": 27450, "duration_s": 2580}}
```

App trả `{"opened": true}` hoặc `{"opened": false, "reason": "NOT_INSTALLED|LAUNCH_FAILED|INVALID_PAYLOAD|DEEPLINK_NOT_CONFIGURED"}`.

Bản đầy đủ và chi tiết nhất của hợp đồng nằm ở mục 5 của hai prompt trong `docs/prompts/`. Hai prompt dùng chung một khối giống hệt nhau.

### 10.3 Token request (app gửi backend)

Mở rộng [MobileTokenRequestDTO](../src/backend/schemas/mobile.py): thêm `location {lat, lng, accuracy_m}` và `screen`. Sửa lỗi `trigger_source` bằng cách cho phép `push_to_talk`, `wake_word`, `prefetch`. Backend đưa các trường này vào dispatch metadata, `schema_version` "2".

### 10.4 Cấu hình deeplink (`assets/config/greensm_deeplink.json`)

```json
{
  "template": "<DÁN URL MẪU CỦA BẠN, ví dụ scheme://host/path?pickup_lat={pickup_lat}&...>",
  "coordinate_precision": 6,
  "service_codes": {"GSM_BIKE": "<mã>", "GSM_CAR": "<mã>"},
  "fallback_url": "<link cửa hàng ứng dụng hoặc web>"
}
```

Biến hỗ trợ: `{pickup_lat}`, `{pickup_lng}`, `{pickup_name}`, `{pickup_address}`, `{dest_lat}`, `{dest_lng}`, `{dest_name}`, `{dest_address}`, `{service_code}`. Chốt khi có spec deeplink thật.

---

## 11. Kiểm thử và nghiệm thu

| Lớp | Nội dung | Ngưỡng đạt |
|---|---|---|
| Python unit | Parser trên 60 câu tiếng Việt (golden JSON), Goong client với fixture ghi sẵn, schema state v2, payload RPC | 100% pass, toàn bộ test cũ vẫn xanh |
| Hành vi agent | 15 hội thoại bằng công cụ test của LiveKit Agents: happy path, mơ hồ, sửa, ngắt lời, đổi dịch vụ, huỷ, không tìm thấy, ASR kém | 15/15 |
| ASR | 50 câu × 3 giọng người thật Bắc, Trung, Nam, có ồn và không ồn. Đo bằng harness streaming như mục 8A, so Nova-3 với AssemblyAI Universal-3.5 Pro | Đúng 100% POI kịch bản sau alias, final p50 ≤ 600 ms |
| Wake word | 200 lần nói của 10 người, 3 giờ âm thanh nền tiếng Việt, `livekit-wakeword eval` | Cổng ở mục 8B.5 |
| Địa điểm | 50 POI Hà Nội ngẫu nhiên qua resolver | ≥ 90% đúng trong top 3 |
| Latency | 20 phiên, p50/p95 theo stage | Ngưỡng ở mục 1 |
| Flutter | Unit test deeplink builder và parser state, golden test 5 màn, integration test phát lại luồng state đã ghi (không cần mạng) | Pass |
| Thiết bị | Quyền, loa, 4G và Wi-Fi, có và chưa cài Green SM, deeplink đúng dữ liệu, 10 phiên liên tiếp, tắt mở app, mất mạng rồi có lại | 10/10 |

Bộ đồ ngày demo: 2 điện thoại (chính và dự phòng) đã đăng nhập Green SM, bộ phát 4G riêng, video quay sẵn toàn luồng, thẻ kịch bản câu nói, dashboard LiveKit mở sẵn.

---

## 12. Lịch 10 ngày và phân công

Ví dụ nếu bắt đầu thứ Hai 19/10/2026 thì Ngày 10 là thứ Sáu 30/10/2026.

| Ngày | Phương (Mobile, UI) | Khánh (Agent, Backend) | Mốc |
|---|---|---|---|
| 1 | Chụp tham chiếu Green SM, đo token | Sửa `.env`, hết 503, smoke test, nâng cấp agents (2 giờ) | Có URL deeplink mẫu chạy được bằng adb |
| 2 | Design system, component. Khởi chạy huấn luyện wake word trên GPU, chạy nền | Profile `greensm_demo`, store ephemeral, cấu hình STT và TTS theo mục 8A | |
| 3 | Màn Home và bản đồ Goong | Goong client, gazetteer có toạ độ, keyterm | |
| 4 | Màn Route, Voice sheet, chạy bằng state giả. Deeplink builder | Fast path, state v2, danh sách lựa chọn, route, RPC chuyển | Hai bên chạy độc lập bằng dữ liệu giả |
| 5 | Ghép Session API, token lấy sẵn, agent state, transcript | Ghép metadata GPS, sửa lỗi ghép | **Kịch bản 1 chạy E2E tới deeplink** |
| 6 | Danh sách lựa chọn chạm được, gõ chữ dự phòng | Kịch bản 2 và 3, đường LLM 4 tool | 3 kịch bản chạy E2E |
| 7 | Đo phía client | Benchmark 20 phiên, chọn LLM và vị trí agent, chỉnh VAD | Đạt ngưỡng latency |
| 8 | Sửa UI theo so pixel. Đánh giá wake word theo cổng 8B.5 | ASR 50 câu × 3 giọng người thật, chỉnh alias và keyterm, chốt Nova-3 hay AssemblyAI | Đạt ngưỡng độ đúng |
| 9 | Golden test, tối ưu 60 fps. Tích hợp wake word Android nếu đạt cổng | Prefetch suy đoán, audio dựng sẵn, nghe thử TTS | |
| 10 | Tổng duyệt 10 lần × 2 máy, quay video dự phòng | Như bên trái | **Sẵn sàng demo** |

Làm sau nếu còn thời gian: bản iOS kèm wake word qua Swift package, tự bật voice khi vào Home để rảnh tay hoàn toàn, khử nhiễu BVC, A/B AssemblyAI với `turn_detection="stt"`.

---

## 13. Rủi ro và dự phòng

| Rủi ro | Mức | Phòng ngừa |
|---|---|---|
| Spec deeplink chưa rõ hoặc Green SM đòi đăng nhập | Cao | Chốt URL mẫu ngày 1, test bằng adb, đăng nhập sẵn Green SM trên máy demo |
| STT nghe sai địa danh | Cao | Nova-3 `vi` + keyterm (đo được 92,1%), alias, fallback AssemblyAI, danh sách lựa chọn trên màn hình, gõ chữ dự phòng |
| Wake word tiếng Việt kém chính xác hoặc báo nhầm nhiều | Trung bình | Cổng nghiệm thu ở mục 8B.5, không đạt thì dùng bấm mic |
| Mạng hội trường kém | Cao | 4G riêng, video dự phòng |
| Goong hết quota hoặc chậm từ vùng agent | Trung bình | Cache, prefetch, gazetteer cho POI kịch bản, đo vị trí agent |
| Chưa được dùng asset thương hiệu | Trung bình | Xin GSM sớm, có bản vẽ lại |
| LiveKit Build plan khởi động nguội | Trung bình | Worker tự chạy có idle process, hoặc gói trả phí |
| Tiếng vọng, âm lượng loa | Trung bình | AEC mặc định, bật loa ngoài, thử trên đúng máy demo |
| Nâng cấp agents 1.8 xung đột openai | Thấp | Gỡ `aider-chat` khỏi runtime, không được thì giữ 1.6.8 |

---

## 14. Câu hỏi cần chốt trước Ngày 1

1. **Deeplink:** scheme, host, path. Nhận toạ độ hay place_id của Green SM? Có nhận tên, địa chỉ, mã dịch vụ không? Màn đích có hiện giá không? Chưa đăng nhập thì sao? Có chạy trên cả Android và iOS không? Gửi 1 đến 2 URL mẫu đã chạy được.
2. **Thành phố và danh sách POI** cho demo, mặc định là Hà Nội.
3. **Danh sách dịch vụ** cần hỗ trợ và mã tương ứng trong deeplink.
4. **Tên trợ lý:** "Trợ lý Green SM" hay "OlaSM".
5. **Quyền dùng** logo, icon, font của Green SM.
6. **Gói LiveKit Cloud** đang dùng, và có được deploy agent lên LiveKit Cloud không.
7. **Giá:** giữ nguyên tắc không hiển thị giá trong demo, hay hiện giá ước tính có ghi rõ "ước tính".
8. **Wake word:** dùng cụm "Green SM ơi" hay cụm khác, và demo có bắt buộc rảnh tay hoàn toàn không. Có GPU đám mây để huấn luyện không.

---

## 15. Nguồn tham khảo

- LiveKit Flutter: [PreConnectAudioBuffer](https://docs.livekit.io/reference/client-sdk-flutter/livekit_client/PreConnectAudioBuffer-class.html), [changelog livekit_client](https://pub.dev/packages/livekit_client/changelog), [Session](https://pub.dev/documentation/livekit_client/latest/livekit_client/Session-class.html), [SessionOptions](https://pub.dev/documentation/livekit_client/latest/livekit_client/SessionOptions-class.html), [Agent](https://pub.dev/documentation/livekit_client/latest/livekit_client/Agent-class.html), [agent-starter-flutter](https://github.com/livekit-examples/agent-starter-flutter), [Token endpoint](https://docs.livekit.io/frontends/build/authentication/endpoint/), [Agent state](https://docs.livekit.io/frontends/build/agent-state/)
- LiveKit Agents: [Turn detection](https://docs.livekit.io/agents/logic/turns/), [Turn tuning](https://docs.livekit.io/agents/logic/turns/tuning/), [Turn detector](https://docs.livekit.io/agents/logic/turns/turn-detector), [STT models](https://docs.livekit.io/agents/models/stt/), [Deepgram](https://docs.livekit.io/agents/models/stt/deepgram/), [TTS models](https://docs.livekit.io/agents/models/tts/), [LLM models](https://docs.livekit.io/agents/models/llm/), [PyPI livekit-agents](https://pypi.org/project/livekit-agents/), [Release notes](https://github.com/livekit/agents/releases), [Agent deployment regions](https://docs.livekit.io/deploy/admin/regions/agent-deployment)
- Latency: [Understand and improve agent latency](https://livekit.com/blog/understand-and-improve-agent-latency), [Building performant voice agents in India](https://livekit.com/blog/building-performant-voice-agents-india)
- Deepgram: [Nova-3 thêm 11 ngôn ngữ, có tiếng Việt](https://deepgram.com/learn/deepgram-expands-nova-3-with-11-new-languages-across-europe-and-asia)
- Goong: [REST API](https://docs.goong.io/rest/), [MapLibre trên Flutter với Goong](https://help.goong.io/kb/app/flutter/tich-hop-maplibre-treemn-nen-ban-do-goong-trong-flutter/), [maplibre_gl](https://pub.dev/packages/maplibre_gl)
- Wake word: [livekit-wakeword](https://github.com/livekit/livekit-wakeword), [hello-wakeword](https://github.com/livekit-examples/hello-wakeword)
- Số đo STT và TTS ở mục 8A: nhóm tự đo ngày 19/10/2026 qua LiveKit Inference
- Green SM: [Green SM Car và danh sách dịch vụ](https://www.greensm.com/vn-vi/greensm-car), [Nhận diện ứng dụng mới](https://www.greensm.com/vn-vi/news/xanh-sm-thay-doi-nhan-dien-ung-dung-moi)
