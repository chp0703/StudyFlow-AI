# Planner follow-up traceability (2026-11-13)

Leader requirements are supplied in the correction brief. `frontend-demo-follow-up.md` is not present in this checkout. The versioned `main` API contract remains the transmission boundary; PR #32 is open.

| Requirement | Leader's expected behavior | Current implementation at `917e652` | Decision | Affected files | Test |
| --- | --- | --- | --- | --- | --- |
| FE-01 | Name, exact start, minutes, numeric priority, color, optional description; no Planner course | Legacy API priority and course mapping; demo hourly starts | MODIFY / BLOCKED for API persistence until PR #32 runtime | `types/task.ts`, `api/mappers.ts`, `plannerAgent.ts`, `TaskPanel.tsx`, `WeekCalendar.tsx`, `Assistant.tsx` | Mapper, planner, calendar tests |
| FE-02 | All Planner dates and times in Vietnam timezone | Vietnam date helpers and tests exist | KEEP | `utils/date.ts`, Planner, calendar | `date.test.ts` across host timezones |
| FE-03 | One frontend-only display start/end per weekday | Weekly availability editor, proposal, scheduler constraints, calendar availability segments | REMOVE incorrect path; IMPLEMENT display settings | `WorkingTimeEditor.tsx`, `workingTime.ts`, `App.tsx`, `usePlanner.ts`, `plannerAgent.ts`, `proposal.ts`, Planner, calendar, CSS | Display settings and calendar tests |
| FE-04 | Complete proposed schedule and issues; explicit decision with original reference | Preview exists but lacks exact end time and lists only changed demo entries | MODIFY | `ProposalReview.tsx`, `api/mappers.ts` | Proposal and mapper tests |
| FE-05 | Sticky Vietnam weekday/date header | Header is sticky inside calendar scroll | KEEP / VERIFY after calendar refactor | `WeekCalendar.tsx`, CSS | Calendar markup and browser QA |
| FE-06 | Real server upload/extraction with confirmation | No versioned route or source DTO; API button disabled, demo display-only | BLOCKED / KEEP safe behavior | Assistant, ChatComposer, API contracts | Existing attachment test and browser QA |

The UX refresh branch changes the weekly editor and Planner styling. It is not an implementation base. The FE branch contains a clean working tree; unrelated changes already on `origin/main` belong to other contributors and are not copied here.
