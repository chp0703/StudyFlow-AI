## 2026-11-12 — Planner frontend follow-up

**Mục tiêu:** Cải thiện trải nghiệm Planner theo contract F1 hiện hành mà không áp dụng trước thay đổi đang chờ ở PR #32.

**Đã làm**
- Chuyển ngày và giờ của Planner/API mapper sang múi giờ Việt Nam; thêm kiểm thử nhiều múi giờ máy.
- Hiển thị ngày trên tiêu đề lịch cố định khi cuộn, sửa bố cục Planner trên màn hình nhỏ.
- Mở rộng bản xem trước lịch học: thay đổi, cảnh báo, mức phủ và công việc chưa xếp hết.
- Thêm trình sửa thời gian học hằng tuần qua `POST /v1/actions` và duyệt riêng bằng ActionReference; giữ giờ bận tách biệt.
- Bỏ câu hỏi môn học khỏi biểu mẫu nháp; ghi rõ ranh giới contract và upload trong `frontend/PLANNER_FOLLOWUP_CONTRACT.md`.

**Kết quả:** Nhánh `feat/fe-planner-followup-kent`; chưa mở PR. Đã chạy formatter, TypeScript, build và Node tests của các lớp frontend liên quan.

**Ghi chú**
- FE-01 cần PR #32 được merge và xác minh runtime trước khi đổi DTO công việc trên API.
- FE-06 cần hợp đồng upload/trích xuất của backend; không có endpoint hiện hành.
- Chưa xác minh luồng API có đăng nhập với backend đang chạy.

## 2026-11-12 — Hoàn thiện thời gian học hằng tuần FE-03

**Mục tiêu:** Cho phép sửa thời gian học chính xác đến phút trong cả bản demo và chế độ API, không xếp lịch vào giờ bận hoặc khoảng học không đủ 60 phút.

**Đã làm**
- Mở trình sửa thời gian học trong demo; giữ các thay đổi trong đề xuất đến khi duyệt, với trạng thái demo chỉ nằm trong bộ nhớ.
- Hiển thị các đoạn thời gian học/bận chính xác trên lịch; giờ bận được ưu tiên khi chồng lấp.
- Giới hạn bộ xếp lịch demo và lệnh thủ công vào khối đủ 60 phút; giữ lệnh rảnh/bận cũ làm ngoại lệ ngày cụ thể.
- Giữ khóa idempotency khi thử lại thao tác API, kiểm tra payload ADD/UPDATE/ARCHIVE và bổ sung kiểm thử múi giờ, lịch tuần, giới hạn phút.

**Kết quả:** Nhánh `feat/fe-planner-followup-kent`; 46 Node tests đạt, TypeScript và Vite build đạt; đã kiểm tra giao diện demo trên trình duyệt.

**Ghi chú**
- Chưa kiểm thử trực tiếp với phiên đăng nhập và backend API đang chạy.
- Demo chỉ xếp khối 60 phút bắt đầu đúng giờ; API vẫn dùng hợp đồng F1 v1.1 hiện hành.
