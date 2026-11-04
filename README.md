# StudyFlow AI

StudyFlow AI is a student-controlled academic planning assistant. It turns confirmed tasks and time constraints into feasible study-plan proposals, then saves a new schedule snapshot only after explicit approval.

This repository currently contains the frontend prototype and approved F1 design documentation. The backend, database migrations, authentication integration, and live AI services are not yet implemented here.

## Current release scope

F1 is the Initial Release / MVP: Intelligent Academic Planner.

- Create task candidates from user messages or manual input.
- Validate and explicitly confirm an `AcademicTask` before scheduling.
- Record availability and busy periods as unified `TimeWindow` records.
- Generate deterministic study-plan proposals with visible warnings and unscheduled work.
- Approve or reject proposals; approval creates an immutable `StudyPlan` snapshot.
- Keep one current plan per user through `current_plan_id` and `schedule_revision`.
- Preserve historical snapshots and logical `StudyBlock` identity across replanning.
- Support user scheduling preferences and one-time policy overrides.

F2 (Learning Assessment & Adaptive Revision) and F3 (Daily AI Learning) are planned post-MVP features, outside the v1.1 execution scope.

## Official data contract

The authoritative logical contract is [Official F1 Schema v1.1](docs/database/schema_F1.md). It defines fields, lifecycle states, ownership rules, time semantics, tool contracts, scheduling-engine inputs/outputs, proposal approval, and idempotency behavior.

The database mapping is documented in [Database Design Baseline v1.1](docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md). The v1.0 draft remains historical and is superseded for F1 integration.

Key v1.1 rules:

- `TaskCandidate`: `DRAFT`, `CONFIRMED`, `CANCELLED`.
- `AcademicTask`: `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
- `PlanProposal`: `PROPOSED`, `APPROVED`, `REJECTED`, `STALE`.
- `PendingAction` has explicit awaiting states and `requires_review`; it has no product TTL.
- `IdempotencyRecord` is the only contract with an operational `expires_at`.
- `TimeWindow` uses `AVAILABILITY` or `BUSY` with `NONE` or `WEEKLY` recurrence.
- API timestamps use offsets; persistence stores UTC instants. Intervals are half-open: `[start_at, end_at)`.
- Scheduling never infers task completion or decrements `remaining_minutes`.
- LLM extraction is untrusted; ownership and approval evidence come from the trusted backend context.

## Planning workflow

```text
User message / manual input
        |
Extraction and clarification (untrusted output)
        |
ValidationReport and TaskCandidate
        |  explicit user confirmation
AcademicTask + TimeWindow records
        |
Deterministic Scheduling Engine
        |
Full PlanProposal snapshot
        |  explicit user approval
Immutable StudyPlan + StudyBlocks
        |
Atomically update current_plan_id and schedule_revision
```

The Scheduling Engine is pure and deterministic: it does not call the LLM, access the database, assign proposal IDs, or commit plans. The service layer resolves ownership, expands recurring windows, retains protected blocks, assigns block IDs, validates the full snapshot, and persists it.

Proposal coverage is explicit: `FULL`, `PARTIAL`, `NONE`, or `NO_CHANGE`. Partial coverage must show unscheduled work; `NONE` is not committable.

## Architecture and current implementation

The planned architecture separates the UI, shared orchestrator, validation, F1 domain services, deterministic scheduler, persistence, and contract schemas. See [repository structure](docs/architecture/StudyFlow_AI_Repo_Structure.md).

The currently present application is a React/Vite prototype under [`frontend/`](frontend/). It is demo-only: there is no backend, authentication, persistence, PDF parsing, or live AI integration yet.

## Repository structure

```text
StudyFlow-AI/
├── frontend/                         # React/Vite prototype
│   ├── src/                           # UI, assistant demo, styles and tests
│   ├── public/                        # Brand assets
│   ├── package.json
│   └── README.md
├── docs/
│   ├── database/
│   │   ├── schema_F1.md               # Official logical schema v1.1
│   │   ├── StudyFlow_AI_Database_Design_Baseline_v1.1.md
│   │   └── StudyFlow_AI_Supabase_Database_Codex_Guide.md
│   ├── srs/                           # Software requirements
│   ├── project/                       # Proposal, context and worklist
│   ├── architecture/                 # Target repository architecture
│   └── prompts/                       # Engineering prompts
├── README.md
└── .gitignore
```

The planned implementation layout (contracts, backend, tests, scheduler and database layers) is described in [StudyFlow_AI_Repo_Structure.md](docs/architecture/StudyFlow_AI_Repo_Structure.md). Those folders are architectural guidance and should not be interpreted as already implemented.

## Run the frontend prototype

```bash
cd frontend
npm install
npm run dev
```

Other commands: `npm run build`, `npm run preview`, and `npm run format`.

## Documentation map

| Area | Document |
|---|---|
| Official F1 logical schema | [docs/database/schema_F1.md](docs/database/schema_F1.md) |
| Database baseline | [docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md](docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md) |
| Requirements | [docs/srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md](docs/srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md) |
| Team proposal | [docs/project/Team03_Proposal_Updated.md](docs/project/Team03_Proposal_Updated.md) |
| Project context | [docs/project/context.md](docs/project/context.md) |
| Worklist | [docs/project/cong_viec_can_lam.md](docs/project/cong_viec_can_lam.md) |
| Repository target structure | [docs/architecture/StudyFlow_AI_Repo_Structure.md](docs/architecture/StudyFlow_AI_Repo_Structure.md) |
| Supabase/database guide | [docs/database/StudyFlow_AI_Supabase_Database_Codex_Guide.md](docs/database/StudyFlow_AI_Supabase_Database_Codex_Guide.md) |

## Out of scope for F1 v1.1

- F2/F3 assessment and guided-learning entities.
- Course management as a separate entity; F1 uses `course_label`.
- PDF/OCR processing and mandatory `SourceDocument` persistence.
- Manual study-block creation or individual block rescheduling.
- Task update/cancel APIs and `StudySession`.
- Automatic task completion or progress inference from elapsed blocks.
- Multiple active confirmed plans, proposal/candidate/action TTLs, or legacy `EXPIRED` states.

## Status and implementation blockers

The documentation baseline is ready for team review, not implementation. Before backend/database work begins, the team still needs to approve nested payload/policy storage, same-owner composite foreign keys, polymorphic approval-target enforcement, overlap enforcement, runtime role/RLS behavior, idempotency retention, indexes, and corresponding SRS scope revisions.

Do not treat design documents, proposal diagrams, or frontend mock data as evidence that backend or database functionality has been implemented.
