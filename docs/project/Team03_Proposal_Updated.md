# MIDTERM ENGINEERING REPORT — StudyFlow AI

> Bản chuyển đổi Markdown từ PDF nguồn. Nội dung văn bản được giữ theo thứ tự tài liệu; các hình ảnh nhúng được lưu trong thư mục `assets/`. Các header/footer lặp lại và số trang in ở chân trang được thay bằng chú thích trang HTML để tránh lặp nội dung trình bày.

<!-- PDF page 1 -->
V IETNAM NATIONAL U NIVERSITY, H O C HI M INH C ITY U NIVERSITY OF S CIENCE FACULTY OF I NFORMATION T ECHNOLOGY MIDTERM ENGINEERING REPORT Project: StudyFlow AI Course: Computational Thinking (CSC10014)
```text
Students (Group 3):                                              Instructors:
Châu Hoà Phát (25127224)                               PhD. Châu Thành Đức
Nguyễn Ngọc Thanh Hương (25127197)                        PhD. Đỗ Đức Hào
Nguyễn Trần Minh Khang (25127369)                     MSc. Trần Hoàng Quân
```
Phạm Hùng Khôi (25127390) Đặng Minh Hùng (25127340) Huỳnh Nguyễn Thế Hiển (25127327) Ho Chi Minh City, October 2026

![Hình ảnh được trích xuất từ trang PDF 1](assets/proposal/page-01-figure-000.png)

<!-- PDF page 2 -->
Table of Contents
```text
1   Problem Definition & Existing Solutions                                                    1
    1.1 Problem Statement . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .      1
    1.2 Project Objectives . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   2
    1.3 Target Users . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   2
    1.4 Project Scope . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    3
    1.5 Overview of Related Solutions and Technologies . . . . . . . . . . . . . . . .         3
2   System Requirements Analysis                                                            4
```
## 2.1 Core Features . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
### 2.1.1 Feature 1 - Intelligent Academic Planner . . . . . . . . . . . . . . . . 4
### 2.1.2 Feature 2 - Learning Assessment & Adaptive Revision . . . . . . . . . 5
### 2.1.3 Feature 3 - Daily AI Learning . . . . . . . . . . . . . . . . . . . . . . 8
## 2.2 Non-functional Requirements . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
## 2.3 Use Case Model . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
### 2.3.1 Overall Use Case Diagram: Initial Release and Post-MVP Core Features 11
### 2.3.2 Use Case Specifications . . . . . . . . . . . . . . . . . . . . . . . . . 11
```text
3   System Design                                                                              13
    3.1 Overall System Architecture . . . . . . . . . . . . . . . . . . . . . . . . . . .      13
         3.1.1 Proposed Architecture Diagram . . . . . . . . . . . . . . . . . . . . .         14
    3.2 Detailed Design . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    14
         3.2.1 Core Data Entities and Feature Responsibilities . . . . . . . . . . . . .       14
         3.2.2 Conceptual Class / Data Model . . . . . . . . . . . . . . . . . . . . . .       15
         3.2.3 Main Interaction Sequence . . . . . . . . . . . . . . . . . . . . . . . .       15
         3.2.4 Illustrative F1 MVP Sequence Diagram . . . . . . . . . . . . . . . . .          16
    3.3 User Interface Design . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    16
4   Development Process                                                                        21
    4.1 Team Responsibilities . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    21
    4.2 Current Deliverables and Expected Results . . . . . . . . . . . . . . . . . . . .      21
    4.3 Next-stage Plan . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    22
    4.4 Challenges and Risks . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .     22
```

<!-- PDF page 3 -->
References                                            23

<!-- PDF page 4 -->
List of Figures
```text
 2.1   Use cases grouped by Initial Release (F1 MVP) and post-MVP Core Features
       (F2/F3). . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
 3.1   F1 Initial Release (MVP) and post-MVP Core Features F2/F3. . . . . . . . . .             14
 3.2   Conceptual class/data model distinguishing F1 MVP records from F2/F3 Core
       Feature records. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .     15
 3.3   Proposed F1 planning interaction; schedule changes require student approval. .           16
 3.4   Initial Release / F1 MVP mockup: dashboard with upcoming tasks and the
       current study plan. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .      17
 3.5   Initial Release / F1 MVP mockups: focused views of task entry and the weekly
       calendar. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    18
 3.6   Post-MVP Core Feature / F3 concept with adjacent F2 practice-question func-
       tionality. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   19
 3.7   Post-MVP Core Feature / F2 mockup: source-based practice quiz. . . . . . . .             19
 3.8   Post-MVP Core Feature / F3 mockup: student review and confirmation of a
       study-session outcome. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .       20
```

<!-- PDF page 5 -->
List of Tables
```text
 2.1   UC-01 (Initial Release / F1 MVP): Generate and Approve a Study Plan . . . . 11
 2.2   UC-02 (Post-MVP Core Feature / F2): Complete a Quiz and Review Revision
       Priorities . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
 2.3   UC-03 (Post-MVP Core Feature / F3): Complete a Guided Learning Session . . 12
```

