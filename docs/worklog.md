# Worklog — Team OlaSM (OlaSM Voice AI)

> Ghi lại công việc đã được implement theo ngày dựa trên commit, branch và PR. Các merge commit được gộp vào task/kết quả tương ứng để tránh lặp.
>
> Cột **Time** chỉ ghi thời lượng khi có dữ liệu rõ ràng. Git history không ghi số giờ làm việc nên các mục chưa có dữ liệu được đánh dấu `—`.
>
> **Trạng thái tài liệu:** APPROVED · Cập nhật đến **2026-08-31**.

---

## 2026-08-02

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @NamKhanh2128 | Khởi tạo baseline sản phẩm OlaSM Voice AI và bộ tài liệu G1 | ✅ Done | `docs/PRODUCT_BRIEF.md`, `docs/PRD_OlaSM_Voice.md`, `docs/architecture_diagram.md` | — |

**Tổng kết ngày:** Định hình mục tiêu sản phẩm, kiến trúc ban đầu và phạm vi trợ lý đặt xe bằng giọng nói.

---

## 2026-08-07

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @NamKhanh2128 | Hợp nhất baseline G1 vào repository | ✅ Done | [PR #1](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/1) | — |
| @NamKhanh2128 | Chuẩn hóa thư mục tài liệu đặc tả | ✅ Done | `specification_documents/` | — |
| @PhucHung | Hoàn thiện PRD, architecture diagram và interface design cho OlaSM Voice AI | ✅ Done | `docs/PRD_OlaSM_Voice.md`, `docs/architecture_diagram.md`, `docs/FEATURE_USER_STORIES.md` | — |

**Tổng kết ngày:** Product scope, yêu cầu MVP, kiến trúc và luồng giao diện được ghi thành tài liệu làm nền cho các branch implementation.

---

## 2026-08-08

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @DanielK345 | Khởi tạo backend FastAPI, API routes, controllers, integrations và health checks | ✅ Done | `src/api/`, `src/controllers/`, `src/integrations/`, `src/main.py` | — |
| @DanielK345 | Bổ sung README và xử lý xung đột cấu trúc source | ✅ Done | `src/backend/README.md`, commit `34a4c8` | — |
| @PivePipiopia | Tạo walking skeleton cho trợ lý ride-hailing | ✅ Done | `src/agents/`, commit `bc62a20` | — |

**Tổng kết ngày:** Có backend skeleton và agent skeleton để bắt đầu nối các workflow đặt xe.

---

## 2026-08-09

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Xây dựng Core Agent intent routing và graph điều phối | ✅ Done | [PR #4](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/4), `src/agents/router.py`, `src/agents/graph.py` | — |

**Tổng kết ngày:** Agent có thể phân loại intent và điều hướng request đến booking, FAQ, trip status hoặc handoff.

---

## 2026-08-10

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Implement human handoff policy và workflow chuyển sang nhân viên | ✅ Done | [PR #5](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/5), `src/agents/workflows/handoff.py` | — |
| @PhucHung | Xây dựng customer UI và operator UI bằng React/TypeScript | ✅ Done | `frontend/src/components/CustomerUI.tsx`, `frontend/src/components/OperatorUI.tsx` | — |

**Tổng kết ngày:** Hoàn thành nhánh handoff đầu tiên và giao diện cơ bản cho khách hàng/operator.

---

## 2026-08-11

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Implement conversation state, memory và state store theo session | ✅ Done | `src/agents/state.py`, `src/agents/state_store.py` | — |
| @PivePipiopia | Implement tool calling lifecycle, call ID và typed tool schemas | ✅ Done | `src/agents/tools/lifecycle.py`, `src/agents/tools/call_id.py` | — |
| @PivePipiopia | Implement booking workflow nhiều bước và booking models | ✅ Done | `src/agents/workflows/booking.py`, `src/agents/workflows/booking_models.py` | — |
| @PivePipiopia | Ghi lại kiến trúc Core Agent và roadmap | ✅ Done | `src/agents/README.md`, commit `ca24b2f` | — |
| @PivePipiopia | Hợp nhất Core Agent routing và human handoff vào branch agentic-ai | ✅ Done | Commit `3acb0ea`, `5dbebca` | — |

**Tổng kết ngày:** Core Agent có state/memory, lifecycle gọi tool, booking flow và handoff flow có thể kiểm thử độc lập.

---

## 2026-08-12

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Implement trip lookup workflow và truy vấn trạng thái chuyến | ✅ Done | `src/agents/workflows/trip_lookup.py` | — |
| @PivePipiopia | Implement grounded FAQ/RAG và answer generator | ✅ Done | `src/agents/workflows/faq.py`, `src/agents/rag/answer_generator.py` | — |
| @PivePipiopia | Thêm guardrails, policy và offline evaluator cho Agent | ✅ Done | `src/agents/guardrails.py`, `src/agents/eval/` | — |
| @PivePipiopia | Compose Agent turn bằng LangGraph | ✅ Done | `src/agents/graph.py`, commit `0acc886` | — |
| @PivePipiopia | Tích hợp OpenAI language understanding, rules và provider factory | ✅ Done | [PR #9](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/9), `src/agents/understanding/` | — |
| @PivePipiopia | Bổ sung end-to-end scenarios cho Core Agent | ✅ Done | `tests/test_agents/` | — |
| @DanielK345 | Nối frontend với session/user ID, sửa auth/logout và chatbox | ✅ Done | `src/frontend/`, các commit `2569049`, `c8cc423`, `0980234` | — |
| @DanielK345 | Bổ sung success panel, session creation/termination và prompt/logging | ✅ Done | Commit `f16287f`, `abb930d` | — |

**Tổng kết ngày:** Core Agent hoàn chỉnh các nhánh booking, FAQ, trip lookup, handoff; frontend đã gọi đúng session và user context.

---

## 2026-08-13

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @NamKhanh2128 | Tích hợp Core Agentic AI và voice AI vào application | ✅ Done | `src/agents/`, `src/voice/`, commit `878c0fa`, `ede7df1` | — |
| @NamKhanh2128 | Tích hợp Supabase layer, auth hardening và sửa conflict voice boot | ✅ Done | `src/backend/`, migrations, commit `c8e1a4b` | — |
| @NamKhanh2128 | Hoàn thiện backend booking history, trip tracking và settings | ✅ Done | `src/backend/services/`, commit `bc4afe3` | — |
| @NamKhanh2128 | Nối các orphaned pages với dữ liệu backend và sửa screen transitions | ✅ Done | Commit `a675f89`, `f66aaf1` | — |
| @NamKhanh2128 | Hoàn thiện taskbar, conversation history, dark theme và sidebar | ✅ Done | `src/frontend/src/features/`, commit `3fe848d`, `14a26be`, `ff5dd98` | — |
| @PivePipiopia | Định nghĩa conversation history contract và turn history lifecycle | ✅ Done | Commit `c698899`, `47ebcb2` | — |
| @PivePipiopia | Implement contextual understanding, conversation repair và interruption | ✅ Done | Commit `d194167`, `58c9177`, `d15441c` | — |
| @NamKhanh2128 | Hợp nhất branch speech model và ghi nhận implementation report | ✅ Done | Commit `86fcfcb`, `6007bd9` | — |

**Tổng kết ngày:** Agentic AI, voice runtime ban đầu, backend persistence và UI đã được nối vào cùng application flow.

---

## 2026-08-14

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Thêm production guardrails, completion/readiness evaluation và state/tool contracts | ✅ Done | Commit `558ee7c`, `16ae53c`, `e5eabd7` | — |
| @PivePipiopia | Xử lý late booking requirement changes và cập nhật completion status | ✅ Done | Commit `2665f31`, `36f61e2` | — |
| @NamKhanh2128 | Import Core Agent + RAG vào backend integration | ✅ Done | Commit `454b1d6`, `bf8830f`, `915a762` | — |
| @NamKhanh2128 | Đồng bộ vehicle taxonomy của frontend với Core Agent | ✅ Done | Commit `55a467d` | — |
| @DanielK345 | Sửa voice service sau khi hợp nhất các branch | ✅ Done | Commit `d2a5044` | — |

**Tổng kết ngày:** Core Agent được kiểm soát bằng guardrails và contract; backend/frontend dùng cùng mô hình workflow và vehicle taxonomy.

---

## 2026-08-15

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Refactor Agent sang model-driven tool architecture | ✅ Done | Commit `86cfe2e`, `src/agents/` | — |
| @NamKhanh2128 | Chuyển Voice AI từ full page sang floating button/popup | ✅ Done | `VoiceAIButton.tsx`, `VoiceAssistantPopup.tsx` | — |
| @NamKhanh2128 | Implement hands-free voice call và call-only interaction | ✅ Done | `VoiceCallPanel.tsx`, commit `accc4f8`, `b1ac9af` | — |
| @NamKhanh2128 | Thêm TOTP 2FA enforcement và tracking marker simulation | ✅ Done | Commit `074b9e4` | — |
| @DanielK345 | Thêm Gemini rewrite, sửa ASR hallucination và cấu hình voice model | ✅ Done | Commit `a823a58`, `9a84bb5`, `8f79336` | — |
| @DanielK345 | Thêm reset button và sửa các lỗi UI/voice test | ✅ Done | Commit `8718c6e` | — |

**Tổng kết ngày:** Trải nghiệm voice được chuyển thành popup gọi trực tiếp, có hands-free mode, model-driven agent và các biện pháp sửa ASR.

---

## 2026-08-16

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @NamKhanh2128 | Tích hợp versioned demo pricing catalog | ✅ Done | `data/pricing/`, commit `f7e6bd6` | — |
| @NamKhanh2128 | Tích hợp approved policy catalog và policy source | ✅ Done | `data/policies/`, commit `024982d` | — |
| @NamKhanh2128 | Implement durable persistence, quote integrity và maps contract | ✅ Done | Migrations, repositories, commit `0e9506b` | — |
| @DanielK345 | Sửa migration, registration/auth, popup UI và voice fallback | ✅ Done | Commit `8925189`, `adf385d`, `224c2fe`, `8ea654f` | — |
| @DanielK345 | Sửa gazetteer và transcript rewrite cho địa danh Việt Nam | ✅ Done | Commit `14379f9`, `0c53535`, `94ce55a` | — |
| @NamKhanh2128 | Hợp nhất backend-data và voice-ai để dùng chung backend/voice flow | ✅ Done | Merge commits `f72aca5`, `81ad534` | — |

**Tổng kết ngày:** Business truth, pricing/policy versioning, maps, persistence và voice rewrite được nối vào booking flow.

---

## 2026-08-17

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @DanielK345 | Tạo bộ evaluation cases cho agent workflow | ✅ Done | `eval_cases/`, commit `72a67e1` | — |
| @DanielK345 | Cập nhật README và hoàn thiện gazetteer/transcript rewrite | ✅ Done | `README.md`, commit `d7d5e1f`, `9762e91` | — |

**Tổng kết ngày:** Có bộ case tái chạy được cho happy path, sửa pickup/destination/vehicle, out-of-scope và handoff.

---

## 2026-08-18

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Xây dựng LiveKit-native voice agent baseline | ✅ Done | `src/voice_agent/`, `src/backend/api/routes/livekit.py`, `src/frontend/src/features/livekit/` | — |
| @PivePipiopia | Tạo LiveKit token/control plane, AgentServer worker, AgentSession và booking tools | ✅ Done | `src/voice_agent/server.py`, `src/voice_agent/tasks/booking.py`, `src/voice_agent/tools/` | — |
| @PivePipiopia | Thêm state persistence, LiveKit migration và room smoke runner | ✅ Done | Migrations, `scripts/livekit_room_smoke.py` | — |
| @PivePipiopia | Viết hướng dẫn setup LiveKit cho team | ✅ Done | `docs/LIVEKIT_TEAM_SETUP.md` | — |

**Tổng kết ngày:** Voice runtime có transport LiveKit-native, worker riêng, session state và đường chạy smoke test.

---

## 2026-08-19

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Chuẩn hóa LiveKit environment example | ✅ Done | `.env.example`, commit `807586a` | — |
| @NamKhanh2128 | Cập nhật OSRM/map configuration và deployment | ✅ Done | Commit `1d35c38`, `04d225b` | — |
| @DanielK345 | Sửa database migration, VAD và LiveKit LLM rewrite | ✅ Done | Commit `ce5db12`, `0e70589` | — |

**Tổng kết ngày:** Hoàn thiện cấu hình provider, maps và các điểm tích hợp cần thiết để chạy LiveKit voice ở môi trường team.

---

## 2026-08-20

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Hardening LiveKit voice baseline, handoff và session recovery | ✅ Done | Commit `80c1d1a`, `src/voice_agent/`, `tests/test_voice_agent/` | — |
| @PivePipiopia | Viết coding-agent handoff, Phase 4 evaluation plan và latency plan | ✅ Done | `docs/evaluation.md`, `docs/performance/latency-remediation-plan.md` | — |
| @DanielK345 | Warm worker và chuẩn bị call trước khi người dùng bắt đầu voice session | ✅ Done | `src/frontend/src/features/livekit/prepareCall.ts`, commit `e017c0c` | — |
| @DanielK345 | Thu hồi access khi session kết thúc | ✅ Done | Commit `f034646` | — |
| @DanielK345 | Hiển thị transcript rewrite progress và trạng thái provider trên UI | ✅ Done | `src/voice_agent/state_sync.py`, `LiveKitVoiceSession.tsx`, commit `992daf2` | — |
| @DanielK345 | Thêm observability, timeout cho rewrite/publish và fail-open về raw transcript | ✅ Done | `src/voice_agent/observability.py`, commit `515ed71`, `0ff1f1e` | — |
| @DanielK345 | Ổn định transcript rewrite khi interruption, booking context và ASR confusion | ✅ Done | Commit `e8381b8`, `b646e60`, `823130f`, `ea15675`, `4585931` | — |
| @DanielK345 | Sửa UI bubble chat và các lỗi voice/backend trong quá trình merge | ✅ Done | Commit `31bb377`, `1ce3269`, `ca04b61` | — |

**Tổng kết ngày:** LiveKit runtime được harden cho startup, reconnect, handoff, transcript progress, timeout, observability và interruption.

---

## 2026-08-22

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Cập nhật agentic AI implementation và chuyển runtime chính sang LiveKit flow | ✅ Done | [PR #10](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/10), commit `83b685c` | — |
| @PivePipiopia | Chuẩn hóa developer setup, environment profile và cách chạy ba process | ✅ Done | `docs/LIVEKIT_TEAM_SETUP.md`, `README.md` | — |
| @NamKhanh2128 | Hợp nhất agentic-ai với voice-ai và xử lý merge conflict | ✅ Done | Commit `524949f`, `bdcdb9b` | — |
| @NamKhanh2128 | Sửa Docker runtime permission khi chạy bằng appuser | ✅ Done | Commit `8292db4` | — |

**Tổng kết ngày:** Các nhánh agentic-ai và voice-ai được đồng bộ, legacy voice path được thu hẹp khỏi happy path và setup được chuẩn hóa cho teammate.

---

## 2026-08-23

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @NamKhanh2128 | Tạo Docker packaging scripts cho Linux và PowerShell | ✅ Done | `scripts/deploy_to_ghcr.sh`, `scripts/deploy_to_ghcr.ps1` | — |
| @NamKhanh2128 | Tạo GitHub Actions workflow publish image lên GHCR | ✅ Done | `.github/workflows/docker-publish.yml` | — |
| @NamKhanh2128 | Sửa image tag, branch trigger và PowerShell variable interpolation | ✅ Done | Commit `889c70e`, `3d63048` | — |

**Tổng kết ngày:** Có quy trình build/publish container và CI packaging cho deployment voice runtime.

---

## 2026-08-24

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Hoàn thiện LiveKit handoff, room lifecycle, state restore/publish và structured events | ✅ Done | PR [#10](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/10), commit `270e849` | — |
| @PivePipiopia | Refactor model factory cho STT/LLM/TTS và giảm provider logic trong server | ✅ Done | Commit `5fbd041`, `src/voice_agent/model_factory.py` | — |
| @PivePipiopia | Thêm xác nhận bằng nút bấm khi yêu cầu hủy chuyến | ✅ Done | Commit `2030171`, `LiveKitVoiceSession.tsx`, `session_data.py` | — |
| @PivePipiopia | Điều chỉnh ASR timeout trong cấu hình mẫu | ✅ Done | Commit `3b1fa9d`, `.env.example` | — |
| @PivePipiopia | Merge PR #10 vào develop | ✅ Done | [PR #10](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/pull/10) | — |

**Tổng kết ngày:** PR #10 hoàn tất việc hợp nhất Agentic AI, backend data, frontend voice và LiveKit-native runtime; các commit sau đó tiếp tục hoàn thiện model factory, hủy chuyến và ASR timeout.

---

## Tổng kết implementation

| Thành phần | Kết quả |
|------------|---------|
| Product/UI | Có customer assistant, operator UI, booking progress, confirmation, history, popup và hands-free voice call. |
| Core Agent | Có intent routing, LangGraph turn, typed state, memory, tool lifecycle, booking, FAQ/RAG, trip lookup và guardrails. |
| Booking | Có thu thập địa điểm/vehicle, quote, explicit confirmation, correction flow, quote invalidation, idempotent confirmation và cancel confirmation. |
| Backend data | Có auth, TOTP, session/booking/trip/handoff repositories, migrations, maps, pricing/policy catalog và quote integrity. |
| Voice | Có ASR, VAD, transcript normalization/rewrite, TTS/fallback, provider timeout handling và emergency safety gate trước LLM. |
| LiveKit | Có Room/WebRTC, AgentServer, AgentSession, state sync/restore, reconnect handling, text fallback và operator takeover. |
| Evaluation | Có workflow eval, LiveKit smoke runner, structured JSONL evidence, latency/usage observability, release runbook và evidence cho issue #34. |
| Deployment | Có developer setup, Docker image, GHCR scripts, GitHub Actions publish workflow, staging HTTPS/Caddy và staging deploy qua AWS SSM. |

## Trạng thái kiểm chứng và việc tiếp tục

- PR #1, #4, #5, #9 và #10 đã được merge theo lịch sử GitHub.
- PR #6 và #7 vẫn được GitHub ghi nhận là các PR frontend mở; phần UI tương ứng đã được các branch khác tiếp tục hợp nhất và phát triển.
- Workflow evaluation, LiveKit product evaluation và CI vẫn còn các lỗi cần xử lý; chưa nên coi hệ thống là production-ready.
- Việc tiếp theo là sửa regression trong booking/evaluation, chạy lại backend/frontend checks, hoàn tất browser/device/reconnect/provider-failure tests và kiểm chứng các tích hợp production.


## 2026-08-27

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Team | Hardening branch agentic-ai theo review: sửa catalog path, correction flow, provider/docs drift và CI evidence | ✅ Done | `459 passed, 3 skipped`; deterministic eval 6/6; `docs/evaluation.md` | — |

**Tổng kết ngày:** Source hiện tại có thể rebuild/test từ branch, các giới hạn external và release gates được ghi rõ thay vì để reviewer suy đoán.

---

## 2026-08-28

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Chuyển CI checks sang cohort3 self-hosted runner | ✅ Done | Commit `7e96692`, `.github/workflows/ci.yml` | — |
| @PivePipiopia | Refactor ranh giới supervision của booking task để tách orchestration khỏi agent/server | ✅ Done | Commit `fdeb950`, `src/voice_agent/tasks/booking.py`, `tests/test_voice_agent/test_booking_task.py` | — |
| @PivePipiopia | Bổ sung tài liệu tiếng Việt cho các LiveKit booking tools và luồng xử lý booking | ✅ Done | Commit `a0f88bf`, `src/voice_agent/agent.py`, `src/voice_agent/tasks/booking.py` | — |

**Tổng kết ngày:** Booking task và LiveKit tool flow được làm rõ boundary, dễ kiểm thử và dễ bàn giao hơn.

---

## 2026-08-29

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Sửa các lỗi review ở persistence, booking service, place search, LiveKit state và frontend API; bổ sung performance regression tests | ✅ Done | Commit `79bd445`, `tests/test_backend/test_booking_service_performance.py`, `tests/test_voice_agent/` | — |
| @PivePipiopia | Làm mới activity history sau khi booking hoàn tất | ✅ Done | Commit `e0dfea6`, `src/frontend/src/app/events.ts`, `ActivityList.tsx` | — |
| @PivePipiopia | Cho policy/FAQ xử lý an toàn khi query không xác định hoặc không có câu trả lời phù hợp | ✅ Done | Commit `c9fbda0`, `src/agents/capabilities/faq.py`, `src/backend/services/knowledge_service.py` | — |
| @PivePipiopia | Chuẩn hóa deploy staging với HTTPS Caddy và AWS OIDC/SSM | ✅ Done | Commits `099fb11`, `be92200`, `.github/workflows/deploy-staging.yml`, `Caddyfile` | — |
| @NamKhanh2128 | Cấu hình GHCR token cho staging deploy | ✅ Done | Commit `f4f9de1`, `.github/workflows/deploy-staging.yml` | — |
| @PivePipiopia | Mount Google service-account credentials vào backend và voice worker staging | ✅ Done | Commit `8baac2a`, `docker-compose.staging.yml`, `scripts/deploy-staging.sh` | — |

**Tổng kết ngày:** Booking/persistence và policy được harden; staging có pipeline deploy, HTTPS, credential mount và kiểm tra CI phù hợp với hạ tầng team.

---

## 2026-08-30

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Làm cho thao tác xác nhận booking lặp lại có tính idempotent, không tạo duplicate booking khi retry | ✅ Done | Commit `bdcbd00`, `src/voice_agent/tasks/booking.py`, `tests/test_voice_agent/test_booking_task.py` | — |
| @PivePipiopia | Thêm emergency safety gate nhận diện tín hiệu nguy hiểm trước khi gọi LLM và chuyển ngay tới hàng đợi operator khẩn cấp | ✅ Done | Commit `75a2c79`, `data/safety/emergency_policy.yaml`, `src/voice_agent/safety.py`, `src/voice_agent/tools/handoffs.py`, `tests/test_voice_agent/test_emergency_safety.py` | — |

**Tổng kết ngày:** Retry booking được bảo vệ khỏi duplicate side effect; các tín hiệu an toàn nghiêm trọng được ưu tiên xử lý trước hội thoại LLM.

---

## 2026-08-31

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| @PivePipiopia | Kiểm chứng và ghi lại cách reproduce issue thay đổi đồng thời pickup, destination và vehicle sau khi đã có quote | ✅ Done | Commit `613b94d`, `docs/verification/issue-34-research.md` | — |
| @PivePipiopia | Bổ sung danh sách canonical mock locations và hướng dẫn test staging cho issue #34 | ✅ Done | `docs/verification/issue-34-research.md` | — |

**Tổng kết ngày:** Issue #34 đã có code-path review, test deterministic và hướng dẫn staging; flow thay đổi ba trường có thể tạo quote mới khi dùng mock location hợp lệ.
