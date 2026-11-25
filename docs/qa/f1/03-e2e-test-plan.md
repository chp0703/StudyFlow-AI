# Deliverable 3 – Kế hoạch Kiểm thử & Đánh giá End-to-End cho F1 (F1 E2E Test Plan)

Tài liệu này thiết kế quy trình kiểm thử và đánh giá toàn diện cho **Feature 1 (Intelligent Academic Planner)** dựa trên kiến trúc thực tế của StudyFlow AI và các nguyên tắc cốt lõi từ **Anthropic – *Demystifying Evals for AI Agents*** (`Master Prompt §6, §8, §10`).

---

## 1. Phạm vi Kiểm thử (Test Scope)

### 1.1. Trong phạm vi (In-Scope)
- Toàn bộ luồng người dùng cuối từ giao diện **Trợ lý AI (`/` Assistant Chat)** và **Lịch học (`/planner`)** qua FastAPI Backend, model `deepseek-flash` thật, Deterministic Scheduler (`greedy-edf-1.1.0`), cơ chế duyệt `POST /v1/decisions` đến PostgreSQL (`app_api.*` / `app_private.*`) và hiển thị ngược lên `WeekCalendar` / `MonthCalendar`.
- Khả năng hiểu tiếng Việt thực tế (có dấu, không dấu, Telex/IME, viết tắt, giờ khẩu ngữ `8r` / `kém` / `12h đêm`, tự sửa ý giữa câu, đa tác vụ, câu mơ hồ, câu mâu thuẫn).
- Toàn bộ chu trình bản nháp (`NEEDS_CLARIFICATION` → `AWAITING_APPROVAL` → `APPROVE` / `REJECT`), khôi phục trạng thái sau F5, đa tab, chống gửi trùng (`Idempotency-Key`), mạng chậm/mất mạng và an toàn bảo mật.

### 1.2. Ngoài phạm vi hoặc Đánh dấu Đặc biệt (`OUT OF SCOPE` / `N/A`)
- **Dời giờ 1 `StudyBlock` đơn lẻ hoặc sửa/xóa `AcademicTask` đã xác nhận qua Chat (`OUT OF SCOPE v1.1`):** Chỉ kiểm thử dưới góc độ **Negative / Guardrail** (đảm bảo hệ thống từ chối an toàn, không sửa nhầm hoặc nhân bản công việc), tuyệt đối không chấm là lỗi thiếu tính năng trừ khi Product nâng cấp Contract lên v1.2.
- **Đính kèm file/ảnh trong khung Chat UI (`N/A`):** Nút upload trên `ChatComposer.tsx` đang khóa chủ đích theo `AGENTS.md` và `contracts/INGESTION.md`. Không đưa test upload UI vào danh sách tính lỗi F1.
- **Demo Mode (`plannerAgent.ts`):** Chỉ kiểm tra smoke để đảm bảo không vỡ chế độ offline demo; kết quả trên Demo Mode **không bao giờ** được tính là kết quả nghiệm thu F1 AI/API.

---

## 2. Triết lý Đánh giá Agent Áp dụng Thực tế cho F1 (`Anthropic Eval Principles`)

1. **End-to-End First (Đơn vị chấm là Nhiệm vụ Hoàn chỉnh của Người dùng):**
   - Mỗi test case bắt đầu từ một `Initial State` xác định (tài khoản sạch, đồng hồ/múi giờ xác định, dữ liệu nền nếu có), đi qua câu lệnh của người dùng + các lượt trả lời bổ sung / bấm nút xác nhận, và chấm trên **Trạng thái Cuối cùng (`Final DB State` + `Calendar UI` + `Phản hồi cuối`)**. Không cộng điểm rời rạc của parser hay regex để kết luận PASS.
