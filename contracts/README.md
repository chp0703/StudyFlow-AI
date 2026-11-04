# StudyFlow AI F1 tool contracts v1.1 — TV2-02

`schemas/validated_command.json` is the structural schema for the ten normalized commands. `schemas/tool_result.json` is the structural result schema. Validate each result against `$defs/result_<operation>` using the operation already selected by the trusted dispatcher; ToolResult itself does not contain an operation. Examples contain positive and negative cases; `valid` is the expected validation result, not part of the command or result.

These schemas are the only hand-maintained type definitions in this patch. No Pydantic model is claimed or generated. A JSON Schema Draft 2020-12 implementation must enable format assertions for UUID, date and RFC 3339 date-time. Unknown command and payload fields are rejected where the specification defines a closed object. `details`, raw expressions and field-source maps are intentionally maps.

## Trust and application checks

Principal, approval and idempotency are server-owned and passed separately from `ValidatedCommand`; command JSON is not proof of authentication or approval. The server must verify conversation ownership and bind a verified `conversation_id` and source message for candidate creation. The precise internal context shape remains open and is not added to the public command.

JSON Schema validates shape, not authorization, ownership, approval, idempotency, transactional behavior, timezone/DST, valid IANA zone, chronological ordering, minute precision, cross-field arithmetic, workload, policy after merge, or the integrity of a proposal and its base. The service must enforce all v1.1 semantic and state rules, including expected versions, review and revalidation. The published transport must cap page size. Do not treat schema validation as permission to execute.

The `generate_study_plan` READ data shape is **provisional**, for internal coordination only: v1.1 requires `coverage` and `task_summaries`; `conflicts`, `warnings` and `current_plan` are proposed additions, not approved public contract. Confirm with TV3 and TV4 before exposing it. The other nine operations do not depend on this decision.

## Tests

With Python and `jsonschema` supporting Draft 2020-12 already available, from the repository root:

```text
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

No dependency installation is included. Tests validate the schema itself and examples by operation. Semantic and service checks are outside this contract-only patch. In particular, test fixtures are structural examples and do not demonstrate a valid schedulable proposal, approval, or a transaction.
