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

## 2026-11-05 — Backend F1: WP2c-2 (lưu đề xuất kế hoạch)

**Mục tiêu:** giai đoạn 2c-2: `persist_plan_proposal`.

**Đã làm**

- Migration 019: lưu đề xuất do engine sinh sau khi DB tự kiểm tra lại phạm vi, policy hiệu lực, revision và kế hoạch nền (sai thì `STALE_PROPOSAL`), chủ sở hữu/chồng lấn/phạm vi của block; idempotency theo lệnh gốc nên retry với ID mới trả lại đề xuất đã lưu; không đổi `schedule_revision`.
- Thêm `supabase/tests/15_wp2c2_persist_proposal.sql` (17 kiểm tra) và cập nhật `docs/implementation/WP2C_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`; pgTAP local pass 13 bộ (436 kiểm tra).

**Ghi chú**

- Chưa kiểm tra block có tôn trọng giờ rảnh/bận, deadline, kích thước block (việc của engine); sẽ kiểm tra lại lúc duyệt ở 2c-3.

## 2026-11-05 — Backend F1: WP2c-3 (duyệt/từ chối kế hoạch)

**Mục tiêu:** giai đoạn 2c-3: `approve_study_plan`, `reject_study_plan`.

**Đã làm**

- Migration 020: duyệt tạo kế hoạch mới và block trong một giao dịch (approval, plan version+1, block, con trỏ plan hiện tại, `schedule_revision+1`, trạng thái proposal/action, idempotency); kiểm tra lại task/deadline/kích thước block; proposal lỗi thời được đánh dấu STALE bền vững; từ chối ghi approval REJECT và hủy action.
- Thêm `supabase/tests/16_wp2c3_approve_reject_plan.sql` (24 kiểm tra) và cập nhật `docs/implementation/WP2C_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`; pgTAP local pass.

**Ghi chú**

- Chưa kiểm tra lại giờ rảnh/bận lúc duyệt; dựa vào revision guard.

## 2026-11-05 — Backend F1: WP2c-4 (cảnh báo khi đổi khung giờ/policy)

**Mục tiêu:** giai đoạn 2c-4, trả nợ cảnh báo "block đã duyệt có thể bị ảnh hưởng".

**Đã làm**

- Migration 021: `set_availability`, `set_busy_interval`, `set_scheduling_preferences` trả cảnh báo `APPROVED_BLOCKS_MAY_BE_AFFECTED` kèm danh sách block tương lai của kế hoạch hiện tại; cảnh báo được lưu cùng kết quả idempotent.
- Mở rộng `supabase/tests/12_wp2b4_windows_preferences.sql` (5 kiểm tra mới) và `docs/implementation/WP2C_NOTES.md`.

**Kết quả:** nhánh `feat/f1-mvp-intergration`; pgTAP local pass 14 bộ (465 kiểm tra).

**Ghi chú**

- Cảnh báo thận trọng (liệt kê mọi block tương lai), chưa đối chiếu chính xác với khung giờ lặp.

## 2026-11-05 — Backend F1: WP2c-5 (kiểm thử đồng thời và CI)

**Mục tiêu:** chạy bộ kiểm thử đồng thời trên PostgreSQL thật và nối vào CI.

**Đã làm**

- Chạy `supabase/tests_concurrency` (6 kịch bản) trên Postgres local: 6/6 pass sau khi sửa một lỗ hổng mà bộ test phát hiện (lỗi STALE của `approve_study_plan` chưa được lưu làm kết quả idempotent nên retry cùng khóa trả thông báo khác); đã sửa trong migration 020.
- `database-tests.yml` thêm: kiểm tra migration schema hợp đồng được sinh (`--check`), so sánh đường nâng cấp với replay sạch (dump `app_private`/`app_api` giống nhau, đã xác minh local), và bộ kiểm thử đồng thời.

**Kết quả:** nhánh `feat/f1-mvp-intergration`; pgTAP local 14 bộ (465 kiểm tra) pass; concurrency 6/6.

**Ghi chú**

- Bộ concurrency cố ý để lại dữ liệu, cần `supabase db reset` trước khi chạy lại pgTAP. Các bước CI mới chưa chạy trên GitHub Actions.

## 2026-11-05 — Backend F1: WP3a (nền FastAPI: JWT, RPC ký, lỗi, CORS)

**Mục tiêu:** dựng lớp HTTP nền cho 8 endpoint theo hợp đồng, đạt bộ 30 test HTTP của Sol.

**Đã làm**

- `backend/app/main.py` (`create_app`, các transport và clock tiêm được), `core/config.py` (`Settings`), `core/security.py` (JWT/JWKS: thuật toán, kid, issuer, audience, hết hạn theo clock tiêm vào), `core/contract.py` (validate theo schema chuẩn, canonical JSON), `clients/rpc.py` (gọi `app_api.*` bằng JWT của chính người dùng, ký attestation HMAC 60 giây cho thao tác ghi), `api/v1/` (4 GET đọc, 4 POST có Idempotency-Key, giới hạn 64 KiB, envelope lỗi, request id do server cấp, CORS, replay receipt đã hoàn tất).
- `POST /v1/messages`, xử lý `actions/review/decisions` trả `UNSUPPORTED_OPERATION` cho tới bước sau (receipt được nhả lease).

**Kết quả:** 30/30 test HTTP của Sol pass (chỉ giả lập HTTP ngoài), 16 test addendum và test dịch vụ cũ vẫn pass.

**Ghi chú**

- Chưa chạy với Supabase thật qua HTTP (JWT thật/PostgREST): sẽ kiểm ở bước tích hợp.

## 2026-11-05 — Backend F1: WP3b (luồng có cấu trúc: tạo candidate → quyết định → đọc task)

**Mục tiêu:** `POST /v1/actions`, `/v1/actions/{id}/review`, `/v1/decisions` chạy thật trên DB, bền qua retry và restart.

**Đã làm**

- `backend/app/api/v1/workflow.py`: claim receipt → replay hoặc xử lý → complete; mọi bước DB dùng khóa dẫn xuất từ Idempotency-Key nên retry sau sự cố lặp lại đúng các bước và DB trả lại kết quả đã commit; lỗi tạm thời nhả lease, lỗi nghiệp vụ cuối cùng được lưu để replay. Hỗ trợ `create_task_candidate` (biểu mẫu thiếu trường thì hỏi lại, không lưu gì), `set_availability`, `set_busy_interval`, `set_scheduling_preferences` (trình bày policy hiệu lực đầy đủ), review, APPROVE/REJECT (`confirm_task`, thao tác cần duyệt, `approve/reject_study_plan` khi có proposal).
- `backend/tests/integration/test_http_local_supabase.py`: 5 test HTTP chạy trên Supabase local thật (token ES256 thật từ GoTrue, JWKS thật, PostgREST, RLS, attestation): replay, restart app, đổi body cùng khóa → conflict, người khác không quyết định được action của bạn (404), chốt chỉ một task, REJECT không lưu, đổi preferences cần quyết định. Đã thêm bước CI tương ứng.

