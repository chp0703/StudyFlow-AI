# Báo cáo kiểm tra contract

Ngày kiểm tra: **05/11/2026**, múi giờ Việt Nam.

| Hạng mục | Kết quả |
|---|---|
| JSON Schema 2020-12 | PASS — 104 definitions |
| OpenAPI 3.1.1 | PASS — 8 paths; external schema references resolve local |
| Service registry | PASS — đúng 10 operation F1, arguments/result schema tồn tại |
| Data mapping | PASS — đủ field của 10 entity, PK/nullability khớp shared schema; 4 infrastructure records |
| Đối chiếu schema F1 nguồn | PASS — tên field 10 entity và catalog operation khớp docs/database/schema_F1.md |
| Ví dụ | PASS — 88 positive/negative fixtures, gồm policy custom, deadline/date/timezone, stale/partial và RPC request shape |
| Liên kết Markdown nội bộ của bộ contract và trang dẫn | PASS |
| git diff --check | PASS |
| Backend/DB/auth/UI runtime | **NOT_RUN**; chưa có implementation trong phạm vi thay đổi này |

Môi trường kiểm tra: Python 3.13.9, jsonschema 4.25.0, openapi-spec-validator 0.7.2. Validator OpenAPI được cài trong thư mục tạm để kiểm tra, không thêm dependency runtime cho frontend/backend. Người dùng có thể tạo môi trường riêng bằng requirements-check.txt và chạy check_contract.py.

Kiểm tra schema/invariant thuần không chứng nhận chữ ký HMAC, RLS/grants, transaction/rollback, concurrency hoặc luồng UI. Fixture RPC có signature giả chỉ kiểm tra cấu trúc JSON. Các ca cần chạy thật được liệt kê trong acceptance-cases.md và vẫn NOT_RUN.
