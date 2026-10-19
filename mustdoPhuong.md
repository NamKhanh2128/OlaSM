# MUST DO, Phương: việc chỉ người làm được (mobile và UI)

Cập nhật 19/10/2026. Liên quan: [plan](docs/PLAN_DEMO_GREENSM_VOICE.md), [prompt AI](docs/prompts/PROMPT_PHUONG.md).

AI chỉ được thêm mục mới vào file này, không sửa hay xoá mục đã có. Một mục chỉ đóng khi đã làm đúng dòng **Kiểm chứng**.

---

## P-H1. Chụp ảnh tham chiếu app Green SM

- **Việc làm:** chụp đủ các màn của luồng đặt xe trên app Green SM thật để AI đo token thiết kế.
- **Tại sao AI không làm được:** cần điện thoại thật đã cài và đăng nhập Green SM.
- **Ở đâu:** máy Android dùng cho demo, thư mục `olasm_mobile/design_reference/`. Nếu repo để public thì không commit thư mục này.
- **Thao tác:**
  1. Cập nhật Green SM lên bản mới nhất.
  2. Chụp từng màn bằng `adb shell screencap -p /sdcard/<tên>.png` rồi `adb pull /sdcard/<tên>.png`. Đặt tên đúng thứ tự:
     `01_home.png`, `02_search_destination.png`, `03_search_results.png`, `04_pickup_on_map.png`, `05_service_selection.png`, `06_payment_promo.png`, `07_confirm.png`, `08_deeplink_landing.png`, `09_bottom_sheet_expanded.png`, `10_activity_tab.png`, `11_payment_tab.png`, `12_account_tab.png`.
  3. Quay một lượt đặt xe bằng `adb shell screenrecord /sdcard/flow.mp4` để AI xem chuyển cảnh.
  4. Tạo `device.txt` ghi model máy cùng kết quả của `adb shell wm size` và `adb shell wm density`.
- **Kết quả mong đợi:** đủ 12 ảnh, 1 video, `device.txt`.
- **Kiểm chứng:** thư mục có đủ các file trên.
- **Đang chặn:** phase P4 (design system và màn hình).

## P-H2. Spec deeplink Green SM

- **Việc làm:** điền cấu hình deeplink thật và thử trên máy demo.
- **Tại sao AI không làm được:** spec deeplink chỉ bạn có. AI không được tự đặt template.
- **Ở đâu:** `olasm_mobile/assets/config/greensm_deeplink.json`, máy demo.
- **Thao tác:**
  1. Thử URL mẫu trước:
     ```powershell
     adb shell am start -a android.intent.action.VIEW -d "<URL mẫu>"
     ```
     Ghi lại màn đích có hiện đúng điểm đón, điểm đến, dịch vụ hay không, và có cần đăng nhập trước không.
  2. Điền `template` với các biến `{pickup_lat}`, `{pickup_lng}`, `{pickup_name}`, `{pickup_address}`, `{dest_lat}`, `{dest_lng}`, `{dest_name}`, `{dest_address}`, `{service_code}`. Chỉ dùng biến mà deeplink thật nhận.
  3. Điền `service_codes` cho `GSM_BIKE`, `GSM_MINI`, `GSM_CAR`, `GSM_PREMIUM`, và `fallback_url`.
  4. Báo scheme cho AI để thêm `<queries>` trong AndroidManifest và `LSApplicationQueriesSchemes` trong Info.plist.
- **Kết quả mong đợi:** lệnh adb mở đúng màn xác nhận Green SM với đúng dữ liệu.
- **Kiểm chứng:** chạy lại lệnh adb bằng URL do `GreenSmDeeplinkBuilder` sinh ra cho kịch bản 1 của plan.
- **Đang chặn:** mở deeplink thật ở P3, chạy E2E.

## P-H3. Chạy app với key bản đồ Goong

- **Việc làm:** nhận Map tiles key từ Khánh, chạy app có bản đồ thật.
- **Tại sao AI không làm được:** key do tài khoản Goong của nhóm cấp, xem mục K-H1 của Khánh.
- **Ở đâu:** lệnh `flutter run` trên máy demo.
- **Thao tác:**
  ```powershell
  flutter run --dart-define=GOONG_MAP_TILES_KEY=<map tiles key> --dart-define=BACKEND_URL=http://<IP máy chạy backend>:8000
  ```
