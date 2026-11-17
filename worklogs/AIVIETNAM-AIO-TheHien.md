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
