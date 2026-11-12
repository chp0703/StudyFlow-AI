# StudyFlow AI documentation

StudyFlow AI is delivered as one product with three connected features:

1. Intelligent Academic Planner
2. Learning Assessment & Adaptive Revision
3. Daily AI Learning

The Planner foundation is the currently implemented module. Assessment and Daily Learning are part of the approved product scope and must be designed and implemented against the shared trust, source and approval boundaries.

## Start here

| Need | Document |
|---|---|
| Product scope and cross-feature requirements | [product/requirements.md](product/requirements.md) |
| Feature boundaries and implementation status | [features/README.md](features/README.md) |
| Current runtime architecture | [architecture/overview.md](architecture/overview.md) |
| Planner domain model | [features/planner/schema.md](features/planner/schema.md) |
| Planner scheduling behavior | [features/planner/scheduling.md](features/planner/scheduling.md) |
| Planner machine-readable contract | [../contracts/README.md](../contracts/README.md) |
| Database implementation | [../supabase/migrations/](../supabase/migrations/) |
| Frontend conventions | [../frontend/DESIGN.md](../frontend/DESIGN.md) |

## Documentation rules

- Product scope lives in `product/requirements.md`.
- Feature-specific behavior lives under `features/<feature>/`.
- Machine-readable contracts and migrations override prose when describing implemented interfaces.
- Test status comes from test source and CI, not committed result snapshots.
- Historical proposals and superseded handoff documents are kept in Git history, not in the current tree.
