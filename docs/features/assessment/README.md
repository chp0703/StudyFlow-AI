# Learning Assessment & Adaptive Revision

This feature owns source-grounded question preparation, verified answer keys, quiz attempts, deterministic assessment results, topic performance and revision recommendations.

## Boundaries

- Generated questions are drafts until reviewed or verified.
- Automatic grading is allowed only against verified answer keys.
- Insufficient evidence is reported explicitly and is not treated as mastery.
- Revision recommendations carry source and assessment evidence.
- Recommendations can propose Planner workload changes but cannot edit a confirmed schedule.

## Specifications and Contracts

- Product requirements: [requirements.md](../../product/requirements.md#feature-2--learning-assessment--adaptive-revision)
- Domain schema, states, invariants, and consumer impact matrix: [schema.md](schema.md)
- Contract extension overview (`1.0.0`): [contracts/ASSESSMENT.md](../../../contracts/ASSESSMENT.md)
- OpenAPI 3.1 specification: [contracts/assessment-openapi.yaml](../../../contracts/assessment-openapi.yaml)