**Kết quả:** 5/5 integration pass; 30/30 test HTTP của Sol vẫn pass.

**Ghi chú**

- `generate_study_plan` qua actions chưa có (cần engine + persist, bước tiếp theo); `POST /v1/messages` chưa có (cần DeepSeek).
- Hợp đồng không có kết quả "đã hủy"; hủy trả `SUCCEEDED` kèm presentation của action ở trạng thái CANCELLED, cần nhóm xác nhận.
- Dữ liệu của set_availability/busy chỉ được DB kiểm tra khi quyết định, chưa có dry-run lúc chuẩn bị.

## 2026-11-05 — Backend F1: WP3c (sinh kế hoạch qua HTTP với scheduler thật)

**Mục tiêu:** `generate_study_plan` qua `POST /v1/actions`: snapshot DB → scheduler thật → lưu đề xuất → chờ duyệt.

**Đã làm**

- `backend/app/f1/planning/generate.py`: chuyển snapshot hợp đồng thành `SchedulingContext` (mở rộng khung giờ lặp, tách block giữ lại/thay thế, phạm vi chọn task), chạy `PlanningService`, dựng `PlanProposal` đầy đủ; không có gì để đề xuất thì trả báo cáo `SchedulingReadData` (NO_CHANGE/NONE); block đang diễn ra của task được chọn trả `ACTIVE_BLOCK_REQUIRES_REVIEW`.
- `workflow.py`: bước `prepare_plan` (ensure → get_scheduling_context → engine → persist_plan_proposal với khóa dẫn xuất → pending action PLAN_PROPOSAL); quyết định APPROVE/REJECT dùng lại luồng sẵn có.
- Sửa migration 019/020: block giữ nguyên từ kế hoạch hiện tại (`is_base_plan_block`) được phép nằm ngoài cửa sổ/tập chọn và không bị kiểm tra lại với task khi duyệt.
- Thêm test tích hợp end-to-end: task → giờ rảnh → sinh kế hoạch → xem đề xuất → duyệt → đọc kế hoạch hiện tại → sinh lại cho NO_CHANGE.

**Kết quả:** integration 6/6 trên Supabase local thật, pgTAP 14 bộ (465 kiểm tra), test HTTP/unit/scheduler pass.

**Ghi chú**

- Chưa có replan khi có block active cần review qua HTTP (trả lỗi `ACTIVE_BLOCK_REQUIRES_REVIEW`), và chưa có endpoint review riêng cho trường hợp đó.

## 2026-11-05 — Backend F1: WP4 (luồng chat: trích xuất, hàng đợi bền vững, tiếp tục sau quyết định)

**Mục tiêu:** `POST /v1/messages` chạy trọn vòng: trích xuất → hàng đợi ý định bền vững → chuẩn bị ghi → chờ quyết định → tiếp tục.

**Đã làm**

- `backend/app/nlu/extractor.py` (DeepSeek JSON mode có kiểm schema, extractor kịch bản cho test, extractor "chưa cấu hình"), `backend/app/api/v1/chat.py` (hàng đợi bền vững, phụ thuộc, hỏi lại và gộp vào bản nháp, từ chối khi đang có thao tác chờ, tiếp tục sau `/v1/decisions`, tự sửa hàng đợi mồ côi), sửa `decide` để retry sau sự cố không bị chặn bởi trạng thái đã đổi.
- Tập đánh giá 40 câu tiếng Việt (`nlu_eval_vi.json`), bộ chấm điểm có test, script `evaluate_nlu.py` (cần khóa DeepSeek).
- 5 test tích hợp chat trên Supabase local thật; 4 test đơn vị cho extractor; 4 test cho bộ chấm.

**Kết quả:** integration 11/11, unit 33, HTTP Sol 30/30 pass.

**Ghi chú**

- **NOT_RUN:** đo thật 38/40 với DeepSeek (chưa có khóa); prompt là bản đầu.
- Chat chỉ ADD cửa sổ giờ; sửa/lưu trữ qua biểu mẫu. Chi tiết trong `docs/implementation/WP4_NOTES.md`.
## 2026-11-05 — Gộp trang chủ và làm lại Lập kế hoạch

**Mục tiêu:** gộp Trang chủ và Tổng quan thành một trang, và để người dùng chỉnh lịch bằng chat thay vì danh sách công việc.

**Đã làm**

