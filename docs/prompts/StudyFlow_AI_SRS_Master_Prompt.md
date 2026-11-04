# MASTER PROMPT — Tạo tài liệu SRS hoàn chỉnh cho StudyFlow AI

> Bản chuyển đổi Markdown từ PDF nguồn. Nội dung văn bản được giữ theo thứ tự tài liệu; các hình ảnh nhúng được lưu trong thư mục `assets/`. Các header/footer lặp lại và số trang in ở chân trang được thay bằng chú thích trang HTML để tránh lặp nội dung trình bày.

<!-- PDF page 1 -->
MASTER PROMPT — Tạo tài liệu SRS hoàn chỉnh cho StudyFlow AI Prompt đặc tả yêu cầu phần mềm toàn dự án Tài liệu hướng dẫn sử dụng ChatGPT 04/11/2026 Mục lục
```text
Hướng dẫn sử dụng                                                                                      2
  Bối cảnh dự án đã được phản ánh trong prompt . . . . . . . . . . . . . . . . . . . . . . . . . .     2
```
MASTER PROMPT — GENERATE COMPLETE SOFTWARE REQUIREMENTS SPECIFICATION (SRS) FOR
STUDYFLOW AI                                                                                          2
# 1. ROLE AND RESPONSIBILITY . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
# 2. SOURCE MATERIALS — MANDATORY . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
Source interpretation rules . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
# 3. PROJECT CONTEXT AND SCOPE . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
## 3.1 Core features . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
## 3.2 Scope policy . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
# 4. REQUIRED SRS STRUCTURE . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
# 0. DOCUMENT CONTROL . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
# 1. INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
# 2. OVERALL SYSTEM DESCRIPTION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
# 3. SYSTEM ARCHITECTURE AND COMPONENT RESPONSIBILITIES . . . . . . . . . . . . . . 6
# 4. FUNCTIONAL REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
# 5. ORCHESTRATOR INPUT/OUTPUT CONTRACTS . . . . . . . . . . . . . . . . . . . . . . . 8
# 6. INTENT CATALOG AND PARAMETER SPECIFICATION . . . . . . . . . . . . . . . . . . . . 9
# 7. BUSINESS RULES AND VALIDATION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
# 8. WORKFLOW AND STATE MANAGEMENT . . . . . . . . . . . . . . . . . . . . . . . . . . 10
# 9. TOOL CONTRACTS AND API REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . . . . 11
# 10. DATA REQUIREMENTS AND DATA MODEL . . . . . . . . . . . . . . . . . . . . . . . . . 11
# 11. TIME AND DATE HANDLING . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
# 12. ERROR HANDLING AND RECOVERY . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
# 13. SECURITY AND AUTHORIZATION REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . 13
# 14. NON-FUNCTIONAL REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
# 15. EXTERNAL INTERFACE REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . 14
# 16. USE CASE SPECIFICATIONS . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
# 17. ACCEPTANCE CRITERIA . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
# 18. TESTING AND QUALITY ASSURANCE REQUIREMENTS . . . . . . . . . . . . . . . . . . . 15
# 19. TRACEABILITY MATRIX . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
# 20. MVP SCOPE AND RELEASE CRITERIA . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
# 21. OPEN ISSUES, RISKS, AND REQUIRED DECISIONS . . . . . . . . . . . . . . . . . . . . . 16
# 22. IMPLEMENTATION ROADMAP AND DEPENDENCIES . . . . . . . . . . . . . . . . . . . . 16
# 23. APPENDICES . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
# 5. REQUIREMENT WRITING RULES . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
# 6. MANDATORY TECHNICAL PRINCIPLES . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
1

<!-- PDF page 2 -->
```text
   7. DOCUMENT QUALITY REQUIREMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .            18
   8. FINAL OUTPUT — FILE GENERATION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .         18
        Word document formatting . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .       18
        Deliverables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   19
   9. FINAL SELF-REVIEW — REQUIRED BEFORE DELIVERY . . . . . . . . . . . . . . . . . . . . . .             19
   10. EXECUTION INSTRUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .         19
Lưu ý quan trọng khi sử dụng prompt                                                                  20
```
Ba cơ chế nên giữ nguyên trong SRS . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20 Lưu ý về nguồn proposal chính thức . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20 Hướng dẫn sử dụng Tài liệu này chứa toàn bộ prompt được xây dựng cho dự án StudyFlow AI. Đính kèm hai tài liệu nguồn context.md và cong_viec_can_lam.md vào ChatGPT, sau đó sao chép toàn bộ nội dung từ phần MASTER PROMPT trở đi để yêu cầu tạo SRS. Prompt được thiết kế theo hướng SRS toàn dự án nhưng đặc tả sâu F1 – Intelligent Academic Planner. F2 và F3 được mô tả ở mức độ mà tài liệu nguồn hỗ trợ, không tự ý mở rộng thành phạm vi MVP. Bối cảnh dự án đã được phản ánh trong prompt
- F1 – Intelligent Academic Planner: trọng tâm Initial MVP.
- F2 – Learning Assessment & Adaptive Revision: Post-MVP.
- F3 – Daily AI Learning: Post-MVP.
- Các thiết kế Step 01–04 hiện là thiết kế sơ bộ, chưa được freeze; tài liệu công việc ghi nhận chưa có
bằng chứng triển khai hoặc benchmark thực tế.
- Các nội dung chưa được nhóm quyết định phải được ghi rõ là TBD, PROPOSED hoặc REQUIRES REVIEW.
- Tài liệu proposal chính thức 0-main-20.pdf chưa được cung cấp để đối chiếu trực tiếp trong nguồn
hiện tại. MASTER PROMPT — GENERATE COMPLETE SOFTWARE REQUIREMENTS SPECIFICATION (SRS) FOR STUDYFLOW AI
# 1. ROLE AND RESPONSIBILITY
Act as a Senior Software Requirements Engineer, System Analyst, and Solution Architect with extensive experience in designing production-grade software systems and writing formal Software Requirements Specification (SRS) documents. Your task is to analyze all provided project documents and produce a comprehensive, technically precise, internally consistent, and implementation-ready Software Requirements Specification (SRS) for StudyFlow AI. The document must be sufficiently detailed for: - Software developers to implement the system. - AI/ML engineers to design and integrate the NLU/LLM components. - Backend developers to define APIs, business logic, validation, and persistence. - Frontend developers to implement user interactions and workflows. - QA engineers to derive test cases and verify requirements. - Project managers to manage scope, dependencies, and acceptance criteria. - Academic evaluators to understand the system’s objectives, architecture, requirements, and technical feasibility. Do not produce a generic SRS template. Produce an SRS specifically tailored to the actual StudyFlow AI project. 2