<!-- PDF page 6 -->
Chapter 1 Problem Definition & Existing Solutions
## 1.1     Problem Statement
University students managing multiple courses may struggle to organize deadlines when sched- ules change, identify weak topics for revision, and obtain understandable, reliable explanations from course materials. These issues can lead to rushed assignments, inefficient review, and interrupted study. Prior research reports that 38.1% of 470 students at Can Tho University of Medicine and Pharmacy rarely or never planned their studies [1]; in a Cornell introductory statistics course survey, 31% of 190 respondents expressed high concern about knowing what to study and having the necessary skills or background [2]; and 53% of students who used GenAI for study were concerned about inaccurate information [3]. A preliminary survey by our team (n = 17) provides local observations. In the previous four weeks, 76.5% had forgotten a deadline or completed work closer to it than planned. When asked about time-consuming or difficult situations, 70.6% selected managing study time and deadlines, 41.2% identifying weak topics, and 76.5% finding explanations suitable for course materials (multiple selections allowed). Additionally, 88.2% reported manually transferring information between study tools in the past week. The source questionnaire and anonymized response data were not included in the supplied project files, so these local survey figures cannot be independently audited from this report alone. For example, a student preparing for an exam while finishing an assignment may need to coordinate information across multiple tools, potentially disrupting study and increasing manual effort. StudyFlow AI proposes a student-controlled workflow connecting academic planning, guided learning, and optional assessment. Problem Brief
- Target users: Undergraduate students balancing multiple courses and independent study.
- Inputs: Academic deadlines, study availability, course materials, and practice or quiz
experiences.
- Desired outcomes: Manageable study plans, clearer revision priorities, and dependable
learning support.
- Constraints: Limited time, changing commitments, incomplete material, and student control
over decisions. 1

<!-- PDF page 7 -->
- Scope: Coordination of planning, guided study, and optional assessment; not replacement of
a full LMS.
- Edge cases: Unclear deadlines, last-minute changes, insufficient study time, or unreliable
explanations.
- Success criteria to evaluate: Feasible plans, useful revision guidance, credible explanations,
and lower coordination effort.
## 1.2     Project Objectives
The project aims to achieve the following objectives, each associated with a verifiable outcome.
- Feature 1 (F1) - Intelligent Academic Planner (Initial MVP): Generate feasible study
schedules from student-confirmed tasks, deadlines, and availability. Proposed study blocks must satisfy scheduling constraints, and any unscheduled work must be identified.
- Feature 2 (F2) - Learning Assessment & Adaptive Revision (Core Feature; planned
post-MVP): Assess students through source-grounded quizzes, grade responses against verified answer keys, and provide topic-level feedback with evidence-based revision recom- mendations.
- Feature 3 (F3) - Daily AI Learning (Core Feature; planned post-MVP): Provide con-
textual explanations and progressive hints grounded in authorized course materials, with traceable source references and session outcomes confirmed by students.
- Cross-feature Integration: Coordinate planning, guided learning, and optional assessment
through a shared orchestrator. Revision recommendations can reach the planner without automatically changing confirmed schedules.
- User Control & Reliability: Require student confirmation of extracted task information and
schedule changes. Ambiguous inputs and insufficient evidence must trigger clarification or a safe fallback.
## 1.3     Target Users
Primary users. StudyFlow AI is intended primarily for undergraduate students who manage multiple courses and independent study. These students need to coordinate assignments, aca- demic deadlines, weekly availability, and exam revision while working with their own authorized course materials, particularly text-based lecture PDFs. The proposed system supports three connected needs: organizing feasible study schedules, checking understanding, and obtaining explanations grounded in course content. Representative context. A student has assignments due in several courses, limited free time during the week, and lecture PDFs to review before an upcoming exam. The student enters tasks or imports a supported PDF, confirms extracted details such as deadlines and estimated study time, and provides available study periods. StudyFlow AI proposes a weekly plan for the student to review and approve. During a planned study session, the student requests a source-grounded explanation or progressive hints, then optionally completes a quiz with verified answers. Topic-level feedback can inform revision recommendations. Any resulting schedule changes remain subject to the student’s approval. 2

