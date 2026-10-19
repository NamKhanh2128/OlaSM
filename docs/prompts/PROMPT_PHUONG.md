# PROMPT CHO AI: Phương, app Flutter demo Green SM

> Cách dùng: mở repo OlaSM ở thư mục gốc, đưa toàn bộ file này cho AI coding agent. Có thể chạy lại nhiều lần. Mỗi lần chạy, AI tự xác định phase nào đã xong (đầu mục 6) rồi tiếp tục từ phase chưa xong.
>
> Cập nhật 19/10/2026. Các API trong prompt đã đối chiếu với mã nguồn `livekit_client` 2.13.1, `maplibre_gl` 0.24.1 và `livekit-wakeword` vào ngày này.

---

## 1. Vai trò và mục tiêu

Bạn là kỹ sư Flutter phụ trách **app mobile và UI** của demo trợ lý giọng nói đặt xe Green SM. Người chịu trách nhiệm là Phương.

Hoàn thiện toàn bộ phần việc sau trong `docs/PLAN_DEMO_GREENSM_VOICE.md`: Workstream A (mục 5), Workstream B (mục 6), phía app của hợp đồng dữ liệu (mục 10), wake word phía app (mục 8B).

Kết quả cuối: app Android có giao diện khớp app Green SM. Người dùng bấm mic, nói yêu cầu đặt xe, thấy bản đồ và thông tin cập nhật theo lời agent. Khi người dùng đồng ý, app mở deeplink tới màn xác nhận đặt xe của app Green SM thật.

Ưu tiên Android. iOS chỉ sửa các khai báo được nêu ở P1 và P3. Build iOS cần máy Mac, nên nếu máy đang chạy không phải macOS thì ghi mục mustdo kiểm build iOS thay vì tuyên bố iOS biên dịch được.

---

## 2. Đọc trước khi code (bắt buộc, theo thứ tự)

1. `docs/PLAN_DEMO_GREENSM_VOICE.md`: mục 0, 2.2, 3, 4, 5, 6, 8B, 9, 10, 11, 13. Đọc cả mục 14 (câu hỏi còn mở), không tự quyết thay người.
2. `mustdoPhuong.md`: việc người đang làm. Không làm thay, không thêm mục trùng.
3. Toàn bộ `olasm_mobile/`, cùng `configs/hey_olasm_vietnamese.yaml` và `scripts/train_export_wakeword.py` (các file này sẽ bị xoá ở P1 và P6, đọc để biết đang dùng gì).
4. Tài liệu LiveKit Flutter: lớp `Session`, `SessionOptions`, `Agent` trên pub.dev, và `lib/controllers/app_ctrl.dart` của repo `livekit-examples/agent-starter-flutter`.
5. Khi dùng API của `livekit_client`, `maplibre_gl`, `url_launcher`, `geolocator`, `go_router`, `audioplayers`, đọc source trong pub cache của đúng bản đã cài để lấy chữ ký. Không đoán API.
6. Phase P6: repo `livekit/livekit-wakeword`, gồm `src/livekit/wakeword/inference/{model,listener}.py`, `src/livekit/wakeword/models/feature_extractor.py`, `src/livekit/wakeword/session.py`, `docs/feature-extraction.md`, `configs/prod_voxcpm.yaml`, `tests/test_pretrained.py`.

### Điểm plan lệch với mã nguồn thật (đã kiểm ngày 19/10/2026)

Khi plan và bảng này khác nhau, làm theo bảng. Không sửa plan. Ghi các điểm đã áp dụng vào báo cáo cuối.

| Plan nói | Mã nguồn thật | Cách làm |
|---|---|---|
| B5: `localParticipant.registerRpcMethod` | Hàm nằm trên `Room`: `registerRpcMethod(String method, RpcRequestHandler handler)`, với `RpcRequestHandler = Future<String> Function(RpcInvocationData)`. Đăng ký hai lần cùng tên ném ngoại lệ | `session.room.registerRpcMethod(...)` đúng một lần, ngay sau khi tạo `Room`, trước `session.start()` |
| B7: `Hardware.instance.setSpeakerphoneOn(true)` | Hàm đã `@Deprecated`. SDK mặc định ưu tiên loa ngoài (`isSpeakerOutputPreferred` là true) và áp dụng lúc kết nối, trên cả Android lẫn iOS | Gọi `AudioManager.instance.setSpeakerOutputPreferred(true)` một lần. Không dùng hàm deprecated (analyze sẽ báo), không cấu hình `audio_session` thủ công |
| A4: caption khách interim màu xám, final màu đậm | `UserTranscript` và `AgentTranscript` chỉ có trường `text`, không có cờ final | Câu khách mới nhất là interim khi `agent.agentState` còn `listening`, thành final khi agent sang `thinking` hoặc `speaking` |
| B3: `session.start()` | Không ném lỗi. Lỗi nằm ở `session.error` (`SessionError`), còn `agent.error` là `AgentFailure` (timeout, left). `agent.agentState` có thể null | Kiểm cả hai sau `start()` và trong listener |
| B2: pre-connect vẫn đệm mic lúc chờ token | Với `preConnectAudio: true`, `Session.start()` bật đệm mic trước rồi mới gọi `fetch()` của token source | Dùng `TokenSourceFixed` tự viết: `fetch()` trả ngay token lấy sẵn, chưa có thì gọi HTTP bên trong `fetch()`. Không `await` lấy token trước `start()` |
| B3: vòng đời Session | Mỗi token gắn một room. `Session.dispose()` không giải phóng `Room` | Mỗi phiên tạo `Room` và `Session` mới. Kết thúc: `end()`, hủy listener, `await session.dispose()`, `await room.dispose()` |
| B1: SDK | `livekit_client` 2.13.1 yêu cầu Dart ≥ 3.10 và Flutter ≥ 3.38, còn `pubspec.yaml` hiện ghi `>=3.5.0` | Gate ở P0, cập nhật `environment` ở P1 |
| A3: bản đồ | `maplibre_gl` 0.24.1: `CameraUpdate.newLatLngBounds(LatLngBounds, {left, top, right, bottom})`. Marker là `Symbol`, cần `addImage` đăng ký ảnh trước. Chấm điểm đón dùng `addCircle` | Dùng đúng các API này |

---

## 3. Phạm vi sở hữu

### 3.1 Quyền sửa

**Được sửa:** `olasm_mobile/`, file cấu hình wake word trong `configs/`, xoá `scripts/train_export_wakeword.py`, `mustdoPhuong.md`.

**Không được sửa:** `src/`, `data/`, `tests/` của Python, toàn bộ `docs/` (kể cả plan và các prompt), `mustdoKhanh.md`, `mustdo.md`, `README.md` và `.gitignore` ở thư mục gốc.

### 3.2 Bản đồ file đích trong `olasm_mobile/`

Mọi file mới phải nằm trong bản đồ này. Thêm file ngoài bản đồ chỉ khi bắt buộc về kỹ thuật, và phải nêu trong báo cáo. Không thêm thư mục cấp cao mới, không tạo file `.md`.

