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
