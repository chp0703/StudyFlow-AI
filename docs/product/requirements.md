# StudyFlow AI product requirements

| Field | Value |
|---|---|
| Status | Current product scope |
| Scope | Planner, Assessment & Adaptive Revision, Daily AI Learning |
| Primary actor | Authenticated student |
| Product language | Vietnamese-first web experience |
| Timezone baseline | `Asia/Ho_Chi_Minh` |

## Product goal

StudyFlow AI helps a student plan academic work, assess understanding from authorized materials and complete source-grounded daily learning sessions. The three features share identity, course context, source provenance and approval boundaries, but each feature owns its domain records and cannot silently mutate another feature.

## Feature 1 — Intelligent Academic Planner

The Planner turns confirmed tasks, personalized working time and busy intervals into reviewable study-plan proposals.

Required behavior:

- Capture a task name, exact start time, duration, priority weight, color and optional description.
- Interpret an exact requested start time as a commitment to begin at that time.
- Use Vietnam time consistently at the product boundary.
- Allow users to configure working time independently for each day.
- Accept supported images, documents and calendar inputs as untrusted sources for plan preparation.
- Show extracted task and scheduling information before confirmation.
- Generate deterministic plans that expose conflicts and unscheduled work.
- Show the proposed schedule, warnings and changes before approval.
- Persist a confirmed plan only after explicit user approval.
- Preserve immutable plan history and reject stale approvals.

The implemented Planner schema and scheduler are documented under [features/planner/](../features/planner/).

## Feature 2 — Learning Assessment & Adaptive Revision

Assessment measures understanding using authorized learning materials and returns evidence-based revision recommendations.

Required behavior:

- Retrieve topic-relevant passages with document, page and topic provenance.
- Draft candidate questions and answer keys grounded in retrieved passages.
- Require review or verification before a generated question becomes eligible for automatic grading.
- Grade objective responses deterministically against a verified answer key.
- Store quiz attempts and assessment results separately from generated question drafts.
- Calculate topic error rates only from valid responses.
- Mark topics with no valid responses as insufficient data instead of inferring mastery.
- Produce revision recommendations with evidence and confidence limitations.
- Send recommendations to the Planner only as a proposed workload change requiring student confirmation.

Assessment must never directly rewrite a confirmed study plan.

## Feature 3 — Daily AI Learning

Daily AI Learning provides source-grounded explanations, progressive hints and reviewable session outcomes.

Required behavior:

- Retrieve relevant passages from authorized course materials for the current goal or question.
- Ground explanations and hints in retrieved evidence.
- State clearly when available material does not support an answer.
- Preserve session context for follow-up questions under an explicit retention policy.
- Offer progressive hints without presenting unsupported claims as facts.
- Present a session summary for student review.
- Save a SessionOutcome only after the student confirms the summary.
- Treat a session outcome as an activity record, not proof of mastery.
- Allow an optional Assessment handoff without requiring every learning session to end in a quiz.

Daily Learning must not modify Planner tasks or schedules directly.

## Shared requirements

### Trust and authorization

- User identity and ownership come only from verified server-side authentication.
- User text, files, extracted content and model output are untrusted.
- Every privileged operation uses an allowlisted, validated command.
- Cross-user reads and writes fail closed.
- Secrets, tokens and private source content are never logged or committed.

### Source handling

- Only authorized learning materials may be processed.
- Extracted facts retain source references whenever available.
- Unsupported, unreadable or ambiguous input requires clarification or manual entry.
- File ingestion does not itself authorize persistence or execution.

### Review and approval

- Drafts, extracted data, recommendations and generated plans are visually distinct from confirmed records.
- The UI shows the material information a student needs before confirmation.
- An approval binds to the exact target and version shown to the student.
- A stale target requires a refreshed review.

### Cross-feature integration

```text
Planner block/topic context
        |
        v
Daily Learning session ---- optional ----> Assessment
        |                                      |
        v                                      v
confirmed SessionOutcome              RevisionRecommendation
                                               |
                                               v
                                  Planner workload proposal
                                               |
                                      student confirmation
```

Cross-feature handoffs use typed records and preserve provenance. No recommendation, assessment or session result can bypass Planner validation and approval.

## Delivery status

| Feature | Scope status | Implementation status |
|---|---|---|
| Intelligent Academic Planner | Current | Existing frontend, backend, contract, database and scheduler foundation |
| Learning Assessment & Adaptive Revision | Current | Requirements defined; implementation pending |
| Daily AI Learning | Current | Requirements defined; implementation pending |

The legacy technical identifiers `F1`, `schema_version="1.1"`, `/v1` and `f1.schema.json` remain compatibility identifiers for the current Planner implementation. They do not define the product-wide feature scope.
