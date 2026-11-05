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

## 2026-11-05 — Backend F1: sửa hợp đồng 1.0.1 và WP2a (biên DB)

**Mục tiêu:** tiếp nhận bàn giao backend F1 trên `feat/f1-mvp-intergration`, chốt WP0 (hợp đồng) và làm WP2a (ranh giới bảo mật, hạ tầng, bộ xác minh) để chuẩn bị WP2b.

**Đã làm**

- WP0: sửa `contracts/schemas/f1.schema.json` (kết quả `READ` dùng `anyOf`; `WorkflowStepOutcome` bắt `result` khớp schema của đúng operation); cập nhật `contracts/CHANGELOG.md` và `contracts/VALIDATION.md`.
- WP2a: migration 009 (role `sf_rpc_owner`, 6 bảng hạ tầng, FORCE RLS), 010 (`canonical_json`, `verify_rpc_request`), 011 (gỡ RPC cũ, chuyển quyền sang `sf_rpc_owner`, 27 wrapper từ chối an toàn), 012 (schema hợp đồng sinh tự động bằng `backend/scripts/generate_contract_schema_migration.py`).
- Thêm `supabase/tests/08_wp2a_contract_schema.sql`, `backend/tests/unit/test_contract_schema_migration.py` và `docs/implementation/WP2A_NOTES.md`.
- Cài Docker Desktop, Supabase CLI 3.0.0 và Python 3.12 để chạy DB local.

**Kết quả:** nhánh `feat/f1-mvp-intergration`. Checker hợp đồng pass (122 định nghĩa, 100 fixture), test hợp đồng 16/16; scheduler 33, unit 25, tests 78 pass. pgTAP local: 03, 04, 05, 08 pass; 06 còn 12/81 lỗi, 07 còn 33/58 lỗi (đều thuộc WP2b); kết quả giống nhau khi replay từ DB trống và khi nâng cấp từ baseline 008.

**Ghi chú**

- Wrapper mới chỉ kiểm tra request rồi trả `UNSUPPORTED_OPERATION`; hành vi nghiệp vụ làm ở WP2b/WP2c.
- Chưa chạy: harness đồng thời, JWT thật qua HTTP, CI mới. Chưa đụng tới project Supabase trên cloud.

