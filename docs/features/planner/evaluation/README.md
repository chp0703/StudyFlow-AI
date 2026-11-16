# Planner evaluation

This directory keeps the evaluation protocol, human-review material and machine-readable results together. Standards define what to measure; StudyFlow's acceptance thresholds remain project decisions.

## Metrics

| ID | Metric | Current criterion |
|---|---|---|
| NLU-D01 | Development Case Pass Rate: intent order and listed assertions pass | Worst of 5 runs >= 95% |
| NLU-H01 | Candidate-set Semantic Frame Exact Match: complete intent order and behavioral slots match | Worst point estimate of 5 runs >= 95%; always report Wilson 95% interval |
| NLU-H02 | Intent Macro-F1 and sequence accuracy | Observational until the first approved held-out baseline |
| NLU-H03 | Slot Precision, Recall and Micro-F1 | Observational until the first approved held-out baseline |
| SCH-C01 | Hard-constraint violations | 0 |
| SCH-C02 | Determinism for identical input | 100% |
| SCH-Q01 | Coverage optimality gap against CP-SAT on the declared subset | Observational |
| PERF-01 | Scheduler p50/p95/p99 nearest-rank latency after warm-up | Observational; no production SLO yet |

The development set uses partial assertions and must not be called exact match. The candidate set is strict after documented equivalences: missing SEARCH_TASKS `query`/`status_filter` equals `null`/`[]`, and optional display-only `window.label` is ignored. Other extra slots are false positives. `raw_expressions` is excluded from semantic scoring; model output must still pass the contract. A 95/100 point estimate has a Wilson lower bound near 88.8%, so it must not be described as proof that population accuracy is at least 95%.

## Reproduction

```powershell
python -m pip install -r backend/requirements-evaluation.txt
python -B backend/scripts/benchmark_f1.py --repetitions 1000 --warmups 10 --output docs/features/planner/evaluation/results/offline.json
python -B backend/scripts/benchmark_scheduler_quality.py --cases 100 --seed 20261116 --time-limit 300 --output docs/features/planner/evaluation/results/scheduler-quality.json

# After human approval and loading .env into the current process without printing it:
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_eval_vi.json --output docs/features/planner/evaluation/results/nlu-development.json
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_heldout_vi.json --output docs/features/planner/evaluation/results/nlu-heldout.json
```

Live evaluation is run only after the labels in `nlu_heldout_vi.json` are approved and frozen by SHA-256. Never store API keys or request headers in artifacts. The current set mirrors some prompt rules and has one approver, so even after freezing its generalization limits must remain explicit.

## Interpretation limits

- The 40-case development set was used while editing the prompt and is not held out.
- The 100-case candidate set becomes a one-shot held-out set only after approval. With one approver, inter-annotator agreement is unavailable.
- `change_type` coverage is ADD-only because edit/delete window intents are outside the current contract.
- CP-SAT proves an optimum only for 60-minute tasks on a 5-minute grid without retained or exact-start blocks.
- Local latency does not represent concurrent production traffic.
- Usability results remain empty until real participants complete the protocol.

## Results

Results are intentionally absent until the implementation is committed, the worktree is clean and the benchmarks are rerun. Performance reports must state that the 50/200-task workloads exceed available capacity. A bimodal latency distribution must be reported as such and rerun on an otherwise idle machine; it must not be summarized as an algorithm property without investigation.

## References

1. ISO/IEC 25010:2023, *Systems and software Quality Requirements and Evaluation — Product quality model*.
2. ISO/IEC 25023:2016, *Measurement of system and software product quality*.
3. Tabassi, E. (2023), *NIST AI Risk Management Framework 1.0*. https://doi.org/10.6028/NIST.AI.100-1
4. Autio, C. et al. (2024), *NIST AI 600-1*. https://doi.org/10.6028/NIST.AI.600-1
5. Goo, C.-W. et al. (2018), “Slot-Gated Modeling for Joint Slot Filling and Intent Prediction.” https://doi.org/10.18653/v1/N18-2118
6. Pinedo, M. L. (2016), *Scheduling: Theory, Algorithms, and Systems*. https://doi.org/10.1007/978-3-319-26580-3
7. Wilson, E. B. (1927), “Probable Inference, the Law of Succession, and Statistical Inference.” https://doi.org/10.1080/01621459.1927.10502953
8. Hyndman, R. J. & Fan, Y. (1996), “Sample Quantiles in Statistical Packages.” https://doi.org/10.1080/00031305.1996.10473566
9. Brooke, J. (1996), “SUS: A Quick and Dirty Usability Scale.”
10. Alvidrez, M. et al. (2016), “Service Level Objectives,” *Site Reliability Engineering*.
