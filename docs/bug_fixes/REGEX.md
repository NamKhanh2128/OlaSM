# Regex và deterministic parsing trong voice booking

## Phạm vi

Tài liệu này ghi lại các lỗi parsing được sửa trong luồng đổi thông tin booking tại
`src/voice_agent/tasks/booking.py`. Mục tiêu là nhận đúng intent đổi điểm đón, điểm
đến hoặc loại xe mà không để transcript ASR dài hay malformed gây over-match,
backtracking hoặc làm sai booking slot.

## Pipeline hiện tại

```text
Final transcript (tối đa 1.000 ký tự)
        |
        v
Regex chỉ nhận cue + field
        |
        v
Chuẩn hóa field (NFC + casefold + whitespace)
        |
        v
Tách linker độc lập: là / thành / sang / qua
        |
        v
Token scanner một lượt lấy replacement entity
        |
        v
Giới hạn 200 ký tự / 24 token
        |
        v
Ground vào BookingDraft rồi mới search/update
```

Regex không còn chịu trách nhiệm capture toàn bộ entity. Nó chỉ phát hiện cấu trúc
đổi field; phần còn lại được xử lý bằng parser tuyến tính có giới hạn.

## Các lỗi và cách sửa

### 1. Field regex khớp nhưng dictionary lookup có thể lỗi

Trước đây `field` từ regex được dùng trực tiếp làm key. Chữ hoa, Unicode NFD hoặc
nhiều loại whitespace có thể khiến key khác `"điểm đón"` và gây `KeyError`.

Đã sửa bằng:

- chuẩn hóa transcript về Unicode NFC;
- `casefold()` và gom whitespace bằng `_normalize_change_field`;
- dùng `_CHANGE_FIELD_TARGETS.get(...)` và bỏ qua field không hợp lệ thay vì làm
  crash phiên thoại.

Các trường hợp được khóa bằng test: chữ hoa, tab/NBSP, Unicode NFD và mapping bị
thiếu key.

### 2. Capture `.+?`/`[^.!?;]+` lấy cả lời nói không thuộc địa chỉ

Một replacement kiểu `Đổi điểm đón thành VinUni và gọi cho tôi` từng có thể trở
thành `VinUni và gọi cho tôi`. Với ASR thiếu dấu câu, phần capture còn có thể kéo
dài đến hết transcript.

Đã sửa bằng cách:

- `_CHANGE_PATTERNS` chỉ kết thúc tại cue + field;
- entity được lấy từ `match.end()` bằng `_consume_change_link` và
  `_trim_trailing_non_entity_clause`;
- dừng ở ranh giới câu hoặc action clause đã biết;
- từ chối entity vượt 200 ký tự hoặc 24 token, không truncate rồi gửi chuỗi rác
  sang place search.

### 3. Regex route có nguy cơ backtracking trên ASR dài

Route `từ ... tới/đến ...` không còn dùng nhiều capture non-greedy và lookahead.
`extract_complete_route` giới hạn transcript ở 2.000 ký tự rồi tìm các marker cố
định bằng `_first_marker`:

- marker bắt đầu: `đi từ`, `từ`;
- marker điểm đến: `tới`, `đến`;
- marker kết thúc: loại xe hoặc dấu kết câu.

Số marker là hằng số nên thời gian xử lý tăng tuyến tính theo độ dài transcript,
không có nested backtracking.

### 4. Linker `sang`/`thay` gây false positive

Các câu bình thường như `Tôi muốn đi sang VinUni`, `Tôi thay anh Nam đi đến
VinUni` hoặc tên `thầy Sang` không được coi là thay đổi booking.

Biện pháp:

- change cue chỉ hợp lệ khi đi cùng một field rõ ràng như `điểm đón`, `điểm đến`,
  `loại xe`;
- `_consume_change_link` chỉ bỏ `là`, `thành`, `sang`, `qua` khi chúng là token
  độc lập ngay sau field/cue;
