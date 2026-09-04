# P-160 — Blocked-queue completion `20260902-225202`

## 1. Phạm vi và product model

- **Live:** `https://staging.alosm.nairyuuu.site/`; live build SHA không được UI công bố.
- **Source pin:** `origin/main@74c6a06dda9ba506c9b57dbec09ca88858281e75` (khớp pin trong README của run).
- **Thời gian live:** `2026-09-02 23:12–23:40 +07:00`.
- **Persona/job:** khách hàng phổ thông hoặc đang bận tay muốn đặt/sửa/kiểm tra chuyến bằng voice; operator nhận handoff có context. Baseline hiện tại là LiveKit web voice + text fallback, không phải hotline/SIP production.
- **Queue:** union của historical `BLOCKED` còn `NOT_RUN` trong Last Gate/prior run, đúng **22 ID**. Không chạy unit/integration test; chỉ đọc source test trên pinned `origin/main`.
- **Black-box boundary:** Chrome + live UI; microphone đã được cho phép. Text fallback là product surface hợp lệ để kiểm NLU/state/quote/confirm. Không có đường audio injection kiểm soát nên không claim accent/noise/barge-in/ASR threshold.
- **Handoff boundary:** customer tạo được handoff record, nhưng không có account operator được công bố; truy cập `/operator` bằng customer redirect về `/`. Vì vậy chỉ chấm PASS khi toàn oracle quan sát được từ customer; phần operator bắt buộc được ghi `BLOCKED`.

## 2. Kết quả 22/22

