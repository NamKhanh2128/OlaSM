# P-160 — Hướng dẫn kiểm thử dễ hiểu cho team

> **Verdict live mới nhất:** xem [review.md](./review.md), batch 31/08/2026: **28/28 — 3 PASS, 3 FAIL, 22 BLOCKED, 0 case chưa chạy**. Các mục lịch sử bên dưới chỉ giúp tái hiện và không được dùng thay verdict mới.

## Product Model

AloSM phục vụ khách hàng lớn tuổi, người ít quen ứng dụng hoặc đang bận tay và muốn đặt xe bằng giọng nói. Hệ thống phải hiểu địa điểm, giữ đúng thông tin qua nhiều lượt, tính lại giá sau khi người dùng sửa, chỉ tạo đúng một chuyến sau xác nhận rõ ràng, chuyển đầy đủ ngữ cảnh cho tổng đài viên và ưu tiên an toàn khi có tình huống khẩn cấp. AI được dùng để hiểu lời nói và hội thoại; mã địa điểm, báo giá, quyền truy cập, xác nhận, tạo chuyến và chuyển người phải được kiểm soát bằng quy tắc xác định.

## Cách đọc trạng thái

- `PASS`: đã quan sát được toàn bộ behavior mong đợi.
- `FAIL`: đã tới được hành vi cần kiểm tra nhưng kết quả sai.
- `BLOCKED`: chưa thể tới hành vi vì thiếu tài khoản, quyền, dữ liệu hoặc dịch vụ phụ thuộc.
- `chưa chạy`: chưa thực hiện được case trong vòng đang báo cáo. Vòng 31/08 không còn case chưa chạy.
- Các ảnh ngày 28/08 là lịch sử trên production cũ; evidence và verdict staging ngày 31/08 nằm trong review.md.

## Tóm tắt

- Catalog hiện có **28 case**: 22 P0 và 6 P1.
- Target vòng mới: `https://staging.alosm.nairyuuu.site/login`.
- Source tham chiếu vòng mới: `origin/main@16febff2764808cef7754824e53525d39a77082a`.
- Trạng thái staging ngày 31/08: **3 PASS / 3 FAIL / 22 BLOCKED / 0 case chưa chạy**. Xem matrix và ảnh mới trong review.md.
- Live build SHA của staging chưa được xác minh.

## Tối đa 5 ưu tiên trước vòng review

1. Sửa tình trạng gửi text hoặc voice rồi treo; luôn có timeout, nút thử lại và giữ nguyên draft.
2. Giữ đúng state hội thoại khi sửa thông tin, xác nhận lặp hoặc kết nối lại; không hỏi lại từ đầu và không tạo chuyến trùng.
3. Không tự đoán địa điểm thiếu ngữ cảnh; phải hỏi lại và lưu đúng candidate/place ID.
4. Cấp tài khoản tổng đài viên staging hoạt động để kiểm tra takeover, privacy và hành trình chuyển người.
5. Hoàn thiện behavior khẩn cấp an toàn: hướng dẫn ngay, hỏi vị trí tối thiểu, ghi rõ giới hạn của demo và không gọi dịch vụ thật.

## Test cases

### P160-F1-HAPPY-001 — Đặt một chuyến hoàn chỉnh

- **Người dùng và mục tiêu:** Khách muốn đặt xe 4 chỗ từ VinUni tới Hồ Gươm bằng giọng nói.
- **Tiền điều kiện và dữ liệu:** Đăng nhập tài khoản khách trên staging; microphone hoạt động; dùng câu `Đón tôi ở VinUni, đi Hồ Gươm, xe 4 chỗ` và một câu xác nhận rõ như `Tôi xác nhận đặt chuyến này`.
- **Các bước:** 1. Bắt đầu phiên mới. 2. Nói câu đặt xe. 3. Chọn đúng candidate khi hệ thống hỏi. 4. Kiểm tra điểm đón, điểm đến, loại xe và báo giá. 5. Xác nhận rõ. 6. Mở lịch sử chuyến.
- **Behavior mong đợi:** Transcript đúng; candidate có place ID; giá có nguồn và nhãn demo/staging; trước xác nhận chưa có chuyến; sau xác nhận có đúng một booking ID ở trạng thái confirmed và lịch sử đọc lại được.
- **Cách chấm:** PASS khi toàn bộ state và đúng một booking được quan sát; FAIL nếu treo, sai entity, tạo sớm hoặc không tạo; BLOCKED nếu không đăng nhập, không dùng được voice hoặc dịch vụ tạo chuyến không sẵn sàng.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; hệ thống báo phản hồi chậm, các trường vẫn trống và không có chuyến mới. [Ảnh luồng lỗi](./P160-F1-HAPPY-001-booking-not-completed.png) · [Ảnh lịch sử](./P160-F1-HAPPY-001-no-new-activity.png)
- **Team cần làm gì:** Bảo đảm luồng speech/text đi tới state machine, hiển thị timeout có thể retry và thêm kiểm tra E2E xác nhận một lần rồi đọc lại booking.

### P160-F1-EDGE-002 — Người dùng chỉ nói “Đặt xe giúp tôi”

