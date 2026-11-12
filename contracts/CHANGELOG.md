# Contract changelog

## 1.0.1 — 05/11/2026 — APPROVED / CHÍNH THỨC

- Thêm 6 internal RPC (ensure_user_context, list_time_windows, get_workflow_context, get_workflow_continuation, initialize_workflow_continuation, checkpoint_workflow_continuation) và hạ tầng `workflow_continuations` theo phụ lục A/B/C/D đã duyệt; giữ 8 endpoint, 10 operation và logical schema 1.1.
- Sửa lỗi schema: `ToolResult` READ `data` dùng `anyOf` thay `oneOf` (kết quả rỗng `{items: [], next_cursor: null}` khớp cả hai kiểu danh sách nên bị loại sai). Ràng buộc theo operation chuyển sang `WorkflowStepOutcome`: khi `disposition=SUCCEEDED`, `result` phải khớp `<operation>Result`. Không đổi fixture và không nới lỏng thêm.

## 1.0.0 — 05/11/2026 — APPROVED / CHÍNH THỨC

- Team đã phê duyệt theo xác nhận của người dùng ngày 05/11/2026; phạm vi gồm cả ba ranh giới và IC-01–IC-08, ghi tại APPROVAL.md.
- Chuyển từ REVIEW_READY sang APPROVED và đồng bộ metadata/tài liệu kiến trúc; giữ nguyên package 1.0.0, schema 1.1 và toàn bộ giao diện đã bàn giao.

- Cụ thể hóa API FE–BE, 10 Tool/Service operation và mapping 10 entity Planner schema v1.1 trong cùng một package.
- Thêm OpenAPI 3.1.1 và JSON Schema 2020-12 dùng chung, typed presentation cho confirmation và lỗi transport.
- Chốt RPC attestation, owner row lock, retry/idempotency, source-message/presentation persistence và policy custom.
- Thêm fixtures hợp lệ/không hợp lệ, kiểm tra tĩnh và ca nghiệm thu runtime có owner.
- Giữ `schema_version="1.1"`; không thay logical field/state/scope. Approval thiết kế không chứng nhận implementation hoặc kiểm thử runtime đã hoàn tất.
