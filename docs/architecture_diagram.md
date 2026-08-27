# System design — AloSM Voice AI

Cập nhật: 2026-08-27
Trạng thái: MVP demo-ready; các phần tích hợp production được đánh dấu rõ bên dưới.

## 1. Mục đích và phạm vi

AloSM là trợ lý đặt xe bằng tiếng Việt trên web. Người dùng có thể nói hoặc nhập tin nhắn để:

- tìm và chọn điểm đón, điểm đến;
- chọn loại xe;
- xem báo giá ước tính;
- xác nhận, tạo và tra cứu chuyến;
- thay đổi địa điểm hoặc loại xe trước khi đặt;
- hủy chuyến theo cơ chế xác nhận hai bước;
- hỏi thông tin trong kho FAQ/chính sách đã được phê duyệt;
- yêu cầu chuyển sang nhân viên hỗ trợ.

System design này mô tả runtime hiện tại, không mô tả các tính năng còn nằm trong PRD cũ nhưng chưa được triển khai, như thanh toán thật, hoàn tiền, điều phối tài xế thật hoặc gọi khẩn cấp.

## 2. Kiến trúc tổng thể

~~~mermaid
flowchart LR
    U[Người dùng trên trình duyệt]
    FE[React/Vite Web App]
    API[FastAPI REST API]
    AUTH[Auth + Policy]
    SES[Session Service]
    AGENT[Core Agent<br/>typed actions + guardrails]
    DOMAIN[Booking / Handoff / Maps / Quotes / Trips]
    DB[(SQLAlchemy<br/>SQLite local / PostgreSQL-Supabase shared)]
    STORE[(DatabaseVoiceStateStore)]
    LK[LiveKit Cloud / Server<br/>Room + token]
    WORKER[LiveKit Agent Worker<br/>AgentServer + JobContext]
    AS[AgentSession<br/>một session cho một cuộc hội thoại]
    STT[STT<br/>ElevenLabs Scribe realtime]
    LLM[LLM<br/>OpenAI via LiveKit plugin]
    TTS[TTS<br/>Google Gemini Flash TTS]
    FALLBACK[TTS fallback<br/>Google Chirp 3 HD]
    CAT[Local catalogs<br/>places / pricing / FAQ]
    MAPS[Optional maps adapters<br/>Nominatim / OSRM]
    OP[Operator UI]
    HUMAN[Nhân viên hỗ trợ]

    U --> FE
    FE -->|HTTP JSON| API
    FE <-->|LiveKit token + room| LK
    API --> AUTH
    API --> SES
    SES --> AGENT
    API --> DOMAIN
    AUTH --> DB
    SES --> DB
    DOMAIN --> DB
    AGENT --> CAT
    DOMAIN --> CAT
    DOMAIN -. optional .-> MAPS
    LK <--> WORKER
    WORKER --> AS
    AS --> STT
    AS --> LLM
    AS --> TTS
    TTS -. lỗi / timeout .-> FALLBACK
    WORKER --> AGENT
    WORKER --> STORE
    STORE --> DB
    OP --> API
    OP -->|operator token / cùng room| LK
    HUMAN --> OP
    WORKER -->|handoff context| API
~~~

Kiến trúc có hai mặt phẳng phối hợp:

1. **Application plane**: trình duyệt gọi FastAPI qua REST để xác thực, quản lý session, booking, quote, maps, handoff và lịch sử.
2. **Realtime voice plane**: trình duyệt tham gia LiveKit Room; LiveKit Agent Worker chạy một AgentSession cho cuộc hội thoại, xử lý audio và gọi cùng domain tools/guardrails.

Luồng text và luồng voice là hai transport khác nhau nhưng dùng chung quy tắc nghiệp vụ, state contract và các kiểm tra an toàn ở tầng backend/domain.

## 3. Thành phần và trách nhiệm

| Thành phần | Trách nhiệm chính | Không sở hữu |
|---|---|---|
| React/Vite | UI, transcript, booking progress, quote/confirmation modal, rating, text fallback, operator UI | Giá, booking truth, quyền xác nhận cuối |
| FastAPI routes | Auth, session, booking, quote, maps, trip, handoff, LiveKit token | Suy luận tự do hoặc xử lý audio realtime |
| Session Service | Nhận message/transcript, chạy vòng lặp agent-action-tool, cập nhật state và lịch sử | Kết nối trực tiếp tới microphone/LiveKit |
| Core Agent | Chuyển input thành typed action, hỏi lại khi thiếu dữ kiện, áp guardrails | HTTP, database session, TTS/STT, side effect trực tiếp |
| Domain tools/services | Place search, route/fare estimate, booking, cancel, status, FAQ, handoff | Quyết định ngoài contract hoặc tự phát ngôn |
| LiveKit Agent Worker | Join room, khởi tạo AgentSession, gắn STT/LLM/TTS, publish state, takeover | Quyền tự bypass confirmation hoặc ghi âm mặc định |
| DatabaseVoiceStateStore | Restore/persist voice state và optimistic revision | Raw audio và transcript thô |
| SQLAlchemy repositories | Durable user/session/booking/handoff/policy data | Logic hội thoại |
| Local catalogs | Gazetteer, pricing, vehicle options, FAQ/policy có version | Dữ liệu fleet/tài xế realtime |
| Operator console | Xem queue, nhận handoff, vào cùng room, resolve case | Tự ý thay đổi booking nếu không qua quyền nghiệp vụ |

