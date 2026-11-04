# StudyFlow AI — Các công việc cần làm hiện tại

Ngày tổng hợp: 04/11/2026 | Đọc cùng [context.md](context.md)
Nguồn: [S1], [S2] và quan sát workspace, được mô tả chi tiết trong [context.md](context.md).

## ĐIỂM XUẤT PHÁT

Step 01–03 đã có thiết kế sơ bộ. Step 04 đã có Pipeline v0.1, chưa freeze.
Chưa có bằng chứng triển khai/benchmark; repository hiện mới có README.md
được theo dõi. “Có thiết kế” không đồng nghĩa công việc kỹ thuật đã hoàn tất.

Việc bắt đầu ngay: Step 04 vòng A — Orchestrator Input/Output Contract.
Thứ tự dưới đây là đề xuất để thực thi, không phải lịch đã được nhóm phê duyệt.
Chưa có owner hay ngày hoàn thành được chốt; không tự gán người/deadline.

Ký hiệu: [x] đã làm trong lần tổng hợp; [ ] còn phải làm.
P0: ưu tiên chốt thiết kế hiện tại; P1: triển khai sau contract;
P2: phần mở rộng/công việc để sau F1 core, tùy quyết định scope.
Các output dưới đây là cần tạo, chưa phải file hoặc API đang tồn tại.

## 0. ĐÃ HOÀN THÀNH TRONG LẦN TỔNG HỢP

- [x] Đọc toàn bộ các lượt được trả về của cả hai chat và context đính kèm.
- [x] Hợp nhất Step 01–04 vào [context.md](context.md), giữ rõ đề xuất và phần chưa kiểm chứng.
- [x] Lập danh sách việc có ưu tiên, dependency và tiêu chí hoàn thành.

## P0 — CHỐT THIẾT KẾ TRƯỚC KHI TRIỂN KHAI

- [ ] **P0-01. Xác nhận baseline và phạm vi F1 core**

  **Nguồn:** S1/S2; bổ sung tiêu chí hoàn thành khi tổng hợp.

  **Việc làm:**

  - Đối chiếu 0-main-20.pdf khi cần xác nhận yêu cầu chính thức; PDF hiện
    chưa có trong dữ liệu đã đọc. Không chặn soạn contract đề xuất vì việc này.
  - Tách rõ luồng core: task candidate/confirm, availability, automatic plan,
    xem lịch, propose reschedule, approval/commit.
  - Chốt UPDATE_TASK, DELETE_TASK, CREATE_STUDY_BLOCK có thuộc đợt MVP này
    không; chốt có cần entity FixedCommitment riêng hay biểu diễn khác.

  **Output:** danh sách in-scope/deferred, kèm nguồn yêu cầu và điểm còn cần duyệt.

  **Xong khi:** không có tính năng mở rộng nào âm thầm trở thành bắt buộc của MVP.

- [ ] **P0-02. Thiết kế Input/Output Contract của Orchestrator — LÀM NGAY**

  **Nguồn:** S2, vòng A được ưu tiên đầu tiên.

  **Việc làm:**

  - UserMessage: message gốc, timestamp, timezone, locale, conversation context;
    tách input user khỏi trusted authentication/system context.
  - ExtractionResult: intent(s), candidate slots, biểu thức gốc, ambiguities,
    missing fields và nguồn giá trị nếu áp dụng provenance.
  - PendingAction: định danh, intent, slots, missing/ambiguous fields,
    workflow state, version, expiry và tham chiếu proposal nếu có.
  - ValidatedCommand: operation/intent, normalized arguments và tham chiếu
    context cần thiết; không tin identity/ID/approval tự sinh từ LLM.
  - ToolResult: read/draft/proposal/commit/error, entity ID, version,
    unscheduled work và thông tin cần hiển thị cho user.
  - Approval evidence/context: cách gắn hành động user với đúng proposal,
    version và thời hạn; không chỉ là approval=true trong output LLM.
  - Thống nhất parameters/slots, candidate_id/task_candidate_id,
    end_date/deadline và cách chuyển duration thành interval.

  **Output:** schema có thể kiểm tra bằng máy và ví dụ hợp lệ/không hợp lệ.
    JSON Schema/Pydantic là các phương án đã nêu, chưa chọn stack.

  **Xong khi:** mọi ranh giới LLM ↔ Orchestrator ↔ F1 có input/output rõ;
    phân biệt field cần cho draft, confirm và scheduling; thiếu/null có nghĩa rõ.

  **Dependency:** có thể soạn ngay; freeze phần mở rộng sau P0-01.

