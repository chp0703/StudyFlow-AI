# Tổng hợp Lỗi QA Feature 1 (Intelligent Academic Planner) — Tài liệu Sửa lỗi cho Team DEV

> **Phạm vi tài liệu:** Tổng hợp, khử trùng lặp và đối chiếu tận dòng code toàn bộ kết quả từ **9 báo cáo QA Feature 1** trên nhánh chuẩn `main @ e366422`.
>
> **Quy ước gộp lỗi:** **1 nguyên nhân gốc rễ = 1 mã lỗi duy nhất** (`F1-FIX-01` → `F1-FIX-21` cho mã nguồn sản phẩm; tách riêng `F1-FIX-22` ở Phụ lục 1 cho script Auto-QA). Các lỗi liên tầng (`[BE + FE]`, `[BE + DB + FE]`, ...) chỉ xuất hiện **đúng 1 lần** tại nhóm chính và trình bày đầy đủ phần sửa cho từng tầng ngay trong mục đó.

---

## 1. Ngữ cảnh 9 Báo cáo QA Nguồn & Trạng thái Nhánh Code

### 1.1. Danh sách 9 báo cáo QA đầu vào

| # | Tài liệu nguồn | Người chạy / Môi trường & Commit | Phạm vi ghi nhận |
|---|---|---|---|
| 1 | `F1_QA_BaoCao_25-11.md` | Hùng · `e4f38f9` / `origin/main` `e366422` · `deepseek-flash` · Vite `5173`, FastAPI `8001` · Browser `1366×820` + test tay `TAY-01..05` | 29 mục FAIL / NOT TESTED / Cần Dev xác nhận |
| 2 | `F1_QA_BaoCao_25-11_final.pdf` | Hùng · cùng đợt kiểm thử File 1 | Trang 1–8 trùng File 1 + trang 9–20 gồm 47 ảnh chụp bằng chứng |
| 3 | `F1_QA_Report_Huong_20261125.md` | Hương · `main @ e366422` · Vite `5173`, FastAPI `8000`, Supabase `54321` | Auto QA 6/12 PASS, UI runner 1/5 PASS, Unit 212 BE / 137 FE, 177 contract fixtures |
| 4 | `F1_Auto_QA_Report_Kent_20261125.md` | Kent (Part 1) · nhánh riêng `fix/f1-chat-planner-qa-kent @ 7b58575` · `deepseek-chat` | 25/32 PASS · 7 BUG · 5 P0 FAIL; UI runner 4/5 PASS |
| 5 | `F1_Manual_QA_Report_Kent_20261125.md` | Kent (Part 2) · Chrome/macOS trên `7b58575` | 15 mã `KENT-QA-001..015`: 14 mở/cần xác minh, 1 đóng (`KENT-QA-010`) |
| 6 | `bao-cao-f1-auto-qa.pdf` | `main @ e366422` · `deepseek-flash` thật · FastAPI `8193`, Supabase QA `55421` (52 migration) | 24/32 PASS + kiểm tra web `CF-01` |
| 7 | `bao-cao-f1-web-va-calendar.pdf` | `main @ e366422` · Edge Computer Use · `deepseek-flash` thật | Calendar, Web UI, mạng/refresh và NLU thủ công |
| 8 | `f1_qa_report_20261125_111830.md` | Pre-`040213fb` · `deepseek-flash` + Embedded RPC Harness | 23/32 PASS · 9 BUG · P0 FAIL 6 |
| 9 | `f1_qa_report_20261125_111933.md` | `deepseek-flash` + Embedded RPC Harness | 1/1 PASS `F1-E12-02` (khép lỗi lịch sử `[200, 422]` ở File 8) |

### 1.2. Đối chiếu trạng thái `main @ e366422` so với `fix/f1-chat-planner-qa-kent @ 7b58575`

Toàn bộ các bản vá trên nhánh riêng `fix/f1-chat-planner-qa-kent @ 7b58575` hiện **CHƯA được merge vào `main @ e366422`**. Khi đối chiếu trực tiếp mã nguồn trên `main @ e366422`:

- **`F1-FIX-06` (`F1-E08-03`):** Nhánh Kent đã PASS 1/1 (`19:04`, `20:16`), nhưng **`main` CÒN LỖI** — [chat.py:315](../../../backend/app/orchestrator/chat.py#L315), [chat.py:348-349](../../../backend/app/orchestrator/chat.py#L348-L349) và [actions.py:278-279](../../../backend/app/orchestrator/actions.py#L278-L279) chưa truyền `reference=` khi trả `NEEDS_CLARIFICATION`.
- **`F1-FIX-12` (`F1-E07-01`):** Nhánh Kent đã PASS UI runner từ `19:10:30`, nhưng **`main` CÒN LỖI** — [clarification.ts:105-128](../../../frontend/src/features/planner/clarification.ts#L105-L128), [clarification.ts:182-188](../../../frontend/src/features/planner/clarification.ts#L182-L188).
- **`F1-FIX-13` (`F1-E13-02-UI`):** Nhánh Kent đã PASS UI runner từ `19:02:47`, nhưng **`main` CÒN LỖI** — cả [ChatComposer.tsx:131-151](../../../frontend/src/features/assistant/ChatComposer.tsx#L131-L151) lẫn [PlannerCommandComposer.tsx:172-189](../../../frontend/src/features/planner/PlannerCommandComposer.tsx#L172-L189) đều thiếu `maxLength={8000}`.
- **`F1-FIX-14` (`F1-E14-02-UI` & Latency):** Nhánh Kent đã PASS UI runner từ `19:02:47` (và chạy `deepseek-chat` đạt P95 = `1.624,5 ms`), nhưng **`main` CÒN LỖI** — [endpoints.ts:404-418](../../../frontend/src/api/endpoints.ts#L404-L418) (`sendMessage`) thiếu `retry: false`, còn `deepseek-flash` có P95 `6,45s–10,66s`.
- **Toàn bộ các mã còn lại (`F1-FIX-01..05`, `07..11`, `15..22`):** Đều **CÒN LỖI** trên `main @ e366422`.

---

## 2. Bảng Tổng hợp Phân công Nhanh (21 Lỗi Sản phẩm)

| Mã lỗi | Mức độ | Layer | Tóm tắt nguyên nhân gốc rễ | File chính trên `main @ e366422` |
|---|---|---|---|---|
| [F1-FIX-01](#f1-fix-01-p0-be--fe--lỗi-http-422-horizon-start_at-and-end_at-must-be-minute-aligned-khi-lập-lịch-qua-chat--action) | **P0** | `[BE + FE]` | `start_at`/`end_at` còn giây/microsecond lẻ không làm tròn phút trước khi gọi scheduler | [chat.py](../../../backend/app/orchestrator/chat.py#L267-L272), [actions.py](../../../backend/app/orchestrator/actions.py#L96-L118), [revisionScheduling.ts](../../../frontend/src/features/planner/revisionScheduling.ts#L78-L91) |
| [F1-FIX-02](#f1-fix-02-p0-be--db--hạn-mặc-định-không-tính-thời-gian-nghỉ-cf-01--llmbackend-chấp-nhận-deadline_at--start_at) | **P0** | `[BE + DB]` | Hạn mặc định `start_at + estimated_minutes` thiếu `break_minutes` gây rớt block (`CF-01`); DB chỉ chặn `start_at > deadline` nên lọt `deadline_at == start_at` | [workflow_shared.py](../../../backend/app/orchestrator/workflow_shared.py#L56-L66), [actions.py](../../../backend/app/orchestrator/actions.py#L107-L118), [202611140001_...sql](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L128-L134) |
| [F1-FIX-03](#f1-fix-03-p0-be--fe--lỗi-lập-lại-lịch-cf-02-retained-block-is-outside-current-availability-http-422) | **P0** | `[BE + FE]` | `generate.py` cắt `available_intervals` theo `generation_scope` trong khi `constraints.py` kiểm tra mọi `retained_blocks` ngoài scope; `TaskPanel` che lỗi bằng chuỗi cứng | [generate.py](../../../backend/app/f1/planning/generate.py#L102-L116), [constraints.py](../../../backend/app/f1/scheduler/constraints.py#L250-L260), [TaskPanel.tsx](../../../frontend/src/features/planner/TaskPanel.tsx#L231-L232) |
| [F1-FIX-04](#f1-fix-04-p0-be--ràng-buộc-cứng-start_at--expected_utc-khiến-task-không-xếp-được-lịch-dù-còn-giờ-rảnh-trước-hạn-hcọ-lý) | **P0** | `[BE]` | Scheduler khóa cứng block đầu đúng từng phút `== task.start_at`, loại toàn bộ khung rảnh hợp lệ khác trước hạn | [engine.py](../../../backend/app/f1/scheduler/engine.py#L129-L181), [constraints.py](../../../backend/app/f1/scheduler/constraints.py#L452-L462) |
| [F1-FIX-05](#f1-fix-05-p0--gate-3-fail-fe--lộ-lịch-sử-chat--bản-nháp-giữa-2-tài-khoản-dùng-chung-trình-duyệt-qa-sec-01) | **P0** *(Gate 3)* | `[FE]` | IndexedDB lịch sử chat dùng 1 tên DB cố định toàn trình duyệt, không cô lập theo `userId` và không reset state khi đổi tài khoản | [conversationHistory.ts](../../../frontend/src/features/assistant/conversationHistory.ts#L436-L517), [useConversationHistory.ts](../../../frontend/src/features/assistant/useConversationHistory.ts#L34-L106) |
| [F1-FIX-06](#f1-fix-06-p0--gate-4-fail-be--db--fe--kẹt-cứng-hội-thoại-409-action_review_required-khi-làm-rõ-hủy-popup-planner-hoặc-f5-giữa-chừng-cf-04) | **P0** *(Gate 4)* | `[BE + DB + FE]` | `NEEDS_CLARIFICATION` trả `action_reference: null`; đóng popup chỉ clear local state; thiếu API khôi phục pending sau F5 nên kẹt 409 | [chat.py](../../../backend/app/orchestrator/chat.py#L291-L349), [actions.py](../../../backend/app/orchestrator/actions.py#L278-L279), [routes.py](../../../backend/app/api/v1/routes.py#L359-L375), [usePlanner.ts](../../../frontend/src/features/planner/usePlanner.ts#L176-L454), [Assistant.tsx](../../../frontend/src/features/assistant/Assistant.tsx#L718-L748) |
| [F1-FIX-07](#f1-fix-07-p1-fe--tab-bị-từ-chối-đồng-thời-409-stale_entity_version-vẫn-giữ-nút-xác-nhận--hủy) | **P1** | `[FE]` | Nhánh `catch` của `api.decide` không đóng proposal / không chuyển trạng thái khi gặp `409 STALE_ENTITY_VERSION` | [usePlanner.ts](../../../frontend/src/features/planner/usePlanner.ts#L404-L406), [Assistant.tsx](../../../frontend/src/features/assistant/Assistant.tsx#L822-L823) |
| [F1-FIX-08](#f1-fix-08-p1-be--contractdb--fe--thiếu-validate-sớm-dữ-liệu-công-việc-start_at--deadline_at-estimated_minutes-cực-đoan-0) | **P1** | `[BE + Contract/DB + FE]` | Không chặn sớm `start_at >= deadline_at` khi tạo nháp; `estimated_minutes` thiếu trần hợp lý (cho phép `99999`); lỗi `<= 0` trả câu chung chung và FE ghi đè bằng `"Dữ liệu chưa hợp lệ."` | [chat.py](../../../backend/app/orchestrator/chat.py#L216-L316), [actions.py](../../../backend/app/orchestrator/actions.py#L77-L146), [f1.schema.json](../../../contracts/schemas/f1.schema.json#L337-L348), [client.ts](../../../frontend/src/api/client.ts#L179-L210) |
| [F1-FIX-09](#f1-fix-09-p0-nluprompt--be--ai-trích-xuất-sai-tiếng-việt-khẩu-ngữteencode-rơi-intent-hoặc-trả-sai-khi-hỏi-lịch-bận-n03) | **P0** | `[NLU/Prompt + BE]` | Prompt thiếu quy tắc/few-shot khẩu ngữ & teencode (`8r`, `lm bt`, câu ghép 2 intent); hỏi lịch bận bị dồn vào `GET_STUDY_PLAN` | [extractor.py](../../../backend/app/nlu/extractor.py#L15-L42), [chat.py](../../../backend/app/orchestrator/chat.py#L180-L370) |
| [F1-FIX-10](#f1-fix-10-p1-be--fe--không-chặn-khung-giờ-rảnhbận-đảo-ngược-start--end-trước-thẻ-duyệt-n02b) | **P1** | `[BE + FE]` | Không kiểm tra `start < end` trước `build_action` cho `SET_AVAILABILITY`/`SET_BUSY_INTERVAL`; Trợ lý AI không khóa nút `Xác nhận` theo `approvalError` | [chat.py](../../../backend/app/orchestrator/chat.py#L252-L262), [mappers.ts](../../../frontend/src/api/mappers.ts#L439-L511), [apiAssistant.ts](../../../frontend/src/features/assistant/apiAssistant.ts#L45-L61), [ChatTranscript.tsx](../../../frontend/src/features/assistant/ChatTranscript.tsx#L171-L183) |
| [F1-FIX-11](#f1-fix-11-p2-be--compose-lặp-câu-xác-nhận-5-lần--ghép-câu-lỗi-bước-trước-vào-thẻ-bước-sau) | **P2** | `[BE]` | `compose()` nối thô message các step trong `workflow_continuations` gây lặp 5 lần hoặc ghép câu lỗi bước trước vào thẻ xác nhận bước sau | [chat.py](../../../backend/app/orchestrator/chat.py#L225-L355) |
| [F1-FIX-12](#f1-fix-12-p0--gate-5-fail-fe--bộ-phân-tích-câu--điền-sẵn-form-làm-rõ-trên-planner-sai-giờ-thời-lượng-ngày-và-rác-tiêu-đề-cf-03) | **P0** *(Gate 5)* | `[FE]` | Regex `clarification.ts` bắt nhầm giờ thành thời lượng (`8h` → `480p`), bắt `"trong 2h"` thành `02:00 AM`, sót `"mai"`, thừa rác tiêu đề và prefill giả `60p` | [clarification.ts](../../../frontend/src/features/planner/clarification.ts#L49-L218), [TaskClarificationFields.tsx](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L50-L132) |
| [F1-FIX-13](#f1-fix-13-p1-fe--cả-2-ô-nhập-lệnh-trợ-lý-ai--planner-thiếu-giới-hạn-8000-ký-tự-cf-08) | **P1** | `[FE]` | Cả `ChatComposer` lẫn `PlannerCommandComposer` thiếu `maxLength={8000}` và validate độ dài trước submit | [ChatComposer.tsx](../../../frontend/src/features/assistant/ChatComposer.tsx#L131-L151), [PlannerCommandComposer.tsx](../../../frontend/src/features/planner/PlannerCommandComposer.tsx#L172-L189) |
| [F1-FIX-14](#f1-fix-14-p1-be--fe--độ-trễ-chat-p95-vượt-ngưỡng-6-giây-f1-e14-01--sendmessage-tự-retry-bắn-2-request-llm-cf-05) | **P1** | `[BE + FE]` | `DeepSeekExtractor` không giới hạn `max_tokens`/reasoning khiến `deepseek-flash` P95 `6,45s–10,66s`; `sendMessage` thiếu `retry: false` bắn 2 request LLM | [extractor.py](../../../backend/app/nlu/extractor.py#L100-L112), [endpoints.ts](../../../frontend/src/api/endpoints.ts#L404-L498), [client.ts](../../../frontend/src/api/client.ts#L151-L164) |
| [F1-FIX-15](#f1-fix-15-p1-fe--lỗi-mất-mạng-offline-báo-nhầm-lỗi-máy-chủ-xóa-ô-nhập--lặp-request-lỗi-cf-09) | **P1** | `[FE]` | Lỗi mạng `fetch` throw bị gộp vào `SERVICE_UNAVAILABLE`, vẫn retry khi offline, xóa trắng input và không có nút `"Gửi lại"` giữ `idempotencyKey` | [client.ts](../../../frontend/src/api/client.ts#L66-L210), [Assistant.tsx](../../../frontend/src/features/assistant/Assistant.tsx#L718-L752), [conversationHistory.ts](../../../frontend/src/features/assistant/conversationHistory.ts#L103-L122), [endpoints.ts](../../../frontend/src/api/endpoints.ts#L463-L477) |
| [F1-FIX-16](#f1-fix-16-p1-fe--bedb--ba-lỗi-hiển-thị--điều-hướng-lịch-cal-02-cal-03-cal-06) | **P1** | `[FE + BE/DB]` | Chuyển `Tháng` → `Tuần` nhảy lùi tháng trước (`CAL-02`); badge & legend đếm block thay vì công việc (`CAL-03`); hardcode 1 màu mặc định `#596CF0` (`CAL-06`) | [Planner.tsx](../../../frontend/src/pages/Planner.tsx#L443-L671), [workflow_shared.py](../../../backend/app/orchestrator/workflow_shared.py#L11), [clarification.ts](../../../frontend/src/features/planner/clarification.ts#L192) |
| [F1-FIX-17](#f1-fix-17-p1-fe--vỡ-layout-planner-ở-màn-hình-1366820-và-khi-mở-taskpanel-qa-ui-01-kent-qa-011) | **P1** | `[FE]` | Container query `max-width: 1050px` không kích hoạt ở `1366×820` khi mở `TaskPanel`, ép hẹp `.planner-command` và để lịch Tháng che nút `"Tuần"` | [layout.css](../../../frontend/src/styles/layout.css#L193), [planner.css](../../../frontend/src/styles/planner.css#L55-L1147) |
| [F1-FIX-18](#f1-fix-18-p1-fe--nhãn-khung-giờ-rảnh-trên-lịch-tuần-bị-hiển-thị-theo-mốc-đã-cắt-0800-thay-vì-giờ-thật-qa-ui-02-kent-qa-006) | **P1** | `[FE]` | `WeekCalendar` dùng giờ đã clip theo khung hiển thị (`08:00`) để render cả nhãn chữ thay vì giờ thật lưu trong DB (`06:00`/`07:00`) | [workingTime.ts](../../../frontend/src/features/planner/workingTime.ts#L81-L99), [WeekCalendar.tsx](../../../frontend/src/features/planner/WeekCalendar.tsx#L128-L171) |
| [F1-FIX-19](#f1-fix-19-p2-fe--tùy-chỉnh-lưu-hiển-thị-khung-giờ-lịch-tự-reset-về-08001800-khi-chuyển-trang) | **P2** | `[FE]` | `displayRanges` chỉ nằm trong `useState` cục bộ nên mất ngay khi `Planner` unmount lúc chuyển trang | [Planner.tsx](../../../frontend/src/pages/Planner.tsx#L217-L219), [App.tsx](../../../frontend/src/App.tsx#L780) |
| [F1-FIX-20](#f1-fix-20-p2-fe--be--hiển-thị-mã-lỗi-và-thông-báo-tiếng-anh-thô-trên-giao-diện-đề-xuất-lịch-qa-ui-05) | **P2** | `[FE + BE]` | `ProposalReview` render thô `reason_codes` (`INSUFFICIENT_CAPACITY`) và `warning.message` tiếng Anh (`The greedy baseline...`) từ engine | [ProposalReview.tsx](../../../frontend/src/features/planner/ProposalReview.tsx#L130-L153), [engine.py](../../../backend/app/f1/scheduler/engine.py#L365-L374) |
| [F1-FIX-21](#f1-fix-21-p2-fe--nhãn-chờ-xác-nhận-và-đã-xác-nhận-và-lưu-vào-tài-khoản-xuất-hiện-mâu-thuẫn-cùng-lúc-trên-thẻ-chat-kent-qa-005) | **P2** | `[FE]` | Badge đầu thẻ kiểm tra `entry.proposal?.reference` (luôn còn sau duyệt) thay vì `entry.proposal?.status` | [ChatTranscript.tsx](../../../frontend/src/features/assistant/ChatTranscript.tsx#L94-L108) |

> **Phụ lục riêng cho người bảo trì script QA:** [F1-FIX-22](#phụ-lục-1--lỗi--bất-đồng-bộ-trong-script-auto-qa-f1-fix-22) (`P2`, `[QA Script]` — [run_f1_ui_qa.mjs](./run_f1_ui_qa.mjs), [run_f1_auto_qa.py](./run_f1_auto_qa.py)).

---

## 3. Chi tiết Lỗi theo Nhóm

### Nhóm A — Scheduler, Planning & Quy tắc Thời gian (`F1-FIX-01` → `F1-FIX-04`)

#### F1-FIX-01 (P0) `[BE + FE]` — Lỗi HTTP 422 `Horizon start_at and end_at must be minute-aligned` khi lập lịch qua Chat / Action

- **Gộp mã QA:** `F1-E01-01` (lượt 3), `F1-E01-02`, `QA-0422`, `V2-05`, `F1-E01-01-WEB`, `KENT-QA-001`.
- **Các trường hợp con (Sub-cases):**
  - `F1-E01-01` (File 1, 3, 4, 6): Gửi `"Hãy lập lịch học cho tuần này."` → Thực tế: HTTP `422 INVALID_PARAMETER`, `state="ERROR"`, thông báo `"Dữ liệu giờ rảnh/bận không hợp lệ: Horizon start_at and end_at must be minute-aligned"`. Kỳ vọng: Sinh bản đề xuất kế hoạch `AWAITING_APPROVAL`.
  - `F1-E01-02` (File 1, 3, 4, 6): Gửi `"Hãy lập lịch học cho tuần này giúp tôi."` → Thực tế: Nổ cùng lỗi HTTP `422` chặn ngay trước khi tới bước chia block `CF-01`. Kỳ vọng: Sinh kế hoạch học hợp lệ.
  - `V2-05` / `QA-0422` (File 1, File 2 ảnh `v2-05-chat-422-cau1.jpg`, `v2-05-chat-422-cau2.jpg`): Gửi `"xếp lịch học tuần này giúp t với"` và `"Lập lịch học cho các công việc chưa xếp trong tuần này"` → Thực tế: 3/3 lượt lỗi HTTP `422`, UI hiển thị `"Dữ liệu chưa hợp lệ."`. Kỳ vọng: Sinh bản đề xuất lịch để người dùng xác nhận.
  - `F1-E01-01-WEB` (File 6 Hình 1, File 7 Hình 10) & `KENT-QA-001` (File 5): Nổ cùng lỗi `422` khi yêu cầu lập lịch tuần này qua Web/Chat.
  - *Ghi chú vì sao File 8 (`--mode embedded`) PASS:* [run_f1_auto_qa.py:1521](./run_f1_auto_qa.py#L1521) và [run_f1_auto_qa.py:1647-1650](./run_f1_auto_qa.py#L1647-L1650) ép `now_vn = datetime.now(VN_TZ).replace(second=0, microsecond=0)` làm `clock()`, vô tình che khuất lỗi; môi trường chạy thật (`live`) dùng đồng hồ có giây/microsecond nên nổ 100%.
- **Trace IDs (`X-Request-ID`):** `4e4ad0fb-2aac-4c0a-97b9-19887b2013d1`, `7103b5b3-4ee0-44d4-ac3d-a65ef4022098`, `c0ba3c14-2c72-435f-8499-c67ef6330e43`, `62c42ea4-b86d-435f-8e62-dda31815d2e7`, `5778bdfc-f4d0-446b-90b1-9994fdc99461`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/main.py:27](../../../backend/app/main.py#L27): `clock = clock or (lambda: datetime.now(timezone.utc))` giữ nguyên `second`/`microsecond` khác `0`.
  - [backend/app/nlu/extractor.py:35](../../../backend/app/nlu/extractor.py#L35), [extractor.py:107](../../../backend/app/nlu/extractor.py#L107): truyền `current_time: now.isoformat()` vào LLM kèm prompt yêu cầu `start_at` của `GENERATE_STUDY_PLAN` là `current_time` khi kỳ chứa hiện tại → LLM copy nguyên phần giây lẻ vào `slots["start_at"]` (và đôi khi cả `end_at`).
  - [backend/app/orchestrator/chat.py:267-272](../../../backend/app/orchestrator/chat.py#L267-L272): tính `now` đã tròn phút nhưng khi `slots.get("start_at")` / `slots.get("end_at")` có giá trị thì dùng thẳng giá trị chưa làm tròn từ LLM.
  - [backend/app/f1/scheduler/normalization.py:262-263](../../../backend/app/f1/scheduler/normalization.py#L262-L263) & [backend/app/f1/scheduler/constraints.py:104-105](../../../backend/app/f1/scheduler/constraints.py#L104-L105), [constraints.py:147-162](../../../backend/app/f1/scheduler/constraints.py#L147-L162): yêu cầu bắt buộc `second == 0 and microsecond == 0` cho horizon và các mốc thời gian task.
  - [backend/app/orchestrator/actions.py:96-118](../../../backend/app/orchestrator/actions.py#L96-L118) (`normalize_slots`): chưa làm tròn phút cho `start_at`, `available_from_at`, `deadline_at`; [actions.py:164-167](../../../backend/app/orchestrator/actions.py#L164-L167) còn bọc nhầm lỗi `generation_scope` thành thông báo `"Dữ liệu giờ rảnh/bận không hợp lệ: ..."`.
  - [frontend/src/features/planner/revisionScheduling.ts:78-91](../../../frontend/src/features/planner/revisionScheduling.ts#L78-L91): gửi `end_at` có thể chưa chuẩn hóa tròn phút tới `POST /v1/actions`.
- **Đặc tả sửa lỗi:**
  1. **BE — [chat.py:267-272](../../../backend/app/orchestrator/chat.py#L267-L272)** (`operation_for` cho `GENERATE_STUDY_PLAN`): luôn chuẩn hóa `start_at` và `end_at` về ranh giới phút (`second=0, microsecond=0`); nếu `start_at` có `second > 0` hoặc `microsecond > 0` thì làm tròn lên phút kế tiếp và kẹp `start_at >= ceil_minute(now)` (đảm bảo `end_at > start_at`).
  2. **BE — [actions.py:96-118](../../../backend/app/orchestrator/actions.py#L96-L118)** (`normalize_slots`): chuẩn hóa tròn phút cho `start_at`, `available_from_at`, `deadline_at` trước khi lưu candidate hoặc truyền xuống scheduler.
  3. **BE — [actions.py:164-167](../../../backend/app/orchestrator/actions.py#L164-L167)**: tách thông báo lỗi của `generation_scope` / horizon khỏi `"Dữ liệu giờ rảnh/bận không hợp lệ"` để trả đúng nguyên nhân cho UI và log.
  4. **FE — [revisionScheduling.ts:78-91](../../../frontend/src/features/planner/revisionScheduling.ts#L78-L91)**: đảm bảo `start_at`/`end_at` luôn có `second=0, millisecond=0` trước khi gọi `POST /v1/actions`.

---

#### F1-FIX-02 (P0) `[BE + DB]` — Hạn mặc định không tính thời gian nghỉ (`CF-01`) & LLM/backend chấp nhận `deadline_at <= start_at`

- **Gộp mã QA:** `CF-01`, `F1-E01-02` (`90/120p`), `TAY-01` (ghi chú hạn `+60p`), `F1-E04-01`, `KENT-QA-009`.
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`CF-01` — Task không nêu hạn riêng bị cắt mất block cuối):**
    - Prompt: `"Ngày mai tôi muốn học Toán lúc 8h sáng trong 2 tiếng, ưu tiên cao."` (giờ rảnh `08:00–18:00`, không nêu hạn hoàn thành).
    - Thực tế (File 8 `111830`, File 6 Hình 2, File 7 Hình 6, trace `1087eef9-bc30-4689-8f66-d0d76ff7c1e5`): hệ thống tự gán `deadline_at = start_at + 120m = 10:00`. Do chính sách mặc định `max_block_minutes = 90`, `break_minutes = 10`, `min_block_minutes = 25` (`allow_short_final_block = True`), block 1 chiếm `08:00–09:30`, nghỉ `09:30–09:40`, chỉ còn `20p` (`09:40–10:00`) trước `deadline_at` — nhỏ hơn `min_block_minutes = 25` và không thỏa điều kiện block cuối ngắn (`remaining = 30p > 20p`) → rớt `30p` cuối (`unscheduled_minutes: 30`, `reason_codes: ['BLOCK_TOO_SHORT']`), chỉ xếp được `90/120p`. Tương tự `TAY-01` (File 1): task `60p` không nêu hạn bị gán cứng hạn = `start_at + 60m` (`09:00`).
    - Kỳ vọng: xếp đủ `120/120p` (ví dụ `08:00–09:30` và `09:40–10:10`), hoặc hỏi hạn chót / gán hạn hợp lý (tính đủ thời gian nghỉ hoặc cuối ngày).
  - **Sub-case B (`deadline_at == start_at` — Cửa sổ thời gian 0 phút):**
    - `F1-E04-01` (File 4 `deepseek-chat`, 0/3 FAIL): `"ngay mai hoc Vat Ly luc 14h trong 90 phut uu tien cao"` → tạo task có `start_at == deadline_at == 2026-11-26T14:00:00+07:00`.
    - `KENT-QA-009` (File 5): 4 task bị `deadline_at == start_at`: `ôn Giải tích` (`E01-01`), `lm bt toan` (`E04-02`, trace `ac150458-5b29-4fbd-a1e6-76436795e1a0`), `Giải đề thi thử 90p môn Toán` (`E04-06`), `Học Anh` (`E04-07-D`).
    - Kỳ vọng: Không bao giờ tạo hoặc lưu task có `deadline_at <= start_at` (hoặc `deadline_at - start_at < estimated_minutes`).
- **Trace IDs (`X-Request-ID`):** `1087eef9-bc30-4689-8f66-d0d76ff7c1e5`, `ac150458-5b29-4fbd-a1e6-76436795e1a0`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/orchestrator/actions.py:107-118](../../../backend/app/orchestrator/actions.py#L107-L118) & [backend/app/orchestrator/workflow_shared.py:56-66](../../../backend/app/orchestrator/workflow_shared.py#L56-L66) (`end_instant_from_start`): gán mặc định `deadline_at = start_at + estimated_minutes` mà không cộng `break_minutes` giữa các block khi `estimated_minutes > max_block_minutes` (chính sách mặc định `DEFAULT_POLICY` tại [generate.py:24](../../../backend/app/f1/planning/generate.py#L24) & [workflow_shared.py:13-14](../../../backend/app/orchestrator/workflow_shared.py#L13-L14); giới hạn cửa sổ theo `task.deadline_at` tại [engine.py:159](../../../backend/app/f1/scheduler/engine.py#L159) và chia block/kiểm tra `min_block_minutes` tại [engine.py:202-214](../../../backend/app/f1/scheduler/engine.py#L202-L214)).
  - [supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql:128](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L128), [:134](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L134): fallback `v_deadline` dùng `v_start_at + (v_minutes * interval '1 minute')` và chỉ chặn `v_start_at > v_deadline` (dấu `>` bỏ lọt trường hợp `==`, cho phép cửa sổ `0` phút lưu thẳng vào DB).
- **Đặc tả sửa lỗi:**
  1. **BE & DB — Công thức hạn mặc định:** Cập nhật đồng thời [workflow_shared.py:56-66](../../../backend/app/orchestrator/workflow_shared.py#L56-L66) ([actions.py:107-118](../../../backend/app/orchestrator/actions.py#L107-L118)) và tạo migration mới cập nhật `confirm_task` (dựa trên [202611140001_...sql:128](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L128)): khi người dùng không nêu deadline rõ ràng, tính tối thiểu `estimated_minutes + ceil(estimated_minutes / max_block_minutes - 1) * break_minutes` (hoặc áp dụng phương án chốt từ PO/Lead bên dưới).
  2. **BE — Chuẩn hóa đầu ra LLM ([actions.py:96-118](../../../backend/app/orchestrator/actions.py#L96-L118), `normalize_slots`):** Nếu LLM tự điền `deadline_at <= start_at` (hoặc không có biểu thức deadline trong `raw_expressions` mà model trả `deadline_at == start_at`), xóa giá trị sai của model để áp dụng công thức mặc định hợp lệ hoặc yêu cầu làm rõ.
  3. **BE & DB — Siết điều kiện chặn ([202611140001_...sql:134](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L134) & validation tạo nháp):** Đổi `v_start_at > v_deadline` thành `v_deadline <= v_start_at` và kiểm tra tối thiểu `v_deadline - v_start_at >= estimated_minutes`.
- > **Cần Product/Lead chốt nhanh trước khi code:** Khi người dùng chỉ nói giờ bắt đầu + thời lượng mà không nói hạn hoàn thành, chọn quy tắc nào: **(a)** tự động cộng thêm đủ `break_minutes` giữa các block, **(b)** mặc định cuối ngày `23:59`, hay **(c)** bắt buộc hỏi thêm `deadline` trong `questions()`?

---

#### F1-FIX-03 (P0) `[BE + FE]` — Lỗi lập lại lịch `CF-02`: `retained block is outside current availability` (HTTP 422)

- **Gộp mã QA:** `CF-02`, `F1-E02-02` (FAIL trên mọi báo cáo Auto-QA: File 1, 3, 4, 6, 8), `V2-03` (File 1, File 2 ảnh `rc-v2-03-422-cf02`).
- **Các trường hợp con (Sub-cases):**
  - `F1-E02-02` (Auto-QA API): Đã duyệt 1 kế hoạch có block ở ngày mai, sau đó lập lại lịch với phạm vi `"tuần tới"` (không bao phủ ngày mai) → Thực tế: HTTP `422 INVALID_PARAMETER`, `message = "retained block is outside current availability"`. Kỳ vọng: Giữ nguyên block tương lai ngoài phạm vi và xếp lịch mới cho phạm vi `"tuần tới"`.
  - `V2-03` (Web Planner): Sau khi đã duyệt block cho task trước, bấm `"Tìm giờ học"` cho task mới có phạm vi khác → Thực tế: Server trả HTTP `422` cùng lỗi, nhưng UI (`TaskPanel`) chỉ hiện câu cứng `"Chưa tìm được khung giờ phù hợp"` che mất lỗi thật. Kỳ vọng: Lập lịch thành công; nếu có lỗi từ API phải hiển thị đúng thông báo lỗi từ server.
- **Trace ID (`X-Request-ID`):** `45d938d0-d46a-4895-b02c-6acc3ce51d1b`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [supabase/migrations/202611050018_f1_wp2c1_plan_reads.sql:46-83](../../../supabase/migrations/202611050018_f1_wp2c1_plan_reads.sql#L46-L83): RPC `get_scheduling_context` trả về toàn bộ `time_windows` và `base_plan` (không lọc theo scope).
  - [backend/app/f1/scheduler/replanning.py:26-59](../../../backend/app/f1/scheduler/replanning.py#L26-L59) (đặc biệt dòng [:55](../../../backend/app/f1/scheduler/replanning.py#L55)): giữ lại (`retained_blocks`) tất cả block tương lai nằm ngoài `generation_scope`.
  - [backend/app/f1/planning/generate.py:102-116](../../../backend/app/f1/planning/generate.py#L102-L116) (dòng [:103-104](../../../backend/app/f1/planning/generate.py#L103-L104)): gọi `normalize_time_windows` **cắt** `available_intervals` và `busy_intervals` chỉ trong phạm vi `generation_scope` `[scope.start_at, scope.end_at]`.
  - [backend/app/f1/scheduler/constraints.py:250-260](../../../backend/app/f1/scheduler/constraints.py#L250-L260) (dòng [:259-260](../../../backend/app/f1/scheduler/constraints.py#L259-L260)): kiểm tra mọi `retained_blocks` (gồm cả các block nằm ngoài `generation_scope`) phải nằm trong `available_intervals` vừa bị cắt → chắc chắn fail HTTP `422`.
  - [frontend/src/features/planner/TaskPanel.tsx:231-232](../../../frontend/src/features/planner/TaskPanel.tsx#L231-L232): hardcode chuỗi `"Chưa tìm được khung giờ phù hợp"` thay vì hiển thị thông điệp lỗi cụ thể từ `scheduling.message`.
- **Đặc tả sửa lỗi:**
  1. **BE — [generate.py:102-116](../../../backend/app/f1/planning/generate.py#L102-L116) & [constraints.py:250-260](../../../backend/app/f1/scheduler/constraints.py#L250-L260):** Mở rộng khoảng horizon dùng để chuẩn hóa `available_intervals` / `busy_intervals` bao phủ union của `generation_scope` và `[min(b.start_at), max(b.end_at)]` của toàn bộ `retained_blocks` (trong khi vẫn giữ chặt `generation_scope` để `engine.py` chỉ sinh block mới trong `scope`), **HOẶC** truyền hai tập intervals riêng (full-horizon cho kiểm tra `retained_blocks` tại `constraints.py:259-260` và scope-clipped cho sinh block mới).
  2. **FE — [TaskPanel.tsx:231-232](../../../frontend/src/features/planner/TaskPanel.tsx#L231-L232):** Hiển thị `scheduling.message` (kèm fallback hợp lý) khi API trả lỗi thay vì che bằng chuỗi cứng `"Chưa tìm được khung giờ phù hợp"`.

---

#### F1-FIX-04 (P0) `[BE]` — Ràng buộc cứng `start_at == expected_utc` khiến task không xếp được lịch dù còn giờ rảnh trước hạn (`hcọ Lý`)

- **Gộp mã QA:** `V2-09` & Mục 7(2) (File 1, File 2 ảnh `rc-v2-09-*`).
- **Các trường hợp con (Sub-cases):**
  - Prompt: `"ngày mia 14h hcọ Lý 50 phuts, hạn chủ nhụt"` → tạo task `start_at = 26/11 14:00`, `deadline_at = 29/11`, `estimated_minutes = 50`. Tài khoản có giờ rảnh buổi tối `19:00–22:00` từ `26/11` đến `29/11`.
  - Thực tế: Bấm `"Tìm giờ học"` trả `0` block (`"Chưa xếp được khối học nào"`, reason `INSUFFICIENT_CAPACITY`, hoặc `OUTSIDE_HORIZON` nếu `now > task.start_at`).
  - Kỳ vọng: Nếu người dùng không rảnh lúc `14:00` nhưng rảnh `19:00–22:00` trong khoảng `[start_at, deadline_at]`, hệ thống xếp vào khung rảnh phù hợp hoặc giải thích rõ lý do bằng tiếng Việt `"Giờ bắt đầu dự kiến (14:00) không nằm trong khung giờ rảnh"`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/f1/scheduler/engine.py:129-147](../../../backend/app/f1/scheduler/engine.py#L129-L147) (`_expected_block_start`) & [:171-181](../../../backend/app/f1/scheduler/engine.py#L171-L181) (`_eligible_windows`): khi `task.start_at` khác `None`, scheduler ép block đầu tiên phải khớp **chính xác từng phút** `== expected_utc` (`14:00`), loại sạch mọi khung rảnh `19:00–22:00`.
  - [backend/app/f1/scheduler/constraints.py:452-462](../../../backend/app/f1/scheduler/constraints.py#L452-L462): validator hậu kiểm cũng áp cùng điều kiện `GENERATED_START_MISMATCH` nếu block đầu khác `task.start_at`.
- **Đặc tả sửa lỗi:**
  1. Nếu chọn phương án linh hoạt (`>= task.start_at`): cập nhật `_eligible_windows` ([engine.py:171-181](../../../backend/app/f1/scheduler/engine.py#L171-L181)) và [constraints.py:452-462](../../../backend/app/f1/scheduler/constraints.py#L452-L462) cho phép đặt block trong bất kỳ khoảng rảnh nào `>= max(task.start_at, available_from_at)` và `<= deadline_at`, ưu tiên gần `task.start_at` nhất (chỉ giữ `==` khi có cờ cố định giờ riêng).
  2. Dù chọn phương án linh hoạt hay khóa cứng, bổ sung mã lý do riêng (ví dụ `START_TIME_OUTSIDE_AVAILABILITY`) và ánh xạ sang tiếng Việt rõ ràng để không báo chung chung `INSUFFICIENT_CAPACITY`.
- > **Cần Product/Lead chốt nhanh trước khi code:** `task.start_at` mang ý nghĩa là **"thời điểm sớm nhất có thể bắt đầu"** (`>= start_at`, tương tự `available_from_at`) hay **"khóa cứng đúng phút bắt đầu"** (`== start_at`)?

---

### Nhóm B — Bảo mật Phiên & Trạng thái Hội thoại / Pending (`F1-FIX-05` → `F1-FIX-07`)

#### F1-FIX-05 (P0 — Gate 3 FAIL) `[FE]` — Lộ lịch sử chat & bản nháp giữa 2 tài khoản dùng chung trình duyệt (`QA-SEC-01`)

- **Gộp mã QA:** `QA-SEC-01` (File 1, File 2 ảnh `rc-sec-b-thay-nhap-cua-a.jpg`, `rc-sec-b-bi-server-chan.jpg`, File 3 Gate 3).
- **Các trường hợp con (Sub-cases):**
  - Thao tác: Tài khoản A tạo bản nháp `"mai 7h tối học Sinh 20 phút, hạn thứ 7"` (chưa duyệt) → Đăng xuất A → Đăng nhập Tài khoản B trên cùng trình duyệt (kể cả sau khi F5).
  - Thực tế: Tài khoản B nhìn thấy toàn bộ lịch sử hội thoại và thẻ bản nháp chưa duyệt của A. Khi B bấm `"Xem lại bản nháp"`, backend chặn đúng bằng HTTP `404 ENTITY_NOT_FOUND` (`"Không tìm thấy nội dung này."`), nhưng dữ liệu riêng tư của A đã bị rò rỉ ngay trên UI của B.
  - Kỳ vọng: Đăng xuất hoặc đổi tài khoản phải cô lập hoàn toàn lịch sử chat và bản nháp cục bộ theo `userId`; Tài khoản B không được thấy bất kỳ dữ liệu nào của A.
- **Trace ID (`X-Request-ID`):** `eab17730-2a80-40b9-9345-d3240f164f91`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/assistant/conversationHistory.ts:436-517](../../../frontend/src/features/assistant/conversationHistory.ts#L436-L517): dùng chung một tên IndexedDB cố định toàn trình duyệt (`DB_NAME = "studyflow-assistant-history"`), không gắn `userId` vào tên DB hay khóa phân vùng (trái ngược với [frontend/src/api/pending.ts:11](../../../frontend/src/api/pending.ts#L11), [:34](../../../frontend/src/api/pending.ts#L34) vốn đã tách key theo `userId`).
  - [frontend/src/features/assistant/useConversationHistory.ts:34-106](../../../frontend/src/features/assistant/useConversationHistory.ts#L34-L106): không nhận `userId` làm dependency để reset state in-memory, đóng kết nối DB cũ và tải lại DB riêng của user mới khi phiên đăng nhập thay đổi.
- **Đặc tả sửa lỗi:**
  1. **FE — [conversationHistory.ts:436-517](../../../frontend/src/features/assistant/conversationHistory.ts#L436-L517):** Đổi tên IndexedDB theo phiên người dùng: `studyflow-assistant-history-${userId}` (và `studyflow-assistant-history-demo` khi ở Demo mode). Xóa/không đọc lại DB legacy `studyflow-assistant-history` không có `userId` để tránh lộ dữ liệu cũ.
  2. **FE — [useConversationHistory.ts:34-106](../../../frontend/src/features/assistant/useConversationHistory.ts#L34-L106):** Truyền `userId` vào hook và đưa vào dependency array của `useEffect`; khi `userId` thay đổi hoặc trở về `null` (đăng xuất), lập tức xóa state hội thoại/draft trong RAM, đóng handle DB cũ và mở đúng DB của `userId` mới.
  3. **FE — Rà soát lưu trữ cục bộ:** Xác minh toàn bộ khóa `localStorage` / `sessionStorage` liên quan đến Planner/Assistant đều có tiền tố theo `userId` hoặc được dọn sạch khi đăng xuất.
- > **Cần Product/Lead chốt nhanh trước khi code:** Khi người dùng bấm **Đăng xuất** trên trình duyệt dùng chung, muốn **(a)** giữ nguyên DB cục bộ đã tách theo `userId` (để cùng user đăng nhập lại vẫn thấy lịch sử chat local) hay **(b)** xóa sạch luôn IndexedDB của user vừa đăng xuất để đảm bảo an toàn tuyệt đối trên máy công cộng?

---

#### F1-FIX-06 (P0 — Gate 4 FAIL) `[BE + DB + FE]` — Kẹt cứng hội thoại `409 ACTION_REVIEW_REQUIRED` khi làm rõ, hủy popup Planner hoặc F5 giữa chừng (`CF-04`)

- **Gộp mã QA:** `CF-04`, `F1-B03`, `F1-E08-03`, `KENT-QA-003`, `PLANNER-CANCEL`, `TAY-03`, `V3-04`, `F1-E11-02`.
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`F1-E08-03` — API `NEEDS_CLARIFICATION` không thể hủy):**
    - Lượt 1: `"Thêm bài tập Giải tích"` → Thực tế: HTTP `200`, `state = "NEEDS_CLARIFICATION"`, nhưng **`action_reference: null`** (trên `main`).
    - Lượt 2: `"Hủy bản nháp này đi"` → Thực tế: HTTP `409 ACTION_REVIEW_REQUIRED`, không thể hủy qua Chat mà cũng không có `action_reference` để gọi `/v1/decisions` (`REJECT`). Kỳ vọng: Có `action_reference` hoặc cho phép hủy thoát khỏi trạng thái `AWAITING_CLARIFICATION`.
  - **Sub-case B (`KENT-QA-003` & `PLANNER-CANCEL` — Đóng popup làm rõ trên Planner gây kẹt 409 hoặc ghép nhầm ngữ cảnh cũ):**
    - `KENT-QA-003` (File 5): Đóng popup làm rõ bằng nút `X`, sau đó gõ `"Tìm công việc"` hoặc `"Hủy thao tác đang chờ."` → Thực tế: HTTP `409 ACTION_REVIEW_REQUIRED` (`action_reference: null`).
    - `PLANNER-CANCEL` (File 7 Hình 9): Mở popup làm rõ của câu trước (đang giữ `120p 20:00`), bấm hủy/đóng popup rồi gõ câu mới `"tạo cv ôn bai đi"` → Thực tế: Backend ghép slot cũ vào câu mới thành `cv ôn bai` `120p lúc 20:00`. Kỳ vọng: Đóng/hủy popup phải đóng hẳn pending action trên server, không giữ lại slot cũ.
  - **Sub-case C (`V3-04`, `TAY-03`, `F1-E11-02` — F5 khi đang chờ server trả lời làm mất thẻ duyệt & kẹt 409):**
    - Mạng thường (`V3-04`, File 1 & File 2 ảnh `rc-cf04-chat.jpg`): Gửi `"mai 21h học Anh 30 phút, hạn thứ 7"`, bấm F5 sau ~0.5s → DB đã tạo `pending_action`, nhưng trình duyệt mất thẻ và mất 2 nút `Xác nhận`/`Hủy`; gửi tin nhắn tiếp theo bị HTTP `409 ACTION_REVIEW_REQUIRED`.
    - Mạng 3G (`TAY-03` File 1 & File 2 ảnh `tay-test3-f5-409.png`: `"mai 16h học địa 30 phút, hạn thứ 7"`; `F1-E11-02` File 6 Hình 3 & File 7 Hình 11: `"Ngày mai 15h ôn Sinh trong 45 phút"`): cùng triệu chứng mất thẻ sau F5 và kẹt `409`.
    - Kỳ vọng: Sau khi F5 (hoặc khi nhận `409`), FE tự khôi phục đúng thẻ `Xác nhận`/`Hủy` hoặc form làm rõ đang chờ trên server.
- **Trace IDs (`X-Request-ID`):** `46fcaf8e-...`, `690933a5-...`, `47edcfcc-...`, `f542d5f6-9ae0-4718-a910-2e2a071acb58`, `03d523fe-0eb3-4784-bf33-d4c9b7d62431`, `988c8939-d1a7-4367-a322-d06dfb368766`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/orchestrator/chat.py:315](../../../backend/app/orchestrator/chat.py#L315), [:342-349](../../../backend/app/orchestrator/chat.py#L342-L349) và [backend/app/orchestrator/actions.py:278-279](../../../backend/app/orchestrator/actions.py#L278-L279) (`candidate_review_reply`): trả `NEEDS_CLARIFICATION` với `action_reference=None`, mặc dù DB RPC `cancel_pending_action` tại [supabase/migrations/202611050015_f1_wp2b3_actions_confirm_search.sql:379-380](../../../supabase/migrations/202611050015_f1_wp2b3_actions_confirm_search.sql#L379-L380) **đã hỗ trợ sẵn** hủy trạng thái `AWAITING_CLARIFICATION` qua `/v1/decisions` (`REJECT`).
  - [backend/app/orchestrator/chat.py:291-293](../../../backend/app/orchestrator/chat.py#L291-L293): khi đang có pending action và người dùng gõ `"Hủy..."`, luồng ném `409 ACTION_REVIEW_REQUIRED`; ở dòng [:296](../../../backend/app/orchestrator/chat.py#L296) ghép `{**candidate["slots"], **patch}` khi `AWAITING_CLARIFICATION` chưa được đóng trên server.
  - [frontend/src/features/planner/usePlanner.ts:452-454](../../../frontend/src/features/planner/usePlanner.ts#L452-L454) (`dismissClarification`): chỉ chạy `setClarification(null)` ở local state, không gọi `POST /v1/decisions` (`REJECT`) nên pending action vẫn sống trên server.
  - [frontend/src/features/assistant/AssistantTaskClarificationForm.tsx:95-99](../../../frontend/src/features/assistant/AssistantTaskClarificationForm.tsx#L95-L99): chỉ có nút submit `Tiếp tục` / `Xem bản nháp`, thiếu nút `Hủy` gọi `REJECT`.
  - [backend/app/api/v1/routes.py:359-375](../../../backend/app/api/v1/routes.py#L359-L375) & [usePlanner.ts:176-181](../../../frontend/src/features/planner/usePlanner.ts#L176-L181), [Assistant.tsx:718-748](../../../frontend/src/features/assistant/Assistant.tsx#L718-L748), [App.tsx:404-444](../../../frontend/src/App.tsx#L404-L444): chưa có endpoint đọc trạng thái pending đang mở từ server theo `conversation_id`, nên nếu F5 trước khi response về tới `pending.ts` thì FE mất hoàn toàn `action_reference` và không thể phục hồi thẻ.
- **Đặc tả sửa lỗi:**
  1. **BE — Luôn trả `action_reference` khi `NEEDS_CLARIFICATION`:** Truyền `reference` vào `reply(...)` tại [chat.py:315](../../../backend/app/orchestrator/chat.py#L315), [chat.py:348-349](../../../backend/app/orchestrator/chat.py#L348-L349) và [actions.py:278-279](../../../backend/app/orchestrator/actions.py#L278-L279). *(Cập nhật contract schema nếu cần và phối hợp đồng bộ với Phụ lục `F1-FIX-22` về điều kiện kiểm tra `state == "AWAITING_APPROVAL"` trong script QA.)*
  2. **BE — Hỗ trợ thoát/hủy khi đang `AWAITING_CLARIFICATION`:** Nhận diện ý định hủy trong `AWAITING_CLARIFICATION` (hoặc trả kèm `action_reference` rõ ràng để FE gọi `/v1/decisions` `REJECT`) nhằm không khóa chết hội thoại.
  3. **BE & Contract — Thêm API khôi phục pending theo hội thoại:** Bổ sung endpoint mới (ví dụ `GET /v1/conversations/{conversation_id}/pending` trong [routes.py:359-375](../../../backend/app/api/v1/routes.py#L359-L375) và cập nhật `contracts/`) gọi `app_api.get_workflow_context` với `action_id = None` trả về `active_action` (nếu có) gồm `action_reference`, `state`, `candidate`/`proposal`/`presentation`.
  4. **FE — Đóng popup phải hủy trên server:** Lưu `action_reference` vào state `clarification`; khi người dùng bấm `X` / `Esc` / nút `Hủy` tại [usePlanner.ts:452-454](../../../frontend/src/features/planner/usePlanner.ts#L452-L454) và bổ sung nút `Hủy` cạnh nút submit tại [AssistantTaskClarificationForm.tsx:95-99](../../../frontend/src/features/assistant/AssistantTaskClarificationForm.tsx#L95-L99), gọi `api.decide(conversationId, reference, "REJECT")` trước khi đóng form để giải phóng `pending_actions` và `workflow_continuations`.
  5. **FE — Tự khôi phục sau F5 hoặc khi gặp `409 ACTION_REVIEW_REQUIRED`:** Khi `Planner` / `Assistant` mount (hoặc khi `sendMessage` nhận `409 ACTION_REVIEW_REQUIRED`), tự gọi endpoint đọc pending + `reviewAction` để dựng lại đúng thẻ `Xác nhận / Hủy` hoặc form làm rõ đang treo trên server.

---

#### F1-FIX-07 (P1) `[FE]` — Tab bị từ chối đồng thời (`409 STALE_ENTITY_VERSION`) vẫn giữ nút `Xác nhận` / `Hủy`

- **Gộp mã QA:** `V3-03` & Mục 7(3) (File 1, File 2 ảnh `v3-03-tab-bi-tu-choi`).
- **Các trường hợp con (Sub-cases):**
  - Thao tác: Mở cùng 1 tài khoản trên 2 tab, tạo bản nháp `"t7 tuần sau lúc 9h học Vật lý 45 phút, hạn chủ nhật tuần sau"`. Tab 1 bấm `Xác nhận` → HTTP `200`. Tab 2 bấm `Xác nhận` → server trả HTTP `409 STALE_ENTITY_VERSION` (`"Nội dung đã thay đổi. Hãy tải lại rồi thử lại."`).
  - Thực tế: Tab 2 hiển thị thông báo lỗi nhưng vẫn giữ nguyên 2 nút `Xác nhận` và `Hủy` cho phép bấm tiếp.
  - Kỳ vọng: Vô hiệu hóa/ẩn ngay 2 nút `Xác nhận`/`Hủy`, chuyển trạng thái thẻ sang đã đóng/hết hiệu lực và tự làm mới dữ liệu nền.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/planner/usePlanner.ts:404-406](../../../frontend/src/features/planner/usePlanner.ts#L404-L406): nhánh `catch` của `api.decide` không đóng `proposal` và không xóa `pending` khi gặp lỗi stale / `409` / `404`.
  - [frontend/src/features/assistant/Assistant.tsx:822-823](../../../frontend/src/features/assistant/Assistant.tsx#L822-L823): nhánh `catch` của `decide` giữ nguyên `proposal.status = "awaiting_approval"` nên 2 nút thao tác vẫn render.
- **Đặc tả sửa lỗi:**
  1. Khi `api.decide` ném `ApiError` thuộc nhóm kết thúc/hết hiệu lực (`STALE_ENTITY_VERSION`, `STALE_PROPOSAL`, `STALE_PLAN_VERSION`, `ENTITY_NOT_FOUND`, hoặc HTTP `404`/`409`):
     - Tại [usePlanner.ts:404-406](../../../frontend/src/features/planner/usePlanner.ts#L404-L406): gọi `setProposal(null)`, `savePending(userId, null)`, `await reload()`, đồng thời giữ banner thông báo lỗi cho người dùng.
     - Tại [Assistant.tsx:822-823](../../../frontend/src/features/assistant/Assistant.tsx#L822-L823): cập nhật `proposal.status` sang `"cancelled"` (hoặc trạng thái mới `"expired"`/`"stale"` hiển thị `"Đã hết hiệu lực"`) để ẩn ngay 2 nút `Xác nhận`/`Hủy`.

---

### Nhóm C — Validation, NLU Tiếng Việt & Phản hồi Trợ lý (`F1-FIX-08` → `F1-FIX-11`)

#### F1-FIX-08 (P1) `[BE + Contract/DB + FE]` — Thiếu validate sớm dữ liệu công việc (`start_at > deadline_at`, `estimated_minutes` cực đoan/`<= 0`)

- **Gộp mã QA:** `CF-07`, `F1-E06-03` (FAIL trên mọi báo cáo Auto-QA), `KENT-QA-012`, `KENT-QA-013`, `KENT-QA-014`.
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`F1-E06-03`, `KENT-QA-012` — `start_at > deadline_at`):**
    - Prompt: `"Học Toán ngày mai lúc 20h tối trong 60 phút, hạn chót nộp là 10h sáng mai"`.
    - Thực tế: `POST /v1/messages` vẫn trả HTTP `200 AWAITING_APPROVAL` cho tạo thẻ duyệt; chỉ đến khi bấm `Xác nhận` mới nổ HTTP `422 INVALID_PARAMETER` (`"start_at is after the deadline."`).
    - Kỳ vọng: Chặn ngay ở bước tạo nháp (`POST /v1/messages` và `POST /v1/actions`) với thông báo tiếng Việt rõ ràng `"Thời gian bắt đầu không được sau hạn hoàn thành."`, không tạo thẻ `AWAITING_APPROVAL`.
  - **Sub-case B (`KENT-QA-013` — `estimated_minutes` phi thực tế `99999`):**
    - Prompt: `"Học Anh 8h sáng mai trong 99999 phút"` → Thực tế: Vẫn tạo thẻ duyệt với `99999` phút.
    - Kỳ vọng: Giới hạn trần hợp lý (ví dụ `<= 1440` phút hoặc theo ngưỡng chốt trong `contracts/schemas/f1.schema.json`) và trả lỗi tiếng Việt cụ thể.
  - **Sub-case C (`KENT-QA-014` — `estimated_minutes <= 0` báo lỗi chung chung):**
    - Prompts: `"Học Sử 8h sáng mai trong 0 phút"`, `"Học Văn 8h sáng mai trong -5 phút"`.
    - Thực tế: Trả HTTP `422 INVALID_PARAMETER` kèm câu chung `"Mình chưa hiểu thông tin công việc."` (UI hiện `"Dữ liệu chưa hợp lệ."`).
    - Kỳ vọng: Trả thông báo cụ thể đúng trường (`field="estimated_minutes"`): `"Thời lượng dự kiến phải lớn hơn 0 phút."` và hiển thị rõ câu này trên UI.
- **Trace IDs (`X-Request-ID`):** `68dabf19-...`, `4cdeba70-...`, `316263d7-...`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/orchestrator/chat.py:216-223](../../../backend/app/orchestrator/chat.py#L216-L223), [:296-316](../../../backend/app/orchestrator/chat.py#L296-L316) & [backend/app/orchestrator/actions.py:77-81](../../../backend/app/orchestrator/actions.py#L77-L81), [:134-146](../../../backend/app/orchestrator/actions.py#L134-L146): không kiểm tra quan hệ `start_at <= deadline_at` và `available_from_at <= deadline_at` trước khi gọi `create_task_candidate` ([supabase/migrations/202611050014_f1_wp2b2_candidates_idempotency.sql:45-98](../../../supabase/migrations/202611050014_f1_wp2b2_candidates_idempotency.sql#L45-L98)); chỉ đến `confirm_task` mới kiểm tra.
  - [chat.py:217](../../../backend/app/orchestrator/chat.py#L217), [:297](../../../backend/app/orchestrator/chat.py#L297): gọi thẳng `contract.is_valid("CandidateTaskFields", ...)` khiến mọi vi phạm `estimated_minutes <= 0` đều rơi vào thông điệp chung `"Mình chưa hiểu thông tin công việc."`.
  - [contracts/schemas/f1.schema.json:337-348](../../../contracts/schemas/f1.schema.json#L337-L348): đặt `"maximum": 9007199254740991` quá rộng nên lọt `99999` phút.
  - [frontend/src/api/client.ts:179](../../../frontend/src/api/client.ts#L179), [:207-210](../../../frontend/src/api/client.ts#L207-L210): `errorText()` tra `MESSAGES[error.code]` trước `error.message`, nên mọi lỗi `INVALID_PARAMETER` đều bị ghi đè thành chuỗi cứng `"Dữ liệu chưa hợp lệ."` kể cả khi backend trả thông điệp tiếng Việt cụ thể.
- **Đặc tả sửa lỗi:**
  1. **BE & DB — Hàm validate nghiệp vụ dùng chung:** Áp dụng tại `chat.py:write`, `chat.py:answer_open_queue`, `actions.py:prepare` (và bổ sung guard tại `create_task_candidate` nếu cần):
     - Kiểm tra riêng `estimated_minutes <= 0` trước schema check → trả lỗi `INVALID_PARAMETER`, `field="estimated_minutes"`, `"Thời lượng dự kiến phải lớn hơn 0 phút."`.
     - Kiểm tra `start_at >= deadline_at` hoặc `available_from_at > deadline_at` → trả lỗi `INVALID_PARAMETER`, `"Thời gian bắt đầu phải trước hạn hoàn thành."`, không tạo `pending_action` / `AWAITING_APPROVAL`.
  2. **Contract & DB Schema — [f1.schema.json:337-348](../../../contracts/schemas/f1.schema.json#L337-L348):** Đặt giới hạn `maximum` hợp lý cho `estimated_minutes`, đồng bộ migration sinh từ contract và backend kèm thông báo lỗi tiếng Việt nêu rõ giới hạn tối đa.
  3. **FE — [frontend/src/api/client.ts:179](../../../frontend/src/api/client.ts#L179), [:207-210](../../../frontend/src/api/client.ts#L207-L210):** Trong `errorText()`, ưu tiên hiển thị `error.message` tiếng Việt chi tiết từ backend (khi không phải thông báo kỹ thuật tiếng Anh) thay vì luôn ghi đè bằng `MESSAGES.INVALID_PARAMETER` (`"Dữ liệu chưa hợp lệ."`).

---

#### F1-FIX-09 (P0) `[NLU/Prompt + BE]` — AI trích xuất sai tiếng Việt khẩu ngữ/teencode, rơi intent hoặc trả sai khi hỏi lịch bận (`N03`)

- **Gộp mã QA:** `F1-E04-04`, `KENT-QA-007`, `F1-E04-02`, `KENT-QA-008` (phần server), `F1-E01-01` (Trial 1/3), `F1-E03-01` (File 8), `V2-03` lần 1 (File 2 ảnh `v2-03-gio-ranh-tu-suy.jpg`), `N03` (File 7).
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`F1-E04-04` / `KENT-QA-007` — `"8r tối"` sai phút):**
    - Prompt: `"Học Hóa lúc 8r tối nay trong 1 tiếng rưỡi"` (FAIL ở File 1, 4, 5, 6, 8).
    - Thực tế: Trích xuất `start_at = 20:00` (mất `:30`), dù `"1 tiếng rưỡi"` đúng `90p`. Kỳ vọng: `20:30` và `90p`.
  - **Sub-case B (`F1-E04-02` / `KENT-QA-008` — Teencode thiếu `start_at`):**
    - Prompt: `"lm bt toan mai 9h sang nha, 45p"` (FAIL 3/3 ở File 1, 4, 6, 8; File 5 `KENT-QA-008`).
    - Thực tế: Model bỏ sót `start_at` → trả `NEEDS_CLARIFICATION` hỏi lại `start_at` dù người dùng đã ghi rõ `mai 9h sang`. Kỳ vọng: Trích đúng `start_at = ngày mai 09:00`, `estimated_minutes = 45`.
  - **Sub-case C (`F1-E01-01` Trial 1 & `F1-E03-01` File 8 — Câu đầy đủ vẫn hỏi lại `start_at` / không tạo nháp):**
    - `"Ngày mai tôi muốn ôn Giải tích lúc 9h sáng trong 60 phút, ưu tiên cao."` (File 1 Trial 1/3 → `NEEDS_CLARIFICATION` `q=[{'field':'start_at'}]`).
    - `"Ngày mai 10h sáng học Sinh học trong 45 phút."` (File 8 `F1-E03-01` → HTTP `200` không có `action_reference`).
  - **Sub-case D (`V2-03` lần 1 — Rơi mất intent `CREATE_TASK` khi câu ghép giờ rảnh + task):**
    - Prompt (File 2 ảnh `v2-03-gio-ranh-tu-suy.jpg`): `"mai t rảnh sáng, nhét hộ bài giải tích 2 tiếng tầm 9h nha"` → Thực tế: Chỉ tách ra nháp `SET_AVAILABILITY` (`06:00–12:00`), bỏ rơi luôn bước tạo task `bài giải tích`. Kỳ vọng: Tách đủ cả 2 hành động `SET_AVAILABILITY` và `CREATE_TASK`.
  - **Sub-case E (`N03` — Hỏi khung giờ bận trả nhầm `"Bạn chưa có kế hoạch"`):**
    - Prompt (File 7): `"mai t có bận lúc 8h ko"` (tài khoản đã lưu khung `BUSY` lúc `08:00` ngày mai nhưng chưa có `StudyPlan`).
    - Thực tế: Rơi vào nhánh `GET_STUDY_PLAN` và trả `"Bạn chưa có kế hoạch."`.
    - Kỳ vọng: Đọc kết hợp `list_time_windows` (cả `BUSY` và `AVAILABILITY`) + `get_study_plan` để trả lời chính xác người dùng có lịch bận lúc `08:00` ngày mai hay không.
- **Trace ID (`X-Request-ID`):** `ac150458-...`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/nlu/extractor.py:15-42](../../../backend/app/nlu/extractor.py#L15-L42): `PROMPT` thiếu quy tắc rõ và few-shot cho khẩu ngữ/teencode tiếng Việt (`8r` = `:30`, `1 tiếng rưỡi` = `90`, `10h kém 15` = `09:45`, `lm bt`, `mai 9h sang`, `45p`), thiếu quy tắc bắt buộc trích `start_at` khi có cụm ngày + giờ (`lúc Xh`, `Xh sáng`), và thiếu ví dụ giữ đủ các bước cho câu ghép nhiều hành động (`SET_AVAILABILITY` + `CREATE_TASK`).
  - [backend/app/orchestrator/chat.py:180-181](../../../backend/app/orchestrator/chat.py#L180-L181), [:369-370](../../../backend/app/orchestrator/chat.py#L369-L370): chưa có intent hoặc nhánh đọc tra cứu `list_time_windows` khi người dùng hỏi trạng thái rảnh/bận tại một thời điểm, nên mọi câu hỏi kiểm tra lịch đều bị dồn về `GET_STUDY_PLAN`.
- **Đặc tả sửa lỗi:**
  1. **NLU/Prompt — [extractor.py:15-42](../../../backend/app/nlu/extractor.py#L15-L42):** Cập nhật `PROMPT` bổ sung bảng quy tắc + few-shot chuẩn cho tiếng Việt khẩu ngữ/teencode (`8r tối` → `20:30`, `lm bt toan mai 9h sang nha, 45p` → `start_at` ngày mai `09:00` + `45p`), ràng buộc bắt buộc điền `start_at` khi có giờ cụ thể, và ví dụ tách đủ 2 bước cho câu ghép `SET_AVAILABILITY` + `CREATE_TASK`.
  2. **BE — Chuẩn hóa hậu xử lý xác định (deterministic normalizer):** Bổ sung guard ở backend xử lý các biểu thức giờ Việt hóa từ `raw_expressions` (như `(\d{1,2})r` → `:30`) để không phụ thuộc 100% vào xác suất LLM.
  3. **BE — [chat.py:180-181](../../../backend/app/orchestrator/chat.py#L180-L181), [:369-370](../../../backend/app/orchestrator/chat.py#L369-L370):** Bổ sung nhánh/intent truy vấn lịch rảnh/bận (`CHECK_AVAILABILITY` hoặc mở rộng nhánh đọc lịch) gọi cả `list_time_windows` và `get_study_plan`, trả lời rõ khung `BUSY` / `AVAILABILITY` / `StudyBlock` trùng thời điểm người dùng hỏi.

---

#### F1-FIX-10 (P1) `[BE + FE]` — Không chặn khung giờ rảnh/bận đảo ngược (`start >= end`) trước thẻ duyệt (`N02B`)

- **Gộp mã QA:** `N02B` (File 7).
- **Các trường hợp con (Sub-cases):**
  - Prompt: `"mai t rảnh từ 12h trưa tới 8h sáng cùng ngày"`.
  - Thực tế:
    - Backend vẫn tạo thẻ `AWAITING_APPROVAL` thay vì từ chối.
    - Trên **Trợ lý AI**: thẻ hiển thị bị thiếu giờ nhưng vẫn **bật nút `Xác nhận`**.
    - Trên **Planner**: nút `Xác nhận` bị khóa nhưng thông báo lỗi chưa nêu rõ lý do giờ kết thúc trước giờ bắt đầu.
  - Kỳ vọng: Backend chặn ngay trước khi tạo thẻ duyệt với lỗi rõ ràng `"Giờ kết thúc phải sau giờ bắt đầu."`; Frontend ở cả Planner lẫn Trợ lý AI đều tôn trọng `approvalError` và khóa nút `Xác nhận` khi khoảng giờ không hợp lệ.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/orchestrator/chat.py:252-262](../../../backend/app/orchestrator/chat.py#L252-L262) (`operation_for` cho `SET_AVAILABILITY` / `SET_BUSY_INTERVAL`): không kiểm tra `start_at < end_at` (với `NONE`) và `start_time < end_time` (với `WEEKLY`) trước khi gọi `build_action`.
  - [frontend/src/api/mappers.ts:439](../../../frontend/src/api/mappers.ts#L439), [:450](../../../frontend/src/api/mappers.ts#L450), [:488-511](../../../frontend/src/api/mappers.ts#L488-L511): thông báo `approvalError` khi `startDate >= endDate` chưa đủ rõ nghĩa.
  - [frontend/src/features/assistant/apiAssistant.ts:45-61](../../../frontend/src/features/assistant/apiAssistant.ts#L45-L61), [frontend/src/types/assistant.ts:13-30](../../../frontend/src/types/assistant.ts#L13-L30) & [ChatTranscript.tsx:171-183](../../../frontend/src/features/assistant/ChatTranscript.tsx#L171-L183): `summarize(presentation)` có trả `approvalError` nhưng `apiAssistant.ts:45` chỉ destructure `{ title, details }`, `ActionProposal` chưa có trường `approvalError?: string`, và nút `Xác nhận` tại `ChatTranscript.tsx:176` chỉ khóa theo `disabled={thinking}`.
- **Đặc tả sửa lỗi:**
  1. **BE — [chat.py:252-262](../../../backend/app/orchestrator/chat.py#L252-L262):** Kiểm tra `start_at < end_at` (cho `NONE`) và `start_time < end_time` (cho `WEEKLY`) trước `build_action`; nếu sai thì trả phản hồi lỗi rõ ràng `"Giờ kết thúc phải sau giờ bắt đầu."` và không tạo `AWAITING_APPROVAL`.
  2. **FE — [mappers.ts:439-511](../../../frontend/src/api/mappers.ts#L439-L511):** Chuẩn hóa câu `approvalError` thành `"Giờ kết thúc phải sau giờ bắt đầu."`.
  3. **FE — [types/assistant.ts:13-30](../../../frontend/src/types/assistant.ts#L13-L30), [apiAssistant.ts:45-61](../../../frontend/src/features/assistant/apiAssistant.ts#L45-L61) & [ChatTranscript.tsx:171-183](../../../frontend/src/features/assistant/ChatTranscript.tsx#L171-L183):** Bổ sung `approvalError?: string` vào `ActionProposal`, truyền từ `summarize(presentation)` qua `apiAssistant.ts`, hiển thị cảnh báo và vô hiệu hóa nút `Xác nhận` (`disabled={thinking || Boolean(entry.proposal.approvalError)}`) giống bên Planner.

---

#### F1-FIX-11 (P2) `[BE]` — `compose()` lặp câu xác nhận 5 lần & ghép câu lỗi bước trước vào thẻ bước sau

- **Gộp mã QA:** `QA-UI-03`, `KENT-QA-004`, `QA-UI-04` (File 1, File 2 ảnh `rc-v2-01-cau-lap`, `rc-v2-03-chat.jpg`, File 5).
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`QA-UI-03`, `KENT-QA-004`):** Sau khi duyệt liên tiếp 5 khung giờ rảnh (ví dụ dải Thứ 2–Thứ 6), phản hồi hiển thị lặp 5 lần y hệt nhau: `"Đã cập nhật giờ rảnh. Đã cập nhật giờ rảnh. Đã cập nhật giờ rảnh. Đã cập nhật giờ rảnh. Đã cập nhật giờ rảnh."`.
  - **Sub-case B (`QA-UI-04`, File 2 ảnh `rc-v2-03-chat.jpg`):** Gửi `"mai t rảnh sáng, nhét hộ bài giải tích 2 tiếng tầm 9h nha"`, step 0 thất bại còn step 1 tạo thẻ hợp lệ → phản hồi ghép nguyên văn: `"Mình chưa hiểu yêu cầu này, bạn thử dùng biểu mẫu nhé. Xem nội dung và xác nhận thao tác."` đi kèm thẻ `Thêm công việc: bài giải tích` gây mâu thuẫn.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/orchestrator/chat.py:225-228](../../../backend/app/orchestrator/chat.py#L225-L228), [:335-355](../../../backend/app/orchestrator/chat.py#L335-L355) (`compose()`): nối toàn bộ message của các step trong `workflow_continuations` bằng khoảng trắng mà không khử trùng lặp và không tách riêng bước lỗi trước đó khỏi thông điệp của thẻ `AWAITING_APPROVAL` hiện tại.
- **Đặc tả sửa lỗi:**
  1. **BE — [chat.py:335-355](../../../backend/app/orchestrator/chat.py#L335-L355) (`compose()`):**
     - Gom các thông điệp hoàn tất trùng nhau (ví dụ `5` bước `"Đã cập nhật giờ rảnh."` → `"Đã cập nhật 5 khung giờ rảnh."`, hoặc chỉ trả tóm tắt kết quả không lặp).
     - Khi kết quả trả về đang ở trạng thái `AWAITING_APPROVAL` hoặc `AWAITING_CLARIFICATION`, không ghép nguyên văn chuỗi `"Mình chưa hiểu yêu cầu này, bạn thử dùng biểu mẫu nhé."` của bước `FAILED` trước đó lên đầu thông điệp xác nhận bước sau; nếu cần báo bước trước bị bỏ qua thì ghi chú tách biệt rõ ý (ví dụ: `"Mình chưa tạo được phần giờ rảnh từ câu trên, nhưng đã chuẩn bị sẵn công việc bên dưới để bạn xác nhận:"`).

---

### Nhóm D — Frontend Form làm rõ, Nhập liệu, Mạng & Hiệu năng (`F1-FIX-12` → `F1-FIX-15`)

#### F1-FIX-12 (P0 — Gate 5 FAIL) `[FE]` — Bộ phân tích câu & điền sẵn form làm rõ trên Planner sai giờ, thời lượng, ngày và rác tiêu đề (`CF-03`)

- **Gộp mã QA:** `CF-03`, `F1-E07-01`, `N01`, `U01`, `U06`, `KENT-QA-002`, `KENT-QA-008` (phần FE).
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`F1-E07-01` / `CF-03` / `N01` — Giờ đồng hồ bị biến thành thời lượng `480` phút & sai ngày/buổi):**
    - Prompts: `"Học Toán 8h tối mai"` (File 1, 3) và `"mai t lm bt toán 8h tối"` (File 7 Hình 8).
    - Thực tế: Form tự điền **Thời lượng = `480` phút** (do `8h × 60`), **Giờ bắt đầu = `08:00 AM`** (bỏ qua `"tối"`), **Ngày = hôm nay `25/11`** (bỏ qua `"mai"` đứng sau `"tối"` hoặc đứng đầu câu), tiêu đề còn rác `"mai t ... tối"`.
    - Kỳ vọng: Không bắt `8h` thành `480p` (để trống thời lượng cho người dùng nhập), giờ `20:00`, ngày mai `26/11`, tiêu đề sạch `"Học Toán"` / `"làm bài tập toán"`.
  - **Sub-case B (`U01` — Thời lượng `"trong 2h"` bị nhầm thành giờ bắt đầu `02:00 AM` & rác `"trong"`):**
    - Prompt: `"Tạo công việc làm bài tập toán vi tích phân trong 2h ngày mai"` (File 7 Hình 7).
    - Thực tế: Form điền `120p`, nhưng gán nhầm **`start_at = 02:00 AM`** và tiêu đề còn thừa chữ **`"trong"`**.
    - Kỳ vọng: `estimated_minutes = 120`, `start_at` để trống (không lấy từ `"trong 2h"`), tiêu đề sạch `"làm bài tập toán vi tích phân"`.
  - **Sub-case C (`U06` — Rác từ khóa trong tiêu đề):**
    - Prompt: `"tạo cv ôn bai đi"` (File 7) → Thực tế: Tiêu đề còn thừa `"cv"` và `"đi"`. Kỳ vọng: Tiêu đề sạch `"ôn bai"`.
  - **Sub-case D (`KENT-QA-002` — Tự điền sẵn `60` phút khi thiếu thời lượng):**
    - Prompts: `"Học Toán 8h tối mai"` & `"Nộp bài tập Lập trình"` (File 5 — *lưu ý: câu `"Học Địa lý lúc 25h ngày mai trong 60 phút"` có sẵn `"60 phút"` nên không tính là lỗi này*).
    - Thực tế: Form tự prefill `"60"` phút cho trường đang nằm trong danh sách `missing`, khiến người dùng dễ bấm nhầm mà không nhận ra đang thiếu thời lượng.
    - Kỳ vọng: Để trống các trường đang nằm trong `missing` nếu không trích xuất được từ câu nhập.
  - **Sub-case E (`KENT-QA-008` phần FE):** `"lm bt toan mai 9h sang nha, 45p"` còn sót cụm giờ/từ đệm trong tiêu đề trước khi bấm `Tiếp tục`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/planner/clarification.ts:118-127](../../../frontend/src/features/planner/clarification.ts#L118-L127) (`parseDurationMinutes`): regex đặt nhóm tiền tố tùy chọn (`?`) trước `(\d+)h` nên mọi giờ đồng hồ (`8h tối`, `12h đêm`, `25h`, `10h kém 15`) đều bị bắt thành thời lượng `N × 60` phút.
  - [clarification.ts:105-112](../../../frontend/src/features/planner/clarification.ts#L105-L112) (`parseTimeFromText`): không loại trừ cụm thời lượng (`trong 2h`), không xử lý buổi (`sáng`/`chiều`/`tối`/`đêm`), không xử lý `"rưỡi"` và `"kém"`.
  - [clarification.ts:49-51](../../../frontend/src/features/planner/clarification.ts#L49-L51), [:94](../../../frontend/src/features/planner/clarification.ts#L94) (`DEMO_DATE_RE`, `parseRelativeOrNumericDate`): chỉ khớp `"ngày mai"`, bỏ sót `"mai"` đứng riêng (`"tối mai"`, `"mai t ..."`).
  - [clarification.ts:131-145](../../../frontend/src/features/planner/clarification.ts#L131-L145) (`extractTaskTitle`): chưa dọn sạch `"cv"`, `"trong"` (đi kèm thời lượng), từ đệm cuối câu (`"đi"`, `"nha"`, `"nhé"`), và các cụm giờ/buổi.
  - [clarification.ts:182-188](../../../frontend/src/features/planner/clarification.ts#L182-L188) (`extractTaskDraftFromPrompt`) và [:207-218](../../../frontend/src/features/planner/clarification.ts#L207-L218) (`createClarificationDraft`): tự gán giá trị fallback mặc định (`"60"`, `"09:00"`, `todayIso`) ngay cả khi trường đang nằm trong danh sách `missing` cần người dùng tự điền (trong khi [TaskClarificationFields.tsx:50](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L50), [:125](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L125) chỉ render `<MissingBadge>` và [:132](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L132) chỉ đặt `placeholder="60"`).
- **Đặc tả sửa lỗi:**
  1. `parseDurationMinutes` ([clarification.ts:118-127](../../../frontend/src/features/planner/clarification.ts#L118-L127)): chỉ nhận diện `h`/`giờ`/`tiếng` là thời lượng khi đi kèm chỉ thị thời lượng (`trong`, `khoảng`, `tầm`, `dự kiến`, `hết`) hoặc mẫu thời lượng (`1 tiếng rưỡi` = `90`, `45p`/`45 phút`); tuyệt đối không bắt giờ đồng hồ (`8h tối`, `12h đêm`, `10h kém 15`).
  2. `parseTimeFromText` ([clarification.ts:105-112](../../../frontend/src/features/planner/clarification.ts#L105-L112)): loại bỏ các cụm thời lượng (`trong 2h`, `khoảng 1h30`) trước khi tìm giờ đồng hồ; hỗ trợ đầy đủ buổi (`chiều`/`tối`/`đêm` quy đổi `+12h` hợp lệ, `sáng`), `"rưỡi"` (`:30`) và `"kém"` (`10h kém 15` → `09:45`).
  3. `parseRelativeOrNumericDate` ([clarification.ts:94](../../../frontend/src/features/planner/clarification.ts#L94)) & `DEMO_DATE_RE` ([:50](../../../frontend/src/features/planner/clarification.ts#L50)): nhận diện `"mai"` độc lập bằng ranh giới từ (`\bmai\b`) bên cạnh `"ngày mai"`, `"tối mai"`, `"sáng mai"`.
  4. `extractTaskTitle` ([clarification.ts:131-145](../../../frontend/src/features/planner/clarification.ts#L131-L145)): làm sạch các tiền tố lệnh (`tạo cv`, `cv`, `thêm`), giới từ đi kèm thời lượng (`trong`), từ đệm (`đi`, `nha`, `nhé`, `t`, `mình`), và các cụm ngày/giờ đã trích xuất.
  5. [clarification.ts:182-188](../../../frontend/src/features/planner/clarification.ts#L182-L188), [:207-218](../../../frontend/src/features/planner/clarification.ts#L207-L218) & [TaskClarificationFields.tsx:50](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L50), [:125-133](../../../frontend/src/features/planner/TaskClarificationFields.tsx#L125-L133): bỏ prefill giá trị giả (`"60"`, `"09:00"`, `todayIso`) cho các trường nằm trong `missing` khi không trích được từ câu nhập; để trống `value` và highlight rõ ô đang thiếu.

---

#### F1-FIX-13 (P1) `[FE]` — Cả 2 ô nhập lệnh (Trợ lý AI & Planner) thiếu giới hạn 8.000 ký tự (`CF-08`)

- **Gộp mã QA:** `CF-08`, `F1-E13-02-UI` (File 1, 3, 7).
- **Các trường hợp con (Sub-cases):**
  - Thao tác: Dán chuỗi `8.005` ký tự vào ô nhập của **Trợ lý AI** (`ChatComposer`) và ô nhập lệnh của **Planner** (`PlannerCommandComposer`).
  - Thực tế: Cả 2 ô đều nhận đủ `8.005` ký tự và cho phép gửi request lên API, sau đó mới bị backend chặn HTTP `422` (UI hiển thị `"Dữ liệu chưa hợp lệ."`).
  - Kỳ vọng: Chặn ngay trên client ở ngưỡng `8.000` ký tự (khớp contract) và cảnh báo tiếng Việt rõ ràng trước khi gọi API.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/assistant/ChatComposer.tsx:131-151](../../../frontend/src/features/assistant/ChatComposer.tsx#L131-L151) và [frontend/src/features/planner/PlannerCommandComposer.tsx:172-189](../../../frontend/src/features/planner/PlannerCommandComposer.tsx#L172-L189): cả 2 `<textarea>` đều không có `maxLength={8000}` và không validate độ dài trước khi submit (trong khi [contracts/schemas/f1.schema.json:2257](../../../contracts/schemas/f1.schema.json#L2257) quy định `maxLength: 8000`).
- **Đặc tả sửa lỗi:**
  1. Khai báo hằng số dùng chung `MAX_MESSAGE_LENGTH = 8000` khớp [f1.schema.json:2257](../../../contracts/schemas/f1.schema.json#L2257).
  2. Áp dụng `maxLength={8000}` và kiểm tra độ dài `<= 8000` trước khi submit trên **cả** [ChatComposer.tsx:131-151](../../../frontend/src/features/assistant/ChatComposer.tsx#L131-L151) lẫn [PlannerCommandComposer.tsx:172-189](../../../frontend/src/features/planner/PlannerCommandComposer.tsx#L172-L189), kèm bộ đếm/cảnh báo tiếng Việt (ví dụ `"Nội dung tối đa 8.000 ký tự."`) khi chạm hoặc vượt ngưỡng.

---

#### F1-FIX-14 (P1) `[BE + FE]` — Độ trễ Chat P95 vượt ngưỡng 6 giây (`F1-E14-01`) & `sendMessage` tự retry bắn 2 request LLM (`CF-05`)

- **Gộp mã QA:** `CF-05`, `F1-E14-01`, `F1-E14-02-UI` (File 1, 3, 6, 8).
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`F1-E14-01` — Độ trễ Chat P95 > `6.000 ms` trên `deepseek-flash`):**
    - File 1 (50 lượt): `P50 = 2.852,2 ms`, **`P95 = 7.795,7 ms`**, `Max = 8.011,7 ms` (`503 = 0/50`; Decisions `P95 = 541,4 ms`).
    - File 3 (16 lượt): `P50 = 2.163,1 ms`, **`P95 = 6.449,8 ms`**, `Max = 6.449,8 ms` (`503 = 0/16`; Decisions `P95 = 146,5 ms`).
    - File 6 (51 lượt): `P50 = 3.645,1 ms`, **`P95 = 10.662,5 ms`**, `Max = 14.795,7 ms` (Decisions `P95 = 733,8 ms`).
    - File 8 (34 lượt): `P50 = 2.821,1 ms`, **`P95 = 10.572,1 ms`**, `Max = 12.392,7 ms` (Decisions `P95 = 22,5 ms`).
    - *Đối chiếu:* File 4 dùng `deepseek-chat` đạt `P50 = 1.150,2 ms`, `P95 = 1.624,5 ms`, `Max = 1.924,8 ms`.
    - Kỳ vọng: Chat P95 `<= 6.000 ms`.
  - **Sub-case B (`F1-E14-02-UI` / `CF-05` — Tự retry trên `sendMessage`):**
    - Thực tế: Khi gặp lỗi tạm thời/`503`, `sendMessage` tự retry 1 lần (= tổng **2 request LLM**, không phải 3 như câu mô tả cũ trong script QA).
    - Kỳ vọng: Không tự retry ngầm các request gọi LLM; để người dùng chủ động gửi lại.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/nlu/extractor.py:100-112](../../../backend/app/nlu/extractor.py#L100-L112) (`DeepSeekExtractor`): không đặt `max_tokens`, không tắt/kiểm soát reasoning/thinking token khi gọi `deepseek-flash`, prompt còn dài, `timeout` cứng `30.0s`.
  - [frontend/src/api/endpoints.ts:404-418](../../../frontend/src/api/endpoints.ts#L404-L418) (`sendMessage`, và tương tự các F1 write endpoints ở [:404-498](../../../frontend/src/api/endpoints.ts#L404-L498), trái ngược với `decideLearningOutcome` ở [:379-394](../../../frontend/src/api/endpoints.ts#L379-L394) đã có `retry: false`): không truyền `retry: false` nên [frontend/src/api/client.ts:151-164](../../../frontend/src/api/client.ts#L151-L164) tự retry 1 lần khi gặp lỗi retryable.
- **Đặc tả sửa lỗi:**
  1. **FE — [endpoints.ts:404-418](../../../frontend/src/api/endpoints.ts#L404-L418):** Đặt `retry: false` cho `sendMessage` để người dùng chủ động bấm gửi lại khi `503`/timeout, không tự nhân đôi request gọi LLM. Rà soát đặt tương tự cho `prepareAvailability`, `prepareStudyPlan`, `decide`, `reviewAction` tại [:404-498](../../../frontend/src/api/endpoints.ts#L404-L498).
  2. **BE — [extractor.py:100-112](../../../backend/app/nlu/extractor.py#L100-L112):** Giới hạn `max_tokens` (ví dụ `512`–`800`), cấu hình tham số tắt thinking/reasoning nếu model `deepseek-flash` hỗ trợ (hoặc cấu hình model mặc định `deepseek-chat` cho luồng chat trích xuất JSON), tối ưu độ dài prompt, đưa `timeout` ra cấu hình `Settings` thay vì cứng `30.0s`, nhằm kéo Chat P95 về `<= 6.000 ms`.

---

#### F1-FIX-15 (P1) `[FE]` — Lỗi mất mạng Offline báo nhầm lỗi máy chủ, xóa ô nhập & lặp request lỗi (`CF-09`)

- **Gộp mã QA:** `CF-09`, `F1-E11-03-UI`, `F1-E11-03`, `TAY-04`, `TAY-05`, `KENT-QA-015` / `MANUAL-05A` (File 1, 2, 3, 4, 5, 7).
- **Các trường hợp con (Sub-cases):**
  - `TAY-04` (File 1, File 2 ảnh `tay-test4-offline-chat.png`): Tắt mạng, gửi `"mai 17h học văn 30 phút, hạn thứ 7"` → Thực tế: Hiển thị `"Dịch vụ tạm thời chưa sẵn sàng. Hãy thử lại sau."`, **xóa trắng nội dung ô nhập**, không có nút `"Gửi lại"`, Network bắn **2 request `(failed)`**.
  - `TAY-05` (File 1, File 2 ảnh `tay-test5-offline-xac-nhan.webp`): Đã có thẻ nháp `"mai 18h học GDCD 30 phút, hạn thứ 7"`, tắt mạng rồi bấm `Xác nhận` 3 lần → Thực tế: Hiển thị 3 thông báo lỗi máy chủ, Network bắn **6 request `(failed)`** (2 request/lần bấm).
  - `KENT-QA-015` (File 5): Gửi `"Ôn tập Tiếng Anh ngày mai lúc 15h trong 45 phút, hạn hoàn thành 18h ngày mai."` khi Offline → báo nhầm `"Dịch vụ tạm thời chưa sẵn sàng. Hãy thử lại sau."`.
  - `F1-E11-03` (File 7 Hình 12 & 13): Gửi `"Ngày mai 14h ôn tiếng Anh trong 45 phút"` khi mất mạng (`ERR_INTERNET_DISCONNECTED`) → bắn 2 lần thử và báo lỗi máy chủ.
  - Kỳ vọng: Báo rõ lỗi mất kết nối mạng, không tự retry khi offline, không xóa mất nội dung người dùng đã gõ, có nút `"Gửi lại"` tái sử dụng đúng `idempotencyKey`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/api/client.ts:66-74](../../../frontend/src/api/client.ts#L66-L74), [:115-117](../../../frontend/src/api/client.ts#L115-L117), [:175](../../../frontend/src/api/client.ts#L175), [:207-210](../../../frontend/src/api/client.ts#L207-L210): khối `catch` lỗi mạng (`fetch` throw) quy về mã `SERVICE_UNAVAILABLE` nên dùng chung thông báo `"Dịch vụ tạm thời chưa sẵn sàng. Hãy thử lại sau."`, đồng thời vẫn kích hoạt retry 1 lần kể cả khi `navigator.onLine === false`.
  - [frontend/src/features/assistant/Assistant.tsx:718](../../../frontend/src/features/assistant/Assistant.tsx#L718), [:730](../../../frontend/src/features/assistant/Assistant.tsx#L730), [:752](../../../frontend/src/features/assistant/Assistant.tsx#L752) & [conversationHistory.ts:103-122](../../../frontend/src/features/assistant/conversationHistory.ts#L103-L122): xóa trắng ô nhập ngay khi nhấn gửi ở cả hai nhánh — `setEmptyInput("")` tại `Assistant.tsx:730` (hội thoại mới) và `appendMessages` reset `draftInput: ""` tại [conversationHistory.ts:119](../../../frontend/src/features/assistant/conversationHistory.ts#L119) (hội thoại đang mở) — đồng thời không cung cấp nút `"Gửi lại"` tái sử dụng `idempotencyKey` (`attempt.current`) khi `sendApi` thất bại.
  - [frontend/src/api/endpoints.ts:463-477](../../../frontend/src/api/endpoints.ts#L463-L477) (`decide`): chưa tắt auto-retry khi lỗi mạng offline → 3 lần bấm thành 6 request failed.
- **Đặc tả sửa lỗi:**
  1. **FE — [client.ts](../../../frontend/src/api/client.ts#L66-L210):** Tách riêng mã lỗi `NETWORK_ERROR` (khác với `SERVICE_UNAVAILABLE` HTTP `503`), thêm thông điệp tiếng Việt: `"Không có kết nối mạng hoặc không thể kết nối máy chủ. Hãy kiểm tra mạng rồi thử lại."`.
  2. **FE — Chặn retry khi offline:** Không tự retry khi `navigator.onLine === false` hoặc lỗi là `NETWORK_ERROR` trên các request ghi (`sendMessage`, `decide`, `prepare*`), tránh bắn 2–6 request thất bại liên tiếp.
  3. **FE — [Assistant.tsx:718-752](../../../frontend/src/features/assistant/Assistant.tsx#L718-L752) & [conversationHistory.ts:119](../../../frontend/src/features/assistant/conversationHistory.ts#L119):** Khi `sendApi` thất bại do `NETWORK_ERROR` / `SERVICE_UNAVAILABLE`, khôi phục/giữ lại nội dung ô nhập (`emptyInput` hoặc `draftInput`) và/hoặc hiển thị nút `"Gửi lại"` ngay cạnh tin nhắn lỗi, tái sử dụng đúng `idempotencyKey` trong `attempt.current` để tránh tạo trùng bản nháp khi mạng hồi phục.

---

### Nhóm E — Frontend Calendar, Layout & Hiển thị Tiếng Việt (`F1-FIX-16` → `F1-FIX-21`)

#### F1-FIX-16 (P1) `[FE + BE/DB]` — Ba lỗi hiển thị & điều hướng Lịch (`CAL-02`, `CAL-03`, `CAL-06`)

- **Gộp mã QA:** `CAL-02`, `CAL-03`, `CAL-06` (File 7 Hình 1 & Hình 2).
- **Các trường hợp con (Sub-cases):**
  - **Sub-case A (`CAL-02` — Chuyển `Tháng` → `Tuần` nhảy lùi về tháng trước):** Đang xem tuần hiện tại (tháng 11/2026), bấm tab `Tháng` rồi bấm lại tab `Tuần` → Thực tế: Lịch nhảy về `26/10–01/11/2026`. Kỳ vọng: Giữ nguyên tuần đang xem trước đó.
  - **Sub-case B (`CAL-03` — Badge nút `Công việc` và legend đếm số block thay vì số công việc):** Tài khoản có **3 công việc** (được chia thành **4 study blocks**) → Thực tế: Nút `"Công việc"` hiển thị badge **`4`**; ngược lại khi có 3 công việc chưa xếp lịch (`0` block) thì dòng legend không phản ánh đúng số công việc đang có. Kỳ vọng: Tách bạch đúng số lượng "công việc" và "buổi học (block)".
  - **Sub-case C (`CAL-06` — Trùng màu mặc định giữa các công việc):** Hai task tạo liên tiếp (`bt toán` và `đọc lý thuyết xác suất`) không chỉ định màu đều nhận cùng màu `#596CF0`, khó phân biệt trên lịch. Kỳ vọng: Tự động xoay vòng màu khác nhau giữa các công việc khi người dùng không chỉ định màu.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - `CAL-02` — [frontend/src/pages/Planner.tsx:443-457](../../../frontend/src/pages/Planner.tsx#L443-L457) (`chooseView`): khi chuyển từ `Tháng` sang `Tuần` mà chưa chọn ngày cụ thể (`selectedMonthDate === null`), code fallback về `${month}-01` (ngày mùng 1 đầu tháng 11 rơi vào tuần `26/10–01/11`).
  - `CAL-03` — [frontend/src/pages/Planner.tsx:647-649](../../../frontend/src/pages/Planner.tsx#L647-L649), [:668-671](../../../frontend/src/pages/Planner.tsx#L668-L671): dùng `shown.length` (mảng `events` = số `StudyBlock` trong API mode) cho cả badge nút `"Công việc"` lẫn dòng legend, trong khi `TaskPanel` nhận `tasks` tại [:752](../../../frontend/src/pages/Planner.tsx#L752).
  - `CAL-06` — [backend/app/orchestrator/workflow_shared.py:11](../../../backend/app/orchestrator/workflow_shared.py#L11), [supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql:153](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L153) và [frontend/src/features/planner/clarification.ts:192](../../../frontend/src/features/planner/clarification.ts#L192): hardcode 1 màu mặc định duy nhất `#596CF0` (hoặc `#6C5CE7`).
- **Đặc tả sửa lỗi:**
  1. **FE — [Planner.tsx:443-457](../../../frontend/src/pages/Planner.tsx#L443-L457):** Giữ nguyên tuần `week` đang xem khi chuyển `Tháng` → `Tuần` nếu `selectedMonthDate === null` (chỉ nhảy sang tuần mới khi người dùng chủ động click 1 ngày trong lịch Tháng).
  2. **FE — [Planner.tsx:647-649](../../../frontend/src/pages/Planner.tsx#L647-L649), [:668-671](../../../frontend/src/pages/Planner.tsx#L668-L671):** Trong API mode, hiển thị `tasks.length` trên badge nút `"Công việc"` và tính đúng số công việc chưa xếp lịch ở dòng legend (tách bạch khái niệm "công việc" và "buổi học").
  3. **BE/DB & FE — Màu mặc định:** Xoay vòng tự động bảng màu `TASK_COLOR_OPTIONS` (ví dụ theo màu ít dùng nhất hoặc hash ổn định không trùng task liền trước) khi người dùng không chỉ định màu cụ thể.

---

#### F1-FIX-17 (P1) `[FE]` — Vỡ layout Planner ở màn hình `1366×820` và khi mở `TaskPanel` (`QA-UI-01`, `KENT-QA-011`)

- **Gộp mã QA:** `QA-UI-01`, `V2-06`, `KENT-QA-011`, File 6 Hình 1, File 7 Hình 10, File 2 ảnh `v2-06-*`, `rc-v2-02-*`.
- **Các trường hợp con (Sub-cases):**
  - Viewport `1366×820`, sidebar mở và `TaskPanel` (`300px`) mở:
    - Ô nhập lệnh `.planner-command` bị ép hẹp còn ~50px; placeholder và dòng feedback `#planner-command-feedback` (`"Đã duyệt kế hoạch học."`) bị ngắt xuống dòng **từng chữ một**.
    - Ở chế độ `Tháng` (khi xuất hiện thêm nút `"Hôm nay"`), thanh `.dashboard-calendar-controls` bị tràn/chồng lấn, **Lịch Tháng che một phần nút `"Tuần"`**.
  - Kỳ vọng: Thanh điều khiển và ô nhập lệnh tự xuống dòng gọn gàng, giữ chiều rộng sử dụng tối thiểu, không đè chồng lên lưới Lịch Tháng.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/styles/layout.css:193](../../../frontend/src/styles/layout.css#L193) & [frontend/src/styles/planner.css:1115-1147](../../../frontend/src/styles/planner.css#L1115-L1147): ở `1366×820`, `.main-content` rộng `1122px > 1050px` nên `@container (max-width: 1050px)` không kích hoạt; khi `TaskPanel` (`300px`) mở, `.planner-calendar` chỉ còn `~814px`.
  - [planner.css:55-68](../../../frontend/src/styles/planner.css#L55-L68), [:388-399](../../../frontend/src/styles/planner.css#L388-L399), [:415-422](../../../frontend/src/styles/planner.css#L415-L422), [:597-601](../../../frontend/src/styles/planner.css#L597-L601), [:813-815](../../../frontend/src/styles/planner.css#L813-L815): `.planner-heading-action` chỉ đặt `flex-wrap: wrap` khi có `.planner-command.is-expanded` ([:391](../../../frontend/src/styles/planner.css#L391)), `.dashboard-calendar-controls` không wrap, còn các luật chế độ Tháng `.main-content:has(.planner-page):has(.month-calendar)`, `.planner-page:has(.month-calendar)` và `.planner-page:has(.month-calendar) .planner-calendar` đều đặt `overflow: visible` ([:813-815](../../../frontend/src/styles/planner.css#L813-L815)).
- **Đặc tả sửa lỗi:**
  1. Cho phép `.planner-heading-action` và `.dashboard-calendar-controls` tự xuống dòng (`flex-wrap: wrap; row-gap: 8px;`) khi chiều rộng container hẹp (nâng ngưỡng container query lên khoảng `1200px` hoặc dùng container query riêng trên `.planner-calendar` ở `max-width: 920px`).
  2. Đặt `min-width: 240px` (hoặc `flex: 1 1 260px`) cho `.planner-command` và `white-space: normal; word-break: normal;` cho `#planner-command-feedback` để không bao giờ vỡ thành cột 1 từ/dòng.
  3. Đặt `flex-shrink: 0` cho `.planner-calendar .card-heading` và điều chỉnh `z-index`/overflow của `.month-calendar` để khung lịch Tháng không bao giờ đè lên nút `"Tuần"` / `"Hôm nay"`.

---

#### F1-FIX-18 (P1) `[FE]` — Nhãn khung giờ rảnh trên lịch tuần bị hiển thị theo mốc đã cắt `08:00` thay vì giờ thật (`QA-UI-02`, `KENT-QA-006`)

- **Gộp mã QA:** `QA-UI-02`, `V2-07`, `KENT-QA-006` (File 1, File 2 ảnh `v2-07-*`, `rc-0422-lich`, File 5).
- **Các trường hợp con (Sub-cases):**
  - Người dùng lưu khung giờ rảnh `06:00–12:00` (File 1 `V2-07`) hoặc `07:00–18:00` (File 5 `KENT-QA-006`), trong khi khung hiển thị lịch mặc định bắt đầu từ `08:00`.
  - Thực tế: Lịch tuần cắt hình khối tại `08:00` và **in luôn nhãn `"Rảnh 08:00–12:00"` / `"08:00–18:00"`**, khiến người dùng hiểu nhầm hệ thống đã lưu sai giờ `06:00`/`07:00` thành `08:00`.
  - Kỳ vọng: Tọa độ vẽ cắt theo khung lưới nhưng nhãn giờ vẫn hiển thị đúng giờ gốc đã lưu (`"Rảnh 06:00–12:00"` / `"Rảnh 07:00–18:00"`).
- **Trace IDs (`X-Request-ID`):** `c606870d-...`, `0d4ce4cc-...`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/planner/workingTime.ts:81-99](../../../frontend/src/features/planner/workingTime.ts#L81-L99) & [frontend/src/features/planner/WeekCalendar.tsx:128-171](../../../frontend/src/features/planner/WeekCalendar.tsx#L128-L171) (đặc biệt [:158-170](../../../frontend/src/features/planner/WeekCalendar.tsx#L158-L170)): dùng chung cặp giá trị `[start, end]` đã bị clip theo khung hiển thị để vừa tính tọa độ `top`/`height` vừa format chuỗi nhãn giờ hiển thị.
- **Đặc tả sửa lỗi:**
  1. Tại [workingTime.ts:81-99](../../../frontend/src/features/planner/workingTime.ts#L81-L99): giữ nguyên `sourceStart`, `sourceEnd` (giờ gốc từ DB/API) song song với `clippedStart`, `clippedEnd` (tọa độ vẽ trong khung lưới).
  2. Tại [WeekCalendar.tsx:128-171](../../../frontend/src/features/planner/WeekCalendar.tsx#L128-L171): dùng `clippedStart`/`clippedEnd` để tính `top`/`height`, nhưng **render nhãn bằng `sourceStart`–`sourceEnd`** (ví dụ `"Rảnh 06:00–12:00"`, có thể kèm chỉ báo nhỏ nếu có phần nằm ngoài khung hiển thị).

---

#### F1-FIX-19 (P2) `[FE]` — Tùy chỉnh `"Lưu hiển thị"` khung giờ lịch tự reset về `08:00–18:00` khi chuyển trang

- **Gộp mã QA:** Mục 7(1) (File 1 — tái hiện 2 lần).
- **Các trường hợp con (Sub-cases):**
  - Thao tác: Người dùng chỉnh khung giờ hiển thị trên Lịch (ví dụ `06:00–22:00`), bấm `"Lưu hiển thị"`, chuyển sang trang khác (`Trợ lý AI` / `Ôn tập`...) rồi quay lại trang `Lịch học`.
  - Thực tế: Khung giờ hiển thị bị reset về mặc định `08:00–18:00`.
  - Kỳ vọng: Giữ nguyên khung giờ người dùng đã lưu khi chuyển trang hoặc tải lại trang.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/pages/Planner.tsx:217-219](../../../frontend/src/pages/Planner.tsx#L217-L219): `displayRanges` chỉ lưu bằng `useState(DEFAULT_DISPLAY_RANGES)` cục bộ trong component `Planner`.
  - [frontend/src/App.tsx:780](../../../frontend/src/App.tsx#L780): khi chuyển `page !== "Planner"`, component `Planner` bị unmount nên toàn bộ state cục bộ bị mất.
- **Đặc tả sửa lỗi:**
  1. Lưu `displayRanges` vào `localStorage` theo khóa gắn `userId` (`studyflow_display_ranges_${userId}`, tương tự cơ chế `studyflow_task_panel_open`) mỗi khi bấm `"Lưu hiển thị"`, và đọc lại khi khởi tạo `Planner` (có validate JSON an toàn + fallback về `DEFAULT_DISPLAY_RANGES`).

---

#### F1-FIX-20 (P2) `[FE + BE]` — Hiển thị mã lỗi và thông báo tiếng Anh thô trên giao diện đề xuất lịch (`QA-UI-05`)

- **Gộp mã QA:** `QA-UI-05`, `V2-08` (File 1, File 2 ảnh `rc-v2-08-de-xuat-mot-phan`).
- **Các trường hợp con (Sub-cases):**
  - Khi lịch chỉ xếp được một phần (partial plan), khung `ProposalReview` hiển thị nguyên văn tiếng Anh: `INSUFFICIENT_CAPACITY` và `UNALLOCATED_WORK: The greedy baseline...`.
  - Kỳ vọng: Toàn bộ lý do không xếp hết giờ và cảnh báo phải hiển thị bằng tiếng Việt tự nhiên cho sinh viên.
- **Trace ID (`X-Request-ID`):** `741bf52f-b350-4916-bf53-a1a2afd6e434`.
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [backend/app/f1/scheduler/engine.py:365-374](../../../backend/app/f1/scheduler/engine.py#L365-L374): trả `reason_codes` dạng enum (`INSUFFICIENT_CAPACITY`, `NO_AVAILABILITY`, `OUTSIDE_HORIZON`, `DAILY_LIMIT_REACHED`, `BLOCK_TOO_SHORT`, `DEADLINE_PASSED`, ...) và `warning.message` tiếng Anh (`"The greedy baseline..."`).
  - [frontend/src/features/planner/ProposalReview.tsx:130-153](../../../frontend/src/features/planner/ProposalReview.tsx#L130-L153) (dòng [:133](../../../frontend/src/features/planner/ProposalReview.tsx#L133), [:151](../../../frontend/src/features/planner/ProposalReview.tsx#L151)): render thô `i.code: i.message` và `item.reasons.join(", ")` mà không qua bảng ánh xạ tiếng Việt.
- **Đặc tả sửa lỗi:**
  1. **FE — [ProposalReview.tsx:130-153](../../../frontend/src/features/planner/ProposalReview.tsx#L130-L153):** Bổ sung từ điển ánh xạ toàn bộ `reason_codes` (`INSUFFICIENT_CAPACITY`, `NO_AVAILABILITY`, `OUTSIDE_HORIZON`, `START_TIME_CONFLICT`, `DAILY_LIMIT_REACHED`, `BLOCK_TOO_SHORT`, `DEADLINE_PASSED`, `GENERATED_START_MISMATCH`, và mã mới từ `F1-FIX-04` nếu có) cùng `warning.code` (`UNALLOCATED_WORK`) sang tiếng Việt dễ hiểu; chỉ fallback sang chuỗi mặc định tiếng Việt nếu gặp mã lạ, không bao giờ in raw tiếng Anh `The greedy baseline...` lên UI.
  2. **BE — [engine.py:365-374](../../../backend/app/f1/scheduler/engine.py#L365-L374):** Giữ `code` ổn định theo contract để FE map chính xác (hoặc chuẩn hóa `warning.message` thân thiện thay cho chuỗi kỹ thuật nội bộ `"The greedy baseline..."`).

---

#### F1-FIX-21 (P2) `[FE]` — Nhãn `"Chờ xác nhận"` và `"Đã xác nhận và lưu vào tài khoản."` xuất hiện mâu thuẫn cùng lúc trên thẻ Chat (`KENT-QA-005`)

- **Gộp mã QA:** `KENT-QA-005` (File 5 — `E04-08`, `MANUAL-03/06`) và File 2 ảnh `rc-sec-the-cu-sau-f5.jpg`.
- **Các trường hợp con (Sub-cases):**
  - Sau khi người dùng đã bấm `Xác nhận` (hoặc sau khi F5 tải lại thẻ đã lưu), phần đầu thẻ vẫn hiện badge `"Chờ xác nhận"` trong khi phần thân thẻ ghi `"Đã xác nhận và lưu vào tài khoản."`.
  - Kỳ vọng: Badge đầu thẻ phản ánh đúng trạng thái thực tế (`Đã xác nhận` / `Đã hủy` / `Chờ xác nhận` / `Cần xem lại`).
- **Nguyên nhân gốc rễ (`main @ e366422`):**
  - [frontend/src/features/assistant/ChatTranscript.tsx:94-108](../../../frontend/src/features/assistant/ChatTranscript.tsx#L94-L108) (dòng [:100-103](../../../frontend/src/features/assistant/ChatTranscript.tsx#L100-L103)): logic hiển thị badge chỉ kiểm tra sự tồn tại của `entry.proposal?.reference` (trường này vẫn được giữ nguyên sau khi approve/reject) thay vì kiểm tra `entry.proposal?.status`.
- **Đặc tả sửa lỗi:**
  1. Tại [ChatTranscript.tsx:100-103](../../../frontend/src/features/assistant/ChatTranscript.tsx#L100-L103): suy badge trực tiếp từ `entry.proposal?.status` (khớp đủ 5 trạng thái trong [conversationHistory.ts:43](../../../frontend/src/features/assistant/conversationHistory.ts#L43) và [ChatTranscript.tsx:177](../../../frontend/src/features/assistant/ChatTranscript.tsx#L177), [:212-216](../../../frontend/src/features/assistant/ChatTranscript.tsx#L212-L216) để giữ hoạt động chuẩn cho cả API mode lẫn Demo mode):
     - `"awaiting_approval"` → `"Chờ xác nhận"`
     - `"approved"` → `"Đã xác nhận"`
     - `"demo_acknowledged"` → `"Đã xác nhận (bản mẫu)"`
     - `"cancelled"` → `"Đã hủy"`
     - `"review_required"` → `"Cần xem lại"`

---

## 4. Báo cáo sau khi Fix & Bảng Tick Nghiệm thu (GitHub / Google Sheet)

### 4.1. Cách báo cáo tối giản cho DEV

1. **Khi mở PR trên GitHub** (tiêu đề tiếng Anh, mô tả tiếng Việt, kèm cập nhật `worklogs/<github-username>.md`), dán đúng 3 dòng ngắn:
   ```markdown
   - **Mã lỗi đã sửa:** `F1-FIX-xx`
   - **Tác động môi trường:** Không / Cần `supabase db reset` / Cần đổi `.env`
   - **Quy tắc đã chốt (nếu có):** ...
   ```
2. **Cập nhật tiến độ bằng 1 cú tick:**
   - **Dùng Google Sheet:** Import file [F1_Bang_Nghiem_Thu_Fix.csv](./F1_Bang_Nghiem_Thu_Fix.csv) vào Google Sheets → chọn 3 cột `DEV_da_fix`, `Can_DB_reset_hoac_Env`, `QA_da_duyet` → bấm **Insert → Checkbox**. DEV sửa xong chỉ điền `PR_hoac_Commit_SHA` rồi **tick `DEV_da_fix`**; QA kiểm tra lại xong chỉ **tick `QA_da_duyet`**.
   - **Dùng GitHub Issue / Markdown:** Copy trực tiếp danh sách checklist bên dưới vào 1 GitHub Tracking Issue để tick nhanh.

### 4.2. Checklist Tick nhanh trên GitHub

**Lỗi sản phẩm (`21` mã):**
- [ ] `F1-FIX-01` (`P0`, `BE + FE`) — Horizon `minute-aligned` HTTP 422 *(PR/SHA: ...)*
- [ ] `F1-FIX-02` (`P0`, `BE + DB`) — Hạn mặc định `CF-01` & chặn `deadline_at <= start_at` *(Chờ chốt rule; PR/SHA: ...)*
- [ ] `F1-FIX-03` (`P0`, `BE + FE`) — Replan `CF-02` `retained block is outside current availability` *(PR/SHA: ...)*
- [ ] `F1-FIX-04` (`P0`, `BE`) — Ràng buộc cứng `start_at == expected_utc` (`hcọ Lý`) *(Chờ chốt rule; PR/SHA: ...)*
- [ ] `F1-FIX-05` (`P0 · Gate 3`, `FE`) — Cô lập IndexedDB lịch sử chat theo `userId` (`QA-SEC-01`) *(Chờ chốt rule đăng xuất; PR/SHA: ...)*
- [ ] `F1-FIX-06` (`P0 · Gate 4`, `BE + DB + FE`) — Kẹt `409` khi làm rõ, đóng popup Planner & F5 giữa chừng (`CF-04`) *(PR/SHA: ...)*
- [ ] `F1-FIX-07` (`P1`, `FE`) — Tab bị `409 STALE_ENTITY_VERSION` phải ẩn nút Xác nhận/Hủy *(PR/SHA: ...)*
- [ ] `F1-FIX-08` (`P1`, `BE + Contract/DB + FE`) — Validate sớm `start_at >= deadline_at` & `estimated_minutes` *(PR/SHA: ...)*
- [ ] `F1-FIX-09` (`P0`, `NLU/Prompt + BE`) — Khẩu ngữ/teencode (`8r`, `lm bt`), câu ghép 2 intent & hỏi lịch bận `N03` *(PR/SHA: ...)*
- [ ] `F1-FIX-10` (`P1`, `BE + FE`) — Chặn khung giờ đảo ngược `start >= end` (`N02B`) cả BE lẫn Trợ lý AI *(PR/SHA: ...)*
- [ ] `F1-FIX-11` (`P2`, `BE`) — `compose()` khử lặp câu xác nhận & không ghép lỗi bước trước vào thẻ sau *(PR/SHA: ...)*
- [ ] `F1-FIX-12` (`P0 · Gate 5`, `FE`) — Sửa parser & bỏ prefill giả trên form làm rõ Planner (`CF-03`) *(PR/SHA: ...)*
- [ ] `F1-FIX-13` (`P1`, `FE`) — Chặn tối đa `8.000` ký tự ở cả `ChatComposer` & `PlannerCommandComposer` (`CF-08`) *(PR/SHA: ...)*
- [ ] `F1-FIX-14` (`P1`, `BE + FE`) — Giảm Chat P95 `<= 6s` (`F1-E14-01`) & đặt `retry: false` cho `sendMessage` (`CF-05`) *(PR/SHA: ...)*
- [ ] `F1-FIX-15` (`P1`, `FE`) — Tách lỗi Offline khỏi `503`, không retry khi offline, giữ ô nhập/nút Gửi lại (`CF-09`) *(PR/SHA: ...)*
- [ ] `F1-FIX-16` (`P1`, `FE + BE/DB`) — Lịch `CAL-02` (Tháng→Tuần), `CAL-03` (badge đếm task), `CAL-06` (xoay vòng màu) *(PR/SHA: ...)*
- [ ] `F1-FIX-17` (`P1`, `FE`) — Sửa vỡ layout `1366×820` & chế độ Tháng khi mở `TaskPanel` (`QA-UI-01`) *(PR/SHA: ...)*
- [ ] `F1-FIX-18` (`P1`, `FE`) — Hiển thị đúng nhãn giờ gốc `sourceStart–sourceEnd` thay vì mốc cắt `08:00` (`QA-UI-02`) *(PR/SHA: ...)*
- [ ] `F1-FIX-19` (`P2`, `FE`) — Lưu `displayRanges` vào `localStorage` theo `userId` *(PR/SHA: ...)*
- [ ] `F1-FIX-20` (`P2`, `FE + BE`) — Dịch tiếng Việt toàn bộ `reason_codes` & `UNALLOCATED_WORK` trên `ProposalReview` *(PR/SHA: ...)*
- [ ] `F1-FIX-21` (`P2`, `FE`) — Đồng bộ badge thẻ Chat theo `entry.proposal?.status` (`KENT-QA-005`) *(PR/SHA: ...)*

**Phụ lục Script QA (`1` mã — người bảo trì script QA):**
- [ ] `F1-FIX-22` (`P2`, `QA Script`) — Sửa `run_f1_ui_qa.mjs` & `run_f1_auto_qa.py` *(PR/SHA: ...)*

---

## Phụ lục 1 — Lỗi / Bất đồng bộ trong Script Auto-QA (`F1-FIX-22`)

> *Phụ lục này dành riêng cho người bảo trì bộ script QA (`docs/qa/f1/run_f1_ui_qa.mjs` và `docs/qa/f1/run_f1_auto_qa.py`), tách biệt khỏi 21 lỗi mã nguồn sản phẩm.*

### F1-FIX-22 (P2) `[QA Script]` — Bất đồng bộ & lỗi kỹ thuật trong `run_f1_ui_qa.mjs` và `run_f1_auto_qa.py`

- **Gộp mã QA:** `F1-FE-UNIT` (treo >5 phút ở File 1; báo `pass=0, fail=0` ở File 4 & 7), `F1-E04-02` `KeyError: 'start_at'` (File 4), mô tả sai trong `F1-E13-02-UI` (File 7) & `F1-E14-02-UI` (File 1), `F1-E03-01` thiếu log (File 8), `F1-E12-02` `[200, 422]` ở harness tiền-commit (File 8, đã khép ở File 9), `--mode embedded` che lỗi `minute-aligned` (File 8).
- **Nguyên nhân gốc rễ & Đặc tả sửa script:**
  1. **[run_f1_ui_qa.mjs:152-179](./run_f1_ui_qa.mjs#L152-L179) (`F1-FE-UNIT`):**
     - Thiếu cờ định dạng TAP nên trên Node 23+/24 đầu ra mặc định chuyển sang reporter `spec` (`ℹ pass N`), khiến regex `/# pass (\d+)/` trả về `pass=0, fail=0`.
     - 6 file test React (`PlannerCommandComposer.test.ts`, `WeekCalendar.test.ts`, `monthCalendar.test.ts`, `ProposalReview.test.ts`, `DecisionActions.test.ts`, `QuizOverview.test.ts`) khởi tạo `vite.createServer(...)` song song qua `spawnSync` gây treo >5 phút trên Windows khi có `node_modules`.
     - *Sửa:* Bổ sung cờ reporter TAP, cấu hình timeout rõ ràng và giới hạn chạy tuần tự hoặc tách riêng nhóm 6 file khởi tạo Vite server trong `run_f1_ui_qa.mjs`.
  2. **[run_f1_ui_qa.mjs:104-118](./run_f1_ui_qa.mjs#L104-L118) (`F1-E13-02-UI`):** Dòng [:117](./run_f1_ui_qa.mjs#L117) ghi sai thực tế `"(PlannerCommandComposer có nhưng ChatComposer thiếu)"` → sửa kiểm tra tĩnh kiểm duyệt `maxLength` trên **cả 2 file** `ChatComposer.tsx` và `PlannerCommandComposer.tsx`.
  3. **[run_f1_ui_qa.mjs:127-132](./run_f1_ui_qa.mjs#L127-L132) (`F1-E14-02-UI`):** Sửa mô tả từ `"3 request"` về đúng hành vi của `client.ts` (`retry 1 lần = tổng 2 request`).
  4. **[run_f1_auto_qa.py:853-1320](./run_f1_auto_qa.py#L853-L1320) (17 hàm case):** Các hàm `tc_e01_02` ([:889](./run_f1_auto_qa.py#L889), [:895](./run_f1_auto_qa.py#L895)), `tc_e01_03` ([:917](./run_f1_auto_qa.py#L917)), `tc_e02_01` ([:942](./run_f1_auto_qa.py#L942)), `tc_e02_03` ([:985](./run_f1_auto_qa.py#L985)), `tc_e04_02` ([:1083](./run_f1_auto_qa.py#L1083)), `tc_e04_07` ([:1129](./run_f1_auto_qa.py#L1129)) cùng 11 hàm khác chỉ kiểm tra `r.get("action_reference")` mà không kiểm tra `r.get("state") == "AWAITING_APPROVAL"` và không check `slots.get("start_at")` trước `local_hhmm(slots["start_at"])` → khi `F1-FIX-06` trả `action_reference != null` cho `NEEDS_CLARIFICATION`, script bị crash `KeyError: 'start_at'`. Cần siết guard kiểm tra đồng thời `state == "AWAITING_APPROVAL"` và `slots.get("start_at")`.
  5. **[run_f1_auto_qa.py:1019-1020](./run_f1_auto_qa.py#L1019-L1020) (`tc_e03_01`):** Bổ sung in `state` và `questions` vào message lỗi khi không tạo ra nháp để dễ chẩn đoán.
  6. **[run_f1_auto_qa.py:1521](./run_f1_auto_qa.py#L1521), [:1647-1650](./run_f1_auto_qa.py#L1647-L1650):** Chế độ embedded đang ép `second=0, microsecond=0` vào `clock()` nên không phát hiện được `F1-FIX-01`; cần bỏ ép `second=0` ở đồng hồ harness nếu muốn phản ánh đúng điều kiện chạy thật.
  7. *Ghi nhận lịch sử:* `F1-E12-02` `[200, 422]` ở File 8 (`111830`, pre-`040213fb`) đã tự khép PASS `[200, 409]` sau 63 giây ở File 9 (`111933`).

---

## Phụ lục 2 — Bảng Đối soát 100% 9 File Báo cáo QA (Coverage Matrix) & Các mục Đã đóng / Ngoài phạm vi F1

### P2.1. Coverage Matrix (`9 File Báo cáo → F1-FIX-01..22`)

| Mã Fix | Prio | File 1 (`BaoCao_25-11.md`) | File 2 (`_final.pdf`) | File 3 (`Huong`) | File 4 (`Kent Auto`) | File 5 (`Kent Manual`) | File 6 (`auto-qa.pdf`) | File 7 (`web-calendar.pdf`) | File 8 (`111830.md`) | File 9 (`111933.md`) |
|---|---|---|---|---|---|---|---|---|---|---|
| **F1-FIX-01** | P0 | `F1-E01-01` (T2), `F1-E01-02`, `V2-05`, `QA-0422` | Ảnh `v2-05-cau1/2`, `rc-0422-*` | `F1-E01-01`, `F1-E01-02` | `F1-E01-01`, `F1-E01-02` | `KENT-QA-001` | `F1-E01-01`, `F1-E01-02`, Hình 1 | `F1-E01-01-WEB` | — *(clock tròn phút)* | — |
| **F1-FIX-02** | P0 | `TAY-01` *(note hạn +60p)* | — | — | `F1-E04-01` | `KENT-QA-009` (`E01-01`, `E04-02`, `E04-06`, `E04-07-D`) | `CF-01` web (Hình 2) | `CF-01` (Hình 6) | `F1-E01-02` (`CF-01` 90/120p) | — |
| **F1-FIX-03** | P0 | `F1-E02-02`, `V2-03` (`CF-02`) | Ảnh `rc-v2-03-422-cf02` | `F1-E02-02` | `F1-E02-02` | — | `F1-E02-02` | — | `F1-E02-02` | — |
| **F1-FIX-04** | P0 | `V2-09`, Mục 7(2) (`hcọ Lý`) | Ảnh `rc-v2-09-*` | — | — | — | — | — | — | — |
| **F1-FIX-05** | P0 | `QA-SEC-01` (Gate 3) | Ảnh `rc-sec-*` | Gate 3 *(mở theo Hùng)* | — | — | — | — | — | — |
| **F1-FIX-06** | P0 | `F1-E08-03`, `V3-04`, `TAY-03` | Ảnh `rc-cf04-*`, `tay-test3-*`, `v3-04-*` | `F1-E08-03` | — *(PASS trên nhánh Kent)* | `KENT-QA-003` | `F1-E08-03`, Hình 3 | `F1-E11-02`, `PLANNER-CANCEL` | `F1-E08-03` | — |
| **F1-FIX-07** | P1 | `V3-03`, Mục 7(3) | Ảnh `v3-03-tab-bi-tu-choi` | — | — | — | — | — | — | — |
| **F1-FIX-08** | P1 | `F1-E06-03` (`CF-07`) | — | `F1-E06-03` | `F1-E06-03` | `KENT-QA-012`, `013`, `014` | `F1-E06-03` | — | `F1-E06-03` | — |
| **F1-FIX-09** | P0 | `F1-E01-01` (T1), `F1-E04-02`, `F1-E04-04` | Ảnh `v2-03-gio-ranh-tu-suy` | — | `F1-E04-02` (NLU), `F1-E04-04` | `KENT-QA-007`, `008` (server) | `F1-E04-02`, `F1-E04-04` | `N03` | `F1-E03-01`, `F1-E04-02`, `F1-E04-04` | — |
| **F1-FIX-10** | P1 | — | — | — | — | — | — | `N02B` | — | — |
| **F1-FIX-11** | P2 | `QA-UI-03`, `QA-UI-04` | Ảnh `rc-v2-01-cau-lap`, `rc-v2-03-chat` | — | — | `KENT-QA-004` | — | — | — | — |
| **F1-FIX-12** | P0 | `F1-E07-01` (`CF-03`) | — | `CF-03` | — *(PASS trên nhánh Kent)* | `KENT-QA-002`, `008` (FE) | — | `U01`, `U06`, `N01` | — | — |
| **F1-FIX-13** | P1 | `F1-E13-02-UI` (`CF-08`) | — | `CF-08` | — *(PASS trên nhánh Kent)* | — | — | `F1-E13-02-UI` *(2 ô)* | — | — |
| **F1-FIX-14** | P1 | `F1-E14-01`, `F1-E14-02-UI` | — | `F1-E14-01`, `CF-05` | — *(PASS trên nhánh Kent)* | — | `F1-E14-01` | — | `F1-E14-01` | — |
| **F1-FIX-15** | P1 | `F1-E11-03-UI`, `TAY-04`, `TAY-05` | Ảnh `tay-test4-*`, `tay-test5-*` | `CF-09` | `F1-E11-03-UI` | `KENT-QA-015` | — | `F1-E11-03` | — | — |
| **F1-FIX-16** | P1 | — | — | — | — | — | — | `CAL-02`, `CAL-03`, `CAL-06` | — | — |
| **F1-FIX-17** | P1 | `V2-06` (`QA-UI-01`) | Ảnh `v2-06-*`, `rc-v2-02-*` | — | — | `KENT-QA-011` | Hình 1 | Hình 10 | — | — |
| **F1-FIX-18** | P1 | `V2-07` (`QA-UI-02`) | Ảnh `v2-07-*`, `rc-0422-lich` | — | — | `KENT-QA-006` | — | — | — | — |
| **F1-FIX-19** | P2 | Mục 7(1) *(reset hiển thị)* | — | — | — | — | — | — | — | — |
| **F1-FIX-20** | P2 | `QA-UI-05` | Ảnh `rc-v2-08-de-xuat-mot-phan` | — | — | — | — | — | — | — |
| **F1-FIX-21** | P2 | — | Ảnh `rc-sec-the-cu-sau-f5` | — | — | `KENT-QA-005` | — | — | — | — |
| **F1-FIX-22** | P2 | `F1-FE-UNIT` (treo), đính chính `CF-05` | — | — | `F1-FE-UNIT` (TAP), `E04-02` `KeyError` | — | — | `F1-FE-UNIT` (TAP), `E13-02` static check | `E12-02` harness, `E03-01` log | *(khép `E12-02`)* |

### P2.2. Các mục Đã đóng / Ngoài phạm vi Feature 1

- **`KENT-QA-010`** (File 5, `E04-05`): **CLOSED — NOT A BUG**.
- **`GET /v1/materials?limit=20` HTTP `500`** (File 5 mục 8, ảnh `123818`, `123939`, `132634`, `132732`): Lỗi thuộc **Feature 3 (Materials)**, chuyển nhóm F3 xử lý riêng (không tính vào danh sách lỗi F1).
- **Các hạng mục chưa thực thi do thiếu công cụ môi trường (không phải lỗi mã nguồn F1):**
  - Chế độ `--browser` của UI script thiếu Playwright (File 1).
  - `F1-E04-03` gõ Telex thiếu bộ gõ IME UniKey/EVKey (File 7) / `PARTIAL` ở lượt đầu (File 5).
  - Fault-injection HTTP `503` nhân tạo trên trình duyệt (File 7).
