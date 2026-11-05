# Worklog — phkhoiit-1508

## 2026-11-02 — Thiết kế wireframe

**Mục tiêu:** thiết kế wireframe và prototype cho giao diện StudyFlow AI.

**Đã làm**

- Thiết kế wireframe 5 màn hình bằng Figma Make, kèm một số prototype.
- Thêm wireframe/prototype vào repo.
- Cấu hình Git LFS cho các ảnh (png/jpg/gif/ico) trong `frontend/public/brand`.

**Kết quả:** PR #2 (`feat/frontend`) — commit "add wireframes and some prototypes" và "configure Git LFS for image assets".

**Ghi chú**

- Ảnh nhị phân được lưu qua Git LFS, cần `git lfs` khi clone.

## 2026-11-04 — Tổ chức lại cấu trúc frontend

**Mục tiêu:** chia `frontend/src` gọn gàng thành các thư mục và xóa mock data/demo.

**Đã làm**

- Tách `App.tsx` (2117 dòng) thành `pages/` (Dashboard, Planner, Study), `components/ui/` (Button, Card, Modal), `types/`, `utils/date.ts`; `App.tsx` chỉ còn phần khung (~250 dòng).
- Chuyển trợ lý AI vào `features/assistant/` (Assistant, assistantService, conversationHistory + test); đổi tên `assistantDemo` → `assistantService`.
- Chuyển CSS vào `styles/`, cập nhật import trong `main.tsx`.
- Xóa mock data: task/deadline/sự kiện lịch mẫu, số liệu thống kê giả, tài liệu và quiz mẫu, đề xuất kế hoạch AI cố định; xóa trang Review và Materials (không có mục menu dẫn tới).
- Các trang hiển thị trạng thái rỗng; danh sách deadline tính từ task thật.
- Cập nhật `DESIGN.md`, `README.md` theo đường dẫn mới.

**Kết quả:** PR #6 (`refactor/frontend-structure`). `tsc --noEmit` và `npm run build` pass; test `conversationHistory` 5/5 pass.

**Ghi chú**

- Giữ nguyên giá trị `demo_acknowledged` / `valid_demo_draft` vì đã lưu trong IndexedDB.
- `getAssistantReply` vẫn là stub theo kịch bản, chưa nối AI thật.

## 2026-11-05 — Backend F1: sửa hợp đồng 1.0.1 và WP2a (biên DB)

**Mục tiêu:** tiếp nhận bàn giao backend F1 trên `feat/f1-mvp-intergration`, chốt WP0 (hợp đồng) và làm WP2a (ranh giới bảo mật, hạ tầng, bộ xác minh) để chuẩn bị WP2b.

**Đã làm**

- WP0: sửa `contracts/schemas/f1.schema.json` (kết quả `READ` dùng `anyOf`; `WorkflowStepOutcome` bắt `result` khớp schema của đúng operation); cập nhật `contracts/CHANGELOG.md` và `contracts/VALIDATION.md`.
- WP2a: migration 009 (role `sf_rpc_owner`, 6 bảng hạ tầng, FORCE RLS), 010 (`canonical_json`, `verify_rpc_request`), 011 (gỡ RPC cũ, chuyển quyền sang `sf_rpc_owner`, 27 wrapper từ chối an toàn), 012 (schema hợp đồng sinh tự động bằng `backend/scripts/generate_contract_schema_migration.py`).
- Thêm `supabase/tests/08_wp2a_contract_schema.sql`, `backend/tests/unit/test_contract_schema_migration.py` và `docs/implementation/WP2A_NOTES.md`.
- Cài Docker Desktop, Supabase CLI 3.0.0 và Python 3.12 để chạy DB local.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. Checker hợp đồng pass (122 định nghĩa, 100 fixture), test hợp đồng 16/16; scheduler 33, unit 25, tests 78 pass. pgTAP local: 03, 04, 05, 08 pass; 06 còn 12/81 lỗi, 07 còn 33/58 lỗi (đều thuộc WP2b); kết quả giống nhau khi replay từ DB trống và khi nâng cấp từ baseline 008.

