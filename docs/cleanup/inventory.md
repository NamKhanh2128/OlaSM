# Codebase Cleanup Inventory & Dependency Graph

- **Thời điểm lập bảng:** 2026-10-04T16:27:00+07:00
- **Phạm vi khảo sát:** Toàn bộ repository `C:\Users\KHANH\Documents\GitHub\OlaSM`

---

## 1. Bảng phân loại ứng viên kiểm toán (Candidate Inventory)

| path | tracked/untracked/ignored | category | owner | referenced_by | evidence | confidence | proposed_action | rollback |
|---|---|---|---|---|---|---|---|---|
| `main.py` (root) | tracked | `DELETE_SAFE_GENERATED` | uv init / boilerplate | Không có (chỉ in "Hello from p-160!") | Entrypoint active là `src/main.py` và `src/backend/main.py`. Makefile, Dockerfile trỏ tới `src.main:app`. | 0.98 | Xóa an toàn | `git restore main.py` |
| `asr_server/` | ignored | `DELETE_SAFE_GENERATED` | Legacy ASR server | Không có source active | Thư mục chỉ chứa `__pycache__` và bytecode `.pyc` cũ, 0 source code | 1.00 | Xóa thư mục rỗng và bytecode | Tái tạo thư mục nếu cần |
| `src/voice/` | ignored | `DELETE_SAFE_GENERATED` | Legacy ZipFormer/TTS | Không có source active | Thư mục chỉ chứa cây thư mục rỗng và `__pycache__` cũ. Runtime active là `src/voice_agent/` | 1.00 | Xóa thư mục rỗng và bytecode | Tái tạo thư mục nếu cần |
| `tests/test_voice/` | ignored | `DELETE_SAFE_GENERATED` | Legacy voice tests | Không có source active | Chỉ chứa `__pycache__`. Test suite active nằm ở `tests/test_voice_agent/` | 1.00 | Xóa thư mục rỗng và bytecode | Tái tạo thư mục nếu cần |
| `.pytest_cache/` | ignored | `DELETE_SAFE_GENERATED` | pytest | pytest runtime | Cache kiểm thử tự sinh khi chạy pytest | 1.00 | Xóa cache generated | Tự sinh lại khi chạy pytest |
| `.ruff_cache/` | ignored | `DELETE_SAFE_GENERATED` | ruff | ruff linter | Cache linter tự sinh khi chạy ruff | 1.00 | Xóa cache generated | Tự sinh lại khi chạy ruff |
| `.coverage` | ignored | `DELETE_SAFE_GENERATED` | coverage.py | pytest-cov | Database coverage cục bộ từ lần chạy test trước | 1.00 | Xóa file coverage | Tự sinh lại khi chạy test coverage |
| `data/skills/` | ignored | `DELETE_SAFE_GENERATED` | Local duplication | Không có | Bản copy thừa của `.agents/skills`. Canonical là `.agents/skills` | 0.98 | Xóa bản copy thừa | Copy lại từ `.agents/skills` |
| `DEPLOY-FIX.md` | tracked | `ARCHIVE` | DevOps / VPS Fix | `README-DEPLOYMENT.md` | Bản ghi fix VPS tạm thời ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `deploy-fixed.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script shell fix VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `DEPLOY-VPS-FINAL.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | `START-HERE.md` | Script shell deploy VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `DEPLOYMENT-SUMMARY.md` | tracked | `ARCHIVE` | DevOps / VPS Fix | `START-HERE.md`, `README-DEPLOYMENT.md` | Báo cáo fix VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `deploy_mustdo.md` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Hướng dẫn triển khai cũ | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `FINAL-DEPLOY.md` | tracked | `ARCHIVE` | DevOps / VPS Fix | `START-HERE.md`, `README-DEPLOYMENT.md` | Hướng dẫn deploy VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `final-deploy.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script shell deploy VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `fix-deploy.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script shell deploy VPS ngày 31/08/2026 | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `README-DEPLOYMENT.md` | tracked | `ARCHIVE` | DevOps / VPS Fix | `START-HERE.md` | Hướng dẫn tổng quan deploy VPS cũ | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `fix-voice-worker.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script restart voice worker VPS cũ | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `quick-fix.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script fix nhanh VPS cũ | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `vps-fix-database.sh` | tracked | `ARCHIVE` | DevOps / VPS Fix | Không có | Script fix db VPS cũ | 0.95 | Chuyển vào `docs/archive/deployment/` | `git mv` ngược lại |
| `src/agents/legacy/` | tracked | `KEEP_ACTIVE` | Agent compatibility | `src/agents/agent.py`, `tests/` | Lớp tương thích và fallback khi `agent_llm_enabled=False`. Được import bởi nhiều test | 1.00 | **Giữ nguyên 100%** | N/A |
| `data/gazetteer/` | tracked | `KEEP_ACTIVE` | Maps / Gazetteer | `src/backend/services/maps_service.py` | Dữ liệu địa danh Hà Nội phục vụ tìm kiếm địa điểm offline | 1.00 | **Giữ nguyên 100%** | N/A |
| `data/pricing/`, `policies/`, `safety/` | tracked | `KEEP_ACTIVE` | Backend Domain | `PricingService`, `PolicyService`, `SafetyEngine` | Seed data nghiệp vụ, chính sách an toàn, bảng cước | 1.00 | **Giữ nguyên 100%** | N/A |
| `.agents/skills` | tracked | `KEEP_ACTIVE` | Antigravity AI IDE | Workspace Customization Root | Thư mục skill chính thức của Antigravity IDE | 1.00 | **Giữ nguyên 100%** | N/A |
| `.claude/skills` | tracked | `KEEP_ACTIVE` | Claude Code CLI | Claude CLI tooling | Cấu hình và skill cho Claude CLI | 0.95 | **Giữ nguyên 100%** | N/A |
| `agent/skills` | tracked | `KEEP_ACTIVE` | Git tracked skills | `skills-lock.json` | Được track trong Git và khóa qua skills-lock.json | 0.90 | **Giữ nguyên (không xóa mù)** | N/A |
| `specification_documents/` | tracked | `KEEP_HISTORICAL` | Course / Boilerplate specs | `docs/README.md` | Tài liệu mẫu và đặc tả ban đầu từ chương trình | 0.90 | Giữ nguyên làm tài liệu tham chiếu | N/A |
| `presentation/` | tracked | `KEEP_HISTORICAL` | Slide / Deliverables | Báo cáo thuyết trình | Tài liệu thuyết trình và minh họa dự án | 0.90 | Giữ nguyên làm tài liệu tham chiếu | N/A |
| `.venv/` | ignored | `KEEP_ACTIVE` | Python virtualenv | IDE, test, execution | Môi trường Python local đang được sử dụng | 1.00 | **Không xóa .venv** | N/A |
| `logs/`, `.ai-log/` | ignored/tracked | `KEEP_HISTORICAL` | AI audit / Runtime logs | Audit trail | Bằng chứng thực thi và lịch sử trao đổi AI | 0.95 | Giữ theo chính sách retention | N/A |

---

## 2. Kết luận phân loại số lượng

- **DELETE_SAFE_GENERATED**: 8 mục (root `main.py`, `asr_server/`, `src/voice/`, `tests/test_voice/`, `data/skills/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`).
- **ARCHIVE**: 12 tệp deployment scripts rời rạc tại root (tập trung về `docs/archive/deployment/`).
- **KEEP_ACTIVE**: 8+ nhóm cốt lõi (runtime, backend, agent, legacy compatibility layer, seed data, active skills, venv).
- **KEEP_HISTORICAL**: 4 nhóm (specification_documents, presentation, logs, benchmarks).
- **BLOCKED_NEEDS_CONFIRMATION**: 0 mục vi phạm quy tắc.
