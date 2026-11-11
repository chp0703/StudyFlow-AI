# Ma Trận Quyền Sở Hữu File & Module (File Ownership Matrix)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Xác định rõ chủ sở hữu chính (`Primary Owner`), người đồng kiểm duyệt (`Co-Reviewer`), vùng dùng chung (`Shared`) và vùng cấm sửa tự ý (`Protected`) cho từng đường dẫn thực tế trong repository |
| **Thẩm quyền (Authority)** | Bắt buộc áp dụng khi giao task, mở PR và kiểm tra diff cho cả 6 vai trò (`FE-1`, `FE-2`, `BE-1`, `BE-2`, `BE-3`, `BE-4`) |
| **Chủ sở hữu (Owner)** | Project Owner & Repository Governance (`BE-4` điều phối phân xử) |
| **Base commit kiểm chứng** | `main` @ `7837050` (`Merge pull request #21 from chp0703/feat/f1-frontend-integration`) |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Nguyên tắc Phân quyền Sở hữu (Ownership Rules)

1. **Dựa trên source tree thực tế tại `main` (`7837050`):** Mọi đường dẫn dưới đây đã được kiểm chứng trên `HEAD` của `main`. Các đường dẫn dự kiến cho tính năng mới chưa tồn tại trên `main` được gắn nhãn **`[PLANNED]`** rõ ràng.
2. **Mỗi file hoặc migration chỉ có MỘT Primary Owner tại một thời điểm:**
   - Agent chỉ được sửa các file thuộc `Primary Owner` của vai trò mình và nằm trong danh sách `Allowed Files` của Task Spec.
   - Không cho phép hai agent cùng sửa một file trong hai nhánh song song mà không có thứ tự phụ thuộc.
3. **File dùng chung (`Shared Files`) bắt buộc có Co-Review:**
   - Các file khung ứng dụng (`frontend/src/App.tsx`, `frontend/src/api/*`, `backend/app/main.py`, `backend/app/orchestrator/actions.py`, `supabase/migrations/*`, `contracts/*`) có một `Primary Owner` chịu trách nhiệm điều phối nhưng **bắt buộc phải có `Co-Reviewer`** thuộc các vai trò bị ảnh hưởng trước khi merge.
4. **Quy tắc riêng cho Database Migrations (`supabase/migrations/`):**
   - Các migration lịch sử `202611050001_*.sql` đến `202611050021_*.sql` là **BẤT BIẾN (`IMMUTABLE HISTORY`)** — cấm sửa nội dung để bảo toàn đường nâng cấp (`upgrade route`).
   - Migration `202611050012_f1_contract_schema.sql` là **GENERATED FILE** từ `backend/scripts/generate_contract_schema_migration.py` — chỉ được cập nhật bằng script sau khi thay đổi `contracts/schemas/f1.schema.json` đã được duyệt.
   - Khi cần thêm migration mới (`202611050022+` hoặc timestamp mới): chỉ một agent tạo migration tại một thời điểm theo sự điều phối thứ tự của `BE-1` (cho schema/task/window/timezone) và `BE-2` (cho RPC planning/approval), luôn có `BE-1` đồng kiểm duyệt về khóa ngoại, RLS và quyền `sf_rpc_owner`.
5. **Quy tắc riêng cho Official Contracts (`contracts/`):**
   - Domain owner (`BE-1`, `BE-2`, `BE-3`, `BE-4`) đề xuất thay đổi trong phạm vi domain của mình; `BE-4` kiểm tra tính nhất quán tích hợp; `FE-1`/`FE-2` review dưới góc độ consumer; **Project Owner** phê duyệt cuối cùng theo [`CONTRACT_CHANGE_PROTOCOL.md`](CONTRACT_CHANGE_PROTOCOL.md).

---

## 2. Tổng quan Trách nhiệm 6 Vai trò

