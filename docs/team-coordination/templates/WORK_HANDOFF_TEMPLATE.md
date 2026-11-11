# Biểu Mẫu Bàn Giao Công Việc Giữa Các Phiên / Vai Trò (Work Handoff Template)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Chuẩn hóa báo cáo bàn giao khi kết thúc một phiên làm việc của Codex/Claude hoặc khi một role (`BE-1`..`BE-4`, `FE-1`..`FE-2`) hoàn tất phần việc tiền đề để chuyển cho role phụ thuộc tiếp theo |
| **Thẩm quyền (Authority)** | Biểu mẫu bắt buộc theo Mục 5 của [`INTEGRATION_PROTOCOL.md`](../INTEGRATION_PROTOCOL.md) |
| **Chủ sở hữu (Owner)** | Project Owner & `BE-4` (Coordinator) |

---

## Cách sử dụng

Mỗi phiên agent khi kết thúc một task phải xuất báo cáo theo đúng cấu trúc 10 mục bên dưới để thành viên tiếp theo hoặc phiên agent kế tiếp có thể tiếp nhận ngay mà không cần đọc lại toàn bộ lịch sử chat.

---

```markdown
# WORK HANDOFF: <TASK-ID> (<OWNER-ROLE> → <DOWNSTREAM-ROLES>)

## 1. Định danh Phiên & Nhiệm vụ (Identity)
- **Task ID & Title:** `<VD: BE2-002 — Approval-Time Validation>`
- **Owner Role:** `<FE-1 | FE-2 | BE-1 | BE-2 | BE-3 | BE-4>`
- **Agent / Tool Used:** `<OpenAI Codex | Claude Code>`
- **Branch Name:** `<feat/be2-approval-validation>`
- **PR URL / Status:** `<URL hoặc "Local branch ready for push / Draft PR">`
- **Timestamp:** `<YYYY-MM-DD HH:mm> (Asia/Ho_Chi_Minh)`

## 2. Mốc Git (Git Commits)
- **Base Branch & Base Commit SHA:** `main` @ `<base-sha>`
- **Head Commit SHA(s):** `<head-sha>`
- **Working Tree Status:** `<Clean | Mô tả rõ nếu còn file chưa commit>`

## 3. Danh sách File Thay đổi & Kiểm chứng Ownership (Files Changed)
| Đường dẫn File | Thao tác (`A`/`M`/`D`) | Thuộc Ownership của Role | Co-Reviewer cần thiết |
|---|---|---|---|
| `<path/to/file>` | `<M>` | `<Role>` | `<Không / Role Y>` |

## 4. Phiên bản Contract & Schema Áp dụng (Contract / Schema Version)
- **Contract Package:** `1.0.1 — APPROVED` *(hoặc phiên bản sau addendum nếu đã duyệt)*
- **Logical Schema:** `F1 v1.1` (`schema_version: "1.1"`)

## 5. Thay đổi Giao diện API / Service / DTO (API & Contract Changes)
- **HTTP Endpoints bị ảnh hưởng:** `<Không có | Liệt kê>`
- **Request / Response / Error Codes:** `<Không đổi so với 1.0.1 | Mô tả chi tiết>`

## 6. Chi tiết Database Migration (Migration Details)
- **File Migration mới (nếu có):** `<Không có | supabase/migrations/...>`
- **Bảng / RPC / RLS bị ảnh hưởng:** `<Không có | Liệt kê>`
- **Xác nhận bảo toàn lịch sử:** Đã giữ nguyên 100% các migration `202611050001`..`202611050021`.

## 7. Kết quả Chạy Kiểm thử Thực tế (Test Execution Summary)
| Lệnh đã chạy | Trạng thái (`PASS`/`FAIL`/`NOT_RUN`) | Số lượng (`Pass / Fail / Skip`) | Ghi chú môi trường (`Mock` vs `Local DB` vs `Live`) |
|---|---|---|---|
| `<command>` | `<PASS>` | `<X pass, 0 fail>` | `<...>` |

## 8. Bằng chứng Đã Làm sạch (Sanitized Evidence)
- **Check secret & whitespace:** `git diff --check` → `PASS` (0 lỗi, 0 secret/token).
- **Trích dẫn kết quả chính:** `<Tóm tắt ngắn gọn kết quả kiểm chứng>`.

## 9. Giới hạn Đã Biết & Điểm Chặn (Known Limitations & Blockers)
- **Những gì ĐÃ hoàn thành trong phiên này:**
  - <...>
- **Những gì CHƯA hoàn thành / Giới hạn đã biết:**
  - <...>
- **Blockers / Open Decisions cần giải quyết:**
  - `<Không có | Mã OD-xxx>`

## 10. Hướng dẫn cho Vai trò Tiếp nhận Tiếp theo (Downstream Handoff Instructions)
- **Các vai trò bị ảnh hưởng (`Impacted Roles`):** `<VD: FE-1, BE-4>`
- **Task IDs tiếp theo có thể bắt đầu:** `<VD: FE1-004, INT-002>`
- **Lưu ý kỹ thuật khi tích hợp:**
  1. <Hướng dẫn cụ thể 1 cho role tiếp theo>.
  2. <Hướng dẫn cụ thể 2>.
```
