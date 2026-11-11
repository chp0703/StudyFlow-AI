# Hướng Dẫn Vai Trò `BE-1` — Database / Task Schema / Timezone / Working Time

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`BE-1`** |
| **Nhóm (Team)** | Backend (OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận Schema cơ sở dữ liệu, Mô hình dữ liệu Công việc (`TaskCandidate` / `AcademicTask`), Ngữ nghĩa & Chuyển đổi Múi giờ (`Asia/Ho_Chi_Minh`), và Lưu trữ/Kiểm tra `Personalized Working Time` (`TimeWindow` / `SchedulingPolicy`) |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) và [`docs/database/schema_F1.md`](../../database/schema_F1.md) (`v1.1`) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`BE-1` là chủ sở hữu kỹ thuật của **tầng Dữ liệu / Schema / Timezone / Working Time** trong miền F1:

1. **Task Schema, Data Model & Migrations Owner:** Quản lý mô hình dữ liệu và các ràng buộc toàn vẹn cho `User` (`app_private.user_profiles`), `TaskCandidate` (`app_private.task_candidates`), `AcademicTask` (`app_private.academic_tasks`), `TimeWindow` (`app_private.time_windows`), khóa ngoại cùng chủ sở hữu (`same-owner composite FKs`), RLS và quyền của `sf_rpc_owner`.
2. **Timezone Semantics & Conversion Owner:** Đảm bảo ngữ nghĩa thời gian và múi giờ sản phẩm (`Asia/Ho_Chi_Minh`), quy tắc `DATE` deadline cutoff (`00:00` đầu ngày kế tiếp theo `deadline_timezone`), quy tắc `WEEKLY` `end_time = 24:00`, và chuẩn hóa khung giờ trong `backend/app/f1/scheduler/normalization.py` & `intervals.py`.
3. **Personalized Working Time Persistence & Validation Owner:** Chủ trì lưu trữ và kiểm tra tính hợp lệ của `Personalized Working Time` (kết hợp `TimeWindow` và `SchedulingPolicy` theo quyết định `OD-003`), đồng thời **bảo toàn các khái niệm khoảng bận (`BUSY`) và kiểm tra xung đột nội bộ** mà bộ lập lịch (`BE-2`) cần.
4. **Schema / Data Contract Coordinator (trong phạm vi DB/Domain):** Phối hợp với `BE-2` về hợp đồng ràng buộc đầu vào cho Scheduler, phối hợp với `BE-4` về API/data contract, và cung cấp schema/types/fixtures chuẩn cho `FE-1` và `FE-2`.
   > **Lưu ý:** `BE-1` không phải là người duyệt mọi code trong toàn repo; `BE-1` chịu trách nhiệm điều phối schema/data contract trong phạm vi cơ sở dữ liệu và domain của mình.

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) & [`docs/team-coordination/README.md`](../README.md).
2. [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`ARCHITECTURE_AND_RUNTIME_RULES.md`](../ARCHITECTURE_AND_RUNTIME_RULES.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`docs/database/schema_F1.md`](../../database/schema_F1.md), [`docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md`](../../database/StudyFlow_AI_Database_Design_Baseline_v1.1.md), [`docs/database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md`](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md).
4. [`contracts/README.md`](../../../contracts/README.md) (mục 2, 5, 6, 7), [`contracts/data-contract.json`](../../../contracts/data-contract.json), [`contracts/service-contract.json`](../../../contracts/service-contract.json), [`contracts/schemas/f1.schema.json`](../../../contracts/schemas/f1.schema.json).
5. Ghi chú thực thi DB: [`docs/implementation/WP2_DATABASE.md`](../../implementation/WP2_DATABASE.md), [`WP2A_NOTES.md`](../../implementation/WP2A_NOTES.md), [`WP2B_NOTES.md`](../../implementation/WP2B_NOTES.md), [`WP2C_NOTES.md`](../../implementation/WP2C_NOTES.md).
6. Code & SQL thực tế:
   - `supabase/migrations/202611050001_*.sql` .. `202611050017_*.sql`, `202611050021_f1_wp2c4_window_warnings.sql`
   - `backend/scripts/generate_contract_schema_migration.py`
   - `backend/app/f1/scheduler/normalization.py` & `backend/app/f1/scheduler/intervals.py`
   - `supabase/tests/03_foundation.sql` .. `13_wp2b5_workflow.sql`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa / tạo trực tiếp (`Allowed Changes — Primary Owner`)
