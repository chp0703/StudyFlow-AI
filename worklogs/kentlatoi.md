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

## 2026-11-13 — Sửa đề xuất thời gian học FE-03

**Mục tiêu:** Giữ đề xuất thời gian học hằng tuần khi lệnh chat tiếp theo không đổi công việc hoặc khung giờ cũ.

**Đã làm**
- Sửa nhánh không có thay đổi trong `frontend/src/features/planner/usePlanner.ts` để giữ đề xuất tuần đến khi duyệt hoặc từ chối.
- Bổ sung kiểm thử hồi quy trong `frontend/src/features/planner/proposal.test.ts`.

**Kết quả:** Nhánh `feat/fe-planner-followup-kent`; 46 Node tests đạt, TypeScript, Vite build và kiểm tra định dạng đạt.

**Ghi chú**
- Chưa kiểm thử thủ công luồng demo trên trình duyệt hoặc phiên API có đăng nhập.

## 2026-11-13 — Sửa phản hồi lệnh khi chờ duyệt FE-03

**Mục tiêu:** Giữ mô tả thay đổi giờ học đang chờ và hiển thị phản hồi lệnh chat không hợp lệ riêng biệt.

**Đã làm**
- Giữ nội dung đề xuất tuần trong `frontend/src/features/planner/usePlanner.ts`; đưa phản hồi lệnh không đổi lịch vào thông báo Planner hiện có.
- Mở rộng kiểm thử hồi quy trong `frontend/src/features/planner/proposal.test.ts` cho thay đổi tuần và lệnh không hợp lệ.
- Kiểm tra demo trên trình duyệt: mô tả giữ nguyên, toast riêng, chỉ ghi sau Duyệt và Từ chối không ghi.

**Kết quả:** Nhánh `feat/fe-planner-followup-kent`; 47 Node tests đạt, TypeScript, Vite build và `git diff --check` đạt.

**Ghi chú**
- Chưa kiểm thử E2E API có đăng nhập vì không có backend và tài khoản thử nghiệm được cấp quyền.

## 2026-11-13 — Correct Planner follow-up to leader specification

**Mục tiêu:** Sửa cách hiểu sai FE-03 thành tùy chỉnh giờ hiển thị lịch theo từng thứ, chỉ nằm ở frontend.

**Đã làm**
- Ghi ma trận truy vết FE-01–FE-06; giữ nhánh FE follow-up làm nền, không lấy editor từ nhánh UX refresh.
- Gỡ editor giờ học hằng tuần và ràng buộc scheduler demo do FE-03 cũ tạo ra. `CalendarDisplaySettings` giữ một dải giờ cho mỗi thứ trong bộ nhớ frontend; lịch đặt sự kiện đúng phút theo từng cột ngày.
- Giữ múi giờ Việt Nam, đầu đề ngày cố định và luồng duyệt đề xuất; mở rộng chi tiết lịch học đầy đủ, bỏ môn học khỏi Planner và sửa phản hồi tệp bản mẫu để không nhận là đã tải/đọc.
- Bổ sung kiểm thử dải giờ hiển thị, giờ 09:15 và tệp chỉ hiển thị; giữ các kiểm thử API/đề xuất hợp lệ.

**Kết quả:** Nhánh `fix/planner-followup-leader-spec-kent`; chưa mở PR mới hoặc đẩy nhánh. Kiểm tra kỹ thuật và QA ghi trong báo cáo bàn giao.

**Ghi chú**
- FE-01 API còn chờ PR #32 được merge và xác minh runtime; FE-06 còn chờ hợp đồng upload/trích xuất.
- FE-03 ban đầu được triển khai từ yêu cầu hiểu nhầm về giờ học hằng tuần; commit lịch sử không bị xóa hay viết lại.

## 2026-11-13 — Restore Planner Free/Busy display

**Mục tiêu:** Khôi phục cách xem Rảnh/Bận sau khi FE-03 chuyển thành tùy chỉnh giờ hiển thị.

**Đã làm**
- Vẽ các khoảng Rảnh/Bận chỉ để xem trong `WeekCalendar.tsx`, gộp đoạn liền nhau, ưu tiên Bận và cắt phần vẽ theo dải giờ hiển thị.
- Giữ trạng thái đề xuất khác với đã duyệt; bổ sung kiểm thử phép chiếu theo phút và HTML render cho Demo/API.
- Kiểm tra Demo trên trình duyệt: Rảnh 09:00–12:00, sau đó Bận 10:00–11:00 chia thành ba đoạn đúng.

**Kết quả:** Nhánh `fix/planner-followup-leader-spec-kent`; 49/49 Node tests, TypeScript, Vite build và `git diff --check` đạt.

**Ghi chú**
- API E2E có đăng nhập chưa chạy; Vite cảnh báo chunk JS trên 500 kB.
