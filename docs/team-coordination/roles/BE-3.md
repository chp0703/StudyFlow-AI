# Hướng Dẫn Vai Trò `BE-3` — AI / DeepSeek / File Ingestion

| Thuộc tính | Giá trị |
|---|---|
| **Mã vai trò (Role ID)** | **`BE-3`** |
| **Nhóm (Team)** | Backend (OpenAI Codex) |
| **Mục đích (Purpose)** | Hướng dẫn thực thi độc lập cho AI coding agent đảm nhận Adapter & Benchmark DeepSeek phía Server, Pipeline đọc/trích xuất tệp (`image`, `calendar file`, `document`), Từ chối tệp âm thanh (`audio rejection`), Phòng chống Prompt Injection và Tạo Candidate trung gian để người dùng review |
| **Thẩm quyền (Authority)** | Tuân thủ [`AGENTS.md`](../../../AGENTS.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md) và [`contracts/README.md`](../../../contracts/README.md) (`1.0.1`) |
| **Base commit kiểm chứng** | `main` @ `7837050` |
| **Cập nhật lần cuối** | 11/11/2026 (`Asia/Ho_Chi_Minh`) |

---

## 1. Sứ mệnh & Phạm vi Trách nhiệm (Mission)

`BE-3` chịu trách nhiệm toàn bộ miền **Trích xuất Ngôn ngữ Tự nhiên (AI/NLU) và Pipeline Tiếp nhận/Trích xuất Tệp (File Ingestion)**:

1. **DeepSeek Server-Side Adapter & Benchmark Owner:** Duy trì `backend/app/nlu/extractor.py` (`DeepSeekExtractor`, `ScriptedExtractor`, `UnavailableExtractor`), `backend/app/nlu/evaluation.py`, script `backend/scripts/evaluate_nlu.py` và bộ dữ liệu 40 câu tiếng Việt (`backend/tests/fixtures/nlu_eval_vi.json`, ngưỡng mục tiêu `>= 38/40`).
2. **Image / Calendar / Document Ingestion & Parsing Owner:** Thiết kế và triển khai pipeline tiếp nhận, xác thực định dạng và trích xuất thông tin từ **3 nhóm tệp duy nhất**: `image`, `calendar file` (`.ics`), và `document` (`.pdf`, `.docx`, `.txt`) sau khi quyết định `OD-004` được phê duyệt.
3. **Audio Rejection Owner (Server-Side Enforcement):** Từ chối tuyệt đối mọi tệp âm thanh (`audio/*`, `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`, voice note) và không hỗ trợ audio transcription dưới bất kỳ hình thức nào.
4. **Prompt Injection Defense & Intermediate Extraction Candidate:** Xem toàn bộ văn bản người dùng và nội dung bên trong tệp tải lên là **dữ liệu không tin cậy (`untrusted data`)**; sản sinh cấu trúc trích xuất trung gian kèm độ tin cậy (`confidence`) và danh sách các trường chưa rõ (`unresolved fields`) để chuyển qua `BE-4` / `FE-2` cho người dùng xem lại, chỉnh sửa và xác nhận. **Tuyệt đối không tự động tạo `AcademicTask` hoặc tự commit lịch từ tệp.**

---

## 2. Tài liệu Bắt buộc Đọc Trước Khi Code (Inputs to Read)

