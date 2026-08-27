# Journal — Team P-160 (AloSM Voice AI)

> Nhật ký kỹ thuật thực tế của project, tổng hợp từ commit, branch, PR, test và evaluation artifact. Worklog ghi “ai làm gì”; journal ghi “vì sao làm, kết quả, vấn đề và bài học”.

---

## 2026-08-02 — Khởi tạo sản phẩm

### Người tham gia

- @NamKhanh2128 — branch G1, commit f513b94.

### Bối cảnh và quyết định

Team bắt đầu bằng việc chốt bài toán AloSM Voice AI: trợ lý đặt xe có thể nhận yêu cầu bằng text hoặc voice. Product brief, PRD và architecture được dùng làm nền để tách product scope khỏi implementation.

### Kết quả

- Xác định flow đặt xe, customer/operator và các capability chính của MVP.
- Tạo các tài liệu nền ALOSM_Brief.md, ALOSM_PRD.md và ARCHITECTURE.md.

### Kiểm chứng và vấn đề

Đây là product/design baseline, chưa phải runtime implementation. Các API, database và agent workflow vẫn cần được xây dựng.

### Bước tiếp theo

Tạo backend skeleton, frontend MVP và Core Agent routing.

---

## 2026-08-07 — Chuẩn hóa đặc tả

### Người tham gia

- @NamKhanh2128 — hợp nhất G1 qua PR #1.
- @PhucHung — commit bc19d70.

### Bối cảnh và quyết định

Product documents được sắp xếp lại thành khu vực đặc tả riêng. Đồng thời team cập nhật PRD, architecture diagram và interface design để các branch code dùng cùng vocabulary.

### Kết quả

- PR #1 được merge vào develop.
- Hoàn thiện docs/PRD_AloSM_Voice.md, docs/architecture_diagram.md và docs/architecture_diagram.md.

### Kiểm chứng và vấn đề

Các tài liệu đã thống nhất phạm vi, nhưng chưa thể chứng minh behavior vì backend và frontend còn là skeleton.

### Bước tiếp theo

Khởi tạo API backend và agent routing.

---

## 2026-08-08 — Backend và agent skeleton

### Người tham gia

- @DanielK345 — backend skeleton và README.
- @PivePipiopia — commit bc62a20.

### Bối cảnh và quyết định

Team chọn FastAPI làm backend và tách agent, controller, integration thành các boundary riêng. Agent trước mắt chỉ cần walking skeleton để các workflow có seam rõ ràng.

### Kết quả

- Tạo API routes, controllers, integrations, health checks và entrypoint backend.
- Tạo walking skeleton cho trợ lý ride-hailing.
- Bổ sung README backend và xử lý xung đột path ban đầu.

### Kiểm chứng và vấn đề

Skeleton cho phép bắt đầu phát triển song song nhưng chưa có state, tool lifecycle hay business persistence.

### Bước tiếp theo

Implement intent routing, handoff và state model.

---

## 2026-08-09 — Intent routing

### Người tham gia

- @PivePipiopia — commit 2f5a385, PR #4.

### Bối cảnh và quyết định

Thay vì để một handler xử lý mọi yêu cầu, team tách intent routing và graph điều phối. Cách này cho phép booking, FAQ, trip status và handoff phát triển độc lập.

### Kết quả

- Agent có router và graph cho các nhánh nghiệp vụ.
- Bổ sung test cho agent, graph và router.
- PR #4 được merge vào branch agentic-ai.

### Kiểm chứng và vấn đề

Routing đã có contract test, nhưng các workflow phía sau mới ở mức ban đầu.

### Bước tiếp theo

Thêm handoff workflow và giao diện operator.

---

## 2026-08-10 — Human handoff và UI đầu tiên

### Người tham gia

- @PivePipiopia — commit 447b920, PR #5.
- @PhucHung — customer/operator UI, commit 13b61d1.

### Bối cảnh và quyết định

