# Danh Mục Quyết Định Đang Mở (Open Decisions Register)

| Thuộc tính | Giá trị |
|---|---|
| **Mục đích (Purpose)** | Ghi nhận tất cả các câu hỏi sản phẩm, ngữ nghĩa domain và thay đổi hợp đồng đang chờ Project Owner hoặc nhóm kỹ thuật chốt trước khi các agent thực thi phần phụ thuộc |
| **Thẩm quyền (Authority)** | Cổng kiểm soát (`Decision Gate`) cho các task có trạng thái `NEEDS_DECISION` hoặc `BLOCKED` trong [`TASK_BOARD.md`](TASK_BOARD.md) |
| **Chủ sở hữu (Owner)** | Project Owner (Quyết định cuối cùng) · `BE-4` (Thư ký điều phối) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Quy tắc Sử dụng Sổ đăng ký Quyết định Mở

1. **Không tự bịa câu trả lời:** Không một AI coding agent nào (`FE-1`, `FE-2`, `BE-1`, `BE-2`, `BE-3`, `BE-4`) được tự ý chọn một phương án trong bảng này rồi sửa thẳng vào `contracts/` hoặc DB migrations như thể đã được phê duyệt.
2. **Không dừng toàn bộ dự án vì một quyết định mở:** Các task không phụ thuộc vào quyết định đang mở (ví dụ `FE1-003` Sticky Date Header, `BE2-002` Approval-time revalidation theo contract 1.0.1, `BE2-003` Concurrency tests) vẫn được triển khai bình thường. Chỉ những task phụ thuộc trực tiếp mới giữ ở trạng thái `NEEDS_DECISION` / `BLOCKED`.
3. **Cách đóng một Open Decision:** Khi Project Owner chốt phương án, tạo một bản ghi theo [`templates/DECISION_RECORD_TEMPLATE.md`](templates/DECISION_RECORD_TEMPLATE.md), cập nhật trạng thái tại đây sang `APPROVED` (kèm ngày và căn cứ), sau đó thực hiện [`CONTRACT_CHANGE_PROTOCOL.md`](CONTRACT_CHANGE_PROTOCOL.md) (`INT-001`).

---

## 2. Danh sách Các Quyết định Đang Chờ Chốt (`NEEDS_PRODUCT_OWNER` / `OPEN`)

### `OD-001` — Chuẩn hóa Schema cho các trường Task mới: `priority` (`0.1 | 0.5 | 1`), `color`, và `duration`

- **Trạng thái:** **`NEEDS_PRODUCT_OWNER`**
- **Yêu cầu nguồn:** `REQ-F1-02`, `REQ-F1-03`, `REQ-F1-04` tại [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](PRODUCT_REQUIREMENTS_AND_DECISIONS.md)
- **Các vai trò bị ảnh hưởng:** `BE-1`, `BE-2`, `BE-4`, `FE-1`, `FE-2` (`BE1-001`, `FE1-001`, `INT-001`)
- **Bối cảnh kỹ thuật:**
  - Trong `contracts/schemas/f1.schema.json` và `docs/database/schema_F1.md` (`v1.1`), `priority` đang là enum chuỗi `"LOW" | "NORMAL" | "HIGH"`, thời lượng là `estimated_minutes: integer > 0`, và chưa có trường `color`.
  - Đặc biệt, hàm `app_private.canonical_json(jsonb)` trong `supabase/migrations/202611050010_f1_rpc_verifier.sql` được thiết kế để **từ chối mọi số thực (float/decimal)** với lỗi `SQLSTATE 22023` nhằm đảm bảo băm chữ ký HMAC-SHA256 tất định tuyệt đối giữa Python và PostgreSQL. Nếu truyền số thực `0.1` hoặc `0.5` trực tiếp trong JSON của `RpcRequest`, tầng xác minh chữ ký RPC hiện tại sẽ từ chối request.
- **Các phương án lựa chọn:**
  - **Phương án A (Giữ an toàn canonical JSON & tương thích ngược cao):**
    - Về `priority`: Trên UI (`FE-1`) và API/cấu hình hiển thị đúng bộ giá trị `0.1`, `0.5`, `1` (hoặc chuỗi `"0.1" | "0.5" | "1"` trong JSON để không vi phạm luật cấm float của `canonical_json`), hoặc ánh xạ 1-1 (`0.1 ↔ LOW`, `0.5 ↔ NORMAL`, `1 ↔ HIGH`) kèm trọng số tương ứng trong `f1/scheduler/engine.py`.
    - Về `duration`: Giữ tên trường `estimated_minutes` (số nguyên phút) trong contract/DB; trên UI hiển thị nhãn "Thời lượng (Duration)".
    - Về `color`: Thêm trường `color: string?` (cho phép null hoặc mã màu/token trong danh mục) vào `CandidateTaskFields` và `AcademicTask`.
  - **Phương án B (Sửa sâu Contract & Verifier):**
    - Đổi kiểu `priority` thành số thực trong schema và sửa lại `app_private.canonical_json` cùng bộ test vector HMAC trong `06_sol_rpc_boundary.sql`.