2. **Evaluate Outcomes, Not Prescribed Steps (Chấm Kết quả Cuối, Không Ép Đường Đi Cứng Nhắc):**
   - Ví dụ với câu `"Rảnh thứ 2 đến thứ 6 từ 7h đến 18h"`, dù hệ thống sinh 5 intent trong 1 hàng đợi hay hỏi xác nhận gộp, miễn là sau khi người dùng xác nhận xong thì bảng `time_windows` có đủ đúng 5 khung giờ `weekday = 1..5` (`07:00–18:00`) và không vi phạm ranh giới phê duyệt thì đều đạt **PASS**.
   - Ngược lại, các bất biến về **an toàn, quyền sở hữu và phê duyệt tường minh qua `/v1/decisions`** là điều kiện cứng bắt buộc phải tuân thủ ở mọi bước.
3. **Ba tầng Bộ chấm điểm (Three-Tier Graders):**
   - **Code-based Grader (Ưu tiên số 1 – Tự động hóa chính xác):** Kiểm tra HTTP status, cấu trúc `OrchestratorReply`, dữ liệu thật từ `GET /v1/tasks`, `GET /v1/time-windows`, `GET /v1/plans?view=CURRENT` (hoặc truy vấn SQL `app_private.*` trên local Supabase), kiểm chứng `0` vi phạm Hard Constraint, bảo toàn `block_id` của các buổi không liên quan, và `0` bản ghi mồ côi/trùng lặp.
   - **Model-based Grader (LLM Rubric – Phụ trợ cho hội thoại):** Đánh giá chất lượng câu trả lời tiếng Việt ở các ca hỏi lại (`NEEDS_CLARIFICATION`), báo bận/thiếu chỗ (`PARTIAL`/`NONE`), hoặc từ chối thao tác ngoài phạm vi (`UNSUPPORTED`) theo rubric nhị phân (Rõ ràng / Đúng trọng tâm / Không bịa thông tin).
   - **Human Grader (Kiểm định viên QA):** Xác minh trực quan trên trình duyệt cho các ca gõ bộ gõ tiếng Việt IME/Telex thật, trải nghiệm kéo/xem lịch tuần-tháng, thao tác mạng chập chờn Slow 3G / F5 và hiệu chuẩn (calibrate) kết quả của Model Grader.
4. **Kiểm tra Độ ổn định Đa lượt (`Pass@k` & `Pass^k`):**
   - Thực nghiệm trên `main` đã chứng minh ngay cả với `temperature = 0`, API `deepseek-flash` vẫn cho kết quả khác nhau giữa các lần gọi (`NLU-01` đạt ở Trial 1 nhưng lỗi ở Trial 2 & Trial 3!).
   - Quy định bắt buộc cho các ca có gọi Real Model (`E01`, `E02`, `E04`, `E05`, `E07`, `E08`):
     - Chạy tối thiểu **`k = 3` trials độc lập** (mỗi trial tạo `conversation_id` mới và dữ liệu sạch).
     - Ghi nhận đồng thời **`Pass@3`** ($\ge 1$ lần đạt — đo khả năng tối đa của hệ thống) và **`Pass^3`** (cả $3/3$ lần đều đạt — đo độ tin cậy thực tế người dùng nhận được). **Release Gate sử dụng `Pass^3`**, không dùng `Pass@3`.

---

## 3. Cấu trúc 14 Evaluation Suites (`E01` – `E14`)