Handoff được thiết kế như một workflow có policy thay vì chỉ trả một câu xin lỗi. Giao diện customer và operator được xây song song để kiểm tra cả hai đầu của luồng hỗ trợ.

### Kết quả

- Có handoff policy, reason/priority và workflow chuyển case sang nhân viên.
- Có customer UI, operator UI, API client và WebSocket integration ban đầu.
- PR #5 được merge vào agentic-ai.

### Kiểm chứng và vấn đề

Handoff lúc này chưa có durable record, operator authentication hoàn chỉnh hay LiveKit room takeover.

### Bước tiếp theo

Thêm conversation state, tool lifecycle và booking workflow.

---

## 2026-08-11 — State, tools và booking

### Người tham gia

- @PivePipiopia — commits 19f4240, 7af825c, 8cd3a39, 3acb0ea và 5dbebca.

### Bối cảnh và quyết định

Booking nhiều bước cần state lâu sống hơn một turn. Team đưa conversation memory, state store, call ID và typed tool schemas vào trước khi mở rộng workflow.

### Kết quả

- Agent giữ được state và memory theo session.
- Tool lifecycle theo dõi được từng tool call.
- Booking workflow thu thập pickup, destination, vehicle, confirmation và tạo chuyến.
- Core routing và handoff được hợp nhất vào agentic-ai.

### Kiểm chứng và vấn đề

Booking có test workflow riêng, nhưng dữ liệu backend lúc này chưa phải durable business truth.

### Bước tiếp theo

Thêm trip lookup, grounded FAQ, guardrails và model-based understanding.

---

## 2026-08-12 — Core Agent hoàn chỉnh các workflow chính

### Người tham gia

- @PivePipiopia — commits e4577f1, 9171e0f, 58dd42a, 0acc886, 78ff4bc và 9476b56.
- @DanielK345 — session/user wiring, auth, chatbox và success flow.

### Bối cảnh và quyết định

Team chọn LangGraph để compose một Agent turn có cấu trúc. FAQ phải grounded vào knowledge/policy, còn trip lookup và booking phải đi qua workflow typed. OpenAI language understanding được đặt sau factory để vẫn giữ khả năng dùng fallback/test double.

### Kết quả

- Có trip lookup, grounded FAQ/RAG, guardrails và offline evaluator.
- Agent turn chạy qua LangGraph.
- Có OpenAI understanding service, rules, models và factory.
- Frontend truyền đúng user/session context; có session creation/termination, logout handling và success panel.
- PR #9 được dùng để tích hợp OpenAI language understanding vào backend-data.

### Kiểm chứng và vấn đề

Đã có test agent, integration scenario, guardrails, FAQ, trip lookup và understanding. Provider thật vẫn phụ thuộc environment và credential.

### Bước tiếp theo

Hợp nhất Core Agent với voice runtime và backend data.

---

## 2026-08-13 — Hợp nhất Agentic AI, voice và backend

### Người tham gia

- @NamKhanh2128 — commits 878c0fa, ede7df1, c8e1a4b, bc4afe3 và a675f89.
- @PivePipiopia — commits c698899, 47ebcb2, d194167, 58c9177 và d15441c.

### Bối cảnh và quyết định

Team bắt đầu nối các nhánh độc lập vào application thật. State/history được giữ ở contract của Agent; voice runtime ban đầu vẫn dùng gateway riêng để thử ASR, VAD, TTS và transcript rewrite.

### Kết quả

- Core Agentic AI và voice AI được tích hợp vào application.
- Backend có Supabase layer, auth hardening, booking history, trip tracking và settings.
- Các orphaned pages được nối với dữ liệu thật thay vì chỉ hiển thị mock.
- Conversation history, contextual understanding, repair và interruption được bổ sung.
- Frontend có taskbar, dark theme, sidebar và assistant history.

### Kiểm chứng và vấn đề