| Vai trò | Nhóm | Phạm vi sở hữu chính (Primary Ownership Summary) |
|---|---|---|
| **FE-1** | Frontend | Giao diện và logic client cho **Task / Planner / Calendar / Confirmation**: `pages/Planner.tsx`, `features/planner/*` (`WeekCalendar.tsx`, `ProposalReview.tsx`, `TaskPanel.tsx`, `usePlanner.ts`, `plannerAgent.ts`, `proposal.ts`), `types/{planner,task}.ts`, `utils/date.ts`, `styles/planner.css` |
| **FE-2** | Frontend | Giao diện và logic client cho **Personalized Working Time / Upload Review / Assistant**: `features/assistant/*` (`Assistant.tsx`, `ChatComposer.tsx`, `ChatTranscript.tsx`, `ConversationSidebar.tsx`, `useConversationHistory.ts`, `conversationHistory.ts`, `assistantService.ts`, `apiAssistant.ts`), `features/auth/LoginPage.tsx`, `components/HomeSummary.tsx`, `types/assistant.ts`, `styles/{assistant,history,home,auth}.css` |
| **BE-1** | Backend | **Database / Task Schema / Timezone / Working Time**: Mô hình dữ liệu `User`, `TaskCandidate`, `AcademicTask`, `TimeWindow`, ngữ nghĩa múi giờ (`Asia/Ho_Chi_Minh`), chuẩn hóa khung giờ (`f1/scheduler/normalization.py`, `intervals.py`), các migration về thực thể/task/time-windows/preferences/RLS, script sinh schema migration (`generate_contract_schema_migration.py`) và tài liệu `docs/database/*` |
| **BE-2** | Backend | **Scheduler / Proposal / Approval**: Bộ lập lịch tất định và dịch vụ lập kế hoạch (`backend/app/f1/planning/generate.py`, `backend/app/f1/scheduler/{models,constraints,engine,replanning,service,evaluation,__init__}.py`), script `evaluate_planner.py`, các RPC SQL về đọc/lưu/duyệt/từ chối đề xuất lịch (`018`–`021` và các migration mới thuộc miền planning/approval), cùng bộ test ` tests_concurrency/` |
| **BE-3** | Backend | **AI / DeepSeek / File Ingestion**: Bộ trích xuất ngôn ngữ tự nhiên (`backend/app/nlu/{extractor,evaluation}.py`), script `evaluate_nlu.py`, bộ dữ liệu đánh giá (`backend/tests/fixtures/nlu_eval_vi.json`, `eval/**`), và toàn bộ pipeline đọc/trích xuất tệp (`image`/`calendar`/`document`) + từ chối `audio` **`[PLANNED]`** |
| **BE-4** | Backend | **Chat / Task Draft / API Integration Coordinator**: Điểm vào FastAPI và HTTP layer (`backend/app/main.py`, `core/*`, `clients/rpc.py`, `api/v1/*`), tầng điều phối bền vững (`backend/app/orchestrator/{actions,chat,receipts,workflow_ports,workflow_shared}.py`), phối hợp chỉ mục contract và kiểm thử tích hợp HTTP (`backend/tests/integration/*`) |

---

## 3. Bảng Ánh xạ Quyền Sở hữu Chi tiết theo Đường dẫn (Verified Path Matrix)

### 3.1. Nhóm Frontend (`frontend/`)

