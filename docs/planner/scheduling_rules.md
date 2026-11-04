# Scheduling rules — F1 schema 1.1

This module follows `schema_F1.md` version 1.1. It treats the assignment document as role guidance and the official schema as the contract when wording differs.

## Input boundary

- The engine receives only normalized, timezone-aware, minute-aligned data.
- `now`, timezone, generation scope and the effective full policy are explicit inputs.
- Recurrence has already been expanded to concrete intervals by the application layer.
- Availability intervals may overlap; the engine merges them before allocation.
- Busy intervals and retained study blocks are subtracted from availability.
- Replaceable blocks are not counted as retained work or occupied time.

## Hard constraints

Generated blocks must:

1. be inside the half-open generation scope and a merged availability interval;
2. start no earlier than `now` and the task's `available_from_at`;
3. end no later than the task deadline;
4. avoid busy intervals and every retained/generated block;
5. stay in one local day, while allowing an end exactly at next midnight;
6. obey the effective block length, daily limit and break policy;
7. never make retained plus newly scheduled minutes exceed remaining work.

Future retained blocks are validated too. A retained block that is now outside availability, overlaps busy time, exceeds remaining work, breaks the daily limit, or violates another hard constraint produces a conflict. The engine does not silently move locked or retained blocks.

## Deterministic baseline

Tasks are ordered by:

1. ascending deadline;
2. `HIGH`, `NORMAL`, `LOW` priority;
3. ascending UUID text as a stable tie-breaker.

For each task, the earliest valid slot is used. A block is as long as possible up to `max_block_minutes`, the free slot, daily remaining capacity and task work remaining. A block shorter than `min_block_minutes` is allowed only when `allow_short_final_block=true` and it completes all still-unallocated work for that task.

The engine never mutates `remaining_minutes`. It only reports retained, newly scheduled and unallocated minutes.

## Coverage

- `FULL`: all selected remaining work is covered and at least one new block is generated.
- `PARTIAL`: some work is covered and some remains unallocated.
- `NONE`: no selected work is covered despite remaining demand.
- `NO_CHANGE`: retained blocks already cover the work, there are no selected tasks, or service-level diff is empty.

`PARTIAL` is not proof that no better schedule exists. It only describes this deterministic greedy baseline.

## Replanning

History, active blocks, locked blocks, blocks outside/crossing the scope and blocks for unselected tasks are retained. Only future, unlocked, selected-task blocks fully inside the scope are replaceable. An active selected-task block raises `ACTIVE_BLOCK_REQUIRES_REVIEW`.

When materializing a snapshot, replaceable block IDs are reused per task in stable time order. Same-time pairs are unchanged, changed-time pairs are moved, surplus generated blocks receive backend IDs, and surplus old blocks are removed.

## Non-responsibilities

The module does not read a database, authenticate a user, interpret natural language, create a proposal record, verify approval or commit a StudyPlan. The application/tool/persistence layers own those actions.

