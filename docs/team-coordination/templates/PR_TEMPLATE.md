# Biểu Mẫu Mô Tả Pull Request (Pull Request Template)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Chuẩn hóa nội dung mọi Pull Request mở về nhánh tích hợp hoặc `main`, đảm bảo kiểm soát chặt phạm vi ownership, tác động contract/migration, bảo mật secret và bằng chứng kiểm thử thực tế |
| **Thẩm quyền (Authority)** | Biểu mẫu bắt buộc thuộc [`INTEGRATION_PROTOCOL.md`](../INTEGRATION_PROTOCOL.md) |
| **Chủ sở hữu (Owner)** | Project Owner & `BE-4` (Coordinator) |

---

## Cách sử dụng

Khi tạo Pull Request (luôn để ở chế độ **Draft** hoặc ghi rõ chưa merge nếu chưa đủ review), sao chép và điền đầy đủ mẫu bên dưới:

---

```markdown
# PR: [<ROLE>] <TASK-ID> — <Tiêu đề ngắn gọn mô tả thay đổi>

## 1. Thông tin Định danh (Metadata)
- **Task ID(s):** `<VD: FE1-003>` (tham chiếu [`docs/team-coordination/TASK_BOARD.md`](docs/team-coordination/TASK_BOARD.md))
- **Owner Role:** `<FE-1 | FE-2 | BE-1 | BE-2 | BE-3 | BE-4>`
- **Required Reviewers:**
  - **Domain Owner / Co-Reviewer(s):** `<VD: FE-2, BE-4>`
  - **Final Merge Approver:** `Project Owner`
- **Base Branch:** `main` (Base Commit SHA: `<base-sha>`)
- **Head Branch:** `<feat/role-slug>` (Head Commit SHA: `<head-sha>`)

---

## 2. Tóm tắt Thay đổi (Summary)
- **Mục tiêu:** <Nêu ngắn gọn PR này giải quyết vấn đề gì>.
- **Các thay đổi chính:**
  - <Điểm chính 1>
  - <Điểm chính 2>

---

## 3. Danh sách File & Module Thay đổi (Files / Modules Changed)
| Đường dẫn File | Loại thay đổi (`Added` / `Modified` / `Deleted`) | Primary Owner theo `FILE_OWNERSHIP.md` | Ghi chú Co-Review (nếu là Shared File) |
|---|---|---|---|
| `<path/to/file>` | `<Added/Modified>` | `<Role>` | `<Không / Cần Role X review>` |

---

## 4. Tác động Hợp đồng & Cơ sở dữ liệu (API / Contract / DB Impact)
- **Phiên bản Contract / Schema áp dụng:** `Package 1.0.1` / `Schema F1 v1.1`
- **Thay đổi trên `contracts/` (`openapi.yaml`, `f1.schema.json`, `service-contract.json`, `data-contract.json`):**
  - [ ] **Không có thay đổi** trên `contracts/` hoặc `docs/database/schema_F1.md`.
  - [ ] **Có thay đổi đã được phê duyệt** theo [`CONTRACT_CHANGE_PROTOCOL.md`](docs/team-coordination/CONTRACT_CHANGE_PROTOCOL.md) (Mã quyết định: `<OD-xxx / ADR-xxx>`).
- **Thay đổi trên Database / Migrations (`supabase/migrations/`):**
  - [ ] **Không có thay đổi** về SQL migration.
  - [ ] **Có thêm migration mới:** `<Tên file migration mới>` (Xác nhận: **không** sửa các migration lịch sử `001`–`021`).
- **Tương thích ngược (Backward Compatibility):**
  - `<Mô tả rõ tính tương thích với các nhánh/module đang chạy của các role khác>`.

---

## 5. Kết quả Kiểm thử & Phân biệt Môi trường Thật vs. Giả lập (Test Results & Real-vs-Mock Distinction)

### 5.1. Bảng kết quả chạy lệnh kiểm thử thực tế
| Lệnh kiểm thử đã chạy | Kết quả (`PASS` / `FAIL` / `NOT_RUN`) | Số lượng (`Passed / Failed / Skipped`) | Loại môi trường (`Pure/Unit` · `Mock Transport` · `Local Supabase DB` · `Live Provider/Browser`) |
|---|---|---|---|
| `<VD: python -B contracts/check_contract.py>` | `<PASS / NOT_RUN>` | `<...>` | `Static Contract Check` |
| `<VD: python -B -m unittest discover -s backend/tests/unit -t . -v>` | `<PASS / NOT_RUN>` | `<...>` | `Pure / Unit` |
| `<VD: node --test ...>` | `<PASS / NOT_RUN>` | `<...>` | `Node Unit Test` |
| `<VD: npm --prefix frontend run build && npx --prefix frontend tsc --noEmit>` | `<PASS / NOT_RUN>` | `<...>` | `TypeScript & Vite Build` |

### 5.2. Phân biệt rõ Mock / Demo vs. Live Integration
- **Những gì đã được chứng minh bằng môi trường thật trong PR này:**
  - `<Mô tả trung thực>`
- **Những gì mới chỉ kiểm chứng qua Fixture / Mock / Chế độ Demo hoặc chưa chạy (`NOT_RUN`):**
  - `<Mô tả trung thực; không tuyên bố mock là live acceptance>`

---

## 6. Bằng chứng Đã Làm sạch (Sanitized Logs / Screenshots)
- <Đính kèm trích đoạn output kiểm thử hoặc ảnh chụp giao diện đã loại bỏ hoàn toàn JWT, API key, email cá nhân hoặc đường dẫn nhạy cảm>.

---

## 7. Giới hạn Đã Biết & Blockers (Known Limitations & Blockers)
- **Known Limitations:** `<Không có | Nêu rõ>`
- **Blockers / Open Decisions chờ chốt:** `<Không có | Liên kết tới OD-xxx>`
- **Vai trò cần nhận bàn giao tiếp theo (`Handoff Roles`):** `<FE-1 / FE-2 / BE-1 / BE-2 / BE-3 / BE-4>`

---

## 8. Checklist An toàn & Bảo mật Bắt buộc (Mandatory Safety & Security Checklist)
- [ ] **No Main Commit / Push:** Không có commit hoặc push trực tiếp nào lên nhánh `main`; PR này không bật auto-merge và không tự merge.
- [ ] **No Secrets Exposed:** Đã kiểm tra toàn bộ diff — không có `DEEPSEEK_API_KEY`, Supabase service-role key, `RPC_SIGNING_SECRET_BASE64`, DB password, JWT thật hoặc file `.env` / `.env.local`.
- [ ] **No Destructive Changes:** Không sửa các migration lịch sử `001`–`021`, không xóa hoặc làm yếu assertion của các bộ test nghiệm thu độc lập (`acceptance_sol`, `acceptance_api_sol`, `06_sol_rpc_boundary.sql`, `07_sol_internal_addendum.sql`).
- [ ] **Ownership Respected:** Mọi file thay đổi đều tuân thủ [`FILE_OWNERSHIP.md`](docs/team-coordination/FILE_OWNERSHIP.md).
- [ ] **Clean Diff:** Đã chạy `git diff --check` và xác nhận 0 lỗi khoảng trắng / conflict marker.
```