```text
olasm_mobile/
  pubspec.yaml, pubspec.lock, analysis_options.yaml, .gitignore, .metadata
  assets/
    config/greensm_deeplink.json          P3
    sounds/{wake_ack.wav,end_session.wav} có sẵn
    models/                               P6: melspectrogram.onnx, embedding_model.onnx, NOTICE.txt
                                          người đưa vào: green_sm_oi.onnx (P-H10)
    brand/, fonts/                        người đưa vào (P-H4, P-H5)
  design_reference/                       người đưa vào (P-H1), không commit
  tool/wakeword_parity.py                 P6
  lib/
    main.dart
    app/ app.dart, router.dart
         theme/ gsm_tokens.dart, gsm_theme.dart
         widgets/ gsm_<tên>.dart          mỗi component một file (mục A2 của plan)
    core/ config/app_config.dart
          backend/ token_prefetcher.dart, voice_credentials.dart
          location/location_service.dart
          permissions/permission_service.dart
          telemetry/perf_client.dart
          audio/chime_player.dart
    features/
      splash/  home/  route/              mỗi màn một thư mục, file màn + widget riêng của màn
      voice/ voice_session_controller.dart, voice_token_source.dart,
             voice_providers.dart, booking_state.dart, voice sheet widgets
      map/ gsm_map.dart, polyline_decoder.dart
      deeplink/ greensm_deeplink_config.dart, greensm_deeplink_builder.dart, greensm_launcher.dart
      wakeword/wakeword_bridge.dart       P6
  test/                                   phản chiếu lib/, tên file *_test.dart
  android/app/src/main/kotlin/com/olasm/mobile/
    MainActivity.kt
    wakeword/ WakeWordPipeline.kt, WakeWordEngine.kt, WakeWordPlugin.kt     P6
  android/app/src/test/kotlin/com/olasm/mobile/wakeword/WakeWordParityTest.kt   P6
  android/app/src/test/resources/wakeword/ positive.wav, negative.wav, hey_livekit.onnx, reference_scores.json   P6
  android/app/src/debug/AndroidManifest.xml   do flutter create sinh ra (P0)
```

---

## 4. Nguyên tắc bắt buộc

1. **Không mock, không bịa dữ liệu.**
   - Không viết gateway giả, LiveKit giả, agent giả để app "chạy được".
   - Không tự đặt mã màu, cỡ chữ, bo góc, bóng, khoảng cách. Mọi token thiết kế phải đo từ ảnh chụp app Green SM thật trong `olasm_mobile/design_reference/`.
   - **Kỷ luật token:** không có literal màu (`Color(0x…)`, `Colors.<tên>` trừ `Colors.transparent`), cỡ chữ, bán kính, bóng, khoảng cách bằng số ngoài `olasm_mobile/lib/app/theme/`. Widget đọc giá trị từ `GsmTokens`. Khi chưa có số đo (P4a), `gsm_tokens.dart` dùng giá trị mặc định của Material 3 và font hệ thống, mỗi giá trị có comment `// provisional: chưa đo, chờ P-H1`. Không tự chọn màu thương hiệu.
   - Không tự đặt template deeplink, scheme hay mã dịch vụ. Các giá trị này do người điền vào `olasm_mobile/assets/config/greensm_deeplink.json`.
   - Logo, icon, font của Green SM chỉ dùng khi người đã đưa file chính thức vào repo. Trước đó dùng Material Icons và font hệ thống.
   - Không tự bịa nội dung hiển thị: mục "địa điểm gần đây" ở Home chỉ hiện khi có dữ liệu thật, demo chưa có nguồn nên ẩn mục này và nêu trong báo cáo. Các tab Hoạt động, Thanh toán, Tài khoản chỉ có khung và tiêu đề, không điền dữ liệu người dùng.
   - Fixture JSON mẫu (ví dụ ở mục 5.2) chỉ được nằm trong `test/`, không lọt vào `lib/` hay `assets/`.
2. **Việc cần người thì ghi vào `mustdoPhuong.md`.** Khi gặp việc AI không tự làm được, viết code đầy đủ tới sát ranh giới đó, rồi thêm một mục theo mẫu ở mục 7. Không đánh dấu xong thay người, không xoá hay sửa mục người đã ghi, không thêm mục trùng P-H1 đến P-H12. Các trường hợp chưa có mục sẵn và phải thêm khi gặp: thiếu hoặc quá cũ toolchain (P0), cần máy Mac để kiểm build iOS (P1), chạy bộ so điểm wake word trên điện thoại ARM64 thật (P6).
3. **Test tự động chỉ cho logic thuần và hiển thị.**
   - Được test: parser booking state, deeplink builder, logic hạn token, bộ giải mã polyline, hàm định dạng, widget render từ state ví dụ đúng hợp đồng ở mục 5.
   - Không viết integration test với gateway giả.
   - Không khoá golden test khi người chưa duyệt giao diện. Việc duyệt đã có trong mustdo (P-H6).
4. **Không làm ngoài plan.** Không thêm màn hình, tính năng, tài liệu, báo cáo. Chuỗi app gửi cho agent chỉ có hai loại: chữ người dùng gõ và `chọn số N` (mục 5.4). Danh sách dịch vụ ở màn Route chỉ hiển thị dịch vụ hiện tại, không chạm được, vì hợp đồng chưa có thông điệp đổi dịch vụ bằng chạm. Không tạo file `.md` nào ngoài `mustdoPhuong.md`.
5. **Chất lượng:** `flutter analyze` sạch (kể cả mức info, nên không dùng API deprecated), `flutter test` xanh, `flutter build apk --debug` thành công. Tuân thủ `analysis_options.yaml` có sẵn và không tắt lint. Log bằng `debugPrint`, không dùng `print` (lint `avoid_print` đang bật). Không để code chết, code bị comment, TODO không có mục mustdo tương ứng. Model viết tay, không dùng sinh mã (freezed, json_serializable, riverpod_generator).
6. **Bí mật và riêng tư:** key bản đồ và URL backend truyền bằng `--dart-define`, không commit giá trị. Không log toạ độ người dùng và `participantToken`. Không `git add` thư mục `design_reference/` (ảnh thuộc Green SM, để trong `.gitignore` của `olasm_mobile`), người dùng tự quyết định việc commit theo mục P-H1.
7. **Git:** làm trên nhánh `feat/greensm-demo-mobile`. Commit sau mỗi phase đạt tiêu chí, message dạng `feat(mobile): P<phase> <nội dung>` (ví dụ `P2`, `P4a`). Luôn `git add` theo đường dẫn cụ thể, không dùng `git add -A` hay `git add .` (cây làm việc có file chưa theo dõi ngoài phạm vi như `docs/`, `mustdoKhanh.md`, `olasm_mobile/android/.gradle/`). `mustdoPhuong.md` đang chưa được git theo dõi, thêm nó vào commit khi có thay đổi. Không push khi người dùng chưa yêu cầu.

---

## 5. Hợp đồng dữ liệu chung

Khối này giống hệt trong prompt của Khánh. Không tự đổi tên trường, giá trị enum hay topic. Cần đổi thì dừng phần đó và thêm mục vào mustdo để hai người thống nhất.

**5.1 Token** `POST /api/v1/mobile/voice-token`