- [ ] **P0-03. Hoàn thiện tool contracts và bảng intent → operation**

  **Nguồn:** S1/S2; contract Step 03 còn thiếu và một số tool chỉ có mô tả tối thiểu.

  **Việc làm:**

  - Hoàn thiện create_task_candidate, confirm_task, search_tasks,
    set_availability, generate_study_plan, get_study_plan,
    propose_reschedule và approve_study_plan theo scope đã chọn.
  - Bổ sung contract update/delete/manual block nếu chúng nằm trong scope;
    nếu chưa làm, ghi rõ cách trả UNSUPPORTED hoặc hướng dẫn thay thế.
  - Mỗi operation có input/output, validation, read/draft/propose/commit,
    authorization, confirmation policy, error, version và idempotency semantics.
  - Quy định availability mới/thay thế/xóa tác động thế nào tới confirmed plan.
  - Thống nhất partial proposal so với INSUFFICIENT_AVAILABILITY dạng lỗi;
    biểu diễn số phút chưa xếp được và lý do nếu chỉ xếp được một phần.

  **Output:** contract catalog và dispatch allowlist; không bắt intent:tool = 1:1.

  **Xong khi:** mọi intent in-scope có đường thực thi rõ; tool ghi không thể bỏ
    qua validation, quyền hay approval bắt buộc.

  **Dependency:** P0-01 và P0-02; có thể chỉnh đồng thời khi review contract.

- [ ] **P0-04. Chốt state management và routing rules**

  **Nguồn:** S2, vòng B.

  **Việc làm:**

  - Tách validation status, workflow state và entity status.
  - Viết transition table: input, điều kiện, action, next state, side effect.
  - Merge câu trả lời ngắn như “19h” vào đúng pending action.
  - Xử lý sửa slot, hủy, từ chối, expiry, đổi chủ đề và nhiều pending actions.
  - Khi user sửa yêu cầu, xác định khi nào proposal cũ mất hiệu lực.
  - Định nghĩa multi-intent tuần tự/dependency cho MVP; không tự thêm
    workflow phức tạp khi chưa cần.
  - Với “rảnh thứ Hai 8–11h, lập lịch tuần sau”: approval availability phải
    được xử lý trước khi dùng nó như dữ liệu chính thức để lập lịch.
  - “Đồng ý” chỉ route được khi có một proposal đích xác định rõ.

  **Output:** state/transition table và các kịch bản multi-turn/multi-intent.

  **Xong khi:** một câu trả lời không bị gắn nhầm action hoặc duyệt nhầm proposal.

  **Dependency:** P0-02/P0-03.

