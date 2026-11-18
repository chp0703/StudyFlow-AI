# StudyFlow AI — Learning Assessment & Adaptive Revision domain schema (F2)

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản extension | **1.0.0** (`assessment_version: "1.0.0"`) |
| Tương thích nền tảng | Envelope `schema_version: "1.1"`, RPC wire `contract_version: "1.0.1"` |
| Feature | **Learning Assessment & Adaptive Revision (F2)** |
| Trạng thái | **Runtime B2–B7 và contract assessment 1.0.0; màn hình F2 chưa triển khai** |
| Múi giờ chuẩn | `Asia/Ho_Chi_Minh` (API chuẩn hóa UTC `Z` hoặc RFC 3339 có offset) |
| Đối tượng sử dụng | Database (`app_private`/`app_api`), Backend (`backend/app/assessment/`), Orchestrator, Frontend (`frontend/src/api/`) |

Tài liệu này quy định các thực thể, trạng thái, bất biến nghiệp vụ, hợp đồng HTTP/RPC và ma trận consumer bị ảnh hưởng của Feature 2 (Learning Assessment & Adaptive Revision) theo kế hoạch triển khai B1–B7. Bộ định nghĩa máy đọc được nằm tại [contracts/schemas/f1.schema.json](../../../contracts/schemas/f1.schema.json), [contracts/assessment-openapi.yaml](../../../contracts/assessment-openapi.yaml), [contracts/service-contract.json](../../../contracts/service-contract.json) và [contracts/data-contract.json](../../../contracts/data-contract.json).

---

## 1. Quyết định kiến trúc và nguyên tắc bắt buộc

1. **Truy xuất tài liệu bằng PostgreSQL Full-Text Search:** Dùng `tsvector` với cấu hình `simple` cho tiếng Việt trên bảng `app_private.material_chunks`. Chưa dùng `pgvector` ở v1. Mọi đoạn trích xuất trả về đều phải giữ nguyên provenance `{chunk_id, material_id, page, topic, text}`.
2. **Dạng câu hỏi khách quan tất định ở v1:** Chỉ hỗ trợ trắc nghiệm một đáp án đúng (`MCQ`, 2–6 lựa chọn) và Đúng/Sai (`TRUE_FALSE`, 2 lựa chọn `TRUE`/`FALSE`). Chấm điểm tất định bằng Python thuần chỉ áp dụng cho câu hỏi đã ở trạng thái `VERIFIED`.
3. **Độc lập với Feature 3 (Daily AI Learning):** Bảng `quiz_attempts` có trường `origin` (`MANUAL` | `SESSION_HANDOFF`) và `session_outcome_id` (`UUID?`, là UUID trơn không gắn khóa ngoại ở v1). Chưa mở endpoint nhận handoff tự động từ F3 ở v1.
4. **Ranh giới tin cậy và xác thực (kế thừa F1):**
   - `user_id` chỉ lấy từ JWT đã xác thực ở server; không bao giờ nhận `user_id` từ body/query của client hay output của model.
   - Mọi thao tác ghi đi qua RPC `app_api.*` (`SECURITY DEFINER`, owner `sf_rpc_owner`, `FORCE RLS`, kiểm tra `auth.uid()` và chữ ký HMAC attestation từ FastAPI). Truy cập tài nguyên của người dùng khác trả `404 ENTITY_NOT_FOUND` giống hệt ID không tồn tại.
   - Lỗi nghiệp vụ trả `ErrorResult` / `OrchestratorReply` có cấu trúc, không dùng exception để rollback trạng thái domain hợp lệ; luôn validate đầy đủ trước khi ghi.
5. **Chuẩn hóa output mô hình và cổng xác nhận `/v1/decisions`:**
   - Output của DeepSeek là dữ liệu không tin cậy, phải được parse và chuẩn hóa nghiêm ngặt ở server; câu hỏi thiếu `source_chunk_ids` hợp lệ hoặc có `answer_key` không khớp `options[].option_id` bị loại bỏ ngay, không lưu vào database.
   - Câu hỏi mới sinh chỉ có trạng thái `DRAFT` và đi kèm một `PendingAction`. Chỉ `POST /v1/decisions` với `action_reference` nguyên vẹn mới chuyển câu hỏi từ `DRAFT` sang `VERIFIED` (hoặc `REJECTED`). Chat không bao giờ tự duyệt.
   - Bản ghi `VERIFIED` là bất biến (immutable). Muốn sửa nội dung phải tạo bản ghi câu hỏi mới.
