# Hướng dẫn triển khai Database StudyFlow AI bằng Supabase và Codex

> Bản Markdown của hướng dẫn triển khai đã trao đổi trong cuộc trò chuyện. Giữ nguyên các bước, ví dụ, checklist và prompt Codex; đây là hướng dẫn kỹ thuật đề xuất, không tự biến các lựa chọn TBD thành quyết định đã được nhóm phê duyệt.

## 1. Trước tiên, hiểu đúng vai trò database của bạn

Mục tiêu là xây dựng hoàn chỉnh tầng Database cho F1 MVP bằng Supabase PostgreSQL, sau đó tích hợp với Backend FastAPI thông qua ORM và Repository Pattern.

Theo cấu trúc repository đã gửi, database nằm trong phạm vi:

| Thành phần | Trách nhiệm |
|---|---|
| `backend/app/db/orm/` | Định nghĩa ORM models |
| `backend/app/db/repositories/` | Truy vấn và thao tác dữ liệu |
| Migration | Quản lý phiên bản cấu trúc database |
| Supabase PostgreSQL | Lưu trữ dữ liệu thực tế |
| RLS Policies | Kiểm soát quyền truy cập từng user |
| Database tests | Kiểm thử constraint, RLS và tính toàn vẹn |
| Seed data | Dữ liệu mẫu phục vụ development/test |

`contracts/` vẫn là nguồn sự thật chung cho hai nhóm; không tự thay đổi API contract mà chưa review.

### 1.1. Database cần lưu những gì?

Với F1 MVP, các nhóm dữ liệu được đề xuất:

- Supabase Auth: authenticated user identity, UUID.
- Academic Tasks: task, deadline, workload, priority, draft/confirmed.
- Availability: available intervals, weekday, recurrence.
- Study Plans: proposed, confirmed, version, approval.
- Study Blocks: task allocation, start/end, duration.
- Pending Actions: multi-turn context, state, expiry.
- Approval Events: user, proposal, version, decision, idempotency.
- Source Documents: metadata và tham chiếu đến PDF được người dùng tải lên, phục vụ F1 text extraction.

Đây là mô hình đề xuất cho F1. `FixedCommitment` và một số quy tắc availability vẫn cần nhóm chốt trước khi freeze schema.

Ba nguyên tắc tuyệt đối phải giữ:

1. Task chưa xác nhận không được đưa vào scheduler.
2. StudyPlan ở trạng thái `PROPOSED` không được xem là lịch chính thức.
3. Chỉ sau khi user approval hợp lệ, Backend revalidate và commit thành công thì lịch mới được chuyển sang `CONFIRMED`.

## 2. Kiểm tra Supabase hiện tại

Ảnh Dashboard được người dùng cung cấp cho thấy project Supabase đã có:

- Publishable key: `sb_publishable_...`
- Secret key: `sb_secret_...`
- Project `StudyFlow AI`.

Lưu ý:

| Thành phần | Cách sử dụng |
|---|---|
| Publishable key | Có thể đưa vào frontend khi đã cấu hình RLS đầy đủ |
| Secret key | Chỉ dùng trong môi trường server được kiểm soát; bypass RLS |
| Database password | Dùng để kết nối PostgreSQL qua connection string |
| Project URL | Địa chỉ project Supabase |

Secret key không phải database password. Không đưa secret key vào prompt cho Codex và không commit vào GitHub.

Supabase có hệ thống publishable/secret keys thay cho hệ thống key legacy `anon`/`service_role`; Dashboard đã hiển thị thông báo legacy keys dự kiến bị retire vào đầu năm 2027.

Kiến trúc đề xuất: Frontend gọi FastAPI; FastAPI xử lý authentication, authorization và business logic; PostgreSQL trên Supabase lưu dữ liệu. Không để frontend tự ý ghi trực tiếp vào các bảng nghiệp vụ nếu chưa có thiết kế quyền riêng.

## 3. Chuẩn bị môi trường làm việc

### Bước 1 — Mở repository bằng Codex

Mở thư mục gốc `studyflow-ai/` trong VS Code, sau đó mở Codex.

Không nên làm trực tiếp trên `main`. Tạo nhánh riêng cho phần database:

```bash
git status
git switch -c feat/database-supabase
```

Nếu repository đang có thay đổi chưa commit, kiểm tra và bảo toàn trước khi chuyển nhánh.

### Bước 2 — Đưa tài liệu vào repository

Đề xuất đặt tài liệu như sau:

```text
studyflow-ai/
├── docs/
│   └── srs/
│       ├── StudyFlow_AI_SRS_v1.0_Draft.pdf
│       └── StudyFlow_AI_SRS_v1.0_Draft.md
├── contracts/
├── backend/
├── frontend/
└── README.md
```

Bản Markdown là tài liệu tiện nhất cho Codex đọc và đối chiếu yêu cầu; PDF dùng để tra cứu và review.

### Bước 3 — Kiểm tra môi trường Supabase CLI

Trên Windows, mở PowerShell tại thư mục gốc của project. Kiểm tra:

```powershell
node --version
npm --version
docker --version
```

Supabase CLI hiện yêu cầu Node.js 20 trở lên khi chạy qua npm/npx. Local Supabase cần Docker Desktop hoặc container runtime tương thích.

Có thể thử:

```powershell
npx supabase@latest --version
```

