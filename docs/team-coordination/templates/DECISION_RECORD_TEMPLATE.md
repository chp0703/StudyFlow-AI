# Biểu Mẫu Bản Ghi Quyết Định Kiến Trúc & Sản Phẩm (Decision Record Template)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Chuẩn hóa việc ghi nhận, phân tích phương án và phê duyệt các quyết định sản phẩm/hợp đồng/kiến trúc (đặc biệt khi giải quyết các mục trong [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) và [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md)) |
| **Thẩm quyền (Authority)** | Biểu mẫu bắt buộc khi đóng một Open Decision hoặc đề xuất thay đổi Contract `1.0.1` / Schema `v1.1` |
| **Chủ sở hữu (Owner)** | Project Owner (Phê duyệt) · Domain Owner & `BE-4` (Soạn thảo) |

---

## Cách sử dụng

Sao chép mẫu bên dưới khi lập đề xuất giải quyết một mục trong [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) hoặc khi tạo ADR mới. Giữ trạng thái là `PROPOSED` cho đến khi Project Owner xác nhận phê duyệt rõ ràng.

---

```markdown
# DECISION RECORD: <DECISION-ID> — <Tiêu đề quyết định ngắn gọn>

| Thuộc tính | Giá trị |
|---|---|
| **Decision ID** | `<VD: DR-F1-001 / Giải quyết OD-001>` |
| **Status** | `<PROPOSED | APPROVED | REJECTED | SUPERSEDED>` |
| **Date / Time & Timezone** | `<YYYY-MM-DD HH:mm> (Asia/Ho_Chi_Minh)` |
| **Proposer Role(s)** | `<VD: BE-1, BE-4>` |
| **Required Reviewer Role(s)** | `<VD: BE-2, FE-1, FE-2>` |
| **Approver** | `Project Owner` *(chỉ ghi ĐÃ DUYỆT khi có xác nhận thực tế)* |
| **Approval Evidence** | `<Trích dẫn xác nhận của Project Owner / PR / Commit SHA; ghi PENDING nếu chưa duyệt>` |
| **Supersedes** | `<Không có | Mã quyết định hoặc đoạn tài liệu cũ được thay thế>` |
| **Superseded By** | `<Không có | Mã quyết định mới hơn>` |

---

## 1. Bối cảnh & Vấn đề Cần Giải quyết (Context)
- **Nguồn phát sinh:** `<Liên kết tới REQ-F1-xx trong PRODUCT_REQUIREMENTS_AND_DECISIONS.md hoặc OD-xxx trong OPEN_DECISIONS.md>`.
- **Hiện trạng trong Contract `1.0.1` / Schema `v1.1` / Codebase (`7837050`):**
  - <Mô tả chính xác những gì đang được quy định hiện tại>.
- **Lý do cần ra quyết định:**
  - <Giải thích mâu thuẫn hoặc khoảng trống kỹ thuật cần chốt>.

---

## 2. Các Phương án Lựa chọn (Options Considered)

### Phương án 1: `<Tên phương án 1>`
- **Mô tả kỹ thuật:** <Chi tiết>.
- **Ưu điểm:** <...>.
- **Nhược điểm / Rủi ro:** <...>.

### Phương án 2: `<Tên phương án 2>`
- **Mô tả kỹ thuật:** <Chi tiết>.
- **Ưu điểm:** <...>.
- **Nhược điểm / Rủi ro:** <...>.

---

## 3. Quyết định Được Chọn (Decision)
- **Phương án được chọn:** `<Phương án X — hoặc ghi CHỜ PROJECT OWNER CHỐT nếu Status = PROPOSED>`.
- **Chi tiết quy định chính thức sau quyết định:**
  - <Nêu chính xác tên trường, kiểu dữ liệu, enum, quy tắc xác thực hoặc hành vi UI/BE>.

---

## 4. Lý do & Các Phương án Bị Từ chối (Rationale & Alternatives Rejected)
- **Lý do chọn:** <Vì sao phương án này bảo toàn tốt nhất các bất biến của F1 (security, determinism, canonical JSON, owner isolation...)>.
- **Lý do từ chối các phương án khác:** <Giải thích rõ>.

---

## 5. Phạm vi Ảnh hưởng (Affected Contracts / Modules / Roles)
- **Official Contracts (`contracts/`):** `<Không ảnh hưởng | Liệt kê file cần cập nhật: openapi.yaml, f1.schema.json, service-contract.json, data-contract.json>`
- **Logical Schema (`docs/database/schema_F1.md`):** `<Không ảnh hưởng | Mục cần cập nhật>`
- **Database & Migrations (`supabase/`):** `<Không ảnh hưởng | Cần tạo migration mới 022+ và chạy lại generator 012>`
- **Backend Modules (`backend/app/`):** `<Liệt kê đường dẫn>`
- **Frontend Modules (`frontend/src/`):** `<Liệt kê đường dẫn>`
- **Vai trò bị ảnh hưởng (`Affected Roles`):** `<FE-1 | FE-2 | BE-1 | BE-2 | BE-3 | BE-4>`
- **Task IDs được mở khóa trong `TASK_BOARD.md`:** `<VD: BE1-001, FE1-001, INT-001>`

---

## 6. Kế hoạch Triển khai, Di trú & Kiểm thử (Rollout / Migration / Test Plan)
1. **Bước Contract (`INT-001`):** <Cập nhật schema/fixtures và chạy `python -B contracts/check_contract.py`>.
2. **Bước Migration / Backend:** <Tạo migration mới, kiểm tra `upgrade route` và chạy unit/acceptance tests>.
3. **Bước Frontend:** <Cập nhật `frontend/src/api/types.ts`, `mappers.ts` và component UI>.
4. **Các bài kiểm thử nghiệm thu bắt buộc:**
   - `<Liệt kê test case dương tính (valid) và âm tính (invalid)>`.
```
