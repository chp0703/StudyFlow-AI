# Kế hoạch tiếp tục — thứ tự triển khai

Không làm lại WP1 hoặc phân tích lại bốn branch từ đầu. Khôi phục WIP rồi xác minh trạng thái mới nhất. G1/G2/G3 đều chưa được đánh dấu hoàn tất.

## 0. Chốt WP0 đang dở

Đọc `docs/implementation/WP0_CONTRACT_ADDENDUM.md` và A/B/C/D. Chạy checker +16 test contract. Giao implementer đúng 2 ca đang fail (valid ADVANCE và completed prefix chứa READ empty list), kèm source `ToolResult`/`WorkflowStepOutcome`. Reviewer đánh giá sửa union/operation binding; không giảm assertions. Review cả các lỗi khác có thể còn bị ca đầu tiên che, 100 official fixtures, metadata/version/CHANGELOG. Đạt rồi commit tiếng Anh và push branch tích hợp. Chưa đạt thì tiếp tục loop, không tự chuyển bước.

## G1 — tích hợp và nền tảng

WP1 đã xong. Giao Gemini tuần tự theo `docs/implementation/WP2_DATABASE.md`:

| Gói | Cần implement | Nghiệm thu |
|---|---|---|
| WP2a | Migration009+; role/grants/FORCE RLS; đủ infrastructure kể cả continuation/key; schema validation deterministic; canonical_json/verify_rpc_request; bỏ overload/bypass cũ. Không sửa migration001–008. | Migration thật chạy được; vectors HMAC/canonical, auth/owner/role checks đúng. Incomplete domain phải fail closed, không thành công giả. |
| WP2b | Source/candidate/pending/presentation/review/cancel/confirm/search; time windows/policy; receipt lease/fencing; 6 helper mới và continuation CAS/immutable queue. | SQL06/07 phần liên quan; đúng schema/result; replay/concurrent confirm/rollback/custom policy/lease thực. |
| WP2c | Consistent scheduling snapshot, proposal persistence/reads/lookup; approve/reject full snapshot, protected ID/history, workload/availability/policy/time revalidation; durable stale; atomic plan commit. | Toàn SQL03–07 + concurrency harness; proposal race/stale/rollback/protected/recovery thực. |
| WP3 phần nền | FastAPI/JWT/JWKS/errors/body limits/CORS/RPC signing/client; durable structured create candidate→decision→read tasks. | Factory/Settings seam đúng 30 HTTP tests; JWT forwarding per-request; restart/retry không ghi trùng trên DB thật. |

G1 cần DB thực trong CI, không chỉ SQL parse hoặc mock. Có thể tách những phần WP3 độc lập để làm nhỏ sau khi DB interface ổn; mỗi lúc một implementer. Test migration mới từ empty và upgrade baseline8 là hai bằng chứng riêng. CLI3 flags đã kiểm: `supabase db reset --version 202611050008 --yes`, rồi `supabase migration up --yes` đều **local mặc định**; không có cờ `--local` ở bản3.0.0. Chưa cấu hình route upgrade/seed/concurrency vào CI: đây là việc cần làm, không phải đã chạy.

## G2 — đủ nghiệp vụ F1

Theo `WP3_API.md` và `WP4_WORKFLOW.md`:

1. Đủ settings/time-windows/read views và generate/replan/approve/reject với scheduler thật + atomic RPC.
2. TV3 state machine bằng scripted extractor trước: thiếu slot, clarification, sửa/hủy nháp, đổi chủ đề/requires_review, multi-intent phụ thuộc, quyết định đúng target/version, reject.
3. Receipt/domain replay/continuation recovery thật: crash trước/sau persist/commit/checkpoint; không re-extract queue đã lưu; source/action IDs ổn định; không tự duyệt sau restart.
4. Đủ 8 endpoint/10 operation. Không expose raw internal RPC thành tool/FE route. Không bỏ việc vì 78 TV2 test cũ đã xanh.

## G3 — demo live và bàn giao UI

1. Người dùng cấu hình Supabase + DeepSeek ngoài Git theo `DEMO_ENVIRONMENT.md`; kiểm metadata/schema/history trước deployment. Không reset cloud; chưa biết project hiện tại là demo riêng hay chung có dữ liệu.
2. Nối DeepSeek thật, evaluator dùng production extractor/normalizer; 40 câu Việt đạt >=95% (=38/40), mọi ambiguous/fake approval không ghi trái phép. Không lấy benchmark prompt khác để thay bằng chứng sản phẩm.
3. Migrations đã qua CI mới deploy phạm vi được xác nhận; provisioning HMAC key kín. User JWT normal requests, admin credentials chỉ deployment/test setup.
4. Sáu live journeys ×2 dữ liệu mới, ít nhất một lượt sau restart backend; owner isolation/retry/replay/security/cloud thật. Chuẩn bị OpenAPI, examples và collection cho UI.

## Quy tắc gate và thứ tự kiểm

- Reviewer viết/chốt test trước mỗi gói. Implementer không sửa tests/contracts đã duyệt tùy tiện.
- Rerun đúng test fail → regression liên quan → review diff → kiểm chứng dependency thật → commit/push. Một test xanh không đủ để đóng cả giai đoạn.
- Context đầy: phiên mới + handoff. Argon quota hết thật: Flash3.8High. Không có AI khả dụng thì ghi phần chưa xong, không làm giả kết quả.
- Những thứ chưa test phải ghi NOT_RUN; giữ rõ mock/parse/local/CI/live. Không merge main trong quá trình này.