| Đường dẫn / Pattern (đã xác minh trên `7837050`) | Phân loại | Primary Owner | Co-Reviewers bắt buộc | Ghi chú & Ranh giới chỉnh sửa |
|---|---|---|---|---|
| `frontend/src/pages/Planner.tsx` | Feature UI | **FE-1** | `FE-2` (nếu chạm vùng nhập khung giờ làm việc) | Ghép lịch tuần, khung lệnh, vùng xem trước đề xuất và bảng công việc |
| `frontend/src/features/planner/WeekCalendar.tsx` | Feature UI | **FE-1** | — | Lịch tuần, Sticky Date Header, hiển thị ngày cụ thể cạnh thứ, hiển thị khối học và khung giờ |
| `frontend/src/features/planner/ProposalReview.tsx` | Feature UI | **FE-1** | `BE-2`, `BE-4` (khi đổi trường hiển thị DTO) | Hiển thị preview đề xuất lịch, diff, cảnh báo, `unscheduled duration` (`PARTIAL`) và nút Duyệt/Từ chối |
| `frontend/src/features/planner/TaskPanel.tsx` | Feature UI | **FE-1** | — | Danh sách/lọc task, form tạo/xem chi tiết task, tách hiển thị `title` và `course_label` |
| `frontend/src/features/planner/usePlanner.ts` | Feature Hook | **FE-1** | `FE-2`, `BE-4` | Điều phối state Planner, gọi API/Demo, xử lý `AWAITING_APPROVAL` và `ActionReference` |
| `frontend/src/features/planner/proposal.ts`<br/>`frontend/src/features/planner/proposal.test.ts`<br/>`frontend/src/features/planner/plannerAgent.ts`<br/>`frontend/src/features/planner/plannerAgent.test.ts` | Feature Logic & Tests | **FE-1** | — | Logic so sánh đề xuất, kiểm tra `STALE` và agent mẫu ở chế độ Demo |
| `frontend/src/types/task.ts`<br/>`frontend/src/types/planner.ts`<br/>`frontend/src/utils/date.ts`<br/>`frontend/src/styles/planner.css` | Types / Utils / Styles | **FE-1** | `FE-2` (nếu đổi kiểu dùng chung trong `App.tsx` hoặc `mappers.ts`) | Kiểu dữ liệu Task/Planner, xử lý ngày tháng và CSS trang Lập kế hoạch |
| `frontend/src/features/tasks/**` *(hiện có `.gitkeep`)*<br/>`frontend/src/features/schedule/**` *(hiện có `.gitkeep`)*<br/>`frontend/src/features/proposals/**` *(hiện có `.gitkeep`)* | Placeholder / **`[PLANNED]`** | **FE-1** | — | Dùng khi tách thêm component con cho Task Form, Sticky Calendar hoặc Confirmation Preview |
| `frontend/src/features/assistant/Assistant.tsx`<br/>`frontend/src/features/assistant/ChatComposer.tsx`<br/>`frontend/src/features/assistant/ChatTranscript.tsx`<br/>`frontend/src/features/assistant/ConversationSidebar.tsx` | Feature UI | **FE-2** | `FE-1` (nếu liên kết điều hướng sang Planner) | Giao diện chat trợ lý, đính kèm tệp (image/calendar/document, chặn audio), hiển thị thẻ làm rõ/review trích xuất |
| `frontend/src/features/assistant/useConversationHistory.ts`<br/>`frontend/src/features/assistant/conversationHistory.ts`<br/>`frontend/src/features/assistant/conversationHistory.test.ts`<br/>`frontend/src/features/assistant/apiAssistant.ts`<br/>`frontend/src/features/assistant/apiAssistant.test.ts`<br/>`frontend/src/features/assistant/assistantService.ts` | Feature Logic & Tests | **FE-2** | `BE-4`, `BE-3` | Lưu trữ IndexedDB (`studyflow-assistant-history`), ánh xạ phản hồi API sang tin nhắn/đề xuất chat và luồng mẫu |
| `frontend/src/features/availability/**` *(hiện có `.gitkeep`)*<br/>`frontend/src/features/chat/**` *(hiện có `.gitkeep`)* | Placeholder / **`[PLANNED]`** | **FE-2** | `BE-1` (cho Working Time), `BE-3` (cho Upload Review) | Nơi đặt component Personalized Working Time UI và Extraction Review/Correction UI khi triển khai |
| `frontend/src/components/HomeSummary.tsx`<br/>`frontend/src/features/auth/LoginPage.tsx`<br/>`frontend/src/types/assistant.ts`<br/>`frontend/src/styles/{assistant,history,home,auth}.css` | Feature UI / Types / Styles | **FE-2** | `FE-1` (với `HomeSummary.tsx` nếu đổi cấu trúc `Task`) | Trang chủ, màn hình đăng nhập Supabase, kiểu dữ liệu Assistant và CSS tương ứng |
| `frontend/src/App.tsx`<br/>`frontend/src/main.tsx`<br/>`frontend/src/vite-env.d.ts` | **Shared App Shell** | **FE-1** (điều phối chính) | **FE-2** (bắt buộc co-review mọi thay đổi) | Khung ứng dụng, điều hướng trang, state dùng chung (`tasks`, `availability`, `proposal`, `revision`). Không để hai FE sửa `App.tsx` cùng lúc |
| `frontend/src/api/client.ts`<br/>`frontend/src/api/client.test.ts`<br/>`frontend/src/api/config.ts`<br/>`frontend/src/api/auth.ts`<br/>`frontend/src/api/endpoints.ts`<br/>`frontend/src/api/index.ts`<br/>`frontend/src/api/types.ts`<br/>`frontend/src/api/mappers.ts`<br/>`frontend/src/api/mappers.test.ts`<br/>`frontend/src/api/pending.ts`<br/>`frontend/src/api/useServerData.ts` | **Shared FE API Layer** | **FE-1** (cho `tasks`/`plans`/`proposals`/`mappers` lịch) & **FE-2** (cho `auth`/`messages`/upload/working-time) | **BE-4**, **FE-1**, **FE-2** (bắt buộc đồng kiểm duyệt) | Client HTTP gọi 8 endpoint F1 và mapper DTO ↔ UI model. Mọi thay đổi trong `frontend/src/api/` phải bám sát `contracts/openapi.yaml` và `f1.schema.json` |
| `frontend/src/components/ui/{Button,Card,Modal}.tsx`<br/>`frontend/src/styles/{index,tokens,base,layout,cards,overlays,overrides}.css` | **Shared UI & Design System** | **FE-1** | **FE-2** | Thành phần UI gốc và hệ thống CSS cascade. **Cấm** tự ý đảo thứ tự `@import` trong `styles/index.css` |
| `frontend/src/pages/Study.tsx`<br/>`frontend/src/styles/study.css` | Out-of-Scope Demo (`F2`/`F3`) | **Protected / No-Touch trong F1** | `FE-1`, `FE-2`, Project Owner | Trang demo Học tập (F2/F3); không sửa trong phạm vi task F1 trừ khi có yêu cầu tách biệt từ Project Owner |
| `frontend/package.json`<br/>`frontend/package-lock.json`<br/>`frontend/tsconfig.json`<br/>`frontend/vite.config.ts`<br/>`frontend/index.html`<br/>`frontend/.env.example`<br/>`frontend/DESIGN.md`<br/>`frontend/README.md` | **Shared Frontend Config & Docs** | **FE-1** | **FE-2**, **BE-4** | Không tự cài thêm thư viện npm mới khi chưa được duyệt; `.env.example` chỉ chứa tên biến `VITE_*` rỗng |

