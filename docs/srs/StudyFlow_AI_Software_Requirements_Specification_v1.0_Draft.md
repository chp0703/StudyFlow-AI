# StudyFlow AI — Software Requirements Specification

> Bản chuyển đổi Markdown từ PDF nguồn. Nội dung văn bản được giữ theo thứ tự tài liệu; các hình ảnh nhúng được lưu trong thư mục `assets/`. Các header/footer lặp lại và số trang in ở chân trang được thay bằng chú thích trang HTML để tránh lặp nội dung trình bày.

<!-- PDF page 1 -->
StudyFlow AI — Software Requirements  
Specification  
**SRS v1.0 — Draft for Engineering Review**  
StudyFlow AI Group 03  
04 November 2026  
# TABLE OF CONTENTS
Revision history................................................................................................................................................................................................................................3  
Approval record...............................................................................................................................................................................................................................3  
Document map................................................................................................................................................................................................................................ 4  
1. INTRODUCTION.................................................................................................................................................................................................................................. 4
1.1 Purpose......................................................................................................................................................................................................................................4  
1.2 Scope..........................................................................................................................................................................................................................................4  
1.3 Project background and problem statement............................................................................................................................................................................4  
1.4 Objectives..................................................................................................................................................................................................................................4  
1.5 Intended audience.....................................................................................................................................................................................................................5  
1.6 Definitions and abbreviations...................................................................................................................................................................................................5  
1.7 Source documents and references...........................................................................................................................................................................................5  
2. OVERALL SYSTEM DESCRIPTION......................................................................................................................................................................................................6
2.1 Product perspective...................................................................................................................................................................................................................6  
2.2 Target users and user characteristics........................................................................................................................................................................................6  
2.3 Product functions by release.....................................................................................................................................................................................................6  
2.4 Operating environment.............................................................................................................................................................................................................6  
2.5 Constraints.................................................................................................................................................................................................................................6  
2.6 Assumptions and dependencies................................................................................................................................................................................................7  
2.7 Product boundaries...................................................................................................................................................................................................................7  
3. SYSTEM ARCHITECTURE AND COMPONENT RESPONSIBILITIES.................................................................................................................................................7
3.1 High-level architecture..............................................................................................................................................................................................................7  
3.2 Component responsibilities.......................................................................................................................................................................................................8  
3.3 Trust boundaries and data ownership......................................................................................................................................................................................8  
3.4 Main data/control sequence.....................................................................................................................................................................................................9  
3.5 Future integration model.......................................................................................................................................................................................................... 9  
4. RELEASE SCOPE AND FEATURE BOUNDARIES.............................................................................................................................................................................10
4.1 Initial Release / F1 MVP — in scope........................................................................................................................................................................................10  
4.2 Explicitly out of F1 MVP / deferred.........................................................................................................................................................................................10  
4.3 Change control.........................................................................................................................................................................................................................10  
5. FUNCTIONAL REQUIREMENTS.......................................................................................................................................................................................................10
5.1 System-wide requirements.....................................................................................................................................................................................................11  
5.2 F1 — Task capture and confirmation......................................................................................................................................................................................11  
5.3 F1 — PDF task extraction........................................................................................................................................................................................................12  
5.4 F1 — Availability management...............................................................................................................................................................................................13  
5.5 F1 — Automatic planning and scheduling..............................................................................................................................................................................14  
5.6 F1 — Study-plan retrieval........................................................................................................................................................................................................15  
5.7 F1 — Rescheduling..................................................................................................................................................................................................................15  
5.8 F1 — Orchestrator and conversation management...............................................................................................................................................................16  
5.9 F2 — Learning Assessment & Adaptive Revision (Post-MVP)................................................................................................................................................17  
5.10 F3 — Daily AI Learning (Post-MVP).......................................................................................................................................................................................17  
6. INTENT CATALOG AND PARAMETER SPECIFICATION.................................................................................................................................................................18
6.1 Canonical vocabulary proposal...............................................................................................................................................................................................18  
6.2 Parameter definitions..............................................................................................................................................................................................................19  
6.3 Two-stage command validation..............................................................................................................................................................................................19  
7. BUSINESS RULES AND VALIDATION..............................................................................................................................................................................................19
7.1 Structural validation................................................................................................................................................................................................................19  
7.2 Semantic validation.................................................................................................................................................................................................................20  
7.3 Domain validation....................................................................................................................................................................................................................20  
7.4 Scheduler algorithm contract..................................................................................................................................................................................................20  

<!-- PDF page 2 -->
7.5 Interval semantics....................................................................................................................................................................................................................21  
7.6 Validation statuses..................................................................................................................................................................................................................21  
8. WORKFLOW AND STATE MANAGEMENT.....................................................................................................................................................................................22
8.1 Orchestrator processing stages...............................................................................................................................................................................................22  
8.2 Workflow state definitions......................................................................................................................................................................................................22  
8.3 State transition table...............................................................................................................................................................................................................23  
8.4 PendingAction lifecycle...........................................................................................................................................................................................................23  
8.5 Multi-intent dependencies......................................................................................................................................................................................................23  
9. TOOL CONTRACTS AND API REQUIREMENTS..............................................................................................................................................................................24
9.1 Contract envelope — illustrative only....................................................................................................................................................................................24  
9.2 Detailed minimum tool semantics..........................................................................................................................................................................................25  
9.3 Error response envelope.........................................................................................................................................................................................................25  
10. DATA REQUIREMENTS AND DATA MODEL................................................................................................................................................................................26
10.1 F1 entities..............................................................................................................................................................................................................................26  
10.2 Post-MVP entities from proposal..........................................................................................................................................................................................27  
10.3 Relationships and cardinality................................................................................................................................................................................................27  
10.4 Data integrity and lifecycle....................................................................................................................................................................................................27  
11. TIME AND DATE HANDLING.........................................................................................................................................................................................................27
11.1 Data representation..............................................................................................................................................................................................................27  
11.2 Natural-language date/time interpretation.........................................................................................................................................................................28  
11.3 Vietnamese examples...........................................................................................................................................................................................................28  
12. ERROR HANDLING AND RECOVERY............................................................................................................................................................................................28
12.1 Retry policy............................................................................................................................................................................................................................29  
12.2 Transaction and rollback....................................................................................................................................................................................................... 29  
13. SECURITY AND AUTHORIZATION REQUIREMENTS...................................................................................................................................................................29
13.1 Threats and mitigations.........................................................................................................................................................................................................30  
14. NON-FUNCTIONAL REQUIREMENTS...........................................................................................................................................................................................30
15. EXTERNAL AND USER INTERFACE REQUIREMENTS..................................................................................................................................................................31
15.1 Student-facing interface........................................................................................................................................................................................................31  
15.2 Existing proposal UI illustrations...........................................................................................................................................................................................32  
15.3 Software interfaces...............................................................................................................................................................................................................33  
15.4 Communication and protocol decisions...............................................................................................................................................................................33  
16. USE CASE SPECIFICATIONS...........................................................................................................................................................................................................33
16.1 UC-F1-01 — Capture, review and confirm an academic task...............................................................................................................................................33  
16.2 UC-F1-02 — Import a task candidate from an authorized PDF............................................................................................................................................33  
16.3 UC-F1-03 — Declare or change availability..........................................................................................................................................................................34  
16.4 UC-F1-04 — Generate, inspect and approve a weekly study plan.......................................................................................................................................34  
16.5 UC-F1-05 — Retrieve a study plan........................................................................................................................................................................................35  
16.6 UC-F1-06 — Propose rescheduling of a confirmed study block...........................................................................................................................................35  
16.7 UC-F1-07 — Resolve clarification and pending action across turns....................................................................................................................................36  
16.8 UC-F2-01 — Complete a verified quiz and review revision priorities (Post-MVP)..............................................................................................................36  
16.9 UC-F3-01 — Complete a source-grounded guided learning session (Post-MVP)................................................................................................................36  
17. ACCEPTANCE CRITERIA..................................................................................................................................................................................................................37
18. TESTING AND QUALITY ASSURANCE REQUIREMENTS.............................................................................................................................................................38
18.1 Test levels..............................................................................................................................................................................................................................38  
18.2 Test scenario matrix.............................................................................................................................................................................................................. 38  
18.3 AI/NLU metrics......................................................................................................................................................................................................................39  
18.4 Test data governance............................................................................................................................................................................................................40  
19. REQUIREMENT TRACEABILITY MATRIX......................................................................................................................................................................................40
19.1 Traceability maintenance rule...............................................................................................................................................................................................41  
20. OPEN DECISIONS, RISKS AND REQUIRED TEAM ACTIONS......................................................................................................................................................41
20.1 Risk register...........................................................................................................................................................................................................................43  
21. IMPLEMENTATION ROADMAP AND RELEASE GATES..............................................................................................................................................................43
21.1 P0 — Freeze requirements and design contracts.................................................................................................................................................................43  
21.2 P1 — Implement and verify F1 MVP.....................................................................................................................................................................................44  
21.3 P2 and Post-MVP...................................................................................................................................................................................................................44  
21.4 Team roles recorded by the proposal...................................................................................................................................................................................44  
APPENDICES..........................................................................................................................................................................................................................................44  
Appendix A — Canonical terminology proposed for implementation.........................................................................................................................................44  
Appendix B — Illustrative contract examples...............................................................................................................................................................................45  
Appendix C — Status taxonomy....................................................................................................................................................................................................47  
Appendix D — Scheduler invariants and verification formulas....................................................................................................................................................48  
Appendix E — Assumption and TBD register................................................................................................................................................................................48  
Appendix F — Source register and limitations.............................................................................................................................................................................49  
Appendix G — Final engineering readiness checklist...................................................................................................................................................................49  

<!-- PDF page 3 -->
# DOCUMENT CONTROL
```text
 Field                                                                        Value
 Document title                                                               StudyFlow AI — Software Requirements Specification
 Document ID                                                                  SFAI-SRS-001
 Version                                                                      1.0-DRAFT
 Date                                                                         04 November 2026 (reference timezone: Asia/Ho_Chi_Minh)
 Project / course                                                             StudyFlow AI / CSC10014 — Computational Thinking
 Institution                                                                  University of Science, Vietnam National University Ho Chi Minh City
 Prepared for                                                                 StudyFlow AI Group 03
 Document owner                                                               TBD — team decision required
 Reviewers / approvers                                                        TBD — no approval evidence supplied
 Primary implementation scope                                                 F1 — Intelligent Academic Planner (Initial Release / MVP)
 Future scope                                                                 F2 — Learning Assessment & Adaptive Revision; F3 — Daily AI Learning (Post-
                                                                              MVP)
```
## Revision history
```text
 Version                              Date                                    Change                                   Status
 0.1                                  04 Nov 2026                             Initial consolidation from proposal,     Draft
                                                                              context and worklist.
 1.0-DRAFT                            04 Nov 2026                             Expanded implementation-level            For review
                                                                              requirements, contracts, workflows,
                                                                              test scenarios and traceability.
```
## Approval record
```text
 Role                                 Name                                    Decision                                 Date
 Project sponsor / instructor         TBD                                     Not approved                             TBD
 Project manager / team               TBD                                     Pending team review                      TBD
```
representative
```text
 Technical reviewer                   TBD                                     Pending technical review                 TBD
         Draft status. This document is an implementation-oriented specification draft. It does not claim that any feature has been
         implemented, tested, benchmarked or approved. Requirements labelled PROPOSED or TBD must be ratified before they
         become the team baseline.
```
## HOW TO READ THIS SRS
This SRS uses the updated Group 03 Midterm Engineering Report as the primary source for product goals, release boundaries, feature descriptions, user flows and conceptual design. The two handoff files provide additional F1 intent, parameter, tool-contract, orchestrator and unresolved-work details. The earlier Master Prompt is used as a completeness checklist, not as a source of product facts.
```text
 Label                                              Meaning                                               Engineering treatment
 BASELINE                                           Explicitly stated in                                  Current project proposal baseline; confirm in team
                                                    Team03_Proposal_Updated(1).pdf.                       review before implementation freeze.
 DESIGN                                             Present in context(2).md or                           Preserve, but do not assume formally approved or
                                                    cong_viec_can_lam(2).md as prior conceptual           implemented.
                                                    design.
 PROPOSED                                           Derived technical specification needed to make        Review and approve before freezing.
                                                    behavior testable or codeable.
 TBD                                                Source does not decide the point or contains an       Do not silently invent a product decision; resolve
                                                    unresolved conflict.                                  via the decision register.
 DEFERRED                                           Explicitly outside F1 MVP or planned after MVP.       Do not implement in F1 MVP unless scope changes
                                                                                                          are approved.
```
Normative terms: SHALL indicates mandatory behavior within the stated release scope; SHOULD indicates a recommended behavior; MAY indicates an optional capability. Normative wording does not turn an unapproved proposal into an approved project decision.

<!-- PDF page 4 -->
## Document map
```text
 Sections                                                               Content
 1–2                                                                    Introduction, product context, objectives, users, environment and boundaries
 3–4                                                                    Architecture, trust boundaries, release scope and feature ownership
 5                                                                      Functional requirements: 74 requirements across system, F1, F2 and F3
 6–8                                                                    Intent/slot contracts, business rules, validation and workflow/state
                                                                        management
 9–12                                                                   Tool/API contracts, data model, date/time rules and error recovery
 13–15                                                                  Security, non-functional requirements and external/UI interfaces
 16–18                                                                  Use cases, acceptance criteria and test scenarios
 19–21                                                                  Traceability, risks/decisions, roadmap, team roles and appendices
```
# 1. INTRODUCTION
## 1.1 Purpose
This document specifies the software requirements for StudyFlow AI, an intelligent academic learning assistant designed for undergraduate students. It defines externally visible behavior, component responsibilities, data contracts, business rules, state transitions, interfaces, security controls, quality requirements and verification conditions needed to implement and evaluate the system. It is intended as the shared implementation contract between frontend, backend, AI/NLU, QA and project coordination.
## 1.2 Scope
The product-level scope includes three connected student-facing features: F1 Intelligent Academic Planner, F2 Learning Assessment & Adaptive Revision, and F3 Daily AI Learning. The Initial Release / MVP includes only F1. F2 and F3 are planned Post-MVP core features. StudyFlow AI is a student support workflow, not a replacement for a full learning management system (LMS). The F1 MVP covers manual task entry, candidate extraction from authorized text-based PDF files, student review and confirmation of task data, availability declaration, weekly study-plan generation, plan viewing and student-approved rescheduling. It must present infeasible or unscheduled work honestly. Confirmed schedules must not change without student approval and a successful backend commit.
## 1.3 Project background and problem statement
The proposal describes undergraduate students balancing several courses, assignments, deadlines, independent study and learning materials. Their coordination problem includes consolidating deadlines, identifying feasible study time, responding to changes and reducing manual information transfer among tools. The proposal cites a team preliminary survey (n=17): 76.5% reported forgetting a deadline or completing work closer to it than planned during the previous four weeks; 70.6% selected study-time/deadline management as a time-consuming or difficult situation; 41.2% selected identifying weak topics; 76.5% selected finding explanations suitable for course materials; and 88.2% reported manually transferring information between study tools in the previous week. The report explicitly states that the questionnaire and anonymized response data were not supplied, so these figures cannot be independently audited from the report alone. They are contextual observations, not verified population estimates.
## 1.4 Objectives
```text
 ID                                Objective                            Release                                  Verification concept
 OBJ-01                            Generate feasible study schedules    F1 MVP                                   Hard-constraint tests and student
                                   from student-confirmed tasks,                                                 review.
                                   deadlines and availability; expose
                                   unscheduled work.
 OBJ-02                            Reduce manual coordination by        F1 MVP                                   Task capture and extraction-review
                                   supporting manual and authorized                                              tests.
                                   text-PDF task capture.
 OBJ-03                            Allow students to inspect and        F1 MVP                                   Approval, rejection, stale-proposal
                                   approve proposed schedule changes.                                            and commit tests.
```

<!-- PDF page 5 -->
```text
 ID                                    Objective                             Release                                    Verification concept
 OBJ-04                                Assess students using source-         F2 Post-MVP                                Human-reviewed question/key and
                                       grounded quizzes with verified                                                   grading evaluation.
                                       answer keys and deterministic
                                       grading.
 OBJ-05                                Provide source-grounded               F3 Post-MVP                                Evidence-support and outcome-
                                       explanations and progressive hints,                                              confirmation tests.
                                       with student-confirmed session
                                       outcomes.
 OBJ-06                                Coordinate later feature handoffs     Post-MVP integration                       Handoff and authorization/approval
                                       without silently changing confirmed                                              tests.
                                       plans.
```
## 1.5 Intended audience
- Project manager and team members coordinating requirements and release scope.
- Frontend developers implementing the web UI and confirmation workflows.
- Backend developers implementing task, availability, scheduling, persistence and APIs.
- AI/ML engineers implementing PDF text extraction, NLU/LLM adapters and later source-grounded features.
- QA engineers deriving unit, contract, integration, end-to-end and AI evaluation tests.
- Academic evaluators reviewing problem fit, design consistency, feasibility and evidence.
## 1.6 Definitions and abbreviations
```text
 Term                                                                        Definition
 SRS                                                                         Software Requirements Specification.
 MVP / Initial Release                                                       Minimum viable first release; F1 is the only included feature.
 LLM / NLU                                                                   Large Language Model / Natural Language Understanding component used
                                                                             for candidate interpretation or suitable language tasks.
 Orchestrator                                                                Shared coordination layer for routing, dialogue context, clarification, tool
                                                                             dispatch and safe handoffs.
 Intent                                                                      Detected user goal, e.g. CREATE_TASK or GENERATE_STUDY_PLAN.
 Slot / parameter                                                            Named value extracted from a message, e.g. deadline_date or
                                                                             duration_minutes.
 AcademicTask                                                                A unit of academic work with a deadline and estimated/remaining effort; not
                                                                             itself a calendar interval.
 PlannedStudyBlock                                                           A specific start/end interval allocated to an AcademicTask.
 StudyPlan                                                                   A set of proposed or confirmed study blocks for a planning period.
 Availability                                                                A time interval in which the student declares they can study.
 Busy interval / commitment                                                  A time interval that must not be used for planning; a dedicated
                                                                             FixedCommitment entity is not yet approved.
 TaskCandidate                                                               Unconfirmed task data from manual input or PDF extraction.
 PendingAction                                                               Persisted conversational workflow context awaiting clarification or another
                                                                             user decision.
 ValidatedCommand                                                            Normalized, entity-resolved and authorized operation input prepared by
                                                                             trusted application logic.
 Proposal                                                                    A non-final draft of a change; it is not a confirmed schedule.
 Approval evidence                                                           A trusted record binding an explicit student decision to a specific proposal and
                                                                             version.
 Commit                                                                      Transactional persistence of an approved and revalidated change.
 Idempotency                                                                 Property ensuring retries of the same logical write do not create duplicate
                                                                             effects.
 Half-open interval                                                          Interval [start, end) that includes start and excludes end; adjacent blocks may
                                                                             touch without overlapping.
 Post-MVP                                                                    Planned later release, not part of F1 Initial Release.
```
## 1.7 Source documents and references
```text
   1.        Team03_Proposal_Updated(1).pdf — Midterm Engineering Report, StudyFlow AI, Group 03, October 2026, 28
             pages. Primary source for project context and proposal baseline.
   2.        context(2).md — StudyFlow AI context handoff, version 1.1, 04 November 2026. Primary source for prior F1 design
             context and unresolved design details.
```

