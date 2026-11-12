# Planner frontend follow-up: contract boundary

Checked against `main` at `6ef890c` and PR #32 head `fb6be04` on 2026-11-12. PR #32 is open. The current `contracts/schemas/f1.schema.json` (schema 1.1, contract package 1.0.1) remains authoritative for API mode. The named `frontend-demo-follow-up.md` and `backend-demo-follow-up.md` were not present in the checkout or at the repository root on GitHub; the FE requirements in the task request supplied the checklist.

| FE requirement | Current main contract | PR #32 reference | Current API/runtime | Safe frontend action |
| --- | --- | --- | --- | --- |
| Task `start_at` | Absent | Exact requested start | Main create-task validator uses legacy deadline/availability fields | Gate API task form until merge and runtime verification. Do not confuse with a StudyBlock start. |
| `available_from_at` | Optional availability bound | Defaults from `start_at` | Main scheduler reads availability bound | Preserve current meaning. |
| `deadline_at`, `deadline_precision` | Required task deadline and precision | Derived when no separate deadline | Main exposes both | Continue displaying deadline; render DATETIME in Vietnam time. |
| `estimated_minutes`, `remaining_minutes` | Integer effort and remaining effort | Same, with derived initial remaining | Main task list exposes both | Preserve duration from server. |
| `priority` | `LOW`, `NORMAL`, `HIGH` | Numeric `0.1`, `0.5`, `1` | Main mapper expects legacy enum | Do not send numeric priority until PR #32 is merged. |
| `color` | Absent | `#RRGGBB` | Main task response has no color | Do not invent a persisted color. |
| `description` | Nullable task field | Nullable task field | Main list response includes it | Preserve and display server description; defer the new task form. |
| `course_label` | Nullable task field | Removed | Main DTO includes it | Stop asking for it in the demo draft; retain stored legacy field and main API mapping. |
| `timezone` | IANA timezone; product default is Vietnam | Fixed `Asia/Ho_Chi_Minh` | Main server defaults Vietnam | Render Planner instants in Vietnam time without sending a new timezone contract. |
| `TimeWindow` | Weekly/one-off `AVAILABILITY` or `BUSY`; versioned `ADD`, `UPDATE`, `ARCHIVE` | Fixed Vietnam timezone | `POST /v1/actions`, `POST /v1/decisions`, `GET /v1/time-windows` | Weekly editor prepares one availability change at a time, validates intervals, then requires explicit approval. Busy windows remain separate. |
| `PlanProposal` | Full snapshot, `plan_diff`, warnings, coverage, task summaries | Same entity | Read from action presentation and proposal view | Show entries, differences, partial coverage, warnings and unallocated minutes. |
| `StudyBlock` | Scheduled start/end instants | Same entity | Read from current plan and proposal | Render as Lịch học in Vietnam time; keep DTO name. |
| File upload/extraction | No route or source DTO | No route in PR #32 | No upload route in backend | Keep API attachment control disabled. |

The task form's numeric priority, exact requested start, color, and new DTO mapping require a merged and verified backend contract. The current hourly demo calendar also needs a separate minute-level layout change before it can faithfully place overlapping sub-hour blocks.