---

### 3.2. Nhóm Backend (`backend/` & `tests/` & `eval/`)

| Đường dẫn / Pattern (đã xác minh trên `7837050`) | Phân loại | Primary Owner | Co-Reviewers bắt buộc | Ghi chú & Ranh giới chỉnh sửa |
|---|---|---|---|---|
| `backend/app/f1/scheduler/normalization.py`<br/>`backend/app/f1/scheduler/intervals.py`<br/>`backend/tests/acceptance_sol/test_normalization_contract.py` | Domain Time / Window Normalization | **BE-1** | **BE-2** | Chuẩn hóa `TimeWindow` (`NONE`/`WEEKLY`, `24:00`, DST, IANA timezone `Asia/Ho_Chi_Minh`) thành các khoảng cụ thể cho Scheduler. Lưu ý: các file trong `acceptance_sol/` là test nghiệm thu độc lập, **cấm làm yếu assertion** |
| `backend/scripts/generate_contract_schema_migration.py`<br/>`backend/tests/unit/test_contract_schema_migration.py` | Schema Bundling Script | **BE-1** | **BE-4** | Sinh tự động migration `012` từ `contracts/schemas/f1.schema.json` |
| `backend/app/f1/tasks/**` *(hiện có `__init__.py`)*<br/>`backend/app/f1/availability/**` *(hiện có `__init__.py`)* | Placeholder / **`[PLANNED]`** | **BE-1** | **BE-2**, **BE-4** | Dành cho domain validation của Task / Personalized Working Time / Timezone nếu tách khỏi orchestrator |
| `backend/app/f1/planning/generate.py`<br/>`backend/app/f1/planning/__init__.py` | Planning Adapter | **BE-2** | **BE-1**, **BE-4** | Chuyển snapshot từ DB sang `SchedulingContext`, áp policy/override, gọi `PlanningService` và dựng `PlanProposal` hoặc `SchedulingReadData` |
| `backend/app/f1/scheduler/models.py`<br/>`backend/app/f1/scheduler/constraints.py`<br/>`backend/app/f1/scheduler/engine.py`<br/>`backend/app/f1/scheduler/replanning.py`<br/>`backend/app/f1/scheduler/service.py`<br/>`backend/app/f1/scheduler/evaluation.py`<br/>`backend/app/f1/scheduler/__init__.py`<br/>`backend/scripts/evaluate_planner.py` | Pure Deterministic Scheduler | **BE-2** | **BE-1** (khi chạm `models.py` hoặc `constraints.py`) | Bộ lập lịch thuần, kiểm tra ràng buộc, tái lập lịch giữ `block_id`, tính `FULL`/`PARTIAL`/`NONE`/`NO_CHANGE` và `unallocated` |
| `backend/tests/unit/f1/scheduler/**`<br/>`backend/tests/acceptance_sol/test_scheduler_contract.py`<br/>`backend/tests/acceptance_sol/test_scheduler_review_regressions.py`<br/>`docs/planner/{scheduling_rules,evaluation}.md` | Scheduler Tests & Docs | **BE-2** | — | Chỉ thêm test mới khi mở rộng; **cấm sửa giảm điều kiện** trong `acceptance_sol/` |
| `backend/app/f1/approval/**` *(hiện có `__init__.py`)* | Placeholder / **`[PLANNED]`** | **BE-2** | **BE-4** | Dành cho logic kiểm tra phê duyệt bổ sung ở tầng Python (nếu tách riêng) |
| `backend/app/nlu/extractor.py`<br/>`backend/app/nlu/evaluation.py`<br/>`backend/app/nlu/prompts/**`<br/>`backend/scripts/evaluate_nlu.py`<br/>`backend/tests/unit/test_extractor.py`<br/>`backend/tests/unit/test_nlu_evaluation.py`<br/>`backend/tests/fixtures/nlu_eval_vi.json`<br/>`eval/**` | NLU / DeepSeek Adapter & Benchmark | **BE-3** | **BE-4** (khi đổi giao diện `Extractor` hoặc `ExtractionResult`) | Adapter gọi DeepSeek server-side, prompt trích xuất, bộ chấm 40 câu tiếng Việt (`>= 38/40`) |
| `backend/app/ingestion/**` **`[PLANNED]`**<br/>`backend/tests/unit/test_ingestion*.py` **`[PLANNED]`** | File Ingestion Pipeline **`[PLANNED]`** | **BE-3** | **BE-4**, **BE-1**, **FE-2** | Dự kiến cho đọc/trích xuất `image`, `calendar`, `document`, từ chối `audio`, chống prompt injection và tạo candidate trung gian (chỉ tạo sau khi chốt ADR/contract) |
| `backend/app/main.py`<br/>`backend/app/core/config.py`<br/>`backend/app/core/security.py`<br/>`backend/app/core/contract.py`<br/>`backend/app/clients/rpc.py`<br/>`backend/app/api/v1/routes.py`<br/>`backend/app/api/v1/http.py`<br/>`backend/app/api/v1/workflow.py`<br/>`backend/app/api/v1/chat.py` | **HTTP / Auth / RPC Client / App Factory** | **BE-4** | **BE-1**, **BE-2**, **BE-3** (tùy route bị ảnh hưởng) | Giữ nguyên chữ ký `create_app(settings=None, *, rpc_transport=None, llm_transport=None, jwks_transport=None, clock=None, extractor=None)` |
| `backend/app/orchestrator/actions.py`<br/>`backend/app/orchestrator/chat.py`<br/>`backend/app/orchestrator/receipts.py`<br/>`backend/app/orchestrator/workflow_ports.py`<br/>`backend/app/orchestrator/workflow_shared.py`<br/>`backend/app/orchestrator/README.md` | **Durable Orchestrator & Task Draft Flow** | **BE-4** | **BE-1** (cho task/window/policy), **BE-2** (cho `build_plan`/decision), **BE-3** (cho `extract`) | Điều phối multi-intent queue, `PendingAction`, chỉnh sửa/làm rõ `TaskCandidate`, recovery/cancel/resume và idempotency |
| `backend/tests/unit/test_action_rejection.py`<br/>`backend/tests/unit/test_receipt_recovery.py`<br/>`backend/tests/unit/test_workflow_errors.py`<br/>`backend/tests/integration/test_chat_local_supabase.py`<br/>`backend/tests/integration/test_http_local_supabase.py` | Orchestrator & HTTP Integration Tests | **BE-4** | **BE-1**, **BE-2**, **BE-3** | Kiểm thử đơn vị và tích hợp HTTP trên Supabase local |
| `backend/tests/acceptance_api_sol/**`<br/>`backend/tests/acceptance_db_sol/**` | **Protected Independent Acceptance Tests** | **Protected (BE-4 giám sát)** | **Project Owner** | Bộ test nghiệm thu độc lập của Sol; **cấm các implementer tự ý sửa để làm xanh test** |
| `backend/app/orchestrator/{dispatcher,registry}.py`<br/>`backend/app/services/{tasks,settings,plans,scheduling_policy,README}.py`<br/>`tests/**` *(thư mục gốc)* | Legacy Draft Modules & Root Tests | **BE-4** (bảo trì trạng thái đóng băng) | **BE-1**, **BE-2** | Giữ nguyên để pass `python -B -m unittest discover -s tests -v`; không tự nối vào `create_app()` |
| `backend/requirements.txt`<br/>`backend/requirements-acceptance.txt`<br/>`backend/pyproject.toml`<br/>`backend/README.md` | **Shared Backend Config** | **BE-4** | **BE-1**, **BE-2**, **BE-3** | Mọi bổ sung thư viện Python (ví dụ parser cho `BE-3`) phải được đồng thuận và cập nhật đồng bộ |

