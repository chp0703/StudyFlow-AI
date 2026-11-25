# Deliverable 5 – Danh sách Kiểm tra Hồi quy Nhanh trước Mỗi Bản Build / Release (F1 Regression Checklist)

Checklist ngắn gọn này dành cho team QA và Developer chạy **mỗi khi có PR/build mới đụng tới F1 (Frontend, Orchestrator, Prompt/Model, Scheduler hoặc Migrations)**. Ưu tiên tuyệt đối các lỗi **P0 / P1** đã từng xảy ra trong 4 báo cáo QA (Hùng, Hương, Thế Hiển, Kent) và các lỗi mới phát hiện khi kiểm toán `main` (`e0cf937`).

**Quy ước trạng thái ghi nhận:** `PASS` | `FAIL` | `BLOCKED` | `NOT TESTED` | `N/A` *(Tuyệt đối không ghi Mock PASS thành Real E2E PASS).*

---

## A. Cổng Chặn Tự động (Automated Gate – Chạy trước khi mở trình duyệt, < 2 phút)

- [ ] **CHK-01 (Contract & Schema Sync):** `python -B contracts/check_contract.py` và `python -B backend/scripts/generate_contract_schema_migration.py --check` đều **PASS**.
- [ ] **CHK-02 (Backend & Deterministic Scheduler):** Toàn bộ `backend/tests/unit`, `acceptance_sol`, `acceptance_api_sol` và `evaluate_planner.py` đạt **100% PASS** (`hard_constraint_violations = 0`, `deterministic = true`).
- [ ] **CHK-03 (Frontend Type & Unit Tests):** `npx tsc --noEmit`, `node --experimental-strip-types --test src/**/*.test.ts` và `npm run build` đều **PASS**.

---

## B. Hồi quy P0 – Phê duyệt, Toàn vẹn Dữ liệu & Lập lịch Cốt lõi (Bắt buộc 100% PASS)

- [ ] **CHK-04 (Không tự động phê duyệt qua Chat – `F1-E09-01`):** Gửi câu tạo task đầy đủ → trước khi bấm nút Xác nhận, `GET /v1/tasks` phải rỗng (`0` bản ghi); gõ tiếp `"ok đồng ý lưu luôn"` vào Chat vẫn không tạo bản ghi; chỉ khi bấm nút Xác nhận (`POST /v1/decisions`) mới tạo đúng `1` task.
- [ ] **CHK-05 (Task dài `> 90` phút không nêu hạn riêng – `F1-E01-02` / Bug `CF-01`):** Với cả ngày rảnh (`07:00–20:00`), gửi `"Ngày mai tôi muốn học Toán lúc 8h sáng trong 2 tiếng, ưu tiên cao"` → duyệt task → sinh lịch → phải xếp đủ **120 phút** (2 blocks có tính `break_minutes = 10`), không bị cắt hụt còn 90 phút.
- [ ] **CHK-06 (Lập lại lịch tuần tới không vỡ block tuần này – `F1-E02-02` / Bug `CF-02`):** Khi đã có `StudyBlock` được duyệt vào ngày mai, gửi `"Sắp xếp lại lịch tuần tới"` → phải sinh được đề xuất hợp lệ, **không** nổ lỗi `422 retained block is outside current availability`, và giữ nguyên `StudyBlock` ngày mai.
- [ ] **CHK-07 (Regex giờ đồng hồ trên Popup Làm rõ – `F1-E07-01` / Bug `CF-03` / Hùng `TC-01`):** Trên `/planner`, gửi `"Học Toán 8h tối mai"` (thiếu thời lượng) → popup hiện lên phải giữ tên `"Học Toán"`, ngày mai lúc `"20:00"`, và ô thời lượng **để trống** (không biến `"8h"` thành `480` phút, không nhảy về hôm nay `08:00`).
- [ ] **CHK-08 (Hủy / thoát nháp khi đang `NEEDS_CLARIFICATION` – `F1-E08-03` / Bug `CF-04` / `F1-B03`):** Gửi `"Thêm bài tập Giải tích"` → khi hệ thống hỏi thêm thông tin, người dùng phải hủy được bản nháp ngay trên UI (hoặc qua Chat) và gửi câu `"Tìm công việc"` tiếp theo đạt HTTP `200`, không bị khóa cứng ở `409 ACTION_REVIEW_REQUIRED`.
- [ ] **CHK-09 (F5 giữa lúc request đang `Pending` trên mạng chậm – `F1-E11-02` / Hiển `TC-08` / Bug `CF-04`):** Bật `Slow 3G`, bấm Gửi tạo task rồi nhấn `F5` ngay khi request chưa trả về → sau khi tải lại trang, người dùng phải thấy lại thẻ Xác nhận/Hủy để xử lý tiếp, không bị kẹt chết `409` (`action_reference: null`).
- [ ] **CHK-10 (Chống ghi trùng & 2 Tab đồng thời – `F1-E12-01`, `F1-E12-02` / Hiển `TC-03..06`):** Double-click / nhấn Enter 3 lần vào nút Gửi và nút Duyệt; mở 2 tab cùng bấm Duyệt trong `< 0.5s` → chỉ tạo đúng `1` bản ghi duy nhất, tab thứ hai nhận thông báo `STALE_PROPOSAL` an toàn.
- [ ] **CHK-11 (Bảo mật JWT & Chống truy cập chéo – `F1-E13-01`):** Request không token trả `401`; User B dùng `proposal_id` hoặc `action_reference` của User A bị chặn `404/403`, không rò rỉ dữ liệu.

