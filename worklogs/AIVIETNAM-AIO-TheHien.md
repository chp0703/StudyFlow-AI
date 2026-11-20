# Worklog — AIVIETNAM-AIO-TheHien

## 2026-11-17 — F2 B3/B4 sinh câu hỏi nháp và duyệt theo lô

**Mục tiêu**

Sinh câu hỏi từ tài liệu B2, cho người dùng xem câu hỏi và nguồn rồi xác nhận qua luồng quyết định hiện có.

**Đã làm**

- Thêm module assessment sinh MCQ/TRUE_FALSE, chuẩn hóa output DeepSeek, lọc nguồn và hỗ trợ lô đạt một phần.
- Thêm migration mới cho câu hỏi, nguồn, liên kết lô, RLS, bất biến và ba RPC tạo/duyệt/liệt kê câu hỏi.
- Nối pending action, review, decisions và receipt. Lỗi model được lưu thành kết quả lỗi để cùng khóa gửi lại không gọi model thêm lần nữa.
- Đồng bộ contract, migration schema, kiểu API và mapper hiển thị nội dung, đáp án đề xuất cùng đoạn nguồn.
- Bổ sung test cho dữ liệu B2 có khoảng trắng, UUID viết hoa, output model lỗi, gửi lại request, phân quyền và tranh chấp quyết định.

**Kết quả**

- Nhánh `feat/f2-b3-b4-question-review`, bắt đầu từ B2 `2289c96`.
- Local đạt 107 unit test, 64 API acceptance test, 37 scheduler test và 31 test API frontend.
- Contract checker, migration `--check`, TypeScript, frontend build và planner evaluation đạt. Planner không có vi phạm hard constraint.

**Ghi chú**

- Supabase/pgTAP, integration và concurrency đang chờ workflow GitHub xác minh vì máy thiếu Docker/WSL.
- Chưa kiểm tra DeepSeek thật vì chưa có API key. Kiểm thử model dùng transport giả lập.
- Đã chạy formatter trên các file frontend thay đổi. Bản oxfmt hiện tại làm hỏng type inline, đã khôi phục phần format ngoài phạm vi và sửa cú pháp, sau đó TypeScript/test/build đạt.

## 2026-11-18 — F2 B7: tạo gợi ý ôn tập có bằng chứng

**Mục tiêu:** tạo gợi ý từ tối đa 50 lượt hợp lệ gần nhất và chờ duyệt trước khi bàn giao F1.

**Đã làm**
- Thêm contract, migration/RPC tạo recommendation, snapshot bằng chứng, FORCE RLS và presentation digest; giữ migration lịch sử.
- Nối endpoint vào durable receipts; đồng bộ client types/mapper. agy sinh code, Codex review và sửa các sai lệch interface/helper.
- Thêm 6 unit test độc lập cho orchestration, lỗi/retry/reference và cặp trường patch/version.

**Kết quả:** nhánh `feat/f2-b7-revision-recommendations`; contract checker 189 definitions/126 fixtures và 6 test B7 PASS. Baseline B6: 124 unit, 72 HTTP, 37 scheduler và 80 frontend test PASS; typecheck/build PASS.

**Ghi chú:** phần duyệt/bàn giao và patch task còn tiếp tục; chưa chạy DB trên host vì thiếu Docker. CI local Supabase sẽ kiểm tra migration/RPC; chưa công bố B7 hoàn tất.

- CI lần đầu phát hiện FK dùng sai tên bảng conversation; sửa sang conversation_records theo schema B2. Contract job PASS; DB chưa PASS, đang chạy lại.

## 2026-11-18 — F2 B7: duyệt và bàn giao task nháp

- Thêm RPC quyết định nguyên tử, UI reference/digest checks, chuyển PROPOSED sang ACCEPTED/REJECTED; nhận gợi ý chỉ tạo candidate và action F1 cần bổ sung thời gian.
- 8 unit test B7 PASS; CI DB của phần tạo gợi ý tại 8cbdc2b PASS (clean reset, pgTAP, upgrade, integration, concurrency). Test DB cho quyết định và patch tiếp tục được bổ sung.