6. **Không tự ý ghi đè lịch học đã xác nhận:**
   - Gợi ý ôn tập (`RevisionRecommendation`) bắt buộc kèm bằng chứng (`attempt_ids`, `chunk_ids`, số câu hợp lệ, số câu sai, tỷ lệ lỗi) và giới hạn độ tin cậy (`confidence_limit`).
   - Gửi gợi ý sang Planner chỉ tạo đề xuất khối lượng công việc (`PendingAction` / `TaskCandidate`) chờ sinh viên xác nhận qua `/v1/decisions`; tuyệt đối không ghi thẳng vào `StudyPlan` hay `StudyBlock`.

---

## 2. Mô hình thực thể, trạng thái và bất biến

Mọi đối tượng chuẩn hóa đều đóng (`additionalProperties: false`), dùng `snake_case`, UUID v4 và chuỗi thời gian RFC 3339 có offset.

### 2.1. `LearningMaterial` — Tài liệu học tập đã nạp (`app_private.materials`)

```text
assessment_version: "1.0.0"
material_id: UUID
user_id: UUID
conversation_id: UUID
filename: string                      # 1..255 ký tự, không chứa '/', '\' hoặc ký tự điều khiển
mime_type: text/plain | text/markdown | application/pdf
size_bytes: integer                   # 1..10485760 (tối đa 10 MiB sau giải mã)
sha256: string                        # 64 ký tự hex chữ thường
page_count: integer >= 1
char_count: integer >= 1
topics: string[]                      # 1..50 chủ đề duy nhất, không rỗng
status: UPLOADED | READY | FAILED
error_code: INVALID_PARAMETER | SERVICE_UNAVAILABLE | INTERNAL_ERROR | null
created_at: timestamp
updated_at: timestamp
```

- **Chuyển trạng thái:** `UPLOADED -> READY | FAILED`.
- **Bất biến:**
  - `topics` phải được người dùng cung cấp khi tải lên hoặc xác nhận rõ ràng; không tự lấy nhãn do LLM sinh làm dữ liệu chính thức nếu chưa xác nhận.
  - Khi `status = READY`: `error_code` phải là `null`, `page_count >= 1`, `char_count >= 1` và có ít nhất 1 `MaterialChunk` thuộc tài liệu.
  - Khi `status = FAILED`: `error_code` khác `null`.
  - Nội dung văn bản và provenance không bị thay đổi sau khi tài liệu đạt `READY`.

### 2.2. `MaterialChunk` — Đoạn văn bản phục vụ truy xuất (`app_private.material_chunks`)

```text
chunk_id: UUID
material_id: UUID
user_id: UUID
page: integer >= 1
topic: string                         # khớp một chủ đề của tài liệu
chunk_index: integer >= 0             # thứ tự đoạn trong tài liệu, duy nhất theo material_id
text: string                          # 1..4000 ký tự
created_at: timestamp
```

- **Bất biến:**
  - Tham chiếu cùng chủ sở hữu `(user_id, material_id) -> app_private.materials(user_id, material_id)`.
  - `UNIQUE(material_id, chunk_index)`.
  - Bảng vật lý lưu thêm cột `search_vector tsvector generated always as (to_tsvector('simple', text)) stored` và chỉ mục GIN để truy xuất tiếng Việt tất định.
  - Bất biến sau khi tạo; mọi kết quả `search_material_chunks` đều trả đầy đủ `{chunk_id, material_id, page, topic, chunk_index, text}`.

### 2.3. `QuestionDraft` — Câu hỏi trắc nghiệm nháp / đã xác minh (`app_private.question_drafts`)

```text
assessment_version: "1.0.0"
question_id: UUID
user_id: UUID
conversation_id: UUID
material_id: UUID
version: integer >= 1
topic: string
question_type: MCQ | TRUE_FALSE
stem: string                          # nội dung câu hỏi, không rỗng
options: QuestionOption[]             # 2..6 lựa chọn {option_id, text}
answer_key: string                    # phải khớp đúng một option_id trong options
explanation: string?
source_chunk_ids: UUID[]              # 1..10 chunk_id duy nhất làm căn cứ
status: DRAFT | VERIFIED | REJECTED
model: string?
prompt_version: string                # ví dụ "f2-question-v1"
verified_at: timestamp?
created_at: timestamp
updated_at: timestamp
```

Trong đó mỗi phần tử `QuestionOption` có cấu trúc:

```text
option_id: string                     # không rỗng, duy nhất trong cùng câu hỏi
text: string                          # nội dung lựa chọn, không rỗng
```

- **Chuyển trạng thái:**
  - Khởi tạo ở `DRAFT` (`verified_at = null`) thông qua `POST /v1/assessment/drafts` kèm `PendingAction`.
  - Chuyển `DRAFT -> VERIFIED` (`verified_at != null`) hoặc `DRAFT -> REJECTED` (`verified_at = null`) **chỉ** khi người dùng gửi quyết định qua `POST /v1/decisions` với `action_reference` nguyên vẹn.
- **Bất biến:**
  - `options` phải có các `option_id` phân biệt đôi một; `answer_key` bắt buộc thuộc tập `{o.option_id | o in options}`.
  - Nếu `question_type = TRUE_FALSE`: `options` phải có đúng 2 phần tử với `option_id` là `"TRUE"` và `"FALSE"`.
  - `source_chunk_ids` phải có ít nhất 1 UUID, không trùng lặp và thuộc cùng `(user_id, material_id)`.
  - Câu hỏi do model sinh ra nếu thiếu `source_chunk_ids` hoặc `answer_key` không nằm trong `options` thì bị loại bỏ ngay ở tầng chuẩn hóa, không bao giờ được lưu thành `DRAFT`.
  - `status = VERIFIED` khi và chỉ khi `verified_at != null`.
  - Khi đã ở `VERIFIED`, các trường nội dung (`material_id`, `topic`, `question_type`, `stem`, `options`, `answer_key`, `explanation`, `source_chunk_ids`) là **bất biến**. Mọi chỉnh sửa nội dung phải tạo bản ghi `QuestionDraft` mới ở trạng thái `DRAFT`.

### 2.4. `QuizAttempt` — Lượt làm bài kiểm tra (`app_private.quiz_attempts`)

```text
assessment_version: "1.0.0"
attempt_id: UUID
user_id: UUID
material_id: UUID
origin: MANUAL | SESSION_HANDOFF
session_outcome_id: UUID?             # null khi origin=MANUAL; UUID khi origin=SESSION_HANDOFF
status: IN_PROGRESS | SUBMITTED
question_ids: UUID[]                  # 1..50 question_id duy nhất, tất cả phải là VERIFIED
total_questions: integer              # bằng len(question_ids)
valid_response_count: integer >= 0
correct_count: integer >= 0
incorrect_count: integer >= 0
omitted_count: integer >= 0
score_percent: number?                # 0..100; null khi IN_PROGRESS hoặc valid_response_count = 0
started_at: timestamp
submitted_at: timestamp?
created_at: timestamp
updated_at: timestamp
```

- **Chuyển trạng thái:** `IN_PROGRESS -> SUBMITTED` (qua `POST /v1/assessment/attempts/{attempt_id}/submit`).
- **Bất biến:**
  - Tách biệt hoàn toàn khỏi bảng `question_drafts`.
  - Mọi phần tử trong `question_ids` phải tham chiếu câu hỏi thuộc cùng `(user_id, material_id)` và đang có `status = VERIFIED`. Không có bất kỳ đường nào đưa câu `DRAFT` hoặc `REJECTED` vào `QuizAttempt`.
  - Khi `origin = MANUAL` thì `session_outcome_id = null`; khi `origin = SESSION_HANDOFF` thì `session_outcome_id` bắt buộc là UUID (chưa gắn FK sang F3 ở v1).
  - `total_questions = len(question_ids)`.
  - Khi `status = IN_PROGRESS`: `submitted_at = null`, `score_percent = null`, `valid_response_count = 0`, `correct_count = 0`, `incorrect_count = 0`, `omitted_count = total_questions`.
  - Khi `status = SUBMITTED`:
    - `submitted_at != null` và `submitted_at >= started_at`.
    - `correct_count + incorrect_count = valid_response_count`.
    - `valid_response_count + omitted_count = total_questions`.
    - Nếu `valid_response_count = 0` thì `score_percent = null`; ngược lại `score_percent` nằm trong `[0, 100]`.

### 2.5. `QuizResponse` — Câu trả lời của từng câu hỏi trong lượt làm bài (`app_private.quiz_responses`)

```text
response_id: UUID
attempt_id: UUID
question_id: UUID
user_id: UUID
selected_option_id: string?           # null nếu bỏ trống
validity: VALID | OMITTED | INVALID
is_correct: boolean?                  # chỉ boolean khi validity=VALID và đã chấm; null khi OMITTED/INVALID
graded_at: timestamp?
created_at: timestamp
updated_at: timestamp
```