- regex dùng word/lookahead boundary, không tìm từ `sang` đứng riêng trong câu.

### 5. Cắt trailing clause làm hỏng tên địa chỉ hợp lệ

Không thể cắt tại mọi dấu phẩy hoặc mọi từ `và`, vì địa chỉ có thể là:

- `số 5, đường gọi là Hoa Sữa`;
- `Khu ăn uống và gọi là Phố Ẩm Thực`;
- `Viện Khoa học và Công nghệ Việt Nam`.

Parser hiện dùng một token scan:

- chỉ cắt connector khi phần sau khớp trọn một action prefix như `gọi cho tôi`,
  `nhắn biển số`, `đặt xe`, `ước tính giá`;
- không cắt cụm `gọi là`, vì đó có thể là một phần tên;
- loại các hậu tố lịch sự rõ ràng ở cuối như `nhé`, `ạ`, `giúp tôi`;
- chuẩn hóa và tokenize đúng một lần thay vì nhiều vòng `find/casefold` lồng nhau.

Độ phức tạp là `O(n * k)` với `k` là tập prefix cố định, nhỏ; về thực tế là tuyến
tính theo số token ASR.

### 6. Correction không nói tên field

Barge-in thực tế có thể là:

```text
À, nó không phải, không phải Hồ Gươm mà là Long Biên.
```

Câu này không chứa `đổi điểm đến`, nên explicit regex không đủ thông tin.
`extract_contextual_booking_change` xử lý bằng token markers `không phải OLD mà
là NEW`, không dùng capture tham lam. `OLD` chỉ được ánh xạ khi khớp duy nhất với
query hoặc giá trị hiện tại của một slot trong `BookingDraft`; parser không đoán
từ toàn bộ candidate list. `NEW` tiếp tục đi qua cùng entity boundary và place
search như explicit change.

## Invariants

- Không có regex nào capture phần còn lại của transcript bằng `.*`, `.+?` hoặc
  một character class không giới hạn.
- Input và entity đều có hard limit trước khi search.
- Một change intent phải có field rõ ràng, hoặc giá trị cũ phải ground duy nhất
  vào state hiện tại.
- Không tự suy ra candidate/place ID từ regex.
- Parser trả `None` khi không chắc chắn; agent tiếp tục luồng bình thường thay vì
  ghi sai booking slot.

## Regression tests

Các test chính nằm trong `tests/test_voice_agent/test_booking_task.py`:

- `test_complete_route_parser_stops_at_fixed_route_boundaries`;
- `test_complete_route_parser_bounds_long_malformed_asr`;
- `test_explicit_booking_change_parser_prioritizes_replacement_intent`;
- `test_explicit_booking_change_normalizes_unicode_case_and_whitespace`;
- `test_explicit_booking_change_consumes_only_standalone_linker`;
- `test_normal_route_or_proper_name_is_not_an_explicit_booking_change`;
- `test_explicit_booking_change_keeps_only_the_booking_entity_span`;
- `test_explicit_booking_change_rejects_oversized_unbounded_remark`;
- `test_contextual_correction_grounds_old_value_to_destination_slot`.

## Lịch sử thay đổi

| Commit | Nội dung chính |
| --- | --- |
| `275efa8` | Chuẩn hóa field và lookup an toàn |
| `c80f084` | Giới hạn entity và loại trailing clause |
| `e3c696b` | Tách entity extraction khỏi regex |
| `98efa2e` | Tách standalone linker, chặn false positive |
| `a96332c` | Thêm negative cases cho `sang`/`thay` |
| `0a9f68f` | Không cắt tên chứa `gọi là` hoặc dấu phẩy hợp lệ |
| `c900ced` | Thay nhiều vòng tìm chuỗi bằng token scanner |
| `7b1afe1` | Thêm contextual correction `không phải OLD mà là NEW` |

