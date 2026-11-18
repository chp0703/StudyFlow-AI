# Planner evaluation

This directory keeps the evaluation protocol, human-review material and machine-readable results together. Standards define what to measure [1][2]; metric IDs and acceptance thresholds are StudyFlow project decisions. ISO/IEC 25023:2016 predates the 2023 quality model, so the mapping below is by intent, not by clause number. AI-risk practice follows the NIST AI RMF [3] and its Generative AI Profile [4].

## Metrics

| ID | Metric | Current criterion |
|---|---|---|
| NLU-D01 | Development Case Pass Rate: intent order and listed assertions pass | Worst of 5 runs >= 95% |
| NLU-H01 | Candidate-set Semantic Frame Exact Match [5]: complete intent order and behavioral slots match | Worst point estimate of 5 runs >= 95%; always report Wilson 95% interval [7] |
| NLU-H02 | Intent Macro-F1 and sequence accuracy | Observational until the first approved held-out baseline |
| NLU-H03 | Slot Precision, Recall and Micro-F1 | Observational until the first approved held-out baseline |
| SCH-C01 | Hard-constraint violations | 0 |
| SCH-C02 | Determinism for identical input | 100% |
| SCH-Q01 | Coverage optimality gap of the greedy EDF baseline [6] against CP-SAT [11] on the declared subset | Observational |
| SCH-Q02 | Priority-score gap when greedy and CP-SAT complete the same task count | Observational |
| PERF-01 | Scheduler p50/p95/p99 nearest-rank latency [8] (Hyndman–Fan Type 1) after warm-up | Observational; no production SLO yet [10] |

Mapping of metrics to quality characteristics and AI-risk functions (by intent; verify characteristic names against the standard before citing clause numbers):

| Metrics | ISO/IEC 25010:2023 characteristic [1] | NIST AI RMF function [3] |
|---|---|---|
| NLU-D01, NLU-H01–H03 | Functional suitability | Measure |
| SCH-C01, SCH-Q01, SCH-Q02 | Functional suitability | Measure |
| SCH-C02 | Reliability | Measure |
| PERF-01 | Performance efficiency | Measure |
| Usability protocol (SUS) [9] | Interaction capability | Measure |
| Authorization and approval-boundary tests (outside this directory) | Security | Manage |

The 40-case development set (`nlu_eval_vi.json`) uses partial assertions and must not be called exact match; development set 2 (`nlu_dev2_vi.json`) is scored in exact mode, so its case pass rate equals its frame exact match. The candidate set is strict after documented equivalences: missing SEARCH_TASKS `query`/`status_filter` equals `null`/`[]`, and optional display-only `window.label` is ignored. Other extra slots are false positives. `raw_expressions` is excluded from semantic scoring; model output must still pass the contract. A 95/100 point estimate has a Wilson lower bound near 88.8%, so it must not be described as proof that population accuracy is at least 95%.

## Reproduction

```powershell
python -m pip install -r backend/requirements-evaluation.txt
python -B backend/scripts/benchmark_f1.py --repetitions 1000 --warmups 10 --output docs/features/planner/evaluation/results/offline.json
python -B backend/scripts/benchmark_scheduler_quality.py --cases 100 --seed 20261116 --time-limit 300 --output docs/features/planner/evaluation/results/scheduler-quality.json

# After human approval and loading .env into the current process without printing it:
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_eval_vi.json --output docs/features/planner/evaluation/results/nlu-development.json
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_dev2_vi.json --output docs/features/planner/evaluation/results/nlu-dev2.json
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_heldout_vi.json --output docs/features/planner/evaluation/results/nlu-heldout.json
python -B backend/scripts/benchmark_f1.py --nlu-only --nlu-runs 5 --nlu-dataset backend/tests/fixtures/nlu_heldout2_vi.json --output docs/features/planner/evaluation/results/nlu-heldout2.json
```

Live evaluation of a held-out set is run only after its labels are approved and frozen by SHA-256, and only once. Never store API keys or request headers in artifacts. Each result file keeps per-case `outcomes`; reading them for a held-out set turns it into development data. Both held-out sets mirror some prompt rules and have one approver or author, so their generalization limits must remain explicit.

## Interpretation limits

- The 40-case development set (`nlu_eval_vi.json`) and the 63-case development set 2 (`nlu_dev2_vi.json`) were used while editing the prompt and are not held out.
- Held-out set 1 (`nlu_heldout_vi.json`) was run once and failed; its per-case outcomes were deliberately not inspected. It stays a baseline and must not be used to claim quality after the prompt changed.
- Held-out set 2 (`nlu_heldout2_vi.json`) was written by one author after the prompt rules were known and was run once; it has no recorded human approval. Two labels (US02, US05) are arguably ambiguous, and its outcomes were read, so it is now development data.
- With one author or approver, inter-annotator agreement is unavailable.
- A claim of ≥95% accuracy needs a new set written by someone who has not seen the prompt, about 200 cases, run once: 197/200 gives a Wilson lower bound near 95.7%, while 95/100 gives about 88.8%.
- `change_type` coverage is ADD-only because edit/delete window intents are outside the current contract.
- CP-SAT proves an optimum only for 60-minute tasks on a 5-minute grid without retained or exact-start blocks.
- Local latency does not represent concurrent production traffic.
- Usability results remain empty until real participants complete the protocol.

## Results

Offline scheduler evidence was generated from clean commits. NLU live results are in the section below and in `results/nlu-*.json`.