- Gộp Trang chủ và Tổng quan: chat lớn ở trên, 3 thẻ (Công việc hôm nay, Deadline 5 ngày tới, Thời gian học) ở dưới; thẻ tự ẩn khi chat; đổi `pages/Dashboard.tsx` thành `components/HomeSummary.tsx`.
- Chat: thêm nút quay lại, tên cuộc trò chuyện ở giữa, panel lịch sử tự đóng khi chọn một đoạn chat, khung chat bo tròn như thẻ.
- Làm lại Lập kế hoạch: khung chat + lịch tuần vừa khít màn hình; thêm agent rule-based `features/planner/plannerAgent.ts` (thêm/dời/xóa) và test; `Task` có thêm `date`, `hour`.
- Bỏ thanh tìm kiếm công việc và phím tắt Ctrl/⌘+K.
- Tách `index.css` thành nhiều file trong `styles/`, xóa CSS không còn dùng (~200 selector), gộp còn 11 file (`tokens`, `base`, `overlays`, `overrides`, `planner`, `study`...) và viết lại `DESIGN.md`.
- Cập nhật trang Học tập (`pages/Study.tsx`, `styles/study-page.css`).
- Cài `gsap` và `@gsap/react`; thêm animation: thẻ trượt lên khi mở trang, tin nhắn chat, panel lịch sử co/giãn, chuyển tuần và sự kiện mới trong lịch, chữ chào trang chủ, đổi cuộc trò chuyện, chuyển câu và popup giải thích trong trắc nghiệm (`pages/Study.tsx`).
- Lập kế hoạch: đưa ô nhập yêu cầu lên hàng tiêu đề của thẻ Lịch (nút gửi nằm trong ô), hiện ngày `dd/mm/yyyy` thay cho "Tuần này", thu nhỏ hàng T2…CN và bỏ đường kẻ dưới tiêu đề.
- Nút gửi ở Lập kế hoạch và chat tài liệu chuyển xám khi ô trống, có màu khi đã nhập (giống trang chủ).
- Học tập: thông báo tải lên/xóa tài liệu hiện ngay trong thẻ Tài liệu thay cho toast toàn trang; bỏ prop `notify` của `Study`.
- Menu: nút mở lại luôn hiện cạnh logo khi thu gọn; thanh bên trượt ra/vào và nội dung giãn theo bằng GSAP (biến `--sb-offset`), các mục hiện lần lượt; khi kéo cửa sổ qua mốc responsive các thẻ dịch vào mượt.
- Chat trợ lý: cho đính kèm tệp/ảnh vào tin nhắn (hiển thị thẻ tệp và xem trước ảnh), `getAssistantReply` nhận thêm `attachments`, lịch sử lưu tên/dung lượng tệp và ảnh dạng `dataUrl` trong IndexedDB; thêm test cho `conversationHistory`.
- Cắt viền trắng quanh logo (`public/brand/`) và tăng kích thước logo trên thanh trên.
- Lập kế hoạch theo SRS F1: lệnh chat tạo đề xuất xem trước (viền nét đứt) rồi Duyệt/Từ chối, có kiểm tra lịch đã đổi (`STALE_PLAN_VERSION`) và hết hạn sau 10 phút (`EXPIRED`); thêm `types/planner.ts`, `features/planner/proposal.ts` và test.
- Khung giờ rảnh/bận trên lịch (lệnh `rảnh`/`bận`, bấm ô trống để điền sẵn lệnh, ngày `dd/mm`), chú thích màu kèm chữ.
- Bảng công việc bên phải lịch (`features/planner/TaskPanel.tsx`): tìm kiếm, lọc Nháp/Đã xác nhận/Chưa xếp và theo tuần, lệnh `tạo công việc … hạn …`; đóng/mở bằng GSAP.
- Lệnh `lập kế hoạch` tự xếp việc chưa xếp theo hạn nộp và ưu tiên, báo việc không vừa (`INSUFFICIENT_AVAILABILITY`); huy hiệu "Chờ duyệt" trên menu; cập nhật `DESIGN.md`.
- Chạy `npm run format` cho `TaskPanel.tsx` và `Planner.tsx`.
- Thêm skill `ui-ux-pro-max` vào `.claude/skills/` và quy tắc ghi worklog vào `CLAUDE.md`.

**Kết quả:** PR #13 (`feat/pages`). `tsc --noEmit`, `npm run build` và `npm run format` pass; test `plannerAgent`, `proposal` và `conversationHistory` pass. Review PR #11 (docs kiến trúc Supabase + FastAPI) dưới dạng nhận xét.

**Ghi chú**

- Agent chỉ hiểu lệnh đơn giản (chưa có phút, ngày cụ thể, "tuần sau"); phản hồi chat và tuần đang xem ở Lập kế hoạch reset khi đổi trang.
- Nút chuyển tuần cao 32px, nhỏ hơn mức 44px trong `DESIGN.md`; còn CSS cũ không dùng.
- Chưa kiểm tra giao diện điện thoại (~400px); drawer lịch sử trên điện thoại chưa có animation.
- Animation GSAP luôn chạy, không kiểm tra `prefers-reduced-motion` (quyết định của nhóm).
- Đề xuất, khung giờ rảnh/bận và việc chỉ lưu trong bộ nhớ (mất khi tải lại trang); thời hạn đề xuất 10 phút và khối 60 phút là giá trị đề xuất, SRS chưa chốt.

## 2026-11-05 — Bỏ hết hạn đề xuất theo schema F1 v1.1

**Mục tiêu:** đưa giao diện Lập kế hoạch về đúng hợp đồng `docs/database/schema_F1.md` v1.1, vốn đã bỏ `EXPIRED` và mọi TTL của đề xuất.

**Đã làm**

- Xóa đếm ngược 10 phút, mã `EXPIRED`, `isExpired`, `PROPOSAL_TTL_MS` và test liên quan (`pages/Planner.tsx`, `features/planner/proposal.ts`).
- Đổi thông báo `STALE_PLAN_VERSION` thành `STALE`.
- `DESIGN.md`: cập nhật mục đề xuất; ghi rõ lệnh thêm/dời/xóa khối thủ công nằm ngoài F1 v1.1.

**Kết quả:** nhánh `fix/remove-proposal-expiry`. `tsc --noEmit`, `npm run build` và test `features/planner` (9/9) pass.

**Ghi chú**

- Chưa xử lý các chỗ còn lệch v1.1: thẻ xác nhận công việc, nối chat với công việc, chia khối theo thời lượng, cấu hình lập lịch, lịch hiện hành/lịch sử.

## 2026-11-06 — Frontend F1: lớp API (nhánh feat/f1-frontend-integration)

**Mục tiêu:** bước 1 nối FE với BE: lớp gọi API có kiểu, tách khỏi giao diện.

**Đã làm**

- `frontend/src/api/`: `client.ts` (bearer token, `Idempotency-Key` cố định trước lần gửi đầu và giữ nguyên khi thử lại, lỗi theo catalog, thử lại một lần với lỗi tạm thời, bảng thông báo tiếng Việt), `endpoints.ts` (8 endpoint, tự lật trang), `types.ts` (kiểu DTO hợp đồng), `mappers.ts` (task → UI, khối học → sự kiện lịch, khung giờ lặp/một lần → ô rảnh/bận, đề xuất → bản xem trước lịch, presentation → tiêu đề và dòng chi tiết).
- `Task.id` đổi thành `string` (UUID từ server); cập nhật `plannerAgent`, `TaskPanel` và các test.
- Thêm `@supabase/supabase-js`; 15 test mới (client, mappers có dùng ví dụ hợp đồng).

**Kết quả:** `tsc` sạch; 30 test `node --test` pass (api + planner + assistant). Chưa đổi giao diện nào.

**Ghi chú**

- Giờ hiển thị theo múi giờ trình duyệt (mặc định backend là Asia/Ho_Chi_Minh).

## 2026-11-06 — Frontend F1: đăng nhập, Planner và Assistant chạy với API (chế độ API)

**Mục tiêu:** nối frontend với backend F1; vẫn giữ chế độ demo khi không cấu hình API.

**Đã làm**