Đây là cách thử CLI mà chưa phải thiết lập một binary toàn hệ thống. Khi nhóm đã thống nhất cách quản lý phiên bản CLI, nên pin phiên bản dùng chung.

### Bước 4 — Khởi tạo Supabase trong repository

Chạy tại thư mục gốc:

```powershell
npx supabase@latest init
```

Nếu đã tồn tại thư mục `supabase/`, không khởi tạo lại.

Cấu trúc được tạo sẽ có dạng:

```text
studyflow-ai/
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── backend/
├── frontend/
├── contracts/
└── docs/
```

Theo hướng dẫn Supabase, `supabase/migrations/` là nơi quản lý các SQL migration theo thứ tự thời gian; đây là các thay đổi database được đưa vào Git để các thành viên tái tạo cùng một schema.

Một điểm cần thống nhất với Backend Developer: Repo structure PDF của nhóm đang đặt `migrations/` trong `backend/app/db/`. Nếu sử dụng Supabase CLI, nên dùng `supabase/migrations/` làm nguồn migration duy nhất; còn `backend/app/db/orm/` chứa ORM models và `repositories/` chứa các thao tác truy vấn.

Không duy trì hai bộ migration cùng chỉnh sửa một schema, vì dễ xảy ra tình trạng database local và remote không đồng bộ.

## 4. Kiểm tra và kết nối project Supabase

### Bước 5 — Xác định đúng project và môi trường

Trong Dashboard, project đang hiển thị nhánh `main (PRODUCTION)`.

Không dùng database production để thử nghiệm migration liên tục.

| Môi trường | Mục đích |
|---|---|
| Local Supabase | Phát triển schema, migration, test |
| Development/Staging | Tích hợp và kiểm thử cho cả nhóm |
| Production (`main`) | Chỉ cập nhật sau khi đã review và kiểm thử |

Có thể dùng local Supabase làm bước đầu nếu nhóm chưa có project development riêng.

### Bước 6 — Lấy Database Connection String

Trong Dashboard, mở nút **Connect** của project, sau đó chọn phần connection string.

Cần lấy:
- Host.
- Port.
- Database name.
- Database username.
- Database password.
- Connection string hoàn chỉnh.

Ví dụ minh họa:

```text
postgresql://postgres:YOUR_PASSWORD@HOST:5432/postgres
```

Đây chỉ là cấu trúc minh họa, không phải thông tin kết nối thật.

Chọn connection mode phù hợp. Với backend FastAPI chạy lâu dài, direct connection phù hợp khi môi trường mạng hỗ trợ IPv6; nếu máy chủ chỉ có IPv4, có thể sử dụng shared pooler ở session mode. Transaction mode thường phù hợp với workload tạo nhiều kết nối ngắn hạn.

### Bước 7 — Lưu thông tin môi trường

Tạo file `.env` ở vị trí mà Backend Developer thống nhất, ví dụ:

```env
DATABASE_URL=postgresql://...

SUPABASE_URL=https://YOUR_PROJECT.supabase.co

SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Nếu thực sự cần thao tác quản trị bằng API, secret key sẽ được lưu riêng trong môi trường server:

```env
SUPABASE_SECRET_KEY=sb_secret_...
```

Trong mô hình Backend FastAPI dùng SQLAlchemy kết nối thẳng PostgreSQL, `DATABASE_URL` mới là thông tin kết nối DB chính; không lấy `sb_publishable` hoặc `sb_secret` thay thế cho database password.

Thêm vào `.gitignore`:

```gitignore
.env
.env.*
!.env.example

supabase/.temp/
```

Tạo `.env.example` chỉ chứa tên biến và placeholder:

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
```

Không gửi giá trị thực của các biến này vào prompt Codex, GitHub, ảnh chụp màn hình hoặc commit.

## 5. Làm việc với Codex — thứ tự prompt

Không nên đưa một prompt khổng lồ kiểu "hãy tạo toàn bộ database". Hãy để Codex làm từng lớp, có kiểm tra sau mỗi lớp.

### Giai đoạn A — Audit repository và phân tích database

**Prompt 01 — Chỉ đọc, không sửa file**