<!-- PDF page 3 -->
# 2. SOURCE MATERIALS — MANDATORY
Carefully read and analyze the entirety of the following documents before writing:
1. context.md — StudyFlow AI project context, system architecture, features, data model, intent catalog,
parameter schemas, tool contracts, and preliminary Orchestrator Pipeline.
2. cong_viec_can_lam.md — Current outstanding tasks, priorities, dependencies, unresolved decisions,
and implementation roadmap. Treat these documents as the primary sources of truth for the current project context. Source interpretation rules You MUST distinguish the following four categories throughout the SRS: A. Confirmed baseline Information explicitly identified as part of the project’s existing baseline in the source documents. B. Preliminary design Information that has been discussed or designed conceptually but has not been formally approved or frozen. C. Proposed requirements Requirements that can reasonably be derived from the existing system design to make the SRS complete. These must be explicitly marked as proposals requiring team review. D. Open decisions / TBD Information that is missing, unresolved, inconsistent, or requires a decision from the project team. Strictly follow these rules:
- Never fabricate decisions, technologies, APIs, database schemas, performance benchmarks,
implementation status, or project commitments.
- Never interpret a conceptual design as an implemented feature.
- Never interpret an example JSON object as a finalized API schema.
- Never interpret a proposed workflow as an officially approved workflow.
- Never assign team members, owners, deadlines, or performance targets unless the source material
explicitly provides them.
- Never silently resolve inconsistencies between source documents.
- When two sources disagree, document the discrepancy and identify the decision required.
- If an important requirement is not supported by the sources, mark it as TBD and explain what
information is missing.
- Do not invent detailed F2/F3 behavior merely to make the document appear complete.
If the official project proposal 0-main-20.pdf is not supplied, explicitly state that the SRS has not been directly verified against that document. Do not claim that any unverified requirement is officially mandated by the proposal. You may derive reasonable technical requirements, but clearly label them as proposed requirements rather than confirmed project decisions.
# 3. PROJECT CONTEXT AND SCOPE
The project is: StudyFlow AI — Intelligent Academic Learning Assistant Academic context: - Course: CSC10014 — Computational Thinking. - Institution: University of Science, VNU- HCM (HCMUS). - Project direction: Intelligent Academic Learning Virtual Assistant. 3

<!-- PDF page 4 -->
## 3.1 Core features
The system has three core features: F1 — Intelligent Academic Planner - Manage academic tasks. - Manage deadlines and estimated workloads. - Allow users to declare their availability. - Automatically generate study plans. - Display existing study plans. - Propose study schedule adjustments. - Require appropriate user approval before committing schedule changes. F1 is the primary focus of the Initial MVP and MUST receive the most detailed functional and technical specification. F2 — Learning Assessment & Adaptive Revision - Quiz generation based on learning materials. - Question and answer verification. - Assessment and grading. - Adaptive revision recommendations. F2 is Post-MVP. F3 — Daily AI Learning - Contextual explanations grounded in learning materials. - Progressive hints. - Learning session summaries. - User-confirmed session outcomes. F3 is Post-MVP. The long-term integration direction is: F1 -> F3 -> F2 (optional) -> F1
## 3.2 Scope policy
The SRS must describe the entire StudyFlow AI product at the system level. However: - Specify F1 in implementation-level detail. - Specify F2 and F3 at the level supported by the source materials. - Clearly mark F2/F3 as Post-MVP and out of the current detailed implementation scope. - Explain the architectural boundaries that allow future integration. - Do not turn F2/F3 into mandatory MVP requirements. For F1, explicitly distinguish: - Initial MVP Core. - Proposed extensions requiring approval. - Deferred features. In particular, the following scope decisions remain open and MUST be recorded as TBD until approved: - UPDATE_TASK. - DELETE_TASK. - CREATE_STUDY_BLOCK (manual scheduling). - Whether FixedCommitment should be a separate entity. - Advanced recurrence and related scheduling features. Do not silently include deferred features in the MVP.
# 4. REQUIRED SRS STRUCTURE
Create a formal SRS document using a professional, IEEE/ISO/IEC/IEEE 29148-inspired requirements engineering structure. The document must contain the following sections.
# 0. DOCUMENT CONTROL
Include: - Document title. - Project name. - Document identifier. - Version. - Creation date. - Authors/owners: TBD if unavailable. - Reviewers/approvers: TBD if unavailable. - Document status. - Revision history. - Approval status. - Distribution and intended audience. Do not invent names or approval records. 4

