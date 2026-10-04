# 📚 Hệ Thống Tài Liệu Kỹ Thuật OlaSM

Cập nhật: **04/10/2026** · Trạng thái: **CANONICAL / PRODUCTION-READY**

---

## 🧭 Lộ Trình Đọc Tài Liệu (Reading Path)

1. **Bắt đầu nhanh**: [README.md](../README.md) & [START-HERE.md](../START-HERE.md) — Tổng quan, khởi chạy local và lệnh test.
2. **Đặc tả sản phẩm**: [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) & [PRD_OlaSM_Voice.md](PRD_OlaSM_Voice.md) — Tầm nhìn sản phẩm, user stories và tiêu chí hoàn thành.
3. **Kiến trúc tổng thể**: [PROJECT_SYSTEM_SPECIFICATION.md](PROJECT_SYSTEM_SPECIFICATION.md) & [architecture_diagram.md](architecture_diagram.md) — Master spec kiến trúc, AI audio pipeline và state machine.
4. **Bảo mật & Guardrails**: [OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md](OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md) — 3 tầng phòng thủ: Prompt Injection, Out-of-Scope, PII Redaction và Idempotency Gate.
5. **Nguồn sự thật hệ thống**: [PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md) — Trạng thái module, contract boundaries và mapping tiêu chuẩn.
6. **Vận hành Voice Agent**: [LIVEKIT_TEAM_SETUP.md](LIVEKIT_TEAM_SETUP.md) — LiveKit WebRTC worker, Gemini Flash TTS và Deepgram Nova-3.
7. **Triển khai Production**: [deployment/runbook.md](deployment/runbook.md) — Quy trình Docker Compose chuẩn hóa với script [scripts/deploy.sh](../scripts/deploy.sh).
8. **Đo lường & Benchmarks**: [evaluation.md](evaluation.md) & [benchmarks/README.md](../benchmarks/README.md) — Độ trễ, độ ổn định, chi phí và độ chính xác AI.
9. **Hạ tầng / Owner Checklist**: [../mustdo.md](../mustdo.md) — Các mục hạ tầng live cần cấp quyền thực tế.

Scope đề bài gốc lưu trữ tại: [GSM-08_VOICE_AGENT_SCOPE.md](GSM-08_VOICE_AGENT_SCOPE.md).

---

## 🗂️ Danh Mục Tài Liệu Theo Chuyên Mục

| Phân hệ | Tài liệu chi tiết | Mô tả trọng tâm |
|---|---|---|
| **Product & Scope** | [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)<br>[PRD_OlaSM_Voice.md](PRD_OlaSM_Voice.md)<br>[FEATURE_USER_STORIES.md](FEATURE_USER_STORIES.md)<br>[GSM-08_VOICE_AGENT_SCOPE.md](GSM-08_VOICE_AGENT_SCOPE.md) | Yêu cầu sản phẩm, chân dung khách hàng lớn tuổi/bận tay, luồng đặt xe giọng nói. |
| **System & Architecture** | [PROJECT_SYSTEM_SPECIFICATION.md](PROJECT_SYSTEM_SPECIFICATION.md)<br>[architecture_diagram.md](architecture_diagram.md)<br>[PROJECT_SOURCE_OF_TRUTH.md](PROJECT_SOURCE_OF_TRUTH.md) | Kiến trúc Dual-Plane, máy trạng thái hội thoại, cơ chế đồng bộ và khôi phục phiên. |
| **Security & Safety** | [OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md](OlaSM_SECURITY_AND_GUARDRAILS_SPEC.md) | Lọc injection không qua LLM, chặn audio bomb, xác nhận giá rõ ràng, ẩn số điện thoại. |
| **Voice AI & RTC** | [LIVEKIT_TEAM_SETUP.md](LIVEKIT_TEAM_SETUP.md)<br>[voice-ai/README.md](voice-ai/README.md) | LiveKit WebRTC, VAD ngắt lời barge-in, Gemini Flash TTS, Nova-3 STT tiếng Việt. |
| **Operations & Deploy** | [deployment/runbook.md](deployment/runbook.md)<br>[archive/deployment/README.md](archive/deployment/README.md) | Hướng dẫn vận hành Docker Compose, cấu hình production, tích hợp tự động DB SQLite. |
| **Evaluation & Tests** | [evaluation.md](evaluation.md)<br>[verification/release-readiness.md](verification/release-readiness.md)<br>[eval_cases/README.md](../eval_cases/README.md) | 694 automated tests (100% Green), kết quả benchmark độ trễ (<1.2s TTFB) và chi phí. |
| **Mã nguồn con** | [src/backend/README.md](../src/backend/README.md)<br>[src/agents/README.md](../src/agents/README.md)<br>[src/frontend/README.md](../src/frontend/README.md) | Tài liệu kỹ thuật chi tiết của từng layer backend, agent dialog và frontend React. |
