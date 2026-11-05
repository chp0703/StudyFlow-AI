# Ghi nhận phê duyệt contract F1

| Nội dung | Ghi nhận |
|---|---|
| Trạng thái | **APPROVED — CHÍNH THỨC** |
| Package | **1.0.0** |
| Logical schema | **F1 v1.1**, `schema_version="1.1"` |
| Ngày phê duyệt và hiệu lực | **05/11/2026**, múi giờ Việt Nam (`Asia/Ho_Chi_Minh`) |
| Bên phê duyệt | Team dự án StudyFlow AI, theo xác nhận của người dùng trong cuộc trao đổi này |
| Căn cứ | Người dùng xác nhận: “Oke team t đã duyệt mày hãy đổi thành chính thức đi, nếu có thông tin gì cứ hỏi t” |
| Bản được duyệt | Bộ contract 1.0.0 đã bàn giao ở trạng thái REVIEW_READY, được lưu tại commit `b629a5e` trước khi cập nhật trạng thái chính thức |

Phê duyệt bao gồm cả ba ranh giới **API FE ↔ BE**, **Service/Tool Orchestrator ↔ BE**, **Data/RPC BE ↔ DB**, và toàn bộ quyết định **IC-01–IC-08** tại [hợp đồng chính](README.md#10-quyết-định-đã-phê-duyệt-và-trách-nhiệm-duy-trì).

Các artifact áp dụng chính thức: README.md, openapi.yaml, schemas/f1.schema.json, service-contract.json, data-contract.json, examples và các invariant/ca nghiệm thu được tham chiếu. Việc đổi trạng thái không sửa request/response, field, enum, hành vi nghiệp vụ hoặc tăng phiên bản package/schema.

Không tự bổ sung tên người ký, biên bản họp, chữ ký hay thời gian phê duyệt chi tiết mà người dùng chưa cung cấp. Xác nhận trong cuộc trao đổi là căn cứ ghi nhận hiện có.

Phê duyệt thiết kế không chứng nhận backend, migrations, JWT/HMAC verifier, RLS/grants, transaction, concurrency hoặc UI đã triển khai/chạy đạt. Trạng thái kiểm tra tại [VALIDATION.md](VALIDATION.md), các ca runtime tại [acceptance-cases.md](acceptance-cases.md). Các công việc ngoài phạm vi contract như chỉnh SRS chính thức, chọn phiên bản/local stack và triển khai môi trường tiếp tục được theo dõi riêng.

Từ ngày hiệu lực, các bên triển khai theo package 1.0.0. Thay đổi giao diện hoặc ngữ nghĩa phải đi qua review consumer, cập nhật changelog/fixtures và phiên bản tương ứng; không sửa ngầm bản đã duyệt.