- **Người dùng và mục tiêu:** Khách chưa biết phải cung cấp gì và bổ sung từng thông tin qua nhiều lượt.
- **Tiền điều kiện và dữ liệu:** Phiên mới; lần lượt dùng `Đặt xe giúp tôi`, `Đón ở VinUni`, `Đi Hồ Gươm`, `Xe 4 chỗ`.
- **Các bước:** 1. Gửi câu đầu thiếu dữ liệu. 2. Trả lời từng câu hỏi của agent. 3. Sau mỗi lượt, xem draft và câu hỏi tiếp theo. 4. Dừng trước xác nhận.
- **Behavior mong đợi:** Mỗi lượt chỉ hỏi thông tin còn thiếu; dữ liệu đã nói được giữ nguyên; không báo giá khi chưa đủ trường và không tạo booking.
- **Cách chấm:** PASS khi agent thu thập đủ trường không hỏi lặp và chưa tạo chuyến; FAIL nếu đoán, quên dữ liệu hoặc tạo chuyến sớm; BLOCKED nếu phiên không nhận được message.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; hệ thống hỏi thêm điểm đón và chưa tạo chuyến. [Bằng chứng](./P160-F1-EDGE-002-incomplete-booking.png)
- **Team cần làm gì:** Giữ nguyên behavior đã đạt và chuẩn bị account/session staging để chạy lại từ trạng thái sạch.

### P160-F1-AI-003 — Làm rõ địa điểm “Vincom”

- **Người dùng và mục tiêu:** Khách nói tên địa điểm mơ hồ và cần chọn đúng chi nhánh.
- **Tiền điều kiện và dữ liệu:** Phiên mới; câu `Đón tôi ở Vincom` tại khu vực có nhiều candidate.
- **Các bước:** 1. Gửi câu mơ hồ. 2. Kiểm tra danh sách candidate. 3. Chọn một chi nhánh cụ thể. 4. Kiểm tra draft và phần đọc lại.
- **Behavior mong đợi:** Agent không tự chọn; candidate có thông tin phân biệt; sau lựa chọn lưu đúng place ID và đọc lại đúng địa điểm.
- **Cách chấm:** PASS khi có bước làm rõ và place ID đúng; FAIL nếu tự đoán hoặc lưu sai candidate; BLOCKED nếu dịch vụ địa điểm không trả dữ liệu.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; hệ thống đã đưa danh sách để người dùng chọn. [Bằng chứng](./P160-F1-AI-003-ambiguous-place.png)
- **Team cần làm gì:** Seed danh sách candidate ổn định trên staging và hiển thị place ID để đối chiếu.

### P160-F1-UNHAPPY-004 — Sửa điểm đến sau khi đã có giá

- **Người dùng và mục tiêu:** Khách đổi ý sau khi đã nhận báo giá.
- **Tiền điều kiện và dữ liệu:** Tạo draft VinUni → Hồ Gươm, xe 4 chỗ và lấy báo giá; sau đó nói `Không, đổi điểm đến thành Bệnh viện Bạch Mai`.
- **Các bước:** 1. Ghi lại quote ID/giá cũ. 2. Gửi câu sửa. 3. Chọn candidate mới nếu được hỏi. 4. So sánh draft và quote mới. 5. Thử xác nhận quote cũ.
- **Behavior mong đợi:** Destination mới thay thế destination cũ; quote và confirmation cũ hết hiệu lực; giá được tính lại; cần xác nhận lại; quote cũ không thể tạo chuyến.
- **Cách chấm:** PASS khi state mới thắng và quote cũ bị vô hiệu; FAIL nếu không phản hồi, giữ giá cũ hoặc tạo chuyến theo dữ liệu cũ; BLOCKED nếu không tạo được quote ban đầu.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; sau 12 giây không có phản hồi và không có quote mới. [Bằng chứng](./P160-F1-UNHAPPY-004-correction-no-response.png)
- **Team cần làm gì:** Xử lý correction như một transition bắt buộc invalidate quote; thêm timeout/retry và test state cũ không còn dùng được.

### P160-F1-EDGE-005 — Xác nhận rõ và chống tạo chuyến trùng

- **Người dùng và mục tiêu:** Khách nói một câu mơ hồ rồi xác nhận đúng; mạng có thể gửi lại cùng request.
- **Tiền điều kiện và dữ liệu:** Draft đủ và có quote; dùng `Ừ, được`, sau đó `Tôi xác nhận đặt chuyến`; gửi lại chính câu xác nhận hoặc double-click.
- **Các bước:** 1. Gửi câu mơ hồ. 2. Kiểm tra chưa có booking. 3. Gửi xác nhận rõ hai lần gần nhau. 4. Mở lịch sử và đối chiếu booking ID.
- **Behavior mong đợi:** Câu mơ hồ không tạo chuyến; xác nhận rõ tạo đúng một booking; request lặp trả cùng booking/state, không tạo bản sao.
- **Cách chấm:** PASS khi đúng một booking; FAIL nếu tạo từ câu mơ hồ, tạo trùng hoặc mất state; BLOCKED nếu không đạt được bước quote.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; lịch sử chỉ có một chuyến sau xác nhận lặp. [Bằng chứng](./P160-F1-EDGE-005-idempotency-history.png)
- **Team cần làm gì:** Giữ idempotency hiện có và expose booking/reference ID trên staging để chứng minh hai confirmation cùng trỏ một record.

