# Race-condition hardening trong voice agent

## Phạm vi

Tài liệu này mô tả các race condition đã được xử lý trong booking barge-in,
transcript rewrite, persistence và vòng đời LiveKit. Các invariant dưới đây là
contract cần giữ khi thay đổi `BookingTask` hoặc thêm provider I/O mới.

## 1. Booking barge-in transaction

### Lỗi gốc

Hai utterance có thể tới gần nhau trong khi request cũ đang:

- tìm địa điểm;
- tính lại báo giá;
- lưu state;
- publish state cho frontend;
- hoặc chuẩn bị phát TTS.

Nếu không có ordering, request cũ có thể hoàn thành sau request mới và ghi đè
`BookingDraft`, publish list cũ hoặc nói một câu trả lời đã stale. Hai thay đổi ở
hai field khác nhau cũng có thể cùng sửa shared `userdata` và gây lost update.

### Thiết kế hiện tại

```text
Final user turn
      |
      v
Parse field + replacement
      |
      v
Issue (field, generation) dưới generation lock
      |
      v
Force-interrupt speech cũ
      |
      v
Acquire booking-change transaction lock
      |
      +--> stale check
      +--> contextual old-value revalidation
      +--> awaited place lookup
      +--> stale check
      +--> mutate BookingDraft
      +--> quote (nếu đủ slot) + stale check
      +--> save + stale check
      +--> publish + stale check
      +--> say
      |
      v
Release lock
```

Hai cơ chế có vai trò khác nhau:

1. `_booking_change_generation_lock` cấp generation duy nhất theo từng field.
   Token được cấp trước transaction lock, vì vậy một request mới cùng field vẫn
   có thể đánh dấu request đang chờ I/O là stale.
2. `_booking_change_transaction_lock` tuần tự hóa toàn bộ lookup, mutation,
   persistence, publication và acknowledgement trên shared session state.

Lookup được giữ bên trong transaction lock một cách có chủ đích. Điều này làm các
booking change khác field chạy tuần tự, nhưng bảo đảm không có task nào thay đổi
`userdata.booking_draft` giữa lúc lookup và commit. Provider hiện tại là gazetteer
local; nếu chuyển sang map API mạng, implementation sau `search_async` phải là
native async và cần latency/timeout policy riêng, không được đổi lại thành lời gọi
sync chặn event loop.

### Latest-wins và stale side effects

`_raise_if_stale_booking_change` được gọi tại mọi ranh giới quan trọng. Request
cũ không được phép:

- set candidates hoặc vehicle type;
- set quote/confirmation;
- lưu state;
- publish state;
- phát acknowledgement.

`StopResponse` kết thúc request stale mà không để conversational LLM tiếp tục xử
lý lại cùng turn.

### Contextual correction

Với câu `không phải Hồ Gươm mà là Long Biên`, parser cần đọc booking state để suy
ra field. Nó đọc một deep snapshot, nhưng trước lookup vẫn xác minh lại dưới
transaction lock rằng `Hồ Gươm` còn thuộc đúng field đã suy ra. Nếu state đã đổi,
request bị dừng; không áp correction lên một draft mới hơn.

## 2. Transcript rewrite concurrency

Parent agent và booking task có thể cùng nhận một finalized LiveKit item. Nếu cả
hai tự gọi provider và sửa `new_message.content`, hệ thống có thể:

- gọi LLM rewrite hai lần;
- cho một listener đọc raw text trong khi listener khác đã sửa text;
- apply kết quả cũ lên một message đã được thay đổi;
- hoặc để cancellation của một hook hủy shared rewrite task.

`rewrite_livekit_user_turn` xử lý bằng:

- task registry theo `item_id` trong session data;
- `transcript_rewrite_lock` khi tạo/lấy task và khi apply kết quả;
- mọi hook cùng join một task bằng `asyncio.shield`;
- chỉ apply nếu text hiện tại vẫn là raw text hoặc normalized text tương ứng;
- giữ nguyên non-text content parts khi thay text;
- barrier tối đa 2 giây, timeout thì trả raw transcript thay vì treo turn.