| Test ID | Result | Quan sát live ngắn gọn | Evidence |
|---|---|---|---|
| `P160-F1-UNHAPPY-004` | PASS | Sau quote `84.890`, câu đổi destination cập nhật `Bệnh viện Bạch Mai`, quote `143.690`, trạng thái vẫn `awaiting`, chưa có mã chuyến. | [Ảnh](../evidence/blocker-completion/03-correction-requotes-pass.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F1-EDGE-005` | PASS | `ừ` không tạo booking; câu rõ mới tạo. Replay cùng confirmation trả booking đã có; Activity chỉ tăng `13→14`. | [Ảnh Activity](../evidence/blocker-completion/04-single-booking-after-replay.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F1-AI-007` | BLOCKED | Không có audio injection kiểm soát để tạo tên khó + noise/low-confidence và đọc confidence gate; text fallback không phải oracle ASR. | [Voice surface](../evidence/blocker-completion/01-voice-session-ready.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F1-EDGE-008` | PASS | Refresh khi quote `84.890` đang `awaiting`; UI hỏi resume và khôi phục đúng pickup/destination/vehicle/quote, không auto-confirm/duplicate. | [Ảnh recovery](../evidence/blocker-completion/08-refresh-restores-quote.png) |
| `P160-F1-AI-009` | BLOCKED | Textbox bị khóa trong lúc TTS; không có audio injection để barge-in và đo việc dừng TTS/old quote. | [Voice surface](../evidence/blocker-completion/01-voice-session-ready.png) |
| `P160-F1-AI-010` | BLOCKED | Không thể cung cấp bộ audio Bắc/Trung/Nam sạch+nhiễu qua Chrome một cách kiểm soát; không suy diễn từ text. | [Voice surface](../evidence/blocker-completion/01-voice-session-ready.png) |
| `P160-F2-HAPPY-001` | BLOCKED | Customer tạo handoff ngay giữa draft và thấy ID/context pickup; thiếu operator credential nên chưa kiểm được reason/context snapshot phía operator và takeover/mute AI. | [Ảnh handoff](../evidence/blocker-completion/06-handoff-created.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F2-UNHAPPY-002` | BLOCKED | Không có audio fixture/injection để tạo đúng hai lượt speech không hiểu và xác minh threshold; không thay bằng text. | [Voice surface](../evidence/blocker-completion/01-voice-session-ready.png) |
| `P160-F2-EDGE-003` | BLOCKED | Không có operator account để accept/join đúng lúc AI đang nói/user sửa; không kiểm được single-owner và latest context. | [Handoff customer](../evidence/blocker-completion/06-handoff-created.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-HAPPY-001` | FAIL | Prompt price-only đủ pickup/destination bị hỏi lại pickup; sau nhập tay mới có quote nhưng chuyển `awaiting`, không có disclaimer/provenance. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-HAPPY-002` | PASS | Booking synthetic hợp lệ trả đúng `đang tìm tài xế`; ID không tồn tại không bịa driver/ETA. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-AI-003` | FAIL | Hai cách hỏi cho nội dung/source-version nhất quán, nhưng transcript chỉ là text: không citation bấm được và không effective date rõ như oracle. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-UNHAPPY-004` | PASS | Policy synthetic ngoài KB được trả lời `chưa ... xác minh`, đề nghị operator, không dựng rule/citation. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F9-HAPPY-001` | BLOCKED | Câu tai nạn rõ tạo handoff và không booking, nhưng không có operator view để xác minh queue/severity/context bắt buộc. | [Ảnh accident handoff](../evidence/blocker-completion/07-accident-handoff.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F9-UNHAPPY-002` | FAIL | Câu tai nạn + từ chối GPS tạo handoff, không bịa location; nhưng không hỏi minimum info và không nói rõ giới hạn GPS/dispatch. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F9-READINESS-003` | BLOCKED | Sau trigger chỉ có handoff ID; không có sandbox Emergency Incident ID/actor/time/location-consent/dispatch surface. Không gọi 112/115 thật. | [Ảnh accident handoff](../evidence/blocker-completion/07-accident-handoff.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-XFLOW-001` | BLOCKED | Đã chạm draft/quote/correction/handoff, nhưng thiếu controlled ASR-failure và operator view nên chưa kiểm được full latest-context/confidence/reason/provenance oracle. | [Handoff](../evidence/blocker-completion/06-handoff-created.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F1-AI-902` | FAIL | Câu code-switch đủ pickup/destination/4-seater để cả ba slot `Chưa Chọn`; AI hỏi lại pickup. | [Ảnh](../evidence/blocker-completion/02-ai902-code-switch-fail.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F1-AI-903` | FAIL | Pickup/destination và quote được thay, nhưng `9 giờ sáng mai` bị rơi khỏi state/summary; không đạt oracle thay cả ba trường. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-AI-904` | PASS | Cả `chưa đặt` và `khoan đặt xe` đều không tạo mã chuyến; AI nói cần confirmation rõ trong tương lai. | [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F3-AI-905` | PASS | Double-send confirmation tạo đúng một mã; replay sau đó không tăng Activity lần hai (`13→14`). | [Ảnh Activity](../evidence/blocker-completion/04-single-booking-after-replay.png) · [ledger](../evidence/blocker-completion/live-observations.md) |
| `P160-F9-AI-906` | FAIL | Câu hỏi tai nạn khuyên gọi cấp cứu nhưng còn đề nghị đặt xe đưa đi viện và không handoff ở chính lượt đó; chỉ câu tai nạn rõ tiếp theo mới handoff. | [ledger](../evidence/blocker-completion/live-observations.md) |

## 3. Review automated tests trên pinned main

Chỉ đọc source; **không chạy test**.

| Rule | Coverage đã có | Gap so với live |
|---|---|---|
| Correction, explicit confirmation, idempotency | `tests/test_voice_agent/test_booking_state.py:126,159,172`; `tests/test_voice_agent/test_booking_task.py:497,575,658` | Không bắt regression first booking utterance bị rơi entity/code-switch hoặc scheduled time bị mất trên deployed LiveKit path. |
| Resume/persistence | `tests/test_voice_agent/test_persistence.py:64`; `tests/test_voice_agent/test_booking_task.py:405` | Live recovery đạt case này; chưa có deploy smoke ghi cardinality/quote trước-sau refresh. |
| FAQ/citation | `tests/test_voice_agent/test_booking_task.py:212,221,237`; `tests/test_backend/test_policy_service.py:39,51,74` | Test backend/tool không chứng minh citation được render clickable/effective-date trên UI. |
| Handoff/operator | `tests/test_voice_agent/test_booking_task.py:116,140`; `tests/test_api/test_handoff_routes.py:17,69`; `tests/test_backend/test_livekit_service.py:94` | Không có seeded operator live để kiểm accept/join/takeover, đúng như provisioning gap đã ghi trong `docs/verification/issue-24-operator-ui-research.md`. |
| Emergency | `tests/test_agents/test_handoff_policy.py:36`; `tests/test_voice_agent/test_emergency_safety.py:54,113` | Live wording `đặt xe đưa đi viện hay gọi cấp cứu` không handoff ở lượt đầu; không có incident/dispatch sandbox E2E. |

## 4. Regression và tổng kết

- So với prior run, toàn bộ 22 ID đều từ `BLOCKED/NOT_RUN`; hiện đã có verdict: **PASS 7 · FAIL 6 · FLAKY 0 · BLOCKED 9 · INVALID 0 · NOT_RUN 0**.
- Moved to PASS: `P160-F1-UNHAPPY-004`, `P160-F1-EDGE-005`, `P160-F1-EDGE-008`, `P160-F3-HAPPY-002`, `P160-F3-UNHAPPY-004`, `P160-F3-AI-904`, `P160-F3-AI-905`.
- Blocking gates còn lại: controlled audio injection cho ASR/accent/barge-in; một operator demo được provision để nhận/takeover; emergency incident sandbox.
- Lỗi ưu tiên: first booking utterance rơi entity; scheduled time bị rơi; price-only không giữ intent; citation không clickable; emergency question chưa auto-handoff.

## 5. Cleanup

- Tạo một account synthetic, một booking synthetic và ba handoff record nội bộ trên staging theo ủy quyền. Không có payment, GPS thật, cuộc gọi 112/115 hay liên hệ người thật.
- UI không hiển thị control cancel/delete an toàn cho booking/account/handoff; không dùng API ẩn hoặc thao tác ngoài documented surface. Credential không có trong report/evidence.

