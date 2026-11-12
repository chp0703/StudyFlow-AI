# Ghi nhận phê duyệt Planner contract

| Nội dung | Ghi nhận |
|---|---|
| Trạng thái | **APPROVED — CHÍNH THỨC** |
| Package | **1.0.1** |
| Logical schema | **Planner v1.1**, technical `schema_version="1.1"` |
| Ngày phê duyệt và hiệu lực | **05/11/2026**, múi giờ Việt Nam (`Asia/Ho_Chi_Minh`) |
| Bên phê duyệt | Team dự án StudyFlow AI, theo xác nhận của người dùng trong cuộc trao đổi này |
| Căn cứ | Người dùng xác nhận duyệt chính thức bộ contract `1.0.0` và tiếp tục phê duyệt toàn bộ phụ lục RPC nội bộ A/B/C/D cho bản `1.0.1`; lịch sử chính xác được giữ tại các commit bên dưới |
| Bản được duyệt | Bộ contract `1.0.0` tại commit `b629a5e` cùng phụ lục RPC nội bộ & workflow continuation `1.0.1` theo đề xuất tại commit `2bac72c` / baseline `5d29d2d` |

Phê duyệt bao gồm cả ba ranh giới **API FE ↔ BE**, **Service/Tool Orchestrator ↔ BE**, **Data/RPC BE ↔ DB**, toàn bộ quyết định **IC-01–IC-08** tại [hợp đồng chính](README.md#10-quyết-định-đã-phê-duyệt-và-trách-nhiệm-duy-trì), cùng 6 helper RPC nội bộ (`ensure_user_context`, `list_time_windows`, `get_workflow_context`, `get_workflow_continuation`, `initialize_workflow_continuation`, `checkpoint_workflow_continuation`), bảng hạ tầng `app_private.workflow_continuations` và quy tắc bootstrap attested cho first `GET /v1/preferences`.

Các artifact áp dụng chính thức: README.md, openapi.yaml, schemas/f1.schema.json, service-contract.json, data-contract.json, examples và các invariant/ca nghiệm thu được tham chiếu. Bản `1.0.1` giữ nguyên 8 HTTP endpoint public, 10 domain/LLM operation, 10 entity nghiệp vụ logic và `schema_version="1.1"`; mở rộng danh mục `internal_interfaces` từ 12 lên 18 và `infrastructure_records` từ 4 lên 5.

Không tự bổ sung tên người ký, biên bản họp, chữ ký hay thời gian phê duyệt chi tiết mà người dùng chưa cung cấp. Xác nhận trong cuộc trao đổi là căn cứ ghi nhận hiện có.

Phê duyệt thiết kế không chứng nhận backend, migrations, JWT/HMAC verifier, RLS/grants, transaction, concurrency hoặc UI đã triển khai/chạy đạt. Trạng thái kiểm tra tại [VALIDATION.md](VALIDATION.md), các ca runtime tại [acceptance-cases.md](acceptance-cases.md). Các công việc ngoài phạm vi contract như chỉnh SRS chính thức, chọn phiên bản/local stack và triển khai môi trường tiếp tục được theo dõi riêng.

Từ ngày hiệu lực, các bên triển khai theo package 1.0.1. Thay đổi giao diện hoặc ngữ nghĩa phải đi qua review consumer, cập nhật changelog/fixtures và phiên bản tương ứng; không sửa ngầm bản đã duyệt.