Các branch đã chạy được những flow riêng, nhưng nhiều boundary còn đang thay đổi do merge giữa voice, backend-data và agentic-ai.

### Bước tiếp theo

Chuẩn hóa state/tool contract và chuyển Agent sang model-driven architecture.

---

## 2026-08-14 — Guardrails và contract integration

### Người tham gia

- @PivePipiopia — commits 558ee7c, 2665f31, 16ae53c và e5eabd7.
- @NamKhanh2128 — commits 454b1d6, bf8830f và 55a467d.
- @DanielK345 — commit d2a5044.

### Bối cảnh và quyết định

Khi booking có nhiều thay đổi giữa chừng, Agent cần phân biệt state change hợp lệ với tool result cũ. Team bổ sung completion/readiness gate, state contract và tool-result gate trước khi cho flow kết thúc.

### Kết quả

- Có production guardrails và readiness evaluation.
- Xử lý late booking requirement change.
- Backend dùng Core Agent + RAG contract mới.
- Frontend đồng bộ vehicle taxonomy với Agent.
- Sửa voice service sau các lần hợp nhất branch.

### Kiểm chứng và vấn đề

Regression tests được bổ sung cho state và tool arguments. Các lỗi do khác biệt giữa voice contract cũ và Agent contract mới vẫn là rủi ro cần theo dõi.

### Bước tiếp theo

Refactor Agent model-driven và cải thiện voice UX.

---

## 2026-08-15 — Model-driven Agent và voice popup

### Người tham gia

- @PivePipiopia — commit 86cfe2e.
- @NamKhanh2128 — commits 8519dd5, accc4f8, b1ac9af và 074b9e4.
- @DanielK345 — commits a823a58, 9a84bb5, 8f79336 và 8718c6e.

### Bối cảnh và quyết định

Voice full page và text assistant tạo trải nghiệm phân tách. Team chuyển voice thành floating popup/call-only flow, đồng thời chuyển Agent sang model-driven tools để text và voice dùng chung semantics.

### Kết quả

- Agent được refactor sang model-driven tool architecture.
- Voice AI có floating button, popup và hands-free call.
- Bổ sung TOTP 2FA enforcement và tracking marker simulation.
- Gemini transcript rewrite, ASR hallucination fix, voice model config và reset button được thêm/sửa.

### Kiểm chứng và vấn đề

Voice rewrite đã xử lý được một số lỗi địa danh nhưng phụ thuộc chất lượng ASR và context booking. Handoff realtime và durable voice state chưa hoàn chỉnh.

### Bước tiếp theo

Đưa policy, pricing, maps và persistence vào business flow.

---

## 2026-08-16 — Business data và voice rewrite

### Người tham gia

- @NamKhanh2128 — commits f7e6bd6, 024982d và 0e9506b.
- @DanielK345 — commits 8925189, adf385d, 224c2fe, 8ea654f, 14379f9, 0c53535 và 94ce55a.

### Bối cảnh và quyết định

Frontend và Agent không nên tự quyết định giá, policy hay địa điểm. Team đưa catalog versioned, policy approved, quote integrity và maps contract vào backend; voice rewrite dùng gazetteer để sửa các địa danh dễ nhầm.

### Kết quả

- Có demo pricing catalog có version.
- Có approved policy catalog và source metadata.
- Có durable persistence, quote integrity, route snapshot và maps integration.
- Sửa migration, registration, popup UI, voice fallback, gazetteer và transcript rewrite.
- Backend-data và voice-ai được hợp nhất để dùng chung flow.

### Kiểm chứng và vấn đề

Catalog và quote flow phù hợp demo/staging. Giá, route và fleet vẫn chưa phải dữ liệu realtime production.

### Bước tiếp theo

Tạo evaluation cases và kiểm tra end-to-end.

---

## 2026-08-17 — Evaluation cases

### Người tham gia

- @DanielK345 — commits 72a67e1, d7d5e1f và 9762e91.

### Bối cảnh và quyết định