### P160-F1-UNHAPPY-006 — Microphone bị từ chối và dùng text fallback

- **Người dùng và mục tiêu:** Khách không cấp quyền microphone nhưng vẫn muốn đặt xe bằng văn bản.
- **Tiền điều kiện và dữ liệu:** Chặn quyền microphone cho staging; dùng text `Đón tôi ở VinUni, đi Hồ Gươm, xe 4 chỗ`.
- **Các bước:** 1. Mở phiên và chọn dùng microphone. 2. Từ chối quyền. 3. Đọc hướng dẫn lỗi. 4. Chuyển sang nhập text. 5. Gửi yêu cầu và kiểm tra có thể tiếp tục.
- **Behavior mong đợi:** UI giải thích quyền bị thiếu, cung cấp text fallback; nút gửi không bị khóa vĩnh viễn; không tạo draft/booking ngoài ý muốn từ lần mic lỗi.
- **Cách chấm:** PASS khi text fallback tiếp tục được flow; FAIL nếu treo, khóa gửi hoặc tạo state rác; BLOCKED nếu trình duyệt không cho thiết lập quyền test.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P1`; gửi text xong nút bị khóa hơn 20 giây và không có phản hồi. [Bằng chứng](./P160-F1-UNHAPPY-006-text-fallback-stuck.png)
- **Team cần làm gì:** Tách lỗi microphone khỏi trạng thái gửi text, đặt timeout hữu hạn và luôn mở recovery action.

### P160-F1-AI-007 — Nhận dạng địa danh với độ tin cậy thấp

- **Người dùng và mục tiêu:** Khách nói tên riêng khó trong tiếng ồn và cần hệ thống hỏi lại thay vì đoán.
- **Tiền điều kiện và dữ liệu:** Audio tổng hợp có câu `Đón ở VinUni` với tiếng xe nền, kèm biến thể tự sửa giữa câu.
- **Các bước:** 1. Phát audio trong phiên mới. 2. Kiểm tra transcript/confidence hoặc tín hiệu không chắc chắn. 3. Trả lời câu hỏi làm rõ. 4. Kiểm tra candidate và draft.
- **Behavior mong đợi:** Entity confidence thấp được hỏi lại; không lưu candidate hoặc tạo booking từ transcript yếu; người dùng có cách nghe/đọc lại và sửa.
- **Cách chấm:** PASS khi hỏi đúng entity thiếu chắc chắn; FAIL nếu đoán hoặc chỉ báo lỗi chung không có recovery; BLOCKED nếu không thể phát audio fixture.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; không có replay/control làm rõ và chỉ hiện lỗi nhận dạng chung. [Bằng chứng](./P160-F1-AI-007-no-confidence-replay-control.png)
- **Team cần làm gì:** Expose trạng thái nhận dạng không chắc, hỏi lại đúng trường và không commit transcript yếu vào draft.

### P160-F1-EDGE-008 — Refresh hoặc mất mạng trước xác nhận

- **Người dùng và mục tiêu:** Khách quay lại phiên đang có quote nhưng chưa xác nhận.
- **Tiền điều kiện và dữ liệu:** Draft đầy đủ, có quote, chưa booking; ghi lại session/quote ID.
- **Các bước:** 1. Ngắt mạng hoặc refresh. 2. Khôi phục kết nối. 3. Mở lại phiên. 4. Kiểm tra draft/quote. 5. Xác nhận một lần và kiểm tra lịch sử.
- **Behavior mong đợi:** Khôi phục đúng draft/quote còn hạn hoặc báo hết hạn rõ; không tự confirm; retry không tạo booking trùng.
- **Cách chấm:** PASS khi state được khôi phục hoặc hết hạn có giải thích; FAIL nếu state trống không thông báo, treo hoặc tạo chuyến; BLOCKED nếu không tạo được quote trước đó.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; phiên trở về trống và tin nhắn tiếp theo bị treo. [Bằng chứng](./P160-F1-EDGE-008-pending-not-restored.png)
- **Team cần làm gì:** Persist session/draft theo ID, kiểm tra quote expiry và phục hồi nút tương tác sau reconnect.

### P160-F1-AI-009 — Ngắt TTS để đổi loại xe

- **Người dùng và mục tiêu:** Khách ngắt lời lúc hệ thống đang đọc giá để đổi từ 4 chỗ sang 7 chỗ.
- **Tiền điều kiện và dữ liệu:** Phiên đang phát TTS quote xe 4 chỗ; câu ngắt `Dừng lại, đổi sang xe 7 chỗ`.
- **Các bước:** 1. Chờ TTS bắt đầu. 2. Nói câu ngắt. 3. Quan sát TTS dừng. 4. Kiểm tra draft và quote mới. 5. Xác nhận state cuối.
- **Behavior mong đợi:** Audio cũ dừng; correction mới thắng; loại xe và giá được cập nhật; không còn phát hoặc hiển thị quote cũ.
- **Cách chấm:** PASS khi chỉ một response chain và state mới thắng; FAIL nếu không phản hồi hoặc quote cũ tiếp tục; BLOCKED nếu staging không có voice/TTS.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P1`; sau 12 giây không có phản hồi hoặc trạng thái đã nghe. [Bằng chứng](./P160-F1-AI-009-no-bargein-replay-control.png)
- **Team cần làm gì:** Thêm cancellation cho TTS/agent turn và cơ chế latest-correction-wins.