- Request: `{"device_id": str 8-128 ký tự, "trigger_source": "push_to_talk" | "wake_word" | "prefetch", "location": {"lat": float, "lng": float, "accuracy_m": float} | null, "screen": "HOME" | "ROUTE"}`
- Response `201`: `{"server_url", "participant_token", "room_name", "agent_name", "token_ttl_seconds"}`
- Mỗi token gắn một room mới và chỉ dùng một lần. Backend đưa `location` và `screen` vào dispatch metadata, `schema_version` là `"2"`.

**5.2 Booking state, agent gửi app**

Data packet reliable, topic `greensm.booking_state.v2`, JSON UTF-8, tối đa 10 KB. Gửi sau mỗi thay đổi, trước khi agent nói.

```json
{
  "schema": "greensm.booking_state.v2",
  "revision": 7,
  "stage": "ready_to_confirm",
  "pickup": {"status": "resolved", "source": "current_location", "name": "Vị trí hiện tại",
             "address": "12 Chùa Bộc, Đống Đa, Hà Nội", "lat": 21.007412, "lng": 105.828613},
  "destination": {"status": "resolved", "source": "gazetteer", "name": "Sân bay Nội Bài - Ga T1",
                  "address": "Sóc Sơn, Hà Nội", "lat": 21.218716, "lng": 105.804176},
  "service": {"status": "resolved", "id": "GSM_CAR", "label": "Green SM Car", "defaulted": true},
  "candidates": null,
  "route": {"distance_m": 27450, "duration_s": 2580, "polyline": "<encoded polyline>", "provider": "goong"},
  "failure": null
}
```

Toạ độ trong ví dụ chỉ minh hoạ định dạng, không được dùng làm dữ liệu.

- `stage`: `collecting` | `disambiguating` | `ready_to_confirm` | `handing_off` | `handed_off` | `abandoned`.
- `Place`: `{"status", "source": "current_location" | "gazetteer" | "goong" | null, "name", "address", "lat", "lng"}`. `lat`, `lng` chỉ có giá trị khi `status` là `resolved`. Thiếu hẳn thì gửi `{"status": "missing", ...null}`.
- `SlotStatus`: `missing` | `needs_clarification` | `resolved`.
- `ServiceId`: `GSM_BIKE` | `GSM_MINI` | `GSM_CAR` | `GSM_PREMIUM`.
- `candidates` khi mơ hồ: `{"target": "pickup" | "destination", "query": str, "options": [{"index": int từ 1, "name": str, "subtitle": str, "distance_km": float | null}]}`, tối đa 5 option.
- `route`: `{"distance_m": int, "duration_s": int, "polyline": str, "provider": "goong"}`. `polyline` là encoded polyline chuẩn Google, precision 5.
- `failure`: `{"code", "message": str tiếng Việt hiển thị được, "retryable": bool}`. `code`: `PLACE_NOT_FOUND` | `ASR_LOW_CONFIDENCE` | `OUT_OF_SERVICE_AREA` | `ROUTE_UNAVAILABLE` | `PROVIDER_UNAVAILABLE` | `HANDOFF_FAILED`.
- `revision` tăng dần. App bỏ mọi gói có `revision` nhỏ hơn hoặc bằng gói đang giữ.

**5.3 RPC mở Green SM, agent gọi app**

Method `greensm.open_confirmation`, gọi tới participant của khách, `response_timeout` 5 s.

- Payload: `{"trip_ref": str, "service_id": ServiceId, "pickup": {"name", "address", "lat", "lng"}, "destination": {"name", "address", "lat", "lng"}, "route": {"distance_m", "duration_s"} | null}`
- App trả `{"opened": true}` hoặc `{"opened": false, "reason": "NOT_INSTALLED" | "LAUNCH_FAILED" | "INVALID_PAYLOAD" | "DEEPLINK_NOT_CONFIGURED"}`.

**5.4 App gửi agent:** chữ nhập tay gửi bằng `session.sendText(text)`. Chạm dòng thứ N trong danh sách lựa chọn gửi đúng chuỗi `chọn số N`.

**5.5 Mã dịch vụ trong deeplink** chỉ nằm trong cấu hình app `olasm_mobile/assets/config/greensm_deeplink.json`. Agent chỉ biết `ServiceId`.

---

## 6. Các phase

Làm theo thứ tự. Mỗi phase chỉ xong khi đạt tiêu chí. Phần bị chặn bởi người thì ghi mustdo rồi làm tiếp phần không bị chặn.

**Chạy lại:** chạy `git log --oneline` trên nhánh để biết phase đã commit (commit mở đầu `feat(mobile): P<phase>`), rồi kiểm lại tiêu chí của phase đó bằng lệnh thật trước khi bỏ qua. Đọc lại `mustdoPhuong.md` và các file do người cung cấp (`design_reference/`, `assets/config/greensm_deeplink.json`, `assets/models/green_sm_oi.onnx`, `assets/brand/`, `assets/fonts/`) để biết phần bị chặn nào đã được gỡ. Chỉ dựa vào file có thật, không dựa vào việc mục mustdo còn hay mất.

### P0. Kiểm tra đầu vào và môi trường

1. Tạo nhánh `feat/greensm-demo-mobile` (đã có thì `git switch`).
2. **Cổng toolchain.** Chạy `flutter --version`, `flutter doctor -v`, `adb devices`. Cần Flutter ≥ 3.38 (Dart ≥ 3.10), Android SDK, và JDK từ 17 đến 23 cho Gradle (Gradle 8.10.2 của dự án không chạy với JDK mới hơn, ví dụ JDK 26 đang đặt ở `JAVA_HOME` trên một số máy; khi đó trỏ `flutter config --jdk-dir` về JDK 17 của Android Studio). Thiếu hoặc quá cũ thì thêm mục mustdo "Cài hoặc nâng toolchain" kèm lệnh chính xác, rồi chỉ làm phần không cần toolchain (P6 phần cấu hình huấn luyện) và báo cáo. Không viết code Dart hay Kotlin mà không thể phân tích và build. Không có thiết bị thì vẫn làm tiếp, các bước cần thiết bị đã nằm trong P-H7 và P-H8.
3. **Baseline.** Trong `olasm_mobile/` chạy `flutter pub get`, `flutter analyze`, `flutter test`, `flutter build apk --debug` và ghi kết quả. Trạng thái repo đã biết (19/10/2026): chưa có thư mục `test/` nên `flutter test` báo lỗi, và thiếu scaffolding nên build Android sẽ lỗi. Ghi đúng kết quả thật, không coi là lỗi của bạn.
4. **Sửa scaffolding.** Repo thiếu phần do `flutter create` sinh ra: `android/app/src/main/res/` (manifest tham chiếu `@mipmap/ic_launcher`, `@style/LaunchTheme`, `@style/NormalTheme`), `android/app/src/{debug,profile}/AndroidManifest.xml`, `ios/Runner.xcodeproj`, `ios/Runner.xcworkspace`, `ios/Runner/Assets.xcassets`, `ios/Runner/Base.lproj/`, `ios/Flutter/`, `.metadata` và các `.gitignore` của Flutter. Cách làm:
   - Chạy `flutter create --platforms=android,ios --org com.olasm --project-name olasm_mobile <thư mục tạm ngoài repo>/olasm_mobile`.
   - Chép sang `olasm_mobile/` chỉ những mục còn thiếu ở danh sách trên, không ghi đè file đang có.
   - Không chép `lib/`, `test/`, `pubspec.yaml`, `analysis_options.yaml`, `README.md`, các file `*.kts`. Dự án dùng Gradle Groovy (`build.gradle`, `settings.gradle`), để cả hai kiểu sẽ xung đột.
   - Giữ `applicationId` và namespace `com.olasm.mobile`. Giữ icon launcher mặc định của Flutter (khác app Green SM thật, đúng yêu cầu mục A2 của plan).
   - Xoá thư mục tạm. Đảm bảo `git status` không còn hiện `olasm_mobile/android/.gradle/`, `build/`, `.dart_tool/`. Thêm `design_reference/` vào `olasm_mobile/.gitignore`.