<!-- PDF page 8 -->
Intended support. The system is designed for students seeking help coordinating these activities within one workflow while retaining control over their academic decisions. It relies on student- confirmed task details, realistic availability, and authorized materials suitable for text extraction. Validation status. This description defines the intended user group and a proposed use scenario; it is not a finding from a survey or user study. The relevance of these needs and the suitability of the workflow must be validated through user research. No demographic proportions, specific fields of study, or age ranges are assumed.
## 1.4      Project Scope
The proposed minimum viable product (MVP) is a single web application centered exclusively on Feature 1 (F1), the Intelligent Academic Planner. Its core scope includes academic task entry, supported text-PDF extraction, weekly study planning, and student-approved rescheduling using authorized course materials. Feature 2 (F2), Learning Assessment & Adaptive Revision, and Feature 3 (F3), Daily AI Learning, are Core Features planned for later releases after the F1 workflow is validated; they are outside the Initial Release (MVP) [4]. The shared orchestrator routes F1 requests within the MVP and can route requests to supplemen- tary F2 or F3 if those features are later implemented. AI-extracted task details are treated as candidates and must be reviewed and confirmed by the student before scheduling. Study plans are presented as proposals, and new or modified schedules are saved only after explicit student approval. The initial F1 MVP excludes F2 assessment, F3 guided-learning sessions, and full replacement of a learning management system (LMS), autonomous schedule changes, unrestricted external integrations, voice or video tutoring, OCR-heavy document processing, essay grading, and predictive mastery modeling. These boundaries keep the initial system focused, testable, and manageable. This scope describes the proposed MVP and does not imply that the system has already been implemented.
```text
1.5      Overview of Related Solutions and Technologies
 Solution                 Documented capability                  Relevance / proposed adaptation
 MyStudyLife [5]          Student planner and                    Relevant comparator for planning;
                          homework/task-tracking features.       StudyFlow proposes constraint-checked
                                                                 blocks and explicit student approval.
                                                                 Comparative advantage is unverified.
 Quizlet Practice Tests   Practice tests for study and review.   Relevant to possible F2 assessment;
 [6]                                                             proposed F2 uses reviewed,
                                                                 source-grounded questions and
                                                                 deterministic grading.
 Gemini Notebook [7]      Chat and learning-material study       Relevant to possible F3/F2 workflows;
                          features, including quiz/flashcard     StudyFlow proposes explicit links to F1
                          generation.                            plans and confirmation controls. User
                                                                 value of integration remains a
                                                                 hypothesis.
                                                        3
```

<!-- PDF page 9 -->
Chapter 2 System Requirements Analysis
## 2.1     Core Features
The proposed system has three core student-facing features coordinated by a shared orchestration layer. F1 is the sole feature in the Initial Release (MVP); F2 and F3 remain core features planned for later releases after the F1 MVP is validated.
### 2.1.1    Feature 1 - Intelligent Academic Planner
Release scope: Initial Release (MVP). Feature 1 is the only feature included in the proposed first release. Feature Objective & Problem Definition Students managing several courses may struggle to consolidate deadlines and fit study tasks into limited availability; this is a hypothesis requiring interviews. For example, a student imports an assignment PDF, confirms its title, start date, end date (deadline), priority, and estimated effort, and requests a weekly plan. Feature 1 converts confirmed tasks and free time into editable, feasible study blocks, making conflicts and unscheduled work visible. Computational Thinking Design
- Decomposition: Task capture and validation, availability modeling, constraint-based schedul-
ing, and plan confirmation or replanning are treated as separate subproblems.
- Pattern Recognition: Deadline changes and conflicting commitments may repeatedly require
replanning. This pattern is proposed and must be validated through user research; a reusable conflict-checking procedure addresses it.
- Abstraction: An AcademicTask retains task_id, course_id, title, start date, end date
(deadline), estimated_minutes, remaining_minutes, and priority. PDF fonts, course colors, and profile avatars are excluded from scheduling logic; source provenance, timezone, and permissions remain in related records. 4

<!-- PDF page 10 -->
Core Algorithm & Technical Workflow Feature 1 accepts manual task entries or uses AI to extract candidate information from authorized text-based PDFs. Students validate and confirm essential fields before scheduling. A determinis- tic heuristic prioritizes earlier deadlines and uses task priority to resolve ties. It allocates study blocks within available intervals while checking existing commitments, deadlines, cumulative workload, and overlaps. For half-open study blocks A and B, the overlap test below is consistent with PostgreSQL’s OVERLAPS semantics:
Overlap(A, B) ⇐⇒ sA < eB ∧ sB < eA .                                 [8] AI cannot override these constraints. If time is insufficient, Feature 1 identifies unscheduled work rather than generating an infeasible plan. A proposed StudyPlan is saved as confirmed only after student approval. Integration, Reliability & Evaluation The shared orchestrator routes planning requests to Feature 1. In later releases, after validation of the Initial Release (F1 MVP), accepted PlannedStudyBlock records may provide context for F3 sessions, while F2 may supply RevisionRecommendation records. Feature 1 may read student-confirmed SessionOutcome records without treating them as proof of mastery. Before proposing a revision block, Feature 1 asks the student to confirm effort and deadline, checks availability, and requests approval; F2 never edits the schedule directly. Ambiguous dates trigger clarification, and unreadable PDFs fall back to manual entry. Proposed evaluation measures include deadline-extraction accuracy, hard-constraint violation rate, and correct replanning under changed availability. The F1 MVP covers manual or supported text-PDF task input, weekly scheduling, and approved rescheduling; LMS and calendar-wide synchronization are excluded. No implementation or measured improvement is claimed.
### 2.1.2    Feature 2 - Learning Assessment & Adaptive Revision
System scope: Core Feature (F2). Release phase: planned after validation of the Initial Release (F1 MVP). Feature Objective & Problem Definition Feature 2 addresses the hypothesized difficulty students face in identifying knowledge gaps and deciding what to revise. A student selects a topic, completes a source-grounded multiple- choice quiz, and receives topic-level feedback and revision recommendations. Inputs include authorized learning PDFs, the selected topic, and student responses. Outputs comprise validated quiz questions, an AssessmentResult, and a RevisionRecommendation. Quiz performance reflects understanding of sampled questions, not complete subject mastery. Computational Thinking Design
- Decomposition: The feature separates document retrieval, question generation and verifi-
cation, objective grading and topic-level assessment, and revision recommendation. Each 5

