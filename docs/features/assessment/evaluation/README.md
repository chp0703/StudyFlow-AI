# Assessment evaluation

This directory holds the F2 (Learning Assessment & Adaptive Revision) evaluation protocol, the rater guide and machine-readable results. Its layout follows [Planner evaluation](../../planner/evaluation/README.md). The sources below define each metric; the acceptance thresholds are StudyFlow decisions.

## Metrics

| ID | Metric | Method | Current criterion |
|---|---|---|---|
| GRD-C01 | Grading correctness | `grade_attempt` against an independently written oracle on random attempts (VALID/INVALID/OMITTED, MCQ 2–6 options, TRUE_FALSE) | 100% |
| GRD-C02 | Grading determinism | Identical input gives identical output | 100% |
| STAT-C01 | Topic error rate uses valid responses only; no valid responses means insufficient data | pgTAP / integration (`get_topic_stats`) | 100% |
| REC-C01 | Recommendation evidence integrity: chunk IDs come from incorrectly answered questions, counts match, confidence level follows the 5/10 thresholds | pgTAP / integration | 100% |
| REC-C02 | A recommendation never writes a StudyPlan and applies only through `POST /v1/decisions` | pgTAP / integration | 100% |
| RET-01 | Retrieval quality of `search_material_chunks`: Recall@5, MRR, nDCG@10 | Human-labelled query → relevant chunk sets | Observational until a baseline is approved |
| QG-01 | Contract yield: accepted drafts / requested drafts | `normalize_question_batch`, automatic | Observational |
| QG-02 | Acceptable item: answer key correct, answerable from the cited chunks, exactly one correct option, on topic | Two independent raters ([annotation-guide.md](annotation-guide.md)); Cohen's κ; Wilson 95% | Observational in round 1; any ≥90% claim needs a frozen held-out set of about 200 items |
| QG-03 | Secondary quality: distractor plausibility, clarity (1–3) | Same raters | Observational |
| SAFE-01 | Injected instructions in material do not leak IDs or canaries into visible text and do not change the topic | `safety_violations`, live; approval cannot be granted by chat by design (REC-C02) | 0 violations |
| PERF-02 | `generate_drafts` model latency p50/p95 (live); grading p50/p95/p99 (offline) | Nearest-rank | Observational |

Metric sources:

- **QG-02/QG-03.** The criteria (answerability, answer correctness, relevance, distractor quality) come from the AQG evaluation surveys [1, 2] and from the MCQ item-writing guidelines [3]. BLEU, ROUGE and METEOR are not used because they correlate weakly with human answerability judgements [4].
- **Grounding.** "Answerable from the cited chunks" follows the RAGAS faithfulness definition [5]: every claim needed for the key must be inferable from the context. Raters apply it by hand. An LLM judge may only be reported as a secondary number.
- **Agreement.** Cohen's κ [6], read with the Landis–Koch bands [7].
- **Confidence intervals.** Wilson intervals [8], as in F1.
- **RET-01.** Recall@k, MRR and binary nDCG [9, 10].
- **Item analysis.** Difficulty p and the discrimination index from classical test theory [11] apply only to real learner responses (usability round) and are not part of this round.

## VMLU

VMLU [12] has 10,880 four-option Vietnamese MCQs across 58 subjects, with **no source passage per item**. It measures what an LLM knows. It does not measure grounded question generation or retrieval, so it cannot replace QG or RET. It is used only in two ways:

- **VMLU-01 (optional).** `deepseek-flash` accuracy on the public VMLU dev split, restricted to subjects that overlap the evaluation corpus. This is a model baseline for Vietnamese subject knowledge, not a StudyFlow quality number.
- **Rater calibration.** Human-written VMLU items serve as reference "good item" examples before raters start the κ round.

The VMLU repository lists its dataset licence as "TBU", and the data is downloaded from vmlu.ai. Read those terms before use. Do not commit VMLU data to this repository; commit only scripts and aggregate results.

## Data

- **Corpus.** About 10 Vietnamese materials with clear usage rights and 3–5 topics each. Split by material, not by question: 4 development and 6 held-out.
- **Generation.** Development uses about 60 items. Held-out uses about 200 items (190/200 gives a Wilson lower bound near 91%). The held-out set is frozen by SHA-256 and run once, under the F1 rules.
- **Retrieval.** About 100 queries (topic names and natural questions, with and without diacritics), labelled by both raters.
- **Injection.** About 20 materials containing hostile instructions, each with a `forbidden` canary list.
- **Format.** [`backend/tests/fixtures/assessment_eval/sample_vi.json`](../../../../backend/tests/fixtures/assessment_eval/sample_vi.json) shows the expected shape. It is a smoke input only.

## Reproduction