<!-- PDF page 6 -->
```text
   3.      cong_viec_can_lam(2).md — current task register, 04 November 2026. Primary source for priorities, dependencies
           and unresolved work.
   4.      StudyFlow_AI_SRS_Master_Prompt(1).pdf — completeness and SRS structure guidance; not an independent
           source of project facts.
        Source precedence. Use the updated proposal for project scope and stated product behavior. Use context/worklist for
        lower-level technical design only where it does not contradict the proposal. Record unresolved details as TBD or
        PROPOSED.
```
# 2. OVERALL SYSTEM DESCRIPTION
## 2.1 Product perspective
StudyFlow AI is a web application organized around a student-facing interface, a shared orchestration layer, three feature modules, and shared academic records plus authorized course materials. The first release activates F1 only. The architecture should preserve clean boundaries so F2/F3 can be added later without allowing their recommendations or session records to bypass F1 validation and student approval.
## 2.2 Target users and user characteristics
```text
 User class                                           Needs / characteristics                                 Release interaction
 University student (primary and only confirmed       Undergraduate student coordinating multiple             F1 MVP: tasks, PDF import, availability, plans and
 actor)                                               courses, assignments, deadlines, weekly                 approvals. Post-MVP: quiz and guided learning.
                                                      availability and course materials. Uses Vietnamese
                                                      natural-language input and/or forms. Retains
                                                      decision authority.
 Project team / operator (internal stakeholder)       Maintains, tests and evaluates the product; no          Internal development/operations; runtime
                                                      separate administrative product role has been           permissions TBD.
                                                      specified.
 Instructor / evaluator (academic stakeholder)        Reviews project scope, design, implementation           No application use case is mandated by supplied
                                                      evidence and evaluation. Not a confirmed runtime        sources.
                                                      actor.
```
## 2.3 Product functions by release
```text
 Feature                                 Primary inputs                          Primary outputs                           Release
 F1 — Intelligent Academic Planner       Manual task fields; authorized text-    Confirmed AcademicTasks;                  Initial Release / MVP
                                         PDFs; availability; existing            proposed/confirmed StudyPlans;
                                         commitments; user constraints.          PlannedStudyBlocks; visible
                                                                                 unscheduled work; rescheduling
                                                                                 proposals.
 F2 — Learning Assessment &              Authorized course PDFs; selected        QuizAttempt; deterministic                Post-MVP
 Adaptive Revision                       topic; reviewed source-grounded         AssessmentResult;
                                         questions; student responses.           TopicPerformance;
                                                                                 RevisionRecommendation.
 F3 — Daily AI Learning                  Learning goal/question; approved        Source-grounded explanations/hints;       Post-MVP
                                         study context; authorized course        reviewed summary; confirmed
                                         passages.                               SessionOutcome.
```
## 2.4 Operating environment
The proposal specifies a single web application. Browser support matrix, hosting platform, deployment topology, mobile responsiveness target, backend language/framework, database, object storage, authentication provider and LLM provider are not selected in the supplied materials. These are decision items, not known facts. Initial content-input support is text-based PDF extraction; OCR-heavy processing is excluded. Unreadable PDFs must fall back to manual entry.
## 2.5 Constraints
- F1 is the sole Initial Release / MVP feature. F2 and F3 must not become hidden dependencies for F1.
- Student confirmation is required for extracted essential task data before the task becomes eligible for scheduling.
- Proposed schedules and reschedules must be reviewed; autonomous schedule changes are not allowed.
- Scheduling constraints are enforced by deterministic application logic, not unconstrained LLM output.

<!-- PDF page 7 -->
- AI output is candidate/untrusted data and cannot set authenticated identity, authorize writes or prove approval.
- Only authorized course materials may be processed. Unrestricted external integrations and full LMS replacement are outside
MVP.
- Voice/video tutoring, OCR-heavy processing, essay grading and predictive mastery modelling are outside the stated MVP
scope.
## 2.6 Assumptions and dependencies
```text
 ID                                            Assumption / dependency                               Status and consequence
 ASM-01                                        A student identity can be authenticated and           Necessary proposed assumption; authentication
                                               associated with owned academic records.               method TBD.
 ASM-02                                        Course and task records can be isolated by            Required security design; persistence model TBD.
                                               authenticated owner.
 ASM-03                                        The system can extract text from supported PDFs       Baseline behavior in proposal; parser/library and
                                               without OCR.                                          file limits TBD.
 ASM-04                                        A trustworthy timestamp, locale and timezone are      Context design; source and fallback policy TBD.
                                               available to the Orchestrator.
 ASM-05                                        Busy intervals/commitments can be loaded by the       Proposal requires commitment checks;
                                               planner.                                              representation/source unresolved.
 DEP-01                                        F1 contract and scope decisions (P0) precede          Worklist dependency.
                                               production implementation.
 DEP-02                                        F2/F3 depend on validated F1 and separate             Post-MVP dependency.
                                               source/assessment/session ownership.
 DEP-03                                        Model selection follows contract/test dataset         No model/version currently approved.
                                               definition and benchmark.
```
## 2.7 Product boundaries
StudyFlow AI does not replace an LMS, guarantee academic success or mastery, autonomously alter a confirmed timetable, grade essays or predict mastery in the stated MVP. It does not assume unrestricted access to external calendars or institutional systems. Any such integration requires an explicit scope and authorization decision.
# 3. SYSTEM ARCHITECTURE AND COMPONENT RESPONSIBILITIES
## 3.1 High-level architecture
*Figure 3-1. Proposed system context; dashed boxes/arrows indicate Post-MVP modules. The logical architecture is: Student-facing Web UI → Shared Orchestrator → F1 Planner Backend → Shared Academic Records. LLM/NLU is an adapter invoked by the Orchestrator for candidate interpretation. F2/F3 are shown only to preserve the future system boundary.*

![Hình ảnh được trích xuất từ trang PDF 7](assets/srs/page-07-figure-000.jpg)

<!-- PDF page 8 -->
## 3.2 Component responsibilities
```text
 Component                                     Responsibilities                                       Must not do
 Student-facing Web UI                         Capture messages/forms/files; show candidate           Treat a draft as committed; trust client-supplied
                                               task fields and provenance; display tasks,             owner identity or approval state.
                                               availability and weekly calendar; show proposed
                                               plan, unscheduled work, conflicts and
                                               confirmation controls; display operation status.
 LLM/NLU adapter                               Classify intents; extract candidate slots; preserve    Select arbitrary tools/endpoints, invent IDs, assign
                                               original phrases; identify ambiguity and               permissions, validate ownership, schedule around
                                               unsupported requests; optionally propose               hard constraints or commit data.
                                               clarifications.
 Shared Orchestrator                           Load trusted request context; manage                   Let raw model JSON reach privileged writes.
                                               PendingAction; merge turns; coordinate
                                               validation; resolve references via backend;
                                               dispatch through allowlist; route approval to
                                               proposal; interpret ToolResult; recover safely.
 F1 Planner Backend                            Authenticate/authorize; enforce domain                 Rely on model assertions for ownership, approval
                                               validation; load tasks/availability/busy intervals;    or schedule feasibility.
                                               execute deterministic scheduling; produce
                                               plan/reschedule proposal; revalidate; commit
                                               transactionally; persist version/audit data.
 Shared Academic Records                       Persist owned task/planning data and later feature     Permit cross-user reads/writes or accept
                                               records; enforce referential integrity and             unvalidated bulk state from LLM.
                                               ownership boundaries.
 F2 module (Post-MVP)                          Retrieve authorized materials; generate candidate      Edit F1 schedule directly or infer mastery from
                                               MCQs; verify source/key; grade verified items          small/insufficient samples.
                                               deterministically; aggregate topic performance;
                                               produce evidence-based recommendations.
 F3 module (Post-MVP)                          Retrieve relevant passages; generate source-           Claim source support without evidence or save
                                               grounded explanations/hints; manage learning           unconfirmed summary as confirmed outcome.
                                               session; ask student to confirm session summary.
```
## 3.3 Trust boundaries and data ownership
- External user text, uploaded file contents and LLM/NLU output are untrusted inputs.
- Authentication identity, user ownership, authorization scope, timestamps and persisted entity IDs are trusted only when
provided by server-side services.
- The Orchestrator validates extraction shape and routes only an allowlisted operation. The F1 Backend repeats all security-
critical and domain checks.
- A plan proposal is not an approved plan. User approval must be associated with one proposal ID and exact version.
- A backend commit response is the source of truth for persistence status; UI state must follow it.

<!-- PDF page 9 -->
## 3.4 Main data/control sequence
*Figure 3-2. F1 weekly plan generation and student approval. Rejection has no schedule write; stale data requires a refreshed proposal.*
## 3.5 Future integration model
After F1 validation, an approved PlannedStudyBlock may supply course/topic context to F3. F3 owns confirmed SessionOutcome records. A student may request an optional quiz from F3 or directly; F2 independently retrieves authorized sources and owns verified questions, QuizAttempt and AssessmentResult. F2 may return a RevisionRecommendation to F1. F1 asks the student to confirm workload and deadline, checks feasibility and generates another proposal. No handoff may mutate a confirmed schedule without

![Hình ảnh được trích xuất từ trang PDF 9](assets/srs/page-09-figure-001.jpg)

<!-- PDF page 10 -->
student approval. A SessionOutcome records activity and is not proof of mastery. A quiz is optional and does not have to follow a guided session.
# 4. RELEASE SCOPE AND FEATURE BOUNDARIES
## 4.1 Initial Release / F1 MVP — in scope
- Single web application for student-facing F1 workflows.
- Manual academic task entry and task candidate review/confirmation.
- Import authorized text-based PDF and extract candidate task fields; preserve source page/text provenance where available.
- Manual fallback when a PDF is unreadable or does not contain sufficient task details.
- Availability declaration, including date-specific or weekday/weekly patterns as supported by the approved recurrence policy.
- Weekly automatic plan generation from confirmed tasks and time constraints.
- Deterministic deadline-first scheduling; priority resolves equal-deadline ordering.
- Check availability, existing commitments, deadlines, cumulative workload and interval overlaps.
- Show a proposed plan and all unscheduled work; ask student to approve, reject or request revision.
- Retrieve and display existing plans and weekly calendar.
- Propose rescheduling of a planned block; preserve the current confirmed schedule until approval and successful commit.
- Vietnamese natural-language input and multi-turn clarification for missing/ambiguous information, as supported by the
Orchestrator design.
## 4.2 Explicitly out of F1 MVP / deferred
```text
 Capability                                           Release treatment                             Reason / notes
 F2 quiz, grading and adaptive revision               DEFERRED — Post-MVP                           Planned after F1 validation.
 F3 guided learning, progressive hints and            DEFERRED — Post-MVP                           Planned after F1 validation.
```
SessionOutcome
```text
 UPDATE_TASK / DELETE_TASK                            TBD scope; default defer from first           Context/worklist identify as open; proposal does
                                                      implementation slice                          not detail these as core F1 MVP workflows.
 CREATE_STUDY_BLOCK / manual placement                TBD scope; default defer                      Context/worklist identify as scope-dependent; do
                                                                                                    not silently include.
 Dedicated FixedCommitment entity                     TBD data-model decision                       Existing commitments must be checked, but a
                                                                                                    separate entity was not approved.
 Advanced recurrence                                  DEFERRED / TBD                                Only NONE/WEEKLY was discussed preliminarily;
                                                                                                    recurrence horizon and exceptions unresolved.
 LMS replacement / broad calendar                     OUT OF SCOPE                                  Explicit proposal boundary.
```
synchronization
```text
 Autonomous schedule changes                          OUT OF SCOPE                                  Student approval required.
 Unrestricted external integrations                   OUT OF SCOPE                                  Explicit proposal boundary.
 Voice/video tutoring; OCR-heavy PDF processing       OUT OF SCOPE for MVP                          Explicit proposal boundary; unreadable PDFs use
                                                                                                    manual fallback.
 Essay grading; predictive mastery modelling          OUT OF SCOPE                                  Explicit proposal boundary.
 Institution-wide administration or lecturer portal   TBD / not specified                           No confirmed actor or use case in source.
```
## 4.3 Change control
Any feature moved into or out of MVP requires a recorded scope decision, impact assessment, updated requirement IDs/traceability and revised acceptance criteria. The existence of an intent name or mockup does not automatically mean the capability is part of MVP.
# 5. FUNCTIONAL REQUIREMENTS
The requirements below are atomic and testable. BASELINE means stated by the updated proposal; DESIGN means present in the F1 design handoff; PROPOSED means a concrete engineering rule added to make behavior implementable. Priority P0 is required to freeze the F1 design, P1 is implementation/release critical after P0 decisions, and P2 is deferred or Post-MVP.

<!-- PDF page 11 -->
## 5.1 System-wide requirements
```text
ID                Requirement                                              Priority     Source / status         Verification
SYS-FR-001        The system SHALL provide                                      P1      BASELINE                UI/E2E
                  a single student-facing
                  web application for the in-
                  scope Initial Release
                  workflows.
SYS-FR-002        The system SHALL accept                                       P1      DESIGN                  E2E
                  Vietnamese natural-
                  language requests and
                  structured form input for
                  F1 workflows.
SYS-FR-003        The system SHALL route                                        P0      DESIGN                  Integration
                  every request through the
                  Shared Orchestrator
                  before invoking an F1
                  operation.
SYS-FR-004        The system SHALL                                              P0      DESIGN                  Contract test
                  preserve the original user
                  message and trusted
                  request metadata
                  (timestamp, locale and
                  configured timezone) for
                  request processing.
SYS-FR-005        The system SHALL                                              P0      PROPOSED                Contract/E2E
                  distinguish READ, DRAFT,
                  PROPOSE and COMMIT
                  outcomes in its internal
                  result and user-facing
                  response.
SYS-FR-006        The system SHALL report                                       P1      PROPOSED                Review/audit
                  implementation/release
                  status only from actual
                  persisted or test evidence
                  and SHALL NOT represent
                  mockups or proposals as
                  implemented
                  functionality.
```
## 5.2 F1 — Task capture and confirmation
```text
ID                Requirement                                              Priority     Source / status         Verification
F1-TASK-001       The system SHALL allow a                                      P1      BASELINE                UC-F1-01 / TC-01
                  student to submit a task
                  manually with title, course
                  reference/name, start
                  date, deadline, priority
                  and estimated effort.
F1-TASK-002       The system SHALL create                                       P0      BASELINE                UC-F1-01 / TC-02
                  task input as a
                  candidate/draft until
                  required fields have been
                  validated and the student
                  has confirmed the entered
                  or extracted essential
                  details.
F1-TASK-003       The system SHALL retain                                       P0      DESIGN                  Contract test
                  candidate values
                  separately from trusted,
                  normalized task values
                  until validation and
                  confirmation complete.
F1-TASK-004       The system SHALL validate                                     P1      PROPOSED                Unit test
                  that task title is non-empty
                  after trimming whitespace.
F1-TASK-005       The system SHALL validate                                     P0      DESIGN                  Unit test
                  that estimated effort is a
                  positive number of
                  minutes before a task is
                  eligible for scheduling.
```

<!-- PDF page 12 -->
```text
 ID               Requirement                                              Priority     Source / status         Verification
 F1-TASK-006      The system SHALL validate                                     P0      DESIGN                  Unit test
                  that remaining effort,
                  when supplied, is non-
                  negative and does not
                  exceed estimated effort.
 F1-TASK-007      The system SHALL                                              P0      PROPOSED                Schema test
                  distinguish a task start
                  date from its deadline date
                  and SHALL NOT use the
                  deadline field as a
                  scheduled block end time.
 F1-TASK-008      The system SHALL resolve                                      P0      DESIGN                  Security/integration
                  a task reference against
                  records owned by the
                  authenticated student
                  before using it in an
                  update, search-result
                  action or rescheduling
                  workflow.
 F1-TASK-009      The system SHALL ask the                                      P1      DESIGN                  TC-10
                  student to select a task
                  when a name/reference
                  resolves to multiple
                  eligible records.
 F1-TASK-010      The system SHALL make                                         P0      DESIGN                  Scheduler unit test
                  only confirmed, active
                  tasks with positive
                  remaining effort eligible
                  for automatic scheduling.
```
## 5.3 F1 — PDF task extraction
```text
 ID               Requirement                                              Priority     Source / status         Verification
 F1-PDF-001       The system SHALL accept                                       P1      BASELINE                UC-F1-02 / TC-03
                  an authorized PDF file as a
                  task-capture input in the
                  F1 MVP.
 F1-PDF-002       The system SHALL extract                                      P1      BASELINE                Parser integration
                  text from supported text-
                  based PDF pages without
                  requiring OCR.
 F1-PDF-003       The system SHALL produce                                      P1      BASELINE                Extraction evaluation
                  task-field candidates from
                  extracted text and SHALL
                  identify which fields were
                  not found or remain
                  ambiguous.
 F1-PDF-004       The system SHALL retain                                       P1      PROPOSED                Data/traceability test
                  available source
                  provenance for extracted
                  candidates, including file
                  reference and page
                  number; text-span
                  provenance SHOULD be
                  retained where parser
                  output permits.
 F1-PDF-005       The system SHALL require                                      P0      BASELINE                UC-F1-02 / TC-04
                  student review and
                  confirmation of essential
                  extracted fields before the
                  associated task becomes
                  confirmed or schedulable.
 F1-PDF-006       When a PDF is unreadable,                                     P1      BASELINE                TC-05
                  image-only, encrypted or
                  yields insufficient text, the
                  system SHALL explain the
                  limitation and offer
                  manual task entry rather
                  than silently inventing
                  values.
```

<!-- PDF page 13 -->
```text
ID               Requirement                                             Priority     Source / status         Verification
F1-PDF-007       The system SHALL                                             P1      PROPOSED / TBD          Security review
                 preserve the original file as
                 an authorized source
                 reference only according
                 to an approved file-
                 retention policy; until
                 retention is decided,
                 implementation SHALL use
                 configurable retention and
                 avoid indefinite
                 duplication.
```
## 5.4 F1 — Availability management
```text
ID               Requirement                                             Priority     Source / status         Verification
F1-AVL-001       The system SHALL allow a                                     P1      DESIGN                  UC-F1-03
                 student to declare one or
                 more availability intervals
                 for a date or weekday.
F1-AVL-002       The system SHALL capture                                     P0      DESIGN                  Time contract
                 a configured timezone for
                 each availability
                 interpretation and SHALL
                 NOT rely on an LLM-
                 invented timezone.
F1-AVL-003       The system SHALL validate                                    P0      PROPOSED                Unit test
                 that each availability
                 interval has an end later
                 than its start after
                 timezone normalization.
F1-AVL-004       The system SHALL support                                     P1      DESIGN / TBD            Recurrence tests
                 NONE and WEEKLY
                 recurrence only if
                 recurrence is approved for
                 the MVP; recurrence end
                 dates, exceptions and
                 edits SHALL follow a policy
                 recorded in the decision
                 register.
F1-AVL-005       The system SHALL detect                                      P0      DESIGN                  TC-18
                 when a new or changed
                 availability interval
                 conflicts with a confirmed
                 study plan and SHALL NOT
                 silently alter the confirmed
                 plan.
F1-AVL-006       The system SHALL show                                        P1      PROPOSED                UI/E2E
                 the student the
                 normalized availability
                 interval before persisting
                 any ambiguous or
                 replacement availability
                 value.
F1-AVL-007       The system SHALL require                                     P0      DESIGN                  TC-19
                 explicit confirmation
                 before overwriting existing
                 availability when the
                 change replaces or
                 removes previously
                 declared intervals.
F1-AVL-008       The system SHALL make                                        P0      PROPOSED                Integration
                 availability intervals
                 available to the
                 deterministic scheduler
                 only after successful
                 persistence and
                 authorization checks.
```