<!-- PDF page 11 -->
component has defined responsibilities and testable outputs.
- Pattern Recognition: Questions are classified by topic to identify repeated incorrect re-
sponses within or across assessments. Recurring errors are potential indicators of revision needs; their significance requires validation using actual quiz records.
- Abstraction: The proposed TopicPerformance entity retains these fields:
```text
    topic_id                      Identifier of the assessed topic.
    graded_count                  Number of valid answers graded for the topic.
    incorrect_count               Number of incorrect graded answers.
    last_assessed_at              Time of the most recent assessment.
    question_refs                 References to questions used for scoring and traceability.
```
Presentation details such as slide colors, animations, and screen positions are excluded. Core Algorithm & Technical Workflow
- Knowledge retrieval and quiz generation: The system extracts text from authorized lecture
PDFs and retrieves topic-relevant passages with document, page, and topic metadata. AI drafts candidate multiple-choice questions, options, and reference answers grounded in those passages. A proposed verification process checks question structure, source support, and answer correctness. Only reviewed, source-verified questions are eligible for automatic grading; ambiguous or unsupported questions are excluded.
- Deterministic assessment: Student responses are compared with verified answer keys.
The system records a QuizAttempt, calculates an AssessmentResult, and aggregates performance by topic. For topic t in a single assessment, this report defines the observed error rate as follows (no external source is cited): It
```text
                              ErrorRate(t) =      × 100%,             Gt > 0.
                                               Gt
```
For each assessment, It is the number of valid answers for topic t graded incorrect, and Gt is the total number of valid answers graded for that topic in the same assessment; the formula ap- plies when Gt > 0. If there are no valid responses, the topic is marked INSUFFICIENT_DATA; small samples cannot establish mastery.
- Adaptive learning system: Based on the user’s academic schedule, StudyFlow AI generates
a personalized study plan and practice quizzes using uploaded learning materials. After each quiz, the system automatically grades the answers, analyzes performance, and identifies weak knowledge areas. Using these results, the Adaptive Learning system generates targeted revision exercises with adjusted difficulty levels to address individual learning gaps. The revision tasks are then recommended for integration into the user’s study schedule, creating a continuous feedback loop that supports personalized learning and improvement. Integration, Reliability & Evaluation The shared orchestrator routes direct quiz requests or optional course/topic requests from Feature 3 to Feature 2. Feature 3 manages confirmed SessionOutcome records; Feature 2 retrieves authorized sources and owns assessment results and revision recommendations. Feature 1 receives recommendations, asks the student to confirm effort and deadline, checks constraints, 6

<!-- PDF page 12 -->
and requests approval before proposing a schedule change. A session outcome alone does not trigger a quiz score. Missing sources, unverifiable answers, or invalid submissions trigger clarification, exclusion, or review rather than unreliable scoring; failed transfers remain pending. Proposed evaluation measures include source support and answer-key correctness against human review, grading accuracy against known answers, revision-rule compliance, and successful transfer from Feature 2 to Feature 1. As a post-MVP core feature, F2 is proposed to cover text- based PDFs, reviewed multiple-choice questions, deterministic grading, topic-level assessment, and rule-based revision; OCR, essay grading, and predictive mastery modeling remain excluded. No implementation or measured results are claimed. 7

<!-- PDF page 13 -->
### 2.1.3    Feature 3 - Daily AI Learning
System scope: Core Feature (F3). Release phase: planned after validation of the Initial Release (F1 MVP). Feature Objective & Problem Definition Feature 3 is intended to provide contextual learning support during independent study. The need for this support and its value to target users remain to be validated through user research. In the proposed workflow, a student starts a session with a question or learning goal, receives explanations or progressive hints grounded in authorized course materials, and reviews a ses- sion summary before confirming it. Inputs include the student’s topic, question or goal, and authorized learning materials; outputs include source-linked guidance and, after confirmation, a SessionOutcome. A session outcome records confirmed activity and is not proof of subject mastery. Computational Thinking Design
- Decomposition: The proposed workflow separates session setup and goal capture, retrieval
of relevant passages, explanation or hint generation, follow-up interaction, and summary review and confirmation.
- Pattern Recognition: No recurring learning behavior is assumed as established. Interviews
and observed sessions are needed to identify common learning-support needs and determine whether progressive hints are useful.
- Abstraction: A proposed StudySession / SessionOutcome record retains session context,
learning goal, source references, and a student-confirmed summary. Interface styling and other presentation details are excluded from the learning record. Core Algorithm & Technical Workflow The student starts a session and states a question or learning goal. Feature 3 retrieves relevant passages from authorized course materials, retaining available document, page, and topic references. AI provides a contextual explanation or progressive hint based on the retrieved evidence; it must not present unsupported information as source-grounded. If the materials do not support an answer, the feature states the limitation and asks for clarification or additional material. The student may ask follow-up questions or end the session. At the end, the system presents a summary and saves it as a SessionOutcome only after the student reviews and confirms it; if the student declines, it is not saved as a confirmed outcome. Integration, Reliability & Evaluation The shared orchestrator routes direct learning requests to Feature 3 and preserves session context during handoffs. Feature 3 owns confirmed SessionOutcome records; an approved Planned StudyBlock from Feature 1 may provide course/topic context. Feature 3 may send an optional course/topic assessment request to Feature 2, which independently retrieves authorized sources and owns verified questions, grading, and revision recommendations. A learning session alone 8