- [ ] **P0-05. Chuẩn hóa thời gian, entity resolution và scheduler invariants**

  **Nguồn:** S1/S2; các trường hợp ranh giới là câu hỏi bổ sung khi tổng hợp.

  **Việc làm:**

  - Chốt timezone/time representation và cách resolve mai/tuần sau/thứ Sáu tới.
  - Không tự đặt exact time cho “sáng/tối”; hỏi khi còn mơ hồ.
  - Chốt deadline chỉ có ngày, interval qua nửa đêm, planning period,
    recurrence và rule duration/start/end nhất quán.
  - Resolve tên task/block bằng DB; nhiều kết quả thì hỏi chọn.
  - Chốt eligibility và thứ tự deterministic: deadline trước, priority tie-break;
    quy định thêm tie-break/block splitting/workload khi triển khai cần tới.
  - Giữ constraints về availability, commitments, deadline và overlap;
    làm rõ cách tính remaining work khi đã có block trong lịch.

  **Output:** rule sheet dùng chung cho validator/scheduler và ví dụ ranh giới.

  **Xong khi:** cùng dữ liệu và config cho kết quả nhất quán, không dựa vào LLM
    để quyết định tính hợp lệ của lịch.

  **Dependency:** P0-01/P0-02; dùng để hoàn thiện P0-03/P0-04.

- [ ] **P0-06. Chốt approval, concurrency, persistence và recovery**

  **Nguồn:** S1/S2; version dữ liệu nền là nhận xét bổ sung khi tổng hợp.

  **Việc làm:**

  - Xác định bằng chứng user approval, proposal/version/user/expiry binding.
  - Revalidate constraints khi commit; phát hiện task/availability/commitment
    đổi kể cả khi plan version chưa đổi.
  - Chốt transaction boundary, idempotency key/retry semantics và xử lý
    request lặp hoặc hai lần approve đồng thời.
  - Quy định lỗi nào hỏi lại, replan, retry có giới hạn hoặc fallback form.
  - Với proposal cũ/hết hạn: không âm thầm commit; tạo/tải proposal hợp lệ.
  - Làm rõ rollback khi ghi lỗi; không coi rollback kỹ thuật là tính năng undo
    sản phẩm đã được chốt.

  **Output:** commit/recovery sequence và failure policy cho từng write operation.

  **Xong khi:** retry không ghi trùng, stale approval không ghi đè dữ liệu mới,
    kết quả UI luôn phản ánh đúng trạng thái persistence.

  **Dependency:** P0-03/P0-04/P0-05.

- [ ] **P0-07. Xây test matrix và tiêu chí đánh giá**

  **Nguồn:** S2, vòng C; chưa có ngưỡng định lượng được nhóm chốt.

  **Bộ tình huống tối thiểu:**

  - Single intent đầy đủ; thiếu deadline/effort; giá trị âm hoặc sai type.
  - Nhầm GENERATE_STUDY_PLAN / CREATE_STUDY_BLOCK / SET_AVAILABILITY.
  - Ngày tương đối; sáng/tối mơ hồ; ngày/giờ không hợp lệ; interval qua ngày.
  - Task trùng tên, entity không tồn tại hoặc không thuộc user.
  - Multi-turn “19h”, sửa câu trả lời, hủy và đổi chủ đề.
  - Multiple intents có dependency; nhiều pending actions cùng chờ duyệt.
  - Conflict, không đủ availability, partial plan và unscheduled work.
  - Approval thiếu/sai đối tượng, hết hạn, stale version/dữ liệu nền thay đổi.
  - Retry commit, double approval, LLM timeout/invalid JSON.
  Mỗi case ghi input + trusted context + DB fixtures + trạng thái trước,
    expected intent/slots/status/tool/state/response và side effects được phép.

  **Đo:** intent, slot extraction, clarification, dispatch correctness,
    end-to-end completion, hành vi ghi sai/vượt constraint; latency nếu benchmark.

  **Output:** tập case tiếng Việt, expected outcomes và cách tính metrics;
    tách dữ liệu phát triển khỏi tập đánh giá trước khi chọn model.

  **Xong khi:** nhóm có tiêu chí chấp nhận rõ; chưa tự gán tỷ lệ “đạt” khi chưa chạy.

  **Dependency:** soạn cùng P0-02; hoàn thiện expected behavior sau P0-03–P0-06.

## P1 — TRIỂN KHAI SAU KHI CONTRACT CỐT LÕI ĐỦ RÕ