### P160-F1-AI-010 — Giọng vùng miền và tiếng ồn

- **Người dùng và mục tiêu:** Khách nói cùng một chuyến bằng cách phát âm khác nhau hoặc có tiếng xe nền.
- **Tiền điều kiện và dữ liệu:** Bộ audio tổng hợp cùng nội dung VinUni → Hồ Gươm, xe 4 chỗ ở giọng Bắc/Trung/Nam, bản sạch và bản có noise.
- **Các bước:** 1. Mỗi audio dùng một phiên sạch. 2. Ghi transcript, entity, candidate và action. 3. So sánh kết quả. 4. Kiểm tra câu hỏi lại ở phần không chắc.
- **Behavior mong đợi:** Intent/entity cốt lõi nhất quán trong tolerance được team công bố; điểm không chắc phải được hỏi lại, không đoán.
- **Cách chấm:** PASS khi các biến thể giữ cùng nghĩa hoặc hỏi lại an toàn; FAIL nếu silent, đổi sai địa điểm/loại xe hoặc tự đoán; BLOCKED nếu không có bề mặt voice.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P1`; nội dung hiện lên nhưng không có phản hồi hoặc cách sửa. [Bằng chứng](./P160-F1-AI-010-no-accent-noise-replay-control.png)
- **Team cần làm gì:** Chuẩn bị golden audio set và hiển thị recovery khi ASR/agent quá thời gian.

### P160-F2-HAPPY-001 — Yêu cầu gặp tổng đài viên

- **Người dùng và mục tiêu:** Khách muốn chuyển người thật ngay giữa một draft.
- **Tiền điều kiện và dữ liệu:** Draft đã có điểm đón VinUni; câu `Cho tôi gặp tổng đài viên`.
- **Các bước:** 1. Tạo draft một phần. 2. Gửi yêu cầu chuyển người. 3. Kiểm tra state handoff. 4. Đăng nhập operator và mở yêu cầu.
- **Behavior mong đợi:** Handoff tạo ngay với lý do và context đã biết; khách không cần lặp lại; AI dừng hỏi/xác nhận booking.
- **Cách chấm:** PASS khi operator thấy đúng context và AI dừng; FAIL nếu không tạo, mất context hoặc AI tiếp tục; BLOCKED nếu thiếu tài khoản operator.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS` ở phía khách; yêu cầu hỗ trợ được tạo và flow booking dừng. [Bằng chứng](./P160-F2-HAPPY-001-explicit-handoff.png)
- **Team cần làm gì:** Cấp operator staging để xác minh nửa sau của flow: nhận queue, đọc context và takeover.

### P160-F2-UNHAPPY-002 — Hai lần ASR không hiểu

- **Người dùng và mục tiêu:** Khách nói không rõ nhiều lần và cần được chuyển sang cách hỗ trợ khác.
- **Tiền điều kiện và dữ liệu:** Hai audio tổng hợp không thể hiểu nhưng không chứa dữ liệu nhạy cảm.
- **Các bước:** 1. Gửi audio lỗi lần một. 2. Quan sát recovery. 3. Gửi audio lỗi lần hai. 4. Kiểm tra đề nghị text/handoff và draft.
- **Behavior mong đợi:** Sau ngưỡng công bố, agent đề nghị text hoặc người thật; không loop vô hạn; transcript rác không đi vào draft.
- **Cách chấm:** PASS khi có counter/threshold và recovery; FAIL nếu không phản hồi, loop hoặc lưu rác; BLOCKED nếu không phát được audio.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; không thấy counter/ngưỡng và chỉ còn request cũ. [Bằng chứng](./P160-F2-UNHAPPY-002-no-asr-failure-counter.png)
- **Team cần làm gì:** Theo dõi failure count theo session và kích hoạt fallback/handoff deterministic sau ngưỡng.

### P160-F2-EDGE-003 — Operator takeover đúng lúc có correction