<!-- PDF page 14 -->
does not create an assessment result. Missing or irrelevant sources trigger clarification or a safe fallback, and a declined summary is not stored as confirmed. Proposed evaluation checks include whether guidance is supported by retrieved passages, whether unsupported requests trigger the stated fallback, whether session summaries are saved only after confirmation, and whether optional handoffs complete without changing feature ownership. As a post-MVP core feature, F3 is proposed to provide guided sessions using authorized text-based materials; voice or video tutoring and unsupported general-purpose answers remain outside scope. No implementation or measured improvement is claimed. 9

<!-- PDF page 15 -->
## 2.2     Non-functional Requirements
- Reliability: Scheduling constraints and objective grading must be handled by deterministic
procedures rather than unconstrained AI output.
- Traceability: Quiz questions and explanations should retain source references, such as
document, page, and topic metadata.
- Usability: Students should be able to inspect proposed plans and recommendations and
retain control over confirmation and changes.
- Safety and uncertainty handling: The system should not present unsupported answers as
verified or treat limited quiz results as proof of full subject mastery.
- Maintainability: The three features should have separate responsibilities and exchange
defined records through the shared orchestration layer.
- Testability: The design should support measurable checks for scheduling violations, grading
accuracy, source support, and successful transfers between features.
## 2.3     Use Case Model
The use case model distinguishes the Initial Release (F1 MVP) from later-release core features. UC-01 covers F1 and is in the Initial Release. UC-02 (F2) and UC-03 (F3) document proposed post-MVP workflows and do not expand its scope. A quiz is optional and does not have to follow a guided study session. 10

<!-- PDF page 16 -->
```text
2.3.1    Overall Use Case Diagram: Initial Release and Post-MVP Core
         Features
                                                   StudyFlow AI
                                             F1 MVP: Manage tasks
                                             F1 MVP: Generate plan
                                           F1 MVP: Approve changes
                                            F3 core: Guided learning
                 Student
                                              F3 core: Request help
                                                F2 core: Take quiz
                                             F2 core: Review results
```
*Figure 2.1: Use cases grouped by Initial Release (F1 MVP) and post-MVP Core Features (F2/F3).*
### 2.3.2    Use Case Specifications
The following specifications describe three important proposed workflows. Schedule updates and session outcomes remain subject to student confirmation.
*Table 2.1: UC-01 (Initial Release / F1 MVP): Generate and Approve a Study Plan*
```text
 Specification        Description
 Actor                University Student
 Preconditions        The student has entered or confirmed task titles, start and end dates (the end date
                      is the deadline), priorities, estimated effort, and available study time.
 Postconditions       An approved plan is saved as confirmed. If the student does not approve it, the
                      plan remains proposed and no schedule change is applied.
 Basic flow           1. The student requests a study plan.
```
# 2. The system validates task titles, start and end dates, priorities, effort estimates,
and identifies missing or ambiguous information.
# 3. A deterministic scheduling process checks availability, end-date deadlines,
existing commitments, and overlaps.
# 4. The system presents the proposed plan and any unscheduled tasks.
# 5. The student reviews the proposal and approves it or requests changes.
# 6. The system saves the plan only after approval.
```text
 Alternate /          If task details are missing or ambiguous, the system asks the student to clarify
 exception flows      them. If available time is insufficient, it identifies unscheduled work instead of
                      presenting an infeasible plan. If the student rejects the proposal, it remains
                      unconfirmed.
                                                    11
```

<!-- PDF page 17 -->
*Table 2.2: UC-02 (Post-MVP Core Feature / F2): Complete a Quiz and Review Revision Priorities*
```text
 Specification        Description
 Actor                University Student
 Preconditions        Authorized course material and questions with reviewed, source-supported
                      answer keys are available for the selected topic.
 Postconditions       The system records deterministically graded results and presents topic-level
                      recommendations only when sufficient evidence exists. No schedule is changed
                      without student approval.
 Basic flow           1. The student selects a topic and starts a quiz.
```
# 2. The system presents eligible verified questions with source context.
# 3. The student submits responses.
# 4. The system grades responses against verified answer keys.
# 5. The system aggregates results by topic and explains any revision priorities.
# 6. The student reviews the results and may request a proposed schedule update.
```text
 Alternate /          If no verified questions or adequate source material are available, the system
 exception flows      explains the limitation and does not present unverified questions for grading. If
                      too few responses are graded, it reports insufficient evidence rather than
                      claiming mastery or assigning a strong priority. Invalid submissions are returned
                      for correction.
         Table 2.3: UC-03 (Post-MVP Core Feature / F3): Complete a Guided Learning Session
 Specification        Description
 Actor                University Student
 Preconditions        The student selects a learning topic and authorized course material relevant to
                      that topic is available.
 Postconditions       A session outcome is stored only after the student reviews and confirms its
                      summary.
 Basic flow           1. The student starts a guided session and states a question or learning goal.
```
# 2. The system retrieves relevant authorized passages.
# 3. It provides an explanation or progressive hint grounded in those passages.
# 4. The student may ask follow-up questions or end the session.
# 5. The system presents a session summary.
# 6. The student confirms the summary before it is saved as a session outcome.
```text
 Alternate /          If the retrieved materials do not support an answer, the system states that
 exception flows      limitation and asks for clarification or additional material. If the student declines
                      the summary, it is not saved as a confirmed session outcome.
                                                   12
```

