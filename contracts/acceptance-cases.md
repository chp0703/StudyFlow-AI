# Ca nghiệm thu tích hợp F1

Trạng thái ban đầu: **NOT_RUN** cho toàn bộ ca runtime dưới đây. Fixtures JSON và checker chỉ xác minh contract tĩnh/các invariant từ một payload. Người triển khai ghi commit, môi trường, lệnh chạy và bằng chứng vào cột kết quả khi nghiệm thu.

| ID | Owner chính / phối hợp | Trigger | Kết quả bắt buộc | Kết quả |
|---|---|---|---|---|
| API-01 | FE + TV2 | Gửi form tạo task đủ dữ liệu | Chỉ có candidate/action chờ xác nhận; chưa có AcademicTask | NOT_RUN |
| API-02 | FE + TV3 | Tin nhắn thiếu deadline/effort | NEEDS_CLARIFICATION, giữ draft, hỏi đúng field; không báo đã lưu task | NOT_RUN |
| API-03 | FE + TV2 | Bấm xác nhận candidate đúng ActionReference | COMMITTED, task TODO, remaining=estimated, truy xuất lại được sau restart | NOT_RUN |
| API-04 | FE + TV2 | Sửa content/version ở client rồi gửi quyết định cũ | Không ghi; stale/review-required; không tự duyệt target mới | NOT_RUN |
| API-05 | FE + TV2 | Gửi policy 120–150 phút, 600 phút/ngày, nghỉ 0 | Preview full merged policy; xác nhận lưu; lần lập lịch sau dùng custom | NOT_RUN |
| API-06 | FE + TV4 | policy_overrides cho một lần sinh lịch | Proposal giữ policy_snapshot đúng; hồ sơ không bị đổi | NOT_RUN |
| API-07 | FE + TV2 | PARTIAL proposal | Hiện unallocated, warnings và diff trước xác nhận; không che phần thiếu | NOT_RUN |
| API-08 | FE + TV2 | CURRENT chưa có lịch, HISTORY không tồn tại | CURRENT 200/null/[]; HISTORY 404 cùng envelope công bố | NOT_RUN |
| API-09 | TV2 | JWT sai/hết hạn, body quá lớn, request schema sai | 401/413/422 theo catalog; không lộ traceback; request_id khớp header | NOT_RUN |
| API-10 | FE + TV2 | Query calendar một tuần | Chỉ lọc view; block giao ranh giữ thời điểm gốc; proposal approval vẫn dựa full snapshot | NOT_RUN |
| API-11 | TV2 | Cursor bị sửa/đổi owner/filter | Từ chối; không trả dữ liệu user khác; page_size không vượt 100 | NOT_RUN |
| ORCH-01 | TV3 + TV2 | LLM xuất owner/approval hoặc operation ngoài allowlist | Không tin/không thực thi; unsupported/invalid rõ ràng | NOT_RUN |
| ORCH-02 | TV3 + TV1 | Reload action cũ hoặc đổi chủ đề rồi nói “đồng ý” | requires_review, trình bày lại, reference mới; lần xem lại chưa là approval | NOT_RUN |
| ORCH-03 | TV3 + TV1 | Nhiều intent: giờ rảnh → sinh lịch | Một awaiting/conversation; chỉ sinh từ giờ rảnh đã được xác nhận; thứ tự phụ thuộc đúng | NOT_RUN |
| ORCH-04 | TV3 + TV1 | Candidate “mai” mở lại sau nhiều ngày | Giữ ngày tuyệt đối gốc, validate lại; không biến thành “mai” tại thời điểm mới | NOT_RUN |
| ORCH-05 | TV3 + TV2 | CHAT approval không có source message hoặc đích mơ hồ | Không tạo ApprovalAction hợp lệ; hỏi lại/APPROVAL_REQUIRED | NOT_RUN |
| ORCH-06 | TV2 + TV3 | Từ chối candidate/window/policy | Action CANCELLED; candidate CANCELLED nếu có; không ghi task/window/policy | NOT_RUN |
| SEC-01 | TV1 + TV2 | Gọi trực tiếp mutation RPC bằng JWT FE, thiếu/giả attestation | FORBIDDEN; không ghi bất kỳ row nào | NOT_RUN |
| SEC-02 | TV1 + TV2 | Attestation thật nhưng thay args/user/target/payload/routine | Digest/identity mismatch; không ghi | NOT_RUN |
| SEC-03 | TV1 + TV2 | Attestation hết 60 giây hoặc key/signature sai | Fail closed; backend retry ký lại, giữ business key; proposal vẫn được giữ | NOT_RUN |
| SEC-04 | TV1 | anon/PUBLIC execute; authenticated truy cập bảng private/helper | Bị chặn; chỉ wrappers allowlist được gọi; không quyền DML bảng | NOT_RUN |
| SEC-05 | TV1 | SECURITY DEFINER wrapper và cross-user FK qua RPC | Owner role NOLOGIN/NOBYPASSRLS, safe search_path/FORCE RLS; cross-user không đọc/ghi | NOT_RUN |
| SEC-06 | TV2 | Hai request đồng thời của hai user | JWT/client context không lẫn nhau; principal không lấy từ body | NOT_RUN |
| DB-01 | TV1 + TV2 | Timeout sau task confirmation commit, retry cùng key | Trả task cũ; không tạo task/ApprovalAction thứ hai | NOT_RUN |
| DB-02 | TV1 + TV2 | Timeout sau plan approval commit, retry cùng key | Trả plan cũ trước stale/terminal checks; pointer/version không tăng lại | NOT_RUN |
| DB-03 | TV1 | Cùng key khác fingerprint; cùng key đồng thời | Conflict khác payload; cùng payload tối đa một mutation, lookup lại sau lock | NOT_RUN |
| DB-04 | TV1 + TV2 | Hai proposal cùng base được duyệt đồng thời | Một commit; cái sau stale; không overwrite im lặng | NOT_RUN |
| DB-05 | TV1 + TV4 | TimeWindow đổi giữa đọc input và persist proposal | Input+revision cùng snapshot; revision compare loại proposal cũ | NOT_RUN |
| DB-06 | TV1 + TV4 | TimeWindow/policy đổi dù plan.version chưa đổi | Approval cũ STALE; trạng thái stale được giữ bền vững, không commit plan | NOT_RUN |
| DB-07 | TV1 | Lỗi sau insert plan hoặc giữa insert blocks | Rollback plan/blocks/pointer/revision/approval/action/idempotency cùng nhau | NOT_RUN |
| DB-08 | TV1 | Commit snapshot mới giữ block_id cũ | PK(plan_id,block_id) cho phép; lịch cũ không bị UPDATE/DELETE | NOT_RUN |
| DB-09 | TV1 | Block overlap cùng plan và overlap giữa hai historical plans | Cùng plan bị chặn; khác snapshot được giữ; interval sát nhau không overlap | NOT_RUN |
| DB-10 | TV1 + TV2 | Reject proposal thành công nhưng mất response | Retry trả REJECTED cũ; không đổi current plan hoặc revision | NOT_RUN |
| DB-11 | TV1 + TV3 | Worker chết sau message/domain commit trước API response | Recovery dùng lại message/action/key; response bền vững; không sinh action trùng | NOT_RUN |
| DB-12 | TV1 | Hai pending action cùng conversation; typed approval sai target; backlink sai | Constraint/RPC từ chối ở DB boundary, không chỉ ở FastAPI | NOT_RUN |
| DB-13 | TV1 | Dọn idempotency sau retry window 7 ngày | Không xóa nháp/proposal/history; uniqueness task/proposal còn; client reconcile trước retry | NOT_RUN |
| DB-14 | TV1 | Kiểm tra grants theo từng RPC/table | Mỗi wrapper có touched-table matrix cụ thể, không broad grant/helper bypass | NOT_RUN |
| DB-15 | TV1 + TV2 | Lease hết hạn, worker mới reclaim trong lúc worker cũ còn chạy | Fencing lease_version chặn complete của worker cũ; domain idempotency ngăn ghi trùng | NOT_RUN |
| DB-16 | TV1 + TV2 | Generate đã persist proposal nhưng worker chết trước response | Retry lookup kết quả theo command gốc; dùng lại proposal ID, không hash lại generated ID/clock | NOT_RUN |
| PLAN-01 | TV4 + TV2 | Weekly end_time=24:00, DATE deadline, DST invalid/ambiguous | Roundtrip giữ đúng ngày/giờ; DST mơ hồ hỏi lại; không xuất T24:00 | NOT_RUN |
| PLAN-02 | TV4 + TV2 | Retained blocks ngoài horizon/locked/history/giao ranh | Snapshot đầy đủ giữ protected blocks và ID; không vô tình xóa | NOT_RUN |
| PLAN-03 | TV4 + TV2 | Task đang có block diễn ra | Không tái phân bổ task đó, yêu cầu làm rõ tiến độ | NOT_RUN |
| PLAN-04 | TV4 + TV2 | remaining=180, giữ60, mới90, thiếu30 | Summary bảo toàn180; sau approval remaining vẫn180 | NOT_RUN |
| PLAN-05 | TV4 + TV2 | NONE, NO_CHANGE hoặc diff rỗng còn thiếu việc | READ report, không tạo proposal/snapshot trùng hoặc NONE committable | NOT_RUN |
| PLAN-06 | TV4 + TV1 | Proposal giữ lâu còn hợp lệ / block mới đã bắt đầu | Còn hợp lệ được duyệt; quá khứ STALE; không có product TTL | NOT_RUN |
| PLAN-07 | TV4 + TV2 | Đầu vào fixed now/policy/tasks/windows giống nhau | Engine deterministic; không truy cập DB/LLM/clock ẩn; validator phát hiện hard conflicts | NOT_RUN |

Các consumer có thể dùng fixtures chung để chạy mock và implementation thật. Ca DB/security cần PostgreSQL/Supabase thật hoặc local stack tương đương; test giả lập không thay thế bằng chứng runtime này.
