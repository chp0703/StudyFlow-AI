# Nguồn Sự Thật Dự Án & Phân Xử Mâu Thuẫn (Project Source of Truth)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Xác lập thứ tự ưu tiên của mọi tài liệu/artifact trong repo, định nghĩa phạm vi và các bất biến nghiệp vụ của F1, đồng thời giải quyết các mâu thuẫn lịch sử giữa các tài liệu hiện có |
| **Thẩm quyền (Authority)** | Tài liệu phân xử cấp cao nhất trong `docs/team-coordination/`; mọi role guide và task spec phải tuân theo thứ tự ưu tiên tại đây |
| **Chủ sở hữu (Owner)** | Project Owner (phạm vi sản phẩm) · `BE-1` (logical schema) · `BE-4` (điều phối contract) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Định danh Dự án & Phạm vi Hiện hành

| Hạng mục | Nội dung chuẩn |
|---|---|
| **Tên dự án** | **StudyFlow-AI** — Intelligent Academic Learning Planner |
| **Phạm vi phát hành hiện tại** | **F1 (Initial Release / MVP): Intelligent Academic Planner** — Tạo và làm rõ `TaskCandidate`, xác nhận thành `AcademicTask`, quản lý khung giờ (`TimeWindow`) và cấu hình lập lịch (`SchedulingPolicy`), sinh đề xuất lịch (`PlanProposal`) bằng bộ lập lịch tất định, duyệt/từ chối để tạo snapshot `StudyPlan` + `StudyBlock` bất biến |
| **Ngoài phạm vi hiện tại (Out-of-Scope)** | **F2** (Learning Assessment & Adaptive Revision) và **F3** (Daily AI Learning / Quiz / Q&A tài liệu thật). Giao diện `frontend/src/pages/Study.tsx` hiện chỉ là bản mẫu (demo), **không** tự mở rộng thành backend F2/F3 |
| **Hợp đồng tích hợp chính thức** | **Unified F1 Integration Contract — Package `1.0.1` (`APPROVED`)**, hiệu lực ngày 05/11/2026 (`Asia/Ho_Chi_Minh`), bao phủ 8 HTTP endpoints công khai, 10 domain/LLM operations, 18 internal RPC interfaces và 5 infrastructure records ([`contracts/README.md`](../../contracts/README.md), [`contracts/APPROVAL.md`](../../contracts/APPROVAL.md)) |
| **Nguồn chuẩn Schema Logic** | **Logical Schema F1 v1.1** (`schema_version: "1.1"`) tại [`docs/database/schema_F1.md`](../database/schema_F1.md) |
| **Kiến trúc kỹ thuật hiện hành** | **Supabase PostgreSQL** (`app_private` / `app_api` + RLS + SECURITY DEFINER wrappers có kiểm soát) + **FastAPI** (JWT ES256 verification + HMAC-SHA256 RPC signing + durable orchestrator) + **DeepSeek API** (server-side NLU extraction) + **React 19 / Vite 8 / TypeScript / Tailwind CSS v4** (hỗ trợ chế độ Demo và chế độ API) |

---

## 2. Các Bất biến Nghiệp vụ & Bảo mật Cốt lõi (Core Invariants)

Mọi agent (`FE-1`, `FE-2`, `BE-1`, `BE-2`, `BE-3`, `BE-4`) phải bảo toàn tuyệt đối các bất biến sau:

1. **Đầu ra LLM và dữ liệu tệp là không tin cậy (`Untrusted Input`):**
   - Kết quả từ DeepSeek (`ExtractionResult`) hoặc dữ liệu trích xuất từ tệp tải lên chỉ là gợi ý nháp.
   - Không bao giờ lấy `user_id`, quyền sở hữu, `ApprovalAction`, `requires_review`, kết quả lập lịch hay chữ ký xác thực từ LLM hoặc từ request của client.
2. **Định danh và quyền sở hữu (`Owner Isolation`):**
   - `user_id` chỉ được trích xuất từ Supabase access JWT đã xác minh chữ ký (`auth.uid()` / `app_private.current_uid()`).
   - Mọi bảng nghiệp vụ dùng khóa ngoại cùng chủ sở hữu (`same-owner composite FK`); truy cập chéo người dùng bị chặn ở cả tầng RPC và RLS (trả về `404 ENTITY_NOT_FOUND` hoặc `403 FORBIDDEN`, không tiết lộ sự tồn tại của dữ liệu người khác).