5. **Đầu vào do người cung cấp.** Kiểm xem `olasm_mobile/design_reference/` đã đủ 12 ảnh, `flow.mp4` và `device.txt` theo mục P-H1 chưa, và `assets/config/greensm_deeplink.json` đã có `template` chưa. Thiếu thì phần liên quan bị chặn theo mục mustdo tương ứng (P4b theo P-H1, `<queries>` theo P-H2). Key bản đồ truyền lúc chạy nên không phải điều kiện của phase nào.

**Tiêu chí:** toolchain đạt (hoặc đã có mục mustdo và dừng đúng như bước 2), baseline đã ghi, scaffolding đủ, nhánh đã tạo. Commit các file scaffolding đã chép.

### P1. Dọn code cũ, nâng thư viện, đổi tên app (mục B1)

- Trước khi xoá, chạy `git branch archive/wakeword-legacy` để lưu trạng thái hiện tại. Không checkout, không push.
- **Android:** xoá `kotlin/com/olasm/mobile/wakeword/` và `audio/` (`MelFeatureExtractor.kt`, `AudioFocusArbitrator.kt`; kiểm bằng grep rằng không còn nơi dùng). Sửa `MainActivity.kt` thành lớp rỗng kế thừa `FlutterActivity`, bỏ import và dòng đăng ký `WakeWordPlugin`. Trong `AndroidManifest.xml` bỏ `<service>` của `WakeWordService`, quyền `FOREGROUND_SERVICE*`, thuộc tính `package` (đã có `namespace`). Trong `app/build.gradle` bỏ dependency `onnxruntime-android` (P6 thêm lại). Quyền cần có theo README của `livekit_client` 2.13.1: `RECORD_AUDIO`, `ACCESS_NETWORK_STATE`, `CHANGE_NETWORK_STATE`, `MODIFY_AUDIO_SETTINGS`, `BLUETOOTH` (`maxSdkVersion=30`), `BLUETOOTH_CONNECT`, `BLUETOOTH_ADMIN` (`maxSdkVersion=30`), cùng `INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, và giữ `WAKE_LOCK` đang có. Bỏ `CAMERA` và hai `uses-feature` camera trong README vì demo chỉ dùng âm thanh. Nếu chạy máy thật gặp lỗi liên quan thì thêm lại và ghi vào báo cáo.
- **Android debug:** trong `android/app/src/debug/AndroidManifest.xml` thêm `android:usesCleartextTraffic="true"` cho `<application>`. Backend dev chạy HTTP và Android chặn cleartext theo mặc định, thiếu dòng này thì `BACKEND_URL=http://<IP>:8000` không gọi được. Không đặt dòng này ở manifest chính.
- **iOS:** xoá `ios/Runner/WakeWord/`. Trong `AppDelegate.swift` bỏ đăng ký `WakeWordPlugin`. Trong `Podfile` bỏ `pod 'onnxruntime-objc'`. Trong `Info.plist` đổi `UIBackgroundModes` chỉ còn `audio` (README của `livekit_client` chỉ yêu cầu `audio`), bỏ `voip`, và viết lại chuỗi quyền mic và vị trí bằng tiếng Việt theo tên app mới (không còn nhắc OlaSM hay tổng đài viên).
- **Dart:** xoá toàn bộ `lib/` hiện tại (OlaSM dark theme, `livekit_transport.dart`, `token_cache_manager.dart`, `native_wakeword_bridge.dart`, controller, model, widget, `permission_guard.dart`, `latency_telemetry.dart`, `app_config.dart`). Chúng phụ thuộc lẫn nhau và vào wake word nên không thể giữ lại một phần; mọi thứ cần thiết được viết lại ở P2 đến P4. `lib/main.dart` chỉ còn bootstrap tối thiểu: khoá hướng dọc, `runApp(const ProviderScope(child: MaterialApp(title: 'Green SM Voice (Demo)', home: SizedBox.shrink())))`. P4a thay bằng `MaterialApp.router`. Xoá `test/widget_test.dart` do scaffold sinh (tham chiếu `MyApp`).
- **Assets:** xoá `assets/models/hey_olasm_int8.onnx` (655 byte, mạng chưa huấn luyện) và để `.gitkeep` rỗng.
- **`pubspec.yaml`:**
  - `environment`: `sdk: ">=3.10.0 <4.0.0"`, `flutter: ">=3.38.0"`. Cập nhật `description`.
  - Thêm: `livekit_client: 2.13.1` và `maplibre_gl: 0.24.1` (ghim đúng bản, không dùng `^`, vì hai gói này đổi API giữa các bản), `geolocator`, `url_launcher`, `go_router`, `audioplayers` (phát âm báo cho mục A4 và P6, plan chưa chỉ định gói phát âm thanh).
  - Giữ: `flutter_riverpod` (2.x), `dio`, `permission_handler`, `uuid` (sinh `device_id`).
  - Bỏ: `riverpod_annotation`, `freezed_annotation`, `json_annotation`, `build_runner`, `freezed`, `json_serializable` (repo không dùng sinh mã), `audio_session` (LiveKit tự quản lý phiên âm thanh), `flutter_animate`, `google_fonts` (tải font lúc chạy, không dùng font chưa có phép).
  - `assets`: `assets/config/`, `assets/models/`, `assets/sounds/`; thêm `assets/brand/`, `assets/fonts/` khi thư mục đó đã tồn tại.
  - Nếu `pub get` xung đột, nâng các gói phụ lên bản mới nhất tương thích. Không hạ `livekit_client`. Nếu `maplibre_gl` 0.24.1 không build được với toolchain đã cài, thử lần lượt các bản 0.25.0 trở lên, chọn bản thấp nhất build được và ghi nguyên văn lỗi vào báo cáo.
  - Commit `pubspec.lock`.
- **Tên app** "Green SM Voice (Demo)": `android:label`, `CFBundleDisplayName`, `MaterialApp.title`. Giữ `name: olasm_mobile` và `applicationId` `com.olasm.mobile`.
- Không thể build iOS thì thêm mục mustdo "Build iOS trên máy Mac" (`flutter build ios --no-codesign` và `pod install`).

**Tiêu chí:** `flutter analyze` sạch, `flutter build apk --debug` thành công. App chạy lên màn trống là đúng ở thời điểm này.

### P2. LiveKit client (mục B2, B3, B4, B7, B8)

**Cấu hình và quyền**

