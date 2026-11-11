# Hướng Dẫn Vai Trò `BE-2` — Scheduler / Proposal / Approval

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`BE-2`** |
| **Nhóm (Team)** | Backend (OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận Bộ lập lịch tất định (`Scheduler`), Sinh đề xuất lịch (`Proposal Generation`), Ngữ nghĩa `FULL`/`PARTIAL`/`NONE`/`NO_CHANGE`, Kiểm tra lại tại thời điểm duyệt (`Approval-Time Validation`), và Giao dịch/Đồng thời (`Transaction & Concurrency`) |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) và [`docs/planner/scheduling_rules.md`](../../planner/scheduling_rules.md) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`BE-2` chịu trách nhiệm toàn bộ miền **Lập kế hoạch, Đề xuất lịch và Giao dịch Phê duyệt Lịch**:

1. **Scheduler Integration Owner:** Duy trì tính đúng đắn, tính tất định (determinism) và hiệu năng của `backend/app/f1/scheduler/` và adapter `backend/app/f1/planning/generate.py`.
2. **Result Semantics (`FULL` / `PARTIAL` / `NONE` / `NO_CHANGE`) & Unscheduled Feedback:** Đảm bảo tính toán chính xác độ phủ (`coverage`), danh sách công việc/thời lượng chưa xếp được (`unallocated_minutes` / `unscheduled duration`) kèm nguyên nhân/cảnh báo rõ ràng để `FE-1` hiển thị trên màn hình Confirmation Preview.
3. **Approval-Time Validation, Transaction & Concurrency Owner:** Chủ trì các RPC đọc ngữ cảnh lập lịch (`get_scheduling_context`), đọc lịch (`get_study_plan`), lưu đề xuất (`persist_plan_proposal`), duyệt lịch (`approve_study_plan`) và từ chối lịch (`reject_study_plan`), bao gồm việc kiểm tra lại toàn bộ điều kiện tại thời điểm duyệt, xử lý bền vững trạng thái `STALE`, giữ nguyên các khối lịch sử/khóa (`retained blocks`) và kiểm thử đồng thời/rollback (`supabase/tests_concurrency/`).

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) & [`docs/team-coordination/README.md`](../README.md).
2. [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`ARCHITECTURE_AND_RUNTIME_RULES.md`](../ARCHITECTURE_AND_RUNTIME_RULES.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`contracts/README.md`](../../../contracts/README.md) (mục 4.2, 5.2, 6.3, 7, 8) và [`contracts/acceptance-cases.md`](../../../contracts/acceptance-cases.md) (đặc biệt các ca `API-06`, `API-07`, `API-08`, `API-10`, `DB-02`, `DB-04`..`DB-10`, `DB-16`, `PLAN-01`..`PLAN-07`).
4. [`docs/planner/scheduling_rules.md`](../../planner/scheduling_rules.md), [`docs/planner/evaluation.md`](../../planner/evaluation.md), [`docs/implementation/F1_EXECUTION.md`](../../implementation/F1_EXECUTION.md) (mục WP1), [`docs/implementation/WP2_DATABASE.md`](../../implementation/WP2_DATABASE.md), [`docs/implementation/WP2C_NOTES.md`](../../implementation/WP2C_NOTES.md).
5. Code & SQL thực tế:
   - `backend/app/f1/planning/generate.py`
   - `backend/app/f1/scheduler/{models,constraints,engine,replanning,service,evaluation,__init__}.py`
   - `backend/scripts/evaluate_planner.py`
   - `supabase/migrations/202611050018_f1_wp2c1_plan_reads.sql` .. `202611050021_f1_wp2c4_window_warnings.sql`
   - `supabase/tests/14_wp2c1_plan_reads.sql` .. `16_wp2c3_approve_reject_plan.sql`
   - `supabase/tests_concurrency/{harness.py,test_transactions.py}`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa / tạo trực tiếp (`Allowed Changes — Primary Owner`)
- `backend/app/f1/planning/generate.py` & `backend/app/f1/planning/__init__.py`
- `backend/app/f1/scheduler/{models,constraints,engine,replanning,service,evaluation,__init__}.py`
- `backend/app/f1/approval/**` (nếu bổ sung helper kiểm tra phê duyệt ở tầng Python)
- `backend/scripts/evaluate_planner.py`
- `backend/tests/unit/f1/scheduler/**`
- Tạo migration mới trong `supabase/migrations/<new_timestamp>_*.sql` cho các RPC `get_scheduling_context`, `get_study_plan`, `persist_plan_proposal`, `approve_study_plan`, `reject_study_plan` (phối hợp thứ tự số hiệu với `BE-1`).
- `supabase/tests/14_wp2c1_plan_reads.sql` .. `16_wp2c3_approve_reject_plan.sql` và `supabase/tests_concurrency/**`.
- `docs/planner/{scheduling_rules,evaluation}.md`.