Team cần kiểm tra behavior theo scenario thay vì chỉ kiểm tra UI. Các case được tách thành happy path, correction và safety/handoff để quan sát tool/state transition.

### Kết quả

- Tạo eval_cases/ với workflow cases và kết quả JSON.
- Bổ sung scenario đổi pickup, đổi destination, đổi vehicle, out-of-scope và operator handoff.
- Cập nhật README và các artifact liên quan đến gazetteer/rewrite.

### Kiểm chứng và vấn đề

Summary tại [eval_cases/agent_workflow_eval_summary.json](../eval_cases/agent_workflow_eval_summary.json) ghi nhận workflow evaluation chưa đạt toàn bộ case; đây là evidence để sửa regression, không phải release sign-off.

### Bước tiếp theo

Chuyển voice transport sang LiveKit-native và đo reliability bằng smoke runner.

---

## 2026-08-18 — LiveKit-native baseline

### Người tham gia

- @PivePipiopia — commits 54a764e và 357348e.

### Bối cảnh và quyết định

Voice gateway cũ khó đồng bộ room, worker, state và operator takeover. Team chọn LiveKit Room/WebRTC làm transport, tách native AgentServer worker khỏi FastAPI control/business plane và giữ booking rules ở domain tools.

### Kết quả

- Có LiveKit token endpoint, room session và frontend LiveKit session.
- Có AgentServer, AgentSession, voice booking task và voice tools.
- Có state persistence, migration và scripts/livekit_room_smoke.py.
- Có tài liệu migration, runtime architecture và team setup.

### Kiểm chứng và vấn đề

Baseline đã tạo được đường chạy room/worker nhưng startup, reconnect, provider timeout và handoff thật vẫn cần hardening.

### Bước tiếp theo

Ổn định config/provider và giảm latency khởi động worker.

---

## 2026-08-19 — Provider và môi trường LiveKit

### Người tham gia

- @PivePipiopia — commit 807586a.
- @NamKhanh2128 — commits 1d35c38 và 04d225b.
- @DanielK345 — commits ce5db12 và 0e70589.

### Bối cảnh và quyết định

Team cần environment contract thống nhất cho backend, frontend, worker, maps và voice providers. Worker phải dùng VAD/LLM rewrite theo cùng config với test.

### Kết quả

- Chuẩn hóa .env.example cho LiveKit/provider.
- Cập nhật OSRM/maps và deployment configuration.
- Sửa database migration, VAD và LiveKit LLM rewrite.

### Kiểm chứng và vấn đề

Setup local đã có hướng dẫn, nhưng voice live vẫn phụ thuộc credential và hạ tầng LiveKit của môi trường chạy.

### Bước tiếp theo

Thêm warm worker, observability, timeout và recovery.

---

## 2026-08-20 — LiveKit hardening và reliability

### Người tham gia

- @PivePipiopia — commit 80c1d1a.
- @DanielK345 — commits e017c0c, f034646, 992daf2, 515ed71, 0ff1f1e, e8381b8, b646e60, 823130f, ea15675 và 4585931.
- @NamKhanh2128 — deployment và merge integration.

### Bối cảnh và quyết định

Các vấn đề chính là worker cold start, transcript rewrite bị treo, interruption làm sai booking context và data publication có thể chặn agent turn. Team chọn timeout có giới hạn, fail-open về raw transcript, event-level observability và warm worker.

### Kết quả

- LiveKit session recovery, handoff, state sync và early startup được harden.
- UI hiển thị transcript rewrite progress theo trạng thái pending/completed/skipped/failed/timeout.
- Rewrite và reliable publish có timeout; provider treo không giữ agent turn vô hạn.
- ASR confusion, interruption và booking context được xử lý bằng regression tests.
- Có structured observability cho worker lifecycle, latency và provider usage.

### Kiểm chứng và vấn đề