- **Người dùng và mục tiêu:** Operator nhận phiên khi AI đang trả lời và khách vừa sửa thông tin.
- **Tiền điều kiện và dữ liệu:** Tài khoản khách và operator staging; draft có quote; câu sửa `Đổi điểm đến sang Bệnh viện Bạch Mai`.
- **Các bước:** 1. Khách gửi correction. 2. Gần đồng thời operator nhận phiên. 3. Quan sát cả hai màn hình. 4. Operator gửi một phản hồi. 5. Kiểm tra timeline/owner.
- **Behavior mong đợi:** Chỉ một owner; AI dừng sau takeover; operator thấy correction mới nhất; không có hai câu trả lời cạnh tranh.
- **Cách chấm:** PASS khi owner/timeline duy nhất và context mới nhất; FAIL nếu AI vẫn trả lời hoặc operator thấy state cũ; BLOCKED nếu operator không đăng nhập/không có queue.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0` vì tài khoản operator công bố không đăng nhập được. [Bằng chứng](./P160-F2-EDGE-003-operator-demo-invalid.png)
- **Team cần làm gì:** Cấp operator staging hợp lệ và thêm atomic ownership transition/cancellation cho AI turn.

### P160-F2-SEC-004 — Quyền và riêng tư của handoff

- **Người dùng và mục tiêu:** Operator hợp lệ chỉ xem dữ liệu cần thiết; user/operator khác không mở được phiên của khách A.
- **Tiền điều kiện và dữ liệu:** Hai khách A/B, một operator được quyền và một actor không được quyền; handoff A chứa email/địa chỉ sentinel giả.
- **Các bước:** 1. Tạo handoff A. 2. Operator hợp lệ mở từ queue. 3. User B/actor sai quyền thử mở cùng ID qua điều hướng bình thường. 4. Kiểm tra nội dung/redaction.
- **Behavior mong đợi:** Actor sai quyền bị từ chối không lộ metadata/PII; operator hợp lệ chỉ thấy field cần thiết và dữ liệu nhạy cảm được che theo policy.
- **Cách chấm:** PASS khi ownership và redaction đúng; FAIL nếu lộ dữ liệu hoặc actor sai quyền mở được; BLOCKED nếu thiếu nhiều tài khoản/queue.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0` do operator không đăng nhập nên chưa bắt đầu được luồng. [Bằng chứng](./P160-F2-SEC-004-operator-demo-invalid.png)
- **Team cần làm gì:** Chuẩn bị tài khoản/fixture hai user, enforce quyền server-side và hiển thị dữ liệu tối thiểu cho operator.

### P160-F3-HAPPY-001 — Hỏi giá nhưng không đặt xe

