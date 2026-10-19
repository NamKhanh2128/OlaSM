# MUST DO, Khánh: việc chỉ người làm được (agent và backend)

Cập nhật 19/10/2026. Liên quan: [plan](docs/PLAN_DEMO_GREENSM_VOICE.md), [prompt AI](docs/prompts/PROMPT_KHANH.md).

AI chỉ được thêm mục mới vào file này, không sửa hay xoá mục đã có. Một mục chỉ đóng khi đã làm đúng dòng **Kiểm chứng**.

---

## K-H1. Lấy Goong REST API key

- **Việc làm:** tạo tài khoản Goong, tạo REST API key cho môi trường dev, điền vào `.env`.
- **Tại sao AI không làm được:** cần đăng ký tài khoản và chấp nhận điều khoản của Goong.
- **Ở đâu:** trang quản lý tài khoản trên goong.io, file `.env` cục bộ.
- **Thao tác:**
  1. Đăng ký tài khoản, tạo một key loại REST API.
  2. Trong `.env` đặt `GEOCODING_PROVIDER=goong`, `ROUTING_PROVIDER=goong`, `MAPS_API_KEY=<REST key>`, `MAPS_BASE_URL=https://rsapi.goong.io`.
  3. Tạo thêm một Map tiles key trong cùng tài khoản, gửi riêng cho Phương để làm mục P-H3.
- **Kết quả mong đợi:** gọi AutoComplete trả về danh sách gợi ý.
- **Kiểm chứng:**
  ```powershell
  curl.exe "https://rsapi.goong.io/Place/AutoComplete?api_key=<REST_KEY>&input=Vincom%20B%C3%A0%20Tri%E1%BB%87u"
  ```
  Response có trường `predictions` không rỗng. Nếu tài liệu Goong đã đổi endpoint thì dùng endpoint mới.
- **Đang chặn:** phase K3 (client Goong, gazetteer, resolver), phần chạy thật của K5.

## K-H2. Kiểm toạ độ điểm đón của POI demo

- **Việc làm:** xác nhận từng toạ độ trong gazetteer demo là đúng điểm đón thật.
- **Tại sao AI không làm được:** cần người nhìn bản đồ và biết điểm đón thực tế. AI không được tự điền toạ độ.
- **Ở đâu:** `data/gazetteer/greensm_demo_places.json`.
- **Thao tác:**
  1. Sau khi AI xong K3, chạy `uv run python scripts/build_demo_gazetteer.py`.
  2. Mở từng toạ độ trên Google Maps hoặc bản đồ Goong.
  3. Lệch quá 30 m so với điểm đón thật thì sửa toạ độ.
  4. Đúng thì đặt `verified: true`.
- **Kết quả mong đợi:** mọi POI trong kịch bản demo có `verified: true`.
- **Kiểm chứng:** không còn mục nào `verified: false` trong file.
- **Đang chặn:** fast path dùng gazetteer ở K3, K4.

## K-H3. Cung cấp polygon vùng phục vụ Hà Nội

- **Việc làm:** quyết định vùng phục vụ của demo và đưa ra file GeoJSON.
- **Tại sao AI không làm được:** đây là quyết định nghiệp vụ, không có nguồn dữ liệu chính thức trong repo.
- **Ở đâu:** một file GeoJSON Polygon hoặc MultiPolygon, biến `MAPS_SERVICE_AREA_PATH` trong `.env`.
- **Thao tác:** vẽ vùng trên geojson.io hoặc lấy từ nguồn được phép dùng, lưu file, đặt đường dẫn vào `.env`. Nếu chọn không kiểm vùng trong demo thì ghi quyết định đó ngay dưới mục này.
- **Kết quả mong đợi:** điểm ngoài vùng nhận `failure` mã `OUT_OF_SERVICE_AREA`.
- **Kiểm chứng:** nói một điểm đến ngoài Hà Nội, agent báo ngoài vùng phục vụ.
- **Đang chặn:** kiểm vùng phục vụ trong resolver ở K3.

## K-H4. Thu âm bộ ASR giọng thật

- **Việc làm:** thu 50 câu đặt xe × 3 người giọng Bắc, Trung, Nam, có cả môi trường yên tĩnh và ồn.
- **Tại sao AI không làm được:** cần giọng người thật và sự đồng ý ghi âm.
- **Ở đâu:** thư mục audio ngoài git, manifest JSONL.
- **Thao tác:**
  1. Lấy đồng ý ghi âm của từng người.
  2. Thu WAV 16 kHz mono. Câu nói theo kịch bản ở mục 4.2 của plan và các POI trong gazetteer demo.
  3. Viết manifest với các trường `case_id`, `dataset_version`, `audio_path`, `audio_sha256`, `consent: true`, `expected_transcript`, `expected_entities`, `accent`, `noise`.
  4. Sau khi AI xong K7, chạy benchmark với model chính và model dự phòng:
     ```powershell
     uv run python scripts/benchmark_livekit_asr.py --manifest <manifest.jsonl> --output-dir <thư mục mới> --model deepgram/nova-3
     uv run python scripts/benchmark_livekit_asr.py --manifest <manifest.jsonl> --output-dir <thư mục mới khác> --model assemblyai/universal-3-5-pro
     ```
  5. Chốt model STT chính theo mục 8A.2 của plan.