---

### 3.3. Nhóm Database & Supabase (`supabase/`)

| Đường dẫn / Pattern (đã xác minh trên `7837050`) | Phân loại | Primary Owner | Co-Reviewers bắt buộc | Ghi chú & Ranh giới chỉnh sửa |
|---|---|---|---|---|
| `supabase/migrations/202611050001_*.sql` .. `202611050011_*.sql`<br/>`supabase/migrations/202611050013_*.sql` .. `202611050021_*.sql` | **Protected Historical Migrations** | **Protected (BE-1 & BE-2 giám sát)** | **Project Owner** | **CẤM SỬA** các file migration lịch sử đã merge để bảo toàn kiểm tra nâng cấp trong CI |
| `supabase/migrations/202611050012_f1_contract_schema.sql` | **Generated Contract Schema Migration** | **BE-1** | **BE-4** | Chỉ được sinh tự động bằng `backend/scripts/generate_contract_schema_migration.py` khi `f1.schema.json` được duyệt thay đổi |
| `supabase/migrations/<new_timestamp>_*.sql` **`[PLANNED — Task/Window/Timezone/Schema]`** | New Domain/Schema Migrations | **BE-1** | **BE-2**, **BE-4** | Dành cho thay đổi schema Task, Timezone, Personalized Working Time hoặc RLS sau khi contract addendum được duyệt |
| `supabase/migrations/<new_timestamp>_*.sql` **`[PLANNED — Planning/Approval RPC]`** | New Planning/Approval Migrations | **BE-2** | **BE-1**, **BE-4** | Dành cho cập nhật RPC `get_scheduling_context`, `persist_plan_proposal`, `approve_study_plan`, `reject_study_plan` (phải phối hợp số thứ tự với `BE-1`) |
| `supabase/tests/03_foundation.sql` .. `13_wp2b5_workflow.sql` | pgTAP Tests (Foundation, Security, Tasks, Windows, Workflow) | **BE-1** | **BE-4** | Không làm yếu các kiểm tra trong `06_sol_rpc_boundary.sql` và `07_sol_internal_addendum.sql` |
| `supabase/tests/14_wp2c1_plan_reads.sql` .. `16_wp2c3_approve_reject_plan.sql`<br/>`supabase/tests_concurrency/**` | pgTAP Planning Tests & Real-PG Concurrency Suite | **BE-2** | **BE-1** | Kiểm thử đọc/lưu/duyệt lịch và 6 kịch bản đồng thời/rollback bằng `psycopg` |
| `supabase/config.toml`<br/>`supabase/seed.sql`<br/>`supabase/scripts/{inventory_demo,register_dev_key}.sql` | **Shared Supabase Config & Scripts** | **BE-1** | **BE-2**, **BE-4** | Không đưa dữ liệu thật hoặc secret thật vào `seed.sql` / `register_dev_key.sql` |

