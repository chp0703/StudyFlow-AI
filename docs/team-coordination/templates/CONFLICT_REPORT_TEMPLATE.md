# Biểu Mẫu Báo Cáo Xung Đột & Điểm Chặn (Conflict & Blocker Report Template)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Cung cấp cấu trúc chuẩn để AI coding agent báo cáo ngay khi phát hiện mâu thuẫn giữa các tài liệu/contract, xung đột quyền sở hữu file (`File Ownership`), hoặc thiếu quyết định sản phẩm mà agent không được phép tự suy diễn |
| **Thẩm quyền (Authority)** | Biểu mẫu bắt buộc theo Mục 3 của [`AGENTS.md`](../../../AGENTS.md) và Mục 6 của [`INTEGRATION_PROTOCOL.md`](../INTEGRATION_PROTOCOL.md) |
| **Chủ sở hữu (Owner)** | Project Owner & `BE-4` (Coordinator) |

---

## Cách sử dụng

Khi gặp một trong các điều kiện dừng (`Stop Conditions`) trong lúc làm task, agent **không được tự ý sửa bừa hoặc chọn đại một phía**. Hãy dừng phần việc bị xung đột, giữ nguyên các phần độc lập an toàn, và xuất báo cáo theo mẫu bên dưới:

---

```markdown
# CONFLICT / BLOCKER REPORT: <CONFLICT-ID> — <Tóm tắt ngắn gọn xung đột>

| Thuộc tính | Giá trị |
|---|---|
| **Report ID** | `<VD: CR-20261111-01>` |
| **Task ID đang thực hiện** | `<VD: BE1-001>` |
| **Reporting Role** | `<FE-1 | FE-2 | BE-1 | BE-2 | BE-3 | BE-4>` |
| **Loại xung đột** | `<CONTRACT_CONFLICT | PRODUCT_REQUIREMENT_CONFLICT | FILE_OWNERSHIP_CONFLICT | GIT_BRANCH_UNSAFE | ENVIRONMENT_BLOCKER>` |
| **Mức độ ảnh hưởng** | `<BLOCKING_CURRENT_TASK | PARTIAL_BLOCKER | NEEDS_CLARIFICATION>` |
| **Vai trò cần phân xử** | `<Project Owner | BE-4 | BE-1 | BE-2 | BE-3 | FE-1 | FE-2>` |

---

## 1. Mô tả Chi tiết Hai Nguồn hoặc Hai Ranh giới Xung đột (Conflicting Sources)
- **Nguồn A (kèm đường dẫn file & dòng):**
  - `<VD: contracts/schemas/f1.schema.json#L... quy định priority là enum "LOW" | "NORMAL" | "HIGH">`
- **Nguồn B (kèm đường dẫn file & dòng hoặc yêu cầu):**
  - `<VD: Yêu cầu mới REQ-F1-03 yêu cầu priority nhận các giá trị 0.1, 0.5, 1>`
- **Điểm mâu thuẫn cụ thể:**
  - <Giải thích rõ vì sao không thể thỏa mãn đồng thời cả hai nếu không có quyết định hoặc thay đổi contract>.

---

## 2. Phạm vi Bị Ảnh hưởng (Impact Scope)
- **Các file / module bị chặn chưa thể sửa:**
  - `<path/to/file1>`
  - `<path/to/file2>`
- **Các phần việc độc lập VẪN có thể làm an toàn (nếu có):**
  - `<Mô tả những phần không bị ảnh hưởng đã/đang được thực hiện>`

---

## 3. Đề xuất Phương án Giải quyết (Proposed Resolution Options)
- **Phương án 1:** <Mô tả + tác động lên contract/code/migration>.
- **Phương án 2:** <Mô tả + tác động lên contract/code/migration>.
- **Khuyến nghị kỹ thuật từ Agent:** <Nêu khuyến nghị dựa trên thứ tự ưu tiên nguồn sự thật tại `PROJECT_SOURCE_OF_TRUTH.md`, nhưng không tự ý thực thi khi chưa được duyệt>.

---

## 4. Quyết định Cần từ Project Owner / Chủ sở hữu Miền (Action Needed)
- **Người cần chốt:** `<Project Owner / Role Owner>`
- **Câu hỏi cụ thể cần trả lời để mở khóa (`Unblock`):**
  1. `<Câu hỏi 1>`
  2. `<Câu hỏi 2>`
```
