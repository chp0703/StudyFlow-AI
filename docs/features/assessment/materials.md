# F2 B2 — Material Store và Retrieval

Phụ thuộc contract F2 `1.0.0` trong B1 (PR #42). B2 chỉ triển khai tài liệu và
truy xuất; sinh/duyệt câu hỏi, làm bài, chấm điểm và thống kê thuộc B3–B7.

## Upload và đọc tài liệu

- `POST /v1/assessment/materials`: JWT và `Idempotency-Key` (16–128 ký tự).
- Body theo `MaterialUploadRequest`: `schema_version: "1.1"`, `conversation_id`,
  `filename`, `mime_type`, `content_base64`, `topics`.
- B2 nhận **một chủ đề do người dùng đặt** trong `topics`. Chưa có mapping
  chunk–topic nhiều chủ đề trong request B1; gửi nhiều chủ đề bị từ chối rõ ràng.
- Nhận UTF-8 `.txt`/`.md` và PDF có chữ; tối đa **10 MiB, 100 trang,
  200.000 ký tự trích xuất**. PDF chạy trong subprocess có timeout **15 giây**,
  giữ các giới hạn giải nén của parser. PDF mã hóa/scan/trang không có chữ bị từ chối.
- Xử lý đồng bộ, không gọi DeepSeek. Chỉ trả `READY` sau khi material và toàn bộ
  chunk đã lưu trong cùng transaction. Lỗi parse không để lại material/chunk dở dang.
- Lưu văn bản, SHA-256, metadata và số trang nguồn; không lưu bytes gốc.
- `GET /v1/assessment/materials/{material_id}?conversation_id=...` trả
  `AssessmentMaterialDetailResult` với `data.material` và `data.chunks`.
- ID người dùng lấy từ JWT. Sai owner/cuộc hội thoại trả 404 giống ID không tồn tại.
- Gửi lại cùng key/nội dung trả dữ liệu đã lưu với `Idempotency-Replayed: true`.
  Cùng key nhưng thay metadata/chủ đề/nội dung hợp lệ trả 409.

Ingestion F1 giữ mặc định 5 MiB, 20 trang, 24.000 ký tự và timeout PDF 5 giây.

## Điểm tích hợp cho B3

`MaterialOperations(rpc, clock)` tại `backend/app/assessment/materials.py` nhận
cùng RPC port và context đã xác thực của API. Dùng:

```python
result = materials.search(ctx, material_id, topic=None, query="giao thức TCP", limit=20)
chunks = result["data"]["items"]
```

RPC tương ứng: `app_api.search_material_chunks(p_request jsonb)` theo
`SearchMaterialChunksArguments`. `topic`/`query` có thể null, `limit` 1–20.
Query null lấy theo `chunk_index`; query có chữ dùng
`plainto_tsquery('simple', query)`, GIN/`ts_rank_cd`, thứ tự phụ `chunk_index`.
Kết quả gồm `chunk_id`, `material_id`, `user_id`, `page`, `topic`, `chunk_index`,
`text`, `created_at`; không trả cột nội bộ `search_vector`.

Không mở thêm HTTP search endpoint ngoài contract B1. READY và chunk bất biến.
Nội dung nguồn luôn là dữ liệu; upload/search không tạo pending action, task,
câu hỏi hoặc lịch học.

## Kiểm chứng và giới hạn

```bash
python -B -m unittest backend.tests.unit.test_materials backend.tests.unit.test_material_rpc -v
python -B -m unittest backend.tests.acceptance_api_sol.test_material_http -v
supabase test db
```

`supabase/tests/20_f2_b2_materials.sql` kiểm tra ownership, nguyên tử, replay,
immutability và bộ mẫu tiếng Việt tổng hợp: 8 truy vấn trên 4 đoạn, đối chiếu
trang top-1. Kết quả này không đại diện tài liệu thực tế, câu hỏi diễn đạt lại
hay truy vấn không dấu; cấu hình `simple` không cung cấp semantic retrieval.

`backend/tests/integration/test_material_local_supabase.py` kiểm tra HTTP/JWT/
signed RPC/database thật, restart/replay, cross-user và nguồn chứa chỉ dẫn.
Chỉ chạy với local Supabase và các biến `F1_LOCAL_*`, `F1_DB_TEST_DSN` của CI.
