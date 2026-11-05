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
- Thêm skill `ui-ux-pro-max` vào `.claude/skills/` và quy tắc ghi worklog vào `CLAUDE.md`.

**Kết quả:** PR #13 (`feat/pages`). `tsc --noEmit`, `npm run build` và `npm run format` pass; test `plannerAgent` và `conversationHistory` 7/7 pass. Review PR #11 (docs kiến trúc Supabase + FastAPI) dưới dạng nhận xét.

**Ghi chú**

- Agent chỉ hiểu lệnh đơn giản (chưa có phút, ngày cụ thể, "tuần sau"); phản hồi chat và tuần đang xem ở Lập kế hoạch reset khi đổi trang.
- Nút chuyển tuần cao 32px, nhỏ hơn mức 44px trong `DESIGN.md`; còn CSS cũ không dùng.
- Chưa kiểm tra giao diện điện thoại (~400px).