- Chế độ API bật khi đặt đủ `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (xem `frontend/.env.example`); không đặt thì ứng dụng chạy như trước.
- Đăng nhập/đăng ký email + mật khẩu (`LoginPage`, supabase-js), khung tài khoản có đăng xuất; dữ liệu server (`useServerData`) cấp công việc, sự kiện lịch từ khối học, ô rảnh/bận và `schedule_revision` cho Trang chủ, Planner.
- Planner: chat gửi `POST /v1/messages`; đề xuất (công việc, giờ rảnh/bận, tùy chọn, kế hoạch) thành thanh Duyệt/Từ chối gọi `POST /v1/decisions` với `action_reference` nguyên vẹn; xem trước khối học trên lịch; tải lại trang vẫn dựng lại đề xuất đang chờ qua `/review`.
- Assistant: tin nhắn qua API, thẻ xác nhận/hủy thật, câu hỏi làm rõ, danh sách kết quả tìm kiếm; khóa đính kèm tệp ở chế độ API; sửa nhãn demo.
- Backend: `reject` một đề xuất đã STALE giờ hủy action đang chờ (trước đó hội thoại bị kẹt), có test tích hợp.
- Tài liệu: `frontend/DESIGN.md`, `backend/README.md` (cách chạy API cục bộ), `supabase/scripts/register_dev_key.sql`.

**Kết quả:** `tsc` sạch, build ok, 34 test `node --test` pass, 7 test tích hợp backend pass. Đã chạy trình duyệt thật (Puppeteer) trên Supabase local + API: đăng ký → chat thêm việc → duyệt → rảnh → lập kế hoạch → duyệt → tải lại vẫn còn; Assistant làm rõ → xác nhận → tìm kiếm; tải lại giữa chừng rồi "Xem lại bản nháp"; chế độ demo vẫn chạy.

**Ghi chú**

- Phần hiểu ngôn ngữ trong lần chạy trình duyệt là extractor kịch bản (chưa có khóa DeepSeek); chưa kiểm với DeepSeek thật.
- Lịch hiển thị 8h–17h theo giờ bắt đầu khối, múi giờ trình duyệt.

## 2026-11-12 — Refactor repository và chuẩn hóa tài liệu sản phẩm

**Mục tiêu:** loại bỏ mã/tài liệu legacy, làm rõ runtime hiện tại và mở rộng phạm vi tài liệu từ riêng Planner sang đầy đủ ba feature StudyFlow AI.

**Đã làm**

- Xóa handoff, proposal, draft, PDF trùng, cấu hình editor cá nhân và các package rỗng không còn sử dụng.
- Xóa dispatcher/service stack cùng root tests legacy; cập nhật backend CI sang runtime và acceptance suites hiện hành.
- Viết lại README, documentation index và architecture overview theo code đang chạy.
- Tổ chức tài liệu theo Product Requirements và ba feature: Intelligent Academic Planner, Learning Assessment & Adaptive Revision, Daily AI Learning.
- Đổi tài liệu schema/scheduler sang module Planner; giữ các tên kỹ thuật `F1` chỉ để tương thích contract, migration và package hiện tại.
- Hai file giao việc FE/BE từ feedback demo được giữ local và loại khỏi Git, không nằm trong branch.

**Kết quả:** nhánh `refactor/repository-cleanup`; contract checker pass (122 definitions, 100 fixtures), 41 backend unit tests pass, 33 scheduler acceptance tests pass, 46 API acceptance tests pass, planner evaluation pass và frontend production build pass.

**Ghi chú**

- Chưa chạy lại Supabase pgTAP/integration/concurrency trong lượt refactor này.
- Chưa push cloud migration hoặc thay đổi project Supabase dùng chung.

## 2026-11-12 — Hoàn tất repository cleanup và chia sẻ agent skills

**Mục tiêu:** hoàn tất dọn repository, loại tài liệu/placeholder không còn giá trị và đưa hướng dẫn dùng chung cho các coding agent vào Git.

**Đã làm**

- Xóa các `.gitkeep`, thư mục rỗng, metadata nhánh Supabase local, `backend/pyproject.toml` dư thừa và tài liệu acceptance cũ không còn được dùng.
- Xóa approval/changelog/validation/acceptance snapshot và các ADR cũ; gỡ toàn bộ metadata, link và mô tả còn trỏ tới các tài liệu đã xóa.
- Cập nhật `.gitignore` để bỏ qua metadata Supabase local nhưng cho phép commit chỉ dẫn và skills của agent.
- Thêm `AGENTS.md`, `CLAUDE.md`, `.agents/skills/` và `.claude/skills/`; ghi nguồn cài bắt buộc cho `ponytail`, `rtk`, `graphify`.

**Kết quả:** nhánh `refactor/repository-cleanup`; contract checker pass (122 definitions, 100 fixtures), generated contract migration đồng bộ, 41 backend unit tests, 33 scheduler acceptance tests, 46 API acceptance tests, 465 pgTAP tests, 12 integration tests, 6 concurrency tests và 34 frontend tests đều pass; TypeScript và production build pass; 47 Markdown files không có link tương đối hỏng; 18 skill packages validate thành công.

**Ghi chú**

- Không thay đổi workflow YAML và không chạm cloud Supabase project.
- `ponytail` chưa được cài trên máy hiện tại; repository cài đặt chính thức đã được ghi trong `AGENTS.md` cho từng thành viên tự bootstrap.

## 2026-11-13 — Làm lại trang đăng nhập và cải tiến trang Học tập

**Mục tiêu:** đưa vào `main` các thay đổi giao diện frontend đã làm dở trong một lần stash, tách khỏi các sửa backend để PR dễ review.

**Đã làm**

- Làm lại trang đăng nhập/đăng ký (`features/auth/LoginPage.tsx`, `styles/auth.css`) và cập nhật logo ngang nền trong suốt (tệp Git LFS).
- Trang Học tập (`pages/Study.tsx`, `styles/study.css`): làm lại câu trắc nghiệm đã sai, chỉ tính điểm cho lần trả lời đúng đầu tiên.
- `App.tsx`: đóng hộp thoại tài khoản khi phiên đăng nhập đổi hoặc khi đăng xuất.
- `styles/assistant.css`: chỉnh khoảng cách tiêu đề và ô nhập ở màn hình trống.

**Kết quả:** PR từ nhánh `feat/frontend-login-study-restyle`; TypeScript (`tsc --noEmit`) sạch và 34 frontend tests pass. Chưa chạy `npm run build` và `npm run format`.

**Ghi chú**

- Chưa kiểm tra bằng trình duyệt thật; cần xem lại trang đăng nhập và trang Học tập trước khi merge.
- Chưa kiểm tra tệp logo trong LFS có đủ trên máy.
- Không chồng lấn tệp với PR #32.

## 2026-11-15 — Đồng bộ main và hoàn thiện Planner follow-up

**Mục tiêu:** đưa backend/contract mới nhất vào PR #40, khôi phục build frontend và làm cho lịch hiển thị đúng ngữ nghĩa trên desktop, laptop và mobile.

**Đã làm**

- Merge `main`, giữ đầy đủ API ingestion và Planner; đồng bộ task mapper với `start_at`, priority số, color và description.
- Bổ sung helper resize composer, đổi lịch trục thời gian thành view **Tuần** mặc định, agenda thu gọn thành **Tổng quan**, và hiển thị đúng khoảng Thứ 2–Chủ nhật.
- Thêm layout theo chiều rộng vùng Planner; task panel chuyển xuống dưới khi hẹp, chỉ time-grid cuộn ngang.
- Cập nhật test và tài liệu Planner theo schema/view mới.

**Kết quả:** nhánh `fix/planner-followup-leader-spec-kent`; 71 frontend tests, TypeScript, production build, contract checker và generated schema check pass. Browser QA pass ở 1440×900, 1024×768 và 390×844, không có page overflow ngang.

**Ghi chú**

- Bundle frontend vẫn có cảnh báo chunk trên 500 kB; attachment UI vẫn display-only dù backend ingestion đã có.
- Chưa chạy authenticated ingestion/TimeWindow E2E hoặc Supabase reset; không chạm cloud project.

## 2026-11-15 — Tinh chỉnh lịch tuần Planner và form bổ sung thông tin công việc

**Mục tiêu:** đơn giản hóa giao diện lịch tuần Planner (1 cột giờ bên trái, nút cài đặt giờ dạng icon) và thay cảnh báo thiếu thông tin bằng popup/form đầy đủ trường công việc tự điền sẵn từ prompt trên cả Planner và Trang chủ.

**Đã làm**

- Lịch tuần Planner (`features/planner/WeekCalendar.tsx`, `CalendarDisplaySettings.tsx`, `pages/Planner.tsx`, `styles/planner.css`): giữ một cột giờ duy nhất bên trái, đưa cài đặt giờ hiển thị thành nút icon ở góc trên trái trục giờ, bỏ `CompactWeekCalendar` và các tài liệu nháp dư.
- Popup bổ sung thông tin Planner (`features/planner/clarification.ts`, `TaskClarificationFields.tsx`, `PlannerClarificationPopup.tsx`, `PlannerCommandComposer.tsx`, `usePlanner.ts`): mở popup bên phải ô nhập lệnh khi `NEEDS_CLARIFICATION` hoặc thiếu thông tin demo, hiển thị đủ các trường công việc (tên, thời gian bắt đầu, hạn, thời lượng, mức ưu tiên, màu sắc, mô tả), tự điền sẵn thông tin đã có trong prompt và cho phép chỉnh sửa.
- Trang chủ (`features/assistant/AssistantTaskClarificationForm.tsx`, `Assistant.tsx`, `ChatTranscript.tsx`, `apiAssistant.ts`, `types/assistant.ts`): áp dụng form đầy đủ trường công việc tự điền sẵn cho cả API mode (`NEEDS_CLARIFICATION`) và demo mode.
- Bổ sung và cập nhật test (`clarification.test.ts`, `WeekCalendar.test.ts`, `apiAssistant.test.ts`).

**Kết quả:** nhánh `fix/planner-followup-leader-spec-kent`; `contracts/check_contract.py` và `generate_contract_schema_migration.py --check` pass; frontend `tsc --noEmit`, `vite build` và 75/75 Node tests pass; `supabase db reset`, `supabase test db` (16 files, 504 tests) và backend pytest (176 unit/acceptance + 16 integration = 192 tests) pass.

## 2026-11-18 — Hướng dẫn chạy demo local

**Mục tiêu:** để thành viên khác dựng được demo trên máy mình mà không phải đoán các biến môi trường.

**Đã làm**

- Thêm `docs/local-demo.md`: các bước Supabase local, sinh và đăng ký khóa ký RPC, biến môi trường backend, `.env.local` frontend, tạo tài khoản.
- `.env.example`: `SUPABASE_URL` mặc định trỏ Supabase local, `RPC_SIGNING_KEY_ID=f1-dev-1` khớp với `register_dev_key.sql`.
- `README.md`: liên kết tới hướng dẫn và ghi rõ backend chỉ đọc biến môi trường của shell.

**Kết quả:** chỉ thay đổi tài liệu và file mẫu. Các lệnh trong hướng dẫn chưa được chạy lại từ một bản clone sạch.

## 2026-11-18 — Evaluation Learning Assessment F2

**Mục tiêu:** có số đo chất lượng F2 chạy lại được, theo cùng khuôn với evaluation F1, với metric có nguồn trích dẫn.

**Đã làm**

- Thêm metric và oracle (`backend/app/assessment/evaluation.py`) cùng runner `backend/scripts/evaluate_assessment.py` (`offline`, `retrieval-local`, `generate`, `judge`, `score`, `retrieval`), kèm 10 unit test.
- Viết corpus tiếng Việt gốc gồm 10 tài liệu (4 dev / 6 held-out), 80 truy vấn có nhãn và 6 tài liệu prompt injection (`backend/tests/fixtures/assessment_eval/corpus_vi.json`), đóng băng SHA-256 trước khi chạy held-out.
- Viết protocol, rubric và kết quả trong `docs/features/assessment/evaluation/`; lưu items sinh ra và bảng chấm trong `results/annotations/`.

**Kết quả:** nhánh `test/f2-evaluation`. Chấm điểm khớp oracle 10.000/10.000; pgTAP 618 pass; tìm kiếm Recall@5 0,70 (từ khóa 1,00, câu hỏi tự nhiên 0,69, không dấu 0,00); held-out 80/120 câu sinh được, 79/80 đạt rubric (Wilson 93,3–99,8%); injection 0/18 vi phạm. Backend unit 140 test pass.

**Ghi chú**

- Chưa có người chấm thật: người chấm A là AI (Claude), người chấm B là `deepseek-flash`, cùng model sinh câu hỏi. Corpus cũng do AI viết.
- VMLU chưa chạy vì không công bố giấy phép.
- Phát hiện cần sửa ở PR riêng: `QUESTION_MAX_TOKENS=2048` không đủ cho `count=10`; tìm kiếm không dấu và câu hỏi tự nhiên trả rỗng; sinh câu hỏi chỉ dùng 12 chunk đầu; đáp án MCQ lệch vị trí.
- Bổ sung VMLU (dữ liệu do chủ dự án đăng nhập và tải từ vmlu.ai, không commit): `deepseek-flash` đạt 83,6% trên Vi-MQA `valid` (744 câu); sinh 90/90 câu từ 30 đoạn Vi-SQuAD, 89/90 đạt rubric theo một người chấm AI. Judge DeepSeek chạy lại sau khi nạp tiền: hai người chấm AI đồng ý 90/90 về việc câu có đạt hay không (cùng loại câu 40).

## 2026-11-19 — Oracle chấm điểm làm tròn half-up như PostgreSQL

**Mục tiêu:** oracle GRD-C01 phải độc lập với `grade_attempt`; trước đây cả hai cùng dùng `round(x, 2)` của Python (half-even trên float) nên che mất lệch so với PostgreSQL (half-up).

**Đã làm**

- `backend/app/assessment/evaluation.py`: `oracle_grade` làm tròn half-up bằng số nguyên (không dùng `Decimal` để không trùng cách cài của `grade_attempt` ở #57).
- `backend/tests/unit/test_assessment_evaluation.py`: thêm test `1/32 -> 3.13`, `1/3`, `2/3`, `3/4`.

**Kết quả:** trên mã của #57 (`81dcb1b`), oracle cũ khớp 9957/10000 ca (lệch ở ví dụ 9/32: 28.12 so với 28.13), oracle mới khớp 10000/10000. Chưa chạy lại `results/` và phần `db`; cần làm sau khi #57 vào `main`.

## 2026-11-19 — Sửa hướng dẫn chạy demo local

**Mục tiêu:** hướng dẫn trong `docs/local-demo.md` chạy được trên máy không có `psql` và `xxd`.

**Đã làm**

- Bước 2 đăng ký khóa ký RPC qua `docker exec` vào container `supabase_db`, đổi hex sang base64 bằng Python.

**Kết quả:** các lệnh này đã được chạy thật trên Windows (Git Bash) và backend gọi `/v1/tasks` thành công với khóa vừa đăng ký.

## 2026-11-19 — Việc nhỏ sau review #57

**Mục tiêu:** xử lý các góp ý nhỏ của review #57 và hai lỗi môi trường đã gặp khi chạy lại evaluation.

**Đã làm**

- `backend/app/clients/rpc.py`: thêm `operation_fingerprint`; `attempts.py` và `questions.py` dùng chung thay vì tự dựng lại dấu vân tay (tránh lệch khi công thức đổi).
- `backend/tests/integration/test_recommendations_local_supabase.py`: thêm kiểm tra `candidate_patch` không mở lại action đã hoàn tất (409).
- `backend/tests/integration/check_quiz_attempt_upgrade.py`: gọi Supabase CLI qua `shutil.which` để chạy được trên Windows (`supabase.cmd`).
- `.gitattributes`: ép LF cho corpus và CSV đánh giá, vì SHA-256 của chúng được ghi trong kết quả.

**Kết quả:** unit 146/146; acceptance `test_question_http` 5/5 và `test_attempt_http` 6/6; integration recommendations 7/7, attempts 3/3; `check_quiz_attempt_upgrade.py` đạt trên Windows. Corpus checkout ra SHA-256 `19f9c3a9…` đúng giá trị đóng băng.

**Ghi chú**

- Góp ý "UNAUTHENTICATED không nên là lỗi thử lại" ở review #57 là sai: lỗi này đến từ chứng thực RPC của backend và cả `actions.py` của F1 xử lý như vậy; không đổi.
- Chưa làm: quy tắc suy ra `priority`/`suggested_minutes` từ evidence (cần quyết định sản phẩm, migration và pgTAP).
## 2026-11-18 — Đánh giá NLU live và dev/held-out set mới cho F1

**Mục tiêu:** đo chất lượng NLU của Planner bằng bộ held-out có số liệu thật và sửa các lỗi trích xuất lặp lại mà đo được.

**Đã làm**

- Chạy live NLU (DeepSeek, 5 lần mỗi bộ) cho dev set 1 và held-out 1; held-out 1 đạt 70% worst-run nên chỉ giữ làm baseline.
- Thêm `backend/tests/fixtures/nlu_dev2_vi.json` (63 ca) và sửa prompt trong `backend/app/nlu/extractor.py`: `end_at` loại trừ, GET lấy cả ngày/tuần, GENERATE không bắt đầu trong quá khứ, luôn có `deadline_timezone`, giữ nguyên không dấu, UNSUPPORTED cho báo thức và cố ghi đè quy tắc.
- Thêm `_fill_defaults` trong `extractor.py`: server điền `valid_from` (hôm nay) cho lịch lặp và `view=CURRENT` cho GET khi mô hình bỏ sót; thêm test trong `backend/tests/unit/test_extractor.py`.
- Thêm `backend/tests/fixtures/nlu_heldout2_vi.json` (100 ca) và chạy một lần.
- Cập nhật `docs/features/planner/evaluation/README.md` (lệnh live, bảng kết quả, giới hạn diễn giải) và ánh xạ priority trong `annotation-guide.md`; lưu kết quả vào `results/nlu-*.json`.
- Chạy local (Supabase local, backend, frontend) và sửa `backend/app/orchestrator/chat.py`: `operation_for` bù các khóa nullable còn thiếu của cửa sổ rảnh/bận để không bị contract từ chối; thêm `backend/tests/unit/test_chat_window_defaults.py`.

**Kết quả:** nhánh `test/f1-eval-benchmarks`; 99 backend unit test pass; thử qua API local: "Mỗi thứ sáu bận 7h-9h", "Ngày mai rảnh từ 8h đến 11h" và yêu cầu tối đa 45 phút đều vào hàng chờ xác nhận. NLU worst-run: dev 1 100%, dev 2 96,8%, held-out 1 70%, held-out 2 93% (hai bộ held-out chưa đạt ngưỡng 95%).

**Ghi chú**

- Held-out 2 do một tác giả viết sau khi biết prompt, chạy trước khi thêm `_fill_defaults`, chưa có người duyệt và đã bị đọc kết quả nên coi là dev data; muốn tuyên bố ≥95% cần bộ mới khoảng 200 ca do người khác viết.
- Chưa chạy lại contract check, benchmark offline, integration/pgTAP; kết quả dev 1 và 2 chạy khi working tree còn thay đổi chưa commit.

## 2026-11-18 — Xử lý review PR #48

**Mục tiêu:** sửa hai sai lệch metric để kết quả đánh giá Planner phản ánh đúng từng task và từng slot.

**Đã làm**

- Giới hạn coverage theo từng task trong `backend/app/f1/scheduler/evaluation.py`; thêm regression với task có retained block vượt số phút còn lại và task chưa được xếp.
- Chấm `null`, `[]`, `{}` nhất quán giữa slot metrics và frame exact match trong `backend/app/nlu/evaluation.py`; thêm regression cho các slot rỗng ngoài dự đoán.
- Tính lại slot metrics của 15 run exact-scored từ prediction đã lưu, ghi dấu scorer trong `docs/features/planner/evaluation/results/nlu-*.json` và giải thích nguồn số liệu trong README.
- Merge `main` mới nhất vào nhánh PR và hợp nhất hai mục worklog bị conflict.

**Kết quả:** PR #48 (`test/f1-eval-benchmarks`); 141 backend unit tests, contract check và generated schema check pass; 15 run đã lưu khớp scorer mới.

**Ghi chú**

- Chưa gọi lại model, chạy acceptance/integration/pgTAP hoặc benchmark offline; số liệu latency và frame exact match là kết quả lịch sử.

## 2026-11-18 — Chạy lại benchmark cho PR #48

**Mục tiêu:** cập nhật số liệu Planner sau khi sửa metric và xác minh bằng DeepSeek live.

**Đã làm**

- Chạy `benchmark_f1.py` offline với 1.000 mẫu và 10 warm-up cho mỗi workload, rồi đo lại latency riêng sau khi kết thúc NLU live; cập nhật `results/offline.json`.
- Chạy `benchmark_scheduler_quality.py` 100 ca CP-SAT, cập nhật `results/scheduler-quality.json`.
- Chạy DeepSeek `deepseek-flash` 5 lượt cho dev 1, dev 2 và candidate 2; chạy lại dev 2/candidate 2 tuần tự sau khi lượt đồng thời gặp lỗi dịch vụ, cập nhật ba file `results/nlu-*.json` tương ứng.
- Cập nhật `docs/features/planner/evaluation/README.md` với số liệu mới, cách tái lập và giới hạn của candidate 2.

**Kết quả:** PR #48 (`test/f1-eval-benchmarks`); offline unit/contract/schema/scheduler pass; CP-SAT `OPTIMAL` 100/100; NLU worst-run dev 1 100%, dev 2 96,8%, candidate 2 95%, không có lỗi provider-unavailable trong các lượt giữ lại.

**Ghi chú**

- Held-out 1 giữ nguyên baseline lịch sử; candidate 2 đã là development data nên mức 95% không chứng minh khả năng khái quát.

## 2026-11-18 — Chuẩn hóa provenance của benchmark F1

**Mục tiêu:** để hash fixture NLU tái lập được trên Windows/Linux và giải thích commit benchmark trước rebase.

**Đã làm**

- Thêm quy tắc LF cho `backend/tests/fixtures/nlu_*.json` trong `.gitattributes`.
- Sửa `metadata.dataset.sha256` của bốn báo cáo bị ảnh hưởng theo Git blob LF; giữ hash CRLF ban đầu trong `sha256_at_run`, không đổi prediction hay metric.
- Cập nhật `docs/features/planner/evaluation/README.md`: hash LF của candidate 2, nguồn gốc commit `39aa48f` và lệnh đối chiếu với `804dd113` sau rebase.

**Kết quả:** PR #48 (`test/f1-eval-benchmarks`); bốn hash báo cáo khớp fixture LF, diff provenance bằng 0; 163 backend unit tests pass.

**Ghi chú**

- Không gọi lại DeepSeek hoặc benchmark; `git_commit` trong báo cáo vẫn ghi đúng commit lịch sử đã chạy.

## 2026-11-19 — Làm rõ trạng thái held-out 1 trong evaluation F1

**Mục tiêu:** README không được khẳng định điều không kiểm chứng được về held-out 1.

**Đã làm**

- `docs/features/planner/evaluation/README.md`: thay câu "kết quả từng ca được cố ý không xem" bằng mô tả đúng: đã xem tổng hợp theo nhóm lỗi, file kết quả từng ca nằm trong repo, các quy tắc prompt thêm sau trùng với nhóm lỗi lớn nhất của held-out 1 nên không loại trừ được ảnh hưởng; bộ này và candidate 2 đều không còn là held-out.
- Đẩy tag `eval-run-39aa48f` trỏ vào commit chạy benchmark để lệnh `git diff` trong README tái lập được.

**Kết quả:** chỉ thay đổi tài liệu và tag. Số liệu không đổi.

## 2026-11-13 — Viết lại README dự án

**Mục tiêu:** Giới thiệu StudyFlow AI theo bố cục rõ ràng để thành viên mới và người xem đánh giá nắm dự án nhanh.

**Đã làm**
- Viết lại `README.md` với demo, tính năng, cách chạy, cấu trúc, API, kiểm thử và quy ước phát triển.
- Thêm ba ảnh demo Git LFS vào `docs/screenshots/` và kiểm tra liên kết tương đối.

**Kết quả:** PR #35 (`docs/readme-studyflow`); chỉ thay đổi tài liệu và ảnh nên không chạy build hay test.

**Ghi chú**
- Chưa có giấy phép nguồn mở được công bố.

## 2026-11-20 — Đồng bộ PR #35 với main

**Mục tiêu:** Giải quyết xung đột merge và cập nhật trạng thái tính năng trong README.

**Đã làm**
- Merge `origin/main`, kết hợp hướng dẫn cấu hình mới và giữ đầy đủ worklog của hai nhánh.
- Cập nhật README theo backend Assessment hiện có và trạng thái frontend PR #55.

**Kết quả:** PR #35 (`docs/readme-studyflow`); kiểm tra liên kết và xung đột được thực hiện trước khi push.

## 2026-11-23 — Gom kết quả RPC thành một hàm phản hồi HTTP

**Mục tiêu:** Mỗi feature backend tự viết lại bước "kết quả RPC → HTTP" và các bản sao đã lệch nhau, khiến `GET /v1/materials` trả 422 trong khi contract F3 chỉ khai báo 400.

**Đã làm**
- `backend/app/api/v1/http.py`: thêm `result_response` (kiểm schema tuỳ chọn, bảng status truyền vào, suy replay từ outcome `READ` khi không truyền) và `LEARNING_STATUS`.
- `backend/app/api/v1/routes.py`: xoá `Api.result_response` và bốn chỗ tự tính `replayed`; mọi kết quả RPC đi qua hàm mới.
- `backend/app/learning/sessions.py`, `materials.py`: xoá hai `_response` và `_LEARNING_STATUS`; dùng `result_response(..., statuses=LEARNING_STATUS)`, nên materials trả 400 thay cho 422 với `INVALID_PARAMETER`.
- `backend/tests/unit/test_result_response.py`: test bảng status, `Retry-After`, header replay, `request_id`, lỗi schema và hồi quy cursor materials → 400.

**Kết quả:** nhánh `refactor/result-response`; 224 backend unit tests pass, 79 acceptance tests (`acceptance_api_sol`) pass.

**Ghi chú**
- Chưa chạy test tích hợp Supabase local (`test_learning_material_local_supabase.py`) và pgTAP.
- Thông báo lỗi khi kết quả sai contract đổi thành "Kết quả không đúng contract.".

## 2026-11-23 — Test luồng add_turn và gộp kiểm tra chủ sở hữu phiên học

**Mục tiêu:** Các nhánh lỗi của `add_turn` chưa có unit test và kiểm tra chủ sở hữu bị lặp 4 lần trong `sessions.py`.

**Đã làm**
- `backend/app/learning/sessions.py`: thêm `_require_owner`, thay 4 đoạn kiểm tra `owner_id` lặp lại; hành vi và message giữ nguyên.
- `backend/tests/unit/test_learning_turn.py`: 7 test cho `add_turn` (embedder lỗi → 503, model lỗi → 503, độ tương đồng thấp bỏ qua model, `STALE_ENTITY_VERSION` → 409, truy xuất `INVALID_PARAMETER` → 400, phiên của người khác → `INTERNAL_ERROR`).

**Kết quả:** nhánh `refactor/result-response`; 231 backend unit tests pass, 79 acceptance tests (`acceptance_api_sol`) pass.

**Ghi chú**
- Chưa chạy test tích hợp Supabase local (`test_learning_interaction_local_supabase.py`).

## 2026-11-23 — Gộp phần đọc request trong routes.py

**Mục tiêu:** Mỗi luật đọc request (UUID trên path, Idempotency-Key) chỉ được viết một lần; trước đó có 4 chỗ parse UUID và hai regex khác nhau cho cùng một header.

**Đã làm**
- `backend/app/api/v1/routes.py`: xoá `source_id` và hai đoạn parse UUID inline (`get_material`, `post_review`), dùng `_uuid_param`; `post_review` chỉ kiểm tra và vẫn truyền `action_id` gốc vì nó nằm trong fingerprint receipt.
- `backend/app/api/v1/routes.py`: thêm `_idempotency_key` (dùng `fullmatch`) cho `read_json` và `delete_learning_material`.
- `backend/tests/unit/test_route_params.py`: 4 test cho `_uuid_param`, `_idempotency_key` và `post_review` giữ `action_id` gốc.

**Kết quả:** nhánh `refactor/result-response`; 235 backend unit tests pass, 79 acceptance tests (`acceptance_api_sol`) pass.

**Ghi chú**
- Chưa chạy test tích hợp Supabase local.

## 2026-11-23 — Lấy danh sách thao tác đọc của RPC từ contract

**Mục tiêu:** Tránh việc backend ký sai thao tác đọc/ghi (DB trả 403, người dùng thấy lỗi đăng nhập) khi danh sách thao tác đọc ở backend, SQL và contract lệch nhau.

**Đã làm**
- `backend/app/core/contract.py`: nạp `contracts/service-contract.json` và tạo `READ_RPCS` từ các mục `read_only` theo khóa `rpc`.
- `backend/app/clients/rpc.py`: `READ_OPERATIONS` lấy từ `READ_RPCS`, bỏ danh sách viết tay.
- `backend/tests/unit/test_read_operations.py`: so tên trong `app_private.rpc_is_read` của migration mới nhất với `READ_OPERATIONS`.

**Kết quả:** nhánh `refactor/read-operations`; unit test, `acceptance_api_sol` (79 test) và `contracts/check_contract.py` đều đạt. Xóa tạm một tên khỏi migration thì test mới fail.

**Ghi chú**
- Chưa chạy pgTAP và integration với Supabase local (không đổi SQL).
- Test chỉ đối chiếu với migration mới nhất có `rpc_is_read`.

## 2026-11-23 — Ngừng truyền cả đối tượng Api vào workflow

**Mục tiêu:** Bỏ phụ thuộc ngược của `ActionProcessor` vào `Api` và để main.py là nơi duy nhất dựng client DeepSeek.

**Đã làm**
- `backend/app/api/v1/workflow.py`: `ActionProcessor` nhận `rpc, clock, extractor, timezone` và `questions, recommendations, learning_outcomes` qua tham số tường minh.
- `backend/app/api/v1/routes.py`: `Api.__init__` truyền tham số tường minh, bỏ 3 fallback DeepSeek (câu hỏi, learning, source extractor) và các import không còn dùng.

**Kết quả:** nhánh `refactor/workflow-wiring`; unit 219 test và acceptance_api_sol 79 test đều qua; integration với Supabase local 40 test qua; smoke test DeepSeek thật qua `create_app` cho chat, sinh câu hỏi quiz và learning (cần torch và sentence-transformers cài riêng).

**Ghi chú**
- Test dựng `Api` trực tiếp mà không truyền client rồi gọi endpoint question hoặc learning sẽ lỗi `AttributeError` thay vì gọi DeepSeek thật.
- Chưa chạy pgTAP, frontend và `SourceExtractor` với DeepSeek thật.

## 2026-11-23 — Gỡ bộ đánh giá F1 cũ để làm lại

**Mục tiêu:** xóa metric, dataset và kết quả đánh giá Planner cũ để xây lại bộ đánh giá từ đầu, không còn số liệu lỗi thời trong repo.

**Đã làm**

- Xóa `docs/features/planner/evaluation/README.md`, `annotation-guide.md`, `results/`; 4 dataset `backend/tests/fixtures/nlu_*_vi.json`; `eval/datasets/f1_nlu_acceptance.jsonl`, `eval/README_nlu.md`.
- Xóa `backend/app/nlu/evaluation.py`, `backend/scripts/benchmark_f1.py`, `benchmark_scheduler_quality.py`, `evaluate_nlu.py`, `backend/requirements-evaluation.txt` và 3 unit test đi kèm.
- Sửa link gãy trong `docs/features/planner/README.md`, `docs/features/assessment/evaluation/README.md`, `docs/architecture/overview.md`.
- Giữ `backend/app/f1/scheduler/evaluation.py` và `evaluate_planner.py` vì CI và `test_engine.py` còn dùng; giữ các sửa lỗi sản phẩm trong `extractor.py`, `chat.py`.

**Kết quả:** nhánh `chore/remove-f1-eval`; 221 backend unit test pass; `evaluate_planner.py` chạy thành công.

**Ghi chú**

- Chưa chạy contract check và acceptance test. Bộ đánh giá cũ vẫn xem được qua tag `eval-run-39aa48f`.

## 2026-11-23 — Xoá bộ evaluation F2 cũ để làm lại

**Mục tiêu:** bỏ toàn bộ metric, dữ liệu và kết quả evaluation F2 cũ để thiết kế lại từ đầu.

**Đã làm**

- Xoá `backend/app/assessment/evaluation.py`, `backend/scripts/evaluate_assessment.py`, `backend/tests/unit/test_assessment_evaluation.py`, `backend/tests/fixtures/assessment_eval/` và `docs/features/assessment/evaluation/` (README, hướng dẫn chấm, kết quả JSON và CSV).
- `.gitattributes`: bỏ khối ép LF cho dữ liệu evaluation (gồm cả dòng `nlu_*.json` còn sót từ F1).
- Không đổi code production (`grade_attempt`, sinh câu hỏi...), pgTAP và test integration của F2, hay evaluation F3.

**Kết quả:** unit backend 211/211, contract checker đạt, `evaluate_planner.py` chạy đạt; `git grep` không còn tham chiếu tới các đường dẫn đã xoá ngoài worklog.