| Scheduler workload | Scheduled ratio | Mean | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| 10 tasks / 3 days | 1.00 | 2.681 ms | 2.428 ms | 3.877 ms | 6.801 ms |
| 50 tasks / 7 days | 0.56 | 37.726 ms | 35.247 ms | 52.350 ms | 61.399 ms |
| 200 tasks / 14 days | 0.28 | 501.009 ms | 368.405 ms | 889.539 ms | 961.711 ms |

The 50/200-task workloads intentionally exceed available capacity. The 200-task local distribution is wide; no cause or production SLO is inferred from it. `results/offline.json` records commit `bbcd1d5`, `git_dirty=false`, 1,000 samples per workload and sample hashes.

CP-SAT proved `OPTIMAL` for all 100 subset workloads at clean commit `eb9362b`. Greedy matched the maximum completed-task count (`coverage gap = 0`) but had a mean priority-score gap of 7.96% and a worst gap of 60%. This is evidence about the declared restricted subset, not global scheduler optimality. Full per-seed statuses and solver metadata are in `results/scheduler-quality.json`.

### NLU (live, DeepSeek `deepseek-flash`, 5 runs each)

| Set | Cases | Worst run | Mean | NLU criterion (worst ≥95%) |
|---|---:|---:|---:|---|
| Development 1 (`nlu_eval_vi.json`) | 40 | 100% | 100% | met |
| Development 2 (`nlu_dev2_vi.json`) | 63 | 96.8% | 98.7% | met |
| Held-out 1 (`nlu_heldout_vi.json`) | 100 | 70% | 71.4% | **not met** |
| Held-out 2 (`nlu_heldout2_vi.json`) | 100 | 93% | 95% | **not met** |

- Held-out 1 (SHA-256 `86c84628df2c9c8ed5d65153f63b6932b6f3068f13117d020ce9a6eb6f7a9d93`, approved by `phkhoiit-1508` on `2026-11-16`) ran against the original prompt. Intent order was 97–100% correct; the failures were in slots.
- Between the two held-out runs the prompt gained explicit period conventions (exclusive `end_at`, whole day/week for GET, GENERATE never starts in the past), mandatory `deadline_timezone`/`view`/`valid_from`, verbatim title/query text and UNSUPPORTED rules. Development 2 rose from 50.8% to 96.8% worst-run after these changes.
- Held-out 2 (SHA-256 `e30b0582667aa7f7e2b09098524d2974abe66e5967d5b8bb21d9245578ece7ed`, no recorded approval) ran before the server began defaulting `valid_from` and `view` and before the "plain confirmation is UNKNOWN" prompt fix. Its failures were arguably ambiguous labels (US02, US05), weekday phrases read as recurring (AV05, AV10), a rule conflict (UK08) and isolated slot or format errors.
- The development 1 and 2 numbers above were produced after those later changes. All four live NLU result files record `git_dirty=true` (commit `accc99b`), so the live NLU numbers cannot be reproduced from a clean commit. The offline scheduler results (`bbcd1d5`) and the scheduler-quality results (`eb9362b`) were generated from clean commits.
- Wilson 95% intervals for the single-run frame exact match are stored per run in each result file.

## References

1. ISO/IEC 25010:2023, *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*, 2nd ed., ISO/IEC, 2023.
2. ISO/IEC 25023:2016, *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Measurement of system and software product quality*, 1st ed., ISO/IEC, 2016.
3. Tabassi, E. (2023), *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, NIST. https://doi.org/10.6028/NIST.AI.100-1
4. Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall, P. & Roberts, K. (2024), *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile*, NIST AI 600-1, NIST. https://doi.org/10.6028/NIST.AI.600-1
5. Goo, C.-W., Gao, G., Hsu, Y.-K., Huo, C.-L., Chen, T.-C., Hsu, K.-W. & Chen, Y.-N. (2018), “Slot-Gated Modeling for Joint Slot Filling and Intent Prediction,” in *Proc. NAACL-HLT 2018, Vol. 2 (Short Papers)*, pp. 753–757. https://doi.org/10.18653/v1/N18-2118
6. Pinedo, M. L. (2016), *Scheduling: Theory, Algorithms, and Systems*, 5th ed., Springer. https://doi.org/10.1007/978-3-319-26580-3
7. Wilson, E. B. (1927), “Probable Inference, the Law of Succession, and Statistical Inference,” *Journal of the American Statistical Association*, 22(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953
8. Hyndman, R. J. & Fan, Y. (1996), “Sample Quantiles in Statistical Packages,” *The American Statistician*, 50(4), 361–365. https://doi.org/10.1080/00031305.1996.10473566
9. Brooke, J. (1996), “SUS: A ‘quick and dirty’ usability scale,” in Jordan, P. W., Thomas, B., Weerdmeester, B. A. & McClelland, I. L. (eds.), *Usability Evaluation in Industry*, Taylor & Francis, London, pp. 189–194.
10. Jones, C., Wilkes, J. & Murphy, N., with Smith, C. (2016), “Service Level Objectives,” ch. 4 in Beyer, B., Jones, C., Petoff, J. & Murphy, N. R. (eds.), *Site Reliability Engineering: How Google Runs Production Systems*, O’Reilly Media. https://sre.google/sre-book/service-level-objectives/
11. Perron, L. & Didier, F., *OR-Tools CP-SAT* v9.14, Google. https://developers.google.com/optimization/cp/cp_solver (version as pinned in `backend/requirements-evaluation.txt`).
