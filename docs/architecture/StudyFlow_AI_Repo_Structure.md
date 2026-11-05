# StudyFlow AI — Repository Structure

> Bộ contract thực tế nằm tại [contracts/README.md](../../contracts/README.md): OpenAPI, một schema bundle dùng chung, service/data registry và fixtures. Cây bên dưới là bản thiết kế đích từ PDF; tên file minh họa trong cây không thay thế các artifact hiện có hoặc trạng thái review của chúng.

> Bản chuyển đổi Markdown từ PDF nguồn `repo structure.pdf` (3 trang). Cấu trúc cây được giữ trong một khối code để bảo toàn quan hệ thư mục và chú thích gốc.

```text
studyflow-ai/
├── contracts/          # NGUỒN SỰ THẬT DUY NHẤT – 2 team cùng review
│ ├── schemas/            # JSON Schema
│ │ ├── user_message.json
│ │ ├── extraction_result.json
│ │ ├── pending_action.json
│ │ ├── validated_command.json
│ │ ├── tool_result.json
│ │ ├── approval_evidence.json
│ │ └── errors.json       # error code catalog
│ ├── openapi.yaml          # API giữa FE ↔ BE
│ ├── examples/           # JSON valid/invalid cho từng contract
│ │ ├── valid/
│ │ └── invalid/
│ └── CHANGELOG.md               # mọi thay đổi contract phải ghi ở đây
│
├── backend/
│ ├── app/
│ │ ├── main.py
│ │ ├── core/           # config, auth context, timezone, logging
│ │ │ ├── auth.py         # user_id CHỈ lấy từ đây, không từ LLM
│ │ │ ├── clock.py        # request timestamp, timezone
│ │ │ └── errors.py
│ │ ├── api/           # HTTP layer mỏng
│ │ │ ├── chat.py         # POST /messages
│ │ │ ├── tasks.py
│ │ │ ├── availability.py
│ │ │ ├── plans.py
│ │ │ └── approvals.py
│ │ ├── nlu/           # LLM/NLU layer – output là UNTRUSTED
│ │ │ ├── adapter.py        # gọi LLM, timeout, retry
│ │ │ ├── prompts/
│ │ │ ├── parser.py        # raw → ExtractionResult
│ │ │ └── time_expressions.py
│ │ ├── orchestrator/      # Shared Orchestrator
│ │ │ ├── pipeline.py # 10 stage
│ │ │ ├── context.py
│ │ │ ├── pending_actions.py
│ │ │ ├── clarification.py
│ │ │ ├── dispatcher.py # ValidatedCommand → tool (deterministic)
│ │ │ ├── approval_router.py
│ │ │ └── state_machine.py
│ │ ├── validation/      # structural → semantic → domain → state
│ │ │ ├── structural.py
│ │ │ ├── semantic.py
│ │ │ ├── domain.py
│ │ │ └── state.py
│ │ ├── f1/           # F1 Backend – business logic
│ │ │ ├── tasks/          # create_task_candidate, confirm_task, search_tasks
│ │ │ ├── availability/ # set_availability
│ │ │ ├── scheduler/         # generate_study_plan – THUẦN, không gọi LLM/DB
│ │ │ │ ├── engine.py
│ │ │ │ ├── ordering.py # deadline → priority
│ │ │ │ └── slots.py
│ │ │ ├── planning/         # get_study_plan, propose_reschedule
│ │ │ ├── approval/         # approve_study_plan: verify → revalidate → commit
│ │ │ └── entity_resolution.py
│ │ ├── models/            # Pydantic schemas (sinh/đối chiếu từ contracts/)
│ │ └── db/
│ │     ├── orm/         # AcademicTask, StudyPlan, PlannedStudyBlock…
│ │     ├── repositories/
│ │     └── migrations/
│ ├── tests/
│ │ ├── unit/           # scheduler, validator – chạy không cần DB
│ │ ├── integration/
│ │ ├── contract/         # đối chiếu response với contracts/schemas
│ │ ├── workflow/          # multi-turn, pending action, approval
│ │ ├── security/         # forged approval, cross-user access
│ │ └── fixtures/
│ ├── pyproject.toml
│ └── Dockerfile
│
├── frontend/
│ ├── src/
│ │ ├── api/            # client sinh từ openapi.yaml
│ │ ├── types/           # type sinh từ contracts/schemas
│ │ ├── features/
│ │ │ ├── chat/           # khung chat, clarification
│ │ │ ├── tasks/          # task nháp vs đã xác nhận
│ │ │ ├── availability/
│ │ │ ├── schedule/         # lịch confirmed vs proposed
│ │ │ └── proposals/         # preview, approve/reject, unscheduled work
│ │ ├── components/           # UI dùng chung
│ │ ├── i18n/vi/         # error code → thông báo tiếng Việt
│ │ ├── hooks/
│ │ └── lib/           # date/timezone utils
│ ├── mocks/              # mock server từ contracts/examples
│ ├── tests/
│ │ ├── component/
│ │ └── e2e/             # theo UC-01 → UC-13
│ ├── package.json
│ └── Dockerfile
│
├── eval/              # Đánh giá NLU – tách khỏi unit test
│ ├── datasets/           # câu tiếng Việt + intent/slot kỳ vọng
│ ├── run_eval.py
│ └── reports/
│
├── docs/
│ ├── srs/           # SRS .md + .docx
│ ├── adr/            # Architecture Decision Records – ghi D1–D8 khi chốt
│ ├── diagrams/          # Mermaid
│ └── open-issues.md
│
├── docker-compose.yml        # fe + be + db chạy local
├── .github/
│ ├── workflows/
│ │ ├── backend.yml
│ │ ├── frontend.yml
│ │ └── contracts.yml      # validate schema + examples
│ ├── CODEOWNERS
│ └── pull_request_template.md
└── README.md
```