<!-- PDF page 18 -->
Chapter 3 System Design
## 3.1     Overall System Architecture
StudyFlow AI is organized around a student-facing interface, a shared orchestration layer, three core feature modules, and shared academic records and authorized course materials. The Initial Release (MVP) includes only F1; F2 and F3 remain core features planned for later releases after F1 MVP validation.
- Feature 1 (F1) - Intelligent Academic Planner (Initial Release / MVP): Validates task
data, checks scheduling constraints, proposes study blocks, and handles student-approved planning changes.
- Feature 2 (F2) - Learning Assessment & Adaptive Revision (Post-MVP Core Feature):
Planned after F1 MVP validation; retrieves course sources, supports question generation and verification, grades verified objective questions, aggregates topic performance, and proposes revision recommendations.
- Feature 3 (F3) - Daily AI Learning (Post-MVP Core Feature): Planned after F1 MVP
validation; retrieves relevant course passages, provides source-grounded guidance, and records session outcomes only after student confirmation.
- Shared Orchestrator: Identifies request intent, routes work, asks for missing information,
manages handoffs, and triggers safe fallback when required. Representative feedback loop (post-MVP F2/F3 Core Features; proposed after validating the Initial Release): An approved F1 study block may start an F3 session using its course/topic context. F3 saves a SessionOutcome only after student confirmation and may send an optional course/topic quiz request to F2. F2 retrieves authorized sources, grades verified questions, and returns an AssessmentResult with an evidence-based RevisionRecommendation. F1 asks the student to confirm effort and deadline, checks feasibility, and proposes a revised plan for approval. Handoffs never change a confirmed schedule automatically; session activity is not proof of mastery. This is a proposed later-release flow, not implemented in the F1 MVP; its benefit remains unvalidated. 13

<!-- PDF page 19 -->
```text
3.1.1     Proposed Architecture Diagram
                                        Student-facing interface
                                           Shared orchestrator
                                        Intent routing, validation,
                                          clarification, handoffs
                Feature 1 (F1)               Feature 2 (F2)
                                                                           Feature 3 (F3)
                  Intelligent             Learning Assessment
                                                                        Daily AI Learning
             Academic Planner            and Adaptive Revision
                                                                      Post-MVP Core Feature
           Initial Release / MVP        Post-MVP Core Feature
                                    Shared academic records and
                                     authorized course materials
             Figure 3.1: F1 Initial Release (MVP) and post-MVP Core Features F2/F3.
3.2     Detailed Design
3.2.1     Core Data Entities and Feature Responsibilities
 Entity                       Core data and responsibility
 AcademicTask                 Task ID, course ID, title, start date, end date (deadline),
                              estimated and remaining minutes, and priority. Related
                              records should maintain provenance and permissions where
                              relevant.
 StudyPlan / Planned          Proposed schedule and allocated study intervals. A plan
 StudyBlock                   becomes confirmed only after student approval.
 QuizAttempt /                Submitted responses and calculated results based on verified
 AssessmentResult             answer keys.
 TopicPerformance             Topic ID, per-assessment graded and incorrect counts,
                              assessment history, last assessment time, and question
                              references. Supports trend-based revision prioritization but
                              does not establish mastery.
 Revision                     Topic, performance trend, supporting assessment evidence,
 Recommendation               and rationale for suggested revision.
 StudySession /               Session context, learning goal, source references, and a
 SessionOutcome               student-confirmed summary.
                                                   14
```