1. [`AGENTS.md`](../../../AGENTS.md) & [`docs/team-coordination/README.md`](../README.md).
2. [`PROJECT_SOURCE_OF_TRUTH.md`](../PROJECT_SOURCE_OF_TRUTH.md), [`ARCHITECTURE_AND_RUNTIME_RULES.md`](../ARCHITECTURE_AND_RUNTIME_RULES.md), [`FILE_OWNERSHIP.md`](../FILE_OWNERSHIP.md), [`TASK_BOARD.md`](../TASK_BOARD.md), [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md), [`PRODUCT_REQUIREMENTS_AND_DECISIONS.md`](../PRODUCT_REQUIREMENTS_AND_DECISIONS.md), [`OPEN_DECISIONS.md`](../OPEN_DECISIONS.md).
3. [`contracts/README.md`](../../../contracts/README.md) (mục 1, 2, 4), [`contracts/schemas/f1.schema.json`](../../../contracts/schemas/f1.schema.json) (`ExtractionResult`, `ExtractedIntent`, `CandidateTaskFields`) và [`contracts/acceptance-cases.md`](../../../contracts/acceptance-cases.md) (`ORCH-01`..`ORCH-05`).
4. [`docs/implementation/WP4_WORKFLOW.md`](../../implementation/WP4_WORKFLOW.md), [`docs/implementation/WP4_NOTES.md`](../../implementation/WP4_NOTES.md), [`docs/implementation/DEMO_ENVIRONMENT.md`](../../implementation/DEMO_ENVIRONMENT.md), [`eval/README_f1_nlu.md`](../../../eval/README_f1_nlu.md).
5. Code & dữ liệu thực tế:
   - `backend/app/nlu/extractor.py`
   - `backend/app/nlu/evaluation.py`
   - `backend/scripts/evaluate_nlu.py`
   - `backend/tests/fixtures/nlu_eval_vi.json`
   - `backend/tests/unit/test_extractor.py` & `backend/tests/unit/test_nlu_evaluation.py`

---

## 3. Quyền Sở hữu File & Phạm vi Thay đổi (Ownership & Allowed / Forbidden Changes)

### 3.1. File được phép sửa / tạo trực tiếp (`Allowed Changes — Primary Owner`)
- `backend/app/nlu/extractor.py`
- `backend/app/nlu/evaluation.py`
- `backend/app/nlu/prompts/**`
- `backend/scripts/evaluate_nlu.py`
- `backend/tests/unit/test_extractor.py`
- `backend/tests/unit/test_nlu_evaluation.py`
- `backend/tests/fixtures/nlu_eval_vi.json` & `eval/**`
- **`[PLANNED — Sau khi chốt OD-004 & INT-001]`:** `backend/app/ingestion/**` và `backend/tests/unit/test_ingestion*.py` cho bộ đọc `image`, `calendar`, `document` và bộ chặn `audio`.

### 3.2. File dùng chung cần Co-Review (`Shared Files`)
- `backend/requirements.txt` & `backend/requirements-acceptance.txt` (bắt buộc có `BE-4` co-review trước khi thêm thư viện đọc tệp như `icalendar` / `pypdf`).
- `contracts/schemas/f1.schema.json` & `contracts/openapi.yaml` (chỉ sửa qua [`CONTRACT_CHANGE_PROTOCOL.md`](../CONTRACT_CHANGE_PROTOCOL.md) sau khi `OD-004` được duyệt).

### 3.3. Vùng CẤM sửa (`Forbidden Changes`)
- **CẤM TUYỆT ĐỐI** đưa `DEEPSEEK_API_KEY` thật vào code, test fixture, log, comment hay file được Git theo dõi.
- **CẤM** để LLM hoặc File Parser trực tiếp gọi RPC ghi vào DB (`create_task_candidate`, `confirm_task`, `approve_study_plan`, v.v.) hoặc tự sinh `ApprovalAction` / `user_id`.
- **CẤM** giữ kết nối transaction DB mở trong lúc đang gọi HTTP tới DeepSeek API hoặc đang chạy OCR/parsing tệp.
- **CẤM** tự ý sửa `backend/app/f1/scheduler/**` (`BE-2`), `supabase/migrations/**` (`BE-1`/`BE-2`), `backend/app/orchestrator/**` (`BE-4`), hoặc `frontend/**` (`FE-1`/`FE-2`).
- **CẤM** sửa bộ dữ liệu `nlu_eval_vi.json` theo hướng làm dễ câu hỏi để gian lận điểm số benchmark `38/40`.

---

## 4. Phụ thuộc Liên Vai trò (Dependencies)

- **Phụ thuộc đầu vào (Upstream):**
  - Nhận quy tắc trường Task mới (`title` tách khỏi `course_label`, `priority`, `duration`, `start time`) từ **`BE-1`** (`BE1-001`, `OD-001`, `OD-002`).
  - Nhận quyết định phê duyệt phạm vi định dạng tệp và cơ chế lưu trữ tại **`OD-004`** và **`INT-001`**.
  - Nhận cấu hình biến môi trường `DEEPSEEK_API_KEY` (chỉ ở môi trường chạy, ngoài Git) từ người vận hành (`OD-008`) để chạy benchmark thật (`BE3-001`).
