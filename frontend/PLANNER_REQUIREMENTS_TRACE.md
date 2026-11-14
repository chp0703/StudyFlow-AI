# Planner follow-up traceability (audited 2026-11-14)

Leader requirements are supplied in the correction brief. `frontend-demo-follow-up.md` is not present in this checkout. The versioned `main` API contract remains the transmission boundary.

| Requirement | Leader's expected behavior | Audited implementation | Status | Evidence |
| --- | --- | --- | --- | --- |
| FE-01 | Name, exact start, minutes, numeric priority, color, optional description; no fabricated persistence | UI models and Demo preserve minute/duration/color data when present. API mode stays on the versioned contract and does not send unsupported Planner fields. | **PARTIAL / backend-dependent** | Mapper, API client, planner-agent and calendar tests; runtime persistence still waits for the deployed backend contract. |
| FE-02 | All Planner dates and times in Vietnam timezone | Shared Vietnam civil-date/clock helpers drive week/month boundaries, labels and current-time placement. | **VERIFIED** | `utils/date.test.ts`, month boundary tests and browser dates at all audited viewports. |
| FE-03 | One frontend-only display start/end per weekday | `CalendarDisplaySettings` owns seven independent ranges in `Planner` state. Only Detailed Time reads them; no API, task, proposal, revision, `TimeWindow` or scheduler input is changed. | **VERIFIED** | `calendarDisplay.test.ts`, `WeekCalendar.test.ts`; browser hide/reveal retained the same event and Free/Busy data. No weekly working-time editor is mounted. |
| FE-04 | Complete proposed schedule and issues; explicit decision with original reference | Proposal details, partial/unscheduled issues, explicit Approve/Reject, stale lockout and unchanged `ActionReference` remain in the existing flow. | **VERIFIED** | API client reference test, mapper/proposal tests and browser approve/reject/pending-preservation journeys. |
| FE-05 | Sticky Vietnam weekday/date header | Detailed Time retains one sticky weekday/date header inside its horizontal timeline region. | **VERIFIED** | Browser computed style: `position: sticky; top: 0`; 390, tablet-class and 1440 QA. |
| FE-06 | Real server upload/extraction with confirmation | Attachments remain display-only in Demo and disabled in API mode; no uploaded/read/extracted claim is shown. | **BLOCKED / safe frontend behavior verified** | `assistantService.test.ts` attachment assertion and UI copy review; no upload/extraction backend exists in the current contract. |

## Hotfix Round 1 — Compact Week Agenda Scroll (2026-11-14)

**Root cause:** `.main-content:has(.planner-page)` imposed `height: calc(100dvh - 58px)` with `overflow: hidden` propagating down through `.planner-page` and `.planner-calendar`, both also `overflow: hidden`. `.compact-week` had `overflow: auto` but was sized by `flex: 0 0 auto`, meaning its intrinsic height exceeded the fixed viewport budget and was silently clipped by the ancestor `overflow: hidden` chain. The `.compact-agenda` was rendered but unreachable by scroll.

**Fix:** Added `:has(.compact-week)` selector overrides (mirroring the existing Month View pattern) in `frontend/src/styles/planner.css`:
- `.main-content:has(.planner-page):has(.compact-week)` → `height: auto; min-height: calc(100dvh - 58px); overflow: visible`
- `.planner-page:has(.compact-week)` → `flex: 0 0 auto; overflow: visible`
- `.planner-calendar` inside → `overflow: visible`
- `.compact-week` inside → `overflow: visible`

Detailed Time (WeekCalendar) is unaffected because it does not render `.compact-week`; its `overflow: hidden` chain and internal timeline scroll are preserved. Month View is unaffected because its existing `:has(.month-calendar)` override already fires. Mobile `@media (max-width: 800px)` updated to `overflow-x: hidden; overflow-y: visible` for `.compact-week`.

**Verification:** 57/57 Node tests, `npx tsc --noEmit`, `npm run build`, `npm run format`, `git diff --check` all pass. Browser QA performed at 390×844, 768×1024, 1440×900.

## Final UX audit evidence

- Calendar views: Compact Week remains default; Month uses a Monday-first 4–6-row grid; Detailed Time keeps exact-minute placement, per-weekday ranges and sticky dates.
- Free/Busy: API minute intervals and Demo legacy hours render read-only in all views; Busy splits and overrides overlapping Free intervals without mutating source data.
- Composer: multiline keyboard/IME behavior, truthful Demo/API copy, draft retention, proposal separation and inline feedback are covered by rendered-component tests and browser journeys.
- Responsive browser QA: 390×844 and 1440×900 CSS px were exact. The in-app browser rounded the 768 target to 767×1024 CSS px; all three views, composer, focus ring and page overflow were checked at that tablet breakpoint.
- Automated verification on 2026-11-14: **57/57 Node tests**, TypeScript, Vite build, formatter and `git diff --check` passed. Vite still reports the existing >500 kB chunk warning; Vite SSR tests report a sandbox WebSocket bind warning while all assertions pass.
- API E2E with an authenticated backend is **BLOCKED** because no authorized test account/backend was available. Screenshots were captured in the local audit session only; they were not committed or uploaded.

The branch does not copy unrelated `origin/main` work. The latest `origin/main` also changes `frontend/src/App.tsx`; a three-way integration preview auto-merges the independent hunks, but this overlap remains a reviewer integration-risk checkpoint.

## FE Lead review blockers — PR #40 (2026-11-14)

| Finding | Root cause | Fix and regression evidence | Status |
| --- | --- | --- | --- |
| Obsolete Demo `rảnh` interaction | The legacy combined `rảnh|bận` parser still wrote Demo availability and the scheduler still treated Free as an input. | Demo rejects add/remove `rảnh` truthfully without changing tasks, availability or an existing proposal. Busy operations and read-only Free/Busy rendering remain. `plannerAgent.test.ts`, `proposal.test.ts`. | **PASS** |
| TimeWindow confirmation trust boundary | Reload restoration omitted `server.windows`; the mapper formatted every previous target as WEEKLY and allowed unresolved summaries. | Restore passes authoritative windows. One formatter covers WEEKLY/NONE in `Asia/Ho_Chi_Minh`; UPDATE shows old/new and ARCHIVE shows the exact target. Missing IDs/records or malformed intervals produce a Vietnamese warning and block Approve in both UI and handler while preserving Reject and the original ActionReference. Task/plan proposals remain unaffected. `mappers.test.ts`, `ProposalReview.test.ts`, `proposal.test.ts`. | **PASS (authenticated API E2E not run)** |
| Exact clicked minute | Detailed Time reduced `minuteOfDay` to an integer hour before prefill. | Callback now carries `minuteOfDay`; Demo composer receives `HH:mm`, focus and cursor placement remain, and no submit occurs. Tests cover 08:00, 09:15, 10:30, 16:45, next-week navigation and the Nov/Dec boundary. `WeekCalendar.test.ts`. | **PASS** |
| Display Settings relevance | The FE-03 control mounted in all views although only Detailed Time consumed ranges. | The control mounts only for `detail`; seven ranges stay in parent state across view switches and remain presentation-only. `calendarDisplay.test.ts`. | **PASS** |

Current readiness: all four review findings have focused automated coverage. Final verification is 67/67 Node tests plus TypeScript, Vite build, formatter and `git diff --check`; browser QA passed at 1440×900, 390×844 and tablet-class 767×1024 CSS px with no horizontal page overflow or console warning/error. Authenticated API restoration remains unavailable without an authorized backend session. The separate 180-minute Demo scheduler issue remains out of scope.