<!-- PDF page 14 -->
## 5.5 F1 — Automatic planning and scheduling
```text
ID                Requirement                                              Priority     Source / status         Verification
F1-PLAN-001       The system SHALL allow a                                      P1      BASELINE                UC-F1-04
                  student to request a
                  weekly study plan for an
                  explicitly specified or
                  policy-default planning
                  period.
F1-PLAN-002       The system SHALL load                                         P0      BASELINE                Scheduler integration
                  eligible confirmed tasks
                  and the student’s effective
                  availability and existing
                  busy intervals from trusted
                  records before scheduling.
F1-PLAN-003       The system SHALL sort                                         P0      BASELINE                TC-14
                  eligible tasks by earlier
                  deadline first and SHALL
                  use task priority to resolve
                  equal-deadline ordering.
F1-PLAN-004       The system SHALL use a                                        P0      BASELINE                Determinism test
                  deterministic scheduling
                  procedure whose result is
                  reproducible for the same
                  task set, constraints, policy
                  configuration and data
                  snapshot.
F1-PLAN-005       The system SHALL allocate                                     P0      BASELINE / PROPOSED     Constraint test
                  study blocks only within
                  the intersection of the
                  planning period, task
                  eligibility window and
                  student availability.
F1-PLAN-006       The system SHALL exclude                                      P0      BASELINE                TC-15
                  busy intervals and existing
                  confirmed study blocks
                  from available scheduling
                  capacity.
F1-PLAN-007       The system SHALL enforce                                      P0      BASELINE                Boundary test
                  the half-open interval
                  overlap rule: A and B
                  overlap if start_A < end_B
                  AND start_B < end_A.
F1-PLAN-008       The system SHALL NOT                                          P0      BASELINE                TC-16
                  allocate a block that
                  extends beyond the
                  applicable task deadline
                  boundary.
F1-PLAN-009       The system SHALL account                                      P0      BASELINE / TBD          Workload test
                  for cumulative workload
                  and SHALL NOT allocate
                  more minutes to a task
                  than the amount
                  remaining under the
                  approved remaining-effort
                  policy.
F1-PLAN-010       When available capacity is                                    P0      BASELINE                TC-17
                  insufficient, the system
                  SHALL return explicit
                  unscheduled work with
                  task reference, remaining
                  minutes and a reason
                  where determinable.
F1-PLAN-011       The system SHALL                                              P0      BASELINE                TC-20
                  represent a generated
                  plan as PROPOSED until
                  valid student approval and
                  successful commit have
                  occurred.
```

<!-- PDF page 15 -->
```text
 ID                Requirement                                              Priority     Source / status         Verification
 F1-PLAN-012       The system SHALL present                                      P1      BASELINE                UI/E2E
                   proposed blocks, task
                   associations, dates/times,
                   total allocated effort and
                   unscheduled work for
                   student review.
 F1-PLAN-013       The system SHALL                                              P0      BASELINE / PROPOSED     TC-21
                   preserve the current
                   confirmed plan when a
                   proposal is rejected,
                   cancelled, expires or fails
                   validation.
 F1-PLAN-014       The system SHALL record                                       P0      PROPOSED                Persistence test
                   planning-period
                   boundaries,
                   policy/configuration
                   version and relevant input-
                   data version or fingerprint
                   used to generate each
                   proposal.
```
## 5.6 F1 — Study-plan retrieval
```text
 ID                Requirement                                              Priority     Source / status         Verification
 F1-GET-001        The system SHALL allow                                        P1      DESIGN                  UC-F1-05
                   the student to retrieve
                   study plans for a
                   requested date range.
 F1-GET-002        The system SHALL                                              P0      BASELINE                TC-22
                   distinguish PROPOSED
                   from CONFIRMED plans in
                   returned data and UI
                   presentation.
 F1-GET-003        The system SHALL display                                      P1      BASELINE                UI inspection
                   the weekly calendar and
                   associated blocks without
                   treating a proposal as a
                   confirmed calendar entry.
 F1-GET-004        When no plan exists for                                       P2      PROPOSED                Unit/E2E
                   the requested period, the
                   system SHALL return an
                   empty result with a clear
                   next action rather than an
                   error.
```
## 5.7 F1 — Rescheduling
```text
 ID                Requirement                                              Priority     Source / status         Verification
 F1-RSCH-001       The system SHALL allow                                        P1      BASELINE                UC-F1-06
                   the student to request a
                   change to an identified
                   confirmed
                   PlannedStudyBlock.
 F1-RSCH-002       The system SHALL resolve                                      P0      DESIGN                  TC-10
                   the target block from
                   authenticated student-
                   owned records; duplicate
                   or ambiguous references
                   SHALL require selection.
 F1-RSCH-003       The system SHALL retain                                       P1      DESIGN                  Unit/E2E
                   the existing duration when
                   the student changes only
                   the target date/time and
                   the block duration is
                   known, unless the student
                   explicitly requests a
                   duration change.
```

<!-- PDF page 16 -->
```text
ID               Requirement                                               Priority     Source / status         Verification
F1-RSCH-004      The system SHALL validate                                      P0      BASELINE                TC-23
                 a proposed block against
                 availability, commitments,
                 task deadline, task
                 remaining effort and
                 overlap constraints.
F1-RSCH-005      The system SHALL create a                                      P0      BASELINE                TC-24
                 revised proposal and
                 SHALL NOT modify the
                 confirmed block until
                 explicit approval and
                 successful commit.
F1-RSCH-006      If constraints changed                                         P0      PROPOSED                TC-25
                 after proposal creation,
                 the system SHALL reject
                 stale approval and request
                 a refreshed proposal.
```
## 5.8 F1 — Orchestrator and conversation management
```text
ID               Requirement                                               Priority     Source / status         Verification
F1-ORC-001       The system SHALL classify                                      P0      DESIGN                  NLU evaluation
                 each F1 request into an
                 allowlisted intent or mark
                 it
                 ambiguous/unsupported.
F1-ORC-002       The system SHALL retain                                        P0      DESIGN                  Contract test
                 original user expressions
                 for date, time, duration
                 and task references
                 alongside normalized
                 candidate values.
F1-ORC-003       The system SHALL                                               P0      DESIGN                  Contract test
                 represent extraction
                 output separately from a
                 validated execution
                 command.
F1-ORC-004       The system SHALL ask for                                       P0      BASELINE / DESIGN       TC-06 to TC-09
                 missing or ambiguous
                 information that blocks
                 safe execution and SHALL
                 NOT fabricate a deadline,
                 effort, task identity or
                 exact start time.
F1-ORC-005       The system SHALL merge                                         P0      DESIGN                  TC-26
                 short follow-up answers
                 into the uniquely matching
                 PendingAction; if multiple
                 pending actions are
                 plausible, it SHALL ask the
                 student to identify the
                 target.
F1-ORC-006       The system SHALL                                               P0      PROPOSED                TC-25
                 invalidate or supersede a
                 proposal when a relevant
                 field or underlying
                 scheduling constraint
                 changes.
F1-ORC-007       The system SHALL dispatch                                      P0      DESIGN                  Dispatch test
                 only a ValidatedCommand
                 through a deterministic
                 intent-to-operation
                 allowlist.
F1-ORC-008       The system SHALL route                                         P0      BASELINE / DESIGN       TC-27
                 approval only when one
                 active proposal ID and
                 expected version are
                 unambiguously identified.
```

<!-- PDF page 17 -->
```text
 ID               Requirement                                             Priority     Source / status         Verification
 F1-ORC-009       The system SHALL                                             P0      PROPOSED                Failure injection
                  interpret backend
                  ToolResult status faithfully
                  and SHALL NOT report a
                  write as successful before
                  the backend confirms
                  persistence.
```
## 5.9 F2 — Learning Assessment & Adaptive Revision (Post-MVP)
```text
 ID               Requirement                                             Priority     Source / status         Verification
 F2-FR-001        In a Post-MVP release, the                                   P2      BASELINE — POST-MVP     Source traceability test
                  system SHOULD retrieve
                  topic-relevant passages
                  from authorized text-
                  based course materials
                  with document/page/topic
                  metadata.
 F2-FR-002        In a Post-MVP release, the                                   P2      BASELINE — POST-MVP     Human review
                  system SHOULD draft
                  candidate multiple-choice
                  questions and answer keys
                  grounded in retrieved
                  passages.
 F2-FR-003        Only reviewed and source-                                    P2      BASELINE — POST-MVP     Eligibility test
                  verified questions with
                  verified answer keys SHALL
                  be eligible for automatic
                  grading.
 F2-FR-004        The system SHALL grade                                       P2      BASELINE — POST-MVP     Deterministic grading
                  objective responses
                  deterministically against
                  verified answer keys and
                  record a QuizAttempt and
                  AssessmentResult.
 F2-FR-005        The system SHALL                                             P2      BASELINE — POST-MVP     Formula/boundary test
                  calculate topic error rate
                  only when at least one
                  valid response exists and
                  SHALL label a topic
                  INSUFFICIENT_DATA when
                  no valid responses exist.
```
## 5.10 F3 — Daily AI Learning (Post-MVP)
```text
 ID               Requirement                                             Priority     Source / status         Verification
 F3-FR-001        In a Post-MVP release, the                                   P2      BASELINE — POST-MVP     Retrieval evaluation
                  system SHOULD retrieve
                  relevant passages from
                  authorized course
                  materials for a student
                  question or learning goal.
 F3-FR-002        The system SHALL ground                                      P2      BASELINE — POST-MVP     Evidence support test
                  explanations and
                  progressive hints in
                  retrieved evidence and
                  identify the limitation
                  when the material does
                  not support an answer.
 F3-FR-003        The system SHOULD                                            P2      BASELINE — POST-MVP     Session test
                  preserve session context
                  for follow-up questions
                  until the student ends or
                  the session expires under
                  an approved policy.
 F3-FR-004        The system SHALL present                                     P2      BASELINE — POST-MVP     UC-F3-01
                  a session summary for
                  student review before
                  saving a confirmed
                  SessionOutcome.
```

<!-- PDF page 18 -->
```text
 ID                           Requirement                                                Priority     Source / status                 Verification
 F3-FR-005                    The system SHALL NOT                                            P2      BASELINE — POST-MVP             State/safety test
                              store a declined or
                              unconfirmed summary as
                              a confirmed
                              SessionOutcome, and
                              SHALL NOT treat a
                              SessionOutcome as proof
                              of mastery.
```
Functional requirement count: 74.
# 6. INTENT CATALOG AND PARAMETER SPECIFICATION
The catalog reflects the eight intent names discussed in the F1 context. An intent name is a semantic label, not proof that an API exists. CREATE_STUDY_BLOCK, UPDATE_TASK and DELETE_TASK remain scope-dependent and are not assumed to be F1 MVP operations.
```text
 Intent                    Purpose                   Required extraction       Optional/context             Execution notes              Scope
                                                     fields (candidate)
 CREATE_TASK               Create a task candidate   title; course             remaining_minutes;           DRAFT candidate;             F1 MVP
                           from manual text or       reference/name;           priority if defaults         validate and ask
                           extracted PDF fields.     start_date;               approved; source_ref         student to confirm. No
                                                     deadline_date;                                         scheduling while
                                                     estimated_minutes                                      unconfirmed.
 UPDATE_TASK               Modify an existing        task_id;                  reason                       Resolve owned entity         TBD / default defer
                           confirmed task.           fields_to_update (at                                   and assess impact on
                                                     least one)                                             linked blocks/plans
                                                                                                            before write.
 DELETE_TASK               Remove or archive a       task_id                   reason                       Resolve owned entity;        TBD / default defer
                           task.                                                                            determine downstream
                                                                                                            plan/block behavior
                                                                                                            and confirmation
                                                                                                            policy.
 SET_AVAILABILITY          Declare one or more       date or weekday;          recurrence                   Normalize interval;          F1 MVP
                           available intervals.      start_time; end_time;     (NONE/WEEKLY                 confirm replacements;
                                                     timezone from trusted     preliminary)                 do not silently alter
                                                     config                                                 confirmed plans.
 GENERATE_STUDY_PLA        Generate a weekly plan    planning period           selection_mode               Load eligible tasks and      F1 MVP
 N                         proposal.                 start/end or approved     (ALL_ELIGIBLE /              constraints from DB;
                                                     default                   SELECTED_TASKS               return proposal plus
                                                                               preliminary); task_ids       unscheduled work.
                                                                               when selected
 RESCHEDULE_STUDY_B        Propose a change to an    block_id; target          duration; reason             Resolve block; preserve      F1 MVP
 LOCK                      existing confirmed        date/time or                                           duration from record if
                           block.                    constraints                                            not changed; propose
                                                                                                            only.
 GET_STUDY_PLAN            Retrieve plan(s) for a    date range or approved    status_filter                Read-only; clearly           F1 MVP
                           period.                   default                   (CONFIRMED/PROPOSE           separate proposal from
                                                                               D/ALL preliminary)           confirmed plan.
 CREATE_STUDY_BLOCK        Manually place a study    task_id; date;            plan_id                      Must follow constraint       TBD / default defer
                           block for a task.         start_time; end_time                                   validation and
                                                     or duration                                            proposal/approval flow
                                                                                                            if approved for scope.
```
## 6.1 Canonical vocabulary proposal
```text
 Existing variants                       Canonical proposal                    Rule / migration note                     Status
 candidate_id / task_candidate_id        task_candidate_id                     Use one stable field name in              PROPOSED
                                                                               contracts; accept legacy alias only at
                                                                               adapter boundary if needed.
 parameters / slots                      slots                                 Use slots for extracted                   PROPOSED
                                                                               conversational values; arguments for
                                                                               normalized operation input.
 end_date / deadline                     deadline_date                         Use deadline_date for the date-only       PROPOSED
                                                                               task deadline; map legacy end_date
                                                                               at ingestion boundary.
```

<!-- PDF page 19 -->
```text
 Existing variants                   Canonical proposal                     Rule / migration note                      Status
 duration / duration_minutes         duration_minutes                       Integer minutes for a duration; do         PROPOSED
                                                                            not confuse with a start/end
                                                                            timestamp interval.
 start_time/end_time                 start_at/end_at                        Use timezone-aware timestamps for          PROPOSED
                                                                            persisted intervals; local input strings
                                                                            remain candidates until normalized.
 task_id / task_reference            task_id after resolution               LLM extraction may carry                   PROPOSED
                                                                            task_reference_text; only backend
                                                                            resolves to persisted task_id.
```
## 6.2 Parameter definitions
```text
 Field                               Type                                   Required when                              Validation / notes
 title                               string                                 Task candidate creation                    Trim whitespace; not empty;
                                                                                                                       maximum length TBD.
 course_id                           opaque ID                              When a course record is resolved           Must belong to authenticated
                                                                                                                       student or be available in authorized
                                                                                                                       scope.
 course_name                         string                                 When course_id is not yet resolved         Candidate label only; duplicate
                                                                                                                       course names require selection.
 start_date                          date (YYYY-MM-DD)                      Task scheduling                            Inclusive eligibility start date; precise
                                                                                                                       semantics proposed and need
                                                                                                                       approval.
 deadline_date                       date (YYYY-MM-DD)                      Task scheduling                            Target completion date; exact day-
                                                                                                                       end boundary policy must be
                                                                                                                       approved.
 estimated_minutes                   integer                                Task scheduling                            Greater than zero.
 remaining_minutes                   integer                                Task scheduling / replanning               0..estimated_minutes;
                                                                                                                       update/progress source is TBD.
 priority                            enum or configured rank                Task scheduling                            Exact enum and rank direction are
                                                                                                                       TBD; stable tie-break required.
 planning_period_start/end           date                                   Generate/retrieve plan                     start <= end; MVP default length and
                                                                                                                       week boundary TBD.
 start_at/end_at                     timezone-aware timestamp               Availability or block interval             end_at > start_at; normalized to a
                                                                                                                       consistent timezone representation.
 duration_minutes                    integer                                When user gives a duration                 Greater than zero; end calculated
                                                                                                                       only after start is unambiguous.
 recurrence                          enum/object                            Availability recurrence                    NONE/WEEKLY mentioned
                                                                                                                       preliminarily; recurrence
                                                                                                                       horizon/exceptions TBD.
 task_reference_text                 string                                 Natural-language extraction                Untrusted phrase; resolve by
                                                                                                                       database query, never infer ID.
 source_ref                          object                                 PDF extraction                             File reference, page number and
                                                                                                                       extract span where available;
                                                                                                                       authorized access required.
```
## 6.3 Two-stage command validation
```text
 Stage                               Input                                  Permitted output                           Owner / enforcement
 Intent extraction                   Original text + limited conversation   Untrusted intent candidates, raw slot      LLM/NLU adapter; no side effects
                                     context                                values, source phrases,
                                                                            ambiguity/missing fields, provenance
 Validated command                   Extraction result + authenticated      Allowlisted operation, normalized          Orchestrator/shared validator;
                                     context + DB lookups + validators      arguments, resolved entity refs,           backend repeats
                                                                            validation status                          domain/authorization checks
 Execution result                    Validated command                      READ/DRAFT/PROPOSE/COMMIT/                 F1 Backend; persisted state is
                                                                            ERROR result with IDs, versions and        authoritative
                                                                            unscheduled work
```
# 7. BUSINESS RULES AND VALIDATION
## 7.1 Structural validation
- JSON must parse and conform to the selected schema version.

<!-- PDF page 20 -->
- Enum values must be allowlisted; unknown fields are rejected or safely ignored according to a versioned compatibility policy
(TBD).
- Date/time values must be normalized only after parsing; preserve original text for user-facing clarification.
- Numeric work estimates and durations must be integers in minutes and satisfy range constraints.
## 7.2 Semantic validation
```text
 Rule ID                                         Rule                                                   Status
 BR-STR-01                                       title is required for a task candidate and is not      PROPOSED
                                                 blank after trim.
 BR-SEM-01                                       estimated_minutes > 0.                                 DESIGN
 BR-SEM-02                                       If remaining_minutes is provided: 0 <=                 DESIGN
                                                 remaining_minutes <= estimated_minutes.
 BR-SEM-03                                       start_date <= deadline_date.                           DESIGN; canonical name proposed
 BR-SEM-04                                       An interval must have end strictly later than start    PROPOSED
                                                 after normalization.
 BR-SEM-05                                       A duration is positive; the system calculates an end   PROPOSED
                                                 only when start and timezone are unambiguous.
 BR-SEM-06                                       Unknown/missing task deadline or effort prevents       DESIGN / TBD
                                                 scheduling unless an approved default/exception
                                                 policy exists.
 BR-SEM-07                                       A vague period such as morning/evening is not          DESIGN
                                                 converted into an exact time without a user-
                                                 approved policy or clarification.
```
## 7.3 Domain validation
```text
 Rule ID                                         Rule                                                   Enforced by
 BR-DOM-01                                       The entity must exist and belong to the                F1 Backend
                                                 authenticated user (or be explicitly shared under
                                                 an approved policy).
 BR-DOM-02                                       Only confirmed eligible tasks are scheduled.           F1 Backend / Scheduler
 BR-DOM-03                                       Candidate plan blocks must lie inside declared         Scheduler
                                                 availability and outside busy intervals.
 BR-DOM-04                                       No two blocks may overlap under half-open              Scheduler + DB constraint if selected
                                                 interval semantics.
 BR-DOM-05                                       A task block must not exceed its remaining             Scheduler
                                                 schedulable workload.
 BR-DOM-06                                       A task block must respect the task start/deadline      Scheduler
                                                 window.
 BR-DOM-07                                       When availability is insufficient, unscheduled work    Scheduler
                                                 is returned; the algorithm must not fabricate
                                                 capacity.
 BR-DOM-08                                       An availability change conflicting with a confirmed    F1 Backend / Orchestrator
                                                 schedule triggers explanation/replan; no silent
                                                 mutation.
 BR-DOM-09                                       Existing confirmed plans are not changed by            F1 Backend
                                                 proposal generation.
 BR-DOM-10                                       Before commit, the backend revalidates all             F1 Backend
                                                 constraints against current authoritative data.
```
## 7.4 Scheduler algorithm contract
The proposal specifies a deterministic heuristic: earlier deadlines first; task priority breaks equal-deadline ties. It allocates within availability while checking existing commitments, deadlines, cumulative workload and overlap. The following pseudocode turns that behavior into a contract while leaving unresolved policy constants configurable.