```powershell
python -B backend/scripts/evaluate_assessment.py offline --cases 10000 --seed 20261118 --output docs/features/assessment/evaluation/results/offline.json

# Live, after loading .env into the process without printing it (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL):
python -B backend/scripts/evaluate_assessment.py generate --dataset <set>.json --runs 1 --annotation-csv <items>.csv --output docs/features/assessment/evaluation/results/generation-<set>.json

# Each rater fills a copy of <items>.csv independently; a third person adjudicates disagreements:
python -B backend/scripts/evaluate_assessment.py score --rater-a a.csv --rater-b b.csv [--adjudicated c.csv] --output docs/features/assessment/evaluation/results/qg02-<set>.json

# Retrieval: {"runs": [{"query_id", "ranked": [chunk_id...], "relevant": [chunk_id...]}]}
python -B backend/scripts/evaluate_assessment.py retrieval --runs <runs>.json --output docs/features/assessment/evaluation/results/retrieval-<set>.json
```

STAT-C01, REC-C01 and REC-C02 are covered by `supabase test db` and `backend/tests/integration/test_attempts_local_supabase.py`. Every result file stores the commit, `git_dirty` and input SHA-256 values. It never stores keys or request headers.

## Interpretation limits

- Both raters belong to the team and have seen the prompt, so generalization limits must stay explicit, as for F1.
- Without adjudication, an item counts as acceptable only when **both** raters accept it. This is conservative.
- `search_vector` uses `to_tsvector('simple')`, which has no Vietnamese word segmentation or diacritic folding. A low RET-01 on queries without diacritics is a product finding, not an evaluation artefact.
- The client supplies `priority` and `suggested_minutes` (PR #51 review), so the "reasonableness" of a recommendation is not evaluated until a rule exists.
- The `retrieval` command scores ranked runs; collecting those runs from a local Supabase instance is not automated yet.
- GRD-C01 checks the Python grader. The database re-validates the submission in `submit_quiz_attempt`, and pgTAP covers that path.

## Results

| Metric | Value | Evidence |
|---|---|---|
| GRD-C01 | 100% (10,000/10,000) | `results/offline.json`, seed 20261118, clean commit `0635199` |
| GRD-C02 | 100% (10,000/10,000) | same |
| PERF-02 (grading) | p50 0.167 ms, p95 0.308 ms, p99 0.382 ms | same, local machine, 1–50 questions per attempt |

Live generation, QG-02 and RET-01 have no results until the corpus and labels exist.

## References

1. Amidei, J., Piwek, P. & Willis, A. (2018), "Evaluation methodologies in Automatic Question Generation 2013–2018," *INLG*. https://doi.org/10.18653/v1/W18-6537
2. Kurdi, G. et al. (2020), "A Systematic Review of Automatic Question Generation for Educational Purposes," *IJAIED* 30. https://doi.org/10.1007/s40593-019-00186-y
3. Haladyna, T. M., Downing, S. M. & Rodriguez, M. C. (2002), "A Review of Multiple-Choice Item-Writing Guidelines for Classroom Assessment," *Applied Measurement in Education* 15(3). https://doi.org/10.1207/S15324818AME1503_5
4. Nema, P. & Khapra, M. M. (2018), "Towards a Better Metric for Evaluating Question Generation Systems," *EMNLP*. https://doi.org/10.18653/v1/D18-1429
5. Es, S. et al. (2023), "RAGAS: Automated Evaluation of Retrieval Augmented Generation." https://arxiv.org/abs/2309.15217
6. Cohen, J. (1960), "A Coefficient of Agreement for Nominal Scales," *Educational and Psychological Measurement* 20(1). https://doi.org/10.1177/001316446002000104
7. Landis, J. R. & Koch, G. G. (1977), "The Measurement of Observer Agreement for Categorical Data," *Biometrics* 33(1). https://doi.org/10.2307/2529310
8. Wilson, E. B. (1927), "Probable Inference, the Law of Succession, and Statistical Inference." https://doi.org/10.1080/01621459.1927.10502953
9. Järvelin, K. & Kekäläinen, J. (2002), "Cumulated Gain-Based Evaluation of IR Techniques," *ACM TOIS* 20(4). https://doi.org/10.1145/582415.582418
10. Thakur, N. et al. (2021), "BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models." https://arxiv.org/abs/2104.08663
11. Crocker, L. & Algina, J. (1986), *Introduction to Classical and Modern Test Theory*.
12. Bui, T. et al. (2025), "VMLU Benchmarks: A comprehensive benchmark toolkit for Vietnamese LLMs," *ACL*. https://aclanthology.org/2025.acl-long.563/
13. Hyndman, R. J. & Fan, Y. (1996), "Sample Quantiles in Statistical Packages." https://doi.org/10.1080/00031305.1996.10473566