- `lib/core/config/app_config.dart`: `BACKEND_URL` lấy bằng `String.fromEnvironment`. Mặc định `http://10.0.2.2:8000` chỉ khi không phải release; release mà thiếu thì ném `StateError` nói rõ. `GOONG_MAP_TILES_KEY` cũng lấy bằng `--dart-define`.
- `permission_service.dart`: mic và vị trí (`permission_handler`). Pre-connect ném `TrackCreateException` nếu thiếu quyền mic, nên không `start()` khi chưa có quyền. `location_service.dart`: `geolocator`, thời hạn 3 s, giữ vị trí gần nhất (đọc source để chọn đúng API timeout và `getLastKnownPosition`). Không có quyền hoặc không lấy được thì vị trí là null.

**Token**

- `token_prefetcher.dart`, `voice_credentials.dart`: gọi endpoint ở mục 5.1 bằng `dio`, timeout rõ ràng không quá 5 s.
  - `device_id` là UUID v4 sinh mỗi lần mở app (`uuid`), thoả 8 đến 128 ký tự.
  - `trigger_source`: token lấy sẵn gửi `prefetch`. Khi bấm mic mà chưa có token hợp lệ thì lấy tại chỗ với `push_to_talk` (hoặc `wake_word` ở P6). `screen` là `HOME` hoặc `ROUTE` theo màn đang hiển thị. `location` là vị trí mới nhất, null khi không có.
  - Lấy sẵn một token khi vào Home (sau Splash), ngay sau mỗi phiên kết thúc, và khi app quay lại foreground nếu token đang giữ sắp hết hạn. Không dùng timer nền.
  - Mỗi token dùng một lần: `acquire` lấy token ra khỏi bộ nhớ. Token còn dưới 60 s TTL coi như hết hạn. Chỉ một request đang bay; `acquire` trong lúc đang lấy thì chờ request đó.
  - Lỗi phân loại được để UI nói đúng: không kết nối, 503 (máy chủ giọng nói chưa sẵn sàng), 4xx (lỗi hợp đồng, ghi log).
  - Logic hạn token là hàm thuần nhận đồng hồ tiêm vào, để test không cần mạng.
- `voice_token_source.dart`: `implements TokenSourceFixed`, `fetch()` trả `TokenSourceResponse(serverUrl, participantToken, roomName)` từ `acquire`.

**Phiên voice** (`voice_session_controller.dart`, Riverpod `Notifier` viết tay)

- `start(trigger)` theo thứ tự: ghi mốc `mic_tap`; tạo `Room(roomOptions: RoomOptions(enableVisualizer: true))`; đăng ký RPC (bên dưới); tạo `Session.fromFixedTokenSource(VoiceTokenSource(...), options: SessionOptions(room: room, preConnectAudio: true, agentConnectTimeout: Duration(seconds: 8)))`; gắn listener; `await session.start()`; đọc `session.error`. Không `await` thứ gì chậm (token, vị trí) trước `start()`. Bỏ qua lệnh bấm khi đang `starting` hoặc `active`.
- Theo dõi `session` (là `ChangeNotifier`): `session.agent` (`agentState`, `isBuffering`, `isConnected`, `error`), `session.connectionState` (hiện "đang kết nối lại" khi `reconnecting`), `session.messages`, `session.error`. Booking state nhận qua `session.room.createListener()` với `DataReceivedEvent` có `topic == 'greensm.booking_state.v2'`; bỏ qua các topic khác. Hủy listener khi kết thúc phiên.
- Gửi chữ: `session.sendText(text)`. Chạm lựa chọn thứ N: `sendText('chọn số N')`.
- Kết thúc (`end()` hoặc lỗi hoặc phòng bị đóng): `await session.end()`, hủy listener, `await session.dispose()`, `await room.dispose()`, rồi lấy sẵn token cho phiên sau. Khi app sang `paused` mà đang có phiên (trừ trường hợp mở Green SM bên dưới) thì kết thúc phiên.
- Loa ngoài: `AudioManager.instance.setSpeakerOutputPreferred(true)` một lần trước phiên đầu. Giữ echo cancellation, noise suppression, auto gain mặc định của SDK.
- Âm báo (`chime_player.dart`, `audioplayers`): `assets/sounds/wake_ack.wav` khi bắt đầu nghe, `end_session.wav` khi kết thúc nghe. Âm bắt đầu nghe không chặn `start()`. Ghi vào báo cáo để P-H7 kiểm trên máy thật xem mic có thu lại âm báo không.
- Lỗi: controller phơi ra loại lỗi (từ chối quyền mic, token, kết nối, agent timeout hoặc rời phòng) để UI hiện thông báo tiếng Việt ngắn; luôn trả về trạng thái bấm mic lại được; không tự thử lại vô hạn.

**Booking state** (`booking_state.dart`)

- Model bất biến và parser đúng mục 5.2. Parser nghiêm ngặt: sai `schema`, giá trị enum lạ, thiếu `lat`/`lng` khi `resolved` thì bỏ gói đó, ghi log (không log toạ độ), giữ state cũ. Bỏ gói có `revision` nhỏ hơn hoặc bằng gói đang giữ. Reset state và revision khi bắt đầu phiên mới (mỗi phiên là một agent mới).
- `voice_providers.dart`: tách provider phiên voice, booking state, transcript. Widget bản đồ chỉ `watch` route và marker bằng `select`.

**RPC mở Green SM**

- Handler của `greensm.open_confirmation` parse payload mục 5.3, gọi launcher ở P3, trả JSON đúng mục 5.3. Không ném ngoại lệ cho lỗi dự kiến: JSON hỏng hoặc thiếu trường thì trả `INVALID_PAYLOAD`.
- Thành công: trả `{"opened": true}` trước, sau đó mới kết thúc phiên bằng `unawaited`. Tuyệt đối không `await session.end()` bên trong handler, vì phòng đóng trước khi phản hồi được gửi thì agent coi như RPC lỗi. Đánh dấu "đã chuyển sang Green SM"; khi app quay lại foreground (`resumed`) thì về Home sạch (reset state) và hiện snackbar "Đã chuyển sang Green SM để xác nhận chuyến đi."

**Đo phía client**

- `perf_client.dart`: mỗi sự kiện một dòng `debugPrint('[PERF-CLIENT] event=<tên> t_ms=<ms từ mic_tap> room=<room_name hoặc ->')`. Sự kiện: `mic_tap`, `session_started` (`start()` xong), `agent_connected` (lần đầu `agent.isConnected`), `first_speaking` (lần đầu `agentState == speaking`), `deeplink_opened`. Mỗi sự kiện ghi một lần mỗi phiên. Dùng `debugPrint` để `adb logcat` thấy được.

**Test:** parser state v2 với ví dụ mục 5.2 và các trường hợp `disambiguating`, `handing_off`, `abandoned`, `failure`, enum lạ, revision cũ; logic hạn token (đồng hồ tiêm vào, không gọi mạng).

**Tiêu chí:** analyze sạch, test xanh, build thành công. Chưa kiểm được trên máy thật; việc đó thuộc P-H7.

### P3. Deeplink (mục B5, B6)