<!-- PDF page 5 -->
# 1. INTRODUCTION
```text
1.1 Purpose    Explain why this SRS exists, what it specifies, and who will use it.
1.2 Scope   Describe StudyFlow AI and its overall boundaries.
```
## 1.3 Project Background Explain the academic problems the system addresses.
```text
1.4 Objectives    Describe system-level and feature-level objectives.
1.5 Intended Audience       Identify developers, AI engineers, testers, project managers, and academic
```
stakeholders.
## 1.6 Definitions, Acronyms, and Abbreviations Define all important terms, including: - SRS - MVP
- LLM - NLU - Orchestrator - Intent - Slot - PendingAction - ValidatedCommand - AcademicTask - PlannedStudyBlock - StudyPlan - Availability - FixedCommitment - Proposal - Approval - Commit - Idempotency - Entity Resolution
## 1.7 References List the supplied source documents and any additional references actually consulted.
## 1.8 Document Conventions        Explain requirement numbering, priority labels, requirement statuses, and
normative terminology.
# 2. OVERALL SYSTEM DESCRIPTION
## 2.1 Product Perspective      Explain how StudyFlow AI fits into the broader academic learning assistant
concept.
## 2.2 Product Functions     Summarize F1, F2, and F3.
## 2.3 User Classes and Characteristics Identify user types supported by the source documents.
Do not invent administrator, lecturer, or other roles as confirmed actors without evidence.
## 2.4 Operating Environment Document known operating environment information.
Unconfirmed platforms, devices, deployment infrastructure, and operating systems must be marked TBD.
## 2.5 Design and Implementation Constraints Include: - Authenticated backend context. - Deterministic
business rule validation. - LLM output must not directly authorize database writes. - Scheduling constraints. - User approval requirements. - Source limitations. - MVP scope restrictions.
```text
2.6 Assumptions and Dependencies          List assumptions and dependencies separately.
2.7 Product Boundaries      Explain what StudyFlow AI does and does not do.
2.8 Product Roadmap       Distinguish Initial MVP, Post-MVP, and deferred capabilities.
                                                      5
```

<!-- PDF page 6 -->
# 3. SYSTEM ARCHITECTURE AND COMPONENT RESPONSIBILITIES
Describe the proposed Hybrid, Contract-First architecture: User Interface -> Shared Orchestrator -> F1 Backend -> Shared Academic Records Specify each component’s responsibilities.
## 3.1 User Interface
- Accept natural-language input.
- Display clarification questions.
- Display tasks and schedules.
- Display proposals and partial plans.
- Support approve/reject interactions.
- Display errors and unscheduled work.
## 3.2 LLM/NLU Layer
- Intent classification.
- Slot extraction.
- Multi-intent detection.
- Ambiguity identification.
- Candidate parameter generation.
Clearly state that LLM/NLU output is untrusted input.
## 3.3 Shared Orchestrator
- Input processing.
- Context management.
- Pending-action management.
- Validation coordination.
- Clarification.
- Entity resolution coordination.
- Deterministic tool dispatch.
- Approval routing.
- Response handling.
- Error recovery.
## 3.4 F1 Backend
- Authentication and authorization enforcement.
- Business rule validation.
- Entity resolution.
- Task management.
- Availability management.
- Study plan generation.
- Rescheduling proposals.
- Approval verification.
- Revalidation.
- Persistence and transaction handling.
## 3.5 Shared Academic Records Specify the responsibility of the shared academic data layer and its
potential role in future F2/F3 integration. 6

<!-- PDF page 7 -->
## 3.6 Component Interaction Include: - Component responsibility matrix. - Trust boundaries. - Data flow.
- Sequence diagrams for the most important workflows. - Failure boundaries.
# 4. FUNCTIONAL REQUIREMENTS
This is the most important section. Every functional requirement must: - Have a unique ID. - Describe one clear behavior. - Use unambiguous language. - Identify preconditions and postconditions where relevant. - Specify expected system responses. - Include validation and failure behavior. - Be testable. - Have a priority and source/status classification. Use requirement IDs such as: - SYS-FR-001 - F1-FR-001 - F2-FR-001 - F3-FR-001 Prioritize F1.
## 4.1 Natural Language Input and Intent Recognition           Specify how users communicate with the system
in Vietnamese natural language. Cover: - Single-intent requests. - Multiple-intent requests. - Ambiguous requests. - Unsupported requests. - Incomplete requests. - Intent classification errors.
## 4.2 F1 — Task Management Specify: - Create task candidate. - Validate task information. - Ask for
missing information. - Confirm task. - Retrieve/search tasks. - Handle duplicate task names. - Resolve task references. - Update and delete only if included in the approved scope. Distinguish task candidate from confirmed academic task.
## 4.3 F1 — Availability Management Specify: - Declare availability. - Date-specific availability. - Weekday-
based availability. - Weekly recurrence. - Time interval validation. - Timezone handling. - Conflicts with existing confirmed plans. - Availability modification. - Availability deletion, if supported by approved scope.
## 4.4 F1 — Automatic Study Plan Generation Specify: - Planning period. - Task selection mode. -
Eligible tasks. - Scheduling order. - Deadline handling. - Priority handling. - Available time slots. - Fixed commitments/busy intervals. - Workload and duration allocation. - Conflict detection. - Partial scheduling. - Unscheduled tasks. - Study plan proposal generation. Explain that the scheduler must use deterministic rules and must not rely on the LLM to bypass hard scheduling constraints.
## 4.5 F1 — Study Plan Retrieval Specify: - Retrieve study plans. - Filter by period. - Filter by status. - Display
confirmed versus proposed plans. - Handle empty results.
## 4.6 F1 — Rescheduling Specify: - Identify the target study block. - Resolve the referenced entity. - Receive
new date/time or constraints. - Validate the requested change. - Generate a revised proposal. - Handle conflicts. - Preserve the existing confirmed schedule until approval.
## 4.7 F1 — Approval and Commit Specify: - Display the proposal. - Approve proposal. - Reject proposal. -
Cancel proposal. - Check proposal identity. - Verify the authenticated user. - Verify proposal version. - Check expiration. - Revalidate constraints. - Commit changes. - Handle stale data. - Prevent duplicate commits. A proposal must never be treated as confirmed before an appropriate approval and successful commit. An LLM-generated approval=true is not valid evidence of user approval. 7

