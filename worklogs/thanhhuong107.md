# Worklog — thanhhuong107

## 2026-11-13 — Backend Planner BE-03: dữ liệu xác nhận lịch đầy đủ

**Mục tiêu:** trả cho giao diện toàn bộ dữ liệu cần thiết để người dùng kiểm tra lịch đề xuất trước khi duyệt, đồng thời giữ quyết định duyệt gắn với đúng proposal/version/revision.

**Đã làm**

- Mở rộng contract với `ScheduleConfirmation`, gồm snapshot lịch đầy đủ, task ID/tên/màu, ngày/giờ/thời lượng, added/changed/removed, cảnh báo và phần việc chưa xếp.
- Sinh DTO xác nhận trực tiếp từ snapshot/diff phía server trong `backend/app/f1/planning/generate.py` và đưa nguyên trạng vào `ActionPresentation` cho luồng tạo/xem lại proposal.
- Bổ sung kiểm tra semantic, fixture hợp đồng, migration schema sinh tự động, tài liệu Planner và cập nhật các fixture pgTAP dùng `ActionPresentation`.
- Thêm acceptance test cho lịch có block thay đổi/xóa và lịch xếp được một phần; bổ sung assertion cho luồng HTTP tạo, trình bày và duyệt proposal.

**Kết quả:** nhánh `feat/be-03-complete-schedule-confirmation`; contract checker pass (126 definitions, 104 fixtures), migration generator check pass, 44 unit tests, 35 scheduler acceptance tests và 47 HTTP contract acceptance tests pass; planner evaluation pass với kết quả xác định và không vi phạm hard constraint.

**Ghi chú**

- Đã đồng bộ `supabase/tests/14_wp2c1_plan_reads.sql`, `15_wp2c2_persist_proposal.sql`, `16_wp2c3_approve_reject_plan.sql` và `supabase/tests_concurrency/harness.py` với trường `schedule_confirmation` bắt buộc; `test_transactions.py` dùng fixture chung nên không cần sửa.
- Bổ sung negative fixture chứng minh `PlanProposal.payload` thiếu `schedule_confirmation` bị từ chối.
- Kiểm tra local bằng Supabase CLI 3.0.0 và Docker/PostgreSQL thật: clean reset PASS; 15 file pgTAP/479 test PASS; upgrade route từ `202611050008` lên HEAD có schema hash trùng clean replay; 12 HTTP integration test và 6 concurrency test PASS.
- Chạy lại toàn bộ kiểm tra Python: contract checker PASS (126 definitions, 105 fixtures, OpenAPI 3.1), migration generator PASS, 44 unit test, 35 scheduler acceptance test, 47 HTTP contract acceptance test PASS; planner evaluation deterministic và có 0 hard-constraint violation.
- Chỉ dùng local Supabase; không truy cập hoặc thay đổi cloud project `phomrutsdhdgejlskwcb`.

## 2026-11-17 — F2 B6: thống kê tỷ lệ lỗi theo chủ đề

**Mục tiêu:** cung cấp thống kê từ câu trả lời hợp lệ đã chấm, phân biệt rõ thiếu dữ liệu và không suy diễn mức thành thạo.

**Đã làm**

- Thêm `backend/app/assessment/stats.py`, endpoint `GET /v1/assessment/topics/stats`, và đăng ký `get_topic_stats` là RPC chỉ đọc.
- Thêm migration mới `202611190001_f2_b6_topic_stats.sql`: thống kê từ dữ liệu DB bền vững, theo owner JWT và từng cặp tài liệu/chủ đề; không tính bài chưa nộp hoặc response `OMITTED`/`INVALID`.
- Trả `INSUFFICIENT_DATA`, count 0 và rate/time null nếu chưa có response hợp lệ; kiểm tra contract và tính nhất quán của kết quả RPC ở backend.
- Bổ sung unit, HTTP acceptance, integration sau restart backend, pgTAP cho cách ly người dùng, nhiều attempt, chủ đề trùng tên giữa tài liệu, và danh sách RPC công khai; cập nhật tài liệu assessment.

**Kết quả:** [issue #47](https://github.com/chp0703/StudyFlow-AI/issues/47), tiếp tục trên nhánh `feat/f2-b5-attempt-grading`; clean reset/replay PASS; 19 file / 618 pgTAP test PASS; 22 HTTP integration test PASS; 124 unit test và 72 HTTP acceptance test PASS; contract checker PASS (187 definitions, 126 fixtures), generated schema migration `--check` và `git diff --check` PASS.

**Ghi chú**

- DB test chạy trên Docker/PostgreSQL thật với Supabase CLI 3.2.0, project local cô lập `studyflow-b6-validation`; integration dùng auth/DB thật và mock model.
- Không chạy DeepSeek thật vì B6 không gọi model.
- Commit dùng `thanhhuong107 <224420045+thanhhuong107@users.noreply.github.com>` theo tài khoản được người dùng chỉ định.

## 2026-11-18 — Giao diện pastel và nhãn màu trên lịch

**Mục tiêu:** giúp người dùng phân biệt nhóm công việc trên lịch và làm mới giao diện StudyFlow AI.

**Đã làm**

- Mở rộng bảng màu pastel, thêm điểm nhấn cho các màn hình và đưa logo StudyFlow AI vào màn chào.
- Thêm lựa chọn nhãn màu khi tạo công việc, hiển thị nhãn trong bảng công việc và dùng chữ đậm cùng tông trên lịch tuần và lịch tháng.

**Kết quả:** nhánh `fix/planner-event-color-contrast`. Build frontend, TypeScript và 81 bài kiểm thử đạt.

**Ghi chú**

- Kiểm thử màu bằng luồng demo và render lịch. Chưa xác minh lưu màu qua API thật.