## 4. Voice runtime

### 4.1 Khởi tạo cuộc hội thoại

1. Frontend lấy LiveKit token từ backend và tham gia room.
2. Worker nhận job từ LiveKit, join room sớm để không bỏ lỡ participant/audio event.
3. Worker đọc dispatch metadata, tạo trusted user/session context và restore state nếu có.
4. Worker tạo một AgentSession cho cuộc hội thoại đó.
5. AloSMAgent được khởi tạo với persona tiếng Việt, tool set và context của session.
6. Worker publish state để frontend cập nhật tiến trình booking và trạng thái voice.

### 4.2 Audio pipeline hiện tại

- **STT**: ElevenLabs Scribe Realtime, ngôn ngữ tiếng Việt.
- **Turn detection**: STT/server turn detection; dùng Silero VAD trong AgentSession để phát hiện giọng nói và barge-in.
- **LLM**: OpenAI qua LiveKit plugin; model runtime hiện tại là gpt-4.1-mini.
- **TTS**: Google Generative TTS với gemini-2.5-flash-tts, giọng Kore, vi-VN.
- **Fallback TTS**: Google Chirp 3 HD khi provider chính lỗi hoặc timeout.
- **Text transform**: lọc emoji/markdown và chuyển cách đọc tiền Việt trước khi phát âm.
- **Endpointing**: fixed endpointing có min/max delay để cân bằng phản hồi nhanh và tránh cắt câu.
- **Interruption**: VAD cho phép người dùng ngắt lời; câu trả lời đang phát có thể bị preempt.
- **Observability/privacy**: audio recording, raw transcript và trace recording tắt mặc định; debug logs/transcript chỉ bật khi cần.

Voice worker không tạo booking bằng cách tự gọi database. Nó gọi agent/domain contract; mọi side effect đặt xe vẫn đi qua confirmation, idempotency và repository/backend.

### 4.3 Text fallback

Khi microphone, LiveKit hoặc voice provider không khả dụng, người dùng vẫn có thể nhắn tin trong cùng session qua:

POST /api/v1/sessions/{session_id}/messages

Text path và voice path cùng dùng intent/action contract, nên đổi sang text không làm mất quy tắc xác nhận, quote hoặc handoff.

## 5. State và session

State hội thoại tối thiểu gồm:

- session/user identity;
- pickup, destination và candidate place IDs;
- vehicle type;
- quote ID, fare, distance, ETA, expiry;
- confirmation decision;
- booking ID/status;
- cancellation confirmation;
- handoff reason, priority và context snapshot;
- state revision để chống ghi đè khi có cập nhật cạnh tranh.

Frontend giữ UI state tạm thời; backend/domain là nguồn sự thật. Voice state được persist qua DatabaseVoiceStateStore khi cấu hình durable storage. Nếu restore thất bại, runtime có fallback an toàn về memory và tiếp tục hội thoại với trạng thái được phép; không tự bịa booking hoặc quote.

- Local dev/test: SQLite.
- Shared/deployed environment: PostgreSQL/Supabase theo cấu hình triển khai.
- State durable không bao gồm raw audio hoặc transcript thô theo mặc định.
- Session có thể create, resume, reset, end, xem history và gửi feedback.

## 6. Booking flow và bất biến nghiệp vụ

~~~text
User request
  -> search_place(pickup/destination)
  -> nếu nhiều candidate: hiển thị/hỏi user chọn
  -> chọn vehicle type
  -> estimate_fare
  -> hiển thị quote có quote_id, fare, distance, ETA, expiry
  -> explicit confirmation
  -> create_booking với idempotency key
  -> trả booking_id/status
~~~

Các quy tắc bắt buộc:

1. Không tạo booking nếu chưa có pickup, destination, vehicle và quote hợp lệ.
2. Không tạo booking nếu chưa nhận xác nhận rõ ràng của người dùng.
3. Place search có thể trả nhiều candidate; fuzzy/multiple match không được tự chọn im lặng.
4. Đổi pickup, destination hoặc vehicle sẽ invalidate quote và confirmation trước đó.
5. Quote hết hạn phải được estimate lại trước khi xác nhận.
6. create_booking dùng idempotency key dựa trên session và quote fingerprint để tránh đặt trùng khi retry.
7. get_booking_status chỉ trả dữ liệu authoritative từ backend; agent không tự đoán booking ID/trạng thái.
8. Hủy chuyến là hai bước: request confirmation trước, chỉ cập nhật thành CANCELLED sau khi người dùng xác nhận lần hai.
9. Pricing hiện tại là deterministic/local catalog cho demo; chưa phải giá realtime từ fleet.

Loại xe hiện hỗ trợ:

- MOTORBIKE — xe máy;
- CAR_4 — ô tô 4 chỗ;
- CAR_7 — ô tô 7 chỗ;
- LUXURY — xe cao cấp.