- `assets/config/greensm_deeplink.json` theo mục 10.4 của plan, file ban đầu: `{"template": "", "coordinate_precision": 6, "service_codes": {"GSM_BIKE": "", "GSM_MINI": "", "GSM_CAR": "", "GSM_PREMIUM": ""}, "fallback_url": ""}`. Người điền sau (P-H2).
- `greensm_deeplink_config.dart` nạp file; `greensm_deeplink_builder.dart` là Dart thuần, gồm model payload của mục 5.3 và `GreenSmDeeplinkBuilder`:
  - Biến hỗ trợ: `{pickup_lat}`, `{pickup_lng}`, `{pickup_name}`, `{pickup_address}`, `{dest_lat}`, `{dest_lng}`, `{dest_name}`, `{dest_address}`, `{service_code}`. Mã hoá giá trị bằng `Uri.encodeQueryComponent`. Toạ độ theo `coordinate_precision` (6 chữ số thập phân).
  - `DEEPLINK_NOT_CONFIGURED`: `template` rỗng (kiểm đầu tiên), template chứa biến ngoài danh sách trên, template không parse được thành `Uri`, hoặc template dùng `{service_code}` mà `service_codes` thiếu hoặc rỗng mã của `ServiceId` hợp lệ. App hiện thông báo rõ ràng.
  - `INVALID_PAYLOAD`: `service_id` ngoài bốn `ServiceId`, hoặc biến mà template dùng nhưng payload thiếu hoặc rỗng, hoặc toạ độ không hữu hạn hay ngoài miền hợp lệ.
  - Trả kết quả thành công kèm `Uri`, hoặc lỗi thuộc hai loại trên.
- `greensm_launcher.dart`: dựng URL, rồi `launchUrl(uri, mode: LaunchMode.externalNonBrowserApplication)`. Không dùng `canLaunchUrl` làm điều kiện: Android 11 trở lên trả false khi thiếu `<queries>`, dẫn tới báo `NOT_INSTALLED` sai dù Green SM đã cài. `launchUrl` trả false thì mở `fallback_url` nếu có và trả `NOT_INSTALLED`; ngoại lệ thì trả `LAUNCH_FAILED`. Đọc source `url_launcher_android` để xác nhận hành vi khi không có ứng dụng xử lý. Ghi mốc `deeplink_opened` khi mở thành công.
- `<queries>` trong AndroidManifest và `LSApplicationQueriesSchemes` trong Info.plist chỉ thêm khi `template` đã có. Lấy scheme từ chính template (scheme `https` thì khai `<intent>` theo scheme và host). Chưa có template thì ghi vào báo cáo rằng hai khai báo này chờ P-H2.
- **Test:** builder với template thử nghiệm đặt ngay trong file test, ghi rõ đó là template test (không phải spec Green SM). Kiểm: mã hoá tiếng Việt, độ chính xác toạ độ, thiếu giá trị cho biến đang dùng, thiếu mã dịch vụ, `service_id` lạ, biến lạ, template rỗng.

**Tiêu chí:** analyze sạch, test xanh, build thành công.

### P4. Design system và màn hình (mục A2, A3, A4)

Chia hai bước. P4a không cần ảnh tham chiếu và luôn được làm. P4b cần ảnh. Hai bước là hai commit riêng.

#### P4a. Khung chức năng

- Thay `main.dart` bằng `MaterialApp.router` (`lib/app/app.dart`, `router.dart`, `go_router`). Route: `/splash` (khởi đầu), thanh tab 4 mục (Trang chủ, Hoạt động, Thanh toán, Tài khoản) với tab Hoạt động, Thanh toán, Tài khoản dựng tĩnh, và màn Route. Tên tab, nhãn lấy từ ảnh ở P4b; trước đó dùng tên tiếng Việt thông thường.
- `lib/app/theme/gsm_tokens.dart` (`GsmColors`, `GsmText`, `GsmRadius`, `GsmSpace`, `GsmShadow`, thời lượng chuyển động) và `gsm_theme.dart` (dựng `ThemeData` từ token), theo kỷ luật token ở mục 4. Mọi widget đọc giá trị từ đây.
- Component mục A2 của plan trong `lib/app/widgets/`: `GsmSearchBar` (có mic), `GsmServiceTile`, `GsmAddressRow` (chấm đón, ghim đến), `GsmBottomSheet` (có snap point), `GsmPrimaryButton`, `GsmServiceOption`, `GsmCandidateTile` (số thứ tự, tên, địa chỉ phụ, khoảng cách), `GsmBottomNav`.
- **S0 Splash:** xin quyền mic rồi vị trí. Từ chối mic thì hiện giải thích kèm nút mở Cài đặt (`openAppSettings`) và không cho bắt đầu phiên. Từ chối vị trí thì vẫn đi tiếp, `location` là null. Bắt đầu tải style bản đồ ngay từ đây theo mục A3 của plan nếu `maplibre_gl` cho phép; nếu không, chỉ dựng bản đồ sớm nhất có thể và ghi vào báo cáo. Xong thì lấy sẵn token và vào Home.
- **S1 Home:** bản đồ có vị trí hiện tại, `GsmSearchBar` có mic, lưới dịch vụ tĩnh với bốn nhãn "Green SM Bike", "Green SM Mini", "Green SM Car", "Green SM Premium" (từ plan, không hiện giá), thanh tab. Bấm mic: rung nhẹ (`HapticFeedback`), mở voice sheet trong 150 ms (số của plan mục A4), `start(pushToTalk)`. Gõ chữ vào ô tìm kiếm rồi gửi: đang có phiên thì `sendText`; chưa có thì bắt đầu phiên như bấm mic rồi gửi chữ ngay khi `agent.isConnected`.
- **S2 Voice sheet:** overlay sống xuyên suốt Home và Route, không phải route riêng, và có nút kết thúc phiên.
  - Trạng thái từ `agent.agentState`: `listening` (vòng sóng), `thinking` (ba chấm), `speaking` (waveform từ audio track của agent, dùng `enableVisualizer`). Khi `isBuffering` vẫn hiện "Đang nghe". `reconnecting` hiện "Đang kết nối lại". `agent.error` hoặc `session.error` hiện thông báo kèm nút thử lại.
  - Caption: lời khách theo bảng "Điểm plan lệch" ở mục 2 (interim xám, final đậm), lời agent theo `AgentTranscript`. Lời agent đã đồng bộ theo audio từ phía agent.
  - Ba chip Điểm đón, Điểm đến, Dịch vụ đổi màu theo `status`: thiếu, cần làm rõ, đã chốt.
  - Hiện `failure.message` khi `failure` khác null.