- **Bất biến:**
  - `UNIQUE(attempt_id, question_id)`; tham chiếu cùng chủ sở hữu tới `quiz_attempts` và `question_drafts`.
  - Câu trả lời bỏ trống (`selected_option_id = null`) có `validity = OMITTED` và `is_correct = null`.
  - Câu trả lời chọn `option_id` không tồn tại trong `options` của câu hỏi có `validity = INVALID` và `is_correct = null`.
  - **Quy tắc cốt lõi B5:** Câu trả lời `OMITTED` hoặc `INVALID` bị loại khỏi mẫu tính điểm và thống kê chủ đề; `is_correct` bắt buộc là `null`, tuyệt đối không gán `is_correct = false`.
  - Khi `validity = VALID`: `selected_option_id` khác `null`; sau khi nộp bài (`graded_at != null`), `is_correct` phải là `true` hoặc `false` dựa trên so khớp tất định `selected_option_id == question.answer_key`.

### 2.6. `TopicStatsItem` & `TopicStatsData` — Thống kê tỷ lệ lỗi theo chủ đề

```text
material_id: UUID
topic: string
status: AVAILABLE | INSUFFICIENT_DATA
valid_response_count: integer >= 0
error_count: integer >= 0
error_rate: number?                   # 0..1 khi status=AVAILABLE; null khi status=INSUFFICIENT_DATA
last_attempt_at: timestamp?
```

- **Bất biến (Quy tắc cốt lõi B6):**
  - Chỉ tính trên các `QuizResponse` có `validity = VALID` thuộc các `QuizAttempt` đã `SUBMITTED`.
  - Nếu `valid_response_count = 0`: `status` bắt buộc là `INSUFFICIENT_DATA`, `error_count = 0`, `error_rate = null`. Tuyệt đối không suy diễn thành thạo hay trả `error_rate = 0`.
  - Nếu `valid_response_count > 0`: `status` bắt buộc là `AVAILABLE`, `0 <= error_count <= valid_response_count`, và `error_rate = error_count / valid_response_count` (trong đoạn `[0, 1]`).
  - B6 đọc trực tiếp từ database qua `app_api.get_topic_stats`, không phụ thuộc cache của tiến trình chấm bài. Mỗi cặp `(material_id, topic)` của tài liệu `READY` có một dòng, kể cả khi chưa có bài làm; cùng tên chủ đề ở hai tài liệu không bị gộp.
  - `last_attempt_at` là `submitted_at` mới nhất có response hợp lệ đã chấm của chủ đề; bằng `null` khi chưa có dữ liệu hợp lệ. Bài chưa nộp và bài chỉ có `OMITTED`/`INVALID` không làm thay đổi mốc này.
  - `material_id` bị bỏ qua trả tất cả tài liệu của JWT hiện tại; người dùng chưa có tài liệu nhận `items: []`. ID tài liệu không tồn tại hoặc thuộc người khác cùng trả `404 ENTITY_NOT_FOUND`.
  - Thống kê chỉ mô tả tỷ lệ lỗi quan sát được; `AVAILABLE` không phải mức thành thạo, không sinh gợi ý B7 hay thay đổi Planner.

### 2.7. `RevisionRecommendation` — Gợi ý ôn tập có bằng chứng (`app_private.revision_recommendations`)

```text
assessment_version: "1.0.0"
recommendation_id: UUID
user_id: UUID
conversation_id: UUID
material_id: UUID
topic: string
priority: 0.1 | 0.5 | 1               # đồng nhất trọng số ưu tiên với Planner
suggested_minutes: integer            # 15..240 phút
reason_summary: string                # giải thích tiếng Việt dựa trên bằng chứng
evidence: RecommendationEvidence
confidence_limit: ConfidenceLimit
pending_action_id: UUID               # tham chiếu PendingAction chờ người dùng duyệt qua /v1/decisions
candidate_id: UUID?                   # TaskCandidate nháp chuẩn bị cho Planner
status: PROPOSED | ACCEPTED | REJECTED
created_at: timestamp
updated_at: timestamp
```

Trong đó:

```text
RecommendationEvidence:
  attempt_ids: UUID[]                 # >= 1 attempt_id đã SUBMITTED
  chunk_ids: UUID[]                   # >= 1 chunk_id nguồn liên quan
  valid_response_count: integer >= 1
  error_count: integer >= 1           # error_count <= valid_response_count
  error_rate: number                  # 0 < error_rate <= 1

ConfidenceLimit:
  level: LOW | MEDIUM | HIGH
  limitations: string[]               # >= 1 mô tả giới hạn độ tin cậy (vd cỡ mẫu nhỏ, chỉ phủ 1 phần tài liệu)
```