<!-- PDF page 21 -->
INPUTS planning_period confirmed_tasks[] availability_intervals[] busy_intervals[] confirmed_blocks[] scheduler_policy (versioned configuration)
# 1. Validate the planning period and timezone.
# 2. Select confirmed tasks with positive schedulable remaining effort and
eligibility intersecting the planning period.
# 3. Normalize all time intervals to one canonical instant representation.
# 4. Build free intervals = availability minus busy intervals minus existing
confirmed blocks; use half-open intervals [start, end).
# 5. Sort tasks deterministically by:
(deadline ascending, priority rank, stable task key) where priority rank direction and stable tie-break are policy decisions.
# 6. For each task in order:
a. Intersect free intervals with the task eligibility window. b. Allocate chunks according to configurable block-splitting policy. c. Never exceed the task's schedulable remaining minutes. d. Update free intervals after every allocation.
# 7. Return proposed blocks and unscheduled minutes/reasons per task.
# 8. Persist/return as PROPOSED; do not alter the confirmed schedule.
# 9. On approval, re-run all validations against current data before commit.
The following policy values are not decided in the sources and must remain configuration parameters until approved: week start day; default planning period; deadline end-of-day cutoff; priority enum/rank; block minimum/maximum/preferred duration; block splitting; daily workload cap; breaks/buffers; distribution strategy across days; treatment of already scheduled but incomplete workload; and deterministic final tie-break fields.
## 7.5 Interval semantics
Canonical overlap test. For half-open intervals A=[sA,eA) and B=[sB,eB), overlap(A,B) ⇔ sA < eB AND sB < eA. Adjacent intervals such as [09:00,10:00) and [10:00,11:00) do not overlap. This rule is stated in the updated proposal and references PostgreSQL OVERLAPS semantics.
## 7.6 Validation statuses
```text
 Status                                       Meaning                                              Next action
 READY                                        Candidate data passes structural/semantic checks     Continue to deterministic dispatch; READY is not
                                              and enough context exists to prepare a command.      approval.
 NEEDS_CLARIFICATION                          One or more fields or entity references are          Create/update PendingAction and ask a focused
                                              missing/ambiguous.                                   question.
 UNSUPPORTED                                  Request is outside the currently supported           Explain limitation and offer supported fallback.
                                              feature/scope.
 INVALID                                      Supplied value or relationship violates              Return validation details; ask for correction when
                                              schema/domain constraints.                           possible.
```
Validation status is not the same as workflow state (e.g. AWAITING_APPROVAL) or entity status (e.g. PROPOSED/CONFIRMED).

<!-- PDF page 22 -->
# 8. WORKFLOW AND STATE MANAGEMENT
## 8.1 Orchestrator processing stages
```text
 Stage                                         Responsibility                                         Output / control
 1. Input processing                           Preserve original message; attach trusted              UserMessage; context reference.
                                               timestamp, locale, timezone and authenticated
                                               user context; inspect pending actions.
 2. Intent classification                      Identify single, multiple, ambiguous or                Intent candidates, not commands.
                                               unsupported intent.
 3. Slot extraction                            Extract candidate values and original phrases;         ExtractionResult.
                                               attach provenance.
 4. Context management                         Match follow-up to pending action; handle edits,       Updated PendingAction or new action.
                                               cancellation, topic changes, expiry and version.
 5. Validation                                 Structural, semantic and domain validation;            READY / NEEDS_CLARIFICATION / UNSUPPORTED /
                                               resolve entities through backend.                      INVALID.
 6. Clarification                              Ask minimum question that unblocks execution;          User response merged into pending action.
                                               do not guess missing dates/effort/start times.
 7. Tool dispatch                              Select operation from static allowlist using           Tool invocation with trusted context.
                                               ValidatedCommand.
 8. Response handling                          Translate backend result; distinguish read, draft,     User-facing response consistent with persisted
                                               proposal, commit and error.                            status.
 9. Confirmation & persistence                 Collect explicit approval; bind it to                  Confirmed persisted records or safe rejection.
                                               proposal/version/user; revalidate then commit.
 10. Error recovery                            Map error to clarification, limited retry, replan or   No duplicate/stale writes.
                                               manual fallback.
```
*Figure 8-1. Orchestrator control flow with clarification loop and proposal/approval boundary.*
## 8.2 Workflow state definitions
```text
 State                                         Description                                            Terminal?
 RECEIVED                                      A new user message has entered the Orchestrator.       No
 EXTRACTING                                    Intent and candidate slots are being produced.         No
 VALIDATING                                    Structural, semantic and domain checks are             No
                                               running.
 AWAITING_CLARIFICATION                        Workflow waits for a required answer or entity         No
                                               selection.
 READY_TO_DISPATCH                             A validated, allowlisted command is ready.             No
 EXECUTING                                     Backend operation is in progress.                      No
 AWAITING_APPROVAL                             A proposal is available and awaiting a specific        No
                                               student decision.
 COMMITTING                                    Backend is revalidating and transactionally            No
                                               applying approved changes.
 COMPLETED                                     Operation completed; result reflects backend           Yes
                                               state.
 REJECTED                                      Student rejected a proposal; no proposal changes       Yes
                                               committed.
 CANCELLED                                     Pending workflow was cancelled.                        Yes
 EXPIRED                                       Pending action or proposal passed its expiry policy.   Yes
 FAILED                                        Unrecoverable or non-retryable error occurred.         Yes
 UNSUPPORTED                                   Request is outside current supported scope.            Yes
```

![Hình ảnh được trích xuất từ trang PDF 22](assets/srs/page-22-figure-003.jpg)

<!-- PDF page 23 -->
## 8.3 State transition table
```text
 Current state            Event                    Guard                      Action                     Next state                Side effect
 RECEIVED                 Message accepted         Trusted user context       Preserve message;          EXTRACTING                No write
                                                   exists                     inspect PendingAction
 EXTRACTING               Extraction result        Schema invalid             Reject model output;       FAILED or clarification   No write
                                                                              bounded retry/fallback
 EXTRACTING               Candidate intent/slots   Extraction available       Run validators             VALIDATING                No write
 VALIDATING               Missing/ambiguous        Required info              Create/update              AWAITING_CLARIFICAT       No write
                          field                    unresolved                 PendingAction; ask         ION
                                                                              question
 AWAITING_CLARIFICAT      User replies             One pending action         Merge answer with          EXTRACTING /              No write
 ION                                               matches uniquely           provenance; revalidate     VALIDATING
 AWAITING_CLARIFICAT      User replies             Multiple pending           Ask user to choose         AWAITING_CLARIFICAT       No write
 ION                                               actions match              target action              ION
 VALIDATING               Valid command            All checks pass            Create                     READY_TO_DISPATCH         No write
                                                                              ValidatedCommand
 READY_TO_DISPATCH        Dispatch                 Operation is allowlisted   Call backend with          EXECUTING                 Depends on operation
                                                                              trusted identity                                     type
 EXECUTING                READ result              Backend returns            Format retrieved data      COMPLETED                 Read only
                                                   success
 EXECUTING                DRAFT result             Candidate persisted as     Display fields and         AWAITING_APPROVAL         Draft only
                                                   draft                      request confirmation       or COMPLETED
                                                                              as required
 EXECUTING                PROPOSE result           Proposal created           Display proposal,          AWAITING_APPROVAL         No confirmed-plan
                                                                              version and                                          mutation
                                                                              unscheduled work
 AWAITING_APPROVAL        Approve                  Exact                      Create approval            COMMITTING                Not yet committed
                                                   proposal/version/user      evidence and request
                                                   match; not expired         backend revalidation
 AWAITING_APPROVAL        Reject/cancel            Target proposal            Record                     REJECTED / CANCELLED      No commit
                                                   uniquely known             decision/cancel;
                                                                              preserve old confirmed
                                                                              state
 COMMITTING               Revalidation passes      Current data still         Commit within              COMPLETED                 Write allowed
                                                   compatible                 transaction using
                                                                              idempotency
 COMMITTING               Stale/conflict           Version or constraints     Reject approval;           FAILED /                  No stale commit
                                                   changed                    regenerate proposal or     AWAITING_APPROVAL
                                                                              clarify
 Any nonterminal          Expiry                   Expiry policy reached      Mark action/proposal       EXPIRED                   No write
                                                                              expired
 Any nonterminal          Topic change             New intent is not a        Keep/cancel pending        RECEIVED                  No unintended write
                                                   continuation               action per policy; do
                                                                              not merge unrelated
                                                                              message
```
## 8.4 PendingAction lifecycle
- Create PendingAction only when a workflow must survive a user turn (clarification, entity selection or approval).
- Persist intent, collected slots, missing/ambiguous fields, original expressions, provenance, workflow state, version, owner,
created_at and expires_at.
- A user correction increments the action version and triggers revalidation; relevant edits invalidate any derived proposal.
- A short answer such as “19h” may be merged only when one pending action clearly requests a start time and no competing
action is plausible.
- “Đồng ý” may approve only one uniquely identified active proposal; otherwise ask which proposal the student means.
- Expiry, cancellation, rejection and topic-switch behavior must be explicit; never auto-commit on expiry.
## 8.5 Multi-intent dependencies
For MVP, process only explicit, safely orderable intents. Example: “Tôi rảnh thứ Hai 08:00–11:00, lập lịch tuần sau.” The system must first normalize and confirm the availability change if required by replacement/conflict policy, persist it, then generate the weekly plan using the persisted availability. The second operation must not consume an unconfirmed availability candidate. Complex parallel workflows are outside current scope.

<!-- PDF page 24 -->
# 9. TOOL CONTRACTS AND API REQUIREMENTS
The following are logical backend operations. The supplied documents do not select HTTP routes, HTTP methods, RPC transport, authentication protocol, framework or versioning scheme. Names below are operation identifiers, not claims of existing endpoints.
```text
    Operation                     Type                         Purpose                          Input contract                   Output contract
    create_task_candidate         DRAFT                        Create candidate task from       Authenticated user;              candidate_id, DRAFT status,
                                                               manual/PDF extraction.           candidate fields;                missing fields, validation
                                                                                                provenance.                      errors,
                                                                                                                                 confirmation_required.
    confirm_task                  COMMIT / state transition    Promote valid candidate to       candidate_id, expected           task_id, CONFIRMED status,
                                                               confirmed AcademicTask.          candidate version, explicit      canonical fields.
                                                                                                confirmation evidence.
    search_tasks                  READ                         Search owned tasks by            query and filters, pagination.   Task summaries plus
                                                               query/course/status.                                              disambiguation candidates;
                                                                                                                                 no cross-user leakage.
    set_availability              DRAFT/COMMIT (policy TBD)    Create or replace availability   Date/weekday, start/end,         Normalized availability and
                                                               intervals.                       recurrence, trusted              impact/conflict warning;
                                                                                                timezone, expected version       persisted only under
                                                                                                if replacing.                    approved confirmation
                                                                                                                                 policy.
    generate_study_plan           PROPOSE                      Generate weekly schedule         Planning period, selection       plan_id, version, PROPOSED
                                                               proposal.                        mode, optional owned             status, blocks, unscheduled
                                                                                                task_ids.                        work, input
                                                                                                                                 snapshot/version.
    get_study_plan                READ                         Retrieve proposal or             Date range, status filter.       Plan metadata and blocks,
                                                               confirmed plan.                                                   explicitly separated by
                                                                                                                                 status.
    propose_reschedule            PROPOSE                      Create revised proposal for      Owned block_id, target           New proposal/version,
                                                               an existing block.               time/constraints, reason         proposed block changes,
                                                                                                optional.                        conflicts/unscheduled
                                                                                                                                 impact.
    approve_study_plan            COMMIT                       Approve and persist exact        plan_id, expected_version,       CONFIRMED result, new
                                                               proposal version after           approval                         version, committed blocks;
                                                               revalidation.                    evidence/reference,              or structured stale/conflict
                                                                                                idempotency key.                 error.
    reject_proposal               DECISION (proposed logical   Record rejection and keep        proposal_id,                     REJECTED status; no plan
                                  op)                          confirmed state unchanged.       expected_version, explicit       mutation.
                                                                                                reject event.
    cancel_pending_action         CONTROL (proposed logical    Cancel a unique pending          pending_action_id,               CANCELLED status; no
                                  op)                          action.                          expected_version.                domain write.
    extract_task_candidates_fro   DRAFT / AI adapter           Extract candidate fields from    file_ref, user scope,            Candidates with page/text
    m_pdf                                                      authorized text-PDF.             extraction options.              provenance, missing fields
                                                                                                                                 and confidence/uncertainty
                                                                                                                                 metadata; exact confidence
                                                                                                                                 policy TBD.
```
## 9.1 Contract envelope — illustrative only
```json
{
"schema_version": "1.0",
"operation": "generate_study_plan",
"arguments": {
"period_start": "2026-11-09",
"period_end": "2026-11-15",
"selection_mode": "ALL_ELIGIBLE",
"task_ids": []
},
"context_ref": "trusted-request-context-reference"
}
```

<!-- PDF page 25 -->
```json
{
"status": "PROPOSED",
"operation": "generate_study_plan",
"data": {
"plan_id": "opaque-server-generated-id",
"version": 1,
"study_blocks": [],
"unscheduled_work": [],
"requires_approval": true
},
"errors": []
}
```
Trust rule. The context reference, authenticated user ID, entity ownership and approval evidence are supplied/resolved by trusted services. They must not be accepted from arbitrary LLM-generated JSON or the browser as authoritative values.
## 9.2 Detailed minimum tool semantics
```text
    Operation                                    Validation / authorization                               Side effects and idempotency
    create_task_candidate                        Authenticated owner; title/field schema;                 Creates draft/candidate only. Retries with same
                                                 candidate source access.                                 request idempotency key should not create
                                                                                                          duplicate candidates; key strategy TBD.
    confirm_task                                 Candidate owned by user; candidate version               Promotes or creates confirmed task; duplicate
                                                 current; required fields valid; explicit confirmation.   confirmation returns same confirmed task or safe
                                                                                                          conflict.
    search_tasks                                 Authenticated owner filter mandatory; query              Read only; deterministic sort/pagination policy
                                                 never broadens data scope.                               TBD.
    set_availability                             Validate timezone/interval/recurrence; check             Must not overwrite without explicit confirmation
                                                 replacement semantics and conflict with                  where replacement occurs; conflict triggers replan,
                                                 confirmed plan.                                          never silent mutation.
    generate_study_plan                          Period valid; task IDs owned; load only eligible         Creates PROPOSED plan; does not replace active
                                                 confirmed tasks; deterministic scheduler.                confirmed plan. Repeated request
                                                                                                          semantics/versioning TBD.
    get_study_plan                               Authenticated owner and date range.                      Read only.
    propose_reschedule                           Block owned and active; duration/task constraints        Creates a new proposal referencing current plan
                                                 resolved; domain validation.                             version; no confirmed block mutation.
    approve_study_plan                           Exact proposal ID/version, user, expiry, one-time        Transactional commit; idempotency required;
                                                 decision, fresh constraint validation.                   stale proposal rejected; duplicate approval returns
                                                                                                          prior result, not duplicate blocks.
    reject_proposal                              Exact proposal/version and owner.                        Records rejection, no commit; duplicate rejection
                                                                                                          idempotent.
    cancel_pending_action                        Exact pending action/version and owner.                  Marks workflow cancelled; no domain data write.
```
## 9.3 Error response envelope
```json
{
"status": "ERROR",
"error": {
"code": "STALE_PLAN_VERSION",
"message": "The proposal is no longer current.",
"details": {"plan_id": "...", "expected_version": 2, "current_version": 3},
"retryable": false,
"correlation_id": "..."
}
```
}

<!-- PDF page 26 -->
# 10. DATA REQUIREMENTS AND DATA MODEL
*Figure 10-1. Conceptual entity model. Dashed entities/relationships are proposed or Post-MVP.*
## 10.1 F1 entities
```text
 Entity                            Scope/status                         Minimum attributes                      Semantics / constraints
 AcademicTask                      F1 core                              task_id, owner_id, course_id, title,    Task is academic work, not a
                                                                        start_date, deadline_date,              calendar interval. Only confirmed
                                                                        estimated_minutes,                      eligible records enter scheduler.
                                                                        remaining_minutes, priority, status,    deadline_date is proposed canonical
                                                                        created_at, updated_at                  name for source end_date/deadline.
 TaskCandidate                     Proposed F1 helper                   candidate_id, owner_id,                 Temporary candidate from
                                                                        source_type, candidate_fields,          manual/PDF extraction. Must be
                                                                        missing_fields, validation_status,      confirmed before promotion to
                                                                        provenance, version, created_at,        AcademicTask.
                                                                        expires_at
 Availability                      F1 core                              availability_id, owner_id, start_at,    Represents a free interval.
                                                                        end_at, recurrence_type,                Recurrence end/exception model is
                                                                        recurrence_end, timezone, status,       unresolved.
                                                                        version
 BusyInterval / FixedCommitment    F1 required concept; model TBD       commitment_id or source_ref,            Proposal requires checking existing
                                                                        owner_id, start_at, end_at, label,      commitments; separate
                                                                        source, status                          FixedCommitment entity has not
                                                                                                                been approved. Scheduler requires a
                                                                                                                unified busy-interval interface
                                                                                                                regardless of storage choice.
 StudyPlan                         F1 core                              plan_id, owner_id, period_start,        A plan groups proposed/confirmed
                                                                        period_end, status, version,            blocks. PROPOSED must not be
                                                                        policy_version, input_snapshot_ref,     confused with CONFIRMED.
                                                                        created_at, approved_at
 PlannedStudyBlock                 F1 core                              block_id, plan_id, task_id, start_at,   Specific allocated interval; many
                                                                        end_at, duration_minutes, status        blocks may belong to one task and
                                                                                                                one plan. Cardinality in proposal is
                                                                                                                conceptual and must be confirmed
                                                                                                                during schema freeze.
 PendingAction                     Proposed Orchestrator persistence    pending_action_id, owner_id, intent,    Supports multi-turn clarification and
                                                                        slots_json, missing_fields,             approval routing. Storage technology
                                                                        ambiguities, workflow_state,            TBD.
                                                                        version, expires_at
 ApprovalEvent                     Proposed security/audit record       approval_id, owner_id, proposal_id,     Binds decision to exact
                                                                        proposal_version, decision,             user/proposal/version. Exact
                                                                        created_at, expires_at,                 cryptographic/session evidence
                                                                        idempotency_key                         model TBD.
```

![Hình ảnh được trích xuất từ trang PDF 26](assets/srs/page-26-figure-005.jpg)

