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