- **Câu hỏi cần Project Owner chốt:** Chọn Phương án A hay Phương án B? Với `color`, danh sách mã màu/token hợp lệ gồm những màu nào?

---

### `OD-002` — Xác định ngữ nghĩa Domain chính xác cho thông tin `start time` của Task

- **Trạng thái:** **`NEEDS_PRODUCT_OWNER`**
- **Yêu cầu nguồn:** `REQ-F1-05` ("Có thông tin start time nhưng phải xác định đúng domain semantics: task preference hay actual scheduled block start; không tạo field trùng")
- **Các vai trò bị ảnh hưởng:** `BE-1`, `BE-2`, `FE-1`, `BE-4` (`BE1-001`, `FE1-001`, `INT-001`)
- **Bối cảnh kỹ thuật:**
  - Schema `F1 v1.1` hiện đã có:
    1. `AcademicTask.available_from_at: timestamp?` — Thời điểm sớm nhất mà bộ lập lịch được phép xếp các `StudyBlock` cho công việc này.
    2. `StudyBlock.start_at: timestamp` — Thời điểm bắt đầu thực tế của từng phiên học do bộ lập lịch (`BE-2`) tính toán ra trong `PlanProposal` / `StudyPlan`.
- **Các phương án lựa chọn:**
  - **Phương án A (Dùng `available_from_at` có sẵn trong Schema v1.1):** Trường "Start time" trên Task Form chính là `available_from_at` (thời điểm bắt đầu có thể làm việc / mở đề), còn giờ bắt đầu từng buổi học cụ thể do Scheduler xếp vào `StudyBlock.start_at`. Không tạo thêm field mới.
  - **Phương án B (Preferred Start Time cho Task):** Là khung giờ ưu tiên trong ngày mà sinh viên muốn bắt đầu làm task đó (ràng buộc mềm cho Scheduler).
  - **Phương án C (Fixed/Pinned Start Time):** Là thời điểm bắt đầu cố định cho một task chỉ có 1 block.
- **Câu hỏi cần Project Owner chốt:** "Start time" trên Task mang ngữ nghĩa Phương án A (`available_from_at`), Phương án B hay Phương án C?

---

### `OD-003` — Thiết kế Dữ liệu & API cho `Personalized Working Time` (thay thế "Free Time" trên UI)

- **Trạng thái:** **`NEEDS_PRODUCT_OWNER`**
- **Yêu cầu nguồn:** `REQ-F1-07`, `REQ-F1-08` ("Bỏ Free Time trên user-facing experience; thay bằng Personalized Working Time")
- **Các vai trò bị ảnh hưởng:** `FE-2`, `BE-1`, `BE-2`, `BE-4` (`BE1-003`, `FE2-001`, `INT-001`)
- **Bối cảnh kỹ thuật:**
  - Bộ lập lịch `BE-2` (`f1/scheduler/engine.py`) cần biết: (1) những khung giờ nào trong tuần người dùng làm việc/học tập (`availability`), (2) những khoảng thời gian nào người dùng bận cố định (`busy_intervals`) để tránh xung đột, và (3) cấu hình phiên làm việc (`SchedulingPolicy`: độ dài tối thiểu/tối đa mỗi phiên, tổng thời gian tối đa mỗi ngày, thời gian nghỉ).
- **Các phương án lựa chọn:**
  - **Phương án A (Tái sử dụng Contract `1.0.1` — Không phá vỡ DB/Scheduler):**
    - Trên giao diện người dùng (`FE-2`), xóa hoàn toàn tên gọi "Free Time / Giờ rảnh", thay bằng màn hình thiết lập **"Personalized Working Time"** (cho phép cấu hình khung giờ làm việc cá nhân theo các thứ trong tuần + giới hạn thời lượng phiên/ngày).
    - Dưới tầng API/DB (`BE-1`, `BE-4`), các khung giờ làm việc cá nhân này vẫn lưu vào `TimeWindow` với `kind = "AVAILABILITY"` và cấu hình nhịp độ lưu vào `SchedulingPolicy` (`set_availability` + `set_scheduling_preferences`), đồng thời giữ nguyên `TimeWindow` với `kind = "BUSY"` cho các lịch bận/xung đột nội bộ của Scheduler (`BE-2`).
  - **Phương án B (Tạo Entity/Schema mới cho Personalized Working Time):**
    - Thay đổi cấu trúc bảng `time_windows` / `user_profiles` trong `data-contract.json` và `f1.schema.json`.
