# Contract changelog

## 1.0.0 — 05/11/2026 — REVIEW_READY

- Cụ thể hóa API FE–BE, 10 Tool/Service operation và mapping 10 entity F1 v1.1 trong cùng một package.
- Thêm OpenAPI 3.1.1 và JSON Schema 2020-12 dùng chung, typed presentation cho confirmation và lỗi transport.
- Chốt đề xuất RPC attestation, owner row lock, retry/idempotency, source-message/presentation persistence và policy custom.
- Thêm fixtures hợp lệ/không hợp lệ, kiểm tra tĩnh và ca nghiệm thu runtime có owner.
- Giữ `schema_version="1.1"`; không thay logical field/state/scope. Quyết định tích hợp mới chưa tự nhận đã được cả nhóm phê duyệt.