- **Bất biến (Quy tắc cốt lõi B7):**
  - Không bao giờ được tạo gợi ý ôn tập cho chủ đề đang ở `INSUFFICIENT_DATA` (`valid_response_count` phải `>= 1` và `error_count >= 1`).
  - Luôn đính kèm cả `evidence` (`attempt_ids`, `chunk_ids`) lẫn `confidence_limit` (`level`, `limitations`).
  - Không bao giờ ghi trực tiếp vào `StudyPlan` hay `AcademicTask`; bắt buộc gắn với `pending_action_id` để sinh viên duyệt qua `POST /v1/decisions`.

---

## 3. Hợp đồng HTTP Endpoint (`/v1/assessment`)

Tất cả các đường dẫn dùng tiền tố `/v1/assessment`, yêu cầu `Authorization: Bearer <Supabase JWT>`. Các phương thức ghi (`POST`, `PUT`) bắt buộc có header `Idempotency-Key` (`16..128` ký tự `[A-Za-z0-9._:-]`).

| Method | Path | Request Schema | Response 200 Schema | Ghi chú nghiệp vụ |
|---|---|---|---|---|
| `POST` | `/v1/assessment/materials` | `MaterialUploadRequest` | `AssessmentMaterialResult` | Tải tài liệu học tập + danh sách `topics`; trích xuất và lưu `MaterialChunk` |
| `GET` | `/v1/assessment/materials/{material_id}` | Query `conversation_id` | `AssessmentMaterialDetailResult` | Đọc metadata tài liệu, danh sách chủ đề và các chunk |
| `POST` | `/v1/assessment/drafts` | `GenerateQuestionDraftsRequest` | `OrchestratorReply` (`AWAITING_APPROVAL`) | Sinh câu hỏi nháp từ `material_id`/`topic` và tạo `PendingAction` chờ duyệt qua `/v1/decisions` |
| `GET` | `/v1/assessment/questions` | Query `material_id?`, `topic?`, `status?`, `page_size?`, `cursor?` | `QuestionDraftListResult` | Liệt kê câu hỏi theo trạng thái (`DRAFT`, `VERIFIED`, `REJECTED`) |
| `POST` | `/v1/assessment/attempts` | `CreateQuizAttemptRequest` | `QuizAttemptResult` | Tạo lượt làm bài từ các câu hỏi `VERIFIED` |
| `PUT` | `/v1/assessment/attempts/{attempt_id}/responses/{question_id}` | `SaveQuizResponseRequest` | `QuizResponseResult` | Lưu hoặc cập nhật câu trả lời khi `attempt` đang `IN_PROGRESS` |
| `POST` | `/v1/assessment/attempts/{attempt_id}/submit` | `SubmitQuizAttemptRequest` | `QuizAttemptSubmissionResult` | Chấm điểm tất định trên các câu `VERIFIED` và chốt kết quả |
| `GET` | `/v1/assessment/topics/stats` | Query `material_id?` | `TopicStatsResult` | Tính thống kê lỗi theo chủ đề; trả `INSUFFICIENT_DATA` nếu chưa có response hợp lệ |
| `POST` | `/v1/assessment/recommendations` | `CreateRevisionRecommendationRequest` | `OrchestratorReply` (`AWAITING_APPROVAL`) | Tạo gợi ý ôn tập kèm bằng chứng và đưa vào hàng đợi xác nhận `/v1/decisions` của Planner |

---

## 4. Danh mục Internal RPC (`extensions.assessment` trong `service-contract.json`)