<!-- PDF page 27 -->
## 10.2 Post-MVP entities from proposal
```text
 Entity                                          Fields identified in proposal                          Ownership / purpose
 LearningMaterial                                material_id, source/file reference, topic and          Authorized source records used by F2/F3; detailed
                                                 source metadata (page/doc references                   ingestion model TBD.
                                                 recommended).
 QuizAttempt                                     attempt_id, quiz reference, student responses,         F2 owns attempts; detailed question/response
                                                 submission metadata.                                   schema TBD.
 AssessmentResult                                result_id, score, graded_count, incorrect_count        F2 owns objective grading result; deterministic
                                                 and topic summary.                                     comparison to verified answer keys.
 TopicPerformance                                topic_id, graded_count, incorrect_count,               F2 topic-level signal; not a mastery certificate.
                                                 last_assessed_at, question_refs.
 RevisionRecommendation                          recommendation_id, topic, performance trend,           F2 creates recommendation; F1 requires student
                                                 evidence references, rationale.                        confirmation of effort/deadline before schedule
                                                                                                        proposal.
 StudySession                                    session_id, goal, topic/context and authorized         F3 owns guided learning session context.
                                                 source references.
 SessionOutcome                                  outcome_id, confirmed summary and                      F3 saves only after student confirmation; not proof
                                                 source/session references.                             of mastery.
```
## 10.3 Relationships and cardinality
```text
 Relationship                                    Proposed cardinality                                   Notes
 Student → AcademicTask                          1 to 0..N                                              Owner isolation required.
 Student → Availability                          1 to 0..N                                              A user can declare multiple windows.
 AcademicTask → PlannedStudyBlock                1 to 0..N                                              One task may be split into many blocks; zero
                                                                                                        blocks allowed.
 StudyPlan → PlannedStudyBlock                   1 to 0..N                                              Plan is a container for allocated blocks.
 StudyPlan → ApprovalEvent                       1 to 0..N                                              Proposed audit representation; one accepted
                                                                                                        approval can commit a given version once.
 TaskCandidate → AcademicTask                    0..1 confirmed task                                    Promotion only after validation and confirmation.
 LearningMaterial ↔ Quiz                         many to many (future)                                  Source grounding/traceability.
 QuizAttempt → AssessmentResult                  1 to 1 (future proposal)                               Each submitted attempt produces one result if
                                                                                                        validly graded.
 StudySession → SessionOutcome                   1 to 0..1 (future proposal)                            No confirmed outcome if student declines
                                                                                                        summary.
```
## 10.4 Data integrity and lifecycle
- All user-owned records must carry or be query-scoped by owner identity derived from authentication.
- Foreign-key references must not cross owner scope unless an explicit sharing model is approved.
- TaskCandidate values must not be treated as confirmed AcademicTask values.
- PlannedStudyBlock intervals must be valid and linked to one task and one plan.
- A CONFIRMED plan must be committed atomically with its blocks and approval metadata.
- Proposal versions and the input data snapshot/version must be sufficient to detect stale approvals.
- Deletion semantics for tasks with dependent blocks/plans are not specified; UPDATE_TASK and DELETE_TASK remain out of
MVP pending decision.
# 11. TIME AND DATE HANDLING
## 11.1 Data representation
```text
 Value                                           Recommended representation                             Status / rule
 Task start/deadline                             Date-only ISO 8601: YYYY-MM-DD                         PROPOSED canonical form; source uses start date
                                                                                                        and end date (deadline).
 Persisted time interval                         Timezone-aware ISO 8601 timestamp / canonical          PROPOSED; storage representation TBD.
                                                 UTC instant plus original timezone metadata
 Timezone                                        IANA timezone identifier resolved from trusted         DESIGN; source of profile/configuration and
                                                 user profile/configuration                             fallback TBD.
 Duration                                        Integer minutes                                        DESIGN; positive.
 Original natural-language phrase                String preserved without normalization loss            DESIGN; keep provenance.
```

<!-- PDF page 28 -->
```text
 Value                                                  Recommended representation                              Status / rule
 Recurrence                                             Explicit recurrence object and timezone                 TBD beyond NONE/WEEKLY preliminary modes.
```
## 11.2 Natural-language date/time interpretation
- Relative terms (“tomorrow”, “next week”, “this Friday”) must be resolved using request timestamp and trusted timezone;
store the resolved value and original phrase.
- Week boundary and “next week” semantics must be defined by one approved locale policy; this is not selected in supplied
materials.
- “Morning”, “afternoon”, “evening”, “after class” and similar vague phrases are not exact start times. Ask a clarifying question
or show a candidate range for explicit confirmation.
- A duration such as “2 hours” does not define a start time. Ask for a start time if the operation requires one.
- If the task deadline contains only a date, the scheduler must use an approved day-end convention; the exact cutoff is TBD.
- Intervals crossing midnight require a clear date relationship. Do not silently infer a multi-day interval.
- Timezone changes after proposal creation must invalidate or revalidate affected proposals.
- Daylight-saving behavior is relevant only to supported zones that use it; zone database/version handling is TBD.
## 11.3 Vietnamese examples
```text
 User phrase                                            Safe interpretation                                     Required system behavior
 “Tao rảnh thứ Hai 8h–11h.”                             Candidate weekly/date interval only after               Resolve date context and timezone; confirm
                                                        interpreting the requested Monday.                      recurrence intent if not explicit.
 “Xếp tao 2 tiếng OOP tối mai.”                         Intent may be manual block request;                     Resolve date and task; ask start time; do not
                                                        duration=120; task ref=OOP; exact start missing.        choose 19:00 automatically.
 “19h.” after asking start time                         Candidate start time for the uniquely matching          Merge only if one action is waiting for start time;
                                                        PendingAction.                                          derive end using 120 minutes after confirmation.
 “Lập lịch học tuần sau.”                               Generate weekly plan; period dates require              Resolve period; use configured timezone; clarify if
                                                        approved week policy.                                   week policy cannot decide.
 “Tối thứ Sáu.”                                         Ambiguous period, not an exact time.                    Ask the student for a start time or choose a
                                                                                                                candidate explicitly.
 “Bài này hạn thứ Sáu.”                                 Deadline date candidate only.                           Resolve which Friday using request date/time; ask
                                                                                                                if more than one plausible date.
```
# 12. ERROR HANDLING AND RECOVERY
```text
 Code                             Trigger                          Owner                             Recovery                         Write semantics
 MISSING_REQUIRED_FIELD           Required                         Orchestrator / validator          Ask for minimum missing          No domain write unless draft
                                  candidate/execution field                                          information.                     creation explicitly allows
                                  absent.                                                                                             missing field.
 INVALID_PARAMETER                Type, enum, range or date        Validator / backend               Explain field and acceptable     No write.
                                  relationship invalid.                                              correction.
 ENTITY_NOT_FOUND                 Task/block/course not found      Backend                           Ask user to search or select     No write.
                                  in authenticated owner                                             again; do not reveal other
                                  scope.                                                             users’ records.
 AMBIGUOUS_ENTITY                 More than one owned entity       Orchestrator                      Present safe disambiguation      No write.
                                  matches reference.                                                 choices.
 TIME_CONFLICT                    Requested/proposed block         Scheduler/backend                 Return conflicting interval(s)   Do not alter confirmed plan.
                                  overlaps busy/confirmed                                            where safe; propose
                                  interval.                                                          alternatives.
 INSUFFICIENT_AVAILABILITY        Available capacity less than     Scheduler                         Return partial proposal and      Proposal may be partial; not
                                  remaining workload.                                                unscheduled                      necessarily operation error.
                                                                                                     minutes/reasons.
 APPROVAL_REQUIRED                Write/commit lacks valid         Backend                           Request explicit student         No commit.
                                  approval.                                                          confirmation for exact
                                                                                                     proposal.
 STALE_PLAN_VERSION               Proposal or underlying data      Backend                           Reject stale approval;           No stale write.
                                  changed since preview.                                             refresh/replan.
 PROPOSAL_EXPIRED                 Proposal passed expiry           Backend/Orchestrator              Create or fetch a current        No commit.
                                  policy.                                                            proposal.
 UNAUTHORIZED                     Authenticated actor lacks        Backend                           Return safe generic              No data leakage or write.
                                  access to entity/action.                                           message.
 LLM_INVALID_OUTPUT               Model output malformed or        Orchestrator                      Bounded retry, then ask user     No tool dispatch.
                                  fails extraction schema.                                           via form/manual input.
```

<!-- PDF page 29 -->
```text
 Code                        Trigger                          Owner                     Recovery                            Write semantics
 LLM_TIMEOUT                 Model does not return            Orchestrator              Retry under bounded policy          No duplicate operation.
                             within configured limit.                                   or manual fallback.
 PERSISTENCE_FAILURE         Database/object store write      Backend                   Return failure with                 Transaction
                             fails.                                                     correlation ID; retry only if       rollback/consistency
                                                                                        idempotent.                         procedure.
 CONCURRENT_MODIFICATIO      Task/availability/               Backend                   Reject and regenerate               No stale commit.
 N                           commitment changed while                                   proposal.
                             proposal pending.
 IDEMPOTENCY_CONFLICT        Same key used with different     Backend                   Return conflict; do not guess       No duplicate writes.
                             logical payload.                                           intent.
```
## 12.1 Retry policy
Retryable errors must be explicitly classified. The caller must use a bounded retry count and the same idempotency key for the same logical write. Do not retry validation errors, authorization failures, stale approvals or semantic conflicts unchanged. When persistence outcome is unknown after a network interruption, query the operation/idempotency result before attempting another commit.
## 12.2 Transaction and rollback
A successful approval commit should be atomic for the plan state, block set, approval record and version update. On failure, no partially confirmed plan may be exposed. Technical transaction rollback is a data-consistency mechanism; it is not a user-facing undo feature. Product undo semantics are not specified.
# 13. SECURITY AND AUTHORIZATION REQUIREMENTS
```text
 ID                               Security requirement                                                    Priority      Source/status
 SEC-001                          The backend SHALL derive the                                                 P0       PROPOSED
                                  acting user identity from an
                                  authenticated server-side
                                  context, never from LLM output
                                  or a client-supplied owner field.
 SEC-002                          Every read/write operation SHALL                                             P0       DESIGN
                                  enforce ownership/authorization
                                  for each referenced task, block,
                                  plan, availability and file.
 SEC-003                          The system SHALL treat user text,                                            P0       DESIGN
                                  PDF content and LLM output as
                                  untrusted data and validate them
                                  before use.
 SEC-004                          The Orchestrator SHALL dispatch                                              P0       DESIGN
                                  only allowlisted operations
                                  produced from validated
                                  commands.
 SEC-005                          The system SHALL NOT accept an                                               P0       BASELINE / DESIGN
                                  LLM-generated approval flag as
                                  evidence of student approval.
 SEC-006                          Approval SHALL be bound to                                                   P0       DESIGN / PROPOSED
                                  authenticated user, exact
                                  proposal identifier, exact version
                                  and validity window.
 SEC-007                          The backend SHALL revalidate                                                 P0       DESIGN
                                  ownership, proposal version and
                                  current scheduling constraints
                                  immediately before commit.
 SEC-008                          The system SHALL prevent cross-                                              P0       PROPOSED
                                  user data disclosure in entity
                                  search, conflict messages, logs
                                  and errors.
 SEC-009                          The system SHOULD record                                                     P1       PROPOSED / TBD
                                  security-relevant audit events for
                                  task confirmation, proposal
                                  decisions and commits, subject to
                                  retention/privacy policy.
```

<!-- PDF page 30 -->
```text
 ID                                   Security requirement                                                           Priority    Source/status
 SEC-010                              The system SHALL restrict PDF                                                        P0    BASELINE / PROPOSED
                                      access and processing to
                                      materials authorized for the
                                      requesting student and SHALL not
                                      expose extracted content outside
                                      that scope.
```
## 13.1 Threats and mitigations
```text
 Threat                                                Example                                                  Mitigation / required behavior
 Prompt injection in PDF                               A document contains text instructing the model to        Treat document text as data, not instructions;
                                                       expose data or call tools.                               isolate retrieval/extraction prompt; allowlist tools;
                                                                                                                validate outputs.
 Forged owner/entity ID                                LLM returns another user’s task_id.                      Backend ownership lookup; owner context never
                                                                                                                comes from model.
 Forged approval                                       LLM emits approval=true or user says “ok” without        Bind approval to exact proposal/version and
                                                       clear target.                                            authenticated interaction; ask clarification when
                                                                                                                target ambiguous.
 Stale proposal replay                                 Old approval is submitted after availability             Version/snapshot check; expiry; revalidate
                                                       changed.                                                 constraints; reject stale version.
 Duplicate commit/retry                                Network timeout causes approval action to be             Idempotency key and unique
                                                       sent twice.                                              constraint/transaction strategy.
 Cross-user data leak                                  Search result or error reveals another student’s         Owner filtering at backend query and safe non-
                                                       task.                                                    disclosing errors.
 Unauthorized file reference                           User submits file_ref not owned/shared with              File access check before parsing and before
                                                       them.                                                    serving extracted content.
```
# 14. NON-FUNCTIONAL REQUIREMENTS
```text
 ID                            Quality requirement                                           Priority     Source/status                  Verification / measure
 NFR-REL-001                   The scheduler SHALL                                                P0      BASELINE                       Constraint violation tests;
                               enforce availability,                                                                                     target violation count =
                               commitments, deadline,                                                                                    zero for enforced hard
                               workload and overlap                                                                                      constraints.
                               constraints
                               deterministically.
 NFR-REL-002                   The backend SHALL                                                  P0      BASELINE / PROPOSED            Failure injection and state
                               preserve confirmed-plan                                                                                   consistency checks.
                               consistency when proposal
                               generation, rejection,
                               cancellation or validation
                               fails.
 NFR-REL-003                   The system SHALL reject                                            P0      PROPOSED                       Concurrency/stale data
                               stale approvals when                                                                                      tests.
                               relevant plan or input data
                               has changed.
 NFR-TRC-001                   Extracted task candidates                                          P1      PROPOSED                       Provenance inspection.
                               SHALL retain source
                               file/page provenance
                               where available.
 NFR-TRC-002                   F2/F3 source-based                                                 P2      BASELINE — POST-MVP            Citation
                               outputs SHALL retain                                                                                      completeness/human
                               document/page/topic                                                                                       review.
                               references in Post-MVP.
 NFR-USA-001                   The UI SHALL allow                                                 P0      BASELINE                       Usability task walkthrough.
                               students to inspect
                               candidate task details and
                               proposed schedule
                               changes before confirming
                               them.
 NFR-USA-002                   Clarification prompts                                              P1      DESIGN                         Clarification evaluation.
                               SHOULD request only the
                               minimum information
                               needed to safely continue.
 NFR-SAFE-001                  The system SHALL                                                   P0      BASELINE                       Unsupported-source test.
                               communicate uncertainty
                               and unsupported evidence
                               rather than presenting it
                               as verified.
```

<!-- PDF page 31 -->
```text
 ID                        Quality requirement                                              Priority      Source/status                  Verification / measure
 NFR-SAFE-002              The system SHALL not                                                   P2      BASELINE — POST-MVP            F2/F3 safety tests.
                           represent SessionOutcome
                           or small quiz samples as
                           proof of subject mastery.
 NFR-MNT-001               Feature modules SHALL                                                  P1      BASELINE                       Architecture/contract
                           have separated                                                                                                review.
                           responsibilities and
                           exchange defined records
                           through the shared
                           orchestration layer.
 NFR-TST-001               The system SHALL expose                                                P1      PROPOSED                       Testability review.
                           stable seams for unit,
                           contract, integration and
                           end-to-end testing.
 NFR-PERF-001              The system SHOULD                                                      P1      PROPOSED                       Telemetry check;
                           record request latency by                                                                                     numerical target TBD.
                           orchestration stage and
                           backend operation.
 NFR-PERF-002              The system SHOULD                                                      P1      PROPOSED                       Telemetry check;
                           record PDF parsing and                                                                                        numerical target TBD.
                           candidate extraction
                           latency separately from
                           user review time.
 NFR-OBS-001               The system SHOULD                                                      P1      PROPOSED                       Log/trace inspection.
                           associate each request and
                           state transition with a
                           correlation ID.
 NFR-PRIV-001              The system SHALL apply an                                              P0      PROPOSED / TBD                 Policy and deletion tests.
                           approved retention and
                           deletion policy to
                           uploaded documents,
                           extracted text and
                           conversational context.
 NFR-CMP-001               The initial client SHALL be                                            P1      BASELINE / TBD                 Compatibility matrix after
                           delivered as a web                                                                                            decision.
                           application; exact
                           browser/device
                           compatibility targets
                           remain TBD.
       No invented performance targets. The supplied proposal and worklist do not approve response-time, throughput, uptime,
       concurrent-user, extraction-accuracy or model-quality thresholds. This SRS specifies what to measure but leaves numerical
       acceptance thresholds as TBD pending workload assumptions and benchmark evidence.
```
Non-functional requirement count: 16. Security requirement count: 10.
# 15. EXTERNAL AND USER INTERFACE REQUIREMENTS
## 15.1 Student-facing interface
```text
 UI area                                             Minimum content / behavior                                 State-aware controls
 Dashboard                                           Upcoming tasks, near deadlines, current week               Link to task detail/calendar; identify status and
                                                     summary and confirmed study plan summary.                  time range.
 Task entry                                          Manual form and natural-language entry; show               Save candidate; edit candidate; confirm; cancel.
                                                     title, course, start date, deadline, priority,
                                                     estimated effort and missing fields.
 PDF import                                          File selection, processing state, extracted                Review/edit each candidate; confirm selected
                                                     candidate list, source/page references and                 candidate(s); manual fallback.
                                                     uncertainty.
 Availability                                        Date/weekday interval entry, recurrence selection          Preview normalized values; confirm replacement;
                                                     where approved, timezone display.                          warn on confirmed-plan conflicts.
 Weekly planner                                      Calendar view with proposed/confirmed                      Generate proposal; inspect; approve; reject;
                                                     distinction, block/task labels, availability and           request revision.
                                                     conflicts.
 Rescheduling                                        Select a confirmed block and specify target                Show proposed change and impact;
                                                     date/time/constraint.                                      approve/reject.
 Errors and recovery                                 Plain-language error, affected field, safe next            Never show success when backend write failed or
                                                     action and retry indication.                               is unknown.
```

<!-- PDF page 32 -->
## 15.2 Existing proposal UI illustrations
*Figure 15-1. F1 dashboard mockup supplied in the updated Midterm Engineering Report. Illustrative design only; not implementation evidence.*
*Figure 15-2. F1 task-entry and weekly-calendar mockup supplied in the updated Midterm Engineering Report. Illustrative design only; not implementation evidence.*

![Hình ảnh được trích xuất từ trang PDF 32](assets/srs/page-32-figure-007.jpg)
![Hình ảnh được trích xuất từ trang PDF 32](assets/srs/page-32-figure-008.jpg)