```text
You are a Senior Database Architect and PostgreSQL Engineer working on StudyFlow AI.

I am responsible for the database layer. The project uses Supabase PostgreSQL as its managed database platform.

Your first task is to conduct a READ-ONLY audit of the existing repository.

## Source materials

Read and analyze:
1. `docs/srs/StudyFlow_AI_SRS_v1.0_Draft.md`
2. `contracts/` including all JSON Schemas, `openapi.yaml`, examples, and `CHANGELOG.md`.
3. The existing backend structure and implementation.
4. `README.md` and existing technical documentation.

If any file is missing, report it. Do not invent its contents.

## Repository architecture

Respect the existing structure:

- `contracts/`: shared contract source of truth.
- `backend/app/db/orm/`: database ORM models.
- `backend/app/db/repositories/`: database access layer.
- `backend/app/f1/`: F1 domain logic.
- `backend/app/core/auth.py`: trusted authenticated user context.
- `backend/tests/`: unit, integration, contract, workflow, and security tests.

Supabase CLI migrations may be managed under the root `supabase/migrations/` directory. Check whether another migration system already exists before recommending this.

## Audit tasks

1. Inspect existing database-related dependencies.
2. Identify whether SQLAlchemy, Alembic, psycopg, asyncpg, or supabase-py is already installed.
3. Inspect existing ORM models, repositories, database sessions, and configuration.
4. Check whether a Supabase project configuration or migration directory already exists.
5. Identify existing database tables, naming conventions, ID formats, and timestamp conventions.
6. Inspect authentication and determine how trusted `user_id` reaches backend services.
7. Compare the existing implementation with the SRS data model.
8. Identify missing entities, fields, indexes, foreign keys, constraints, RLS policies, and transaction requirements.
9. Identify inconsistencies between database models and shared contracts.
10. Identify whether the proposed database architecture supports approval, revalidation, concurrency, and idempotency.

## Security requirements

- Never open, print, or expose `.env` files or credential values.
- Never print database URLs, passwords, API keys, or JWT secrets.
- Do not execute remote database commands.
- Do not create or modify any files.
- Do not invent implemented features from design documents.

## Output

Produce a detailed database audit report containing:

A. Existing database architecture.
B. Current dependency inventory.
C. Existing entities and relationships.
D. Missing database components.
E. Recommended F1 MVP database schema.
F. Migration strategy.
G. Authentication and RLS strategy.
H. Potential architecture conflicts.
I. Implementation order.
J. Decisions requiring backend-team approval.

For every finding, distinguish:
- CONFIRMED FROM CODE
- CONFIRMED FROM DOCUMENTS
- PROPOSED
- TBD

Stop after presenting the report. Do not modify the repository.
```

**Kết quả cần nhận:** một báo cáo audit xác định được nên dùng SQLAlchemy hay Supabase Python SDK, đang có migration engine nào, và có những bảng nào cần tạo.

### Giai đoạn B — Thiết kế database và ERD

**Prompt 02 — Thiết kế trước khi code**

```text
Act as a Senior PostgreSQL Database Architect.

Based on the repository audit and the StudyFlow AI SRS, design the database schema for the F1 Initial MVP using Supabase PostgreSQL.

Do not implement or edit files yet.

## 1. Scope

The F1 MVP includes:
- Manual task entry.
- Candidate task extraction from authorized text-based PDFs.
- Student confirmation of task details.
- Availability management.
- Weekly automatic study planning.
- Study plan proposal and retrieval.
- Student-approved rescheduling.
- Multi-turn workflow state persistence where required.

Do not implement F2/F3 database features in this phase.

## 2. Proposed entities to evaluate

Evaluate the following entities:

1. AcademicTask.
2. Course, if a normalized course record is necessary.
3. Availability.
4. StudyPlan.
5. PlannedStudyBlock.
6. PendingAction.
7. ApprovalEvidence / ApprovalEvent.
8. SourceDocument.
9. UserSettings / timezone preferences, if required.

FixedCommitment is an unresolved design decision. Do not silently make it a mandatory entity. Propose alternatives for representing existing busy intervals and explain their consequences.

## 3. AcademicTask

Preserve the project vocabulary:

- task_id
- course_id
- title
- start_date
- deadline
- estimated_minutes
- remaining_minutes
- priority

Support the lifecycle:
DRAFT → CONFIRMED

Only confirmed tasks are eligible for automatic scheduling.

Evaluate whether a single `academic_tasks` table with a status column is preferable to separate candidate and confirmed-task tables. Explain the trade-offs and recommend one option.

## 4. StudyPlan and PlannedStudyBlock

Support:

- Multiple blocks in one plan.
- A task distributed across multiple blocks.
- PROPOSED and CONFIRMED plan status.
- Versioning.
- Unscheduled work.
- Proposal expiration.
- Student approval.
- Revalidation before commit.

Use `timestamptz` for actual time instants and preserve the user's IANA timezone where needed.

## 5. Availability

Support the preliminary requirements for:
- Date-specific availability.
- Weekday availability.
- NONE/WEEKLY recurrence where approved.

Clearly identify unresolved recurrence validity periods, exceptions, and overnight interval rules.

## 6. Constraints

Propose database constraints for:
- Valid task date ranges.
- Positive estimated workload.
- Remaining workload within estimated workload.
- Valid study-block time intervals.
- Referential integrity.
- Cross-user ownership.
- Unique idempotency keys.
- Version consistency.

Use half-open intervals `[start, end)` for schedule conflict semantics.

## 7. Security

Every user-owned record must have an ownership model.

Evaluate:
- `user_id` references to `auth.users`.
- Row Level Security.
- Least-privilege grants.
- Foreign keys.
- Indexes for ownership queries.
- Cross-user reference prevention.

Do not assume `auth.uid()` automatically works for a direct SQLAlchemy database connection. Explain the distinction between Supabase Data API requests and direct PostgreSQL connections.

Do not design authorization around an LLM-provided user_id.

## 8. Deliverables

Provide:

1. Entity relationship diagram in Mermaid.
2. Complete table-by-table data dictionary.
3. Primary keys and foreign keys.
4. Cardinality.
5. Check constraints.
6. Unique constraints.
7. Recommended indexes.
8. Proposed RLS policies.
9. Data lifecycle definitions.
10. Migration dependency order.
11. Seed data requirements.
12. A list of all unresolved decisions.

For each design element, mark CONFIRMED, PROPOSED, or TBD.

Do not generate SQL or edit any repository file yet.
```

**Cần review kỹ:** `course_id`, mô hình availability recurrence và cách lưu FixedCommitment. Đây là những điểm có thể khiến cả hệ thống phải đổi schema sau này.