| Routine `app_api.*` | Arguments Schema | Data Schema | Result Schema | Read-only | Attestation |
|---|---|---|---|---|---|
| `store_assessment_material` | `StoreMaterialArguments` | `AssessmentMaterialDetailData` | `AssessmentMaterialDetailResult` | `false` | `true` |
| `get_assessment_material` | `MaterialLookupArguments` | `AssessmentMaterialDetailData` | `AssessmentMaterialDetailResult` | `true` | `false` |
| `search_material_chunks` | `SearchMaterialChunksArguments` | `MaterialChunkSearchData` | `MaterialChunkSearchResult` | `true` | `false` |
| `create_question_drafts` | `CreateQuestionDraftsArguments` | `QuestionDraftBatchData` | `QuestionDraftBatchResult` | `false` | `true` |
| `verify_question_drafts` | `VerifyQuestionDraftsArguments` | `QuestionDraftBatchData` | `QuestionDraftBatchResult` | `false` | `true` |
| `list_questions` | `ListQuestionsArguments` | `QuestionDraftListData` | `QuestionDraftListResult` | `true` | `false` |
| `create_quiz_attempt` | `CreateQuizAttemptArguments` | `QuizAttempt` | `QuizAttemptResult` | `false` | `true` |
| `save_quiz_response` | `SaveQuizResponseArguments` | `QuizResponse` | `QuizResponseResult` | `false` | `true` |
| `submit_quiz_attempt` | `SubmitQuizAttemptArguments` | `QuizAttemptSubmissionData` | `QuizAttemptSubmissionResult` | `false` | `true` |
| `get_topic_stats` | `GetTopicStatsArguments` | `TopicStatsData` | `TopicStatsResult` | `true` | `false` |
| `create_revision_recommendation` | `CreateRevisionRecommendationArguments` | `ActionPresentation` | `RevisionRecommendationResult` | `false` | `true` |

---

## 5. Ma trận các consumer bị ảnh hưởng (Impact Matrix)

| Tầng / Consumer | File bị ảnh hưởng | Thay đổi trong B1 | Công việc tiếp theo (B2–B7 / FE) |
|---|---|---|---|
| **Domain Docs** | `docs/features/assessment/schema.md`, `docs/features/assessment/README.md`, `contracts/ASSESSMENT.md` | Đặc tả thực thể, trạng thái, bất biến, HTTP/RPC contract và ranh giới bảo mật F2 | Giữ đồng bộ khi tinh chỉnh ngưỡng kích thước tài liệu ở B2 |
| **JSON Schema & OpenAPI** | `contracts/schemas/f1.schema.json`, `contracts/assessment-openapi.yaml`, `contracts/openapi.yaml` | Thêm toàn bộ `$defs` cho F2 (`1.0.0`) và 9 endpoint `/v1/assessment/*` | Dùng trực tiếp để validate request/response |
| **Contract Registries & Checker** | `contracts/service-contract.json`, `contracts/data-contract.json`, `contracts/check_contract.py`, `contracts/examples/*` | Đăng ký `extensions.assessment` (`1.0.0`), kiểm tra bất biến ngữ nghĩa thuần và bộ mẫu valid/invalid | Dùng trong CI cổng contract |
| **Database Contract Migration** | `backend/scripts/generate_contract_schema_migration.py`, `supabase/migrations/202611160001_f2_b1_assessment_contract_schema.sql` | Đóng gói `$defs` mới vào `app_private.contract_defs()` qua migration mới | B2–B7 tạo bảng vật lý và RPC `app_api.*` gọi `app_private.matches_contract(...)` |
| **Backend Handlers** | `backend/app/core/contract.py` (tự động đọc `f1.schema.json`); tương lai: `backend/app/assessment/*`, `backend/app/api/v1/routes.py`, `backend/app/orchestrator/actions.py` | Đã có validator `contract.is_valid(...)` cho mọi schema F2 | B2 (material/chunk), B3–B4 (draft/verify), B5 (attempt/grading), B6 (stats), B7 (recommendation) |
| **Frontend Types & API Client** | `frontend/src/api/types.ts`, `frontend/src/api/endpoints.ts` | Bổ sung đầy đủ TypeScript DTOs cho F2 `1.0.0` và 9 hàm gọi endpoint `/v1/assessment/*` | FE dùng trực tiếp để mock UI làm bài trắc nghiệm, duyệt câu hỏi và xem thống kê |
| **Tests** | `backend/tests/unit/test_assessment_contract.py`, `frontend/src/api/assessment.test.ts` | Kiểm tra đóng/mở schema, chống owner injection, kiểm tra bất biến chấm điểm/thống kê và client FE | B2–B7 bổ sung unit tests nghiệp vụ, pgTAP và integration tests |


## B7 runtime addendum

The latest implementation is described in README.md. Recommendations use at most
50 latest eligible submitted attempts, not B6 lifetime totals; source citations are
capped at 50 distinct wrong-answer chunks. LOW confidence is always used in v1.
PROPOSED/REJECTED have no candidate; ACCEPTED references a DRAFT/CONFIRMED/CANCELLED
F1 candidate. Acceptance is a handoff, not task or plan confirmation.