## 2026-11-18 — F2 B7: bổ sung task qua review API

- Thêm patch task nguyên tử có action/candidate version, giữ bằng chứng và giới hạn độ tin cậy; chưa đủ thông tin trả NEEDS_CLARIFICATION, đủ mới phát reference xác nhận F1.
- Đồng bộ client patch/version, tài liệu/OpenAPI; thêm pgTAP security và 5 integration case DB thật (toàn luồng, thiếu dữ liệu, giới hạn 50 lượt/nguồn, race, mất phản hồi). Thêm CI upgrade B6->B7.
- Local: 132 unit, 72 HTTP acceptance, 82 frontend test, TypeScript/build, contract checker và generator --check PASS. Integration B7 cần CI local Supabase; host không có Docker.

## 2026-11-18 — F2 B7: sửa lỗi integration và JSON ratio

- CI cf3827f: migrations, pgTAP, clean/upgrade và B6->B7 upgrade PASS; integration phát hiện canonical_json B5 chỉ nhận 4 chữ số thập phân và fixture bulk chưa đặt omitted_count ban đầu.
- B7 lưu error_rate theo biểu diễn JSON float, nới riêng canonical error_rate tới 24 chữ số có chặn [0,1], so sánh invariant với sai số 1e-12; thêm test 1/3 qua review và pgTAP canonical. Sửa fixture theo bất biến B5, không đổi B5 runtime.
- Loại bỏ formatting ngoài phạm vi trong endpoints.ts; TypeScript PASS. Đang chạy lại CI để xác minh B7 đầy đủ.

## 2026-11-18 — F2 B7: hoàn thiện kiểm chứng và contract bàn giao

- CI 86ce5d6 PASS: 628 pgTAP assertions, 28 HTTP integration (6 case B7), 6 PostgreSQL concurrency, clean reset và cả upgrade từ B6. Backend CI cf3827f PASS.
- Bổ sung race patch/confirm, 7 fixture contract B7 (tổng 133), type ApiTaskCandidate đầy đủ để client đọc version; cập nhật tài liệu runtime. Local 132 unit, 82 frontend, TypeScript, checker/generator PASS.
- Chưa chạy UI F2 vì ngoài phạm vi; B7 không dùng LLM. CI cuối sẽ chạy trên commit bàn giao mới.

- Siết integration: hủy candidate luôn được kiểm tra dù nhánh REJECT thắng race; thêm reference bị sửa và chặn tạo gợi ý khi F1 task đang chờ. Chỉ thay đổi test; CI cuối chạy lại để xác minh đầy đủ.

## 2026-11-19 — Tích hợp F2 B7 và bảo toàn kết quả B5

**Mục tiêu**  
Bàn giao đề xuất ôn tập từ B7 sang Planner và giữ kết quả lưu, nộp bài ổn định qua retry, restart và các worker chạy đồng thời.

**Đã làm**

- Tích hợp B7 từ PR #49. Giữ giới hạn bằng chứng, trình bày lại snapshot và xác nhận riêng cho task nháp F1.
- Chuyển B5 sang đọc dữ liệu bền vững, gắn version cho câu trả lời và xử lý replay theo kết quả RPC. Chấm lại khi autosave đổi version và đồng nhất làm tròn với PostgreSQL.
- Áp dụng giới hạn phản hồi DeepSeek và giải phóng receipt khi gặp lỗi 429/503 từ PR #51.
- Thêm kiểm tra pgTAP, tranh chấp PostgreSQL và upgrade giữ dữ liệu B5 từ schema đã chạy B7.

**Kết quả**  
Nhánh `codex/f2-durable-attempts-b7-integration`. Contract và generator đạt. Đạt 136 backend unit, 76 HTTP acceptance, 37 scheduler acceptance, 83 frontend test, TypeScript, build và kiểm tra Planner không vi phạm hard constraint.