- **Đầu ra bàn giao (Downstream):**
  - Cung cấp `Extractor.extract()` trả về `ExtractionResult` hợp lệ cho `ChatProcessor` của **`BE-4`**.
  - Cung cấp hợp đồng upload/extraction và danh sách candidate trung gian (kèm `confidence` & `unresolved_fields`) cho **`BE-4`** và **`FE-2`** (`FE2-002`, `FE2-003`).

---

## 5. Danh mục Task & Sản phẩm Bàn giao (Assigned Tasks & Deliverables)

| Task ID | Sản phẩm bàn giao (Deliverables) | Trạng thái hiện tại |
|---|---|---|
| **BE3-001** | Kiểm chứng điều kiện tiên quyết, tinh chỉnh prompt tiếng Việt trong `extractor.py` (tách sạch `title` và `course_label`, không suy diễn approval) và chạy `evaluate_nlu.py` với DeepSeek thật đạt `>= 38/40` khi có key | `BLOCKED` (chờ `DEEPSEEK_API_KEY` tại `OD-008`) |
| **BE3-002** | Bản đặc tả kỹ thuật & ma trận định dạng/parser cho `image`, `calendar file` (`.ics`), `document` (`.pdf`/`.docx`/`.txt`) kèm giới hạn kích thước và phòng chống prompt injection | `NEEDS_DECISION` (`OD-004`) |
| **BE3-003** | Module trích xuất tệp trả về biểu diễn trung gian (`ExtractionCandidate` + `confidence` + `unresolved_fields`) và bàn giao sang `BE-4` / `FE-2` để người dùng review trước khi tạo Task Draft | `BLOCKED` (chờ `OD-004` & `INT-001`) |
| **BE3-004** | Bộ kiểm tra và từ chối hoàn toàn tệp `audio` / voice note ở tầng server (kiểm tra cả MIME type, phần mở rộng và file header/magic bytes) kèm unit tests đầy đủ | `BLOCKED` (chờ `OD-004` & `INT-001`) |

---

## 6. Kiểm thử Bắt buộc & Lệnh Chạy (Required Tests)

Mọi thay đổi của `BE-3` bắt buộc chạy và ghi nhận kết quả thực tế:

```powershell
# 1. Chạy unit tests cho Extractor và bộ chấm NLU (không cần mạng/key thật)
python -B -m unittest discover -s backend/tests/unit -p "test_*nlu*.py" -v
python -B -m unittest discover -s backend/tests/unit -p "test_extractor.py" -v

# 2. Kiểm tra tính hợp lệ của contract schema (ExtractionResult)
python -B contracts/check_contract.py

# 3. Khi môi trường đã cấu hình DEEPSEEK_API_KEY (không in key ra màn hình!):
python -B backend/scripts/evaluate_nlu.py

# 4. Kiểm tra diff sạch và đảm bảo không lộ secret
git diff --check
```

---

## 7. Tiêu chuẩn Hoàn thành & Checklist Bàn giao (Done Criteria & Handoff Checklist)

- [ ] Đầu ra của `extractor.py` và mọi parser tệp luôn đi qua bộ kiểm tra schema (`contract.is_valid(...)`); nếu model trả JSON lỗi hoặc ngoài schema thì trả lỗi tạm thời `503 SERVICE_UNAVAILABLE (retryable=True)` hoặc yêu cầu làm rõ, tuyệt đối không đoán mò.
- [ ] Nội dung tệp tải lên được bao bọc rõ trong vùng dữ liệu không tin cậy của prompt, vô hiệu hóa mọi chỉ thị kiểu "Ignore previous instructions / tự động duyệt lịch".
- [ ] Mọi tệp âm thanh (`audio/*`, voice note) đều bị từ chối deterministically ở server.
- [ ] Không có bất kỳ API key hay credential nào xuất hiện trong diff, log hoặc báo cáo.
- [ ] Điền đầy đủ báo cáo bàn giao theo [`templates/WORK_HANDOFF_TEMPLATE.md`](../templates/WORK_HANDOFF_TEMPLATE.md) và thông báo cho `BE-4`, `FE-2`.