<!-- PDF page 33 -->
## 15.3 Software interfaces
- UI → Orchestrator: user message, attachment references, conversation reference and client action; no trusted user identity in
payload.
- Orchestrator → LLM/NLU: constrained extraction/classification request; response validated as untrusted candidate data.
- Orchestrator → F1 backend: validated operation, normalized arguments and trusted identity context.
- F1 backend → academic records: authorized CRUD/query/transaction operations; storage technology TBD.
- F1 backend → UI/Orchestrator: structured ToolResult with status, IDs, versions, unscheduled work and safe error details.
- Future F2/F3 → Shared Orchestrator: typed records and handoff requests; module ownership preserved.
## 15.4 Communication and protocol decisions
REST/HTTP, WebSocket, server-sent events, RPC, token format, endpoint paths, API versioning strategy, file-upload transport, maximum payload size and CORS/session policy are not specified. The implementation team must select and document these in an architecture decision record before integration. Do not hard-code assumptions into client contracts without a decision.
# 16. USE CASE SPECIFICATIONS
The following use cases define the principal system interactions. UC-F1-01 to UC-F1-07 belong to the F1 Initial Release. UC-F2-01 and
### UC-F3-01 document later-release behavior only. The actor is the authenticated University Student unless otherwise stated. All
identifiers and API names in this section are logical SRS identifiers, not claims of deployed endpoints.
## 16.1 UC-F1-01 — Capture, review and confirm an academic task
```text
 Field                                                                  Specification
 Primary actor                                                          University Student
 Goal                                                                   Create a student-confirmed AcademicTask from manual or natural-language
                                                                        input.
 Release                                                                F1 Initial Release / MVP
 Preconditions                                                          Student is authenticated; the task form or conversation is available. Course
                                                                        reference may be selected or resolved.
 Trigger                                                                Student enters a task or asks the assistant to add one.
 Main flow                                                              1. Student submits task information. 2. Orchestrator classifies CREATE_TASK
                                                                        and extracts candidate slots. 3. Validator checks structure, types and
                                                                        relationships. 4. Missing/ambiguous fields are presented for clarification. 5.
                                                                        System shows a reviewable candidate, including normalized dates and
                                                                        estimated effort. 6. Student edits or confirms the candidate. 7. Backend
                                                                        revalidates ownership/context and persists a confirmed task. 8. UI displays
                                                                        the persisted task identifier and confirmed status.
 Alternative flows                                                      A. Course name maps to several courses: ask student to select. B. Deadline or
                                                                        effort is missing: preserve a draft candidate if draft policy permits, but do not
                                                                        schedule it. C. Duplicate-looking task: show potential matches and ask
                                                                        whether to create a separate task; duplicate-detection policy is TBD.
 Exception flows                                                        Invalid date order, non-positive effort or invalid type: return field-specific
                                                                        error; no confirmed task is written. Persistence failure: do not report success;
                                                                        retain retryable candidate only if its storage succeeded.
 Postconditions                                                         Success: one confirmed AcademicTask exists and is owned by the
                                                                        authenticated student. Failure: no confirmed task is created.
 Related requirements                                                   F1-TASK-001..010; F1-ORC-001..004; SEC-001..004.
 Related tests                                                          TC-01, TC-02, TC-06, TC-07, TC-11, TC-30.
```
## 16.2 UC-F1-02 — Import a task candidate from an authorized PDF
```text
 Field                                                                  Specification
 Primary actor                                                          University Student
 Goal                                                                   Extract candidate task information from a supported text-based PDF and
                                                                        confirm it.
 Release                                                                F1 Initial Release / MVP
 Preconditions                                                          Student is authenticated; selected file is accessible to that student; accepted
                                                                        file type and size policy is configured.
 Trigger                                                                Student uploads or selects an authorized PDF for task capture.
```

<!-- PDF page 34 -->
```text
 Field                                                 Specification
 Main flow                                             1. UI uploads or references the file. 2. Backend checks authorization and file
                                                       policy. 3. Parser extracts text from supported text-based pages. 4. AI/NLU
                                                       proposes task candidates and retains file/page provenance where available. 5.
                                                       Validator identifies unsupported, missing or ambiguous fields. 6. UI displays
                                                       candidates and source references. 7. Student selects, edits and confirms a
                                                       candidate. 8. Backend persists the confirmed task.
 Alternative flows                                     A. Several tasks are detected: show each as a separate candidate for
                                                       selection/review. B. Several date expressions conflict: ask the student to
                                                       identify the deadline. C. No task is detected: offer manual entry.
 Exception flows                                       Unauthorized file, encrypted PDF, image-only/unreadable PDF, parser timeout
                                                       or extraction failure: stop extraction, disclose the reason, offer manual entry;
                                                       do not invent task data.
 Postconditions                                        Success: confirmed task stored with available provenance. Failure: no
                                                       confirmed task stored; source file handling follows approved retention policy.
 Related requirements                                  F1-PDF-001..007; F1-TASK-002..006; SEC-010.
 Related tests                                         TC-03, TC-04, TC-05, TC-31.
```
## 16.3 UC-F1-03 — Declare or change availability
```text
 Field                                                 Specification
 Primary actor                                         University Student
 Goal                                                  Record free study intervals that the scheduler may use.
 Release                                               F1 Initial Release; recurrence details require decision.
 Preconditions                                         Student is authenticated; trusted timezone is available or requested from
                                                       configuration.
 Trigger                                               Student enters one or more free intervals in a form or natural language.
 Main flow                                             1. Student provides date/weekday and start/end time. 2. Orchestrator
                                                       extracts original expressions. 3. System resolves dates using trusted
                                                       timestamp/timezone and clarifies ambiguity. 4. Validator checks interval
                                                       order and recurrence scope. 5. System previews normalized availability and
                                                       identifies possible impact on confirmed plans. 6. Student confirms a
                                                       new/replacement interval. 7. Backend persists it and returns the effective
                                                       availability record.
 Alternative flows                                     A. New availability conflicts with a confirmed plan: explain the conflict and
                                                       offer a separate replan proposal; do not alter the confirmed plan. B. Weekly
                                                       recurrence is not approved/configured: accept a date-specific interval or
                                                       explain the limitation.
 Exception flows                                       Missing exact time, invalid interval or unknown timezone: ask for clarification.
                                                       Unauthorized or failed persistence: no change is applied.
 Postconditions                                        Availability is available to the scheduler only after successful persistence.
                                                       Existing confirmed plans remain unchanged unless a separately approved plan
                                                       is committed.
 Related requirements                                  F1-AVL-001..008; F1-ORC-004; SEC-001..004.
 Related tests                                         TC-08, TC-09, TC-18, TC-19, TC-32.
```
## 16.4 UC-F1-04 — Generate, inspect and approve a weekly study plan
```text
 Field                                                 Specification
 Primary actor                                         University Student
 Goal                                                  Produce a feasible proposed weekly schedule and persist it only after student
                                                       approval.
 Release                                               F1 Initial Release / MVP — principal use case
 Preconditions                                         Student is authenticated; eligible confirmed tasks and effective availability are
                                                       available; relevant busy intervals can be queried.
 Trigger                                               Student requests a weekly plan.
 Main flow                                             1. Student states a planning period or uses an approved default. 2.
                                                       Orchestrator validates request and resolves the period. 3. Backend loads
                                                       eligible confirmed tasks, remaining workloads, availability, busy intervals,
                                                       existing confirmed blocks and policy configuration. 4. Deterministic scheduler
                                                       sorts tasks by deadline and priority tie-break. 5. Scheduler allocates blocks
                                                       while enforcing hard constraints. 6. Backend returns proposed blocks and
                                                       explicit unscheduled work. 7. UI displays the proposal, total allocation,
                                                       affected tasks and constraints. 8. Student approves, rejects or requests
                                                       revision. 9. For approval, backend verifies authenticated user and exact
                                                       proposal/version, revalidates underlying data and constraints, and commits
                                                       atomically. 10. UI displays CONFIRMED only after successful persistence.
```

<!-- PDF page 35 -->
```text
 Field                                                Specification
 Alternative flows                                    A. Some work cannot fit: proposal includes partial allocations and
                                                      unscheduled minutes/reasons. B. Student requests changes: create a new
                                                      version/proposal; previous version becomes superseded where relevant. C.
                                                      Student rejects: proposal remains unconfirmed/rejected according to state
                                                      policy and confirmed plan remains unchanged.
 Exception flows                                      No eligible tasks, no availability, stale inputs, scheduler failure, persistence
                                                      failure or expired proposal: return accurate status; do not mutate confirmed
                                                      schedule.
 Postconditions                                       Success: approved plan and blocks are persisted as confirmed. Otherwise:
                                                      current confirmed plan remains unchanged.
 Related requirements                                 F1-PLAN-001..014; F1-ORC-003..009; SEC-005..007.
 Related tests                                        TC-12..TC-21, TC-25, TC-27, TC-33.
```
## 16.5 UC-F1-05 — Retrieve a study plan
```text
 Field                                                Specification
 Primary actor                                        University Student
 Goal                                                 Inspect proposed or confirmed blocks in a selected date range.
 Release                                              F1 Initial Release / MVP
 Preconditions                                        Student is authenticated.
 Trigger                                              Student opens the planner or asks to view a schedule.
 Main flow                                            1. Student selects a date range or approved default. 2. Backend queries only
                                                      the student’s authorized plan records. 3. System returns plans and blocks with
                                                      status, period, version and task references. 4. UI renders calendar entries with
                                                      proposed/confirmed distinction.
 Alternative flows                                    No plans exist: show empty state and a Generate Plan action. Only a proposal
                                                      exists: label it clearly as proposed and not confirmed.
 Exception flows                                      Invalid range or retrieval failure: show safe error and do not imply an empty
                                                      calendar if retrieval failed.
 Postconditions                                       No persistent data is changed.
 Related requirements                                 F1-GET-001..004; SEC-001..004.
 Related tests                                        TC-22, TC-30.
```
## 16.6 UC-F1-06 — Propose rescheduling of a confirmed study block
```text
 Field                                                Specification
 Primary actor                                        University Student
 Goal                                                 Change the date/time of an existing study block without bypassing approval.
 Release                                              F1 Initial Release / MVP
 Preconditions                                        Student is authenticated; target confirmed block belongs to the student and
                                                      can be resolved uniquely.
 Trigger                                              Student asks to move a study session/block.
 Main flow                                            1. Orchestrator resolves the target block. 2. If ambiguous, student selects one.
```
# 3. System collects new time/constraints and retains current duration if
appropriate. 4. Backend validates availability, commitments, task deadline, remaining effort and overlaps. 5. Backend creates a revised proposal referencing the current block and source version. 6. UI displays old and proposed times plus consequences. 7. Student approves or rejects. 8. On approval, backend revalidates and commits using concurrency/idempotency controls.
```text
 Alternative flows                                    Student asks for a different time after seeing proposal: create a new proposal
                                                      version and invalidate the old approval context. Student rejects: original
                                                      confirmed block remains.
 Exception flows                                      Block not found, unauthorized block, stale source data, conflict or expired
                                                      proposal: return appropriate error and do not alter the existing block.
 Postconditions                                       Success: new block state committed. Failure/rejection: original confirmed
                                                      block remains effective.
 Related requirements                                 F1-RSCH-001..006; F1-ORC-006..009; SEC-006..007.
 Related tests                                        TC-23..TC-25, TC-27, TC-28.
```

<!-- PDF page 36 -->
## 16.7 UC-F1-07 — Resolve clarification and pending action across turns
```text
 Field                                                 Specification
 Primary actor                                         University Student
 Goal                                                  Complete an incomplete request through multi-turn conversation without
                                                       misrouting the response.
 Release                                               F1 Initial Release / MVP
 Preconditions                                         A PendingAction exists or a new request has an unresolved field.
 Trigger                                               Student answers a clarification, corrects a value, cancels, or changes topic.
 Main flow                                             1. System asks a focused question for the blocking field. 2. PendingAction
                                                       stores intent, slots, missing fields, version and expiry. 3. Student replies (e.g.,
                                                       “19h”). 4. Orchestrator determines whether exactly one pending action
                                                       matches. 5. Answer is merged with provenance. 6. Validation runs again. 7.
                                                       System continues, asks a follow-up, or routes the validated command.
 Alternative flows                                     Several pending actions could match: ask which request the answer belongs
                                                       to. User corrects a prior slot: update pending version and revalidate. User
                                                       changes topic: suspend, cancel or retain previous action only according to
                                                       policy; do not apply unrelated text to it.
 Exception flows                                       Pending action expired or proposal superseded: explain and restart/retrieve
                                                       current request. User says “đồng ý” with no unique active proposal: ask which
                                                       proposal, or decline to commit.
 Postconditions                                        State reflects the exact request/decision; no unintended side effect occurs.
 Related requirements                                  F1-ORC-001..009; SYS-FR-004..005.
 Related tests                                         TC-06..TC-10, TC-26..TC-29.
```
## 16.8 UC-F2-01 — Complete a verified quiz and review revision priorities (Post-MVP)
```text
 Field                                                 Specification
 Primary actor                                         University Student
 Preconditions                                         Authorized course material and questions with reviewed, source-supported
                                                       answer keys are available for the selected topic.
 Main flow                                             Student selects topic → system displays eligible verified MCQs → student
                                                       submits responses → deterministic grading compares responses to verified
                                                       keys → system records QuizAttempt/AssessmentResult → topic metrics are
                                                       calculated → revision recommendations are presented with evidence.
 Alternatives/exceptions                               No verified questions or source support: explain limitation and do not grade
                                                       unsupported questions. No valid responses: mark INSUFFICIENT_DATA. Small
                                                       sample: do not claim mastery. Schedule update: F1 separately confirms
                                                       effort/deadline, validates feasibility, proposes and asks student approval.
 Postconditions                                        Assessment result and supported recommendation are recorded; no
                                                       confirmed schedule changes without F1 approval.
 Scope note                                            Post-MVP only; question formats beyond verified multiple-choice, essay
                                                       grading and predictive mastery modeling are excluded by proposal.
```
## 16.9 UC-F3-01 — Complete a source-grounded guided learning session (Post-MVP)
```text
 Field                                                 Specification
 Primary actor                                         University Student
 Preconditions                                         Authorized relevant course material is available. An approved F1 block may
                                                       optionally supply context.
 Main flow                                             Student starts session and states goal/question → F3 retrieves relevant
                                                       passages and metadata → F3 provides explanation/progressive hint grounded
                                                       in retrieved evidence → student follows up or ends session → system
                                                       presents summary → student reviews and confirms → F3 saves
                                                       SessionOutcome.
 Alternatives/exceptions                               Retrieved material does not support answer: state limitation and ask
                                                       clarification/additional material. Student declines summary: do not save as
                                                       confirmed outcome. Optional quiz handoff: route to F2 only on
                                                       request/approved flow.
 Postconditions                                        Confirmed SessionOutcome exists only after student confirmation. It is not an
                                                       AssessmentResult or proof of mastery.
 Scope note                                            Post-MVP only; voice/video tutoring and unsupported general-purpose
                                                       answers are out of scope.
```

<!-- PDF page 37 -->
# 17. ACCEPTANCE CRITERIA
Acceptance criteria below define observable release checks. They are proposed verification criteria derived from the proposal and design. Numerical performance thresholds remain TBD; hard scheduling invariants are not relaxed by that omission.
```text
 ID                                Acceptance criterion                      Related requirements                 Evidence required
 AC-001                            A student can manually enter a task       F1-TASK-001..003                     UI/E2E recording and persisted state
                                   and see a candidate before
                                   confirmation.
 AC-002                            A candidate with missing deadline or      F1-TASK-002, 005, 010                DB fixture and scheduler test
                                   effort is not eligible for automatic
                                   scheduling.
 AC-003                            A supported text PDF produces             F1-PDF-001..005                      Parser output, source references and
                                   reviewable task candidates with                                                review trace
                                   file/page provenance where
                                   available.
 AC-004                            An unreadable/image-only PDF              F1-PDF-006                           E2E evidence and database assertion
                                   triggers a manual-entry fallback and
                                   no fabricated confirmed task.
 AC-005                            A confirmed task cannot be                F1-TASK-008; SEC-001..002            Cross-user authorization test
                                   scheduled by another user’s request.
 AC-006                            Invalid/non-positive estimated effort     F1-TASK-005..006                     Unit test report
                                   is rejected before scheduling
                                   eligibility.
 AC-007                            Ambiguous task references require         F1-TASK-009; F1-RSCH-002             Conversation transcript and dispatch
                                   explicit selection before a                                                    log
                                   write/proposal.
 AC-008                            Availability values are normalized        F1-AVL-002..003                      Time parser/validator tests
                                   using trusted timezone and invalid
                                   intervals are rejected.
 AC-009                            A change to availability that conflicts   F1-AVL-005, 007                      Before/after database comparison
                                   with a confirmed plan does not
                                   silently change that plan.
 AC-010                            Scheduler uses deadline-first order       F1-PLAN-003                          Deterministic fixture with tied
                                   and priority only as the documented                                            deadlines
                                   equal-deadline tie-break.
 AC-011                            Repeated scheduling with identical        F1-PLAN-004, 014                     Repeatability test
                                   inputs, data snapshot and policy
                                   version yields identical output.
 AC-012                            Every allocated block falls within the    F1-PLAN-005..009                     Constraint validator report
                                   valid planning period and availability
                                   and respects task deadline and busy
                                   intervals.
 AC-013                            No two blocks overlap under half-         F1-PLAN-007                          Boundary and pairwise overlap tests
                                   open interval semantics.
 AC-014                            Insufficient capacity produces            F1-PLAN-010                          Partial-plan fixture
                                   explicit unscheduled
                                   minutes/reasons; it does not
                                   fabricate a fully scheduled result.
 AC-015                            A generated plan is displayed as          F1-PLAN-011..013                     UI plus persistence state trace
                                   PROPOSED until approval and
                                   successful commit.
 AC-016                            Rejecting, cancelling, expiring or        F1-PLAN-013; F1-RSCH-005             State/persistence regression test
                                   failing a proposal leaves the existing
                                   confirmed schedule unchanged.
 AC-017                            A reschedule proposal identifies its      F1-RSCH-001..004                     Proposal payload and scheduler tests
                                   source block and validates all
                                   applicable hard constraints.
 AC-018                            Approval for a wrong user, proposal,      F1-ORC-008; SEC-005..007             Security/concurrency tests
                                   version or expired context is
                                   rejected.
 AC-019                            Duplicate approval/retry does not         SEC-007; proposed idempotency        Replay test and unique persistence
                                   create duplicate commits or               rules                                evidence
                                   duplicate blocks.
 AC-020                            The UI reports success only after         F1-ORC-009; NFR-REL-002              Failure-injection test
                                   confirmed persistence;
                                   failure/unknown result is never
                                   shown as committed.
```

<!-- PDF page 38 -->
# 18. TESTING AND QUALITY ASSURANCE REQUIREMENTS
## 18.1 Test levels
```text
 Test level                        Purpose                                   Primary scope                            Required evidence
 Unit                              Verify pure validators, interval          Domain and scheduler                     Repeatable automated test output
                                   operations, sorting, allocation and
                                   status transitions.
 Contract                          Verify schemas, nullability, enums,       LLM/Orchestrator/backend                 Schema validation and compatibility
                                   request/result envelopes and version      boundaries                               report
                                   semantics.
 Integration                       Verify authorization, persistence, file   Component boundaries                     Integration logs and database
                                   parsing, orchestrator dispatch and                                                 assertions
                                   backend interactions.
 End-to-end                        Verify the complete student journey       F1 MVP                                   Reproducible scripted user journeys
                                   from message/form to confirmed
                                   persisted plan.
 Security                          Verify cross-user isolation, forged       All trust boundaries                     Security test results
                                   IDs, prompt injection, forged
                                   approval and replay protection.
 Regression                        Ensure changes do not violate             F1 workflows                             Versioned regression suite
                                   already approved requirements or
                                   alter confirmed schedules
                                   unexpectedly.
 AI/NLU evaluation                 Measure intent/slot extraction and        Extraction and clarification only        Frozen test set, annotations and
                                   candidate quality separately from                                                  metric report
                                   deterministic business correctness.
```
The test set SHALL separate development examples from a held-out evaluation set before comparing candidate models. Model selection must consider multi-intent handling, slot extraction, clarification, dispatch correctness and end-to-end behavior—not intent accuracy alone. No benchmark result is claimed by this SRS.
## 18.2 Test scenario matrix
The following 34 scenarios are the minimum initial matrix. Each test must include the user input, trusted request context, database fixtures, initial state, expected intent/slots/status/tool/state/response and allowed/forbidden side effects.
```text
 Test ID                           Scenario / input                          Expected result                          Forbidden side effect
 TC-01                             Complete manual task entry with           Candidate shown; after student           Scheduling an unconfirmed
                                   title, course, start/deadline, priority   confirmation, confirmed task stored.     candidate.
                                   and effort.
 TC-02                             Task has missing deadline or effort.      Missing field identified; task remains   Inventing a date/effort or scheduling.
                                                                             non-schedulable.
 TC-03                             Upload authorized text-based PDF          Extract candidate fields and source      Auto-confirming extracted values.
                                   with a recognizable assignment.           page; student review required.
 TC-04                             PDF has multiple task candidates.         Display separate candidates and          Combining unrelated tasks silently.
                                                                             request selection/review.
 TC-05                             PDF is image-only, encrypted or           Explain unsupported extraction and       Pretending OCR/text extraction
                                   unreadable.                               offer manual entry.                      succeeded.
 TC-06                             User says “Thêm bài OOP”, no              Ask only fields needed by                Creating confirmed task with
                                   remaining details.                        draft/confirmation; preserve             fabricated attributes.
                                                                             PendingAction.
 TC-07                             User enters negative or non-numeric       Structural/semantic validation error.    Persisting invalid workload.
                                   effort.
 TC-08                             User says “tối thứ Hai” without exact     Ask for an exact interval or approved    Choosing arbitrary 19:00.
                                   time.                                     configured default if one exists.
 TC-09                             User says “rảnh thứ Hai 8–11h”.           Resolve date/weekday and                 Treating availability as a study task or
                                                                             timezone; validate interval.             schedule change.
 TC-10                             Two tasks/blocks share similar            Show candidates and require explicit     Guessing an entity ID.
                                   names.                                    selection.
 TC-11                             User references an entity owned by        Non-disclosing authorization/not-        Revealing entity existence or details.
                                   another student.                          found response.
 TC-12                             Generate plan with complete eligible      Deterministic proposed plan              Directly committing confirmed
                                   tasks and availability.                   returned.                                schedule.
```

