# OlaSM — Nhận xét cuối trước Demo Day

## 1. Thực trạng hiện tại

- **Phạm vi kiểm tra:** code được đối chiếu tại `origin/main@74c6a06dda9ba506c9b57dbec09ca88858281e75`. Hành vi sản phẩm được quan sát ở staging qua hai lượt `evaluation/e2e/runs/20260902-144231/P-160.md` và `evaluation/e2e/runs/20260902-225202/P-160.md`. Staging không hiển thị build SHA, vì vậy kết quả live là **Observed live**, không được dùng để khẳng định chính xác code nào đang chạy.
- **Verified main — phần đã làm tốt:** kiến trúc và trạng thái nghiệp vụ được mô tả khá rõ trong `docs/PROJECT_SOURCE_OF_TRUTH.md:50-131`; luồng sửa thông tin, xác nhận rõ ràng, chống tạo booking trùng và khôi phục phiên có test tại `tests/test_voice_agent/test_booking_state.py:126,159,172`, `tests/test_voice_agent/test_booking_task.py:405,497,575,658`. CI đã có lint/build/test cho backend và frontend tại `.github/workflows/ci.yml:1-52`. `docs/journal.md` và `docs/worklog.md` cho thấy các quyết định, giới hạn và trách nhiệm tương đối rõ.
- **Observed live — phần đang hoạt động:** sửa điểm đến làm quote thay đổi mà chưa tự đặt xe (`P160-F1-UNHAPPY-004`); câu xác nhận mơ hồ không tạo booking và gửi lại xác nhận không tạo bản ghi trùng (`P160-F1-EDGE-005`, `P160-F3-AI-905`); refresh giữ đúng draft/quote đang chờ (`P160-F1-EDGE-008`); tra cứu trạng thái không bịa chuyến (`P160-F3-HAPPY-002`); câu ngoài kho tri thức biết từ chối thay vì dựng chính sách (`P160-F3-UNHAPPY-004`).
- **Observed live — lỗi ảnh hưởng trực tiếp tới demo:** một câu đã đủ điểm đón, điểm đến và loại xe vẫn bị rơi cả ba slot (`P160-F1-HAPPY-001`); câu code-switch cũng làm mất các entity (`P160-F1-AI-902`); thời gian “9 giờ sáng mai” bị mất sau khi sửa chuyến (`P160-F1-AI-903`); câu hỏi giá chỉ có đủ hai địa điểm vẫn bị hỏi lại pickup (`P160-F3-HAPPY-001`); nguồn chính sách chưa bấm được và thiếu effective date (`P160-F3-AI-003`). Khi microphone bị chặn, màn lỗi chưa cung cấp hướng dẫn hoặc ô nhập thay thế ngay (`P160-F1-UNHAPPY-006`).
- **Release blocker:** hành vi khẩn cấp chưa nhất quán. Câu hỏi về tai nạn còn đề nghị đặt xe đi viện và chưa handoff ngay (`P160-F9-AI-906`); khi người dùng từ chối GPS, hệ thống chưa hỏi đủ thông tin tối thiểu và chưa nói rõ giới hạn dispatch (`P160-F9-UNHAPPY-002`). Handoff record được tạo ở phía khách hàng nhưng chưa có tài khoản operator để xác minh accept/join/takeover, latest context và việc AI dừng nói (`P160-F2-HAPPY-001`, `P160-F2-EDGE-003`, `P160-XFLOW-001`). Các case accent/noise/low-confidence/barge-in vẫn chưa thể xác minh vì thiếu audio injection kiểm soát (`P160-F1-AI-007`, `P160-F1-AI-009`, `P160-F1-AI-010`).
- **Bằng chứng chất lượng AI:** main có workflow eval và một batch 30 lượt connection smoke, nhưng lượt có transcript từ microphone thật trong `reports/voice-finalization-20260821-3calls/report.md:18-39` mới gồm 3 cuộc gọi và cho thấy tail latency/no-final speech vẫn đáng lo. Connection smoke không thay thế task-completion test; bằng chứng hiện tại chưa đủ để chứng minh voice ổn định trên thiết bị, giọng và môi trường thật.

| Hạng mục cần bàn giao | Trạng thái | Nhận xét ngắn |
|---|---|---|
| Source code | **Đã có** | Có frontend, backend, voice agent, migrations, tests và CI trên `main`. |
| README | **Chưa đủ** | Cần canonical staging URL, ảnh/GIF, team ownership, demo limitations và build SHA được demo. |
| Architecture | **Đã có** | Boundary, state ownership và data status được mô tả rõ; cần giữ đúng nhãn demo/staging khi thuyết trình. |
| AI logs/traces | **Chưa đủ** | Có eval JSON và voice artifacts nhưng chưa chọn 5–10 trace provider-backed, redacted, có model/prompt/version/latency. |
| Live URL | **Chưa đủ** | Staging truy cập được nhưng build SHA chưa xác minh; operator flow chưa có tài khoản kiểm thử. |
| Video demo | **Chưa xác minh** | `docs/video-demo.md` mới cung cấp link ngoài; chưa có transcript/timestamp để kiểm nội dung. |
| Pitch deck | **Chưa đủ** | `docs/pitch-deck.pdf` đã có nhưng cần làm rõ dataset latency, business evidence, team và giới hạn staging. |
| Development journal | **Đã có** | Có các entry về quyết định, lỗi và giới hạn. |
| Worklog | **Đã có** | Có mapping thành viên, đầu việc và commit. |
| Evaluation evidence | **Chưa đủ** | Có workflow eval và voice report, nhưng thiếu ma trận voice/device/accent/noise đủ lớn và handoff hai vai trò. |

## 2. Những gì cần bổ sung trước Demo Day

1. **Khóa lại luồng voice booking cốt lõi:** sửa việc rơi pickup/destination/vehicle, code-switch và scheduled time; chạy lại các ID `P160-F1-HAPPY-001`, `P160-F1-AI-901`, `P160-F1-AI-902`, `P160-F1-AI-903` bằng một script demo cố định và lưu trace từng slot.
2. **Đóng safety và handoff:** với câu tai nạn, phải ưu tiên cấp cứu/handoff ngay, không gợi ý đặt xe như phương án tương đương; cấp một operator demo để quay trọn accept → join/takeover → AI dừng → operator thấy đúng latest context. Nếu chưa làm được, phải giới hạn claim là “tạo handoff record”, không nói đã chuyển cuộc gọi hoàn chỉnh.
3. **Chứng minh độ ổn định voice thay vì chỉ minh họa:** chạy một batch cuộc gọi end-user thực sự trên nhiều thiết bị/giọng/nhiễu, công bố task completion, timeout/no-final và p50/p95 theo cùng metric boundary; không dùng 30 lượt connection smoke để thay cho kiểm thử hội thoại và giữ cả failure examples.
4. **Hoàn thiện provenance và recovery ở UI:** hiển thị place/source cho candidate, nguồn/công thức quote, citation bấm được và effective date; khi mic bị từ chối phải có hướng dẫn bật quyền cùng text fallback dùng được ngay.
5. **Khóa gói trình bày theo đúng bản demo:** ghi canonical URL + exact SHA trong README, reconcile số latency trong deck với artifact, và cung cấp video/transcript có happy path, correction, safety/handoff cùng giới hạn mock/staging.