- **Kết quả mong đợi:** final latency p50 tối đa 600 ms, địa danh demo đúng 100% sau alias.
- **Kiểm chứng:** hai báo cáo benchmark và quyết định model ghi ngay dưới mục này.
- **Đang chặn:** chốt model STT chính ở Ngày 8 của plan.

## K-H5. Nghe và chọn giọng TTS

- **Việc làm:** chọn giọng tiếng Việt cho agent bằng tai người.
- **Tại sao AI không làm được:** độ tự nhiên, nhịp nghỉ, cách đọc địa chỉ cần người nghe đánh giá.
- **Ở đâu:** nghe trực tiếp qua app khi E2E chạy được. File WAV đo ngày 19/10/2026 nằm tạm ở `C:\Users\KHANH\AppData\Local\Temp\claude\c--Users-KHANH-Documents-GitHub-OlaSM\3d958690-4dbb-45bb-b014-52047a03e208\scratchpad\speech_bench\out\tts`, thư mục này có thể đã bị xoá.
- **Thao tác:** hai người nghe Sonic-3.6, Sonic-3.5, Sonic-3 cùng giọng `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`, nghe thêm 2 đến 3 giọng tiếng Việt khác của Cartesia. Chấm độ tự nhiên, độ rõ, cách đọc địa chỉ và số.
- **Kết quả mong đợi:** một model và một voice id được chọn.
- **Kiểm chứng:** `LIVEKIT_TTS_MODEL` và `LIVEKIT_TTS_VOICE` trong `.env` là giá trị đã chọn. Điểm của hai người ghi dưới mục này.
- **Đang chặn:** chốt giọng cho demo.

## K-H6. Chọn vị trí chạy agent

- **Việc làm:** đo và chọn nơi chạy agent worker theo mục 9.2 của plan.
- **Tại sao AI không làm được:** cần tài khoản LiveKit Cloud, quyền deploy, điện thoại thật chạy app.
- **Ở đâu:** LiveKit Cloud project, CLI `lk`, máy demo của Phương.
- **Thao tác:**
  1. Kiểm gói LiveKit Cloud đang dùng. Gói Build có thể khởi động nguội vài giây.
  2. Cài `lk`, đăng nhập bằng `lk cloud auth`.
  3. Deploy agent theo tài liệu agent deployment của LiveKit ở hai vùng `us-east` và `ap-south`. Có VPS Singapore thì chạy thêm worker tự host.
  4. Mỗi phương án chạy 20 phiên kịch bản 1 và 2 từ Hà Nội, làm cùng Phương.
  5. So e2e p50 và p95 bằng `scripts/aggregate_livekit_evaluation.py`.
- **Kết quả mong đợi:** chọn được phương án có e2e p50 và p95 tốt nhất.
- **Kiểm chứng:** bảng p50, p95 của từng phương án và quyết định ghi dưới mục này.
- **Đang chặn:** cấu hình deploy cho ngày demo.

## K-H7. Benchmark latency 20 phiên E2E

- **Việc làm:** đo latency toàn luồng trên máy thật và so với mục tiêu ở mục 1 của plan.
- **Tại sao AI không làm được:** cần app trên điện thoại thật, giọng nói thật, cả hai nhánh code đã gộp.
- **Ở đâu:** worker có `LIVEKIT_DEBUG_EVENT_LOG=true`, log `[PERF-CLIENT]` từ app của Phương.
- **Thao tác:**
  1. Chạy 20 phiên theo 3 kịch bản ở mục 4.2 của plan.
  2. Chạy `scripts/aggregate_livekit_evaluation.py` trên log của worker, xem tham số bằng `--help`.
  3. Ghép với log `[PERF-CLIENT]` Phương gửi.
- **Kết quả mong đợi:** e2e p50 tối đa 1,2 s, p95 tối đa 2,0 s, chốt lượt p50 tối đa 0,6 s.
- **Kiểm chứng:** bảng p50, p95 theo từng stage ghi dưới mục này.
- **Đang chặn:** mốc đạt ngưỡng latency ở Ngày 7 của plan.