<!-- PDF page 39 -->
```text
Test ID                         Scenario / input                          Expected result                           Forbidden side effect
TC-13                           Distinguish “lập lịch tuần sau”, “xếp     Map respectively to                       Dispatching manual block when out
                                buổi OOP 8–10h”, “tôi rảnh 8–10h”.        GENERATE_STUDY_PLAN, scope-               of scope.
                                                                          dependent CREATE_STUDY_BLOCK,
                                                                          SET_AVAILABILITY.
TC-14                           Two tasks share deadline but have         Higher priority is ordered first per      Non-deterministic tie handling.
                                different priorities.                     approved priority convention.
TC-15                           Busy commitment overlaps an               Busy interval excluded from               Allocating a block inside busy time.
                                availability interval.                    scheduling capacity.
TC-16                           Task deadline lies inside requested       No proposed block extends beyond          Scheduling past deadline.
                                planning interval.                        deadline boundary.
TC-17                           Total remaining work exceeds free         Partial proposal with unscheduled         Claiming all work is scheduled.
                                time.                                     minutes/reasons.
TC-18                           Availability is changed so it conflicts   Warn; require replan proposal and         Mutating confirmed blocks
                                with confirmed blocks.                    approval.                                 automatically.
TC-19                           Availability replacement would            Preview and explicit confirmation         Overwriting availability silently.
                                remove existing intervals.                required.
TC-20                           Student views generated plan before       State is PROPOSED, not CONFIRMED.         Displaying proposal as persisted
                                approval.                                                                           confirmed calendar.
TC-21                           Student rejects, cancels or lets plan     Current confirmed plan unchanged.         Partial write to confirmed schedule.
                                proposal expire.
TC-22                           Retrieve a range with no plans versus     Empty state only for successful           Confusing failure with empty result.
                                retrieval backend failure.                empty query; safe error on failure.
TC-23                           Reschedule a block to a conflicting       Reject or return alternative proposal     Updating target block directly.
                                time.                                     only; original block unchanged.
TC-24                           Student requests reschedule with          Preserve known duration and               Resetting duration arbitrarily.
                                only new date/time.                       propose valid new interval.
TC-25                           Availability/task/commitment              Stale proposal rejected;                  Committing stale proposal.
                                changes after proposal creation.          refresh/replan required.
TC-26                           Student replies “19h” to one active       Merge into the correct                    Starting unrelated intent.
                                clarification.                            PendingAction and revalidate.
TC-27                           Student says “đồng ý” while two           Ask which proposal; no commit yet.        Approving both or guessing.
                                proposals are pending.
TC-28                           Student changes a slot after proposal     New version/proposal required; old        Reusing old approval for changed
                                preview.                                  approval context invalidated.             proposal.
TC-29                           Pending action expires or student         Apply documented expiry/topic             Merging unrelated follow-up into
                                changes topic.                            policy; ask to resume if necessary.       expired action.
TC-30                           Retry after backend timeout where         Query commit/idempotency state;           Blind duplicate commit or false
                                commit outcome is unknown.                report accurately.                        success.
TC-31                           PDF contains prompt-injection             Treat contents as document data;          Following document instructions as
                                instructions.                             ignore instructions; no unauthorized      system commands.
                                                                          tool call.
TC-32                           Two availability intervals touch at       Half-open interval semantics treat        False positive overlap.
                                boundary (e.g., 08:00–09:00 and           them as adjacent, not overlapping.
                                09:00–10:00).
TC-33                           Two users approve proposals               At most one valid commit;                 Duplicate blocks or lost update.
                                concurrently or same proposal is          subsequent attempt is
                                approved twice.                           idempotent/stale.
TC-34                           LLM timeout, malformed JSON or            Bounded retry/fallback/clarification;     Dispatching malformed or
                                unsupported intent.                       no backend write.                         unsupported command.
```
## 18.3 AI/NLU metrics
```text
Metric                                        Definition / method                                      Note
Intent precision/recall/F1                    Compare predicted intent labels with human-              Report per intent and macro average; multi-label
                                              annotated held-out examples.                             cases evaluated separately.
Slot exact match                              Fraction of required slots with exact normalized         Keep raw expression and normalization accuracy
                                              match.                                                   separate.
Slot field accuracy                           Per-field precision/recall or exact match for dates,     Date/time scoring uses a frozen timezone and
                                              effort, task references and times.                       locale.
Clarification appropriateness                 Human/criteria-based assessment of whether the           Define rubric before benchmark.
                                              system asks for a genuinely blocking field and does
                                              not ask for known context again.
Dispatch correctness                          Fraction of requests dispatched to the correct           Include confusion between availability, automatic
                                              allowlisted operation after validation.                  planning and manual block.
End-to-end completion                         Fraction of valid scripted journeys reaching the         Separate completion from user approval rate.
                                              intended safe terminal state.
```

<!-- PDF page 40 -->
```text
 Metric                                               Definition / method                                    Note
 Constraint violation rate                            Invalid proposed blocks / all proposed blocks,         For hard constraints, release expectation is zero
                                                      categorized by constraint.                             on deterministic test suite.
 Unauthorized write rate                              Writes performed without valid                         Must be zero in security tests.
                                                      identity/authorization/approval.
 Latency                                              Record stage and end-to-end latency distributions.     Numerical SLO/target is TBD.
```
## 18.4 Test data governance
Use synthetic or permissioned task/availability records for development and security tests. Keep model-development samples separate from the held-out set. Store no real student content in logs unless approved by a documented privacy policy. Freeze timezone, policy version, and expected outputs for deterministic scheduler fixtures. Annotators and evaluation rules are TBD until assigned by the team.
# 19. REQUIREMENT TRACEABILITY MATRIX
The matrix below traces every requirement family and every individual identifier through source, objective, component, use case and verification. Requirement IDs not listed in a family range are not implied; each row lists the complete IDs covered.
```text
 Requirement IDs             Source / classification             Objective and component          Use case                         Verification
 SYS-FR-001..006             Updated proposal §§1.4, 3.1;        Student web workflow;            UC-F1-01..07                     Contract, UI/E2E, status tests
                             context §§4, 9;                     UI/Orchestrator
                             BASELINE/DESIGN/PROPOSE
                             D
 F1-TASK-001..010            Proposal §§2.1.1, 2.3.2, 3.2;       Capture, confirm and resolve     UC-F1-01                         TC-01, TC-02, TC-06, TC-07,
                             context §§5–8;                      tasks; UI/Orchestrator/F1                                         TC-10, TC-11
                             BASELINE/DESIGN/PROPOSE             backend
                             D
 F1-PDF-001..007             Proposal §§1.4, 2.1.1, 4.4;         Authorized text PDF              UC-F1-02                         TC-03..TC-05, TC-31
                             BASELINE/PROPOSED/TBD               extraction; UI/parser/F1
                                                                 backend
 F1-AVL-001..008             Context §§6–8; worklist P0-         Time availability and conflict   UC-F1-03                         TC-08, TC-09, TC-18, TC-19,
                             03/P0-05;                           management;                                                       TC-32
                             DESIGN/PROPOSED/TBD                 Orchestrator/F1 backend
 F1-PLAN-001..014            Proposal §§2.1.1, 2.3.2,            Feasible deterministic           UC-F1-04                         TC-12..TC-21, TC-14..TC-17,
                             3.2.4; context §§5, 8;              weekly planning; F1                                               TC-33
                             BASELINE/DESIGN/PROPOSE             scheduler/backend
                             D/TBD
 F1-GET-001..004             Context §§6, 8; proposal UI         Inspect proposed/confirmed       UC-F1-05                         TC-22
                             mockups;                            plan; UI/F1 backend
                             DESIGN/PROPOSED
 F1-RSCH-001..006            Proposal §§1.4, 2.1.1, 2.3.2,       Student-approved block           UC-F1-06                         TC-23..TC-25, TC-28, TC-33
                             3.2.4; context §§8–9;               change; Orchestrator/F1
                             BASELINE/DESIGN/PROPOSE             backend
                             D
 F1-ORC-001..009             Context §§4, 7–9; worklist          Safe conversational              UC-F1-01..07                     TC-06..TC-10, TC-26..TC-30,
                             P0-02/P0-04/P0-06;                  command routing; Shared                                           TC-34
                             DESIGN/PROPOSED                     Orchestrator
 F2-FR-001..005              Proposal §§2.1.2, 2.3.2, 3.1–       Verified quiz and topic-level    UC-F2-01                         Post-MVP source/grading
                             3.2; BASELINE — POST-MVP            assessment; F2 module                                             tests; not F1 MVP gate
 F3-FR-001..005              Proposal §§2.1.3, 2.3.2, 3.1–       Source-grounded learning         UC-F3-01                         Post-MVP grounding/session
                             3.2; BASELINE — POST-MVP            session; F3 module                                                tests; not F1 MVP gate
 SEC-001..010                Proposal §§1.2, 2.1.1, 3.2;         Identity, ownership, safe        UC-F1-01..07                     TC-11, TC-18, TC-25, TC-27,
                             context §§4, 8;                     approval and files;                                               TC-30, TC-31, TC-33
                             BASELINE/DESIGN/PROPOSE             Orchestrator/backend
                             D/TBD
 NFR-REL-001..003            Proposal §§2.1.1, 2.2;              Determinism and state            UC-F1-03..06                     TC-12..TC-25, TC-30, TC-33
                             context §§8–9;                      consistency;
                             BASELINE/PROPOSED                   scheduler/backend
 NFR-TRC-001..002            Proposal §§2.1.1–2.1.3;             Provenance; PDF                  UC-F1-02, UC-F2-01, UC-F3-       TC-03; post-MVP traceability
                             BASELINE/PROPOSED                   parser/F2/F3                     01                               tests
 NFR-USA-001..002            Proposal §§1.2, 2.1.1, 3.3;         Review/clarification             UC-F1-01..07                     Usability walkthrough
                             BASELINE/PROPOSED                   usability; UI/Orchestrator
 NFR-SAFE-001..002           Proposal §§2.1.2–2.1.3, 4.4;        Evidence/uncertainty             UC-F2-01, UC-F3-01               TC-05, TC-31; Post-MVP tests
                             BASELINE                            handling; F2/F3 and shared
                                                                 layer
```

<!-- PDF page 41 -->
```text
 Requirement IDs            Source / classification            Objective and component             Use case                          Verification
 NFR-MNT-001                Proposal §§3.1–3.2;                Separated feature modules;          All feature use cases             Architecture and contract
                            BASELINE                           architecture                                                          review
 NFR-TST-001                Worklist P0-07/P1-04;              Testable contracts and              UC-F1-01..07                      Testability review
                            PROPOSED                           domain seams
 NFR-PERF-001..002          Worklist P1-01/P0-07;              Observability and                   UC-F1-01..07                      Latency telemetry; targets
                            PROPOSED/TBD                       benchmark;                                                            TBD
                                                               Orchestrator/parser/backen
                                                               d
 NFR-OBS-001                Worklist P0-06; PROPOSED           Correlation and auditability;       UC-F1-01..07                      Trace/log inspection
                                                               all backend operations
 NFR-PRIV-001               Proposal §1.4, worklist P0-        Data lifecycle; file                UC-F1-02, UC-F1-07                Deletion/retention tests
                            06; PROPOSED/TBD                   store/context store                                                   after policy decision
 NFR-CMP-001                Proposal §1.4;                     Web client compatibility; UI        UC-F1-01..07                      Browser/device matrix after
                            BASELINE/TBD                                                                                             decision
```
## 19.1 Traceability maintenance rule
When a requirement is added, changed, deferred or removed, the change SHALL update its source/status, affected use cases, tool/data contracts, acceptance criteria and test cases in the same change set. A requirement without an identified verification method is not ready for implementation sign-off. For the source-to-objective mapping: the principal objective is a student-controlled, feasible F1 weekly plan; PDF capture is an input route, not a separate scheduling engine; F2/F3 remain downstream planned capabilities.
# 20. OPEN DECISIONS, RISKS AND REQUIRED TEAM ACTIONS
The following items are intentionally left open because the supplied sources do not show a team decision. “Suggested resolution” is advice, not a decision. Priorities follow the supplied worklist: P0 design freeze, P1 implementation dependency, P2 later scope.
```text
 ID                                          Priority     Open issue / risk           Why it matters              Decision or evidence      Suggested next step
                                                                                                                  required                  (not approved)
 OD-001                                           P0      Confirm the exact F1        Prevents scope drift.       Team-approved             Freeze task capture,
                                                          Initial Release                                         in/out list.              text-PDF extraction,
                                                          baseline against the                                                              weekly plan, view and
                                                          updated proposal and                                                              approved reschedule
                                                          any instructor                                                                    as F1 scope.
                                                          feedback.
 OD-002                                           P0      Decide whether              Task edits can              Scope decision and        Defer unless required;
                                                          UPDATE_TASK is in           invalidate                  impact policy.            if included, define
                                                          MVP.                        plans/blocks.                                         proposal/approval
                                                                                                                                            impact.
 OD-003                                           P0      Decide whether              Deletion may orphan         Scope decision and        Defer unless required;
                                                          DELETE_TASK is in           blocks or invalidate        referential behavior.     define archive/delete
                                                          MVP.                        plan.                                                 and dependent-
                                                                                                                                            record behavior.
 OD-004                                           P0      Decide whether              Distinct from               Scope decision and        Keep deferred unless
                                                          manual                      automatic planning          UX/use case.              proposal/instructor
                                                          CREATE_STUDY_BLOC           and availability.                                     requires it.
                                                          K is in MVP.
 OD-005                                           P0      Decide how busy             Scheduler must avoid        Data model /              Implement a stable
                                                          commitments are             unavailable intervals       ownership /               busy-interval
                                                          represented and             even if entity design is    recurrence decision.      interface first; decide
                                                          whether                     open.                                                 physical entity later.
                                                          FixedCommitment is
                                                          a separate entity.
 OD-006                                           P0      Freeze Orchestrator         All components need         Schema for                Complete P0-02 with
                                                          Input/Output                stable boundaries.          UserMessage,              machine-valid
                                                          Contract.                                               ExtractionResult,         schemas and invalid
                                                                                                                  PendingAction,            examples.
                                                                                                                  ValidatedCommand,
                                                                                                                  ToolResult and
                                                                                                                  approval context.
 OD-007                                           P0      Canonical field             Inconsistent names          Confirm                   Adopt a single
                                                          vocabulary and              cause integration           task_candidate_id,        glossary/schema and
                                                          semantics.                  failures.                   slots, deadline_date,     migrate examples.
                                                                                                                  duration_minutes,
                                                                                                                  start_at/end_at.
```

<!-- PDF page 42 -->
```text
ID       Priority   Open issue / risk        Why it matters           Decision or evidence       Suggested next step
                                                                      required                   (not approved)
OD-008        P0    Complete tool catalog    Prevents arbitrary       Operation contracts,       Complete P0-03;
                    and intent-to-           LLM tool calls and       side effects, errors,      mark unsupported
                    operation allowlist.     missing workflow         authorization and          operations explicitly.
                                             branches.                confirmation.
OD-009        P0    PendingAction            Short replies can        Multiple pending           Build transition table
                    lifecycle and routing    attach to the wrong      actions, correction,       and test multi-turn
                    policy.                  request.                 cancellation, expiry,      cases.
                                                                      topic change and
                                                                      version semantics.
OD-010        P0    Multi-intent             Availability may need    Supported                  Support only small
                    sequencing and           confirmation before      combinations,              deterministic
                    dependency policy.       plan generation.         ordering and partial       sequential
                                                                      success semantics.         compositions for
                                                                                                 MVP.
OD-011        P0    Timezone and             Incorrect date parsing   Trusted timezone           Use configured
                    date/time                can schedule outside     source, week start,        timezone and
                    normalization.           the intended period.     relative-date              preserve original
                                                                      reference, date-only       expressions; approve
                                                                      deadline boundary,         parsing conventions.
                                                                      overnight interval
                                                                      behavior.
OD-012        P0    Scheduler tie-breaks,    Same data must yield     Minimum/maximum            Put policy constants
                    block splitting,         feasible and             block size, granularity,   in versioned
                    workload and             repeatable plans.        daily workload caps,       configuration;
                    remaining-effort                                  break rules, equal-        benchmark before
                    calculations.                                     deadline/equal-            fixing defaults.
                                                                      priority tie-breaks.
OD-013        P0    Partial proposal vs      UI must distinguish a    When partial proposal      Return proposal with
                    INSUFFICIENT_AVAILA      useful partial plan      is valid; how              unscheduled_work if
                    BILITY error             from total failure.      minutes/reasons are        at least one block is
                    semantics.                                        represented.               feasible; use error
                                                                                                 when none can be
                                                                                                 proposed, subject to
                                                                                                 team approval.
OD-014        P0    Approval evidence,       Prevents forged/stale    UI/chat approval           Bind approval to user
                    proposal expiry and      approvals.               mechanism, expiry          + proposal ID +
                    version binding.                                  policy and                 version + expiry;
                                                                      authenticated              never rely on LLM
                                                                      interaction evidence.      boolean.
OD-015        P0    Concurrency,             Retry/double             Storage-level              Decide atomic
                    transaction boundary,    approval must not        optimistic                 commit boundary and
                    idempotency and          duplicate or overwrite   concurrency/locking        test
                    recovery.                data.                    and idempotency            replay/concurrent
                                                                      strategy.                  approval.
OD-016        P0    Acceptance               Team cannot claim        Annotated                  Freeze held-out test
                    thresholds and           quality without          Vietnamese dataset,        set before model
                    evaluation dataset.      defined evidence.        metrics and release        comparison; no
                                                                      threshold.                 threshold assumed
                                                                                                 here.
OD-017        P1    Backend/API              Affects                  Team skill, runtime,       Compare candidates
                    framework, database      implementation           hosting, operations        through ADRs; do not
                    and deployment           structure and            and course                 infer from proposal.
                    architecture.            interfaces.              constraints.
OD-018        P1    LLM/NLU model,           Cost, latency, privacy   Candidate                  Benchmark multiple
                    router and inference     and extraction           model/version,             candidates against TC
                    provider.                accuracy.                license, data policy       matrix; JEV router and
                                                                      and end-to-end             Qwen remain
                                                                      benchmark.                 candidates, not
                                                                                                 choices.
OD-019        P1    File limits and          Privacy, storage cost    Maximum size/pages,        Configure limits and
                    retention/deletion       and parse reliability.   allowed encryption,        retention; document
                    policy.                                           retention, deletion        student-facing
                                                                      and access.                disclosure.
OD-020        P1    Browser/device           Needed for release-      Supported browsers,        Gather workload
                    compatibility and        level test plan.         viewport/device            assumptions and
                    non-functional service                            scope,                     measure prototype
                    targets.                                          latency/availability/co    before setting
                                                                      ncurrency targets.         numeric SLOs.
```