---

### 3.4. Nhóm Contracts, CI/CD, Root & Documentation (`contracts/`, `.github/`, `docs/`)

| Đường dẫn / Pattern (đã xác minh trên `7837050`) | Phân loại | Primary Owner | Co-Reviewers bắt buộc | Ghi chú & Ranh giới chỉnh sửa |
|---|---|---|---|---|
| `contracts/README.md`<br/>`contracts/APPROVAL.md`<br/>`contracts/CHANGELOG.md`<br/>`contracts/VALIDATION.md`<br/>`contracts/acceptance-cases.md`<br/>`contracts/openapi.yaml`<br/>`contracts/schemas/f1.schema.json`<br/>`contracts/service-contract.json`<br/>`contracts/data-contract.json`<br/>`contracts/check_contract.py`<br/>`contracts/examples/**` | **Protected Official Contract Package (`1.0.1`)** | **BE-4** (điều phối kỹ thuật) + **Domain Owner (`BE-1`/`BE-2`/`BE-3`)** | **Tất cả roles bị ảnh hưởng + Project Owner Approval** | **CẤM TỰ Ý SỬA.** Mọi thay đổi bắt buộc tuân thủ [`CONTRACT_CHANGE_PROTOCOL.md`](CONTRACT_CHANGE_PROTOCOL.md) |
| `docs/database/schema_F1.md`<br/>`schema_F1.md` *(bản ở root)*<br/>`docs/database/**` | **Protected Logical Schema (`v1.1`) & DB Docs** | **BE-1** | **BE-2**, **BE-4**, **Project Owner** | `docs/database/schema_F1.md` là nguồn chuẩn logic; không sửa nếu chưa qua quy trình thay đổi contract |
| `docs/team-coordination/**`<br/>`AGENTS.md`<br/>`CLAUDE.md` | **Multi-Agent Coordination Governance** | **BE-4** (điều phối) | **Project Owner** + các role liên quan | Cập nhật `TASK_BOARD.md` và `OPEN_DECISIONS.md` theo bằng chứng thực tế |
| `.github/workflows/f1-backend-tests.yml`<br/>`.github/workflows/database-tests.yml`<br/>`.gitignore`<br/>`.gitattributes`<br/>`.env.example` | **Protected Repo & CI Infrastructure** | **BE-4** | **BE-1**, **Project Owner** | Không làm yếu CI, không nới lỏng `.gitignore` làm lộ `.env*` hoặc `.claude/` |
| `worklogs/<github-username>.md` | Team Worklogs | Từng thành viên theo tên file | — | Ghi nhật ký công việc theo `worklogs/sample.md` |

