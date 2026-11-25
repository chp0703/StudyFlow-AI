# Hướng dẫn Sửa lỗi & Nghiệm thu Feature 1 (Dành cho Team DEV)

- **Phạm vi:** Feature 1 (Intelligent Academic Planner) — nhánh `main` (`6b6e62e` / `e4f38f9`)
- **Mục tiêu:** Hướng dẫn Team **Backend**, **Frontend** và **AI / Prompt** đọc đúng kết quả Auto-QA, sửa dứt điểm các lỗi P0/P1 đã phát hiện và tự kiểm tra nghiệm thu trước khi bàn giao lại cho QA.
- **Tài liệu QA liên quan:** [F1_Huong_Dan_QA.pdf](F1_Huong_Dan_QA.pdf) · [run_f1_auto_qa.py](run_f1_auto_qa.py) · [run_f1_ui_qa.mjs](run_f1_ui_qa.mjs) · [05-regression-checklist.md](05-regression-checklist.md)

---

## 1. Quy trình 4 Bước Khép kín giữa DEV và QA

1. **Bước 1 – Đọc đúng phiếu lỗi (Lọc `[BUG]` theo nhãn `RC-*`):**
   - QA chạy Auto-QA và gửi file báo cáo từ `logs/f1-qa-reports/` (hoặc 3 ảnh + mã `X-Request-ID` khi test tay).
   - Mỗi lỗi đều gắn 1 nhãn gốc để biết đúng nhóm Dev nhận xử lý:
     - **`RC-BACKEND` / `RC-TOOL` / `RC-DB`** → **Dev Backend**
     - **`RC-FE`** → **Dev Frontend**
     - **`RC-AGENT`** → **Dev AI / Prompt**
2. **Bước 2 – Tái hiện nhanh tại máy cá nhân (10 giây):**
   - Trước khi sửa code, chạy đúng mã `Test ID` bị lỗi để thấy lỗi tái hiện ngay trên máy mình:
     ```bash
     # Tái hiện lỗi Backend/AI cụ thể (VD: F1-E01-02, F1-E02-02)
     python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --env-file .env.local --case F1-E01-02,F1-E02-02 --trials 1

     # Tái hiện lỗi Frontend
     node docs/qa/f1/run_f1_ui_qa.mjs
     ```
3. **Bước 3 – Sửa lỗi đúng Root Cause (tuyệt đối không vá triệu chứng hoặc bỏ qua Gate G1..G5):**
   - Kiểm tra cả **bản sửa code**, **migration (nếu đụng SQL RPC)**, **unit/acceptance test mới** cho bug vừa sửa, và đối chiếu ranh giới Contract tại [contracts/README.md](../../../contracts/README.md).
4. **Bước 4 – Tự nghiệm thu (`k = 3` trials) trước khi mở PR bàn giao QA:**
   - Mã lỗi mình sửa phải đạt **`[PASS] 3/3`** (`Pass^3 = 100%`, không chấp nhận lúc đúng lúc sai).
   - Chạy toàn bộ cổng kiểm tra bắt buộc của repo (`check_contract.py`, `generate_contract_schema_migration.py --check`, `unittest`, `evaluate_planner.py`, `run_f1_ui_qa.mjs`) trước khi yêu cầu QA nghiệm thu.

---

## 2. Danh sách Lỗi & Hướng dẫn Sửa Chi tiết theo Từng Nhóm DEV

### 2.1. Nhóm Backend (`RC-BACKEND` / `RC-TOOL` / `RC-DB`)