3. **Bộ lập lịch tất định và tách biệt (`Pure Deterministic Scheduler`):**
   - Engine trong `backend/app/f1/scheduler/` là hàm thuần: không gọi DB, không gọi LLM, không tự cấp UUID đề xuất và không tự commit lịch.
   - Cùng một `SchedulingContext` đầu vào phải luôn cho ra cùng một `SchedulingResult`.
4. **Chu trình Đề xuất → Phê duyệt rõ ràng → Kiểm tra lại → Commit (`Proposal → Explicit Approval → Revalidation → Commit`):**
   - Không có thao tác ghi nghiệp vụ nào (`AcademicTask`, `TimeWindow`, `SchedulingPolicy`, `StudyPlan`) được thực thi trực tiếp từ văn bản chat hoặc từ tệp tải lên mà không qua bước tạo `PendingAction` / `ActionPresentation` và nhận quyết định `APPROVE` tường minh qua `POST /v1/decisions` kèm đúng `ActionReference`.
   - Khi duyệt `PlanProposal`, hệ thống phải khóa dòng hồ sơ chủ sở hữu (`SELECT ... FOR UPDATE` trên `user_profiles`), đối chiếu lại `base_plan_id`, `base_plan_version`, `schedule_revision` và các ràng buộc trước khi ghi nguyên tử (`atomic commit`).
5. **Bất biến Snapshot, Lịch sử, Idempotency và Tiến độ:**
   - Mỗi người dùng có tối đa một kế hoạch hiện hành (`current_plan_id`); mỗi lần duyệt tạo một `StudyPlan` version mới (`version = previous + 1`) và giữ nguyên các snapshot lịch sử (cấm `UPDATE`/`DELETE` lịch sử).
   - Khóa chính của khối học là `(plan_id, block_id)`; **cấm** đặt `UNIQUE(user_id, block_id)` toàn cục để bảo toàn định danh logic `block_id` của các khối được giữ lại qua nhiều lần lập lịch lại.
   - Công thức bảo toàn thời lượng: `remaining_minutes = retained_future_minutes + newly_scheduled_minutes + unallocated_minutes`. Việc xếp lịch hoặc thời gian trôi qua **không** tự động trừ `remaining_minutes` hay đánh dấu hoàn thành task.
   - `TaskCandidate`, `PendingAction` và `PlanProposal` **không có TTL sản phẩm** (không tự hết hạn sau 24h); chỉ `IdempotencyRecord` và `api_request_receipts` / `workflow_continuations` có thời hạn lưu giữ vận hành (tối thiểu 7 ngày cho replay, 120 giây cho lease đang chạy, 60 giây cho chữ ký vận chuyển HMAC).
6. **Ngữ nghĩa thời gian và Múi giờ (`Time & Timezone Semantics`):**
   - Mọi khoảng thời gian là nửa mở `[start_at, end_at)` với `end_at > start_at`, căn chỉnh theo phút (`second = 0`).
   - API trao đổi timestamp RFC 3339 có offset hoặc `Z`; DB lưu `timestamptz` (UTC) kèm trường tên múi giờ IANA riêng (mặc định sản phẩm: `Asia/Ho_Chi_Minh`).
   - Giờ địa phương `24:00` chỉ hợp lệ cho `end_time` của khung giờ lặp `WEEKLY` (tương ứng `00:00` ngày kế tiếp khi mở rộng thành khoảng cụ thể; không bao giờ xuất timestamp `T24:00`).
   - Deadline kiểu `DATE` có thời điểm cắt (`cutoff`) là `00:00` đầu ngày kế tiếp theo `deadline_timezone`.

---

## 3. Thứ tự Ưu tiên Nguồn Sự Thật (Hierarchy of Authority)

Khi có sự khác biệt giữa các tài liệu hoặc code trong repo, các agent bắt buộc phân xử theo thứ tự ưu tiên từ **1 (cao nhất)** đến **9 (thấp nhất)**:

| Cấp | Nguồn sự thật | Đường dẫn chính | Phạm vi thẩm quyền |
|---|---|---|---|
| **1** | **Quyết định mới nhất được Project Owner phê duyệt rõ ràng** | Ghi nhận trong [`contracts/APPROVAL.md`](../../contracts/APPROVAL.md) hoặc Decision Record đã chuyển trạng thái `APPROVED` | Quyết định phạm vi sản phẩm và phê duyệt thay đổi contract |
| **2** | **Bộ Hợp đồng Tích hợp Chính thức (`Package 1.0.1 — APPROVED`)** | [`contracts/README.md`](../../contracts/README.md), [`contracts/APPROVAL.md`](../../contracts/APPROVAL.md), [`contracts/CHANGELOG.md`](../../contracts/CHANGELOG.md), [`contracts/openapi.yaml`](../../contracts/openapi.yaml), [`contracts/schemas/f1.schema.json`](../../contracts/schemas/f1.schema.json), [`contracts/service-contract.json`](../../contracts/service-contract.json), [`contracts/data-contract.json`](../../contracts/data-contract.json), [`contracts/examples/`](../../contracts/examples/) | Chuẩn giao tiếp HTTP FE↔BE, chữ ký Service/Tool, danh mục 27 RPC, ánh xạ bảng/cột DB và các bất biến kiểm tra tự động |
| **3** | **Logical Schema Chính thức (`F1 v1.1`)** | [`docs/database/schema_F1.md`](../database/schema_F1.md) | Ngữ nghĩa nghiệp vụ của 10 thực thể, vòng đời trạng thái, quy tắc thời gian và đầu vào/đầu ra logic của các operation |
| **4** | **Decision Register & ADR Kiến trúc đã duyệt** | [`docs/database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md`](../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), [`docs/architecture/decisions/ADR-001`..`ADR-005`](../architecture/decisions/ADR-001-database-and-backend-stack.md), [`docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md`](../database/StudyFlow_AI_Database_Design_Baseline_v1.1.md) | Các quyết định kiến trúc nền tảng (`E-01`..`E-15`, `IC-01`..`IC-08`) |
| **5** | **Source Code Runtime, Migrations & Kiểm thử trên `main` (`7837050`)** | `backend/app/`, `supabase/migrations/202611050001`..`0021`, `frontend/src/`, `backend/tests/`, `supabase/tests/`, `supabase/tests_concurrency/`, `.github/workflows/` | Bằng chứng thực tế về những gì đã được lập trình và kiểm thử tự động |
| **6** | **Bản đồ Code & Kiến trúc Runtime hiện hành** | [`docs/architecture/F1_File_Organization_Proposal.md`](../architecture/F1_File_Organization_Proposal.md) + [`ARCHITECTURE_AND_RUNTIME_RULES.md`](ARCHITECTURE_AND_RUNTIME_RULES.md) + [`frontend/DESIGN.md`](../../frontend/DESIGN.md) | Vị trí module, luồng gọi thực tế và quy ước UI sau khi đối chiếu với `main` @ `7837050` |
| **7** | **Ghi chú Thực thi theo Work Package (`WP Notes`)** | [`docs/implementation/WP2A_NOTES.md`](../implementation/WP2A_NOTES.md), [`WP2B_NOTES.md`](../implementation/WP2B_NOTES.md), [`WP2C_NOTES.md`](../implementation/WP2C_NOTES.md), [`WP4_NOTES.md`](../implementation/WP4_NOTES.md), [`WP0_CONTRACT_ADDENDUM.md`](../implementation/WP0_CONTRACT_ADDENDUM.md), [`WP2_DATABASE.md`](../implementation/WP2_DATABASE.md), [`WP3_API.md`](../implementation/WP3_API.md), [`WP4_WORKFLOW.md`](../implementation/WP4_WORKFLOW.md) | Chi tiết quyết định cài đặt và giới hạn đã biết của từng gói công việc |
| **8** | **Tài liệu Lịch sử / Bàn giao Điểm Cũ / README chưa cập nhật** | [`README.md`](../../README.md), [`frontend/README.md`](../../frontend/README.md), [`BAN_GIAO.md`](../../BAN_GIAO.md), [`HUONG_DAN_TIEP_NHAN_BANG_AI.md`](../../HUONG_DAN_TIEP_NHAN_BANG_AI.md), [`docs/handoff/*`](../handoff/CONTEXT.md), [`docs/implementation/F1_EXECUTION.md`](../implementation/F1_EXECUTION.md), [`docs/architecture/StudyFlow_AI_Repo_Structure.md`](../architecture/StudyFlow_AI_Repo_Structure.md), [`docs/srs/*`](../srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md) | Bối cảnh lịch sử tại thời điểm viết; **không dùng để phủ nhận code hoặc contract mới hơn** |
| **9** | **Ghi chú trao đổi (Chat Notes) & Định hướng Yêu cầu Mới** | 13 yêu cầu F1 mới được tổng hợp tại [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](PRODUCT_REQUIREMENTS_AND_DECISIONS.md) | Định hướng sản phẩm (`User-requested direction`); **chưa phải** contract/schema đã phê duyệt cho tới khi hoàn tất [`CONTRACT_CHANGE_PROTOCOL.md`](CONTRACT_CHANGE_PROTOCOL.md) |