Danh sách 14 suite từ định hướng `Master Prompt §8` được hiệu chỉnh sát với chức năng thực tế của F1 v1.1 (tổng cộng **45 Test Cases** chi tiết tại [04-e2e-test-cases.md](file:///d:/StudyFlow-AI/docs/qa/f1/04-e2e-test-cases.md)):

| Suite ID | Tên Evaluation Suite | Trọng tâm kiểm thử theo Implementation thực tế | Số lượng TC | Mức ưu tiên chính |
|---|---|---|---:|---|
| **E01** | Basic Schedule Creation | Thiết lập giờ rảnh cơ bản + tạo 1 Task đủ thông tin + sinh `PlanProposal` + duyệt lên Calendar (bao gồm ca task `> 90p` phát hiện lỗi `CF-01`). | 3 | P0 |
| **E02** | Schedule Modification & Replanning | Các luồng sửa lịch **được hỗ trợ** (thêm lịch bận, đổi `SchedulingPolicy`, lập lại lịch tuần tới `CF-02`) + kiểm tra Guardrail cho yêu cầu dời 1 block đơn lẻ (`OUT OF SCOPE`). | 4 | P0 / P1 |
| **E03** | Cancellation, Archive & Deletion Boundaries | Hủy bản nháp Task/Proposal (`REJECT`), lưu trữ (`ARCHIVE`) khung giờ rảnh qua UI `/v1/actions`, và kiểm tra Guardrail khi user gõ lệnh xóa lịch/task đã duyệt qua Chat (`OUT OF SCOPE`). | 3 | P1 |
| **E04** | Natural Language & Temporal Scenarios (VI) | Tiếng Việt không dấu, viết tắt/teencode, gõ Telex/IME thật, `8r`, `10h kém 15`, `12h đêm`, `1 tiếng rưỡi`, emoji, giờ bất hợp lệ `25h`, thời lượng `0` hoặc âm, dải thứ `T2–T6`. | 8 | P0 / P1 |
| **E05** | Complex & Multiple Task Scheduling | Nhiều công việc trong 1 câu chat (đủ trường vs thiếu trường trên `/planner`), xếp lịch nhiều môn cạnh tranh theo `deadline_at` và `priority`. | 3 | P0 / P1 |
| **E06** | Constraint & Conflict Handling | Tránh lịch bận (`BUSY`), xử lý thiếu dung lượng (`PARTIAL` / `NONE`), mâu thuẫn `start_at > deadline_at` (`CF-07`), và cảnh báo khi thêm lịch bận đè lên `StudyBlock` đã duyệt. | 4 | P0 / P1 |
| **E07** | Ambiguous & Incomplete Requests | Thiếu giờ bắt đầu/thời lượng, câu mơ hồ (`"tối mai học bài"`), chống lỗi regex giờ→phút trên `PlannerClarificationPopup` (`CF-03`), và chống tự bịa ngày giờ. | 3 | P0 |
| **E08** | Multi-turn Conversation | Bổ sung thông tin qua 2–3 lượt giữ nguyên ngữ cảnh, tự sửa ý giữa chừng, và xử lý đổi chủ đề / gõ `"hủy"` khi đang `NEEDS_CLARIFICATION` (`CF-04`). | 3 | P0 / P1 |
| **E09** | Draft, Approval & Cancellation Workflow | Đảm bảo chưa xác nhận không ghi DB, gõ `"ok đồng ý"` trong chat không tự duyệt, xem và sửa/từ chối đề xuất lịch trên `ProposalReview`. | 2 | P0 |
| **E10** | Database & State Integrity | Đồng bộ trạng thái giữa trang Trợ lý AI (`/`) và trang Lịch (`/planner`), bảo toàn `StudyPlan` cũ khi proposal mới bị đánh dấu `STALE_PROPOSAL`. | 2 | P0 / P1 |
| **E11** | Recovery, Offline & Network Failure | F5 sau khi hiện thẻ duyệt, **F5 giữa lúc request đang Pending trên Slow 3G (`CF-04`)**, mất mạng Offline (`CF-09`), và phục hồi sau lỗi `503`. | 3 | P0 / P1 |
| **E12** | Concurrency & Duplicate Prevention | Double-click / nhấn Enter liên tiếp trên nút Gửi & nút Duyệt, và 2 tab trình duyệt cùng duyệt/hủy 1 bản nháp đồng thời (`< 0.5s`). | 2 | P0 / P1 |
| **E13** | Security, Access Control & Safety | Chặn JWT thiếu/hết hạn/chéo tài khoản, chống Prompt Injection tự phê duyệt, kiểm tra giới hạn `8.000` ký tự (`CF-08`), và kịch bản Content Safety (`PROPOSED`). | 3 | P0 / P2 |
| **E14** | Performance & End-to-End Reliability | Đo độ trễ P50/P95 của `POST /v1/messages` & `POST /v1/decisions` với model thật, kiểm soát hành vi retry khi LLM timeout `> 20s` (`CF-05`). | 2 | P1 |

*(Lưu ý tổng số Test Case chuẩn hóa là **45 Test Cases**: `3+4+3+8+3+4+3+3+2+2+3+2+3+2 = 45`, nằm đúng khoảng vàng `20–50` task đại diện theo `Master Prompt §6.E & §11.4`).*

---

## 4. Phân loại Nguyên nhân Gốc khi Đọc Transcript Thất bại (`Master Prompt §6.F`)

Khi bất kỳ Test Case nào trả kết quả `FAIL`, QA bắt buộc mở Network Log / Backend Log / Transcript để gắn đúng **1 trong 7 nhãn nguyên nhân gốc** dưới đây (không đổ lỗi chung chung cho "AI ngu"):

| Mã nhóm lỗi | Tên phân loại | Dấu hiệu nhận diện trên Transcript / Network | Ví dụ thực tế đã gặp ở F1 |
|---|---|---|---|
| **RC-AGENT** | Agent / NLU Extraction Failure | HTTP `200` từ DeepSeek nhưng JSON `ExtractionResult` sai slot, sai giờ (`8r` → `20:00`), sót thứ (`T2–T6` → chỉ `weekday=1`), hoặc rớt trường không nhất quán qua các trial. | `NLU-01` (Trial 2 & 3), `NLU-03` (`8r`), `CF-06` (`F1-B01`). |
| **RC-TOOL** | Intent-to-Operation Dispatch Failure | LLM trích xuất hợp lý nhưng `ChatProcessor` / `ActionProcessor` không nối tới handler hoặc chặn sai quy tắc. | `chat.py#L262` chặn `SET_AVAILABILITY` `UPDATE`/`ARCHIVE`; `chat.py` trả `action_reference = null` khi `NEEDS_CLARIFICATION`. |
| **RC-BACKEND** | Backend / Scheduler / Timeout Failure | Lỗi logic chuẩn hóa, tính lịch hoặc cấu hình gọi provider trong Python (`actions.py`, `generate.py`, `extractor.py`). | `CF-01` (`deadline_at = start_at + minutes`), `CF-02` (`generate.py` cắt `available_intervals`), `CF-05` (không tắt `thinking` gây timeout `20s`). |
| **RC-DB** | Database / Migration / RPC Failure | Lỗi ràng buộc SQL, khóa `lock_owner`, kiểm tra version/RLS hoặc điều kiện chặn trong hàm `app_api.*`. | `202611200004` khóa `candidate_patch` chỉ cho F2 recommendation. |
| **RC-FE** | Frontend / UI State Failure | Backend trả đúng nhưng UI parse sai, lưu `localStorage` trễ, tự retry sai hoặc thiếu kiểm tra input. | `CF-03` (`clarification.ts` biến `"8h"` thành `480` phút), `CF-08` (`ChatComposer` thiếu giới hạn `8.000` ký tự), `CF-04` (mất nháp khi F5 lúc Pending). |
| **RC-GRADER** | Grader / Harness Defect | Hệ thống thực tế chạy đúng nhưng script kiểm thử hoặc câu kiểm tra assert quá cứng nhắc/sai schema. | Lỗi thiếu khóa `base_plan` trong mock harness ban đầu (đã phát hiện và hiệu chỉnh ngay trong quá trình kiểm toán). |
| **RC-TEST** | Invalid / Out-of-Scope Test Case | Test case yêu cầu tính năng nằm ngoài Contract hiện hành mà không gắn nhãn `OUT OF SCOPE` / `N/A`. | Các test upload file Chat (`KENT-08, 09`) hoặc kỳ vọng dời 1 block đơn lẻ trong v1.1. |

---

## 5. Quy trình Thực thi Thường xuyên cho Team QA (`Master Prompt §10`)

### 5.1. Chuẩn bị Môi trường Sạch trước mỗi Đợt Test
1. **Không bao giờ trỏ vào Cloud Supabase `phomrutsdhdgejlskwcb`.** Chỉ dùng Supabase local (`http://127.0.0.1:54321`) + FastAPI local (`http://127.0.0.1:8000`) + Frontend Vite (`http://127.0.0.1:5173`).
2. Trước khi chạy bộ test chính thức: chạy `supabase db reset --yes` để đảm bảo toàn bộ 50 migrations sạch sẽ.
3. Mỗi Test Case (và mỗi Trial trong `Pass^3`) phải dùng **một tài khoản test mới hoặc xóa sạch `localStorage` + tạo `conversation_id` mới** để trạng thái `pending_actions` của ca trước không làm nhiễm `409` sang ca sau.

### 5.2. Biểu mẫu Ghi nhận Kết quả Bắt buộc cho Mỗi Lần Chạy

Mỗi dòng kết quả trong báo cáo của QA phải ghi đủ 12 trường:
- `Build / Commit SHA` (ví dụ: `e0cf937`)
- `Environment` (`Local Full-Stack: Vite + FastAPI + Local Supabase` hoặc `API Harness`)
- `Model Provider & Model Name` (ví dụ: `DeepSeek / deepseek-flash`)
- `Execution Mode` (`REAL MODEL E2E` / `SCRIPTED MOCK` — **cấm gộp chung hai chế độ này!**)
- `Suite & Test ID` (ví dụ: `E01 / F1-E2E-002`)
- `Trial Number` (`1/3`, `2/3`, `3/3`)
- `Status` (chỉ dùng đúng 5 nhãn: **`PASS`**, **`FAIL`**, **`BLOCKED`**, **`NOT TESTED`**, **`N/A`**)
- `Expected vs Actual` (mô tả ngắn gọn sự khác biệt ở trạng thái cuối)
- `Evidence` (Ảnh chụp màn hình Calendar/Chat + Request ID `X-Request-ID` + JSON response `/v1/plans` hoặc `/v1/tasks`)
- `Root Cause Tag` (`RC-AGENT`, `RC-BACKEND`, `RC-FE`, ...)
- `Bug ID` (mã ticket GitHub Issue / mã `CF-xx`)
- `Regression Status` (`NEW BUG`, `REOPENED`, `STILL FAILING`, `VERIFIED FIXED`)

### 5.3. Tần suất Thực thi (Execution Cadence)

| Thời điểm kích hoạt | Bộ kiểm thử bắt buộc chạy | Chế độ Model | Tiêu chí thông qua |
|---|---|---|---|
| **Sau mỗi Pull Request (CI + Dev)** | `contracts/check_contract.py` + `generate_contract_schema_migration.py --check` + Backend Unit/Acceptance + `evaluate_planner.py` + Frontend `tsc --noEmit` & `node --test` + các case hồi quy của module vừa sửa | Mock / Deterministic | `100% PASS` |
| **Trước khi Merge PR lớn vào `main` / Trước bản Demo** | **F1 Regression Checklist ([05-regression-checklist.md](file:///d:/StudyFlow-AI/docs/qa/f1/05-regression-checklist.md))** + toàn bộ các Test Case mức **`P0`** (`26` cases, `k = 1..3`) | **Real Model (`deepseek-flash`) + Local Supabase** | Đạt cả 5 Release Gates (`G1..G5`), `100%` P0 Security/Integrity PASS |
| **Sau khi đổi Model / Prompt / Orchestrator / Scheduler** | Chạy lại toàn bộ Suites **`E01, E02, E04, E05, E06, E07, E08, E14`** với **`k = 3` trials (`Pass^3`)** | **Real Model** | Không tụt `Pass^3`, `0` vi phạm Hard Constraint, P95 latency trong ngưỡng |
| **Định kỳ hàng tuần / Trước Release chính thức** | Toàn bộ **45 Test Cases (`E01`–`E14`)** trên trình duyệt thật + 2 tab + Chaos mạng | **Real Model + Full UI + Local Supabase** | Đạt toàn bộ Release Gates và ngưỡng KPI mục tiêu |
| **Ngay sau khi phát hiện Bug mới** | Viết thêm 1 Test Case tái hiện đúng câu lệnh/trạng thái lỗi vào `04-e2e-test-cases.md` & `f1_e2e_test_cases.json` | Mock (Unit) + Real Model (E2E) | Test mới phải `FAIL` trước khi vá và `PASS` ổn định (`3/3`) sau khi vá |
