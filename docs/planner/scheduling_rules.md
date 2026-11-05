# Scheduling rules — F1 schema 1.1

This module follows `schema_F1.md` version 1.1. It treats the assignment document as role guidance and the official schema as the contract when wording differs.

## Input boundary

- `normalization.py` exposes `normalize_time_windows(windows, *, start_at, end_at) -> tuple[Interval, ...]` to expand contract `TimeWindow` JSON dictionaries (`NONE` and `WEEKLY`) over a finite half-open horizon `[start_at, end_at)`.
  - Output intervals are UTC-aware, clipped to `[start_at, end_at)`, chronologically sorted, and merged across overlapping or adjacent boundaries.
  - Validates the `NONE`/`WEEKLY` union, IANA timezone, `valid_from` inclusive / `valid_until` exclusive bounds, ISO weekday (`1 = Monday` .. `7 = Sunday`), minute alignment, and the single-local-day policy.
  - `WEEKLY` `end_time="24:00"` resolves to `00:00` on the next local day; `start_time` cannot be `24:00`.
  - Invalid, nonexistent (spring-forward gap), or ambiguous (fall-back fold) local times raise `ValueError`; DST folds are never guessed.
  - Archived windows (`archived_at != null`) are ignored before active-kind aggregation and recurrence/DST expansion.
  - Active `AVAILABILITY` and `BUSY` sets must be normalized separately; mixing both active kinds in one call raises `ValueError`.
- The engine receives timezone-aware inputs, explicit `now`, IANA timezone, generation scope, and the effective full policy.
- `now` may carry sub-minute precision (seconds/microseconds) and an IANA timezone with PEP 495 `fold` disambiguation from audit clocks. Upward minute rounding, duration calculation, interval arithmetic, and chronological ordering operate on true UTC instants (`astimezone(timezone.utc)`) rather than naive wall-clock `timedelta` arithmetic, so generated blocks are always minute-aligned, never start before actual UTC `now`, and preserve true elapsed durations across DST transitions while keeping local-day policy in the context's IANA timezone. Business timestamps (`generation_scope`, tasks, intervals, and blocks) must be minute-aligned.
- Availability intervals may overlap; the engine merges them before allocation.
- Busy intervals and future/active retained study blocks (`end_at > now`) are subtracted from availability (with `break_minutes` padding around occupied study blocks).
- Replaceable blocks are not counted as retained work or occupied time.

## Hard constraints

Generated blocks must:

1. have timezone-aware, minute-aligned timestamps with `end_at > start_at` (zero, negative, reversed, naive, or sub-minute intervals are rejected);
2. be inside the half-open generation scope and a merged availability interval;
3. start no earlier than actual `now` and the task's `available_from_at`;
4. end no later than the task deadline;
5. avoid busy intervals and every non-historical retained/generated block;
6. stay in one local day, while allowing an end exactly at next midnight;
7. obey the effective block length, daily limit and break policy;
8. never make retained plus newly scheduled minutes exceed remaining work.

`validate_generated_result` is a self-contained public validator: it validates both the scheduling context (including future retained blocks) and the generated blocks, returning `Issue` records without raising unhandled exceptions on malformed or naive inputs.

Future retained blocks (`end_at > now`) are validated against availability, busy intervals, task window/deadline, remaining work, daily limits, and breaks. Historical retained blocks (`end_at <= now`) are preserved in snapshots for audit history, but are not re-evaluated against current future daily/break policy and do not block new future work. The engine does not silently move locked or retained blocks.

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
- `NO_CHANGE`: retained blocks already cover the work, there are no selected tasks, or the service-level diff is empty while all selected work is covered (`unallocated == 0`). If the materialized diff is empty while unallocated work remains (`PARTIAL`), coverage stays `PARTIAL` and no duplicate proposal payload is created (`proposal_payload = None`).

`PARTIAL` is not proof that no better schedule exists. It only describes this deterministic greedy baseline.

## Replanning

History, active blocks, locked blocks, blocks outside/crossing the scope and blocks for unselected tasks are retained. Only future, unlocked, selected-task blocks fully inside the scope are replaceable. An active selected-task block raises `ACTIVE_BLOCK_REQUIRES_REVIEW`.

When materializing a snapshot, replaceable blocks that exactly match a generated block on `(task_id, start_at, end_at, is_locked=False)` are matched first as `unchanged` to preserve their `block_id`. Remaining unmatched replaceable and generated blocks for the same task are then paired in chronological order as `moved`, surplus generated blocks receive new backend IDs (`added`), and surplus old replaceable blocks are marked `removed`.

## Non-responsibilities

The module does not read a database, authenticate a user, interpret natural language, create a proposal record, verify approval or commit a StudyPlan. The application/tool/persistence layers own those actions.