**Ghi chú**

- Wrapper mới chỉ kiểm tra request rồi trả `UNSUPPORTED_OPERATION`; hành vi nghiệp vụ làm ở WP2b/WP2c.
- Chưa chạy: harness đồng thời, JWT thật qua HTTP, CI mới. Chưa đụng tới project Supabase trên cloud.

## 2026-11-05 — Backend F1: WP2b-1 (bootstrap, tin nhắn nguồn, biên nhận)

**Mục tiêu:** chia WP2b thành các giai đoạn nhỏ; giai đoạn 2b-1 làm helper dùng chung, bootstrap, ghi tin nhắn nguồn và vòng đời lease của API receipt.

**Đã làm**

- Migration 013: helper `precheck/lock_owner/ok_result/failure`; `ensure_user_context`, `record_source_message`, `claim/renew/release/complete_api_receipt` thay cho wrapper từ chối an toàn; bỏ hai FK của receipt (ID được cấp trước khi message/action tồn tại).
- Thêm `supabase/tests/09_wp2b1_receipts_messages.sql` (22 kiểm tra: lease 120 giây, reclaim, fencing, 503 không chốt, replay, ràng buộc tin nhắn) và `docs/implementation/WP2B_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. pgTAP local: 03, 04, 05, 08, 09 pass; 06 còn 10/81 lỗi, 07 còn 24/58 lỗi (thuộc 2b-2 đến 2b-5).

**Ghi chú**

- Chưa chạy: chờ lease 120 giây thật, harness đồng thời, CI mới.

## 2026-11-05 — Backend F1: WP2b-2 (ứng viên công việc, idempotency miền)

**Mục tiêu:** giai đoạn 2b-2: tạo/sửa ứng viên công việc, idempotency miền và tra cứu kết quả đã lưu.

**Đã làm**

- Migration 014: `create_task_candidate` (tra cứu nhanh, khóa owner, tra lại, ghi cùng bản ghi idempotency lưu 7 ngày), `update_candidate_draft` (CAS theo version, replay an toàn), `lookup_operation_result`.
- Thêm `supabase/tests/10_wp2b2_candidates_idempotency.sql` (21 kiểm tra) và cập nhật `docs/implementation/WP2B_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. pgTAP local: 03, 04, 05, 06 (xanh hoàn toàn), 08, 09, 10 pass; 07 còn 24/58 lỗi (giờ rảnh/bận và workflow, thuộc 2b-4/2b-5).

**Ghi chú**

- Chưa thêm FK từ `task_candidates.source_message_id` để không làm hỏng dữ liệu cũ khi nâng cấp; ràng buộc kiểm ở tầng wrapper.

## 2026-11-05 — Backend F1: WP2b-3 (hành động chờ duyệt, xác nhận công việc, tìm kiếm)

**Mục tiêu:** giai đoạn 2b-3: bản trình bày do server cấp, xác nhận công việc nguyên tử và tìm kiếm có phân trang.

**Đã làm**