### Giai đoạn C — Thiết lập migration và tạo database schema

**Prompt 03 — Database migrations**

Trước khi chạy migration, thiết lập local Supabase:

```powershell
# Xác thực Supabase CLI
npx supabase@latest login

# Khởi chạy các service local
npx supabase@latest start
```

Local stack cho phép kiểm thử PostgreSQL, Auth và Storage mà chưa đụng đến production.

Tạo migration đầu tiên:

```powershell
npx supabase@latest migration new create_f1_core_schema
```

Cấu trúc được kỳ vọng:

```text
supabase/
├── config.toml
├── migrations/
│   └── <timestamp>_create_f1_core_schema.sql
└── seed.sql
```

Prompt cho Codex:

```text
You are now implementing the approved StudyFlow AI F1 MVP PostgreSQL schema.

Use the database design that has been reviewed and approved by the team.

## Implementation rules

1. Use Supabase PostgreSQL.
2. Use Supabase CLI migrations as the single schema migration source if this strategy was approved.
3. Preserve the existing repository architecture.
4. Do not create a second competing migration system.
5. Do not connect to or modify the production Supabase project.
6. Do not read or output secrets.
7. Never make destructive changes to existing tables or records.
8. Keep all schema changes reproducible from migration files.

## Schema implementation

Implement the approved versions of:

- academic_tasks
- courses, if approved
- availability records
- study_plans
- planned_study_blocks
- pending_actions
- approval_events
- source_documents
- user_settings, if approved

Do not create fixed_commitments until the team approves its data model.

## Required database properties

Use:
- UUID primary keys where approved.
- Foreign keys with explicit deletion behavior.
- NOT NULL for mandatory fields.
- CHECK constraints for numeric and date validity.
- UNIQUE constraints for idempotency and natural uniqueness where justified.
- Explicit enum or CHECK-based status definitions.
- TIMESTAMPTZ for absolute timestamps.
- DATE for date-only academic deadlines.
- JSONB only for genuinely flexible structured payloads.
- Created/updated timestamps where required.

AcademicTask must support DRAFT and CONFIRMED states.

Only CONFIRMED tasks can be used by the scheduler.

StudyPlan must support the approved proposal and confirmation lifecycle.

PlannedStudyBlock must reference the appropriate StudyPlan and AcademicTask.

An approval event must be tied to:
- authenticated user
- exact plan
- exact plan version
- decision
- timestamp
- idempotency key or equivalent approved mechanism

Do not store a simple `approval=true` field as the complete approval evidence.

## Scheduling-related integrity

Implement the approved validity constraints.

Use half-open intervals `[start, end)`.

The overlap condition is:

start_A < end_B AND start_B < end_A

Prevent invalid start/end intervals.

Do not move scheduling algorithms into PostgreSQL triggers or LLM calls.

The scheduler remains a deterministic backend domain component.

## Ownership and referential integrity

Use the approved ownership model.

Where appropriate:
- user-owned data references `auth.users(id)`.
- Child entities cannot reference another user's parent entity.
- Index user ownership columns.
- Index foreign keys and frequently queried deadline/planning fields.
- Ensure deletion behavior does not unexpectedly remove confirmed academic records.

## Migration quality

The migration must:
- Be idempotent where appropriate.
- Avoid unnecessary destructive statements.
- Define constraints and indexes explicitly.
- Include RLS and grants only according to the approved access design.
- Be understandable and maintainable.
- Work from a clean local Supabase instance.

## Additional deliverables

Generate:
1. SQL migration file(s).
2. Updated ORM models, only if this phase includes ORM work.
3. Database data dictionary.
4. Schema-to-SRS field mapping.
5. Migration README.
6. Updated ERD.
7. A list of decisions that still prevent implementation.

Before finishing, show:
- Files created or modified.
- Tables created.
- Fields and constraints.
- Foreign key relationships.
- RLS status.
- Indexes.
- Commands for local verification.

Do not apply migrations to remote databases.
```

Các bảng cần review kỹ sau khi Codex tạo:

#### `academic_tasks`

| Column | Data type | Ý nghĩa |
|---|---|---|
| id | UUID | Task ID |
| user_id | UUID | Chủ sở hữu |
| course_id | UUID, nullable/TBD | Môn học |
| title | TEXT | Tên task |
| start_date | DATE | Ngày bắt đầu |
| deadline | DATE | Hạn hoàn thành |
| estimated_minutes | INTEGER | Tổng thời gian dự kiến |
| remaining_minutes | INTEGER | Thời gian còn lại |
| priority | INTEGER hoặc enum | Độ ưu tiên |
| status | ENUM/CHECK | DRAFT / CONFIRMED |
| source_document_id | UUID, nullable | Nguồn PDF |
| created_at | TIMESTAMPTZ | Thời điểm tạo |
| updated_at | TIMESTAMPTZ | Thời điểm cập nhật |

Các ràng buộc ví dụ:

```sql
CHECK (start_date <= deadline)
CHECK (estimated_minutes > 0)
CHECK (
    remaining_minutes >= 0
    AND remaining_minutes <= estimated_minutes
)
```

Không tự chọn thang priority 1–5 nếu nhóm chưa thống nhất.

#### `availability_slots`