- **Người dùng và mục tiêu:** Khách chỉ muốn tham khảo giá VinUni → Hồ Gươm.
- **Tiền điều kiện và dữ liệu:** Phiên mới; câu `Từ VinUni đến Hồ Gươm khoảng bao nhiêu tiền? Tôi chưa muốn đặt xe`.
- **Các bước:** 1. Gửi câu hỏi. 2. Kiểm tra assumptions, nguồn và nhãn demo. 3. Mở lịch sử chuyến.
- **Behavior mong đợi:** Trả estimate có giả định/provenance và disclaimer staging; không tạo booking confirmed.
- **Cách chấm:** PASS khi có câu trả lời có nguồn và không side effect; FAIL nếu im lặng, bịa giá production hoặc tạo chuyến; BLOCKED nếu pricing service không sẵn sàng.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P1`; câu hỏi được ghi nhận nhưng không có trả lời. [Bằng chứng](./P160-F3-HAPPY-001-price-only.png)
- **Team cần làm gì:** Bảo đảm query-only không đi vào booking action và luôn gắn nguồn/nhãn demo cho giá.

### P160-F3-HAPPY-002 — Tra trạng thái bằng trip ID

- **Người dùng và mục tiêu:** Khách tra chuyến của mình và thử một mã không tồn tại.
- **Tiền điều kiện và dữ liệu:** Một trip ID synthetic thuộc user A, một ID không tồn tại, và nếu có thể một ID thuộc user B.
- **Các bước:** 1. User A hỏi ID hợp lệ. 2. So trạng thái với lịch sử/provider. 3. Hỏi ID lạ. 4. Thử ID user B qua UI bình thường.
- **Behavior mong đợi:** Chỉ trả provider-backed state đúng owner; ID lạ hoặc sai owner trả not-found/no-access; không bịa tài xế, ETA hoặc trạng thái.
- **Cách chấm:** PASS khi state và ownership đúng; FAIL nếu không trả lời, bịa hoặc lộ chuyến khác; BLOCKED nếu không có trip fixture hợp lệ.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; lịch sử không có trip ID và câu hỏi ID giả không được trả lời. [Ảnh lịch sử](./P160-F3-HAPPY-002-history-no-trip-id.png) · [Ảnh ID lạ](./P160-F3-HAPPY-002-invalid-trip-no-response.png)
- **Team cần làm gì:** Hiển thị trip ID, chuẩn bị fixture sở hữu rõ và trả trạng thái/error có thể hiểu được.

### P160-F3-AI-003 — Trả lời chính sách có nguồn

- **Người dùng và mục tiêu:** Khách hỏi phí hủy rồi hỏi lại cùng ý bằng cách diễn đạt khác.
- **Tiền điều kiện và dữ liệu:** Policy synthetic đang hiệu lực có version/source; hai câu `Phí hủy chuyến là bao nhiêu?` và một paraphrase tương đương.
- **Các bước:** 1. Gửi câu thứ nhất. 2. Mở nguồn/version. 3. Gửi paraphrase. 4. So hai kết luận với policy.
- **Behavior mong đợi:** Kết luận nhất quán; có citation/source/version effective mở được; không thêm chi tiết ngoài evidence.
- **Cách chấm:** PASS khi grounded và nhất quán; FAIL nếu im lặng, mâu thuẫn hoặc bịa; BLOCKED nếu knowledge source không có fixture.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; UI có policy source nhưng agent không trả lời. [Ảnh agent](./P160-F3-AI-003-policy-agent-no-response.png) · [Ảnh nguồn](./P160-F3-AI-003-policy-source.png)
- **Team cần làm gì:** Nối agent với knowledge source đang hiển thị và giữ citation/version trong response.

### P160-F3-UNHAPPY-004 — Chính sách thiếu hoặc có hai phiên bản xung đột

- **Người dùng và mục tiêu:** Khách hỏi điều chưa có căn cứ và cần câu trả lời trung thực.
- **Tiền điều kiện và dữ liệu:** Một câu hỏi policy không có trong kho; một fixture hai version mâu thuẫn nếu hệ thống hỗ trợ.
- **Các bước:** 1. Hỏi policy không tồn tại. 2. Kiểm tra response/citation. 3. Hỏi policy có version xung đột. 4. Kiểm tra đề nghị chuyển người.
- **Behavior mong đợi:** Nói thiếu dữ liệu hoặc xung đột; không tự chọn version, không tạo citation giả; chuyển người khi cần.
- **Cách chấm:** PASS khi thể hiện uncertainty đúng; FAIL nếu im lặng hoặc bịa; BLOCKED nếu không tạo được fixture version xung đột.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; câu hỏi policy giả không có phản hồi. [Bằng chứng](./P160-F3-UNHAPPY-004-missing-policy-no-response.png)
- **Team cần làm gì:** Có fallback grounded cho no-answer/conflict và hành động handoff rõ ràng.

### P160-F9-HAPPY-001 — Tình huống khẩn cấp ngắt booking

- **Người dùng và mục tiêu:** Khách đang đặt xe nhưng báo tai nạn cần hỗ trợ ngay.
- **Tiền điều kiện và dữ liệu:** Draft chưa xác nhận; câu `Tôi vừa gặp tai nạn, xe bốc khói và có người bị thương` trong môi trường demo.
- **Các bước:** 1. Tạo draft. 2. Gửi câu khẩn cấp. 3. Kiểm tra booking state. 4. Kiểm tra severity/priority và handoff. 5. Xác nhận không có cuộc gọi thật.
- **Behavior mong đợi:** Booking thường bị ngắt; tạo ưu tiên cao/handoff có context; đưa hướng dẫn an toàn trong phạm vi; không tạo booking thường hay gọi dịch vụ thật.
- **Cách chấm:** PASS khi emergency thắng flow và không side effect thật; FAIL nếu tiếp tục booking hoặc bỏ qua; BLOCKED nếu môi trường không có sandbox emergency.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; hệ thống chuyển hỗ trợ khẩn và không tạo chuyến thường. [Bằng chứng](./P160-F9-HAPPY-001-emergency-interrupt.png)
- **Team cần làm gì:** Giữ gate emergency đã đạt và chuẩn bị sandbox rõ để retest không tạo hành động thật.

### P160-F9-UNHAPPY-002 — Khẩn cấp nhưng không có GPS

- **Người dùng và mục tiêu:** Khách báo tai nạn nhưng tắt hoặc từ chối GPS.
- **Tiền điều kiện và dữ liệu:** GPS bị từ chối; câu `Tôi gặp tai nạn nhưng không chia sẻ được vị trí`.
- **Các bước:** 1. Gửi tình huống. 2. Từ chối GPS. 3. Kiểm tra câu hỏi về mốc/địa chỉ tối thiểu. 4. Kiểm tra handoff và giới hạn được giải thích.
- **Behavior mong đợi:** Không bịa vị trí; hỏi dữ liệu tối thiểu; vẫn ưu tiên nối người hỗ trợ và nói rõ giới hạn; không gọi thật trong demo.
- **Cách chấm:** PASS khi recovery an toàn không cần GPS; FAIL nếu im lặng, bịa vị trí hoặc quay lại booking; BLOCKED nếu không mô phỏng được GPS denied.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; hơn 20 giây không có câu hỏi/hướng dẫn. [Bằng chứng](./P160-F9-UNHAPPY-002-emergency-no-gps.png)
- **Team cần làm gì:** Thiết kế nhánh no-GPS deterministic với câu hỏi mốc vị trí và handoff tức thời.

### P160-F9-READINESS-003 — Hồ sơ sự cố, consent và dispatch trong demo

- **Người dùng và mục tiêu:** Mentor xác minh mức hoàn thiện của full F9 mà không tạo hành động cứu hộ thật.
- **Tiền điều kiện và dữ liệu:** Chế độ sandbox; location synthetic; không kết nối 112 thật.
- **Các bước:** 1. Báo sự cố. 2. Đồng ý rồi từ chối chia sẻ location ở hai run riêng. 3. Mở record/timeline. 4. Kiểm tra incident ID, actor, time, consent, location và dispatch state.
- **Behavior mong đợi:** Nếu feature được công bố complete, mọi field/state phải quan sát được và nhãn simulation rõ. Nếu source vẫn deferred, UI phải nói chưa hỗ trợ thay vì giả thành công.
- **Cách chấm:** PASS chỉ khi contract full F9 hiện hữu; FAIL nếu tuyên bố đã xử lý nhưng không có record/state; BLOCKED nếu feature được công bố là chưa triển khai và không có bề mặt chạy.
- **Lịch sử 28/08 (không phải verdict 31/08):** Source cũ ghi capability đầy đủ chưa có; lịch sử production ghi `FAIL P0` vì không tạo thông tin sau hơn 20 giây. [Bằng chứng](./P160-F9-READINESS-003-no-incident-gps-dispatch.png)
- **Team cần làm gì:** Hoặc triển khai record/consent/dispatch sandbox đúng AC, hoặc thu hẹp claim Demo Day và ghi rõ mới chỉ có nhận diện + handoff.

### P160-XFLOW-001 — Sửa thông tin, ASR lỗi rồi chuyển người

- **Người dùng và mục tiêu:** Khách đi qua hành trình khó nhưng thực tế và operator phải nhận đúng context cuối.
- **Tiền điều kiện và dữ liệu:** Khách + operator staging; câu mơ hồ, candidate, quote, correction, một audio lỗi rồi yêu cầu người thật.
- **Các bước:** 1. Nói địa điểm mơ hồ. 2. Chọn candidate. 3. Nhận quote. 4. Sửa destination. 5. Gây một ASR failure. 6. Yêu cầu operator. 7. Operator mở handoff.
- **Behavior mong đợi:** Chỉ một draft và quote hiện hành; không booking; handoff chứa candidate/correction mới nhất, confidence, failure reason và provenance; AI dừng sau takeover.
- **Cách chấm:** PASS khi toàn bộ state xuyên feature nhất quán; FAIL nếu mất correction, tạo booking hoặc hai owner; BLOCKED nếu thiếu operator/fixture.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; correction bị dừng và operator không đăng nhập được. [Bằng chứng](./P160-XFLOW-001-no-operator-takeover.png)
- **Team cần làm gì:** Sửa từng transition F1→F2, giữ event timeline chung và cấp operator staging hợp lệ.

### P160-F1-AI-901 — “Đón ở trường rồi ra hồ” thiếu ngữ cảnh

- **Người dùng và mục tiêu:** Khách nói tự nhiên nhưng không nêu trường và hồ cụ thể.
- **Tiền điều kiện và dữ liệu:** Phiên sạch; câu `Đón tôi ở trường rồi ra hồ`.
- **Các bước:** 1. Gửi câu. 2. Kiểm tra agent hỏi pickup/destination. 3. Chọn candidate sau khi được hỏi. 4. Kiểm tra chưa có fare trước khi làm rõ.
- **Behavior mong đợi:** Hỏi rõ cả trường và hồ, đưa candidate được hỗ trợ; không tự chọn địa điểm, không báo giá hoặc booking sớm.
- **Cách chấm:** PASS khi hỏi đúng context thiếu; FAIL nếu tự suy ra địa điểm; BLOCKED nếu message không được xử lý.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P1`; hệ thống tự đổi điểm đón thành Quảng trường Ba Đình. [Bằng chứng](./P160-F1-AI-901-missing-address-context.png)
- **Team cần làm gì:** Đặt confidence/ambiguity gate trước geocoding và không dùng default place khi user chưa chọn.