Phase 4 artifact tại [reports/voice-evaluation/phase4-product/phase4_run/report.md](../reports/voice-evaluation/phase4-product/phase4_run/report.md) cho thấy native room smoke có thể chạy nhưng booking/confirmation vẫn còn regression. Evidence này được dùng để mở release gate thay vì coi hardening là production completion.

### Bước tiếp theo

Hợp nhất các thay đổi vào runtime chính và viết release runbook.

---

## 2026-08-22 — Hợp nhất runtime và chuẩn hóa setup

### Người tham gia

- @PivePipiopia — commits 83b685c và 0d3765f.
- @NamKhanh2128 — commits 524949f, bdcdb9b và 8292db4.

### Bối cảnh và quyết định

Legacy voice path và LiveKit-native path cùng tồn tại gây nhầm lẫn khi chạy project. Team chọn LiveKit-native làm happy path, xử lý merge conflict và giữ tài liệu runtime theo implementation hiện tại.

### Kết quả

- Cập nhật implementation Agentic AI và release/evaluation artifacts.
- Chuẩn hóa README.md, docs/LIVEKIT_TEAM_SETUP.md và environment profiles.
- Hợp nhất agentic-ai với voice-ai, xử lý sync conflict.
- Sửa Docker permission khi chạy bằng appuser.

### Kiểm chứng và vấn đề

Commit merge ghi nhận test sau khi giải quyết conflict, nhưng pipeline cuối vẫn cần chạy lại trên head mới. Deployment chưa được xem là production sign-off.

### Bước tiếp theo

Thêm packaging/CI cho image và hoàn thiện handoff cuối PR.

---

## 2026-08-23 — Container và CI packaging

### Người tham gia

- @NamKhanh2128 — commits 0da268d, 954b90c, 0c545b0, 42bed83, 889c70e và 3d63048.

### Bối cảnh và quyết định

Deployment cần reproducible image và hỗ trợ cả môi trường shell lẫn PowerShell. Team đưa việc build/publish image vào script và GitHub Actions, đồng thời sửa tag/branch trigger để workflow chạy đúng.

### Kết quả

- Có Docker packaging scripts cho Linux và PowerShell.
- Có workflow publish image lên GHCR.
- Sửa image tag lowercase, branch trigger và PowerShell interpolation.

### Kiểm chứng và vấn đề

Packaging path đã được tự động hóa, nhưng deployment thật vẫn phụ thuộc secret, VPS/Render configuration và health verification.

### Bước tiếp theo

Ổn định deployment database/policy catalog và voice worker.

---

## 2026-08-24 — Handoff, model factory và deployment fix

### Người tham gia

- @PivePipiopia — commits 270e849, 5fbd041, 2030171 và 3b1fa9d.
- @PhucHung — commit e7c2756.

### Bối cảnh và quyết định

Voice handoff cần kết thúc đúng lifecycle; provider construction cũng cần tách khỏi server để dễ đổi model và test. Song song đó, deployment gặp lỗi permission, SQLite volume và static catalog path.

### Kết quả

- LiveKit handoff được harden với room lifecycle, state restore/publish, structured events và operator takeover.
- Model factory tách STT/LLM/TTS khỏi server.
- Nút hủy chuyến có một lần xác nhận rõ ràng; session data, frontend contract và booking test được đồng bộ.
- Điều chỉnh ASR timeout trong .env.example.
- Deployment fix xử lý Uvicorn permission, Docker volume cho SQLite và đường dẫn policy/pricing/gazetteer.
- Bổ sung deployment guide, checklist và script hỗ trợ triển khai.

### Kiểm chứng và vấn đề

Commit deployment ghi nhận backend, database, policy catalog, frontend và LiveKit được kiểm tra sau deploy. Tuy nhiên CI/evaluation của branch vẫn cần được xác nhận lại trên head cuối.

### Bước tiếp theo

Chạy lại full CI, workflow evaluation và kiểm tra browser/device trước khi gọi production-ready.