## 7. Agent tools hiện tại

LiveKit AloSMAgent dùng các tool chính:

- start_booking: bắt đầu booking flow;
- get_vehicle_options: lấy danh sách loại xe;
- search_knowledge: tìm FAQ/chính sách đã được phê duyệt, có nguồn và version;
- request_handoff: chuyển người dùng sang nhân viên;
- cancel_booking: yêu cầu/xác nhận hủy;
- get_booking_status: tra cứu chuyến authoritative.

Booking task/domain bổ sung các thao tác tìm/chọn địa điểm, chọn loại xe, estimate quote, confirm và create booking. Agent trả lời tiếng Việt ngắn, thường không quá hai câu ở voice mode, hỏi lại khi thiếu thông tin và không dùng FAQ để bịa giá/trạng thái.

## 8. FAQ, câu hỏi ngoài phạm vi và handoff

### FAQ và câu hỏi ngoài

Agent chỉ trả lời nội dung có trong knowledge catalog/policy được phê duyệt. Với câu hỏi ngoài phạm vi, agent nói rõ khả năng hiện tại hoặc đề xuất chuyển nhân viên; không tự trả lời như một chatbot mở miền.

Ví dụ thuộc phạm vi:

- cách đặt xe;
- loại xe;
- chính sách dịch vụ;
- cách xem/hủy chuyến;
- trạng thái booking.

Không thuộc MVP:

- thanh toán/hoàn tiền thật;
- điều phối tài xế hoặc vị trí xe realtime;
- khiếu nại CRM;
- cấp cứu 112;
- đa kênh/mobile app.

### Handoff

Handoff có thể xảy ra khi:

- người dùng yêu cầu gặp nhân viên;
- provider/tool lỗi;
- agent không đủ confidence;
- có tranh chấp thanh toán hoặc case nhạy cảm;
- active trip/no-show hoặc mức độ nghiêm trọng cao.

Backend tạo handoff record gồm lý do, priority/severity, pickup/destination/vehicle/quote, lỗi nếu có và context snapshot. Operator xem queue, accept case, lấy operator token và tham gia cùng LiveKit Room. Khi operator participant hợp lệ vào room:

1. backend đánh dấu handoff connected;
2. worker tắt AI audio input/output;
3. nhân viên tiếp tục với cùng người dùng và context;
4. worker shutdown session an toàn.

## 9. API surface chính

| Nhóm | Endpoint/khả năng |
|---|---|
| Auth | register, login, me, change password, TOTP setup/confirm/disable |
| Session | create, get, history, resume, messages, feedback, end, reset |
| Booking | create, list |
| Quote | create estimate |
| Maps | search, reverse, resolve, route |
| Trip | status |
| Handoff | create, list, get, accept, connect, resolve |
| LiveKit | customer/operator token |
| Policy | current policy/source |
| Runtime | status, health, live, ready |
| Settings | get/put user settings |

## 10. Security, reliability và vận hành

- Authenticated routes lấy user từ bearer token; booking/session/handoff phải gắn với user/session hợp lệ.
- Policy acceptance được lưu theo version; đăng ký không được bỏ qua điều kiện này.
- Agent tool có allow-list, schema typed và guardrails; không expose tùy ý database/provider.
- Booking mutation cần explicit confirmation và idempotency.
- Optimistic revision bảo vệ state khỏi cập nhật cũ ghi đè cập nhật mới.
- Timeout/retry của provider phải trả lỗi có kiểm soát và có thể kích hoạt handoff.
- Không log secret, token, raw audio hoặc transcript nhạy cảm ở chế độ mặc định.
- Health/readiness endpoint dùng để kiểm tra runtime trước khi demo/deploy.
- Cấu hình provider nằm trong environment; không commit credentials.

## 11. Trạng thái triển khai và giới hạn

Đã có trong MVP demo:

- web React/Vite;
- text chat fallback;
- LiveKit Room + native AgentServer/AgentSession;
- STT/LLM/TTS pipeline và fallback TTS;
- đặt xe demo có tìm/chọn địa điểm, quote, confirmation, idempotent create;
- đổi điểm/đổi loại xe làm quote cũ mất hiệu lực;
- tra cứu/hủy chuyến;
- FAQ grounded;
- handoff cùng LiveKit Room và operator console;
- session/history/state recovery contract.

Chưa phải production integration:

- fleet/driver matching và status realtime;
- payment gateway, refund và CRM;
- emergency dispatch/112;
- multi-channel/mobile;
- tải production, SLA và monitoring đầy đủ;
- bản đồ/giá realtime bắt buộc (hiện có local catalog và adapter tùy chọn).

## 12. Hướng hardening tiếp theo

1. Chuẩn hóa PostgreSQL/Supabase migration, backup, RLS và observability cho môi trường dùng chung.
2. Tích hợp maps/fleet/pricing provider thật với contract và retry/circuit breaker.
3. Bổ sung payment/refund/complaint workflow có audit trail.
4. Mở rộng operator permissions, transcript redaction và retention policy.
5. Đo latency STT-to-first-response, TTS fallback rate, booking completion, duplicate prevention và handoff resolution trước pilot.