- **Kết quả mong đợi:** Home hiện bản đồ Hà Nội có vị trí hiện tại.
- **Kiểm chứng:** nhìn thấy bản đồ và marker vị trí trên máy demo.
- **Đang chặn:** bản đồ ở P4.

## P-H4. Xin quyền dùng logo và icon Green SM

- **Việc làm:** xin bộ asset chính thức của Green SM.
- **Tại sao AI không làm được:** cần phép của chủ thương hiệu, AI không được trích asset từ APK.
- **Ở đâu:** đầu mối GSM của chương trình VRIC × GSM, thư mục `olasm_mobile/assets/brand/`.
- **Thao tác:** gửi yêu cầu, nhận file, đặt vào `olasm_mobile/assets/brand/`, rồi chạy lại prompt để AI thay Material Icons.
- **Kết quả mong đợi:** app dùng logo và icon dịch vụ chính thức.
- **Kiểm chứng:** có văn bản đồng ý, asset nằm trong thư mục trên.
- **Đang chặn:** hoàn thiện nhận diện thương hiệu ở P4.

## P-H5. Chốt font

- **Việc làm:** xác định font app Green SM đang dùng và quyền sử dụng.
- **Tại sao AI không làm được:** cần đối chiếu bằng mắt trên ảnh thật và kiểm giấy phép font.
- **Ở đâu:** ảnh ở P-H1, thư mục `olasm_mobile/assets/fonts/`.
- **Thao tác:** nhận diện font từ ảnh, kiểm giấy phép. Được dùng thì đặt file font vào thư mục trên. Không được dùng thì chọn font gần nhất hiển thị tốt dấu tiếng Việt và ghi lý do dưới mục này.
- **Kết quả mong đợi:** một font đã chốt.
- **Kiểm chứng:** tên font và nguồn giấy phép ghi dưới mục này.
- **Đang chặn:** token chữ `GsmText` ở P4.

## P-H6. Duyệt giao diện và khoá golden test

- **Việc làm:** so từng màn của app demo với app thật rồi khoá golden.
- **Tại sao AI không làm được:** cần người duyệt bằng mắt trên cùng một máy.
- **Ở đâu:** máy demo, Figma.
- **Thao tác:**
  1. Chụp app demo và app thật ở cùng màn, chồng 50% trong Figma.
  2. Đối chiếu checklist mục A5 của plan: màu đúng mã đo được, cỡ chữ lệch tối đa 1 sp, khoảng cách lệch tối đa 2 dp, bo góc và vị trí icon đúng.
  3. Đạt thì chạy `flutter test --update-goldens` rồi commit file golden.
- **Kết quả mong đợi:** 5 màn chính đạt checklist.
- **Kiểm chứng:** `flutter test` xanh với golden đã khoá.
- **Đang chặn:** golden test.

## P-H7. Chạy E2E trên máy thật, làm cùng Khánh

- **Việc làm:** chạy toàn luồng từ bấm mic tới màn xác nhận Green SM.
- **Tại sao AI không làm được:** cần điện thoại thật, giọng nói thật, cả hai nhánh code đã gộp.
- **Ở đâu:** máy demo đã cài và đăng nhập Green SM, backend và worker do Khánh chạy.
- **Thao tác:**
  1. Gộp hai nhánh `feat/greensm-demo-agent` và `feat/greensm-demo-mobile`.
  2. `flutter build apk --debug`, rồi `adb install` file APK.
  3. Chạy 3 kịch bản ở mục 4.2 của plan, 10 lượt liên tiếp.
  4. Lưu log bằng `adb logcat | findstr PERF-CLIENT`, gửi Khánh cho mục K-H7.
- **Kết quả mong đợi:** 10/10 lượt tới đúng màn xác nhận với đúng điểm đón, điểm đến, dịch vụ.
- **Kiểm chứng:** biên bản 10 lượt ghi dưới mục này.
- **Đang chặn:** mốc Ngày 5 đến Ngày 7 của plan.

## P-H8. Đo 60 fps trên máy demo

- **Việc làm:** kiểm app mượt trên máy dùng để demo.
- **Tại sao AI không làm được:** cần máy thật và DevTools.
- **Ở đâu:** `flutter run --profile`, tab Performance của DevTools.
- **Thao tác:** mở Home, Route, voice sheet lúc agent đang nói và lúc bản đồ vẽ tuyến.
- **Kết quả mong đợi:** không có chuỗi frame quá 16 ms kéo dài.
- **Kiểm chứng:** ảnh chụp biểu đồ frame ghi dưới mục này.
- **Đang chặn:** nghiệm thu hiệu năng ở mục A5 của plan.