| Column | Data type | Ý nghĩa |
|---|---|---|
| id | UUID | Availability ID |
| user_id | UUID | Chủ sở hữu |
| availability_date | DATE, nullable | Ngày cụ thể |
| weekday | SMALLINT, nullable | Thứ trong tuần |
| start_time | TIME | Bắt đầu |
| end_time | TIME | Kết thúc |
| timezone | TEXT | Múi giờ |
| recurrence_type | ENUM/CHECK | NONE / WEEKLY |
| effective_from | DATE, nullable | Ngày bắt đầu hiệu lực |
| effective_until | DATE, nullable | Ngày kết thúc hiệu lực |

Đây là thiết kế đề xuất. Codex phải đảm bảo một record không đồng thời vừa là lịch ngày cụ thể, vừa là lịch lặp tuần. Nhóm vẫn cần chốt hiệu lực của recurrence.

#### `study_plans`

| Column | Ý nghĩa |
|---|---|
| id | Plan ID |
| user_id | Chủ sở hữu |
| planning_start_date | Ngày đầu kỳ lập lịch |
| planning_end_date | Ngày cuối kỳ lập lịch |
| status | PROPOSED / CONFIRMED và các trạng thái đã duyệt |
| version | Phiên bản |
| input_fingerprint | Dấu vết dữ liệu đầu vào dùng để tạo proposal |
| approved_at | Thời điểm phê duyệt |
| created_at | Thời điểm tạo |

#### `planned_study_blocks`

| Column | Ý nghĩa |
|---|---|
| id | Block ID |
| user_id | Chủ sở hữu |
| plan_id | StudyPlan liên quan |
| task_id | Task được phân bổ |
| start_at | Thời điểm bắt đầu |
| end_at | Thời điểm kết thúc |
| duration_minutes | Thời lượng |
| created_at | Thời điểm tạo |

#### `approval_events`

Bảng này ghi nhận việc user chấp nhận hoặc từ chối proposal, không chỉ đơn thuần thay đổi trạng thái plan.

Các trường nên có: `id`, `user_id`, `plan_id`, `plan_version`, `decision`, `idempotency_key`, `created_at`.

#### `pending_actions`

Lưu trạng thái xử lý hội thoại nhiều lượt, chẳng hạn user nói:

- "Xếp tao hai tiếng OOP tối mai."
- Hệ thống hỏi: "Bạn muốn bắt đầu lúc mấy giờ?"
- User trả lời: "19h."

Hệ thống phải biết `19h` thuộc đúng pending action đang chờ, không tạo một yêu cầu độc lập.

### ERD logic đề xuất

```mermaid
erDiagram
    AUTH_USERS ||--o{ ACADEMIC_TASKS : owns
    AUTH_USERS ||--o{ AVAILABILITY_SLOTS : defines
    AUTH_USERS ||--o{ STUDY_PLANS : owns
    AUTH_USERS ||--o{ PENDING_ACTIONS : owns

    ACADEMIC_TASKS ||--o{ PLANNED_STUDY_BLOCKS : allocated_to
    STUDY_PLANS ||--o{ PLANNED_STUDY_BLOCKS : contains

    STUDY_PLANS ||--o{ APPROVAL_EVENTS : receives
    AUTH_USERS ||--o{ APPROVAL_EVENTS : performs
    SOURCE_DOCUMENTS ||--o{ ACADEMIC_TASKS : supports
```

ERD là định hướng. Relationships phải được điều chỉnh theo schema đã được nhóm duyệt; `SOURCE_DOCUMENTS` và cách liên kết `courses` vẫn cần xác nhận.

### Giai đoạn D — Cấu hình Row Level Security (RLS)

**Prompt 04 — Bắt buộc kiểm thử bảo mật**

Ví dụ policy ban đầu cho `academic_tasks`:

```sql
ALTER TABLE public.academic_tasks
ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their tasks"
ON public.academic_tasks
FOR SELECT
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can create their tasks"
ON public.academic_tasks
FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT auth.uid()) = user_id
);
```

Đây mới là ví dụ ban đầu. Phải bổ sung policy UPDATE, quyền truy cập chính xác và các kiểm thử tương ứng.

RLS policy và GRANT là hai lớp khác nhau. Cần cấu hình quyền cho từng operation và tạo test RLS cho cả trường hợp cho phép và từ chối.

