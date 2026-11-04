# StudyFlow AI — Context tiếp nối thiết kế F1

Phiên bản tổng hợp: 1.1 | Ngày: 04/11/2026 | Múi giờ tham chiếu: Việt Nam (+07:00)
File công việc đi kèm: [cong_viec_can_lam.md](cong_viec_can_lam.md)

## 1. NGUỒN VÀ GIỚI HẠN

[S1 — Chat “Đọc proposal chính thức”](https://chatgpt.com/c/6ae9dafd-aeb0-83ec-9afd-ecc6ce8e904e)

Đã đọc 5 lượt hội thoại được công cụ trả về: Step 01, giải thích Task/Block/Plan,
Step 02, Step 03 và Context Handoff v1.0. Công cụ không cung cấp trang cũ hơn.

[S2 — Chat “Thiết kế Orchestrator Pipeline”](https://chatgpt.com/c/6aea7016-4684-83ec-bb27-e5015f2383f4)

Đã đọc 1 lượt hội thoại được trả về và file đính kèm “Văn bản đã dán (1).txt”.
File đính kèm là Context Handoff v1.0 từ S1; phản hồi là Step 04 v0.1.

Proposal được nhắc đến là 0-main-20.pdf, Midterm Engineering Report,
October 2026, 28 trang. Bản tổng hợp này KHÔNG đọc trực tiếp được PDF gốc.
Thông tin về proposal dưới đây được ghi nhận qua hai chat, chưa đối chiếu PDF.
Các trích dẫn nội bộ kiểu turn0file0 trong chat không thay thế việc đọc PDF.

Quy ước trạng thái:

- “Baseline theo chat”: nội dung được chat mô tả là thuộc proposal chính thức.
- “Thiết kế sơ bộ”: đã thảo luận, chưa phải specification được nhóm phê duyệt.
- “Còn mở”: cần quyết định, kiểm chứng hoặc thiết kế tiếp.
- “Nhận xét khi tổng hợp”: điểm thiếu được phát hiện lúc làm hai file này.

## 2. BỐI CẢNH VÀ PHẠM VI

Theo S1: StudyFlow AI thuộc môn CSC10014 — Computational Thinking, HCMUS;
nhóm 6 thành viên; vai trò người dùng là Backend Developer & AI Engineer.

Baseline theo chat có 3 core features:

- F1 — Intelligent Academic Planner: quản lý task, deadline, availability,
  tạo và điều chỉnh kế hoạch học tập; là trọng tâm Initial MVP.
- F2 — Learning Assessment & Adaptive Revision: quiz dựa trên tài liệu,
  kiểm chứng câu hỏi/đáp án, chấm điểm, đề xuất ôn tập; Post-MVP.
- F3 — Daily AI Learning: giải thích theo tài liệu, progressive hints,
  session summary và confirmation; Post-MVP.

Phạm vi làm việc hiện tại: thiết kế F1 trước; không tự mở rộng sang F2/F3.
Hướng tích hợp dài hạn được S1 nêu: F1 → F3 → F2 (optional) → F1.

Mục tiêu: user dùng tiếng Việt tự nhiên để thêm task, khai báo giờ rảnh,
lập kế hoạch, xem lịch và yêu cầu dời buổi học. Hệ thống phải xử lý được
thông tin thiếu/mơ hồ, giữ ngữ cảnh và kiểm soát thay đổi dữ liệu.

## 3. ĐIỂM ĐANG DỪNG

- Step 01 — Intent Catalog v0.1: đã thảo luận ở mức conceptual design.
  Ban đầu 7 intent; sau đó bổ sung CREATE_STUDY_BLOCK thành 8 intent.
- Step 02 — Parameter Schema v0.2: đã có field và validation rules sơ bộ.
- Step 03 — F1 Tool Contract v0.1: đã có tool catalog, một số JSON ví dụ,
  nguyên tắc lỗi, authorization và confirmation; chưa đầy đủ mọi tool.
- Step 04 — Orchestrator Pipeline v0.1: ĐÃ CÓ bản thiết kế 10 giai đoạn,
  state machine và các lỗ hổng cần xử lý; vẫn là đề xuất chưa chốt.

Vì vậy, bước tiếp theo không phải bắt đầu Step 04 từ số 0.
Tiếp tục Step 04 theo 3 vòng do S2 đề xuất:

- **Vòng A:** Orchestrator Input/Output Contract.
- **Vòng B:** State Management & Routing Rules.
- **Vòng C:** Test Matrix.

Ưu tiên A trước, đồng thời sửa các contract Step 02–03 chưa nhất quán.

Quan sát workspace E:\TDTT\StudyFlow-AI ngày 04/11/2026:
repository mới có README.md được Git theo dõi, chưa thấy mã nguồn backend
hay bộ kiểm thử. Hai chat cũng không cung cấp bằng chứng đã triển khai F1.
Không suy từ “đã thiết kế” thành “đã code”, “đã chạy” hoặc “đã benchmark”.

## 4. KIẾN TRÚC VÀ RANH GIỚI TRÁCH NHIỆM

Hướng thiết kế Hybrid, Contract-First:
User Interface → Shared Orchestrator → F1 Backend → Shared Academic Records.
Shared Orchestrator có thể mở rộng cho F2/F3 sau, không cần triển khai chúng ngay.

- LLM/NLU: nhận diện intent, trích xuất candidate parameters và sự mơ hồ.
- Orchestrator: quản lý hội thoại, phân giải context, gọi validator, hỏi lại,
  chọn tool trong allowlist, điều phối proposal/approval và diễn giải kết quả.
- F1 Backend: kiểm tra quyền và business rules, truy vấn entity thật,
  scheduling deterministic, revalidation, transaction và persistence.
- UI: hiển thị draft/proposal, câu hỏi bổ sung, lỗi và hành động xác nhận.

Nguyên tắc xuyên suốt trong hai chat:

- Không đưa raw JSON từ LLM thẳng vào thao tác có quyền ghi dữ liệu.
- Không để LLM tự tạo user_id, entity ID hoặc quyền truy cập.
- Identity và quyền lấy từ authenticated backend context.
- Không tự bịa deadline, effort, task đích hoặc giờ bắt đầu còn thiếu.
- LLM không quyết định lịch bằng cách bỏ qua hard constraints.
- Thay đổi lịch quan trọng theo Proposal → User Approval → Revalidate → Commit.
- READY không đồng nghĩa đã được user duyệt; PROPOSED không phải CONFIRMED.
- Đọc dữ liệu, tạo draft/proposal và commit là các loại thao tác khác nhau.

## 5. DATA MODEL ĐÃ THẢO LUẬN

**AcademicTask:** việc học cần hoàn thành, chưa phải một ô thời gian trên lịch.
Field được S1 liệt kê: task_id, course_id, title, start_date,
end_date/deadline, estimated_minutes, remaining_minutes, priority.
Ví dụ: bài OOP cần 240 phút, deadline thứ Sáu.
Luồng sơ bộ: task candidate/DRAFT → user xác nhận → confirmed task.
Chỉ confirmed task đủ điều kiện mới được scheduler sử dụng.

**PlannedStudyBlock:** khoảng thời gian cụ thể dành cho một task.
Ví dụ: thứ Hai 08:00–10:00 làm bài OOP.
Một task có thể có nhiều block; task chưa xếp được có thể có 0 block.
Quan hệ Task → Block 1:0..N là đề xuất cần thống nhất với data model gốc.

**StudyPlan:** tập hợp nhiều block trong một planning period, có thể phục vụ
nhiều task. Trạng thái minh họa: PROPOSED hoặc CONFIRMED; có version.

**Availability:** khoảng thời gian user có thể học.
**FixedCommitment:** khoảng bận như lịch học trên trường hoặc gym.
Theo S1, proposal có yêu cầu kiểm tra existing commitments, nhưng entity
FixedCommitment riêng là đề xuất bổ sung, chưa phải entity đã được chốt.
Gym thứ Hai 15:00–17:00 là ví dụ busy interval, không phải AcademicTask.

Phân biệt hai nhu cầu:

- Automatic planning: hệ thống phân bổ nhiều block từ task và constraints.
- Manual scheduling: user chỉ định buổi học cụ thể; vẫn phải kiểm tra constraint
  và duyệt thay đổi. CREATE_STUDY_BLOCK là mở rộng cần chốt scope trước khi code.

## 6. INTENT CATALOG VÀ PARAMETERS SƠ BỘ

### `CREATE_TASK`

  title, course_name, start_date, deadline, estimated_minutes,
  remaining_minutes, priority.
  Có thể tạo candidate thiếu dữ liệu; cần đủ dữ liệu và xác nhận trước scheduling.

### `UPDATE_TASK`

  task_id, fields_to_update; phải có ít nhất một field thay đổi.
  Entity cần được resolve từ DB; không đoán ID từ tên task.

### `DELETE_TASK`

  task_id; lý do xóa có thể optional. Phải resolve đúng task và xác nhận phù hợp.

### `SET_AVAILABILITY`

  date hoặc weekday, start_time, end_time, recurrence, timezone.
  Recurrence sơ bộ: NONE/WEEKLY; timezone lấy từ cấu hình đáng tin cậy.

### `GENERATE_STUDY_PLAN`

  start_date, end_date, selection_mode, task_ids.
  Selection mode sơ bộ: ALL_ELIGIBLE/SELECTED_TASKS.
  Task list có thể lấy từ DB; không bắt user cung cấp lại mọi task.

### `RESCHEDULE_STUDY_BLOCK`

  block_id, target_date, start_time, end_time, reason hoặc constraints.
  Có thể giữ duration cũ từ DB nếu user không yêu cầu thay đổi.
  Chỉ đề xuất thay đổi, chưa cập nhật confirmed block.

### `GET_STUDY_PLAN`

  start_date, end_date, status_filter: CONFIRMED/PROPOSED/ALL.
  Khoảng truy vấn mặc định nếu có phải được quy định trước.

### `CREATE_STUDY_BLOCK` — intent bổ sung, chưa chốt thuộc MVP

  task_id, date, start_time, end_time, plan_id optional.
  Extraction có thể nhận duration_minutes rồi hệ thống tính end từ start.

Ví dụ phân biệt:

- “Lập lịch học tuần sau” → GENERATE_STUDY_PLAN.
- “Xếp buổi OOP thứ Hai 8h–10h” → CREATE_STUDY_BLOCK.
- “Tao rảnh thứ Hai 8h–10h” → SET_AVAILABILITY.
- “Tạo lịch học sáng thứ Hai” có thể mơ hồ; cần hỏi thêm.
- “Tao rảnh thứ Hai 8h–11h, lập lịch tuần sau” có nhiều intent và dependency.

## 7. HAI CẤP SCHEMA VÀ VALIDATION

Intent Extraction Schema:
  Output chưa đáng tin cậy của LLM; cho phép field thiếu/null,
  giữ biểu thức ngày giờ và task reference khi chưa resolve.

Validated Command Schema:
  Dữ liệu được hệ thống kiểm tra, chuẩn hóa, resolve entity và xác minh quyền;
  đủ điều kiện chuyển sang operation tương ứng. Không thay thế approval.

Phân biệt extraction requirement và execution requirement:
field không xuất hiện trong câu user có thể đã có trong DB/context/config;
chỉ hỏi lại khi thực sự thiếu hoặc còn mơ hồ.

Validation status sơ bộ: READY, NEEDS_CLARIFICATION, UNSUPPORTED, INVALID.
Đây là trạng thái dữ liệu, khác với workflow state và trạng thái entity.

Ba lớp kiểm tra theo S2:

- Structural: JSON, type, enum; Orchestrator.
- Semantic: field bắt buộc, quan hệ thời gian/giá trị; Orchestrator/shared validator.
- Domain: entity ownership, availability, deadline, overlap; F1 Backend.

Rules sơ bộ:

- start_date <= deadline; estimated_minutes > 0.
- 0 <= remaining_minutes <= estimated_minutes.
- Interval kết thúc sau bắt đầu; hỗ trợ qua ngày cần rule riêng.
- Entity phải tồn tại và thuộc quyền truy cập của user.
- “Sáng/tối” không tự biến thành giờ chính xác mặc định.
- Ngày tương đối phải resolve theo timestamp và timezone của request.
- Các ngày/ID trong JSON ở chat chỉ là ví dụ, không phải dữ liệu thật.

## 8. TOOL CONTRACT V0.1

Tool catalog đã đề xuất:

- create_task_candidate: write draft; trả task_candidate_id, DRAFT,
  validation {is_valid, missing_fields, errors}, requires_confirmation.
  Draft thiếu deadline/effort có thể tồn tại nhưng chưa được scheduling.
- confirm_task: chuyển candidate hợp lệ và đã duyệt thành task.
  S3 mới mô tả input/output tối thiểu, chưa có contract đầy đủ.
- search_tasks: read; query, course/status filters → danh sách task.
- set_availability: write; date/weekday, interval, recurrence → availability.
  Cần xác nhận trước khi ghi đè; nếu gây conflict với confirmed plan thì
  thông báo và đề xuất replan, không âm thầm sửa lịch đã xác nhận.
- generate_study_plan: propose; planning period, selection mode/task_ids →
  PROPOSED, plan_id, version, study_blocks, unscheduled_tasks, requires_approval.
- get_study_plan: read; planning period → kế hoạch; filter cần thống nhất schema.
- propose_reschedule: propose; block_id, target time/constraints → revised proposal.
- approve_study_plan: commit; ví dụ input plan_id, expected_version, approval;
  output CONFIRMED và version mới sau kiểm tra lại.

Một intent có thể cần nhiều tool; không áp dụng ánh xạ 1:1 máy móc.
`UPDATE_TASK`, `DELETE_TASK` và `CREATE_STUDY_BLOCK` chưa có tool contract tương ứng.
Tên tool/endpoint cho các phần thiếu chưa được chốt; không coi tên mới tự đặt
trong phiên tiếp theo là API đang tồn tại.

Error envelope minh họa ở S3:
```text
  status: ERROR
  error: {code, message, details, retryable}
```

Codes: MISSING_REQUIRED_FIELD, INVALID_PARAMETER, ENTITY_NOT_FOUND,
TIME_CONFLICT, INSUFFICIENT_AVAILABILITY, STALE_PLAN_VERSION, APPROVAL_REQUIRED.
Không coi danh sách này là error specification đã hoàn chỉnh.

Scheduling theo baseline được chat mô tả:

1. Tải confirmed tasks và các constraints thực tế.
2. Deadline sớm trước, priority phân xử khi deadline bằng nhau.
3. Phân bổ block trong thời gian hợp lệ, kiểm tra deadline/overlap/workload.
4. Trả rõ phần chưa xếp được khi thiếu availability; không giả vờ đã xếp đủ.
5. Đưa proposal để user duyệt; lịch confirmed chưa thay đổi.

Approval phải gắn đúng proposal, version, authenticated user và thời hạn hợp lệ.
LLM sinh approval=true không phải bằng chứng user đã đồng ý.
“Đồng ý” qua chat chỉ hợp lệ khi xác định được đúng proposal đang chờ duyệt.
Backend revalidate quyền, version và constraints khi commit, dùng transaction
và idempotency để tránh ghi trùng khi retry. Chi tiết kỹ thuật vẫn còn mở.

## 9. STEP 04 — PIPELINE V0.1

Đây là 10 giai đoạn logic, có vòng lặp và nhánh; không phải chuỗi tuyến tính cứng.

1. **Input processing:** giữ câu gốc; nạp timestamp, timezone, locale,
   conversation context đáng tin cậy; kiểm tra pending action.
2. **Intent classification:** phân biệt single, multiple, ambiguous/unsupported.
3. **Slot extraction:** lấy candidate parameters và ambiguities, chưa tạo lệnh ghi.
   Đề xuất lưu provenance: user nói, context đã xác nhận, hoặc hệ thống tính.
4. **Context management:** giữ PendingAction để nhận câu trả lời nhiều lượt;
   hỗ trợ sửa, hủy, đổi chủ đề, hết hạn và version của context.
5. **Validation:** structural + semantic + domain; quyết định status.
6. **Clarification:** hỏi tối thiểu field đang chặn xử lý hoặc yêu cầu chọn entity.
7. **Tool dispatch:** chuyển validated command qua mapping/allowlist deterministic;
   không cho LLM tự đặt tool hay gọi endpoint tùy ý.
8. **Response handling:** diễn giải đúng kết quả backend, phân biệt proposal/commit,
   hiển thị conflict và phần unscheduled.
9. **Confirmation & persistence:** nhận approval hợp lệ; revalidate rồi commit.
10. **Error recovery:** xử lý theo mã lỗi, retry có giới hạn, fallback form thủ công.

Workflow state ở mức ý tưởng:

```text
Input → Extract → Validate
  thiếu/mơ hồ → Awaiting clarification → Merge/Extract → Validate
  invalid/unsupported → Error hoặc Fallback
  ready → Tool execution
    read result → Trả kết quả
    proposed change → Awaiting approval
      reject/cancel → Cancelled
      approve → Revalidate & Commit → Committed hoặc Error/Proposal mới
```

Enum đầy đủ và transition guards chưa được freeze.

Ví dụ multi-turn (giả định request ngày 04/11/2026, timezone Việt Nam):
User: “Xếp tao 2 tiếng OOP tối mai.”
Extraction: CREATE_STUDY_BLOCK, task_reference=OOP, date_expression=tối mai,
duration_minutes=120, start_time=null.
Hệ thống resolve ngày 05/11/2026 và tra task; nếu có nhiều task phải hỏi chọn.
Khi đã xác định task, hỏi giờ bắt đầu. User trả “19h” → merge pending action,
tính 19:00–21:00, validate, tạo proposal rồi chờ approval.
Không lưu block chỉ vì extraction đã đủ field. Đây là ví dụ thiết kế cho
manual scheduling, không chứng minh tính năng đã được duyệt hoặc triển khai.

## 10. CÁC ĐIỂM CÒN MỞ VÀ NHẬN XÉT KHI TỔNG HỢP

Các điểm S1/S2 đã nêu:

- Chốt scope manual scheduling, update/delete và FixedCommitment riêng.
- Hoàn thiện các tool contract thiếu; schema chính thức và error rules.
- Pending-action lifecycle, expiry, version, sửa/hủy/đổi chủ đề.
- Multi-intent sequencing, dependency, clarification và approval routing.
- Date/time parser, timezone strategy, database/API/backend stack.
- Cơ chế confirmation, transaction, idempotency và rollback khi lỗi.
- Benchmark model; JEV có thể là router nhẹ, Qwen là một ứng viên LLM.
  Chưa chọn model/version/kích thước, framework hay database.
- Đánh giá cả slots, clarification, dispatch và hành vi ghi sai/vượt constraint;
  intent accuracy đơn lẻ không đủ.

Nhận xét thêm khi tổng hợp, chưa phải quyết định của nhóm:

- Tên field đang lệch giữa ví dụ: parameters/slots; candidate_id/
  task_candidate_id; end_date/deadline. Cần vocabulary thống nhất.
- Step 04 dùng duration_minutes và provenance nhưng chưa có schema chuẩn
  cho chúng; không được coi JSON ví dụ là schema đủ để code.
- Chưa phân định đầy đủ field cần để tạo draft, xác nhận task và scheduling.
- Chưa có policy rõ cho deadline chỉ có ngày, interval qua nửa đêm,
  mốc đầu/cuối planning period và recurrence có hiệu lực tới khi nào.
- Plan version riêng có thể chưa phát hiện task/availability/commitment đổi;
  cần quy định cách phát hiện dữ liệu nền thay đổi và revalidate lúc commit.
- Chưa rõ thiếu giờ rảnh là partial proposal hay ERROR trong từng tình huống;
  cần thống nhất unscheduled work và error semantics để UI không hiểu nhầm.
- Chưa có owner, deadline công việc, ngưỡng benchmark hay tiêu chí release
  do nhóm chốt. File TODO chỉ đưa thứ tự và tiêu chí hoàn thành đề xuất.

Giữ vai trò phản biện: nêu rõ dữ liệu thiếu, không bịa quyết định hoặc kết quả.
Nếu cần kết luận về nội dung chính thức của proposal, phải lấy lại PDF gốc
và kiểm tra mục liên quan. Không cần PDF để tiếp tục phần thiết kế đã ghi rõ
là đề xuất, nhưng không được biến đề xuất đó thành yêu cầu chính thức.