<!-- PDF page 8 -->
## 4.8 F1 — Conversational Context and Pending Actions Specify: - Maintain pending actions across
multiple messages. - Merge short answers into the correct pending action. - Resolve follow-up references. - Handle slot corrections. - Cancel pending actions. - Handle topic changes. - Handle expiration. - Handle multiple pending actions. - Prevent ambiguous approval routing.
## 4.9 F2 — Learning Assessment & Adaptive Revision Only specify requirements supported by the
source documents. Mark detailed algorithms, question formats, grading policies, data requirements, and acceptance criteria as TBD if they are not available.
## 4.10 F3 — Daily AI Learning      Only specify requirements supported by the source documents.
Mark detailed retrieval mechanisms, learning materials processing, hint-generation policies, and session management details as TBD when unsupported.
# 5. ORCHESTRATOR INPUT/OUTPUT CONTRACTS
Define and document all important system boundary objects. At minimum, consider:
## 5.1 UserMessage Include: - Original message. - Timestamp. - Timezone. - Locale. - Conversation context.
- Separation between user-provided input and trusted system/authentication context.
## 5.2 ExtractionResult Include: - Detected intent(s). - Candidate slots. - Original expressions. - Ambiguities.
- Missing fields. - Field provenance where applicable.
## 5.3 PendingAction Include: - Action identifier. - Intent. - Collected slots. - Missing/ambiguous fields. -
Workflow state. - Version. - Expiry. - Proposal reference where relevant.
## 5.4 ValidatedCommand Include: - Resolved operation. - Normalized arguments. - Resolved entity
references. - Validation status. - Trusted context references. Do not trust identity, entity IDs, authorization, or approval information generated by the LLM.
## 5.5 ToolResult Include: - Operation result type. - Read/draft/proposal/commit/error classification. -
Entity IDs. - Version. - Unscheduled work. - Relevant user-facing information.
## 5.6 Approval Evidence Define how approval is securely associated with: - The authenticated user. - A
specific proposal. - A specific proposal version. - An expiration period. - A valid interaction. Clearly distinguish what is generated by LLM, what is verified by the Orchestrator, and what is enforced by the Backend. For every contract: - Define fields. - Define data types. - Define required/optional/null behavior. - Define enums. - Define constraints. - Provide valid JSON examples. - Provide invalid JSON examples. - Explain validation behavior. JSON Schema or Pydantic may be proposed, but do not claim either has been selected by the project. 8

<!-- PDF page 9 -->
# 6. INTENT CATALOG AND PARAMETER SPECIFICATION
Document the preliminary intent catalog:
- CREATE_TASK
- UPDATE_TASK
- DELETE_TASK
- SET_AVAILABILITY
- GENERATE_STUDY_PLAN
- RESCHEDULE_STUDY_BLOCK
- GET_STUDY_PLAN
- CREATE_STUDY_BLOCK
For each intent, include: - Description. - Typical user expressions. - Required parameters. - Optional parameters. - Parameter data types. - Validation rules. - Defaults, if confirmed. - Context-dependent parameters. - Missing information behavior. - Ambiguity behavior. - Entity resolution requirements. - Allowed operations. - Scope status. - Example extraction result. - Example validated command. Explicitly distinguish: - Extraction requirements. - Execution requirements. - Fields that may be resolved from trusted context or the database. Resolve terminology inconsistencies through a proposed canonical vocabulary table, including: - candidate_id versus task_candidate_id. - parameters versus slots. - end_date versus deadline. - duration_minutes versus explicit start/end intervals. Do not silently claim that a proposed naming convention has been approved.
# 7. BUSINESS RULES AND VALIDATION
Write a centralized business rule specification. Cover:
## 7.1 Structural Validation
- JSON validity.
- Required structure.
- Data types.
- Enums.
- Format constraints.
## 7.2 Semantic Validation
- Required information.
- Positive duration.
- Valid date ranges.
- Time interval validity.
- Field relationships.
- Valid recurrence definitions.
## 7.3 Domain Validation
- Entity existence.
- Ownership.
- User authorization.
- Availability.
- Deadline constraints.
- Existing commitments.
- Schedule overlap.
9

<!-- PDF page 10 -->
- Task eligibility.
- Planning period boundaries.
## 7.4 State Validation
- Pending action validity.
- Proposal validity.
- Proposal version.
- Approval validity.
- Expired actions.
- Stale data.
Explicitly document the preliminary validation statuses: - READY - NEEDS_CLARIFICATION - UNSUPPORTED - INVALID Keep validation status separate from workflow state and entity status.
## 7.5 Scheduling Invariants       Specify the confirmed design principles and clearly mark unresolved rules.
At minimum: - Only eligible confirmed tasks may be scheduled. - Scheduling must respect availability. - Scheduling must respect existing commitments. - Scheduling must not create invalid overlaps. - Deadline constraints must be respected. - Remaining workload must be handled consistently. - Partial results must explicitly identify unscheduled work. - Confirmed schedules must not be silently modified. - The same input and configuration should produce a consistent result where deterministic behavior is required. Document the preliminary scheduling ordering: 1. Earlier deadlines first. 2. Priority as a tie-breaker when deadlines are equal. Further tie-breaking, block splitting, workload distribution, and remaining-work calculations must be specified as TBD or proposed where not finalized.
# 8. WORKFLOW AND STATE MANAGEMENT
Define the Orchestrator workflow in sufficient detail for implementation. Use the preliminary 10 logical stages:
# 1. Input Processing.
# 2. Intent Classification.
# 3. Slot Extraction.
# 4. Context Management.
# 5. Validation.
# 6. Clarification.
# 7. Tool Dispatch.
# 8. Response Handling.
# 9. Confirmation & Persistence.
# 10. Error Recovery.
These stages may involve loops and branches; do not force them into a strictly linear sequence. Provide:
## 8.1 Workflow State Model        Define states and transitions.
## 8.2 State Transition Table Include: - Current state. - Input/event. - Preconditions. - Guard conditions. -
System action. - Next state. - Side effects. - Failure handling.
## 8.3 Pending Action Lifecycle        Cover creation, updates, completion, cancellation, expiration, and
versioning. 10

