# Held-out annotation review

Review the candidate file `backend/tests/fixtures/nlu_heldout_vi.json` before any live call. It contains 100 cases: 10 for each of nine intents and 10 multi-intent messages. Do not call it held out until approval and SHA-256 freezing are recorded.

For every case, verify:

1. The Vietnamese message is natural and has one defensible interpretation.
2. Intent order matches the order requested by the user.
3. `slots` is complete: no implied production slot is omitted and no unsaid value is invented.
4. Relative dates are resolved from `2026-11-05T10:00:00+07:00` in `Asia/Ho_Chi_Minh`. A week starts Monday and ends at the next Monday's exclusive `00:00`; a weekend is Saturday `00:00` through Monday's exclusive `00:00`. For GENERATE, “today/this week/from now” starts at the current instant; GET ranges show the full named calendar day/week. An inclusive end date becomes exclusive `00:00` on the following day. Empty `{}` means the user did not state a period.
5. Weekly weekdays use Monday=1 through Sunday=7; `valid_from` is `2026-11-05`.
6. Date-only deadlines use the stated date; datetime deadlines preserve the stated local instant. Priority words map to `cao`=1, `vừa`=0.5, `thấp`=0.1.
7. Free text keeps the user's meaning. Case and repeated whitespace are normalized by the scorer.
8. UNKNOWN is used for unclear/confirmation-only text; UNSUPPORTED is used for a clear request outside Planner capabilities.

Scoring normalizes a missing SEARCH_TASKS `query` to `null` and a missing `status_filter` to `[]`. `window.label` is excluded because it is optional display text; all behavior-changing slots remain strict. The current product only supports `change_type=ADD`, so edit/delete requests are represented as UNSUPPORTED rather than silently relabeled.

Approval statement:

> I reviewed all 100 labels against this guide. The dataset may be frozen and used once as a held-out evaluation set. I understand that changing the prompt from its results makes this set development data for future iterations.

Record approver, date and frozen SHA-256 in the live result artifact. Do not place names inside the dataset itself.

## Approval record

- Approver: `phkhoiit-1508`
- Approved: `2026-11-16`
- Frozen SHA-256: `86c84628df2c9c8ed5d65153f63b6932b6f3068f13117d020ce9a6eb6f7a9d93`

This exact dataset is approved for one-shot held-out evaluation. Any label, prompt or scorer change after observing live results requires a new held-out set for subsequent claims.