```text
Act as a PostgreSQL Security Engineer specializing in Supabase Row Level Security.

Review and implement the approved RLS security model for StudyFlow AI F1 MVP.

## Main objective

Ensure each authenticated student can only access their own authorized records.

## Tables

Review every user-owned table created in the previous migration phase.

At minimum, evaluate:
- academic_tasks
- availability_slots
- study_plans
- planned_study_blocks
- pending_actions
- approval_events
- source_documents
- user_settings, if implemented

## Required security behavior

1. An unauthenticated user must not access private academic records.
2. User A must read only User A's tasks.
3. User A must not insert a record with User B's user_id.
4. User A must not update User B's records.
5. User A must not delete User B's records.
6. A child record must not reference another user's parent entity.
7. A user must not change a record's ownership through UPDATE.
8. Approval records must not be forged by client-controlled fields.
9. Users must not directly write CONFIRMED schedule changes without the approved backend workflow.
10. All policies must match the actual application's access model.

## Supabase-specific requirements

- Enable RLS on every exposed user-owned table.
- Configure table grants using least privilege.
- Write explicit policies for SELECT, INSERT, UPDATE, and DELETE when each operation is supported.
- Use `TO authenticated` or the appropriate approved role.
- Use `auth.uid()` only where a verified Supabase Auth JWT is actually available.
- Add indexes on policy-filtering columns.
- Avoid unnecessary SECURITY DEFINER functions.
- Do not expose secret keys.
- Do not assume a direct PostgreSQL connection automatically enforces the same auth.uid() context as a Supabase Data API request.

## Critical integration check

Inspect how FastAPI connects to PostgreSQL.

If it uses SQLAlchemy and a direct database connection:
- Determine which PostgreSQL role is used.
- Determine whether that role bypasses RLS.
- Never claim RLS protects those connections without proof.
- Propose a safe user-scoped database access strategy.
- Require backend authorization checks on every repository operation.
- Avoid connection-pool identity leakage between users.

Do not use the postgres owner connection as an unquestioned runtime authorization strategy.

## Tests

Create Supabase pgTAP tests under the approved database test directory.

For each applicable table test:
- Anonymous access denied.
- User A can access User A records.
- User A cannot access User B records.
- User A cannot insert with User B ownership.
- User A cannot change ownership.
- Unauthorized relationships are rejected.
- Unsupported write operations are denied.

Run:
`supabase test db`

Also add relevant Python integration/security tests if the backend directly accesses PostgreSQL.

## Output

Report:
1. RLS coverage by table.
2. Grants by role.
3. Policies by operation.
4. Indexes added.
5. Test results.
6. Remaining security gaps.

Do not change production database settings or credentials.
```

### Giai đoạn E — Tạo ORM Models và Repository Layer

**Prompt 05 — Python Backend Integration**

Theo repo structure, phần database nằm ở:

```text
backend/app/db/
├── orm/
│   ├── __init__.py
│   ├── academic_task.py
│   ├── availability.py
│   ├── study_plan.py
│   ├── planned_study_block.py
│   ├── pending_action.py
│   ├── approval_event.py
│   └── source_document.py
│
├── repositories/
│   ├── base.py
│   ├── task_repository.py
│   ├── availability_repository.py
│   ├── study_plan_repository.py
│   ├── pending_action_repository.py
│   └── approval_repository.py
│
└── database.py
```

Tên file có thể điều chỉnh theo codebase hiện tại.

Đề xuất kỹ thuật: dùng SQLAlchemy 2.x + PostgreSQL driver `psycopg` nếu dự án chưa có ORM khác và Backend Developer đồng ý.

```text
You are a Senior Python Backend Database Engineer.

Implement the persistence layer for StudyFlow AI F1 using the approved PostgreSQL schema.

## First inspect

Read:
- Existing FastAPI application.
- Existing requirements/pyproject configuration.
- Existing database setup.
- Existing ORM conventions.
- Existing repository interfaces.
- Existing authentication context.
- Approved Supabase migrations.

Do not introduce a second ORM or database session system.

## ORM requirements

Implement ORM models matching the approved PostgreSQL schema.

Requirements:
- Correct UUID mapping.
- Correct foreign-key mapping.
- Correct nullable fields.
- Correct enum/status mapping.
- Check constraints reflected in metadata where appropriate.
- Timezone-aware timestamp fields.
- Relationships with deliberate loading behavior.
- No accidental cascading deletion of confirmed academic records.

Do not treat Pydantic request schemas as ORM models.
Do not invent columns that are absent from the approved schema.

## Database connection

Use the existing approved database access approach.

If the project adopts SQLAlchemy:
- Implement a reusable engine.
- Implement a safe session factory.
- Implement dependency injection for request-scoped sessions.
- Read DATABASE_URL from environment configuration.
- Never hardcode connection strings.
- Never log credentials.
- Configure the pool appropriately for the selected Supabase connection mode.

Do not expose the database password to the frontend.

## Repository layer

Implement repositories for:

1. AcademicTaskRepository
   - create_draft
   - get_by_id
   - list_by_user
   - confirm_task
   - update_allowed_fields, only if approved

2. AvailabilityRepository
   - create_or_update
   - list_by_user
   - validate_existing_intervals

3. StudyPlanRepository
   - create_proposal
   - get_by_id
   - list_by_period
   - get_blocks
   - retrieve_current_version

4. ApprovalRepository
   - create_approval_event
   - get_approval_event
   - enforce idempotency

5. PendingActionRepository
   - create
   - get_active
   - update_version
   - expire
   - cancel

Adapt the method signatures to the actual approved backend contracts.

## Repository rules

- All user-owned queries must be scoped by trusted authenticated user_id.
- Never trust user_id from an LLM-generated payload.
- Never expose raw SQL construction using untrusted strings.
- Use parameterized queries.
- Do not put NLU or scheduling algorithms into repositories.
- Keep business logic in the appropriate domain/service layer.
- Do not commit transactions from arbitrary repository methods if the existing architecture centralizes transaction ownership.

## Transaction requirements

Support the backend approval workflow:

Proposal → User Approval → Revalidation → Commit

The persistence layer must support:
- Transaction boundaries.
- Optimistic version checking.
- Row locking where needed.
- Idempotent approval recording.
- Atomic persistence of confirmed schedule changes.
- Rollback on failed commit.

For concurrent approval requests, only one operation may successfully commit the expected proposal version.

Do not invent an undo feature.

## Deliverables

- ORM models.
- Database session and connection configuration.
- Repository implementations.
- Necessary dependency updates.
- Type annotations.
- Unit tests.
- Integration tests.
- Updated database documentation.

Run the relevant test suite and report all failures.
```