- **S3 Route:** vào S3 khi booking state có ít nhất một địa điểm `resolved` hoặc `candidates` khác null; về S1 khi `stage` là `abandoned` hoặc state bị reset. Nội dung: bản đồ với marker đón và đến, polyline, thẻ địa chỉ (`GsmAddressRow`), quãng đường và thời gian (hàm định dạng: dưới 1 km hiện mét làm tròn, từ 1 km hiện một chữ số thập phân dùng dấu phẩy, thời gian làm tròn lên phút và từ 60 phút hiện "x giờ y phút"), danh sách lựa chọn đánh số khi mơ hồ (`GsmCandidateTile`, chạm gửi `chọn số N` theo mục 5.4, `distance_km` null thì ẩn), danh sách dịch vụ chỉ hiển thị dịch vụ hiện tại. Không hiện giá. **S4** "Đang mở Green SM..." hiện khi `stage` là `handing_off`.
- **Bản đồ** (`lib/features/map/gsm_map.dart`): `MapLibreMap` với `styleString` là `https://tiles.goong.io/assets/goong_map_web.json?api_key=<key>`, key lấy từ `--dart-define=GOONG_MAP_TILES_KEY` (Map tiles key, khác REST key). Không có key thì hiện thông báo "Chưa cấu hình GOONG_MAP_TILES_KEY" thay vì tải style lỗi. Chấm điểm đón bằng `addCircle`, ghim điểm đến bằng `Symbol` (vẽ icon Material ra ảnh bằng `dart:ui` rồi `addImage` khi chưa có asset thương hiệu), polyline bằng `addLine` với `polyline_decoder.dart` (giải mã encoded polyline precision 5 viết tay), `CameraUpdate.newLatLngBounds` với `bottom` chừa chỗ cho bottom sheet. Cập nhật annotation khi route hoặc marker đổi, không dựng lại bản đồ khi caption đổi. `GsmMap` là ranh giới để test thay bằng widget rỗng (đây là điểm tách hiển thị, không phải dữ liệu giả).
- Chuyển cảnh 200 đến 300 ms theo mục A3 của plan; ghi vào báo cáo là chưa đo cho tới P4b.
- Hiệu năng: `const` widget, `RepaintBoundary` cho animation, bản đồ chỉ `watch` route và marker bằng `select`.
- **Test widget:** mỗi màn render đúng với state ví dụ đặt trong `test/` cho các trạng thái `collecting`, `disambiguating`, `ready_to_confirm`, `failure`; chạm lựa chọn gọi đúng `chọn số N`; bộ giải mã polyline với ví dụ trong tài liệu Google (`_p~iF~ps|U_ulLnnqC_mqNvxq`@` giải ra (38.5, -120.2), (40.7, -120.95), (43.252, -126.453)); hàm định dạng.

**Tiêu chí P4a:** analyze sạch, test xanh, build thành công; app chạy được toàn luồng với giao diện Material 3 mặc định; không có giá trị thiết kế nào ngoài `lib/app/theme/`.

#### P4b. Giao diện khớp Green SM

Chỉ làm khi `design_reference/` đã đủ (12 ảnh, `device.txt`). Chưa đủ thì bỏ qua, ghi "bị chặn bởi P-H1" trong báo cáo; P4a vẫn dùng được cho kiểm thử chức năng.

- Đo ảnh bằng script lấy mẫu pixel đặt ngoài repo (không commit). Quy đổi px sang dp bằng `device.txt`: dp = px × 160 / density.
- Thay mọi giá trị `provisional` trong `gsm_tokens.dart` bằng số đo, mỗi giá trị có comment nguồn gồm tên ảnh và toạ độ pixel. Xoá comment `provisional`.
- Dựng lại component, màn S0 đến S4 và khung tĩnh của ba tab theo ảnh (`01_home` đến `12_account_tab`), chỉ khung và tiêu đề, không điền dữ liệu người dùng. Nhãn và tên tab lấy từ ảnh.
- Thời lượng và đường cong chuyển cảnh: đo từ `flow.mp4` bằng ffmpeg nếu có. Không đo được thì giữ giá trị plan và ghi chưa đo.
- Logo, icon dịch vụ, font: chỉ dùng khi đã có trong `assets/brand/` và `assets/fonts/` theo P-H4 và P-H5; chưa có thì Material Icons và font hệ thống.
- Không khoá golden (chờ P-H6).

**Tiêu chí P4b:** analyze sạch, test xanh, không còn `provisional`, mọi giá trị trong `gsm_tokens.dart` có nguồn.

### P5. Kiểm tra tổng hợp

- Chạy `flutter analyze`, `flutter test`, `flutter build apk --debug`.
- Rà lại bằng grep, mỗi mục phải đạt:
  - không còn import tới file đã xoá, không còn dòng nào nhắc `OlaSM` hay "tổng đài viên" trong chuỗi hiển thị hoặc chuỗi quyền (tên package, namespace, `applicationId` được giữ);
  - không có literal màu, cỡ chữ, bán kính, bóng, khoảng cách ngoài `lib/app/theme/` (sau P4b không còn `provisional`);
  - không có key bản đồ, `participantToken` hay URL backend ghi cứng; không có `print(`;
  - không có TODO không gắn mục mustdo; không dùng API deprecated;
  - mọi file mới nằm trong bản đồ file mục 3.2.
- `git status` chỉ còn file thuộc phạm vi, không có `.gradle/`, `build/`, `.dart_tool/`.

### P6. Wake word phía app (mục 8B)

Làm sau P0 đến P5. Chỉ Android. iOS dùng Swift package `LiveKitWakeWord` là việc "làm sau" của plan (mục 12), không làm ở đây.

**Cấu hình huấn luyện** (không cần toolchain Flutter, làm được dù P0 dừng)

- Xoá `configs/hey_olasm_vietnamese.yaml` và `scripts/train_export_wakeword.py` (đã kiểm: không có test hay mã nào khác tham chiếu).
- Tải `configs/prod_voxcpm.yaml` của livekit-wakeword về đối chiếu từng trường, rồi tạo `configs/green_sm_oi_voxcpm.yaml` đúng schema đó (`WakeWordConfig` trong `src/livekit/wakeword/config.py`):
  - `model_name: green_sm_oi` (file ONNX xuất ra tên `green_sm_oi.onnx`, khớp mục P-H10), `target_phrases: ["Green SM ơi"]` (P-H9 có thể đổi cách viết), `tts_backend: voxcpm`, `n_samples: 50000`, `n_samples_val: 10000`, `model: {model_type: conv_attention, model_size: medium}`.
  - `custom_negative_phrases`: câu âm tính ở mục 8B.3 của plan ("Green", "em ơi", "anh ơi", "xanh ơi", "Grab ơi", "Be ơi", "gọi xe", "xin chào", "ét em").
  - `voxcpm_tts.voice_design_prompts`: 50 đến 100 mô tả phủ giọng người Việt miền Bắc, Trung, Nam, nam và nữ, già và trẻ, nói nhanh và chậm. Viết bằng tiếng Anh theo văn phong mẫu (README của VoxCPM chỉ có ví dụ tiếng Anh, chưa xác nhận mô tả tiếng Việt). Việc nghe thử là P-H9.
  - Các trường còn lại giữ như `prod_voxcpm.yaml`.

**Engine Android** (`android/app/src/main/kotlin/com/olasm/mobile/wakeword/`)

- Tách lõi pipeline `WakeWordPipeline.kt` (Kotlin thuần, không import `android.*`) khỏi `WakeWordEngine.kt` (`AudioRecord`) và `WakeWordPlugin.kt` (method channel, event channel), để test được trên JVM.
- Port đúng pipeline Python (đã đối chiếu mã nguồn 19/10/2026; nếu mã nguồn khác thì theo mã nguồn và ghi báo cáo):
  1. Âm thanh 16 kHz mono int16, đọc từng khung 1.280 mẫu (80 ms), giữ cửa sổ trượt 25 khung (32.000 mẫu, 2 giây). Mỗi khung mới khi cửa sổ đầy thì chạy `predict` trên cả cửa sổ.
  2. int16 chia 32768 thành float32; model `melspectrogram.onnx` nhận `(1, samples)`, ra `(1, 1, frames, 32)`; **hậu xử lý ngoài ONNX: `mel / 10 + 2`**.
  3. Cửa sổ 76 khung mel, bước 8, mỗi cửa sổ chạy `embedding_model.onnx` với đầu vào `(1, 76, 32, 1)`, ra 96 chiều.
  4. Cần ít nhất 16 embedding (khoảng 31.600 mẫu), không đủ thì điểm 0. Lấy 16 embedding cuối thành `(1, 16, 96)` đưa vào classifier (đầu vào `embeddings`, đầu ra `score`).
  5. Ngưỡng mặc định 0,5 và debounce 2 giây (mặc định của thư viện). Phát hiện thì dừng, xoá bộ đệm.
- ONNX Runtime Android: thêm lại dependency, ghim bản ổn định mới nhất lúc làm (Maven Central hiện có 1.31.0) cho cả `onnxruntime-android` lẫn `onnxruntime` dùng trong test JVM, cùng số bản. **Bắt buộc** đặt `mlas.disable_kleidiai = "1"` cho mọi session (`OrtSession.SessionOptions.addConfigEntry`), theo `session.py`: từ ONNX Runtime 1.27 trên ARM64 kernel KleidiAI trả kết quả sai (test chính thức ghi clip positive chỉ ra 0,004), và điện thoại Android là ARM64.
- Model mel và embedding lấy từ package livekit-wakeword (`melspectrogram.onnx`, `embedding_model.onnx`, hàm `get_mel_model_path` và `get_embedding_model_path` trong `livekit.wakeword.resources`), đặt vào `assets/models/`, kèm `NOTICE.txt` ghi nguồn, commit hash và giấy phép Apache-2.0 (gồm nguồn gốc openWakeWord và Google speech_embedding). Model phân loại `assets/models/green_sm_oi.onnx` do người đưa vào sau P-H10. Chỉ đưa file thật từ kết quả huấn luyện, không đưa file giả. Thiếu file thì tắt wake word, ghi log, không crash.

**Kiểm chứng pipeline**

- `olasm_mobile/tool/wakeword_parity.py` dùng `WakeWordModel` của livekit-wakeword (cài bằng `pip install livekit-wakeword`, không cần torch) với model và clip chính thức mà bản Rust và Swift cũng dùng để test: `examples/resources/hey_livekit.onnx`, `tests/fixtures/positive.wav`, `tests/fixtures/negative.wav` (16 kHz, mono, 2,0 giây) của repo livekit-wakeword. Script tải các file này về, chạy `predict`, rồi ghi `android/app/src/test/resources/wakeword/` gồm bản sao ba file đó và `reference_scores.json`. Ngoài hai clip nguyên bản, ghi thêm điểm của chuỗi nối `negative` rồi `positive` cắt cửa sổ 32.000 mẫu tại vài offset là bội số của 1.280, để kiểm cả logic cửa sổ trượt.
- `WakeWordParityTest.kt` chạy `WakeWordPipeline` trên JVM (`testImplementation 'com.microsoft.onnxruntime:onnxruntime:<cùng bản>'`), so điểm với `reference_scores.json`, lệch tối đa 0,01. Đọc model mel và embedding từ `assets/models/`.
- Test JVM chạy trên x86, **không bắt được lỗi kernel ARM64**. Vì vậy luôn thêm mục mustdo "Chạy bộ so điểm wake word trên điện thoại ARM64 thật" (instrumentation test hoặc nút chẩn đoán), kể cả khi test JVM đạt.

**Cầu nối Flutter** (`features/wakeword/wakeword_bridge.dart`)

- Method channel bật và tắt, event channel báo phát hiện. Chỉ nghe khi app ở foreground, đang ở Home, chưa có phiên. Phát hiện thì dừng engine, nhả `AudioRecord`, phát `assets/sounds/wake_ack.wav`, đợi phát xong rồi gọi `start(wakeWord)` (token lấy sẵn nếu có, không thì lấy tại chỗ với `trigger_source` là `wake_word`). Người dùng chờ âm báo rồi mới nói. Sau khi phiên kết thúc và về Home thì bật lại engine.
- Bật bằng `--dart-define=WAKEWORD_ENABLED=true`, mặc định tắt. Ngưỡng truyền bằng `--dart-define=WAKEWORD_THRESHOLD=<số>`, mặc định 0,5 theo thư viện; ghi cách dùng hai cờ này vào mục mustdo mới về ARM64. Chỉ bật khi cổng nghiệm thu ở mục 8B.5 đạt, việc này đã có trong mustdo (P-H11).

**Tiêu chí:** cấu hình đúng schema, `analyze`, `test`, `build apk --debug` và test Kotlin (`./gradlew testDebugUnitTest` trong `android/`, trên Windows là `gradlew.bat`; wrapper có sau lần build đầu) đạt; phần cần người đã có mục mustdo.

---

## 7. Mẫu một mục trong `mustdoPhuong.md`

```markdown
## P-H<số>. <Tên việc>

- **Việc làm:** ...
- **Tại sao AI không làm được:** ...
- **Ở đâu:** file, dịch vụ, thiết bị
- **Thao tác:** từng bước, kèm lệnh chính xác
- **Kết quả mong đợi:** ...
- **Kiểm chứng:** lệnh hoặc cách xác nhận đã xong
- **Đang chặn:** phase hoặc việc code đang chờ mục này
```

Đánh số tiếp theo số lớn nhất đang có (lúc viết prompt là P-H12, nên mục mới bắt đầu từ P-H13; đọc lại file để chắc). Không sửa nội dung mục do người viết.

---

## 8. Định nghĩa hoàn thành

- P0 đến P5 đạt tiêu chí, P6 làm hết phần không cần người. P4b có thể còn bị chặn bởi P-H1; mọi phần bị chặn có mục mustdo cụ thể.
- `flutter analyze` sạch, `flutter test` xanh, `flutter build apk --debug` thành công (kết quả thật, trên toolchain đã qua cổng P0).
- Code mới không có gateway giả, dữ liệu bịa, giá trị thiết kế đoán, template deeplink tự đặt.
- Mọi file mới nằm trong bản đồ mục 3.2, không có file `.md` mới ngoài `mustdoPhuong.md`.

## 9. Báo cáo cuối phiên

In ra ngắn gọn:

1. Bảng phase với trạng thái: xong, bị chặn bởi mục mustdo nào, hoặc chưa làm.
2. Các lệnh kiểm tra đã chạy và kết quả thật (kể cả lệnh lỗi). Nói rõ phần nào chưa kiểm được vì không có thiết bị hoặc không có máy Mac.
3. Mục mustdo mới thêm.
4. Các điểm đã làm khác plan theo bảng ở mục 2, và quyết định đã chốt (bản `maplibre_gl` cuối cùng, bản ONNX Runtime, các chỗ tự quyết như điều kiện vào màn Route).