<!-- PDF page 20 -->
### 3.2.2     Conceptual Class / Data Model
The diagram summarizes proposed records and their ownership. F1 entities belong to the Initial Release (MVP); assessment and guided-learning entities belong to post-MVP Core Features F2/F3. Cardinalities describe intended relationships and remain subject to implementation design. MVP / F1
```text
    AcademicTask               MVP / F1                      MVP / F1
    taskId, courseId       1:N Planned                   1:N StudyPlan
    title                       StudyBlock                    planId, status
    start date, end date        start, end, minutes           approval timestamp
    priority, estimate
                                             1:N
                                                               Core / F3
                                Core / F3               1:0..1 Session
                                StudySession                   Outcome
                                sessionId, goal                outcomeId
                                                               confirmed summary
                                             1:0..N
                                                             Core / F2                 Core / F2
    Core / F2
                               Core / F2                     Assessment                Revision
    Learning               N:M Quiz                      1:N                       1:N
                                                             Result                    Recommendation
    Material
                               quizId                        resultId, score           recommendationId
    materialId
                               topic, difficulty             graded / incorrect        topic, evidence
    source, topic
                                                             counts                    rationale
                                               1:0..N
```
*Figure 3.2: Conceptual class/data model distinguishing F1 MVP records from F2/F3 Core Feature records.*
### 3.2.3     Main Interaction Sequence
# 1. The student submits a request and any relevant task information or authorized course material.
# 2. The orchestrator validates the request and routes it to the appropriate feature; missing or
ambiguous information is clarified.
# 3. The selected feature retrieves required records or source passages and applies deterministic
checks.
# 4. AI is used only for suitable language tasks, such as candidate extraction, candidate question
drafting, or contextual explanation.
# 5. The feature validates outputs, excludes unsupported results, and invokes a safe fallback when
needed.
# 6. The system presents the result and requests student confirmation for schedule changes or
session outcomes.
# 7. Approved records are saved and, where appropriate, handed to another feature through the
orchestrator. 15

<!-- PDF page 21 -->
```text
3.2.4      Illustrative F1 MVP Sequence Diagram
                                                                                        Academic
      Student           StudyFlow UI         Orchestrator          F1 Planner
                                                                                         Records
                Submit tasks
                                   Request plan
                                                        Route to F1
                                                                           Load task data
                                                                         Return constraints
                                               Plan + un-
                                            scheduled work
             Show proposal
            Approve / revise
                                          Approval decision
                                                                          Save if approved
        Figure 3.3: Proposed F1 planning interaction; schedule changes require student approval.
```
For half-open study blocks A and B, the overlap test below is consistent with PostgreSQL’s OVERLAPS semantics:
Overlap(A, B) ⇐⇒ sA < eB ∧ sB < eA .                         [8] For topic t in an assessment, this report defines the error rate as follows (no external source is cited): It
```text
                           ErrorRate(t) =       × 100%,         Gt > 0,
                                             Gt
```
where It is the number of valid answers graded incorrect and Gt is the number of valid graded answers for topic t in that assessment. With no valid responses, mark the topic INSUFFICIENT_DATA instead of assigning a misleading score.
## 3.3       User Interface Design
These figures are design mockups, not evidence of a completed implementation. The dashboard and planner are Initial Release (F1 MVP) concepts. Guided-learning and assessment screens illustrate post-MVP Core Features F2/F3. Cropped views focus on task entry, the weekly calendar, learning content, quiz interaction, and student confirmation. 16

<!-- PDF page 22 -->
*Figure 3.4: Initial Release / F1 MVP mockup: dashboard with upcoming tasks and the current study plan. 17*

![Hình ảnh được trích xuất từ trang PDF 22](assets/proposal/page-22-figure-002.png)

<!-- PDF page 23 -->
*Figure 3.5: Initial Release / F1 MVP mockups: focused views of task entry and the weekly calendar. 18*

![Hình ảnh được trích xuất từ trang PDF 23](assets/proposal/page-23-figure-003.png)
![Hình ảnh được trích xuất từ trang PDF 23](assets/proposal/page-23-figure-004.png)

<!-- PDF page 24 -->
*Figure 3.6: Post-MVP Core Feature / F3 concept with adjacent F2 practice-question functionality.*
*Figure 3.7: Post-MVP Core Feature / F2 mockup: source-based practice quiz. 19*

![Hình ảnh được trích xuất từ trang PDF 24](assets/proposal/page-24-figure-005.png)
![Hình ảnh được trích xuất từ trang PDF 24](assets/proposal/page-24-figure-006.png)

<!-- PDF page 25 -->
*Figure 3.8: Post-MVP Core Feature / F3 mockup: student review and confirmation of a study-session outcome. 20*

![Hình ảnh được trích xuất từ trang PDF 25](assets/proposal/page-25-figure-007.png)

<!-- PDF page 26 -->
Chapter 4 Development Process
## 4.1     Team Responsibilities
The six-member team divides responsibilities across project management, development, proposal preparation, and presentation.
```text
 Team member                     Role                     Responsibilities
 Châu Hoà Phát                   Project Manager;         Coordinate project progress and
                                 Backend Developer        backend development. Lead slide
                                                          preparation, supported by Hùng.
 Phạm Hùng Khôi                  Full-Stack Developer     Develop and integrate frontend and
                                                          backend workflows.
 Nguyễn Ngọc Thanh Hương         UI/UX Designer;          Lead proposal preparation and
                                 Frontend Developer       coordinate task assignments for all
                                                          team members.
 Nguyễn Trần Minh Khang          UI/UX Designer;          Design interfaces and implement
                                 Frontend Developer       frontend components.
 Huỳnh Nguyễn Thế Hiển           Backend Developer; AI    Develop backend services and
                                 Engineer                 integrate AI capabilities.
 Đặng Minh Hùng                  Backend Developer        Develop backend services and support
                                                          slide preparation.
```
Presentation assignments: Midterm - Hùng, Khang, and Hương. Final - Phát, Hiển, and Khôi. The team coordinates through shared requirements, task tracking, and integration reviews. These assignments describe planned responsibilities; completed contributions will be documented based on actual deliverables.
## 4.2     Current Deliverables and Expected Results
Based on the supplied project document, current design deliverables include the system overview, problem framing, three feature definitions, computational-thinking designs, proposed algorithms, integration rules, reliability fallbacks, evaluation metrics, and MVP boundaries. These are 21