| Mã lỗi & Mức độ | Mã Test tái hiện | Vị trí file cần sửa | Nguyên nhân gốc & Hướng xử lý cụ thể | Lệnh tự kiểm tra sau khi sửa |
|---|---|---|---|---|
| **`CF-01` (P0 – Blocker)** | `F1-E01-02` | [backend/app/orchestrator/actions.py](../../../backend/app/orchestrator/actions.py#L107-L120)<br>[202611140001_require_start_at_in_confirm_task.sql](../../../supabase/migrations/202611140001_f1_be01_require_start_at_in_confirm_task.sql#L128) | **Hiện tượng:** Task dài `> 90p` không nêu hạn nộp riêng (VD: *"học Toán lúc 8h sáng trong 2 tiếng"*) bị cắt còn `90/120` phút (`30p` rơi vào `BLOCK_TOO_SHORT`).<br>**Nguyên nhân:** Hệ thống tự gán `deadline_at = start_at + estimated_minutes` (`08:00 + 120p = 10:00`), trong khi policy mặc định tách tối đa `90p/block` và chèn `break_minutes = 10p` → 2 block + nghỉ cần tối thiểu `130p` (`10:10`), không vừa `10:00`.<br>**Hướng sửa:** Khi user không nêu deadline tường minh cho task cố định giờ bắt đầu, không khóa cứng `deadline_at` bằng đúng `start_at + estimated_minutes` mà để cuối ngày `start_at` (hoặc tính thêm thời gian nghỉ theo `SchedulingPolicy`, giữ nguyên bất biến hợp đồng). Thêm unit + integration test cho task `120p`/`180p`. | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E01-02 --trials 1` |
| **`CF-02` (P0 – Blocker)** | `F1-E02-02` | [backend/app/f1/planning/generate.py](../../../backend/app/f1/planning/generate.py#L103-L108) | **Hiện tượng:** Khi đã có `StudyBlock` duyệt ở tuần này và user gõ *"Sắp xếp lại lịch tuần tới"*, API nổ lỗi `422 retained block is outside current availability`.<br>**Nguyên nhân:** `generate.py#L103` truyền `start_at=start, end_at=end` (chỉ giới hạn trong `generation_scope` tuần tới) vào `normalize_time_windows(...)`, làm mọi `retained_blocks` tương lai trước `scope.start_at` bị `constraints.py#L259` báo nằm ngoài giờ rảnh.<br>**Hướng sửa:** Mở rộng phạm vi `normalize_time_windows` bao trùm từ `min(now, scope.start_at, min(retained_future.start_at))` đến `max(scope.end_at, max(retained_future.end_at))` đúng theo đặc tả `schema.md#L513`. | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E02-02 --trials 1` |
| **`CF-04` (P0 – Blocker)** | `F1-E08-03`, `F1-E11-02` | [backend/app/orchestrator/chat.py](../../../backend/app/orchestrator/chat.py#L64-L115)<br>[backend/app/orchestrator/actions.py](../../../backend/app/orchestrator/actions.py) | **Hiện tượng:** Hội thoại bị kẹt cứng `409 ACTION_REVIEW_REQUIRED` không lối thoát khi (a) đang `NEEDS_CLARIFICATION` mà user muốn hủy/đổi ý (`action_reference = null`), hoặc (b) nhấn `F5` lúc request đang bay trên mạng chậm.<br>**Hướng sửa:** Trả `action_reference` hợp lệ (hoặc hỗ trợ endpoint/lệnh hủy rõ ràng) ngay ở trạng thái `NEEDS_CLARIFICATION`; khi trả `409 ACTION_REVIEW_REQUIRED`, đính kèm `active_action` / `action_reference` hoặc để Frontend tự gọi `GET` khôi phục `active_action` của hội thoại sau reload. | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E08-03 --trials 1` |
| **`CF-05` (P1 – High)** | `F1-E14-01` | [backend/app/nlu/extractor.py](../../../backend/app/nlu/extractor.py#L46-L70) | **Hiện tượng:** Chat NLU mất `7s–26s`, P95 vượt ngưỡng `10.5s` (rủi ro timeout `20s` → `503`).<br>**Nguyên nhân:** `DeepSeekExtractor` gửi request tới `deepseek-flash` mà không truyền `"thinking": {"type": "disabled"}` (trong khi `SourceExtractor` ở `ingestion/service.py#L65` đã tắt và chỉ mất `~0.8s`).<br>**Hướng sửa:** Bổ sung `"thinking": {"type": "disabled"}` (hoặc cấu hình theo env) vào payload của `DeepSeekExtractor`, giữ nguyên `temperature=0` và `response_format={"type":"json_object"}`. | Chạy trọn bộ `run_f1_auto_qa.py` và kiểm tra dòng `F1-E14-01`: Chat P95 `<= 6000 ms`, `0` timeout `503`. |
| **`CF-07` (P1 – High)** | `F1-E06-03` | [backend/app/orchestrator/actions.py](../../../backend/app/orchestrator/actions.py#L223-L253) | **Hiện tượng:** Khi user nhập `start_at > deadline_at` (VD: *"lúc 20h, hạn 10h sáng"*), hệ thống vẫn tạo thẻ `AWAITING_APPROVAL`; đến khi user bấm Xác nhận mới nổ `422` và giữ kẹt nháp.<br>**Hướng sửa:** Kiểm tra `start_at > deadline_at` (và `available_from_at > deadline_at`) ngay trước khi gọi `create_task_candidate` / `prepare_pending_action`, trả `NEEDS_CLARIFICATION` hoặc thông báo sửa giờ bằng tiếng Việt. | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E06-03 --trials 1` |

> **Lưu ý kiểm thử đồng thời (`F1-E12-02`):** Đảm bảo trong môi trường PostgreSQL thật (`--mode live`), 2 request `POST /v1/decisions` gửi đồng thời trên cùng 1 proposal luôn trả đúng `[200, 409]` (1 thắng, 1 `STALE_PROPOSAL` / `STALE_ENTITY_VERSION`) nhờ khóa `app_private.lock_owner`.

---

### 2.2. Nhóm Frontend (`RC-FE`)

| Mã lỗi & Mức độ | Mã Test tái hiện | Vị trí file cần sửa | Nguyên nhân gốc & Hướng xử lý cụ thể | Lệnh tự kiểm tra sau khi sửa |
|---|---|---|---|---|
| **`CF-03` (P0 – Blocker)** | `F1-E07-01` | [frontend/src/features/planner/clarification.ts](../../../frontend/src/features/planner/clarification.ts#L80-L175) | **Hiện tượng:** Với câu thiếu thời lượng như `"Học Toán 8h tối mai"`, hàm `createClarificationDraft` biến `"8h"` thành `estimated_minutes = "480"`, đặt giờ thành `"08:00"` (mất chữ `"tối"`), đặt ngày thành hôm nay (không nhận `"tối mai"`), và cắt nhầm giờ trong tên môn.<br>**Hướng sửa:**<br>1. `parseDurationMinutes`: chỉ khớp đơn vị thời lượng (`phút`, `p`, `tiếng`, `giờ`, hoặc sau từ khóa `trong / khoảng / dự kiến / mất`), **tuyệt đối không khớp mốc giờ** (`lúc 8h`, `8h sáng/tối/đêm`, `10h kém 15`, `25h`).<br>2. `parseTimeFromText`: hỗ trợ buổi `chiều/tối` (`+12h`), `đêm` (`12h đêm -> 00:00`), `kém`.<br>3. `parseRelativeOrNumericDate`: hỗ trợ `"mai"`, `"sáng mai"`, `"tối mai"`, `"chiều mai"`.<br>4. Cập nhật [clarification.test.ts](../../../frontend/src/features/planner/clarification.test.ts) bao phủ đủ các ca này. | `node docs/qa/f1/run_f1_ui_qa.mjs` |
| **`CF-04-UI` (P0 – Blocker)** | `F1-E11-02` | [frontend/src/features/assistant/Assistant.tsx](../../../frontend/src/features/assistant/Assistant.tsx)<br>[frontend/src/features/assistant/apiAssistant.ts](../../../frontend/src/features/assistant/apiAssistant.ts) | **Hiện tượng:** Khi mạng `Slow 3G` và user nhấn `F5` trong lúc `POST /v1/messages` đang `Pending`, `localStorage` chưa kịp lưu `PendingRecord`. Reload xong gửi tiếp bị dính `409 ACTION_REVIEW_REQUIRED` nhưng UI không hiện thẻ Xác nhận/Hủy; đồng thời nếu tin cuối là `ERROR`, thẻ đang chờ ở tin trước bị ẩn mất.<br>**Hướng sửa:** Đồng bộ `active_action` từ server khi khôi phục hội thoại hoặc khi nhận `409 ACTION_REVIEW_REQUIRED`, và luôn giữ hiển thị nút Xác nhận/Hủy cho `active_action` đang mở bất kể tin nhắn lỗi chen ngang. | `node docs/qa/f1/run_f1_ui_qa.mjs --browser ...` (và test tay Slow 3G + F5) |
| **`CF-08` (P1 – High)** | `F1-E13-02-UI` | [frontend/src/features/assistant/ChatComposer.tsx](../../../frontend/src/features/assistant/ChatComposer.tsx#L96-L107) | **Hiện tượng:** `PlannerCommandComposer.tsx` có chặn `MAX_MESSAGE_LENGTH = 8000` ký tự theo Contract `UserMessage`, còn `ChatComposer.tsx` ở trang Trợ lý AI lại cho nhập/gửi vượt `8.000` ký tự gây lỗi `422`.<br>**Hướng sửa:** Áp dụng đúng ngưỡng `8.000` ký tự (`maxLength` / validate + bộ đếm + cảnh báo tiếng Việt) đồng nhất với `PlannerCommandComposer.tsx`. | `node docs/qa/f1/run_f1_ui_qa.mjs` |
| **`CF-05-UI` (P1 – High)** | `F1-E14-02-UI` | [frontend/src/api/endpoints.ts](../../../frontend/src/api/endpoints.ts#L222-L231) | **Hiện tượng:** `sendMessage` không truyền `retry: false` nên khi gặp `503` / timeout, `client.ts` tự bắn lặp 3 lần lên LLM gây treo màn hình chờ tới 60 giây.<br>**Hướng sửa:** Thêm `retry: false` vào `sendMessage` (giống `generateQuestionDrafts` ở dòng 140), để người dùng chủ động bấm Gửi lại bằng `Idempotency-Key` đã giữ sẵn trong `apiAssistant.ts`. | `node docs/qa/f1/run_f1_ui_qa.mjs` |
| **`CF-09` (P2 – Medium)** | `F1-E11-03-UI` | [frontend/src/api/client.ts](../../../frontend/src/api/client.ts#L60-L120)<br>[frontend/src/api/mappers.ts](../../../frontend/src/api/mappers.ts) | **Hiện tượng:** Khi mất mạng hoàn toàn (`Offline` / `ERR_INTERNET_DISCONNECTED`), `client.ts` ném `NETWORK_ERROR` gắn mã `SERVICE_UNAVAILABLE` khiến UI báo *"Dịch vụ tạm thời chưa sẵn sàng"* y như lỗi `503` của server.<br>**Hướng sửa:** Tách mã/cờ phân biệt lỗi kết nối mạng client (Offline, không retry lặp 3 lần vô ích) với lỗi `503` từ backend và hiển thị thông báo kiểm tra kết nối Internet bằng tiếng Việt. | `node docs/qa/f1/run_f1_ui_qa.mjs` |

---

### 2.3. Nhóm AI / Prompt (`RC-AGENT`)

| Mã lỗi & Mức độ | Mã Test tái hiện | Vị trí file cần sửa | Nguyên nhân gốc & Hướng xử lý cụ thể | Lệnh tự kiểm tra sau khi sửa (`k = 3`) |
|---|---|---|---|---|
| **Giờ khẩu ngữ `"8r"` (P0)** | `F1-E04-04` | [backend/app/nlu/extractor.py](../../../backend/app/nlu/extractor.py#L15-L42) (`PROMPT`) | **Hiện tượng:** `"Học Hóa lúc 8r tối nay"` bị `deepseek-flash` hiểu sai `2/3` lần thành `20:00` thay vì `20:30` (giờ rưỡi).<br>**Hướng sửa:** Bổ sung quy tắc + ví dụ ngắn trong `PROMPT` cho cách viết tắt giờ rưỡi tiếng Việt (`Xr`, `X giờ rưỡi` = `X:30`; phân biệt `12h đêm` = `00:00` ngày kế tiếp; `Xh kém Y` = `(X-1):(60-Y)`). | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E04-04 --trials 3` |
| **`CF-06` – Dải thứ lặp `"T2–T6"` (P0)** | `F1-E04-08` | [backend/app/nlu/extractor.py](../../../backend/app/nlu/extractor.py#L15-L42)<br>[backend/app/orchestrator/chat.py](../../../backend/app/orchestrator/chat.py#L254) | **Hiện tượng:** Câu `"rảnh thứ 2 đến thứ 6"` có thể chỉ sinh 1 intent `weekday = 1` (Thứ Hai), làm mất Thứ Ba–Thứ Sáu.<br>**Hướng sửa:** Hướng dẫn rõ trong `PROMPT` (hoặc chuẩn hóa ở backend) khi gặp dải thứ `"thứ X đến thứ Y"` phải bung đủ danh sách `SET_AVAILABILITY` tương ứng từng `weekday` từ `X..Y`. | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --case F1-E04-08 --trials 3` |
| **Chập chờn không dấu & Teencode (P0/P1)** | `F1-E04-01`, `F1-E04-02`, `F1-E03-01` | [backend/app/nlu/extractor.py](../../../backend/app/nlu/extractor.py#L15-L42) | **Hiện tượng:** Câu viết tắt (`"lm bt toan mai 9h sang nha, 45p"`) bỏ sót `start_at`; câu không dấu đôi lúc gán `deadline_at == start_at`; đôi lúc câu chuẩn có dấu (`F1-E03-01`) không trả nháp ổn định.<br>**Hướng sửa:** Bổ sung quy tắc trong `PROMPT`: (1) nếu không nêu hạn nộp riêng thì **không** gán `deadline_at == start_at`; (2) nhận diện viết tắt phổ biến (`bt`, `lm`, `mai 9h`, `p`/`phut`); (3) luôn chạy `--trials 3` để kiểm tra `Pass^3 = 100%` sau mỗi lần sửa prompt! | `python -B docs/qa/f1/run_f1_auto_qa.py --mode embedded --suite E01,E03,E04,E08 --trials 3` |

---

## 3. Bộ Lệnh Nghiệm thu Bắt buộc trước khi Mở PR / Bàn giao QA

Trước khi báo QA *"đã sửa xong, vào test lại đi"*, DEV **bắt buộc** chạy qua danh sách lệnh dưới đây và đính kèm kết quả vào mô tả PR (tiếng Việt theo `AGENTS.md`):

### 3.1. Cổng Tĩnh & Unit / Acceptance Tests (Chạy Offline, ~20 giây)
```bash
python -B contracts/check_contract.py
python -B backend/scripts/generate_contract_schema_migration.py --check
python -B -m unittest discover -s backend/tests/unit -p "test_*.py"
python -B -m unittest discover -s backend/tests/acceptance_sol -p "test_*.py"
python -B -m unittest discover -s backend/tests/acceptance_api_sol -p "test_*.py"
python -B backend/scripts/evaluate_planner.py
cd frontend && npx tsc --noEmit && npm run build && cd ..
```

### 3.2. Cổng Database Local Supabase (Bắt buộc nếu có sửa SQL / Migrations)
```bash
supabase db reset --yes
supabase test db
# Chạy integration & concurrency tests trên PostgreSQL local (cấm trỏ Cloud phomrutsdhdgejlskwcb!)
```

### 3.3. Cổng Auto-QA End-to-End (Chứng minh sửa thật trên `deepseek-flash`)
```bash
# 1. Nghiệm thu nhanh đúng mã lỗi vừa sửa (bắt buộc 3/3 PASS):
python -B docs/qa/f1/run_f1_auto_qa.py --mode live --env-file .env.local --case <TEST_ID_VUA_SUA> --trials 3

# 2. Nghiệm thu toàn bộ trước khi Merge lớn / Release:
python -B docs/qa/f1/run_f1_auto_qa.py --mode live --env-file .env.local --trials 3
node docs/qa/f1/run_f1_ui_qa.mjs
```

### 3.4. Quy tắc Bàn giao PR chuẩn của Dự án (`AGENTS.md`)
- Cập nhật log công việc vào `worklogs/<github-username>.md` theo mẫu `worklogs/sample.md` trước khi push.
- Commit message và PR title viết bằng **tiếng Anh** theo Conventional Commits (VD: `fix(f1): compute default deadline with policy breaks`); **không** thêm `Co-Authored-By` hay chữ ký AI.
- PR description viết bằng **tiếng Việt**, ghi rõ: **(1)** Lỗi `CF-xx` / `Test ID` đã sửa, **(2)** Kết quả `Pass^3` trước & sau khi sửa từ `logs/f1-qa-reports/`, **(3)** Các check đã chạy và phần chưa chạy (nếu có).
