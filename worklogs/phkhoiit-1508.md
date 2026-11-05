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
- Thêm skill `ui-ux-pro-max` vào `.claude/skills/` và quy tắc ghi worklog vào `CLAUDE.md`.

**Kết quả:** PR #13 (`feat/pages`). `tsc --noEmit`, `npm run build` và `npm run format` pass; test `plannerAgent`, `proposal` và `conversationHistory` pass. Review PR #11 (docs kiến trúc Supabase + FastAPI) dưới dạng nhận xét.

**Ghi chú**

- Agent chỉ hiểu lệnh đơn giản (chưa có phút, ngày cụ thể, "tuần sau"); phản hồi chat và tuần đang xem ở Lập kế hoạch reset khi đổi trang.
- Nút chuyển tuần cao 32px, nhỏ hơn mức 44px trong `DESIGN.md`; còn CSS cũ không dùng.
- Chưa kiểm tra giao diện điện thoại (~400px); drawer lịch sử trên điện thoại chưa có animation.
- Animation GSAP luôn chạy, không kiểm tra `prefers-reduced-motion` (quyết định của nhóm).
- Đề xuất, khung giờ rảnh/bận và việc chỉ lưu trong bộ nhớ (mất khi tải lại trang); thời hạn đề xuất 10 phút và khối 60 phút là giá trị đề xuất, SRS chưa chốt.
