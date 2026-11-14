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

## 2026-11-13 — Add compact Planner week view

**Mục tiêu:** Giảm các hàng giờ trống và giữ lịch chi tiết khi cần xem theo phút.

**Đã làm**
- Thêm `CompactWeekCalendar.tsx` làm chế độ mặc định: bảy ngày, sự kiện xếp theo giờ bắt đầu, Rảnh/Bận, xem đầy đủ ngày và nút mở thêm sự kiện.
- Thêm nút chuyển sang timeline chi tiết; giữ FE-03, header sticky, đề xuất và dữ liệu lịch không đổi khi chuyển chế độ.
- Sửa bố cục mobile: bộ chọn ngày cuộn ngang, agenda đủ chiều rộng và không tràn trang.
- Kiểm tra Demo trên trình duyệt ở 390×844, 768×1024, 1440×900; sự kiện 09:15 giữ nguyên trong cả hai chế độ.

**Kết quả:** Nhánh `fix/planner-followup-leader-spec-kent`; 50/50 Node tests, TypeScript, Vite build và `git diff --check` đạt.

**Ghi chú**
- Chưa chạy API E2E có đăng nhập. Vite cảnh báo chunk lớn; test SSR phát cảnh báo WebSocket sandbox nhưng toàn bộ assertion đạt.

## 2026-11-13 — Add responsive Planner month view

**Mục tiêu:** Bổ sung lịch tháng dễ đọc mà vẫn giữ lịch tuần thu gọn và timeline chi tiết.

**Đã làm**
- Thêm lưới tháng bắt đầu từ thứ Hai, đủ 4–6 hàng, ngày ngoài tháng, sự kiện đúng phút và màu từ dữ liệu hiện có; mở agenda khi chọn ngày hoặc nút `+N lịch khác`.
- Hiển thị trạng thái Rảnh/Bận chỉ để xem trong ô ngày và các khoảng giờ chính xác trong agenda; giữ đề xuất khác với lịch đã xác nhận.
- Thêm điều hướng Tháng/Tuần/Chi tiết giờ; chọn ngày ở Tháng rồi về Tuần sẽ mở tuần tương ứng. Chuyển chế độ không ghi dữ liệu hay gọi API.
- Kiểm tra trực tiếp 390×844, 768×1024, 1440×900: lịch tháng, điều hướng, agenda, chuyển chế độ, phím Escape và không tràn ngang; sửa lỗi agenda bị cắt bởi khung nội dung.

**Kết quả:** Nhánh `fix/planner-followup-leader-spec-kent`; 52/52 Node tests, TypeScript, Vite build, `npm run format` và `git diff --check` đạt. Chỉ tạo commit cục bộ, chưa push hoặc mở PR.

**Ghi chú**
- Chưa chạy API E2E có đăng nhập. Vite cảnh báo bundle trên 500 kB; test SSR phát cảnh báo WebSocket sandbox nhưng toàn bộ assertion đạt.

## 2026-11-14 — Improve Planner command composer

**Mục tiêu:** Thay ô lệnh một dòng bằng composer gọn, dễ phục hồi lỗi và dùng được bằng bàn phím trên mọi chế độ lịch.

**Đã làm**
- Thêm `PlannerCommandComposer`: thu gọn 56px khi nghỉ, textarea nhiều dòng khi focus, gợi ý đúng khả năng Demo/API, Enter gửi, Shift+Enter xuống dòng, bảo vệ IME và chặn gửi trùng khi đang xử lý.
- Đưa phản hồi làm rõ/lỗi/trạng thái gần composer; giữ proposal, ActionReference và draft khi lệnh sai hoặc API lỗi; chỉ báo đã lưu sau kết quả COMMITTED hoặc thao tác Duyệt trong Demo.
- Giữ prefill từ timeline, draft khi chuyển Tuần/Tháng/Chi tiết giờ và luồng Duyệt/Từ chối; sửa no-op trên proposal để không hiểu nhầm bản xem trước cũ là thay đổi mới.
- QA trình duyệt ở 390×844, 768×1024 và 1440×900: gợi ý, multiline, focus, Escape, proposal, responsive và không tràn ngang.

**Kết quả:** Nhánh `fix/planner-followup-leader-spec-kent`; 56/56 Node tests, TypeScript, Vite build, `npm run format` và `git diff --check` đạt.

**Ghi chú**
- API E2E có đăng nhập bị chặn vì không có backend/tài khoản thử nghiệm được cấp quyền. Vite cảnh báo bundle trên 500 kB; test SSR phát cảnh báo WebSocket sandbox nhưng toàn bộ assertion đạt.

## 2026-11-14 — Final Planner UX audit

**Mục tiêu:** Audit FE-01–FE-06 và toàn bộ hành trình Planner trước khi giao bản cuối vào PR #40.

**Đã làm**
- So sánh với `origin/main`, kiểm tra phạm vi chỉ gồm frontend/tài liệu/worklog và preview tích hợp; ghi nhận `App.tsx` cùng thay đổi nhưng tự merge được theo three-way preview.
- Sửa phản hồi lệnh sai bị lặp giữa composer và vùng proposal; thêm test render hồi quy để proposal review không hiển thị phản hồi thường.
- Sửa hook GSAP dùng ref không tồn tại ở Tuần/Tháng và selector rỗng; scope vào trang luôn mount, chỉ animate phần tử thật. Phiên trình duyệt mới không còn console warning/error.
- Xác minh Tuần/Tháng/Chi tiết giờ, Free/Busy với Busy precedence, proposal không mất sau lệnh sai, Duyệt, FE-03 hide/reveal, draft đa dòng, focus bàn phím và không tràn ngang.
- Browser QA: 390×844 và 1440×900 CSS px chính xác; công cụ làm tròn target tablet thành 767×1024 CSS px. Ảnh chỉ được chụp trong phiên audit, không commit hoặc upload.

**Kết quả:** 57/57 Node tests đạt; `npx tsc --noEmit`, `npm run build`, `npm run format` và `git diff --check` đạt. Vite build còn cảnh báo chunk 634.30 kB (>500 kB); test SSR còn cảnh báo WebSocket sandbox nhưng không làm hỏng assertion.

**Giới hạn**
- API E2E có đăng nhập vẫn BLOCKED vì không có backend/tài khoản thử nghiệm được cấp quyền. FE-01 persistence và FE-06 upload/extraction còn phụ thuộc backend/contract; không có tuyên bố giả trong frontend.
- Chưa mô phỏng dark mode, largest-text hoặc bàn phím ảo thiết bị thật; đã kiểm tra focus ring, nhãn/role, reduced-motion CSS và keyboard flow trong browser desktop.