<!-- PDF page 11 -->
## 8.4 Multi-turn Conversation Scenarios      Include realistic Vietnamese conversations.
## 8.5 Multi-intent Handling Specify sequential execution and dependencies without introducing
unnecessary workflow complexity.
## 8.6 Approval Routing     Ensure that user approval can only be associated with a clearly identified pending
proposal. Include Mermaid state diagrams and sequence diagrams.
# 9. TOOL CONTRACTS AND API REQUIREMENTS
Document the preliminary tool catalog:
- create_task_candidate
- confirm_task
- search_tasks
- set_availability
- generate_study_plan
- get_study_plan
- propose_reschedule
- approve_study_plan
For every operation, specify:
# 1. Operation purpose.
# 2. Operation category: READ, DRAFT, PROPOSE, or COMMIT.
# 3. Input schema.
# 4. Output schema.
# 5. Validation rules.
# 6. Authorization rules.
# 7. Confirmation requirements.
# 8. Business rules.
# 9. Error responses.
# 10. Version handling.
# 11. Idempotency behavior.
# 12. Side effects.
# 13. Example request.
# 14. Example response.
Do not assume that tool names are already implemented APIs. If API paths, HTTP methods, authentication protocols, or transport formats are unknown, mark them TBD rather than inventing them. Include an intent-to-operation mapping table. Do not force a one-intent-to-one-tool mapping. Also specify how unsupported operations should be handled when corresponding contracts do not exist.
# 10. DATA REQUIREMENTS AND DATA MODEL
Document the data model based on existing source materials. At minimum: 11

<!-- PDF page 12 -->
## 10.1 AcademicTask Include known attributes: - task_id - course_id - title - start_date - end_date /
deadline - estimated_minutes - remaining_minutes - priority Explain: - Task candidate. - Draft task. - Confirmed task. - Scheduling eligibility.
## 10.2 PlannedStudyBlock Explain: - Time interval. - Associated task. - Start/end time. - Duration. -
Relationship with StudyPlan. - Confirmation status.
## 10.3 StudyPlan Explain: - Planning period. - Associated study blocks. - Proposal status. - Confirmation
status. - Version. - Unscheduled tasks.
## 10.4 Availability    Explain date-specific and recurring availability.
## 10.5 FixedCommitment Document as a proposed or unresolved entity unless confirmed by the source
materials.
## 10.6 PendingAction      Document the information required for multi-turn interaction.
## 10.7 Approval/Proposal Describe the relationship between user approval, proposal identity, version,
and commit. For every entity: - Define attributes. - Data types. - Required/optional fields. - Constraints. - Relationships. - Lifecycle/status. - Ownership. - Data validation. Include: - ERD using Mermaid. - Data dictionary. - Relationship cardinalities. - Integrity constraints. - Unresolved schema decisions. Never invent database-specific implementation details unless explicitly labeled as proposals.
# 11. TIME AND DATE HANDLING
This section must be particularly precise because scheduling depends heavily on time interpretation. Specify: - Timezone source. - Request timestamp. - Local time interpretation. - Relative date resolution. - Week boundaries. - Planning periods. - Deadlines containing only dates. - Explicit date-time inputs. - Ambiguous expressions such as morning/evening. - Intervals crossing midnight. - Duration-to-interval conversion. - Recurrence semantics. - Time normalization. - Daylight saving considerations if applicable to supported timezones. Do not automatically convert ambiguous expressions such as “sáng”, “chiều”, or “tối” into exact start times. If the necessary rule is not available, mark it as TBD and describe its impact. Provide Vietnamese examples and expected interpretation.
# 12. ERROR HANDLING AND RECOVERY
Specify a complete error handling policy. Include the preliminary codes: - MISSING_REQUIRED_FIELD - INVALID_PARAMETER - ENTITY_NOT_FOUND - TIME_CONFLICT - INSUFFICIENT_AVAILABILITY - STALE_PLAN_VERSION - APPROVAL_REQUIRED Treat this list as preliminary, not exhaustive. Add or propose other error categories only when justified. For each error, define: - Trigger condition. - Responsible component. - Error structure. - User-facing response. - Retryability. - Recovery action. - Whether database changes may have occurred. 12

