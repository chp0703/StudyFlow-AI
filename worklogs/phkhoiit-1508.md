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