- Migration 015: `prepare/review/cancel_pending_action` (bản trình bày kèm digest, một hành động chờ cho mỗi hội thoại bằng unique index), `confirm_task` (ApprovalAction + AcademicTask + backlink + hoàn tất action + tăng `schedule_revision` + idempotency trong một giao dịch), `search_tasks` (keyset, cursor ký, ràng buộc owner/bộ lọc); sửa trigger đích duyệt dùng `current_uid()`.
- Thêm `supabase/tests/11_wp2b3_actions_confirm_search.sql` (47 kiểm tra) và cập nhật `docs/implementation/WP2B_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. pgTAP local: 03, 04, 05, 06, 08, 09, 10, 11 pass; 07 còn 24/58 lỗi (giờ rảnh/bận và workflow, thuộc 2b-4/2b-5).

**Ghi chú**

- Hành động thứ hai trong cùng hội thoại trả `ACTION_REVIEW_REQUIRED` (hợp đồng chưa có mã riêng); cần nhóm xác nhận.
- Cursor dùng khóa dẫn xuất từ khóa attestation đang hoạt động nên đổi khóa sẽ làm cursor đang mở mất hiệu lực.

## 2026-11-05 — Backend F1: WP2b-4 (giờ rảnh/bận, preferences, danh sách khung giờ)

**Mục tiêu:** giai đoạn 2b-4: ghi giờ rảnh/bận và policy qua phê duyệt gắn với PendingAction.

**Đã làm**

- Migration 016: `set_availability`, `set_busy_interval` (ADD/UPDATE/ARCHIVE, kiểm tra múi giờ, phút nguyên, một ngày địa phương, 24:00), `set_scheduling_preferences` (gộp patch vào policy đầy đủ, kiểm tra revision), `list_time_windows` (keyset, cursor ký); phê duyệt chỉ hợp lệ khi lệnh khớp đúng `normalized_command` đã trình bày.
- Thêm `supabase/tests/12_wp2b4_windows_preferences.sql` (33 kiểm tra) và cập nhật `docs/implementation/WP2B_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. pgTAP local: 03, 04, 05, 06, 08, 09, 10, 11, 12 pass; 07 còn 22/58 lỗi (workflow, thuộc 2b-5).

**Ghi chú**

- Chưa có cảnh báo "lịch đã duyệt bị ảnh hưởng" khi đổi khung giờ; làm ở WP2c khi đã có plan/block trong snapshot.


## 2026-11-05 — Backend F1: WP2b-5 (workflow context và continuation)

**Mục tiêu:** giai đoạn 2b-5, hoàn tất WP2b: đọc ngữ cảnh workflow và hàng đợi continuation bền vững.

**Đã làm**

- Migration 017: `get_workflow_context`, `get_workflow_continuation`, `initialize_workflow_continuation` (ghi lần đầu thắng, cần receipt gốc còn lease, một hàng đợi chưa xong cho mỗi hội thoại), `checkpoint_workflow_continuation` (WAIT/ADVANCE, CAS theo version và cursor, step key dẫn xuất, quy tắc phụ thuộc, bằng chứng action hoàn tất cho thao tác ghi cần duyệt).
- Thêm `supabase/tests/13_wp2b5_workflow.sql` (17 kiểm tra) và cập nhật `docs/implementation/WP2B_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. pgTAP local: toàn bộ 11 suite pass (404 kiểm tra), kể cả 07 (58/58).

**Ghi chú**

- Với thao tác ghi cần duyệt, hệ thống mới kiểm tra action đã COMPLETED, chưa đối chiếu lại payload kết quả với dữ liệu đã lưu.
- Hàng đợi thứ hai trong một hội thoại trả `STALE_ENTITY_VERSION` (hợp đồng chưa có mã riêng).

## 2026-11-05 — Backend F1: WP2c-1 (đọc ngữ cảnh lập lịch và kế hoạch)

**Mục tiêu:** giai đoạn đầu của WP2c, phần đọc của lập kế hoạch.

**Đã làm**

- Migration 018: `get_scheduling_context` (snapshot của owner: task, khung giờ đang dùng, kế hoạch nền đầy đủ, `schedule_revision`) và `get_study_plan` (CURRENT/HISTORY/PROPOSAL, lọc block theo khoảng thời gian nhưng giữ nguyên metadata kế hoạch).
- Thêm `supabase/tests/14_wp2c1_plan_reads.sql` (15 kiểm tra, có đối chiếu hợp đồng) và `docs/implementation/WP2C_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`; pgTAP local pass.

**Ghi chú**

- Snapshot hiện chạy nhiều câu lệnh dưới READ COMMITTED; nếu cần nhất quán tuyệt đối thì khóa owner hoặc dùng REPEATABLE READ ở tầng HTTP.