<!-- PDF page 13 -->
Cover: - Invalid LLM output. - LLM timeout. - Invalid JSON. - Tool failure. - Database failure. - Concurrent updates. - Duplicate requests. - Expired proposals. - Stale versions. - Partial scheduling. - Failed commit. - Rollback and consistency considerations.
# 13. SECURITY AND AUTHORIZATION REQUIREMENTS
Specify system security requirements, especially around AI-generated commands and approval. Include: - Authenticated identity. - Authorization enforcement. - User ownership of entities. - Trusted versus untrusted data. - Input validation. - Prompt injection considerations where relevant. - Protection against unauthorized tool dispatch. - Protection against forged approval. - Proposal/version binding. - Data isolation between users. - Secure error handling. - Sensitive data handling and logging. Clearly identify which component is responsible for each security enforcement rule. Never allow the LLM to independently establish: - user_id. - Entity ownership. - Access permissions. - Approval validity. - Database write authorization.
# 14. NON-FUNCTIONAL REQUIREMENTS
Create measurable non-functional requirements where evidence or decisions exist. Cover:
## 14.1 Performance
- Request processing latency.
- Intent/slot extraction latency.
- Scheduling execution time.
- Database response time.
Do not fabricate numeric performance targets. Mark unapproved thresholds TBD and propose how they should be measured.
## 14.2 Reliability and Availability
- Error handling.
- Retry behavior.
- Data consistency.
- Recovery.
## 14.3 Scalability    Discuss likely growth dimensions and identify capacity assumptions requiring
validation.
## 14.4 Usability Focus on natural Vietnamese interaction, minimal clarification, understandable
scheduling results, and clear approval controls.
```text
14.5 Maintainability     Include component separation, contracts, modularity, and testability.
14.6 Security and Privacy     Include the requirements defined in Section 13.
14.7 Compatibility and Portability      Specify only verified constraints; unknown platform requirements
```
remain TBD. 13

<!-- PDF page 14 -->
## 14.8 Observability and Auditability Propose logs and traceability for important state changes,
operations, and approval events, while clearly marking unresolved retention and privacy policies. Every NFR must have: - Unique ID. - Description. - Rationale. - Measurement method. - Acceptance criterion or TBD status. - Priority. - Source/status classification.
# 15. EXTERNAL INTERFACE REQUIREMENTS
Specify known and proposed interfaces.
## 15.1 User Interface Input, task management, availability, schedule display, proposal preview,
confirmation, and error feedback.
## 15.2 Software Interfaces Orchestrator-to-backend contracts, LLM/NLU adapter, data persistence, and
future shared feature integration.
## 15.3 Communication Interfaces         Mark protocols, endpoints, and transport methods TBD when not
selected.
## 15.4 Data Exchange Formats       Describe JSON-based examples where useful without claiming a finalized
implementation format.
# 16. USE CASE SPECIFICATIONS
Create detailed use cases for the main F1 workflows. At minimum: - UC-01: Create an Academic Task. - UC-02: Confirm a Task. - UC-03: Search Academic Tasks. - UC-04: Set Availability. - UC-05: Generate a Study Plan. - UC-06: Retrieve a Study Plan. - UC-07: Propose Rescheduling. - UC-08: Approve a Study Plan. - UC-09: Reject a Proposal. - UC-10: Handle Missing or Ambiguous Information. - UC-11: Continue a Multi-turn Conversation. - UC-12: Handle Scheduling Conflict. - UC-13: Handle Partial Scheduling. For each use case, include: - Use case ID. - Name. - Primary actor. - Supporting components. - Goal. - Preconditions. - Trigger. - Main success scenario. - Alternative flows. - Exception flows. - Postconditions. - Related functional requirements. - Relevant business rules. Use detailed Vietnamese natural-language conversation examples. Do not include unresolved extension use cases as mandatory MVP workflows.
# 17. ACCEPTANCE CRITERIA
Define testable acceptance criteria for each major F1 workflow. Cover: - Correct task creation and confirmation. - Correct eligibility handling. - Availability validation. - Deterministic scheduling behavior. - Deadline constraints. - Conflict handling. - Partial scheduling. - Pending action continuity. - Entity resolution. - Proposal generation. - Approval verification. - Stale proposal rejection. - Idempotent commit behavior. - Data persistence consistency. Every acceptance criterion must have a unique ID. Do not fabricate numerical pass thresholds. If a threshold has not been approved, identify it as an open decision. 14

<!-- PDF page 15 -->
# 18. TESTING AND QUALITY ASSURANCE REQUIREMENTS
Develop a comprehensive test strategy. Include: - Unit testing. - Integration testing. - API/contract testing. - Workflow testing. - End-to-end testing. - Security testing. - Regression testing. - AI/NLU evaluation. Develop a test matrix covering:
# 1. Single intent with complete information.
# 2. Missing required fields.
# 3. Invalid type or value.
# 4. Negative duration or workload.
# 5. Confusion between GENERATE_STUDY_PLAN, CREATE_STUDY_BLOCK, and SET_AVAILABILITY.
# 6. Relative dates.
# 7. Ambiguous morning/evening expressions.
# 8. Invalid time intervals.
# 9. Intervals crossing midnight.
# 10. Duplicate task names.
# 11. Nonexistent or unauthorized entities.
# 12. Multi-turn clarification.
# 13. Slot correction.
# 14. Cancellation.
# 15. Topic change.
# 16. Multiple pending actions.
# 17. Multiple intents with dependencies.
# 18. Scheduling conflicts.
# 19. Insufficient availability.
# 20. Partial scheduling.
# 21. Invalid approval.
# 22. Wrong proposal target.
# 23. Expired proposal.
# 24. Stale version or changed underlying data.
# 25. Retry and duplicate commits.
# 26. Concurrent approval.
# 27. LLM timeout or invalid JSON.
For each test case, specify: - Test ID. - Preconditions. - Input message. - Trusted context. - Database fixtures. - Initial state. - Expected intent. - Expected slots. - Expected validation status. - Expected workflow state. - Expected tool operation. - Expected system response. - Expected persistence behavior. - Forbidden side effects. Include an AI evaluation strategy for: - Intent classification. - Slot extraction. - Clarification quality. - Tool dispatch correctness. - End-to-end task completion. - Violations of authorization or scheduling constraints. Clearly distinguish between proposed tests and tests already executed.
# 19. TRACEABILITY MATRIX
Create a complete traceability matrix connecting: Source -> Business Objective -> Functional Requirement -> Business Rule -> Use Case -> API/Tool Contract -> Test Case For every requirement, identify: - Requirement ID. - Source document/reference. - Source classification. - Related business objective. - Related use case. - Related component. - Related business rules. - Related test cases. - Current status. No requirement should be left without a traceability record. For requirements derived from proposals rather than confirmed source content, mark them accordingly. 15

