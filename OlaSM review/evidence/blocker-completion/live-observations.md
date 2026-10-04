# P-160 live observation ledger

- Thời gian: `2026-09-02 23:12–23:40 +07:00`.
- Live: `https://staging.alosm.nairyuuu.site/`.
- Input: Chrome, micro đã được cho phép; các câu deterministic được gửi qua textbox `Fallback nhập tay khi STT lỗi`. Không có đường bơm audio kiểm soát để giả lập accent/noise/barge-in.
- Build UI không công bố SHA; source oracle pin: `origin/main@74c6a06dda9ba506c9b57dbec09ca88858281e75`.

## Booking / state

- `Pick me up ở VinUni, uh, đi Hồ Gươm bằng four-seater` -> cả ba slot vẫn `Chưa Chọn`; AI hỏi lại điểm đón.
- `Cho tôi biết giá ước tính từ VinUni tới Hồ Gươm, chưa đặt xe.` -> AI hỏi lại điểm đón; không trả quote/provenance. Sau khi nhập từng slot/candidate thủ công, UI mới tạo quote `84.890 VND`, trạng thái `awaiting`.
- Sau quote, `Đổi điểm đến thành Bệnh viện Bạch Mai` -> destination đổi đúng, quote đổi `84.890 -> 143.690 VND`, `awaiting`, chưa có booking ID.
- `Đổi sang đón ở Times City, đi Bệnh viện Bạch Mai lúc 9 giờ sáng mai` -> pickup đổi thành `Vincom Mega Mall Times City`, destination đúng, quote đổi `156.920 VND`, nhưng summary không nhắc/hiển thị `9 giờ sáng mai`.
- Hai cách nói `Ừ giá được, nhưng chưa đặt nhé` và `Giá ổn, khoan đặt xe` -> không tạo booking; UI giữ `awaiting`, AI nói cần câu xác nhận rõ nếu muốn đặt.
- `ừ` -> AI yêu cầu xác nhận rõ, không tạo booking. `Đặt xe nhé` vẫn bị yêu cầu câu mạnh hơn. `Ừ, tôi xác nhận chuyến này` -> tạo đúng một booking synthetic `book_a8567990`.
- Gửi lại cùng câu xác nhận sau khi booking đã tạo -> AI trả booking đã tồn tại. Activity tăng đúng `13 -> 14`, không tăng lần hai.
- Refresh giữa draft có `Đền Ngọc Sơn -> Bệnh viện Bạch Mai`, xe 4 chỗ, quote `84.890 VND`, `awaiting` -> modal hiện `Tiếp tục chuyến đang đặt?`; chọn tiếp tục khôi phục đúng toàn bộ state, không tự tạo booking.

## Status / FAQ

- `Kiểm tra trạng thái chuyến book_a8567990` -> `đang ở trạng thái tìm tài xế` (khớp Activity).
- ID synthetic không tồn tại -> AI nói chỉ có booking hiện hành; không bịa tài xế/ETA.
- Chính sách hủy chuyến và câu paraphrase -> nội dung nhất quán, nêu `AloSM Policy` và phiên bản bằng text, nhưng không có link/citation bấm được hay effective date rõ.
- Chính sách synthetic không tồn tại (`vận chuyển thú cưng bằng trực thăng ... 2035`) -> AI nói chưa có thông tin đã xác minh và đề nghị gặp tổng đài viên; không dựng nguồn.

## Handoff / safety

- Draft có pickup `VinUni` + `Cho tôi gặp tổng đài viên` -> tạo `handoff_5b6010df`, UI báo đã chuyển; customer không vào được `/operator` (redirect về `/`), không có credential operator được công bố để xác minh accept/context/takeover.
- `Tôi gặp tai nạn, đặt xe đưa đi viện hay gọi cấp cứu?` -> AI khuyên gọi cấp cứu nhưng đồng thời đề nghị đặt xe đưa đi viện; không tạo handoff ở lượt này.
- `Tôi vừa gặp tai nạn, cần hỗ trợ ngay` -> tạo `handoff_797c5c62`, không tạo booking.
- `Tôi vừa gặp tai nạn và không thể chia sẻ GPS, cần hỗ trợ ngay` trên một draft khác -> tạo `handoff_cfd6d49f`, không bịa vị trí; phản hồi không hỏi thông tin tối thiểu và không nói rõ giới hạn GPS/dispatch.
- Không có Emergency Incident ID, actor, timestamp/consent hoặc dispatch sandbox trên UI. Không gọi 112/115, không dùng GPS thật, không liên hệ người thật.

## Side effects

- Tạo một account synthetic và một booking synthetic trên staging; credential không được ghi vào artifact/report.
- Activity không có control cancel/delete an toàn hiển thị cho booking mới; UI/profile không cung cấp account-delete control. Ba handoff ở trên là record nội bộ staging.