### P160-F1-AI-902 — Câu nói trộn Việt–Anh và ngập ngừng

- **Người dùng và mục tiêu:** Khách dùng câu hỗn hợp ngôn ngữ nhưng ý định vẫn rõ.
- **Tiền điều kiện và dữ liệu:** Câu `Pick me up ở VinUni, uh, đi Hồ Gươm bằng four-seater`.
- **Các bước:** 1. Nói hoặc gửi câu. 2. Kiểm tra transcript/entity. 3. Chọn candidate. 4. Kiểm tra loại xe và quote.
- **Behavior mong đợi:** Giữ đúng pickup, destination và xe 4 chỗ; chỉ hỏi phần thực sự thiếu, không bắt người dùng nói lại toàn bộ.
- **Cách chấm:** PASS khi intent/entity đúng; FAIL nếu mất entity hoặc không phản hồi; BLOCKED nếu voice không sẵn sàng.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; `four-seater` được hiểu đúng và tính được giá. [Bằng chứng](./P160-F1-AI-902-mixed-language.png)
- **Team cần làm gì:** Giữ behavior đa ngôn ngữ và lưu transcript/entity staging làm evidence mới.

### P160-F1-AI-903 — Sửa nhiều trường trong một câu

- **Người dùng và mục tiêu:** Khách đổi pickup, destination và loại xe sau khi đã có fare.
- **Tiền điều kiện và dữ liệu:** Draft có quote; câu `Đổi điểm đón sang VinUni, điểm đến sang Bệnh viện Bạch Mai và dùng xe 4 chỗ thay vì 7 chỗ`.
- **Các bước:** 1. Ghi state/quote cũ. 2. Gửi câu sửa. 3. Làm rõ candidate nếu cần. 4. Đối chiếu cả ba field. 5. Kiểm tra quote mới và xác nhận lại.
- **Behavior mong đợi:** Tất cả field mới thay thế field cũ; fare được tính lại; UI đọc lại final state; confirmation cũ hết hiệu lực.
- **Cách chấm:** PASS khi ba field và quote đều đúng; FAIL nếu silent hoặc chỉ cập nhật một phần; BLOCKED nếu không có quote ban đầu.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; sau 12 giây không phản hồi và field vẫn trống. [Bằng chứng](./P160-F1-AI-903-correction-no-response.png)
- **Team cần làm gì:** Parse multi-slot correction thành một atomic state update rồi invalidate/recompute quote.

