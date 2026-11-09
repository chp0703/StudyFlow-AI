# Planner evaluation report

Run date: 04/11/2026  
Schema: 1.1  
Algorithm: `greedy-edf-1.1.0`  
Command: `python3 scripts/evaluate_planner.py`

Each fixed case was executed 100 times with the same explicit `now`, timezone, policy and inputs.

| Case | Coverage | Hard violations | Scheduled ratio | Unallocated | Blocks | Deterministic |
|---|---:|---:|---:|---:|---:|---:|
| single_full | FULL | 0 | 1.0000 | 0 min | 2 | yes |
| busy_split | FULL | 0 | 1.0000 | 0 min | 2 | yes |
| partial_capacity | PARTIAL | 0 | 0.3333 | 120 min | 1 | yes |
| retained_work | FULL | 0 | 1.0000 | 0 min | 2 | yes |
| deadline_before_priority | PARTIAL | 0 | 0.5000 | 60 min | 1 | yes |

Observed mean runtime was approximately 0.04–0.07 ms per case on the current local machine. This number is an implementation smoke metric, not an approved performance threshold or cross-environment benchmark.

The partial cases are intentional: they verify that the engine reports exact unallocated work rather than claiming false success. These fixtures do not prove optimality; they verify deterministic baseline behavior and zero hard-constraint violations for the returned schedules.