- Tạo migration mới trong `supabase/migrations/<new_timestamp>_*.sql` thuộc phạm vi schema thực thể, `TaskCandidate`, `AcademicTask`, `TimeWindow`, `User` (`user_profiles`), RLS/grants và các RPC `ensure_user_context`, `create_task_candidate`, `update_candidate_draft`, `confirm_task`, `search_tasks`, `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `list_time_windows`.
- `backend/scripts/generate_contract_schema_migration.py` và chạy script này để tái sinh `supabase/migrations/202611050012_f1_contract_schema.sql` **chỉ sau khi** thay đổi `contracts/schemas/f1.schema.json` đã được duyệt chính thức.
- `backend/app/f1/scheduler/normalization.py` & `backend/app/f1/scheduler/intervals.py`.
- `backend/app/f1/tasks/**` & `backend/app/f1/availability/**` (khi cần tách module kiểm tra domain).
- `backend/tests/unit/test_contract_schema_migration.py` & bổ sung test mới trong `supabase/tests/08`..`13_*.sql`.
- `supabase/config.toml`, `supabase/seed.sql`, `supabase/scripts/{inventory_demo,register_dev_key}.sql`.
- Tài liệu trong `docs/database/**` (khi cập nhật sau một quyết định đã được phê duyệt).

### 3.2. File dùng chung cần Co-Review (`Shared Files`)
- `contracts/data-contract.json`, `contracts/schemas/f1.schema.json`, `contracts/service-contract.json`, `contracts/examples/**` — Chỉ cập nhật trong khuôn khổ [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md) cùng `BE-4` và Project Owner.

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM TUYỆT ĐỐI** sửa các file migration lịch sử đã merge (`202611050001_*.sql` đến `202611050011_*.sql` và `202611050013_*.sql` đến `202611050021_*.sql`) vì sẽ làm hỏng kiểm tra nâng cấp từ `202611050008` trong `.github/workflows/database-tests.yml`. Mọi thay đổi SQL phải tạo file migration mới (`022+`).
- **CẤM** làm yếu assertion trong các file kiểm thử độc lập `supabase/tests/03`..`07_*.sql` và `backend/tests/acceptance_sol/test_normalization_contract.py`.
- **CẤM** tự ý sửa bộ lập lịch `backend/app/f1/scheduler/{engine,replanning,service,constraints}.py` hoặc `backend/app/f1/planning/generate.py` (thuộc `BE-2`).
- **CẤM** tự ý sửa `backend/app/nlu/*` (thuộc `BE-3`), `backend/app/orchestrator/*` / `backend/app/api/v1/*` (thuộc `BE-4`), hoặc bất kỳ file nào trong `frontend/**` (thuộc `FE-1`/`FE-2`).
- **CẤM** cấp quyền DML trực tiếp trên `app_private.*` cho `authenticated`/`anon` hoặc dùng `service_role` cho request người dùng.

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận quyết định chốt từ Project Owner cho `OD-001` (`priority` `0.1|0.5|1`, `color`, `duration`), `OD-002` (`start time` semantics), `OD-003` (`Personalized Working Time`), và `OD-005` (`Asia/Ho_Chi_Minh`).
- **Đầu ra bàn giao (Downstream):**
  - Cung cấp hợp đồng ràng buộc `TimeWindow` (working time + busy intervals) và các trường task đã chuẩn hóa cho **`BE-2`** (Scheduler / Proposal / Approval).
  - Cung cấp chữ ký RPC và schema validation cho **`BE-4`** (Orchestrator / API).
  - Cung cấp schema DTO và fixtures hợp lệ/không hợp lệ cho **`FE-1`** và **`FE-2`**.

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **BE1-001** | Phân tích tác động & đề xuất Contract Addendum cho các trường Task mới (`title`/`course_label` separation, `duration`, `priority` `0.1\|0.5\|1`, `color`, `description`, `start time`), bao gồm xử lý tương thích với `app_private.canonical_json` | `NEEDS_DECISION` (`OD-001`, `OD-002`) |
| **BE1-002** | Rà soát và đảm bảo ngữ nghĩa múi giờ `Asia/Ho_Chi_Minh`, `DATE` deadline cutoff và `WEEKLY` `24:00` trong `normalization.py`, `intervals.py` và các RPC DB | `IN_PROGRESS` (`OD-005`) |
| **BE1-003** | Thiết kế dữ liệu & quy tắc xác thực cho `Personalized Working Time` (giữ nguyên khả năng biểu diễn `BUSY`/conflict cho Scheduler của `BE-2`) | `NEEDS_DECISION` (`OD-003`) |
| **BE1-004** | Tạo migration mới (`022+`), cập nhật `012` qua generator script (nếu schema đổi) và kế hoạch kiểm thử replay + upgrade route | `BLOCKED` (chờ `INT-001`) |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `BE-1` bắt buộc chạy và ghi nhận kết quả thực tế:

```powershell
# 1. Kiểm tra tính đồng bộ của Contract & Schema Migration 012
python -B contracts/check_contract.py
python -B backend/scripts/generate_contract_schema_migration.py --check
python -B -m unittest discover -s backend/tests/unit -p test_contract_schema_migration.py -v

# 2. Kiểm tra chuẩn hóa TimeWindow và Intervals
python -B -m unittest discover -s backend/tests/acceptance_sol -p test_normalization_contract.py -v

# 3. Kiểm tra trên Supabase PostgreSQL local (khi có Docker + Supabase CLI)
supabase db reset --yes
supabase test db

# 4. Kiểm tra diff sạch
git diff --check
```

---

## 7. Tiêu chuẩn Hoàn thành & Checklist Bàn giao (Done Criteria & Handoff Checklist)

- [ ] Giữ nguyên bất biến khóa dòng `user_profiles FOR UPDATE`, kiểm tra idempotency hai lần, `sf_rpc_owner` (`NOLOGIN NOSUPERUSER NOBYPASSRLS`), `search_path = ''`, và `ENABLE / FORCE RLS`.
- [ ] Không sửa các migration lịch sử `001`–`021`; kiểm tra `upgrade route` từ `202611050008` khớp 100% với `clean replay`.
- [ ] Đảm bảo `BE-2` vẫn nhận đủ tập khoảng làm việc khả dụng (`AVAILABILITY`) và khoảng bận (`BUSY`) đã chuẩn hóa.
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md) và thông báo cho `BE-2`, `BE-4`, `FE-1`, `FE-2`.
