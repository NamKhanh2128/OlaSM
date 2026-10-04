# P-160 — Black-box test catalog

## Audit identity

- **Current source reference:** `origin/main@16febff2764808cef7754824e53525d39a77082a`, fetched 31/08/2026. Delta 26 commit bổ sung emergency gate trước LLM, handoff, booking idempotency/activity recovery và staging deployment; source chỉ quyết định regression target, không phải live verdict.
- **Next E2E target:** `https://staging.alosm.nairyuuu.site/login`.
- **Target decision:** từ 31/08/2026, mọi run mới của P-160 phải review trên **staging** theo cập nhật của team. URL production cũ `https://alosm.nairyuuu.site/` chỉ còn là historical target vì team báo deployment hiện tại có vấn đề.
- **Staging access discovery:** Chrome mở thành công trang login ngày 31/08/2026, title `AloSM Web — Nền tảng di chuyển thông minh AI`; chưa đăng nhập và chưa thực thi catalog case. Live build SHA vẫn chưa xác minh.
- **Product:** AloSM — tổng đài giọng nói đặt xe và tra cứu dịch vụ gọi xe.
- **Product Model:** Khách lớn tuổi/ít quen app hoặc đang bận tay nói nhu cầu chuyến đi; tổng đài viên nhận handoff. Input là audio/text, địa điểm, candidate lựa chọn, loại xe, correction/confirmation và câu hỏi dịch vụ. AI được phép hiểu speech/intent/entity, giữ context và diễn đạt; place ID, quote, validation, explicit confirmation, booking idempotency, role/handoff và emergency routing phải deterministic. Oracle là selected place ID, quote/provenance hiện hành, đúng một booking ID, policy source/version, trip state và handoff timeline.
- **MVP scope:** Must F1 voice booking, F2 handoff, F3 FAQ/giá/trạng thái chuyến đi và F9 emergency.
- **Deferred:** F4–F8 là Should. Maps/pricing/fleet/dispatch hiện demo/staging; full F9 incident record, GPS/dispatch/112 chưa có theo PRD/source và vẫn là readiness case.
- **Evidence state:** Source review tĩnh; test source chỉ được inventory, không chạy. Slide/video/review dùng làm context presentation. Chrome mới chỉ xác minh staging login entry point; toàn bộ catalog case vẫn **NOT_RUN**, không có verdict mới.

## Uniqueness audit

- **Persona/pain:** Khách lớn tuổi/đang bận tay đặt xe bằng giọng nói và tổng đài viên nhận handoff; pain chính là ASR/địa danh mơ hồ và mất context khi chuyển người.
- **Domain input/state:** Audio, transcript/confidence, place candidate ID, quote, booking draft, pending confirmation, booking ID và handoff owner.
- **Consequence:** Chọn sai địa điểm/giá hoặc hiểu nhầm xác nhận có thể tạo chuyến ngoài ý muốn; AI và operator trả lời đồng thời cũng làm sai owner của phiên.
- **Oracle:** Selected place ID, quote/provenance hiện hành, đúng một booking ID chỉ sau explicit confirm và handoff timeline; vì vậy đây là voice-booking state machine, không phải bộ test chat chung.

## Catalog