- **Câu hỏi cần Project Owner chốt:** Đồng ý áp dụng Phương án A (giữ nguyên contract nền `TimeWindow` + `SchedulingPolicy` để không phải viết lại Scheduler/DB) hay yêu cầu Phương án B?

---

### `OD-004` — Kiến trúc, Phạm vi Định dạng & Hợp đồng API cho Pipeline Upload & Trích xuất Tệp (`image`, `calendar file`, `document`, từ chối `audio`)

- **Trạng thái:** **`NEEDS_PRODUCT_OWNER`**
- **Yêu cầu nguồn:** `REQ-F1-11`, `REQ-F1-12`, `REQ-F1-13`
- **Các vai trò bị ảnh hưởng:** `BE-3`, `BE-4`, `FE-2`, `BE-1` (`BE3-002`, `BE3-003`, `BE3-004`, `FE2-002`, `FE2-003`, `INT-001`)
- **Bối cảnh kỹ thuật:**
  - Contract `1.0.1` hiện chỉ có 8 endpoint JSON với giới hạn `max_body_bytes = 64 KiB` và chưa có endpoint nhận tệp hay schema cho bước trích xuất tệp.
  - Để `BE-3` và `FE-2` triển khai an toàn mà không tự chế API riêng, cần chốt Contract Addendum cho luồng này.
- **Các câu hỏi cần Project Owner & Nhóm chốt:**
  1. **Danh mục định dạng cụ thể:**
     - `image`: `.png`, `.jpg`/`.jpeg`, `.webp`? (Dùng OCR/Vision model nào ở server? DeepSeek hay công cụ OCR cục bộ/dịch vụ khác?)
     - `calendar file`: `.ics` (iCalendar RFC 5545)? Khi trích xuất sự kiện từ `.ics`, người dùng chọn chuyển thành `AcademicTask` hay khoảng bận `BUSY`?
     - `document`: `.pdf`, `.docx`, `.txt`, `.md`?
     - `audio` (Bị cấm): Chặn mọi `audio/*`, `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`, voice note ở cả client và server.
  2. **Lưu trữ tệp (Storage Policy):** Tệp tải lên chỉ được đọc/trích xuất trong bộ nhớ tạm thời (ephemeral parsing, không lưu file gốc lâu dài) hay lưu vào Supabase Storage bucket riêng có RLS theo `user_id`?
  3. **Giao diện API & Handoff sang Review Flow:**
     - Thêm endpoint mới (ví dụ `POST /v1/ingestions` hoặc `POST /v1/uploads/extract` trả về danh sách `ExtractionCandidate` kèm `confidence` và `unresolved_fields`), sau khi người dùng review/chỉnh sửa trên `FE-2` sẽ gọi `POST /v1/actions` (`create_task_candidate` / `set_busy_interval`) để đi vào luồng xác nhận chuẩn của F1 v1.1?

---

### `OD-005` — Quy tắc Hiển thị & Khóa Múi giờ `Asia/Ho_Chi_Minh` giữa Frontend và Backend

- **Trạng thái:** **`OPEN`** (Chờ `Project Owner` + `BE-1` + `FE-1` xác nhận)
- **Yêu cầu nguồn:** `REQ-F1-06` ("Timezone sản phẩm Asia/Ho_Chi_Minh")
- **Các vai trò bị ảnh hưởng:** `BE-1`, `FE-1`, `FE-2` (`BE1-002`, `FE1-002`)
- **Bối cảnh kỹ thuật:**
  - Backend/DB lưu `timestamptz` (UTC) kèm IANA timezone `Asia/Ho_Chi_Minh`.
  - Tuy nhiên `frontend/src/api/mappers.ts` hiện đang dùng `new Date(iso).getHours()` (tức giờ theo múi giờ cục bộ của trình duyệt người dùng) và lưới lịch `WeekCalendar.tsx` hiện giới hạn từ `8h` đến `17h`.
