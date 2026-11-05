# Báo cáo kiểm tra contract

Ngày cập nhật: **05/11/2026**, múi giờ Việt Nam.

Package **1.0.1** (logical `schema_version="1.1"`) đã được phê duyệt chính thức theo [APPROVAL.md](APPROVAL.md), kế thừa nền tảng `1.0.0` (`b629a5e`) và bổ sung phụ lục RPC nội bộ đã duyệt (`docs/implementation/INTERNAL_RPC_ADDENDUM_PROPOSAL.md`). Trong phạm vi bàn giao WP0 chỉ chỉnh sửa file tĩnh trong `contracts/`, không tự thực thi lệnh terminal/test; việc chạy `contracts/check_contract.py` và bộ test độc lập do Sol thực hiện bên ngoài.

| Hạng mục | Phạm vi / Trạng thái |
|---|---|
| Metadata phê duyệt | Đồng bộ `contract_version="1.0.1"`, `schema_version="1.1"`, trạng thái `APPROVED` ở API, schema bundle, service/data registry và manifest; ngày hiệu lực 05/11/2026 |
| Bảo toàn phạm vi F1 v1.1 | Giữ nguyên 8 HTTP endpoint, 10 operation nghiệp vụ/LLM, 10 entity nghiệp vụ logic và 12 helper RPC nội bộ từ bản `1.0.0` |
| JSON Schema 2020-12 | 122 definitions trong `schemas/f1.schema.json` (`$id: "urn:studyflow:f1:1.1:integration:1.0.1"`), 27 nhánh `RpcRequest.oneOf` |
| OpenAPI 3.1.1 | 8 paths (`info.version: "1.0.1"`); external schema references resolve local |
| Service registry | Đúng 10 operation F1 public và 18 `internal_interfaces` (thêm 6 helper RPC nội bộ); đầy đủ `arguments_schema`, `data_schema`, `result_schema` |
| Data mapping | Đủ field của 10 entity, PK/nullability khớp shared schema; 5 `infrastructure_records` (thêm `WorkflowContinuationRecord` → `app_private.workflow_continuations`) |
| Đối chiếu schema F1 nguồn | Tên field 10 entity và catalog operation khớp `docs/database/schema_F1.md` |
| Ví dụ | 100 positive/negative fixtures trong `examples/manifest.json` (88 fixture gốc cập nhật lên `1.0.1` + 12 fixture mới cho continuation/checkpoint/context/version) |
| Thực thi checker & test độc lập | Đã chạy 05/11/2026 trên Python 3.14: `check_contract.py` PASS (122 definitions, 100 fixtures); `test_contract_addendum.py` 16/16 pass; scheduler acceptance 33, planner unit 24, tests 78 pass. Kiểm riêng: kết quả rỗng hợp lệ với `search_tasks`, bị loại với `get_study_plan` |
| Backend/DB/auth/UI runtime | **NOT_RUN**; chưa có implementation trong phạm vi thay đổi WP0 |

Môi trường kiểm tra tham chiếu: Python, `jsonschema`, `openapi-spec-validator` theo `contracts/requirements-check.txt`.

Kiểm tra schema/invariant thuần không chứng nhận chữ ký HMAC, RLS/grants, transaction/rollback, concurrency hoặc luồng UI. Fixture RPC có signature giả chỉ kiểm tra cấu trúc JSON. Các ca cần chạy thật được liệt kê trong [acceptance-cases.md](acceptance-cases.md) và vẫn `NOT_RUN`.