---

## 4. Bảng Phân Xử Các Mâu Thuẫn Tài Liệu Đã Phát Hiện Khi Audit

Trong quá trình kiểm toán repository tại commit `7837050`, các mâu thuẫn sau giữa các tài liệu đã được ghi nhận và phân xử chính thức:

| Mã | Nguồn A | Nguồn B | Nội dung mâu thuẫn | Phạm vi ảnh hưởng | Quyết định phân xử chính thức |
|---|---|---|---|---|---|
| **CF-01** | [`README.md`](../../README.md) (dòng 6–8, 27, 76–77) và [`frontend/README.md`](../../frontend/README.md) | Code thực tế trên `main` (`7837050`), [`backend/README.md`](../../backend/README.md), [`frontend/DESIGN.md`](../../frontend/DESIGN.md) | `README.md` gốc và `frontend/README.md` vẫn ghi "Database migrations, authentication integration, persistence, HTTP APIs... are not yet implemented" và ghi contract `1.0.0`. Trong khi `main` đã có 21 migrations (`001`–`021`), FastAPI (`backend/app/main.py`), orchestrator, và frontend API client (`frontend/src/api/`). | Nhận thức của agent về hiện trạng repo | **Ưu tiên Nguồn B (Cấp 2, 5, 6):** Xem `README.md` gốc và `frontend/README.md` là mô tả lịch sử chưa cập nhật. Không kết luận repo chưa có backend/DB/API client; đồng thời không tự sửa `README.md` gốc khi chưa được giao task cập nhật README. |
| **CF-02** | [`contracts/README.md`](../../contracts/README.md) (dòng 9) & [`docs/database/schema_F1.md`](../database/schema_F1.md) (dòng 13) | [`contracts/CHANGELOG.md`](../../contracts/CHANGELOG.md), [`contracts/APPROVAL.md`](../../contracts/APPROVAL.md) và `main` @ `7837050` | `contracts/README.md` dòng 9 còn ghi "chưa có API handler, migration hoặc DB chạy thật" (ghi lúc đóng băng thiết kế 05/11); `schema_F1.md` dòng 13 còn viết chữ "1.0.0". | Phiên bản contract và trạng thái code | **Phân xử:** Phiên bản contract chính thức là **package `1.0.1`** (theo `APPROVAL.md`, `CHANGELOG.md`, `openapi.yaml`, `f1.schema.json`). Dòng trạng thái triển khai trong `contracts/README.md` chỉ phản ánh thời điểm ký duyệt thiết kế 05/11/2026, không phủ nhận code WP2/WP3/WP4 đã merge sau đó. |
| **CF-03** | [`docs/architecture/F1_File_Organization_Proposal.md`](../architecture/F1_File_Organization_Proposal.md) (Mục 1–3, viết ngày 07–09/11 trước PR #21) | Bảng đầu file `F1_File_Organization_Proposal.md` (PR #25–#29) và commit `7837050` (PR #21) | Mục 1 và Mục 3 của `F1_File_Organization_Proposal.md` ghi `frontend/src/api/` chỉ chứa `.gitkeep` và `api/v1/chat.py`, `workflow.py` còn giữ phần lớn logic. Tuy nhiên PR #25–#29 đã chuyển logic sang `backend/app/orchestrator/{chat,actions,receipts}.py` và PR #21 đã thêm đầy đủ `frontend/src/api/{client,endpoints,auth,mappers,types,pending,useServerData}.ts`. | Ownership và đường dẫn import của `BE-4`, `FE-1`, `FE-2` | **Phân xử:** Áp dụng bảng đầu mục "Bản đồ sau triển khai refactor ngày 09/11/2026" kết hợp trạng thái thực tế sau PR #21 (`7837050`) được tổng hợp tại [`ARCHITECTURE_AND_RUNTIME_RULES.md`](ARCHITECTURE_AND_RUNTIME_RULES.md) và [`FILE_OWNERSHIP.md`](FILE_OWNERSHIP.md). |
| **CF-04** | [`BAN_GIAO.md`](../../BAN_GIAO.md), [`HUONG_DAN_TIEP_NHAN_BANG_AI.md`](../../HUONG_DAN_TIEP_NHAN_BANG_AI.md), [`docs/handoff/*`](../handoff/CONTEXT.md), [`docs/implementation/F1_EXECUTION.md`](../implementation/F1_EXECUTION.md) | [`WP2A_NOTES.md`](../implementation/WP2A_NOTES.md), [`WP2B_NOTES.md`](../implementation/WP2B_NOTES.md), [`WP2C_NOTES.md`](../implementation/WP2C_NOTES.md), [`WP4_NOTES.md`](../implementation/WP4_NOTES.md) và lịch sử commit `main` (`7837050`) | Các file bàn giao ngày 05/11/2026 ghi WP0 đang fail 2 test, chưa có migration `009+` và chưa có `backend.app.main`. Thực tế các gói WP0, WP2a, WP2b, WP2c, WP3, WP4 và PR #20–#29 đã được hoàn tất và merge vào `main` ngày 09/11/2026. | Trạng thái Task Board và kế hoạch làm việc | **Phân xử:** Giữ nguyên các file bàn giao ngày 05/11 làm hồ sơ lịch sử; đọc trạng thái kỹ thuật hiện tại từ `WP2A/2B/2C/4_NOTES.md`, code trên `main` (`7837050`) và [`TASK_BOARD.md`](TASK_BOARD.md). |
| **CF-05** | `docs/database/schema_F1.md` | Root `schema_F1.md` | Tồn tại hai bản file `schema_F1.md` ở hai đường dẫn (`docs/database/schema_F1.md` và `/schema_F1.md`). | Đường dẫn tham chiếu schema logic | **Phân xử:** [`docs/database/schema_F1.md`](../database/schema_F1.md) là đường dẫn chuẩn chính thức được `contracts/README.md` và Decision Register tham chiếu. Không sửa lẻ một file làm lệch nội dung. |
| **CF-06** | `backend/app/orchestrator/{dispatcher,registry}.py` & `backend/app/services/{tasks,settings,plans,scheduling_policy}.py` | `backend/app/main.py` & `backend/app/orchestrator/{actions,chat,receipts}.py` | Cả hai nhóm đều nằm trong `backend/app/`, nhưng `create_app()` chỉ gọi `api/v1/routes.py` → `api/v1/workflow.py` → `orchestrator/{receipts,actions,chat}.py` → `clients/rpc.py`. Nhóm `dispatcher.py` và `services/*.py` dùng schema nháp (`validated_command.json`, `tool_result.json`) và chỉ được gọi bởi root `tests/`. | Tránh nhầm đường chạy chính khi sửa backend | **Phân xử:** Đường chạy runtime chính thức là `routes.py` → `workflow.py` → `orchestrator/{receipts,actions,chat}.py` → `f1/planning/generate.py` → `clients/rpc.py`. Không tự nối `services/*.py` nháp vào runtime nếu chưa có thiết kế adapter được duyệt; đồng thời không xóa chúng vì root `tests/` đang kiểm tra. |
| **CF-07** | [`docs/srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md`](../srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md) & [`docs/database/StudyFlow_AI_Physical_Database_Design_v1.0_DRAFT.md`](../database/StudyFlow_AI_Physical_Database_Design_v1.0_DRAFT.md) | [`contracts/README.md`](../../contracts/README.md) (`1.0.1`) & [`docs/database/schema_F1.md`](../database/schema_F1.md) (`v1.1`) | Bản SRS v1.0 Draft và Physical Design v1.0 Draft còn chứa khái niệm cũ (`course_id`, `user_settings`, `EXPIRED` state, TTL, manual block move, `StudySession`). | Ngữ nghĩa domain và tên bảng | **Phân xử:** Theo [`StudyFlow_AI_Phase_03_Implementation_Decision_Register.md`](../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md) (`E-06`, `E-12`), contract `1.0.1` và `schema_F1.md` v1.1 hoàn toàn thay thế các chi tiết cũ đó (dùng `course_label`, bảng `app_private.user_profiles`, bỏ `EXPIRED`/TTL, không hỗ trợ dời block thủ công trong F1 v1.1). |
| **CF-08** | 13 yêu cầu F1 mới của người dùng (xem Mục 5 bên dưới) | Contract `1.0.1` (`contracts/`) và Logical Schema `F1 v1.1` (`docs/database/schema_F1.md`) | Người dùng nêu các yêu cầu mới (priority `0.1, 0.5, 1`, `color`, `duration`, `start time`, bỏ Free Time trên UI thay bằng Personalized Working Time, upload image/calendar/document, từ chối audio...) khác với enum/field/scope của contract `1.0.1` hiện hành (`priority: LOW\|NORMAL\|HIGH`, `estimated_minutes`, `TimeWindow.kind: AVAILABILITY\|BUSY`, ngoài scope PDF/OCR). | Toàn bộ 6 vai trò `FE-1`, `FE-2`, `BE-1`..`BE-4` | **Phân xử:** Ghi nhận đầy đủ tại [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](PRODUCT_REQUIREMENTS_AND_DECISIONS.md) với nhãn `User-requested direction` và `Contract impact: NOT YET APPLIED`. **Không tự ý sửa contract 1.0.1 hoặc code phá vỡ contract 1.0.1** trước khi đề xuất thay đổi contract được duyệt theo [`CONTRACT_CHANGE_PROTOCOL.md`](CONTRACT_CHANGE_PROTOCOL.md). |

---

## 5. Tóm tắt 13 Yêu cầu F1 Mới từ Người dùng & Trạng thái Phê duyệt

Các yêu cầu dưới đây đã được người dùng nêu làm định hướng sản phẩm cho F1, nhưng **chưa được hợp thức hóa thành Contract Addendum trên nền Package 1.0.1 / Schema v1.1**. Chi tiết phân tích nằm tại [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](PRODUCT_REQUIREMENTS_AND_DECISIONS.md) và [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md):

1. **Task title tách biệt môn học:** `title` chỉ chứa tên công việc, không gộp tên môn học (hợp đồng hiện tại đã có `title` và `course_label` riêng, cần quy định rõ quy tắc hiển thị/nhập liệu và chuẩn hóa).
2. **Trường `duration`:** Cần làm rõ mối quan hệ ánh xạ với `estimated_minutes` / `remaining_minutes` trong `AcademicTask` và `TaskCandidate`.
3. **Giá trị `priority` là `0.1`, `0.5`, `1`:** Khác với enum `"LOW" | "NORMAL" | "HIGH"` trong `f1.schema.json` hiện tại → **Cần Contract Change Approval**.
4. **Trường `color` và `description`:** `description` đã có trong `AcademicTask`/`CandidateTaskFields`; `color` chưa có trong schema `v1.1` → **Cần Contract Change Approval**.
5. **Thông tin `start time`:** Phải chốt ngữ nghĩa domain (là `available_from_at` / thời điểm ưu tiên của task hay `start_at` của `StudyBlock` đã xếp lịch); tuyệt đối không tạo trường trùng lặp mơ hồ → **Đang ở `OPEN_DECISIONS.md` (`OD-002`)**.
6. **Timezone sản phẩm `Asia/Ho_Chi_Minh`:** Khớp với mặc định hiện tại của hệ thống, cần làm rõ xem có khóa cứng một múi giờ hay vẫn giữ hỗ trợ IANA timezone đa vùng ở tầng DB/contract.
7. **Bỏ "Free Time" trên trải nghiệm người dùng (user-facing UI):** Cần thay đổi nhãn/luồng nhập liệu trên UI mà không phá vỡ dữ liệu nền.
8. **Thay bằng "Personalized Working Time":** Cần chốt cách ánh xạ xuống `TimeWindow` (`kind = AVAILABILITY` + `BUSY` nội bộ) hoặc `SchedulingPolicy` để bộ lập lịch vẫn giữ được khái niệm khoảng bận/xung đột → **Đang ở `OPEN_DECISIONS.md` (`OD-003`)**.
9. **Confirmation hiển thị timetable/calendar preview, warnings và phần `unscheduled duration`:** Phù hợp với định hướng `ActionPresentation` / `PlanProposal` của contract `1.0.1`, cần hoàn thiện UI/UX trên `FE-1` và kiểm chứng dữ liệu từ `BE-2`.
10. **Sticky Date Header và hiển thị ngày cụ thể (`dd/MM` hoặc tương đương) cạnh/dưới thứ trong tuần (`weekday`):** Cải tiến hiển thị lịch tuần thuộc phạm vi `FE-1`.
11. **Upload chỉ gồm `image`, `calendar file` và `document`:** Mở rộng ngoài phạm vi v1.1 ban đầu (vốn để PDF/OCR ngoài scope) → **Cần Contract Change Approval (`OD-004`)**.
12. **Không hỗ trợ audio, voice note hoặc audio transcription:** Phải chặn ở cả client (`FE-2`) và kiểm tra/từ chối chặt ở server (`BE-3`).
13. **File extraction tạo candidate để người dùng review/correct/confirm trước khi chuyển vào Task Draft / Proposal / Approval flow:** Tuân thủ nguyên tắc bất biến "không tự động commit từ tệp".

---

## 6. Repo Này KHÔNG Phải Là Gì ("What This Repo Is NOT")

Để ngăn các AI coding agents suy diễn sai từ tài liệu hoặc tên thư mục, mọi agent phải ghi nhớ **5 điều KHÔNG**:

1. **Không phải mọi tài liệu trong repo đều mô tả runtime hiện tại:**
   - `docs/architecture/StudyFlow_AI_Repo_Structure.md` là cây thư mục mục tiêu lịch sử chuyển từ PDF.
   - `docs/srs/*` và `docs/database/*_v1.0_DRAFT.md` là bản nháp giai đoạn trước.
   - `BAN_GIAO.md` và `docs/handoff/*` là snapshot bàn giao ngày 05/11/2026 trước khi merge PR #20–#29 và PR #21.
2. **Không phải mọi thư mục có sẵn trong source tree đều đã có service hoạt động:**
   - Các thư mục chỉ có `.gitkeep` hoặc `__init__.py` (như `backend/app/domain/scheduling/`, `backend/app/f1/tasks/`, `backend/app/f1/availability/`, `backend/app/f1/approval/`, `backend/app/repositories/`, `backend/app/schemas/`, `backend/app/validation/`, `frontend/src/features/tasks/`, `frontend/src/features/schedule/`, `frontend/src/features/proposals/`, `frontend/src/features/availability/`, `frontend/src/features/chat/`) là **chỗ dành sẵn (placeholders)**, chưa có implementation runtime.
   - Các file `backend/app/services/*.py` và `backend/app/orchestrator/{dispatcher,registry}.py` là mã nháp giai đoạn TV2, chưa được gắn vào `backend/app/main.py:create_app()`.
3. **Không phải mọi bài test hoặc CI xanh đều chứng minh dịch vụ thật / trình duyệt thật đã chạy:**
   - `test_http_contract.py` dùng `httpx.MockTransport` giả lập RPC/JWKS, chỉ chứng minh tầng adapter HTTP của FastAPI.
   - `test_chat_local_supabase.py` dùng `ScriptedExtractor` trên Supabase local, **chưa chứng minh** DeepSeek API thật đã đạt ngưỡng `>= 38/40` trên tập câu tiếng Việt (`evaluate_nlu.py` với model thật vẫn ở trạng thái `NOT_RUN`).
   - Các bài test `*.test.ts` của frontend chạy trên Node (`node --test`), không thay thế kiểm thử E2E trên trình duyệt thật.
4. **Không phải phê duyệt contract (`APPROVED`) đồng nghĩa với hoàn tất nghiệm thu triển khai (`Deployment Acceptance`):**
   - Contract package `1.0.1` được duyệt nghĩa là giao diện và quy tắc đã chốt.
   - Toàn bộ 42 ca nghiệm thu tích hợp trong [`contracts/acceptance-cases.md`](../../contracts/acceptance-cases.md) và Gate `G3` (live demo trên Supabase project thật + DeepSeek thật) cần bằng chứng chạy thực tế trước khi tuyên bố hoàn thành.
5. **Không phải hành vi ở Chế độ Demo (`Demo Mode`) của Frontend là tích hợp Backend sống (`Live Integration`):**
   - Khi không cấu hình đủ `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, frontend chạy `assistantService.ts` và `plannerAgent.ts` bằng regex trong bộ nhớ.
   - Ngay cả ở Chế độ API (`API Mode` sau PR #21), trang `Study.tsx`, tính năng đính kèm tệp và một số thao tác biểu mẫu trực tiếp (`POST /v1/actions`) vẫn chưa được nối đầy đủ. Không được báo cáo tính năng mock/demo là đã tích hợp đầu cuối.