---

## 4. Quy trình Xử lý Khi Cần Sửa File Ngoài Ownership (Escalation & Cross-Role Requests)

Nếu trong lúc thực hiện task, một agent phát hiện cần thay đổi file thuộc `Primary Owner` của vai trò khác:

1. **Dừng ngay việc tự sửa file đó** (không sửa "tiện tay" dù chỉ vài dòng).
2. **Kiểm tra xem có thể giải quyết trong ranh giới hiện tại không** (ví dụ dùng adapter/mapper ở tầng của mình).
3. **Nếu bắt buộc phải sửa ở module của role khác:**
   - Ghi nhận yêu cầu phụ thuộc vào báo cáo bàn giao ([`templates/WORK_HANDOFF_TEMPLATE.md`](templates/WORK_HANDOFF_TEMPLATE.md)) hoặc báo cáo xung đột ([`templates/CONFLICT_REPORT_TEMPLATE.md`](templates/CONFLICT_REPORT_TEMPLATE.md)).
   - Nêu rõ: (a) đường dẫn file cần sửa, (b) vai trò sở hữu (`Owner Role`), (c) chữ ký hàm/kiểu dữ liệu mong muốn, và (d) lý do kỹ thuật.
   - Đánh dấu phần phụ thuộc là `BLOCKED` trong [`TASK_BOARD.md`](TASK_BOARD.md) và chuyển cho `Owner Role` tương ứng (hoặc `BE-4` nếu là xung đột tích hợp liên miền).