<!-- PDF page 16 -->
# 20. MVP SCOPE AND RELEASE CRITERIA
Define: - Initial MVP scope. - In-scope requirements. - Out-of-scope requirements. - Deferred functionality. - Dependencies. - Release acceptance criteria. F1 must be treated as the MVP focus. Do not declare the MVP complete merely because its design is documented. A release claim must require actual implementation and test evidence.
# 21. OPEN ISSUES, RISKS, AND REQUIRED DECISIONS
Create a structured issue register. At minimum, evaluate the unresolved topics from the source documents:
- F1 scope confirmation.
- Manual scheduling scope.
- Update/delete scope.
- FixedCommitment modeling.
- Orchestrator Input/Output Contract.
- Canonical parameter vocabulary.
- Tool contracts.
- State management and routing.
- Multi-intent dependency handling.
- Timezone and date-time normalization.
- Scheduling tie-break and workload rules.
- Partial proposal versus error semantics.
- Approval evidence.
- Concurrency control.
- Persistence and recovery.
- Backend/API/database technology selection.
- LLM/NLU model selection and benchmark.
- Quantitative performance targets.
- Acceptance thresholds.
- Ownership and project timeline.
For each item, provide: - Issue ID. - Description. - Why it matters. - Affected requirements. - Risk level, with rationale. - Decision needed. - Suggested options when appropriate. - Current status. Do not select an option on behalf of the team when the decision remains open.
# 22. IMPLEMENTATION ROADMAP AND DEPENDENCIES
Present a dependency-aware roadmap based on the supplied work plan. Distinguish: - P0: Design completion and contract freeze. - P1: Implementation and verification. - P2: Scope- dependent extensions. - F2/F3: Post-MVP. Represent dependencies with a Mermaid flowchart or dependency diagram. Do not assign owners or dates that have not been confirmed.
# 23. APPENDICES
Include: - Canonical terminology. - Requirement ID conventions. - JSON examples. - Error code catalog. - State transition tables. - API/tool catalog. - Entity data dictionary. - Additional Mermaid diagrams. - Assumption register. - TBD register. - Source-to-requirement mapping. 16

<!-- PDF page 17 -->
# 5. REQUIREMENT WRITING RULES
All requirements must be written in precise, testable language. Use the form: [Requirement ID] The system SHALL ... Use:
- SHALL for mandatory requirements.
- SHOULD for recommended requirements.
- MAY for optional capabilities.
However, the normative strength must reflect actual source status. Do not use SHALL to present an unapproved proposal as a confirmed obligation. Add an explicit status label such as PROPOSED, TBD, or REQUIRES REVIEW. Each requirement must be:
# 1. Atomic — one requirement should express one principal obligation.
# 2. Unambiguous — avoid vague language such as “fast”, “user-friendly”, or “appropriate” without
definition.
# 3. Verifiable — every requirement must be testable or explicitly marked as awaiting a measurable
criterion.
# 4. Traceable — linked to a source or clearly identified as derived.
# 5. Consistent — must not contradict another requirement.
# 6. Feasible — must not assume unavailable technology or resources.
# 7. Necessary — avoid requirements unrelated to the project scope.
Use a table with the following columns where appropriate: Verification
ID                 Requirement      Priority            Source/Status   Rationale          Method
# 6. MANDATORY TECHNICAL PRINCIPLES
The following principles must be preserved throughout the SRS:
# 1. Hybrid, Contract-First architecture.
# 2. LLM/NLU output is untrusted.
# 3. Raw LLM JSON must never directly trigger privileged writes.
# 4. User identity and authorization must come from trusted backend context.
# 5. Entity IDs must be resolved and validated against actual data.
# 6. Missing information must not be fabricated.
# 7. Ambiguous date/time expressions must be clarified.
# 8. Business rules and scheduler constraints must be deterministic.
# 9. Read, Draft, Proposal, and Commit must be distinguished.
# 10. READY does not mean approved.
# 11. PROPOSED does not mean CONFIRMED.
# 12. A confirmed schedule must not be silently changed.
# 13. Important schedule changes must follow:
Proposal -> User Approval -> Revalidation -> Commit
# 14. Approval must be bound to the correct user, proposal, version, and validity period.
# 15. Commit operations must consider concurrency, idempotency, and consistency.
17

<!-- PDF page 18 -->
# 16. Partial scheduling must explicitly expose unscheduled work.
# 17. The system must not claim that a planned action has been persisted before successful commit.
# 7. DOCUMENT QUALITY REQUIREMENTS
The final SRS must satisfy all the following:
- Professional academic and software engineering writing style.
- Consistent terminology throughout.
- Sufficient technical detail for implementation and testing.
- No repetitive filler content.
- No generic descriptions that do not explain StudyFlow AI.
- Clear separation between confirmed requirements, proposals, assumptions, and TBDs.
- Cross-references between requirements, diagrams, use cases, and test cases.
- Detailed tables for requirements and specifications.
- Mermaid diagrams for architecture, data relationships, state transitions, and critical workflows.
- Realistic Vietnamese user interaction examples.
- Consistent requirement IDs.
- No contradictory API contracts.
- No contradictory entity states.
- No unsupported implementation claims.
The SRS should be comprehensive, but completeness must never be achieved by inventing information. When information is missing, a clearly documented TBD is better than an unsupported specification.
# 8. FINAL OUTPUT — FILE GENERATION
Generate the actual SRS document as a professionally formatted Microsoft Word (.docx) file. Primary output: StudyFlow_AI_Software_Requirements_Specification_SRS_v1.0.docx Also provide a Markdown source file: StudyFlow_AI_Software_Requirements_Specification_SRS_v1.0.md Word document formatting
- A4 paper.
- Professional academic/technical document layout.
- Consistent heading hierarchy.
- Automatic table of contents.
- Numbered sections and subsections.
- Page numbering.
- Header/footer.
- Properly formatted tables.
- Readable typography.
- Consistent spacing and margins.
- Clearly styled requirement IDs and status labels.
- Proper diagram placement and captions.
- Revision history table.
- Glossary and appendices.
18