### Giai đoạn F — Kiểm thử database và tích hợp

**Prompt 06 — Kiểm thử toàn bộ**

```text
Act as a Senior Database QA Engineer for StudyFlow AI.

Review and test the entire F1 MVP database implementation.

## 1. Schema tests

Verify:
- Primary keys.
- Foreign keys.
- NOT NULL constraints.
- Unique constraints.
- Check constraints.
- Referential integrity.
- Timestamp consistency.
- Index coverage.

Test invalid values:
- Negative estimated workload.
- Negative remaining workload.
- Remaining workload greater than estimated workload.
- Start date after deadline.
- End time before or equal to start time.
- Invalid status values.
- Invalid user references.

## 2. Ownership tests

Create two test users, User A and User B.

Verify:
- User A can access only User A's data.
- User B can access only User B's data.
- User A cannot reference User B's task.
- User A cannot approve User B's plan.
- Ownership cannot be changed through an update.
- An unauthenticated user cannot access private records.

Test both database-level RLS and backend authorization paths.

## 3. Business integrity tests

Test:
- Draft task cannot be scheduled.
- Confirmed task can be considered by the scheduler.
- Proposed plan remains unconfirmed.
- Rejected plan does not change the confirmed schedule.
- Approval must reference the correct plan and version.
- Expired proposal cannot be committed.
- Stale proposal cannot silently overwrite newer information.
- Duplicate commit requests do not duplicate records.
- Concurrent approvals cannot both commit the same expected version.

## 4. Interval tests

Use the half-open interval rule:

start_A < end_B AND start_B < end_A

Test:
- Overlapping intervals.
- Adjacent intervals.
- Same start time.
- Contained interval.
- Exact matching interval.
- Invalid zero-duration interval.

Adjacent intervals such as 08:00–09:00 and 09:00–10:00 should not count as overlapping.

## 5. Data lifecycle tests

Check:
- DRAFT → CONFIRMED task.
- PROPOSED → CONFIRMED study plan.
- Proposal rejection.
- Proposal expiration.
- Pending action updates.
- Pending action cancellation.
- Approval audit persistence.

## 6. Integration tests

Verify that ORM models and repository methods match the SQL migration schema.

Verify that backend API contracts match the shared JSON Schemas and OpenAPI specification.

## 7. Execution

Run:
- `supabase db reset` against the local database only.
- `supabase test db`.
- `pytest` for backend unit and integration tests.

Never run `db reset` against production.

## 8. Output

Generate a test report containing:
- Test ID.
- Scenario.
- Expected result.
- Actual result.
- PASS/FAIL.
- Error details.
- Suggested fix.

Do not claim tests passed unless they were actually executed.
```

### Giai đoạn G — Hoàn thiện tài liệu và bàn giao cho nhóm

**Prompt 07 — Database handover**

```text
Prepare the StudyFlow AI Database Engineering Handover.

I am responsible for the Supabase PostgreSQL database layer.

Create or update the database documentation under `docs/`.

Include:

1. Database architecture overview.
2. Final ERD.
3. Table data dictionary.
4. Primary key and foreign key definitions.
5. Constraints and indexes.
6. RLS policy documentation.
7. Supabase environment configuration instructions.
8. Migration execution instructions.
9. ORM model references.
10. Repository method signatures.
11. Seed data instructions.
12. Database testing instructions.
13. Known limitations.
14. Unresolved decisions.
15. Integration instructions for the FastAPI Backend Developer.

Also update:
- `docs/adr/` with approved database architecture decisions.
- `docs/open-issues.md` with unresolved issues.
- `contracts/CHANGELOG.md` only if an approved shared contract changes.

Do not document proposed functionality as implemented.

Generate a clear handover checklist for the Backend Developer.

Do not include credentials or real database connection strings in documentation.
```

## 6. Migration lên Supabase thật

Chỉ thực hiện sau khi schema đã được review và các kiểm thử local đạt yêu cầu.

Liên kết CLI với một project development riêng:

```powershell
npx supabase@latest link --project-ref YOUR_DEV_PROJECT_REF
```

Kiểm tra migration history:

```powershell
npx supabase@latest migration list --remote
```

Chạy dry-run trước:

```powershell
npx supabase@latest db push --dry-run --remote
```

Đọc kỹ danh sách thay đổi. Chỉ sau khi nhóm duyệt mới chạy:

```powershell
npx supabase@latest db push --remote
```

Không chạy những lệnh sau trên project `main (PRODUCTION)` trong quá trình thử nghiệm:

```bash
supabase db reset --remote
```

Không tự ý drop table, truncate dữ liệu hoặc chỉnh migration đã được áp dụng mà chưa có kế hoạch xử lý dữ liệu.

## 7. Supabase Storage cho PDF

Proposal xác định F1 MVP có chức năng nhập thông tin task thủ công hoặc trích xuất thông tin từ PDF văn bản được hỗ trợ. Do đó, ngoài PostgreSQL, cần xem xét Supabase Storage.

Kiến trúc đề xuất:

```text
Student uploads PDF
        |
        v
Supabase Storage
(private bucket)
        |
        v
FastAPI Backend
        |
        v
PDF Text Extraction
        |
        v
AI extracts candidate task information
        |
        v
AcademicTask (DRAFT)
        |
        v
Student confirms
        |
        v
AcademicTask (CONFIRMED)
```

