# Context gửi cho AI chính

## Mục tiêu và các quyết định đã chốt

Hoàn tất **backend + API + DB F1 MVP**, UI do nhóm khác phụ trách. Không làm F2/F3, PDF/OCR, sửa/xóa task chính thức, tạo/dời block thủ công. Không thay DeepSeek bằng Gemini trong sản phẩm. Commit tiếng Anh; chưa được merge main.

Người dùng muốn một AI chính mạnh (trước đây chọn **Sol 6.1 High**) tự viết test, quản Git, chạy kiểm chứng, review; một AI khác (**Gemini 4 Argon High**) implement. Chỉ một implementer sửa workspace tại một thời điểm. Flash High chỉ là fallback khi có bằng chứng Argon hết quota, không dùng vì task khó/context đầy. Tài khoản mới có thể dùng model khác theo quyền của họ; không được giả báo đã dùng model không có.

Người dùng đã cho phép push branch `feat/f1-mvp-intergration` lên `chp0703/StudyFlow-AI` để chạy CI. Không cần hỏi lại quyền này. Chưa có quyền merge main. Đã duyệt toàn bộ A/B/C/D tại `docs/implementation/INTERNAL_RPC_ADDENDUM_PROPOSAL.md` cho package 1.0.1; không cần duyệt lại cùng thiết kế.

## Nguồn code và commit

| Thành viên | Nhánh nguồn | SHA nhập |
|---|---|---|
| TV1 persistence/transaction | feat/supabase-database-foundation | f0d079e |
| TV2 API/application service | feat/tv2-tool-layer | c8b4865 |
| TV3 hội thoại/contract | feat/BE_contract_schema | 431991d |
| TV4 scheduler/validator | feature/member4-f1-planner | fecb9f9 |

Main xuất phát `36c9bad`; integrated baseline `ad80c484ba0eb07f8b807bcfff54936f596ef57e`.

Các commit quan trọng:

- `cabce4b`: test scheduler độc lập trước implement.
- `6109815`: HTTP/SQL/NLU acceptance, CI, environment guide.
- `9a86646`: test DST fold trước sửa.
- `2bac72c`: handoff WP2/WP3/WP4 và đề xuất nội bộ cụ thể.
- `5d29d2d`: scheduler/normalizer đã nghiệm thu.
- `4b8844b`: freeze test contract 1.0.1, HTTP replay/bootstrap, SQL 07.
- `52ee7c8`: CI tách scheduler/API/contract; HEAD đã push trước đóng gói.

## Ràng buộc nghiệp vụ/bảo mật

- Logical F1 v1.1; 8 HTTP endpoint, 10 domain/LLM operation. Tham chiếu `contracts/README.md`, `service-contract.json`, `data-contract.json`, `schemas/f1.schema.json` và schema nghiệp vụ trong `docs/database/`.
- 25–90 phút/buổi, 240 phút/ngày, nghỉ 10 phút là **defaults**, không phải hard cap. Custom policy/override phải được merge và lưu đúng.
- Candidate/pending/proposal không tự hết hạn/xóa theo TTL. Proposal revalidate khi duyệt; STALE phải bền vững và replay được. `requires_review` chặn suy diễn đồng ý.
- FE không cấp principal/ApprovalAction/backend attestation hay normalized command có quyền thực thi. JWT user đã verify là nguồn owner. Backend ký HMAC cho **mọi mutation**, kể cả bootstrap/receipt/source/continuation.
- RPC chỉ nhận một `p_request jsonb`; wrapper SECURITY DEFINER, owner `sf_rpc_owner` NOLOGIN/NOSUPERUSER/NOBYPASSRLS, search_path rỗng, FORCE RLS, least grants. Không cấp lại quyền bảng private cho authenticated/anon, không dùng service_role trong request thường.
- Row lock theo owner `user_profiles FOR UPDATE`; tra replay trước và sau lock. Domain idempotency khác HTTP receipt. Receipt lease 120 giây, fencing theo lease_version; giữ replay ít nhất 7 ngày.
- HMAC: canonical UTF-8 JSON sorted Unicode code point, compact, safe integers, không float/NaN/duplicate payload keys; TTL 60 giây, future skew tối đa 5 giây. Đọc `contracts/README.md` để triển khai chính xác.
- Lịch là full immutable snapshot; giữ ID/protected/history/locked/out-of-scope blocks. Không giảm remaining chỉ vì đã xếp lịch/thời gian trôi. PARTIAL phải hiển thị phần chưa xếp trước approval.
- Không LLM/network trong DB transaction. Chưa có pass DB/security/live đồng nghĩa chưa đạt gate.