**Ghi chú**  
Supabase local được xác minh qua workflow CI vì máy phát triển thiếu Docker. Kiểm tra oxfmt báo khác biệt ở năm file API frontend nhập từ PR #49.

## 2026-11-19 — Sửa contract replay phát hiện trên CI #57

**Mục tiêu**  
Đồng bộ lookup B5 giữa backend, PostgreSQL và bộ test.

**Đã làm**

- Thêm hai thao tác B5 vào enum Assessment, sinh lại migration contract và buộc HTTP mock kiểm tra arguments theo schema thật.
- Dùng RpcEnvelope cùng schema arguments theo từng Assessment RPC trong harness PostgreSQL, giữ kiểm tra RpcRequest của F1.

**Kết quả**  
Draft PR #57. Contract checker, generator và 76 HTTP acceptance đều đạt. Chạy lại CI PostgreSQL cho bản sửa.

## 2026-11-19 — Đồng bộ kiểm tra attempt đang làm

**Mục tiêu**  
Để checker và bộ test concurrency chấp nhận đúng trạng thái attempt mà PostgreSQL đã trả.

**Đã làm**

- Đồng bộ quy tắc omitted_count cho IN_PROGRESS trong checker và tài liệu với constraint B5.
- Thêm fixture hợp lệ và fixture sai để giữ quy tắc trong bộ kiểm chứng contract.

**Kết quả**  
Draft PR #57. Contract checker đạt 135 fixture và backend unit đạt 136 test. CI của bản trước đã qua 700 assertion pgTAP, 31 HTTP integration và kiểm tra dữ liệu cũ qua upgrade B7. Chạy lại concurrency với checker đã sửa.

## 2026-11-20 — F3 M1 nạp và lập chỉ mục tài liệu

**Mục tiêu**
Cho Daily Learning nạp, lập chỉ mục và quản lý tài liệu trên kho dùng chung với Assessment.

**Đã làm**

- Mở rộng kho tài liệu F2 và tạo schema phiên học, lượt trao đổi, kết quả phiên. Thêm RPC có chứng thực cho claim, kết quả index, đọc và xóa tài liệu.
- Nối bốn endpoint tài liệu với tách trang và embedding CPU. Thêm ca kiểm tra tương thích F2, retry và upload đồng thời.
- Chuẩn bị PR stack từ M0 tại `a4b4561` trên nhánh `codex/f3-m1-material-indexing`.

**Kết quả**
Bộ unit indexing 28 ca, contract checker, migration generator và test base64 đúng 5 MiB đã đạt. CI Supabase và smoke CPU đang chờ kết quả.
- Smoke CPU E5 thật đạt 384 chiều và norm L2. Văn bản tiếng Việt mất 13,72 giây khi nạp model từ cache đĩa lần đầu. PDF tổng hợp 50 trang và 40.191 ký tự tạo 91 chunk trong 5,48 giây khi model đã nạp.
- Backend CI của draft PR #65 xanh. Đổi tên constraint trùng ở migration M1 và bổ sung ca quota đồng thời, lease hết hạn và kiểm tra chunk F2 qua upgrade. Run local 190 unit (2 skip theo cấu hình), 76 ca HTTP acceptance ở bản trước, checker và generator đạt.
- CI đã replay migration và chạy 710 assertion pgTAP. Cập nhật allowlist kiểm tra ranh giới RPC để đăng ký đúng sáu RPC M1, giữ nguyên kiểm tra quyền và chữ ký. Unit indexing và HTTP acceptance local qua sau bản sửa.
- CI trên `199271e` đã xanh cả backend và DB. DB hoàn thành 710 assertion pgTAP, 37 ca HTTP integration, upgrade có dữ liệu và 9 ca concurrency PostgreSQL. Thêm ca race DELETE với Assessment đang giữ tham chiếu và ca chọn ID ổn định khi F2 có hash trùng.
- Smoke CPU gần ngưỡng 200.000 ký tự đạt. PDF 50 trang có 183.631 ký tự, tạo 300 chunk trong 13,64 giây khi model đã nạp.
