# Documentation index

This directory contains current product and engineering documentation. The files below are the recommended entry points; implementation notes are supporting records, not competing specifications.

## Authoritative documents

| Area | Source |
|---|---|
| F1 business schema and lifecycle rules | [database/schema_F1.md](database/schema_F1.md) |
| Approved integration contract | [../contracts/README.md](../contracts/README.md) |
| Database baseline | [database/StudyFlow_AI_Database_Design_Baseline_v1.1.md](database/StudyFlow_AI_Database_Design_Baseline_v1.1.md) |
| Software requirements | [srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md](srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md) |
| Architecture decisions | [architecture/decisions/](architecture/decisions/) |

## Implementation guides

| Area | Source |
|---|---|
| Current repository/runtime map | [architecture/StudyFlow_AI_Repo_Structure.md](architecture/StudyFlow_AI_Repo_Structure.md) |
| Local demo environment | [implementation/DEMO_ENVIRONMENT.md](implementation/DEMO_ENVIRONMENT.md) |
| Database implementation | [implementation/WP2_DATABASE.md](implementation/WP2_DATABASE.md) |
| Workflow implementation | [implementation/WP4_WORKFLOW.md](implementation/WP4_WORKFLOW.md) |
| Scheduling rules | [planner/scheduling_rules.md](planner/scheduling_rules.md) |
| Planner evaluation | [planner/evaluation.md](planner/evaluation.md) |
| Frontend conventions | [../frontend/DESIGN.md](../frontend/DESIGN.md) |

Files under `implementation/` document work-package decisions and evidence. If an implementation note conflicts with an authoritative document or executable contract, the authoritative source wins.
