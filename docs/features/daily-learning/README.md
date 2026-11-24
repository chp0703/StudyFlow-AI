# Daily AI Learning

This feature owns source-grounded learning conversations, progressive hints, session context and student-confirmed session outcomes.

## Boundaries

- Explanations and hints cite authorized source material.
- Unsupported answers state their limitations.
- Session summaries require student review before persistence.
- A SessionOutcome records completed activity and is not proof of mastery.
- A quiz handoff to Assessment is optional.
- The feature cannot modify Planner tasks or schedules directly.

Detailed requirements are maintained in [product requirements](../../product/requirements.md#feature-3--daily-ai-learning). Machine-readable contracts live in `contracts/learning-openapi.yaml`; persistence is in the F3 migrations under `supabase/migrations/`.