<!-- PDF page 43 -->
```text
 ID                                              Priority     Open issue / risk          Why it matters            Decision or evidence       Suggested next step
                                                                                                                   required                   (not approved)
 OD-021                                                P1     Team ownership,            No execution              Team agreement             Assign only in the
                                                              review schedule and        commitment is             assigning                  team’s project
                                                              completion dates.          evidenced in source       owners/dates.              tracker; SRS
                                                                                         worklist.                                            intentionally leaves
                                                                                                                                              TBD.
```
## 20.1 Risk register
```text
 Risk ID                       Risk                                Likelihood / impact              Mitigation                         Residual issue
 R-001                         Incorrect extraction                Medium / High                    Candidate-only extraction,         Extraction quality needs
                               produces a wrong                                                     provenance, student review,        benchmark.
                               task/deadline.                                                       field validation.
 R-002                         Insufficient availability           High / Medium                    Partial scheduling and             Partial-vs-error threshold
                               makes full schedule                                                  explicit unscheduled               needs decision.
                               infeasible.                                                          minutes; never fabricate
                                                                                                    capacity.
 R-003                         Ambiguous dates or                  Medium / High                    Trusted                            Week boundary/date-only
                               timezone produce incorrect                                           timestamp/timezone,                policy TBD.
                               calendar placement.                                                  original expression
                                                                                                    retention, clarification.
 R-004                         Changed source data                 Medium / High                    Version/fingerprint and            Data snapshot strategy TBD.
                               invalidates proposal.                                                backend revalidation on
                                                                                                    commit.
 R-005                         Duplicate approval or retry         Medium / High                    Transaction, idempotency           Persistence-specific design
                               creates duplicate writes.                                            and concurrency checks.            TBD.
 R-006                         Prompt injection in uploaded        Medium / High                    Treat file text as untrusted       Security review required.
                               PDF manipulates AI                                                   content; tool allowlist and
                               behavior.                                                            backend enforcement.
 R-007                         Scope creep delays F1               High / Medium                    Keep F2/F3 and P2                  Scope approval required.
                               validation.                                                          capabilities outside MVP.
 R-008                         Model selected from intent          Medium / High                    Evaluate slots, clarification,     Evaluation set and threshold
                               accuracy only fails end-to-                                          dispatch, constraint and full      TBD.
                               end.                                                                 workflows.
 R-009                         Unclear file retention creates      Medium / High                    Retention configuration,           Policy approval required.
                               privacy or storage risk.                                             access control, deletion
                                                                                                    process.
 R-010                         F2/F3 ownership is coupled          Medium / Medium                  Separate modules, shared           Future contract evolution
                               to F1 internals.                                                     typed records and                  required.
                                                                                                    orchestrator handoffs.
```
# 21. IMPLEMENTATION ROADMAP AND RELEASE GATES
This roadmap reflects the sequence in cong_viec_can_lam.md; it is an ordering proposal, not an approved calendar. No owners or completion dates are assigned here.
## 21.1 P0 — Freeze requirements and design contracts
```text
 Work item                                             Required output                                           Dependency / exit gate
 P0-01 Scope/baseline                                  F1 in-scope/deferred list, proposal alignment and         Exit when no deferred feature is silently
                                                       instructor/team questions.                                mandatory.
 P0-02 Orchestrator contract                           Machine-valid I/O schemas, provenance and                 Can begin immediately; exit when all component
                                                       approval context.                                         boundaries are explicit.
 P0-03 Tool contracts                                  Complete tool catalog, dispatch allowlist and             Depends on P0-01/P0-02.
                                                       intent-operation mapping.
 P0-04 State/routing                                   Workflow transition table and multi-turn                  Depends on P0-02/P0-03.
                                                       scenarios.
 P0-05 Time/scheduler rules                            Time normalization, entity resolution and                 Depends on P0-01/P0-02; used by P0-03/P0-04.
                                                       deterministic scheduler rule sheet.
 P0-06 Approval/recovery                               Commit sequence,                                          Depends on P0-03/P0-04/P0-05.
                                                       version/concurrency/idempotency and failure
                                                       policy.
 P0-07 Test matrix                                     Vietnamese test data, expected outcomes, metrics          Draft alongside P0-02; finalize after P0-03..P0-06.
                                                       and approved thresholds.
```

<!-- PDF page 44 -->
P0 exit gate: The team approves scope, schemas, scheduler invariants, state transitions, approval semantics, error/recovery rules and the acceptance/test plan. Any unapproved item remains visibly TBD and cannot silently become implementation behavior.
## 21.2 P1 — Implement and verify F1 MVP
```text
   1.     Select backend/API/database/model options with documented architecture decisions and benchmark evidence (P1-01).
   2.     Implement F1 domain and persistence: task candidate/confirmation, availability, commitments/busy intervals,
          plan/block/version and validators (P1-02).
   3.     Implement deterministic scheduler with hard-constraint checks, partial/unscheduled output, and proposal lifecycle.
   4.     Implement approval/commit with backend revalidation, transaction, optimistic concurrency and idempotency.
   5.     Implement Shared Orchestrator: NLU adapter, schema validation, entity resolution, PendingAction store, clarification, allowlist
          dispatch, approval routing and recovery (P1-03).
   6.     Implement minimum UI: task entry/PDF import, availability, weekly planner, proposal preview, approve/reject and errors.
   7.     Run test matrix, integration/E2E/security checks and model evaluation; record environment, dataset, metrics, failures and
          limitations (P1-04).
```
P1 release gate: Demonstrate actual running implementation for the agreed F1 scope; pass agreed hard-constraint/security invariants; complete the relevant acceptance tests; show persisted approved plans and correct rejection/stale/retry behavior. A mockup, generated JSON or happy-path demo alone is insufficient evidence of MVP completion.
## 21.3 P2 and Post-MVP
- P2: UPDATE_TASK, DELETE_TASK, manual CREATE_STUDY_BLOCK, separate
FixedCommitment, advanced recurrence and optional routing optimization only after scope approval.
- Post-MVP F2: authorized source retrieval, question verification, deterministic MCQ grading, topic-level performance and
revision recommendations.
- Post-MVP F3: authorized source-grounded explanations/hints, session lifecycle, summary review and confirmed
SessionOutcome.
- Cross-feature integration: only typed, permission-checked handoffs; F2/F3 outputs must not modify confirmed F1 schedules
without student confirmation and F1 validation/approval.
## 21.4 Team roles recorded by the proposal
The updated proposal records planned responsibilities as follows. These are proposal-level role assignments, not evidence of completed implementation or fixed task ownership for every SRS work item.
```text
 Member                                        Proposal role                                      Responsibility recorded in proposal
 Châu Hoà Phát                                 Project Manager; Backend Developer                 Coordinate progress and backend; lead slide
                                                                                                  preparation with support from Hùng.
 Phạm Hùng Khôi                                Full-Stack Developer                               Develop/integrate frontend and backend
                                                                                                  workflows.
 Nguyễn Ngọc Thanh Hương                       UI/UX Designer; Frontend Developer                 Lead proposal preparation and coordinate task
                                                                                                  assignments.
 Nguyễn Trần Minh Khang                        UI/UX Designer; Frontend Developer                 Design interfaces and implement frontend
                                                                                                  components.
 Huỳnh Nguyễn Thế Hiển                         Backend Developer; AI Engineer                     Develop backend services and AI integration.
 Đặng Minh Hùng                                Backend Developer                                  Develop backend services and support slide
                                                                                                  preparation.
```
The actual owner of each P0/P1 work item, reviewer and due date remains TBD and must be approved by the team.
# APPENDICES
## Appendix A — Canonical terminology proposed for implementation
```text
 Term                                          Meaning                                            Important distinction
 AcademicTask                                  A unit of academic work with an effort estimate    Not a calendar interval.
                                               and deadline.
```

<!-- PDF page 45 -->
```text
 Term                                          Meaning                                               Important distinction
 TaskCandidate                                 Untrusted/manual/AI-extracted task information        Not schedulable.
                                               awaiting review/confirmation.
 PlannedStudyBlock                             A concrete time interval allocated to an              One task may have multiple blocks.
                                               AcademicTask.
 StudyPlan                                     A versioned collection of proposed or confirmed       Not equivalent to one block.
                                               blocks for a planning period.
 Availability                                  Student-declared free time.                           Not proof that no other commitment exists.
 BusyInterval                                  Any interval that must not be scheduled over.         May be sourced from a FixedCommitment or
                                                                                                     another approved record; entity choice TBD.
 Proposal                                      A proposed change awaiting student decision.          Not committed.
 Approval                                      Authenticated student decision bound to a target      Not an LLM extraction field.
                                               proposal/version.
 Commit                                        Successful backend persistence after revalidation.    Not the same as READY or approval receipt.
 PendingAction                                 Versioned conversational workflow awaiting input      Not a domain entity such as Task or StudyPlan.
                                               or decision.
 ExtractionResult                              Untrusted output of the NLU/LLM layer.                Not an executable command.
 ValidatedCommand                              Normalized operation after structural, semantic,      Still does not replace required approval.
                                               domain and authorization checks.
 SessionOutcome                                Student-confirmed summary of a learning session       Not proof of mastery or a graded assessment.
                                               (F3).
 AssessmentResult                              Deterministic result from verified quiz answer keys   Not interchangeable with SessionOutcome.
                                               (F2).
```
## Appendix B — Illustrative contract examples
The following examples illustrate the proposed logical contracts. They are not deployed API payloads or finalized schemas. Fields and enum values must be reconciled with the approved contract in OD-006/OD-007.

<!-- PDF page 46 -->
### B.1 Untrusted extraction result
```json
{
"request_id": "req-example-001",
"intents": [
{
"name": "CREATE_TASK",
"confidence": null,
"slots": {
"title": {
"value": "Bài tập OOP",
"raw_expression": "bài tập OOP",
"provenance": "USER_MESSAGE"
},
"deadline_date": {
"value": null,
"raw_expression": null,
"provenance": null
},
"estimated_minutes": {
"value": 240,
"raw_expression": "4 tiếng",
"provenance": "USER_MESSAGE"
}
},
"missing_fields": ["deadline_date"],
"ambiguities": []
}
```
] }
### B.2 Validated command — identity is server context, not model output
```json
{
"operation": "create_task_candidate",
"arguments": {
"title": "Bài tập OOP",
"estimated_minutes": 240,
"deadline_date": null
},
"validation_status": "NEEDS_CLARIFICATION",
"trusted_context_ref": "server-managed-context-reference"
}
```

<!-- PDF page 47 -->
### B.3 Proposed plan result with unscheduled work
```json
{
"result_type": "PROPOSAL",
"plan": {
"plan_id": "server-generated-id",
"version": 1,
"status": "PROPOSED",
"period_start": "2026-11-09",
"period_end_exclusive": "2026-11-16",
"blocks": [],
"unscheduled_work": [
{
"task_id": "server-resolved-task-id",
"unscheduled_minutes": 120,
"reason_code": "INSUFFICIENT_AVAILABLE_CAPACITY"
}
]
},
"requires_approval": true
}
```
### B.4 Error envelope
```json
{
"status": "ERROR",
"error": {
"code": "STALE_PLAN_VERSION",
"message": "The proposal is no longer current. Please review an updated proposal.",
"details": {
"proposal_id": "server-generated-id"
},
"retryable": false
},
"correlation_id": "server-generated-correlation-id"
}
```
## Appendix C — Status taxonomy
```text
    Domain                        Status/value                         Meaning                             Must not be confused with
    Validation                    READY                                Required values are                 User approval or persistence.
                                                                       structurally/semantically/domain
                                                                       valid for the next operation.
    Validation                    NEEDS_CLARIFICATION                  A missing/ambiguous value blocks    Invalid data necessarily.
                                                                       safe continuation.
    Validation                    UNSUPPORTED                          Request is outside currently        Backend error.
                                                                       supported scope.
    Validation                    INVALID                              Supplied value violates             Clarification when user can correct it.
                                                                       schema/business constraints.
```

<!-- PDF page 48 -->
```text
 Domain                           Status/value                               Meaning                                  Must not be confused with
 Workflow                         AWAITING_CLARIFICATION                     PendingAction is waiting for user        Entity status.
                                                                             input.
 Workflow                         AWAITING_APPROVAL                          One identified proposal awaits           Confirmed plan.
                                                                             student decision.
 Workflow                         COMMITTED                                  Backend confirms persistence.            LLM prediction of success.
 Proposal                         PROPOSED                                   Candidate schedule change for            CONFIRMED.
                                                                             review.
 Proposal                         REJECTED / EXPIRED / SUPERSEDED            Proposal is no longer eligible for       Deleted historical record unless
                                                                             approval.                                retention policy says so.
 Domain                           DRAFT / CANDIDATE                          Task data has not become a               Scheduler eligible task.
                                                                             confirmed task.
 Domain                           CONFIRMED                                  Student-confirmed task/plan/block        Merely extracted or proposed data.
                                                                             according to entity lifecycle.
```
Enum spelling and complete state sets must be frozen in OD-006/OD-009 before code generation. This table expresses the distinctions required by the source design, not a final enum contract.
## Appendix D — Scheduler invariants and verification formulas
For half-open intervals A = [s_A, e_A) and B = [s_B, e_B), the intervals overlap exactly when: s_A < e_B AND s_B < e_A Consequently, [08:00, 09:00) and [09:00, 10:00) are adjacent but do not overlap. A scheduled block must satisfy, at minimum: block.start < block.end block ⊆ planning_period block ⊆ task_eligibility_window block ⊆ student_availability block ∩ busy_intervals = ∅ block ∩ other_confirmed_blocks = ∅ block.end <= applicable_deadline_boundary sum(new_allocations_for_task) <= approved_remaining_minutes The exact endpoint convention for a date-only deadline, block granularity, minimum/maximum block length, breaks, daily caps and task remaining-effort update rule remain TBD. These must be configured and tested before deterministic scheduling is considered release- ready.
## Appendix E — Assumption and TBD register
```text
 ID                                              Assumption / TBD                                        Current treatment
 AT-001                                          User interacts as an authenticated student.             Assumed from target user and authorization
                                                                                                         requirements; auth provider TBD.
 AT-002                                          The Initial Release is a web application.               Baseline in proposal; exact compatibility matrix
                                                                                                         TBD.
 AT-003                                          Supported course PDFs are text-extractable.             Baseline; image-only/OCR-heavy files fall back to
                                                                                                         manual entry.
 AT-004                                          Timezone may default to Asia/Ho_Chi_Minh for            Context reference only; product timezone must
                                                 the current project context.                            come from trusted configuration/user profile.
 AT-005                                          Weekly planning period boundaries.                      Week start, local clock and inclusive/exclusive end
                                                                                                         must be approved.
 AT-006                                          Storage schema and database engine.                     TBD; logical entities are specified without vendor
                                                                                                         choice.
 AT-007                                          Backend/API framework and transport.                    TBD.
 AT-008                                          LLM/NLU provider/model/version.                         TBD pending comparative benchmark and data-
                                                                                                         policy review.
 AT-009                                          File size/page limits and retention.                    TBD; must be configured before public upload.
 AT-010                                          Numeric SLOs and evaluation thresholds.                 TBD; no benchmark evidence supplied.
```

<!-- PDF page 49 -->
```text
 ID                                             Assumption / TBD                                Current treatment
 AT-011                                         PendingAction expiry duration.                  TBD; no expiry interval invented.
 AT-012                                         Approval channel and expiry.                    TBD; approval must still be bound to
                                                                                                user/proposal/version.
 AT-013                                         Recurrence support beyond NONE/WEEKLY.          Deferred/TBD.
 AT-014                                         Separate FixedCommitment entity.                TBD; busy intervals must be represented somehow
                                                                                                in scheduler input.
 AT-015                                         Whether update/delete/manual scheduling are     TBD; treated as deferred by default in this SRS.
                                                MVP.
```
## Appendix F — Source register and limitations
```text
   1.     Team03_Proposal_Updated(1).pdf, Midterm Engineering Report — StudyFlow AI, October 2026, 28 pages. Primary source for
          problem framing, target users, release scope, feature descriptions, proposed workflows, architecture, conceptual data model,
          UI mockups, team roles and roadmap. The proposal itself states that mockups and proposed workflows are not evidence of
          implementation or measured results.
   2.     context(2).md, StudyFlow AI — Context tiếp nối thiết kế F1, version 1.1, 04 November 2026. Source for prior conceptual
          design of intents, parameter schema, tool catalog, orchestrator pipeline, data entities, validation and unresolved decisions. It
          explicitly says the underlying 0-main-20.pdf had not been directly read at the time that context was prepared; the newly
          supplied updated proposal is now used directly as the primary project proposal for this SRS.
   3.     cong_viec_can_lam(2).md, StudyFlow AI — Các công việc cần làm hiện tại, 04 November 2026. Source for P0/P1/P2 tasks,
          dependencies, outputs, proposed completion criteria and the observation that no implementation/benchmark evidence was
          available in the workspace at that date.
   4.     StudyFlow_AI_SRS_Master_Prompt(1).pdf, master prompt supplied by the user. Used as the requested structure and
          coverage checklist, adapted where the updated proposal provides more authoritative scope detail.
```
Source limitations
- The preliminary survey values in the proposal (n=17) cannot be independently audited from supplied files because the
questionnaire and anonymized response data are not included.
- The related external studies/products listed in the proposal were not independently re-researched for this SRS; this document
preserves their role as background rather than asserting fresh validation.
- No source supplied a finalized database engine, programming language/framework, API protocol/path, LLM/NLU
provider/model/version, numeric performance target, approved evaluation threshold, file retention policy, authentication provider, or approved release date.
- The SRS is a detailed engineering draft, not a claim that the system has been implemented, benchmarked, tested or approved.
## Appendix G — Final engineering readiness checklist
Before using this document as an autonomous coding specification, the team should sign off the following gates:
- ☐ Confirm F1 MVP scope and the P2 deferrals in OD-001..OD-005.
- ☐ Freeze I/O schemas, canonical field names and enum sets (OD-006/OD-007).
- ☐ Approve tool contracts and dispatch allowlist (OD-008).
- ☐ Approve PendingAction and multi-intent state transitions (OD-009/OD-010).
- ☐ Approve timezone, deadline boundary and scheduling policy constants (OD-011/OD-012).
- ☐ Approve partial scheduling semantics (OD-013).
- ☐ Approve approval evidence, transaction, concurrency, idempotency and recovery (OD-014/OD-015).
- ☐ Freeze evaluation data, acceptance thresholds and supported environment (OD-016/OD-020).
- ☐ Decide stack/model/file policy and record architecture decisions (OD-017..OD-019).
- ☐ Assign owners/reviewers/dates outside this SRS (OD-021).
- ☐ Implement and run the P1 test suite; attach actual test/benchmark evidence before declaring MVP complete.
Final status: This SRS is detailed enough to guide architecture, contract design, test design and F1 implementation planning. It is not yet a fully frozen autonomous code-generation baseline because the P0 decisions above remain open. A code-generation agent must treat all TBD, PROPOSED, REQUIRES REVIEW and deferred items as constraints: it may scaffold interfaces, tests and configurable policies, but must not silently choose unresolved product behavior.