---

## C. Hồi quy P1 – Tiếng Việt Thực tế, Đa tác vụ, Hiệu năng & UX

- [ ] **CHK-12 (Dải thứ lặp hàng tuần – `F1-E04-08` / Bug `CF-06` / `F1-B01`):** Gửi `"Tôi rảnh thứ 2 đến thứ 6 từ 7h sáng đến 18h chiều"` → sau khi duyệt phải có đủ **5 khung giờ** từ Thứ Hai đến Thứ Sáu (`weekday = 1..5`), không chỉ tạo mỗi Thứ Hai.
- [ ] **CHK-13 (Giờ khẩu ngữ & tiếng Việt không dấu – `F1-E04-01`, `F1-E04-04`, `F1-E04-05`):** Kiểm tra `"8r tối nay trong 1 tiếng rưỡi"` (`20:30`, `90p`), `"10h kém 15 sáng mai"` (`09:45`), `"trước 12h đêm mai"` (`00:00` ngày kế), và câu không dấu chạy lặp `3` lần (`Pass^3`) không gán sai `deadline_at == start_at`.
- [ ] **CHK-14 (Đa công việc trong 1 câu – `F1-E05-01`, `F1-E05-02` / Hùng `TC-08`):** Gửi 3 môn học trong 1 câu trên cả `/` và `/planner` → duyệt tuần tự lưu đủ cả 3 môn, không bị gộp đè mất 2 môn.
- [ ] **CHK-15 (Mâu thuẫn `start_at > deadline_at` & giờ sai `25h` – `F1-E04-07`, `F1-E06-03` / Bug `CF-07`):** Câu `"25h ngày mai"` hoặc `"lúc 20h tối mai, hạn 10h sáng mai"` phải được chặn/hỏi lại ngay trước khi tạo thẻ duyệt (không để tới lúc bấm Xác nhận mới nổ `422` gây kẹt nháp).
- [ ] **CHK-16 (Giới hạn `8.000` ký tự trên cả 2 khung Chat – `F1-E13-02` / Bug `CF-08` / `F1-B04`):** Dán `8.005` ký tự vào cả `ChatComposer` (`/`) và `PlannerCommandComposer` (`/planner`) → UI chặn vượt ngưỡng đồng nhất với Contract.
- [ ] **CHK-17 (Độ trễ LLM & Xử lý lỗi `503` / `Offline` – `F1-E14-01`, `F1-E14-02`, `F1-E11-03` / Bug `CF-05`, `CF-09`):** Phản hồi `POST /v1/messages` đạt P95 `< 10s` (không timeout `20s` hàng loạt do thinking mode); khi gặp `503` hoặc `Offline`, client không bắn lặp 3 request LLM ngầm, không treo chữ `"Đang xử lý..."`, và hiển thị đúng thông báo mạng/dịch vụ bằng tiếng Việt.
- [ ] **CHK-18 (Ranh giới Out-of-Scope không gây hỏng dữ liệu – `F1-E02-04`, `F1-E03-03`):** Gửi `"Dời lịch Toán sang 9h sáng"` và `"Xóa lịch vừa tạo"` → lịch hiện hành (`StudyPlan`) và `AcademicTask` cũ được bảo toàn nguyên vẹn 100%; nút đính kèm file Chat vẫn khóa an toàn (`N/A`) cho tới khi mở UI BE-04.