- [ ] **P1-01. Chốt backend/API stack, database và phương án model bằng bằng chứng**
  - Ghi quyết định kỹ thuật và lý do dựa trên môi trường/nguồn lực thực tế.
  - Benchmark ứng viên LLM/NLU bằng test matrix; JEV router chỉ là phương án
    cần thử, chưa bắt buộc nằm trên critical path. Qwen chưa chốt version/size.
  - Kiểm tra multi-intent, slots, latency và toàn luồng; không chỉ intent accuracy.

  **Xong khi:** có số đo và giới hạn, phân biệt kiểm tra giả lập với inference thật.

  **Dependency:** contract, metric và dữ liệu đánh giá đã rõ; không cần chờ chọn
    model để hoàn thiện business rules deterministic.

- [ ] **P1-02. Dựng F1 backend theo contract và data model đã chọn**
  - Persistence, identity/authorization, candidate/confirmed task,
    availability/commitments theo scope, plan/block/version.
  - Scheduler deterministic và rule validators; partial/unscheduled output.
  - Proposal/reschedule/approval, transaction và idempotency.

  **Thứ tự đề xuất:** task + availability → generate/get plan → approval/commit
    → propose reschedule; điều chỉnh theo dependency của contract.

  **Xong khi:** các luồng core qua kiểm thử nghiệp vụ, không thay confirmed plan
    khi chưa có approval hợp lệ.

- [ ] **P1-03. Dựng Orchestrator và kết nối luồng user**
  - NLU adapter, schema validation, entity resolution, pending-action store.
  - Clarification, dispatch allowlist, approval routing và error recovery.
  - UI tối thiểu cho input, chọn entity, preview/partial plan, approve/reject.

  **Xong khi:** chạy được task → confirm → plan proposal → approval → persisted
    plan, cùng các nhánh multi-turn và lỗi quan trọng trong test matrix.

- [ ] **P1-04. Kiểm chứng F1 MVP và ghi nhận kết quả thực tế**
  - Chạy unit/domain, integration và end-to-end phù hợp với các luồng đã làm.
  - Kiểm tra ownership, stale/expired approval, retry và không ghi sai dữ liệu.
  - Ghi kết quả benchmark/test, môi trường, case lỗi và giới hạn còn lại.
  - Đối chiếu scope/acceptance criteria trước khi báo hoàn thành MVP.

  **Xong khi:** có bằng chứng chạy thật; đạt tiêu chí nhóm đã chốt, không chỉ demo
    một happy path hoặc kiểm tra JSON minh họa.

## P2 — CHỈ LÀM THEO QUYẾT ĐỊNH SCOPE / SAU F1 CORE

- [ ] UPDATE_TASK / DELETE_TASK: hoàn thiện và triển khai nếu được đưa vào đợt này;
  thiết kế tác động tới block/plan liên quan trước khi ghi thay đổi.
- [ ] CREATE_STUDY_BLOCK: manual scheduling sau khi được thống nhất phạm vi,
  có tool contract và luồng proposal/approval riêng hoặc tái sử dụng rõ ràng.
- [ ] FixedCommitment entity riêng và quản lý recurrence nâng cao nếu cần;
  scheduler core vẫn phải có cách tiếp nhận busy intervals theo baseline.
- [ ] JEV router tối ưu nếu benchmark cho thấy có ích và không làm giảm độ đúng.
- [ ] F2/F3: giữ trong lộ trình Post-MVP, chưa triển khai trong công việc hiện tại.

## ĐIỀU KIỆN ĐỂ ĐI TIẾP NGAY

Không cần thêm model hay framework để bắt đầu P0-02. Có thể soạn contract đề xuất
từ context hiện có. Những gì cần nhóm quyết định — scope, tech stack, owner,
deadline và ngưỡng chấp nhận — phải ghi là còn mở đến khi có quyết định thật.
Muốn khẳng định một yêu cầu thuộc proposal chính thức thì cần đối chiếu PDF gốc.