### 3.2. File dùng chung cần Co-Review (`Shared Files`)
- `backend/app/f1/scheduler/models.py` & `constraints.py` (cần `BE-1` co-review nếu chạm tới cấu trúc `Task` hoặc `TimeWindow`).
- `supabase/migrations/<new_timestamp>_*.sql` (cần `BE-1` co-review về khóa ngoại, quyền `sf_rpc_owner` và RLS).

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM** đưa I/O, truy vấn DB, gọi LLM hoặc lấy đồng hồ hệ thống ngầm vào trong `backend/app/f1/scheduler/` — engine phải giữ nguyên tính hàm thuần tất định.
- **CẤM** sửa các file migration lịch sử đã merge (`202611050001`..`202611050021`).
- **CẤM** xóa hoặc làm yếu bất kỳ assertion nào trong `backend/tests/acceptance_sol/` (`test_scheduler_contract.py`, `test_scheduler_review_regressions.py`, `test_normalization_contract.py`).
- **CẤM** tự ý sửa schema Task/TimeWindow của `BE-1`, parser/NLU của `BE-3`, HTTP/Orchestrator của `BE-4` hoặc code `frontend/**` của `FE-1`/`FE-2`.

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận các khoảng thời gian làm việc/bận đã chuẩn hóa (`normalize_time_windows`) và cấu trúc `AcademicTask` / `SchedulingPolicy` từ **`BE-1`** (`BE1-001`..`003`).
  - Nhận lời gọi từ `ActionProcessor.build_plan()` / `decide()` của **`BE-4`**.
- **Đầu ra bàn giao (Downstream):**
  - Cung cấp kết quả `PlanProposal` (gồm full snapshot `study_blocks`, `changes` diff, `coverage`, `warnings`, `unallocated_minutes`) và `StudyPlan` đã duyệt cho **`BE-4`** và **`FE-1`** (`FE1-004`).

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **BE2-001** | Đảm bảo luồng kết quả `PARTIAL` / `NONE` / `NO_CHANGE` cung cấp đầy đủ thời lượng chưa xếp (`unscheduled duration` / `unallocated_minutes`), danh sách task bị thiếu thời gian và cảnh báo cho `FE-1`; cập nhật trọng số `priority` nếu `OD-001` được duyệt | `IN_PROGRESS` |
| **BE2-002** | Hoàn thiện kiểm tra lại tại thời điểm duyệt (`approve_study_plan` revalidation) theo `contracts/README.md` mục 7 và giải quyết các giới hạn còn ghi trong [`WP2C_NOTES.md`](../../implementation/WP2C_NOTES.md) (kiểm tra block mới đối chiếu với khung giờ làm việc/bận hiện hành và thời điểm `now`, bảo toàn trạng thái `STALE` bền vững khi phát hiện lệch revision/base) | `IN_PROGRESS` |
| **BE2-003** | Chạy và cung cấp bằng chứng thực tế trên PostgreSQL cho bộ `supabase/tests_concurrency/` (6 kịch bản race/rollback/fencing) và pgTAP `14`–`16` | `IN_PROGRESS` |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `BE-2` bắt buộc chạy và ghi nhận kết quả thực tế:

```powershell
# 1. Chạy unit tests và independent acceptance tests của Scheduler
python -B -m unittest discover -s backend/tests/unit -t . -v
python -B -m unittest discover -s backend/tests/acceptance_sol -v

# 2. Chạy đánh giá tính tất định (5 tình huống x 100 lần)
python -B backend/scripts/evaluate_planner.py

# 3. Chạy kiểm thử HTTP contract liên quan tới planning/approval
python -B -m unittest discover -s backend/tests/acceptance_api_sol -p test_http_contract.py -v

# 4. Khi có Supabase PostgreSQL local, chạy pgTAP và bộ kiểm thử đồng thời (Concurrency)
supabase db reset --yes
supabase test db
python -B -m unittest discover -s supabase/tests_concurrency -v

# 5. Kiểm tra diff sạch
git diff --check
```

---

## 7. Tiêu chuẩn Hoàn thành & Checklist Bàn giao (Done Criteria & Handoff Checklist)

- [ ] Bảo toàn 100% các bất biến của Scheduler:
  - `remaining_minutes = retained_future + newly_scheduled + unallocated` (không tự giảm `remaining_minutes` khi xếp lịch hoặc khi thời gian trôi).
  - Giữ nguyên `block_id` logic cho các khối không đổi và bảo vệ các khối lịch sử/đã khóa/ngoài phạm vi.
  - Khối đang diễn ra (`active block`) yêu cầu làm rõ tiến độ trước khi tái phân bổ.
  - `NONE` không tạo proposal có thể duyệt; `NO_CHANGE` hoặc diff rỗng trả `READ / SchedulingReadData` (giữ `coverage = PARTIAL` nếu diff rỗng nhưng vẫn còn phần chưa xếp).
- [ ] Pass 33/33 `acceptance_sol`, 100% unit tests, `evaluate_planner.py` với 0 vi phạm ràng buộc cứng, và `tests_concurrency` 6/6 trên Postgres local.
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md) và thông báo cho `BE-1`, `BE-4`, `FE-1`.
