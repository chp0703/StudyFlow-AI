# Biểu Mẫu Đặc Tả Công Việc Cho AI Coding Agent (Task Specification Template)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Chuẩn hóa mọi phiếu giao việc cho một phiên làm việc của OpenAI Codex hoặc Claude Code theo đúng 6 vai trò (`FE-1`, `FE-2`, `BE-1`, `BE-2`, `BE-3`, `BE-4`) |
| **Thẩm quyền (Authority)** | Biểu mẫu bắt buộc thuộc [`INTEGRATION_PROTOCOL.md`](../INTEGRATION_PROTOCOL.md) |
| **Chủ sở hữu (Owner)** | Project Owner & `BE-4` (Coordinator) |

---

## Cách sử dụng

Sao chép toàn bộ khung Markdown bên dưới khi tạo một task mới hoặc khi gửi prompt giao việc cho Codex / Claude Code. **Không giao các task mơ hồ kiểu "hoàn thiện F1"** — mọi task bắt buộc phải có `Allowed Files`, `Forbidden Files`, `Acceptance Criteria` kiểm chứng được và lệnh chạy test cụ thể.

---

```markdown
# TASK SPEC: <TASK-ID> — <Tên công việc ngắn gọn, rõ mục tiêu>

| Trường thông tin | Nội dung |
|---|---|
| **Task ID & Title** | `<VD: FE1-003 — Triển khai Sticky Date Header và hiển thị ngày cụ thể cạnh thứ>` |
| **Feature / F1 Group** | `<VD: Nhóm F — FE-1 (Task / Planner / Calendar / Confirmation)>` |
| **Owner Role** | `<Chọn đúng 1: FE-1 | FE-2 | BE-1 | BE-2 | BE-3 | BE-4>` |
| **Co-Reviewer Role(s)** | `<VD: FE-2, BE-4>` |
| **Target Branch** | `<VD: feat/fe1-sticky-date-header>` (tạo từ `origin/main`) |
| **Base Commit** | `<SHA của origin/main tại thời điểm bắt đầu>` |
| **Contract / Schema Version** | `Contract Package 1.0.1 — APPROVED` / `Logical Schema F1 v1.1` *(hoặc ghi rõ mã Addendum nếu có)* |
| **Status** | `<NOT_STARTED | IN_PROGRESS | BLOCKED | NEEDS_DECISION | DONE | DEFERRED>` |

---

## 1. Mục tiêu & Giá trị Người dùng (Objective / User Value)
- <Mô tả ngắn gọn bài toán cần giải quyết và giá trị mang lại cho người dùng hoặc hệ thống>.

## 2. Nguồn Yêu cầu & Tài liệu Tham chiếu (Source Requirement)
- **Mã yêu cầu:** `<VD: REQ-F1-10 trong PRODUCT_REQUIREMENTS_AND_DECISIONS.md>`
- **Tài liệu bắt buộc đọc:**
  - `AGENTS.md` (hoặc `CLAUDE.md`)
  - `docs/team-coordination/roles/<ROLE>.md`
  - `docs/team-coordination/FILE_OWNERSHIP.md`
  - `<Đường dẫn tới contract / ADR / WP notes liên quan>`

## 3. Hiện trạng & Bằng chứng Đầu vào (Current State / Evidence)
- **Hiện trạng trên `main`:** <Mô tả những gì code hiện tại đang làm ở các file liên quan>.
- **Khoảng trống cần xử lý:** <Mô tả phần còn thiếu hoặc cần sửa>.

## 4. Phụ thuộc (Dependencies)
- **Upstream Dependencies (Phải xong trước task này):** `<VD: COORD-002 | Không có>`
- **Open Decisions liên quan:** `<VD: OD-001 (nếu chưa chốt thì task phải dừng ở NEEDS_DECISION) | Không có>`
- **Downstream Roles bị ảnh hưởng:** `<VD: FE-1, INT-002>`

## 5. Phạm vi File Được Phép & Bị Cấm (File Ownership Scope)

### 5.1. Allowed Files / Paths (CHỈ được sửa/tạo trong danh sách này)
- `<path/to/allowed/file1>`
- `<path/to/allowed/file2>`

### 5.2. Forbidden Files / Paths (CẤM chạm vào)
- `contracts/**` và `docs/database/schema_F1.md` *(trừ khi đây là task cập nhật contract đã có phê duyệt của Project Owner)*
- `supabase/migrations/202611050001_*.sql` .. `202611050021_*.sql` *(migrations lịch sử bất biến)*
- `backend/tests/acceptance_sol/**`, `backend/tests/acceptance_api_sol/**`, `supabase/tests/06_*.sql`, `07_*.sql` *(test nghiệm thu độc lập)*
- `<Các thư mục thuộc vai trò khác>`

## 6. Hành vi Bắt buộc (Required Behavior)
1. <Quy định chi tiết hành vi 1, bao gồm cả xử lý trường hợp biên / lỗi>.
2. <Quy định chi tiết hành vi 2>.
3. <Bảo toàn các bất biến liên quan (owner isolation, explicit approval, idempotency, accessibility...)>.

## 7. Ngoài Phạm vi (Out-of-Scope)
- <Liệt kê rõ những việc KHÔNG làm trong task này để ngăn agent tự suy diễn mở rộng scope>.

## 8. Tiêu chí Nghiệm thu (Acceptance Criteria — Kiểm chứng được)
- [ ] **AC-1:** <Điều kiện kiểm chứng cụ thể 1>.
- [ ] **AC-2:** <Điều kiện kiểm chứng cụ thể 2>.
- [ ] **AC-3:** Không vi phạm `FILE_OWNERSHIP.md` và không làm gãy bất kỳ test hiện hữu nào.
- [ ] **AC-4:** `git diff --check` sạch, không chứa secret/credential/file `.env`.

## 9. Kiểm thử Bắt buộc (Required Tests)
- **Unit / Component Tests cần viết mới hoặc cập nhật:**
  - `<Đường dẫn file test và các kịch bản chính>`
- **Lệnh kiểm tra bắt buộc phải chạy và báo cáo số lượng pass/fail:**
  ```powershell
  <Lệnh test 1>
  <Lệnh test 2>
  git diff --check
  ```

## 10. Tác động Bảo mật & Di trú Dữ liệu (Security & Data Migration Impact)
- **Secret / Auth / RLS Impact:** `<Không có | Mô tả rõ>`
- **Database Migration Impact:** `<Không có | Tạo migration mới số hiệu ...>`
- **Backward Compatibility:** `<Tương thích ngược hoàn toàn | Cần phối hợp với ...>`

## 11. Sản phẩm Bàn giao & Liên kết Bằng chứng (Deliverables & Evidence)
- **Deliverables:** <Danh sách file code/test/tài liệu bàn giao>.
- **Branch / Commit SHA / PR URL:** `<Điền sau khi thực hiện thực tế; không bịa đặt>`
- **Handoff Roles:** `<Danh sách các vai trò nhận bàn giao tiếp theo>`
```