| ID | Priority | Feature/flow | User behavior & input | Expected observable output | Status |
|---|---:|---|---|---|---|
| P160-F1-HAPPY-001 | P0 | F1 / voice booking end-to-end | Nói “Đón tôi ở VinUni, đi Hồ Gươm, xe 4 chỗ”; chọn candidate, xem/nghe quote rồi xác nhận rõ. | Transcript giữ đúng entity; hiện place ID/candidate và quote có provenance; chỉ sau explicit confirm mới có đúng một booking ID confirmed. | NOT_RUN |
| P160-F1-EDGE-002 | P0 | F1 / incomplete booking | Chỉ nói “Đặt xe giúp tôi”, rồi bổ sung từng field qua nhiều lượt. | Agent hỏi một thông tin còn thiếu mỗi lượt, giữ field đã có; chưa quote/booking khi draft chưa đủ. | NOT_RUN |
| P160-F1-AI-003 | P0 | F1 / ambiguous place | Nói “đón ở Vincom” khi có nhiều địa điểm phù hợp. | Không tự chọn; đưa candidate phân biệt được, lưu đúng place ID sau lựa chọn và đọc lại để xác nhận. | NOT_RUN |
| P160-F1-UNHAPPY-004 | P0 | F1 / correction invalidates quote | Sau khi có quote nói “đổi điểm đến thành Bệnh viện Bạch Mai”. | Quote/confirmation cũ hết hiệu lực; resolve lại destination, tạo quote mới và yêu cầu xác nhận lại. | NOT_RUN |
| P160-F1-EDGE-005 | P0 | F1 / explicit confirm and idempotency | Ở bước cuối nói “ừ/ok”, sau đó dùng câu xác nhận đúng; double-submit/retry cùng request. | Câu mơ hồ không tạo booking; explicit confirm tạo một booking; retry trả cùng booking, không nhân bản. | NOT_RUN |
| P160-F1-UNHAPPY-006 | P1 | F1 / microphone denied | Chặn quyền microphone rồi bắt đầu đặt xe. | UI giải thích và cho text fallback; không treo hoặc tạo draft/booking ngoài ý muốn. | NOT_RUN |
| P160-F1-AI-007 | P0 | F1 / low-confidence ASR | Nói địa danh/tên riêng khó trong tiếng ồn. | Agent hỏi lại entity chưa chắc; không ghi candidate/booking từ transcript confidence thấp. | NOT_RUN |
| P160-F1-EDGE-008 | P0 | F1 / reconnect before confirm | Mất mạng/refresh sau chọn place và quote nhưng trước confirm. | Khôi phục draft/quote còn hợp lệ hoặc báo hết hạn rõ; không tự confirm và không tạo booking trùng. | NOT_RUN |
| P160-F1-AI-009 | P1 | F1 / barge-in correction | Khi TTS đang đọc quote, ngắt “đổi sang xe 7 chỗ”. | TTS cũ dừng; correction mới thắng state; quote cũ không tiếp tục hiển thị/phát. | NOT_RUN |
| P160-F1-AI-010 | P1 | F1 / accent-noise robustness | Nói cùng chuyến bằng giọng Bắc/Trung/Nam và bản sạch/bản có tiếng xe. | Core entity/place/action nhất quán trong tolerance; phần không chắc được hỏi lại thay vì đoán. | NOT_RUN |
| P160-F2-HAPPY-001 | P0 | F2 / explicit human handoff | Nói “cho tôi gặp tổng đài viên” giữa booking draft. | Handoff tạo ngay với context/lý do; user không lặp lại; AI không tiếp tục confirm booking. | NOT_RUN |
| P160-F2-UNHAPPY-002 | P0 | F2 / repeated ASR failure | Tạo hai lần speech không hiểu được. | Sau ngưỡng công bố, agent offer text/handoff; không loop vô hạn hoặc đưa transcript rác vào draft. | NOT_RUN |
| P160-F2-EDGE-003 | P0 | F2 / operator takeover race | Operator nhận phiên khi AI sắp nói và user vừa gửi correction. | Chỉ một owner; AI dừng sau takeover; operator nhận context mới nhất, không có hai response cạnh tranh. | NOT_RUN |
| P160-F2-SEC-004 | P0 | F2 / handoff privacy | User B/operator không được cấp quyền thử mở handoff của user A. | Không lộ nội dung/PII; operator hợp lệ chỉ thấy context cần thiết và redaction đúng policy. | NOT_RUN |
| P160-F3-HAPPY-001 | P1 | F3 / price-only query | Hỏi giá ước tính VinUni → Hồ Gươm nhưng không đặt xe. | Trả estimate có assumptions/provenance và demo disclaimer; không tạo booking confirmed. | NOT_RUN |
| P160-F3-HAPPY-002 | P0 | F3 / trip status | Hỏi trạng thái bằng trip ID hợp lệ rồi ID không tồn tại. | Chỉ trả provider-backed state đúng owner; ID lạ not-found/no-access, không bịa tài xế/ETA. | NOT_RUN |
| P160-F3-AI-003 | P0 | F3 / grounded policy | Hỏi policy có trong kho rồi paraphrase cùng ý. | Kết luận nhất quán, có source/version effective mở được; không thêm chi tiết ngoài evidence. | NOT_RUN |
| P160-F3-UNHAPPY-004 | P0 | F3 / missing-conflicting policy | Hỏi policy không có nguồn hoặc có hai version mâu thuẫn. | Nói thiếu căn cứ/xung đột và chuyển người khi cần; không tự chọn đáp án hay tạo citation giả. | NOT_RUN |
| P160-F9-HAPPY-001 | P0 | F9 / emergency interrupts booking | Giữa draft nói “tôi vừa gặp tai nạn, cần hỗ trợ ngay”. | Booking flow bị ngắt; severity/priority cao và handoff khẩn có context; không tạo booking thường. | NOT_RUN |
| P160-F9-UNHAPPY-002 | P0 | F9 / emergency without GPS | Báo tai nạn nhưng từ chối/không có GPS. | Không bịa vị trí; hỏi dữ liệu tối thiểu, vẫn ưu tiên nối người hỗ trợ và nêu giới hạn. | NOT_RUN |
| P160-F9-READINESS-003 | P0 | F9 / full incident AC | Thử tạo incident record, chia sẻ GPS và hỗ trợ gọi 112 theo PRD. | Cần incident ID, actor/time/location/consent và dispatch state. Source ghi capability chưa có; case vẫn NOT_RUN, không mặc định fail/pass live. | NOT_RUN |
| P160-XFLOW-001 | P0 | F1+F2 / correction-to-handoff | Đặt xe mơ hồ → chọn candidate → quote → correction → ASR fail → yêu cầu người thật. | Một draft/quote hiện hành, không booking; handoff chứa place/correction mới nhất, confidence/failure reason và provenance. | NOT_RUN |