Database cần có bảng metadata `source_documents` để lưu đường dẫn file, người sở hữu, trạng thái xử lý và thông tin provenance.

**Prompt 08 — Supabase Storage**

```text
Implement the Supabase Storage persistence design for StudyFlow AI F1 MVP.

Requirements:

1. Create or configure a private storage bucket for authorized course/task PDFs.
2. Never make uploaded academic documents publicly accessible by default.
3. Associate every document with its authenticated owner.
4. Organize storage paths using a user-scoped directory structure.
5. Store document metadata in the approved `source_documents` table.
6. Store file path, original filename, MIME type, file size, checksum, upload timestamp, and processing status where approved.
7. Configure storage access policies to prevent cross-user file access.
8. Validate supported file formats and size limits.
9. Support PDF text extraction only for the approved F1 MVP scope.
10. Do not introduce OCR-heavy processing.
11. Do not store the binary PDF content directly in PostgreSQL.
12. Handle failed uploads, failed extraction, and deleted file references safely.

Review Storage policies and test access using two separate authenticated test users.

Do not expose public URLs for private academic documents.

Keep all credentials and storage secrets outside source code.

Provide the SQL/configuration migrations, metadata ORM model, repository methods, and test cases.

Do not modify production Storage settings.
```

## 8. Quyết định kỹ thuật cần chốt với Backend Developer

| Quyết định | Khuyến nghị ban đầu | Trạng thái |
|---|---|---|
| Database | Supabase PostgreSQL | Đã chọn |
| ORM | SQLAlchemy 2.x | Đề xuất |
| PostgreSQL driver | psycopg 3 | Đề xuất |
| Migration | Supabase CLI | Đề xuất |
| Authentication | Supabase Auth hoặc phương án Auth đã thống nhất | Cần xác nhận |
| User ownership | UUID từ trusted auth context | Nguyên tắc bắt buộc |
| Data isolation | RLS + backend authorization | Bắt buộc thiết kế |
| Storage | Supabase private bucket | Đề xuất |
| FixedCommitment | Entity riêng hoặc mô hình busy interval khác | TBD |
| Course management | Chuẩn hóa thành Course entity hay giữ course reference | TBD |

Đặc biệt về RLS và SQLAlchemy: khi SQLAlchemy kết nối trực tiếp PostgreSQL, `auth.uid()` không tự động có context giống như request đi qua Supabase Data API. Nếu kết nối bằng tài khoản database có quyền bypass RLS, các policy sẽ không bảo vệ các truy vấn đó.

Vì vậy, phải thống nhất một phương án user-scoped database access và kiểm thử thực tế. Không được chỉ bật RLS rồi kết luận hệ thống đã an toàn.

## 9. Definition of Done — Khi nào hoàn thành nhiệm vụ Database?

- [ ] Supabase project và local CLI được cấu hình đúng.
- [ ] Migration được lưu trong Git, không chỉnh schema tùy tiện trên production.
- [ ] ERD và data dictionary được nhóm review.
- [ ] AcademicTask lưu được DRAFT và CONFIRMED.
- [ ] Availability lưu được các khoảng thời gian hợp lệ.
- [ ] StudyPlan và PlannedStudyBlock có quan hệ chính xác.
- [ ] ApprovalEvent gắn với đúng user, plan và version.
- [ ] PendingAction hỗ trợ lưu workflow nhiều lượt.
- [ ] SourceDocument và private Storage hoạt động nếu scope upload PDF đã được duyệt.
- [ ] RLS và grants được cấu hình theo từng bảng và operation.
- [ ] Kiểm thử truy cập chéo giữa hai user đạt yêu cầu.
- [ ] ORM Models khớp SQL migrations.
- [ ] Repositories khớp contract Backend.
- [ ] Transaction, stale version và idempotency đã được kiểm thử.
- [ ] README, ADR và tài liệu bàn giao được cập nhật.

## 10. Tài liệu kỹ thuật chính thức

- [Supabase Local Development Workflow](https://supabase.com/docs/guides/local-development)
- [Supabase Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase API Keys](https://supabase.com/docs/guides/api/api-keys)
- [Supabase PostgreSQL Connection](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase Python SDK](https://supabase.com/docs/reference/python/introduction)

## 11. Bắt đầu công việc

Thứ tự đề xuất:

1. Mở repository bằng Codex và tạo branch `feat/database-supabase`.
2. Gửi Prompt 01 cho Codex đọc/audit codebase.
3. Gửi Prompt 02 để xây dựng ERD, data dictionary và quan hệ giữa các bảng.
4. Review với Backend Developer; chốt SQLAlchemy, migration, authentication, RLS và các field chung.
5. Gửi Prompt 03–06 để tạo migration, ORM, repository, RLS và kiểm thử.
6. Gửi Prompt 07 để hoàn thiện tài liệu và bàn giao.
7. Prompt 08 dùng cho phần Storage nếu scope PDF đã được duyệt.

Không để database trở thành nơi chứa business logic của cả hệ thống. Theo kiến trúc dự án, `scheduler/engine.py` phải là thành phần thuần, deterministic, không truy cập DB hoặc gọi LLM. Database cung cấp dữ liệu đầu vào, lưu kết quả proposal và ghi nhận commit; việc điều phối thuộc Orchestrator, còn quy tắc nghiệp vụ thuộc F1 Backend.