## Contract bổ sung A/B/C/D được duyệt

Thêm đúng 6 helper, không thêm operation LLM:

1. ensure_user_context: attested bootstrap/read User; GET đầu tiên được tạo profile mặc định nếu thiếu, không sửa profile có sẵn.
2. list_time_windows: read list/cursor owner/filter/sort bound.
3. get_workflow_context: cold-load action/candidate/proposal/presentation/source cùng owner/conversation, một snapshot, không tự review.
4. get_workflow_continuation: đọc continuation cụ thể hoặc unfinished.
5. initialize_workflow_continuation: first-write-wins extraction, immutable origin, lease fencing.
6. checkpoint_workflow_continuation: WAIT/ADVANCE, CAS version/cursor, contiguous outcomes, xác minh domain replay/current terminal action.

Infrastructure `workflow_continuations` có 15 cột theo bản được duyệt. Public 8 endpoint/10 operation và logical 10 entity không đổi. Sau bổ sung: 18 internal interfaces, tổng **27 SQL wrapper** (generate tool dùng context/persist, không có raw generate RPC riêng).

## Trạng thái thực tế khi chuyển người

**WP1 ACCEPTED**: sửa 6 lỗi ban đầu, normalizer NONE/WEEKLY/24:00/DST, giữ ID, malformed input fail closed, clock seconds, UTC elapsed arithmetic qua DST fold. Sol kiểm 33 acceptance +24 planner +78 TV2 pass; CI scheduler xanh. Không suy ra DB/API đã đạt.

**WP0 WIP**: Argon vừa tạo 122 definitions/100 official fixtures theo báo cáo và các file hiện có; Sol chưa nghiệm thu. Chạy thật mới nhất: checker fail, independent16 tests còn **2 failures** (14 pass). Lỗi ở generic ToolResult READ data dùng oneOf: `{items:[],next_cursor:null}` khớp cả SearchTasksData/TimeWindowListData nên bị loại. Nó làm valid ADVANCE và completed prefix bị reject. Đây là chẩn đoán từ source/tests; sửa phải giữ operation-specific validation, không nới mọi JSON hoặc đổi fixtures rỗng cho xanh. Còn cần review toàn bộ semantics/diff và CHANGELOG/version metadata. WIP chưa commit.

**DB**: chỉ 202611050001…008; không có migration 009+. Old boundary/atomic functions chưa theo contract hiện tại. SQL 03–07 là test đích; 07 mới chỉ parse. Concurrency harness 6 scenario đã viết, chưa chạy DB.

**API**: chưa có backend.app.main/create_app/Settings runtime. 30 HTTP methods có nhưng class setup lỗi missing factory (0 test executed). TV2 78 test cũ pass không chứng minh đủ 10 operations.

**TV3/DeepSeek**: state machine, real persistence recovery, scripted extractor và live adapter chưa hoàn tất. NLU dataset40 case đã kiểm cấu trúc, chưa benchmark live; mục tiêu >=38/40 và không unauthorized write.

## Môi trường và CI

Supabase ref người dùng cung cấp: `phomrutsdhdgejlskwcb`; URL đã ở `.env.example`. Public JWKS HTTP200 có ES256 key; chưa biết schema/history/admin quyền/dữ liệu. Coi là project cần bảo toàn, không reset cloud. Người dùng trước đó chưa có DeepSeek key; việc vừa đăng nhập Google không thay key này.

- Baseline DB thật, commit2bac72c: https://github.com/chp0703/StudyFlow-AI/actions/runs/42032340280 — replay8migrations PASS; pgTAP190 assertions/128 fail (03:5/18,04:18/47,05:36/44,06:69/81).
- Scheduler CI xanh, commit52ee7c8: https://github.com/chp0703/StudyFlow-AI/actions/runs/42034378754 — API/1.0.1 contract jobs vẫn đỏ.
- Có thể có CI khác sau các lần push; đọc run theo exact SHA, không suy diễn trạng thái mới từ các link baseline.

Official `agy` đã dùng Google sign-in thật. Legacy `gemini`0.67.0 từng trả UNSUPPORTED_CLIENT; câu hỏi đăng nhập cũ được người dùng trả lời muộn, không phải bằng chứng legacy CLI đã chạy model thành công. Không dùng private API/token extraction/spoof client. Không đóng gói token Google cho người nhận.