<!-- PDF page 27 -->
design proposals; the document does not establish that a working implementation or measured results have been completed. Evaluation targets for the Initial Release (F1 MVP) include constraint violations and coordination effort against a documented baseline; no improvement is assumed. After validating F1, later releases may implement core features F2 and F3; evaluate verified grading, evidence-supported revision recommendations, source-grounded explanations, and handoff reliability. Benefits of the cross-feature loop remain unvalidated and must be measured rather than claimed.
## 4.3     Next-stage Plan
# 1. Conduct and document interviews with at least three target users to validate assumed pain
points and record current workflows and difficulties.
# 2. Confirm Initial Release (F1 MVP) requirements, data structures, and acceptance criteria;
plan core features F2 and F3 for later releases.
# 3. Review and validate the proposed use case, class/data model, sequence diagram, and interface
wireframes with target users.
# 4. Implement and test the Initial Release: F1 task validation, schedule conflict detection, and
student-approved replanning.
# 5. After validating F1, implement post-MVP core feature F2: source retrieval, question verifi-
cation, deterministic grading, and topic-level revision recommendations.
# 6. Then implement post-MVP core feature F3: guided learning with source-grounded responses
and confirmed session outcomes.
# 7. Evaluate the F1 MVP and any other core features selected for implementation using prede-
fined test cases, and report measured results with limitations.
## 4.4     Challenges and Risks
- Incorrect or ambiguous task extraction may produce invalid schedules; student confirmation
and explicit field validation are required.
- Insufficient available time may make all tasks impossible to schedule; the system should
expose unscheduled work instead of silently creating an infeasible plan.
- AI-generated questions or explanations may be unsupported; source checks and answer
review must be applied before results are used for grading or recommendations.
- Small quiz samples may overstate or understate topic performance; insufficient data should
trigger more assessment rather than a strong mastery claim.
- A session summary may describe activity without proving understanding; SessionOutcome
must remain separate from AssessmentResult.
- Cross-feature handoffs may fail or duplicate changes; transfers should have explicit status
and should not bypass student approval. Conclusion. This midterm defines proposed workflows and safeguards, not a working imple- mentation. F1 is the sole feature in the Initial Release (MVP); validate it before beginning the planned F2/F3 post-MVP phases. 22

<!-- PDF page 28 -->
References [1] T. T. D. Lu, P. H. Nguyen, and P. T. Nguyen, “Development and Evaluation of an AI- Powered Intelligent Reminder System to Support Academic Time Management: A Mixed- Methods Study of Cohort 50 and Cohort 51 Students at Can Tho University of Medicine and Pharmacy,” International Journal of Research and Innovation in Social Science, vol. 10, no. 6, pp. 12766–12777, 2026, doi: https://doi.org/10.47772/IJRISS.2026. 100600899. [2] C. L. van Es, C. L. Meaders, and M. K. Smith, “Examining Initial Expectations, Preferences, and Concerns of Diverse Students in an Introductory Statistics Course to Inform Course Improvements,” Journal of Statistics and Data Science Education, 2025, doi: https: //doi.org/10.1080/26939169.2025.2455193. [3] Chegg.org, “Global Student Survey 2025,” 2025. Report covering 11,706 undergrad- uate students across 15 countries. [Online]. Available: https://www.chegg.org/ global-student-survey-2025. Accessed: October 29, 2026. [4] Faculty of Information Technology, University of Science, VNU-HCM, “Engineering a Smart Virtual Assistant,” CSC10014: Computational Thinking Project Brief, 2026, pp. 2–5. [5] MyStudyLife, “MyStudyLife Features — Student Planner, Homework Tracker & Study App.” [Online]. Available: https://mystudylife.com/tour/. Accessed: October 26, 2026. [6] Quizlet, “Studying with Practice Tests,” Quizlet Help Center. [Online]. Available: https: //help.quizlet.com/hc/en-us/articles/25946589648013-Studying-with-Practice-Tests. Accessed: October 26, 2026. [7] Google, “Use Chat in Gemini Notebook” and “Generate Flashcards or Quizzes in Gemini Notebook,” Gemini Notebook Help. [Online]. Available: https: //support.google.com/gemininotebook/answer/16179559?hl=en; also avail- able: https://support.google.com/gemininotebook/answer/16958963?hl=en. Accessed: October 26, 2026. [8] PostgreSQL Global Development Group, “Date/Time Functions and Operators,” Post- greSQL 18 Documentation, Sec. 9.9. [Online]. Available: https://www.postgresql. org/docs/18/functions-datetime.html. 23