## P-H9. Nghe thử mẫu VoxCPM cho wake word

- **Việc làm:** chọn cách viết cụm wake word để TTS sinh dữ liệu đúng giọng Việt.
- **Tại sao AI không làm được:** cần tai người nghe và GPU để sinh mẫu.
- **Ở đâu:** bản clone repo `livekit/livekit-wakeword`, file `configs/green_sm_oi_voxcpm.yaml` do AI tạo ở P6.
- **Thao tác:** sinh một lô nhỏ theo kiểu `configs/test_voxcpm.yaml` của thư viện cho hai cách viết "Green SM ơi" và "grin ét em ơi", nghe, chọn cách đúng giọng Việt hơn, sửa `target_phrases` theo cách đã chọn.
- **Kết quả mong đợi:** một cách viết đã chốt.
- **Kiểm chứng:** `target_phrases` trong file cấu hình là cách đã chọn.
- **Đang chặn:** P-H10.

## P-H10. Huấn luyện wake word trên GPU

- **Việc làm:** chạy pipeline huấn luyện của livekit-wakeword.
- **Tại sao AI không làm được:** cần GPU đám mây, tài khoản và nhiều giờ chạy.
- **Ở đâu:** máy có GPU hoặc job SkyPilot theo `skypilot/train.yaml` của thư viện.
- **Thao tác:**
  1. Clone repo `livekit/livekit-wakeword`, chép `configs/green_sm_oi_voxcpm.yaml` từ repo OlaSM vào thư mục `configs/` của bản clone.
  2. Trong bản clone chạy:
     ```bash
     uv sync --extra train --extra voxcpm
     livekit-wakeword setup --config configs/green_sm_oi_voxcpm.yaml
     livekit-wakeword run configs/green_sm_oi_voxcpm.yaml
     ```
  3. Copy file ONNX kết quả vào `olasm_mobile/assets/models/green_sm_oi.onnx` của repo OlaSM.
- **Kết quả mong đợi:** có model ONNX đã huấn luyện.
- **Kiểm chứng:** file model nằm đúng thư mục, kèm log huấn luyện.
- **Đang chặn:** tích hợp wake word ở P6.

## P-H11. Đánh giá cổng nghiệm thu wake word

- **Việc làm:** quyết định có bật wake word trong demo hay không.
- **Tại sao AI không làm được:** cần thu âm người thật và âm thanh nền thật.
- **Ở đâu:** bộ audio ngoài git, lệnh eval của thư viện.
- **Thao tác:**
  1. Thu 200 lần nói "Green SM ơi" của ít nhất 10 người, và ít nhất 3 giờ âm thanh nền tiếng Việt gồm hội thoại, TV, đường phố.
  2. Chạy `livekit-wakeword eval configs/green_sm_oi_voxcpm.yaml -m olasm_mobile/assets/models/green_sm_oi.onnx`, chọn ngưỡng từ đường DET.
  3. Đạt khi recall từ 85% trong phòng yên tĩnh và báo nhầm tối đa 0,5 lần mỗi giờ trên âm thanh nền.
- **Kết quả mong đợi:** quyết định bật hoặc không bật, kèm ngưỡng.
- **Kiểm chứng:** số recall, số báo nhầm mỗi giờ và quyết định ghi dưới mục này. Bật thì chạy app với `--dart-define=WAKEWORD_ENABLED=true`.
- **Đang chặn:** bật wake word trong demo.

## P-H12. Xác nhận danh sách dịch vụ ở Hà Nội

- **Việc làm:** kiểm dịch vụ nào thật sự có trên app Green SM ở Hà Nội.
- **Tại sao AI không làm được:** cần xem app thật, dựa vào ảnh `05_service_selection.png` ở P-H1.
- **Ở đâu:** app Green SM thật.
- **Thao tác:** đối chiếu Green SM Bike, Mini, Car, Premium với app. Khác danh sách trong `data/greensm_demo_services.json` thì báo Khánh sửa.
- **Kết quả mong đợi:** danh sách dịch vụ của demo khớp app thật.
- **Kiểm chứng:** danh sách đã đối chiếu ghi dưới mục này.
- **Đang chặn:** danh mục dịch vụ ở K3 của Khánh, mã dịch vụ trong P-H2.
