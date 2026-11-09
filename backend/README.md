# StudyFlow AI backend

The first implemented backend component is the pure F1 scheduling engine at
`app/f1/scheduler/`. It has no database, framework, authentication, or LLM
dependency. Application and persistence layers can therefore integrate it
without coupling business rules to infrastructure.

## Run scheduler tests

From the repository root:

```bash
python3 -m unittest discover -s backend/tests -v
```

Run the deterministic fixture evaluation:

```bash
python3 backend/scripts/evaluate_planner.py
```

See [`../docs/planner/scheduling_rules.md`](../docs/planner/scheduling_rules.md)
for the supported rules and integration boundary.