### P160-F3-AI-904 — Câu đồng ý giá nhưng phủ định đặt xe

- **Người dùng và mục tiêu:** Khách thấy giá ổn nhưng chưa muốn đặt.
- **Tiền điều kiện và dữ liệu:** Draft có quote; dùng `Ừ giá được, nhưng chưa đặt nhé` và hai paraphrase tương đương.
- **Các bước:** 1. Gửi từng câu ở phiên sạch hoặc reset draft. 2. Kiểm tra confirmation state. 3. Mở lịch sử. 4. Hỏi cách xác nhận sau.
- **Behavior mong đợi:** State vẫn awaiting/not_requested; không booking; agent giải thích câu xác nhận rõ cần dùng sau này.
- **Cách chấm:** PASS khi không có side effect ở mọi paraphrase; FAIL nếu tạo chuyến hoặc đánh dấu confirmed; BLOCKED nếu không tạo được quote.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `PASS`; hệ thống giữ trạng thái chờ và không tạo chuyến. [Bằng chứng](./P160-F3-AI-904-negative-confirmation.png)
- **Team cần làm gì:** Giữ negative-confirmation gate và chạy lại đủ ba paraphrase trên staging.

### P160-F3-AI-905 — Hai cách xác nhận liên tiếp

- **Người dùng và mục tiêu:** Khách gửi hai câu xác nhận tự nhiên cho cùng một quote do không chắc câu đầu đã tới.
- **Tiền điều kiện và dữ liệu:** Một synthetic trip đã prepared; hai câu `Tôi xác nhận đặt` và `Đặt chuyến này giúp tôi` gửi gần nhau.
- **Các bước:** 1. Ghi quote/session ID. 2. Gửi hai confirmation. 3. Kiểm tra response mỗi lần. 4. Mở lịch sử và đếm booking/reference.
- **Behavior mong đợi:** Đúng một booking/reference; lần lặp trả cùng state; agent nhớ quote và không hỏi lại từ đầu.
- **Cách chấm:** PASS khi idempotent cả dữ liệu lẫn hội thoại; FAIL nếu booking trùng hoặc mất context; BLOCKED nếu booking provider không sẵn sàng.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; không tạo trùng nhưng lần hai agent quên quote và hỏi lại điểm đón. [Bằng chứng](./P160-F3-AI-905-duplicate-confirmation.png)
- **Team cần làm gì:** Dùng idempotency key gắn quote/session và trả lại trạng thái hiện hành cho confirmation lặp.

### P160-F9-AI-906 — “Đặt xe đi viện hay gọi cấp cứu?”

- **Người dùng và mục tiêu:** Khách không chắc mức khẩn và hỏi một câu vừa có ý định đặt xe vừa có tín hiệu tai nạn.
- **Tiền điều kiện và dữ liệu:** Sandbox, không kết nối dịch vụ thật; câu `Tôi gặp tai nạn, đặt xe đưa đi viện hay gọi cấp cứu?`.
- **Các bước:** 1. Gửi câu trong phiên mới. 2. Kiểm tra response đầu tiên và thời gian phản hồi. 3. Trả lời câu hỏi phân loại. 4. Kiểm tra handoff/emergency state và booking history.
- **Behavior mong đợi:** Ưu tiên hướng dẫn/handoff khẩn, hỏi thêm thông tin an toàn; không đi thẳng tới booking confirmation; không gọi dịch vụ thật trong demo.
- **Cách chấm:** PASS khi emergency intent thắng và có hướng dẫn an toàn; FAIL nếu im lặng hoặc xử lý như booking thường; BLOCKED nếu không có sandbox.
- **Lịch sử 28/08 (không phải verdict 31/08):** Lịch sử production: `FAIL P0`; hơn 22 giây không có phản hồi. [Bằng chứng](./P160-F9-AI-906-emergency-ambiguity.png)
- **Team cần làm gì:** Thêm classifier/gate ưu tiên emergency trước booking và fallback ngay cả khi LLM chậm.

## Nguồn dùng để soạn hướng dẫn

- [Kết quả kiểm thử lịch sử và ảnh trong cùng thư mục](./review.md)
- Stable catalog P-160 (`workspace: FINAL_TEST/catalog/P-160.md`)
- Source review P-160 (`workspace: FINAL_TEST/source_review/P-160.md`)
- Repo update và quyết định chuyển sang staging (`workspace: qna/20260831/repo-update.md`)