<!-- PDF page 19 -->
Do not leave placeholder sections empty. If a section cannot be completed using available information, populate it with: 1. What is currently known.
# 2. What is not known. 3. Why the information is needed. 4. Who or what decision would be required to
resolve it, without inventing an owner. Ensure that diagrams render correctly in the final document. Do not leave raw Mermaid syntax in the Word document as a substitute for diagrams. Deliverables Provide: 1. The complete .docx SRS file. 2. The corresponding .md source file. 3. A concise completion report listing: - Sections completed. - Number of functional requirements. - Number of non-functional requirements. - Number of use cases. - Number of test cases. - Number of unresolved decisions. - Any source material that was unavailable. - Any limitations preventing full specification.
# 9. FINAL SELF-REVIEW — REQUIRED BEFORE DELIVERY
Before generating the final files, perform a systematic consistency review. Check:
- Does the SRS accurately represent the actual StudyFlow AI project?
- Is F1 clearly distinguished from F2 and F3?
- Are MVP and Post-MVP boundaries explicit?
- Are all requirements supported by sources or marked as proposals?
- Are unresolved scope decisions documented?
- Are the Orchestrator and F1 Backend responsibilities separated?
- Are LLM trust boundaries correctly defined?
- Are task, study block, and study plan clearly distinguished?
- Are extraction requirements separated from execution requirements?
- Are validation status, workflow state, and entity status distinct?
- Are proposal, approval, and commit separate concepts?
- Are state transitions complete enough to test?
- Are API/tool contracts internally consistent?
- Are date/time rules sufficiently precise?
- Are scheduler invariants preserved?
- Are security and authorization requirements covered?
- Are concurrency, idempotency, and recovery addressed?
- Are functional requirements testable?
- Are non-functional requirements measurable or marked TBD?
- Does every requirement have traceability?
- Are test cases linked to the requirements they verify?
- Are unimplemented capabilities never described as completed?
- Are source limitations explicitly disclosed?
Resolve inconsistencies where the source documents provide sufficient evidence. For unresolved conflicts, create an open issue rather than making an unsupported decision. Do not omit a section simply because the information is incomplete.
# 10. EXECUTION INSTRUCTION
Begin by analyzing both supplied source documents in full. 19

<!-- PDF page 20 -->
Then: 1. Extract the existing requirements and project facts. 2. Build a source/status classification register.
# 3. Identify conflicts, missing information, and unresolved decisions. 4. Establish a consistent requirements
vocabulary. 5. Construct the system-level and F1-level requirements. 6. Build use cases, contracts, data specifications, and workflows. 7. Build the test matrix and traceability matrix. 8. Perform consistency checks. 9. Generate the Word and Markdown files. 10. Deliver the actual downloadable files. Do not stop after presenting an outline or a proposed table of contents. Do not ask unnecessary clarification questions before producing the first complete SRS draft. Make the best possible use of the available materials and clearly mark all unresolved decisions as TBD. The final deliverable must be a complete, structured, technically detailed SRS document for StudyFlow AI — not merely a summary, proposal, architecture overview, or generic requirements template. Lưu ý quan trọng khi sử dụng prompt Tài liệu được thiết kế theo hướng SRS toàn dự án nhưng đặc tả sâu F1, thay vì yêu cầu ChatGPT tự suy diễn chi tiết cả ba feature.
```text
Phạm vi                                                    Mức độ đặc tả yêu cầu
StudyFlow AI tổng thể                                      Chi tiết ở cấp hệ thống
F1 – Intelligent Academic Planner                          Chi tiết đến functional requirements, API contracts,
                                                           data model, workflows, validation và test cases
F2 – Learning Assessment & Adaptive Revision               Mô tả phạm vi, chức năng và kiến trúc ở mức hiện
                                                           có
F3 – Daily AI Learning                                     Mô tả phạm vi, chức năng và kiến trúc ở mức hiện
                                                           có
Các quyết định kỹ thuật chưa chốt                          Ghi TBD hoặc Proposed, không tự quyết định
```
Ba cơ chế nên giữ nguyên trong SRS
# 1. Requirement Traceability Matrix: Truy ngược được mỗi requirement từ nguồn nào, phục vụ use
case nào và được test bằng test case nào.
# 2. Open Issues & TBD Register: Nhóm biết chính xác cần quyết định những gì trước khi code.
# 3. Proposal -> Approval -> Revalidation -> Commit: Đây là ranh giới nghiệp vụ và bảo mật cốt lõi của
F1, không nên chỉ mô tả sơ sài. Lưu ý về nguồn proposal chính thức Tài liệu hiện tại ghi nhận 0-main-20.pdf chưa được đọc trực tiếp. Vì vậy, khi có PDF proposal chính thức, hãy đính kèm nó cùng hai file Markdown trên để ChatGPT đối chiếu và nâng độ tin cậy của SRS. Khuyến nghị phát hành: Tạo SRS ở trạng thái Draft v1.0 trước, chưa gọi là Approved SRS. Sau khi cả nhóm review và chốt các TBD quan trọng, mới phát hành bản baseline để developer triển khai theo. 20