---

## 2026-08-27 — Cập nhật runtime và hợp nhất develop/main (historical note)

### Người tham gia

- @PivePipiopia — commit 2d327a8.
- @PhucHung — commits 8d18ca3 và c88c079.
- Team — PR #6, PR #7, PR #11 và PR #12.

### Bối cảnh và quyết định

Sau các lần merge, tài liệu cũ không còn phản ánh runtime hiện tại. Team cập nhật system design theo implementation, sửa LiveKit pipeline/config/session handling và hợp nhất develop vào main.

### Kết quả

- Cập nhật architecture/product documentation theo runtime hiện tại.
- Sửa LiveKit voice pipeline, frontend session handling và backend schema initialization.
- Bổ sung fix-voice-worker.sh và chỉnh Docker frontend/nginx/config.
- PR #6 và PR #7 được merge vào main.
- PR #11 được merge vào develop; PR #12 đưa develop vào main.

### Kiểm chứng và vấn đề

Đây là ghi nhận tại thời điểm merge cũ. Kết quả kiểm chứng mới nhất được ghi ở mục `Review hardening` bên dưới.

### Bước tiếp theo

- Theo dõi CI trên head hiện tại và chạy lại workflow/evaluation khi thay đổi contract.
- Kiểm tra deployment sau các thay đổi schema/config.
- Hoàn tất browser/device, reconnect, multi-tab, provider-failure và ASR checks.

---

## Tổng kết hiện tại

Team đã đi từ product baseline đến web assistant, Core Agent, booking workflow, grounded FAQ, human handoff, backend persistence và LiveKit-native voice runtime. Người dùng hiện có thể đi qua text/voice booking flow, sửa thông tin, nhận quote/confirmation, tra cứu/hủy chuyến và chuyển sang operator theo contract.

Các phần vẫn đang ở trạng thái demo/staging hoặc cần release gate gồm pricing/maps/fleet realtime, production database operations, payment/refund, CRM, emergency flow, browser/device matrix, load/soak, CI và evaluation regression.

Worklog ghi lịch sử task/output theo thành viên; journal này ghi reasoning, kết quả, evidence và các vấn đề cần giải quyết tiếp.


---

## 2026-08-27 — Review hardening trên `feature/agentic-ai`

### Vấn đề phát hiện

Review ban đầu không thể rebuild từ `main`, một số catalog runtime trỏ nhầm sang
`config/`, workflow correction dựng lại confirmation cũ, và tài liệu provider/CI
không đồng bộ với LiveKit baseline hiện tại.

### Thay đổi đã thực hiện

- Đồng bộ đường dẫn policy, pricing và gazetteer theo `data/`, có fallback static
  cho Docker volume.
- Sửa correction flow: đổi pickup/destination/vehicle được đưa qua
  `update_booking`, giữ loại xe trong draft active, invalidate quote cũ và estimate
  lại trước khi xin xác nhận mới. Rebook sau booking hoàn tất vẫn yêu cầu chọn xe lại.
- Đồng bộ provider hiện tại: LiveKit Inference/Deepgram Nova-3, OpenAI LLM qua
  LiveKit và Google Gemini Flash TTS với Chirp fallback.
- Đồng bộ Python 3.12 giữa `pyproject.toml`, Docker và CI; sửa Render worker dùng
  full PostgreSQL DSN do owner cấu hình thay vì lấy host web service.
- Sửa README/index/source-of-truth/release evidence và loại archive deployment có
  chứa environment/database artifacts khỏi source hiện tại.

### Kiểm chứng

- Full pytest: `459 passed, 3 skipped`.
- Targeted booking/eval/config tests: pass.
- Ruff và `git diff --check`: pass.
- Deterministic workflow eval: 6/6 case pass.

Live provider, database migration production, browser/device matrix và operator
transfer vẫn được đánh dấu release-gated; không gọi chúng là production-ready khi
chưa có external evidence.