- **Câu hỏi cần chốt:**
  1. Frontend bắt buộc luôn format và tính ngày/giờ trên lịch theo cố định `Asia/Ho_Chi_Minh` (`UTC+07:00`) bất kể cài đặt OS/trình duyệt của người dùng?
  2. Khung giờ hiển thị trên `WeekCalendar.tsx` cần mở rộng ra ngoài `8h–17h` (ví dụ `06:00–23:00` hoặc `00:00–24:00` có cuộn dọc dưới `Sticky Date Header`) để hiển thị được các buổi học tối?

---

### `OD-006` — Giao thức Chỉnh sửa `TaskCandidate` đang Nháp (`Task Draft Editing`) & Nối `POST /v1/actions` trên Frontend

- **Trạng thái:** **`OPEN`** (Chờ `BE-4` + `BE-1` + `FE-1` + `FE-2` + `Project Owner` xác nhận)
- **Yêu cầu nguồn:** `REQ-F1-01`..`05`, `REQ-F1-13`
- **Các vai trò bị ảnh hưởng:** `BE-4`, `BE-1`, `FE-1`, `FE-2` (`BE4-001`, `FE1-001`, `FE2-003`, `FE2-004`)
- **Bối cảnh kỹ thuật:**
  - Trong `contracts/openapi.yaml` (`1.0.1`), `POST /v1/actions` đã được phê duyệt cho 5 operation chuẩn bị (`create_task_candidate`, `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `generate_study_plan`), nhưng `frontend/src/api/endpoints.ts` chưa bọc hàm gọi `POST /v1/actions`.
  - Khi người dùng mở một `TaskCandidate` đang ở trạng thái `DRAFT` để sửa lại các trường trên UI trước khi bấm `APPROVE`, hiện `ActionRequest` chưa có operation `update_task_candidate` công khai (mới chỉ có helper nội bộ `update_candidate_draft` khi trả lời câu hỏi làm rõ qua `POST /v1/messages`).
- **Câu hỏi cần chốt:**
  - Để chỉnh sửa một `TaskCandidate` nháp từ form UI, nhóm chọn: (A) Hủy action nháp cũ (`POST /v1/decisions` với `REJECT`) rồi gửi `POST /v1/actions` (`create_task_candidate`) mới (không cần đổi contract `1.0.1`), hay (B) Bổ sung cơ chế cập nhật `TaskCandidate` nháp trực tiếp vào contract addendum?

---

### `OD-007` — Đối chiếu Chính thức Tài liệu SRS (`E-12` trong Decision Register)

- **Trạng thái:** **`OPEN`** (Theo dõi từ [`StudyFlow_AI_Phase_03_Implementation_Decision_Register.md`](../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md))
- **Các vai trò bị ảnh hưởng:** Project Owner, `BE-1`, `BE-4`
- **Bối cảnh:** Bản `docs/srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md` vẫn giữ nội dung lịch sử trước khi chốt Schema `v1.1`, Contract `1.0.1` và 13 yêu cầu F1 mới.
- **Câu hỏi cần chốt:** Thời điểm nào thực hiện cập nhật văn bản SRS chính thức sau khi chốt các quyết định `OD-001`..`OD-006`?

---

### `OD-008` — Quyền Quản trị, Lịch sử Migration trên Supabase Project `phomrutsdhdgejlskwcb` & Khóa `DEEPSEEK_API_KEY` cho Gate `G3`

- **Trạng thái:** **`OPEN / ENVIRONMENT BLOCKER`**
- **Các vai trò bị ảnh hưởng:** Project Owner, `BE-1`, `BE-3`, `BE-4` (`BE3-001`, `INT-003`, `INT-004`)
- **Bối cảnh:**
  - Theo [`docs/implementation/DEMO_ENVIRONMENT.md`](../implementation/DEMO_ENVIRONMENT.md), project ref `phomrutsdhdgejlskwcb` mới được xác minh public JWKS ES256; chưa kiểm tra lịch sử migration trên cloud thông qua [`supabase/scripts/inventory_demo.sql`](../../supabase/scripts/inventory_demo.sql).
  - Benchmark 40 câu tiếng Việt (`BE3-001`, ngưỡng `>= 38/40`) đang ở trạng thái `NOT_RUN` vì cần `DEEPSEEK_API_KEY` thật được cấu hình ngoài Git (`.env.local`).
- **Hành động cần từ Project Owner / Người vận hành:**
  - Chạy chỉ đọc `inventory_demo.sql` trên project demo để xác nhận trạng thái schema trước khi áp dụng bất kỳ migration nào (tuyệt đối không chạy `db reset` trên cloud).
  - Cấu hình `.env.local` với `DEEPSEEK_API_KEY` trên máy chạy kiểm thử để `BE-3` thực thi `evaluate_nlu.py` và ghi nhận bằng chứng thật.