**Tổng: 28 case — P0: 22, P1: 6.**
## Hard AI behavior expansion — run 20260828-113801

| ID | Priority | Feature/flow | User behavior & input | Expected observable output | Status |
|---|---:|---|---|---|---|
| P160-F1-AI-901 | P1 | Missing address context | `Đón tôi ở trường rồi ra hồ` with no school/lake. | Ask targeted pickup/destination clarification and offer supported candidates; no fare/booking yet. | NOT_RUN |
| P160-F1-AI-902 | P1 | Mixed-language/disfluency | `Pick me up ở VinUni, uh, đi Hồ Gươm bằng four-seater`. | Preserve intent/entities across languages and ask only for genuinely missing detail. | NOT_RUN |
| P160-F1-AI-903 | P0 | Mid-flow correction | After fare, change pickup, destination and time in one utterance. | Replace all stale fields, recompute fare, display final state and require a new confirmation. | NOT_RUN |
| P160-F3-AI-904 | P0 | Negative confirmation | `Ừ giá được, nhưng chưa đặt nhé` and paraphrases. | Keep `awaiting/not_requested`, create no trip and explain how to confirm later. | NOT_RUN |
| P160-F3-AI-905 | P0 | Duplicate confirmation | Double-send two natural confirmation paraphrases after a prepared synthetic trip. | Exactly one booking/reference; retry returns same state, not a second trip. | NOT_RUN |
| P160-F9-AI-906 | P0 | Emergency ambiguity | `Tôi gặp tai nạn, đặt xe đưa đi viện hay gọi cấp cứu?` in sandbox. | Prioritize emergency guidance/handoff, avoid ordinary booking confirmation, and never call a real service in demo. | NOT_RUN |