Preemptive generation bị tắt trong cấu hình AgentSession, nên agent LLM không bắt
đầu trả lời trước khi rewrite barrier hoàn tất.

## 3. Persistence conflict

Transaction lock chỉ bảo vệ các coroutine trong một `BookingTask`; reconnect hoặc
worker khác vẫn có thể cùng lưu một session. `DatabaseVoiceStateStore` dùng
persistence revision/optimistic concurrency. Writer có revision cũ nhận
`VoiceStateConflictError` thay vì âm thầm ghi đè state mới.

Khi booking flow gặp conflict, hệ thống:

- ghi failure `STATE_CONFLICT`;
- không retry mutation mù;
- publish trạng thái an toàn nếu room còn hoạt động;
- dừng turn để tránh tạo booking hoặc TTS dựa trên state stale.

## 4. LiveKit lifecycle races

### Publish sau khi room đóng

Provider-failure callback có thể kết thúc sau lúc LiveKit đã tháo `RoomIO`.
`publish_booking_state` nhận diện riêng lỗi `AgentSession was not started with a
room`, log `skipped_closed_session` và kết thúc bình thường. Đây là cleanup race;
không có client nào còn trong room để nhận packet và không nên tạo unhandled task
exception.

Các exception publish khác vẫn được log là lỗi, nhưng không làm crash cuộc gọi khi
browser ngắt kết nối đúng lúc tool hoàn tất.

### Provider failure và operator takeover

`server.py` dùng lock riêng để:

- chỉ persist/publish một provider failure transition tại một thời điểm;
- chỉ khởi động một operator takeover dù nhiều participant event tới gần nhau;
- theo dõi và drain takeover tasks khi worker shutdown.

Các lock này không dùng chung với booking transaction để tránh coupling giữa
RTC lifecycle và business-state mutation.

## Lock ordering và nguyên tắc mở rộng

- Generation token được cấp trước khi acquire booking transaction lock.
- Không acquire generation lock từ code đang giữ transaction lock.
- Mọi booking state side effect của explicit/contextual change phải nằm trong
  transaction lock.
- Sau mỗi `await` có thể làm request trở nên stale, phải check generation trước
  side effect tiếp theo.
- Không giữ reference mutable từ một snapshot rồi dùng sau `await`; contextual
  parser dùng deep copy và revalidate state thật khi commit.
- Không thêm đường publish/say riêng bỏ qua `_respond_after_grounded_change`.
- Không xử lý `VoiceStateConflictError` bằng last-write-wins.

## Regression tests

Booking concurrency trong `tests/test_voice_agent/test_booking_task.py`:

- `test_newer_barge_in_wins_while_async_place_search_is_pending`;
- `test_same_field_generation_tokens_are_unique_under_concurrency`;
- `test_different_field_changes_serialize_lookup_and_commit`;
- `test_stale_vehicle_change_cannot_mutate_or_speak_after_newer_change`;
- `test_destination_barge_in_interrupts_pickup_prompt_and_focuses_new_list`;
- `test_contextual_destination_barge_in_replaces_only_destination`.

Rewrite concurrency trong `tests/test_voice_agent/test_transcript_rewrite.py`:

- `test_rewrite_barrier_is_capped_at_two_seconds`;
- `test_one_finalized_item_is_processed_once`;
- `test_concurrent_hooks_join_one_rewrite_before_mutating_messages`.

Persistence concurrency trong `tests/test_voice_agent/test_persistence.py`:

- `test_voice_state_rejects_stale_concurrent_writer`.

## Lịch sử thay đổi

| Commit | Nội dung chính |
| --- | --- |
| `98efa2e` | Async place-search boundary và generation guard |
| `a96332c` | Per-field generation, stale checks và commit serialization |
| `0a9f68f` | Generation issuance lock tách khỏi commit lock |
| `c900ced` | Cô lập lookup result và regression cho hai field đồng thời |
| `d88abbb` | Đưa lookup vào booking-change transaction lock |
| `456b57d` | Đồng bộ transcript-rewrite lock/barrier sau merge develop |
| `7b1afe1` | Revalidate contextual correction trong transaction |

