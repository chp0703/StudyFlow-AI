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
| RET-01 | Retrieval quality of `search_material_chunks`: Recall@5, MRR, nDCG@10, empty-result rate, by query kind | Labelled query → anchor phrases, run against local Supabase | Observational until a baseline is approved |
| QG-01 | Contract yield: accepted drafts / requested drafts | `normalize_question_batch`, automatic | Observational |
| QG-02 | Acceptable item: answer key correct, answerable from the cited chunks, exactly one correct option, on topic | Two independent raters ([annotation-guide.md](annotation-guide.md)); Cohen's κ and raw agreement; Wilson 95% | Observational in round 1; a ≥95% claim needs about 200 human-rated items |
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

VMLU [12] has 10,880 four-option Vietnamese MCQs across 58 subjects, with **no source passage per item**. It measures what an LLM knows. It does not measure grounded question generation or retrieval, so it cannot replace QG or RET. It could serve two secondary purposes:

- a `deepseek-flash` accuracy baseline on subjects that overlap the corpus;
- human-written reference items for rater calibration.

**Status: not run.** Neither the VMLU repository nor vmlu.ai states a dataset licence (the README says "TBU", the site only "© 2025 ZaloAI, Jaist"), and the Hugging Face mirror is gated. Ask contact@vmlu.ai for usage terms before running it. Never commit VMLU data; commit only scripts and aggregate results.

## Data

[`backend/tests/fixtures/assessment_eval/corpus_vi.json`](../../../../backend/tests/fixtures/assessment_eval/corpus_vi.json) (SHA-256 `19f9c3a9753263e6828a9d376c675398e453c7be3661c492ac90c7b3a1f51ed0`, frozen at commit `3f010ef` before any held-out run):

- **Materials.** 10 original Vietnamese materials (about 2,250–2,560 characters, 2 server chunks each), one topic each because B2 accepts one topic per upload. Split by material: 4 development (probability, TCP/UDP, Bạch Đằng 938, photosynthesis) and 6 held-out (Newton's laws, chemical bonding, supply and demand, stacks and queues, Vietnam's climate, Truyện Kiều).
- **Retrieval.** 80 queries, 8 per material. Relevance is defined by anchor phrases and resolved to the server's own chunks. Query kinds: keyword (25), natural question of four or more words (45), Vietnamese typed without diacritics (10).
- **Injection.** 6 short materials with hostile instructions (ignore-previous, ID/prompt leak, topic hijack, forced answer key, fake `</system>` role tag, English override), each with a `forbidden` canary list.
- **Generation cases.** Each material is chunked by the server's `prepare_material` and given to `DeepSeekQuestionGenerator` exactly as `generate_drafts` does (topic filter, no query, first 12 chunks). Development: MCQ and TRUE_FALSE with `count=5`. Held-out: MCQ and TRUE_FALSE with `count=10`, the contract maximum. Injection: MCQ with `count=3`.

## Reproduction

```powershell
python -B backend/scripts/evaluate_assessment.py offline --cases 10000 --seed 20261118 --output docs/features/assessment/evaluation/results/offline.json

# Local Supabase running and reset; F1_LOCAL_* and F1_DB_TEST_DSN as for the integration tests:
python -B backend/scripts/evaluate_assessment.py retrieval-local --corpus backend/tests/fixtures/assessment_eval/corpus_vi.json --output docs/features/assessment/evaluation/results/retrieval.json

# Live, after loading .env into the process without printing it (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL):
python -B backend/scripts/evaluate_assessment.py generate --corpus backend/tests/fixtures/assessment_eval/corpus_vi.json --split heldout --count 10 --annotation-csv items-heldout.csv --output docs/features/assessment/evaluation/results/generation-heldout.json
python -B backend/scripts/evaluate_assessment.py judge --items items-heldout.csv --ratings-csv ratings-deepseek.csv --output judge.json

# Raters fill copies of the items CSV independently; an optional third rater adjudicates:
python -B backend/scripts/evaluate_assessment.py score --rater-a a.csv --rater-b b.csv [--adjudicated c.csv] --output docs/features/assessment/evaluation/results/qg02-heldout.json
```

STAT-C01, REC-C01 and REC-C02 are covered by `supabase test db` and `backend/tests/integration/`. Every result file stores the commit, `git_dirty` and input SHA-256 values. It never stores keys or request headers. The generated items and both rating sheets are in `results/annotations/`.

## Results

Run on 2026-11-18. Model `deepseek-flash`, prompt `f2-question-v1`.

| Metric | Result | Evidence |
|---|---|---|
| GRD-C01 | **100%** (10,000/10,000 random attempts match the oracle) | `offline.json`, seed 20261118, clean commit `0635199` |
| GRD-C02 | **100%** | same |
| STAT-C01, REC-C01, REC-C02 | **pass**: 618/618 pgTAP assertions after `supabase db reset` | local stack |
| RET-01, all 80 queries | Recall@5 0.70, MRR 0.69, nDCG@10 0.70 | `retrieval.json`, clean commit `3f010ef` |
| RET-01, keyword (25) | Recall@5 **1.00**, MRR 0.98, 0% empty results | same |
| RET-01, natural question (45) | Recall@5 **0.69**, 31% empty results | same |
| RET-01, no diacritics (10) | Recall@5 **0.00**, 100% empty results | same |
| QG-01, development | 40/40 = 100% (count 5) | `generation-dev.json` |
| QG-01, held-out | **80/120 = 66.7%**: 4 of 6 MCQ requests with count 10 failed completely | `generation-heldout.json` |
| QG-02, held-out | **79/80 = 98.75%** acceptable, Wilson 95% [93.3%, 99.8%] | `qg02-heldout.json` |
| QG-02 agreement | Observed 79/80 (98.75%); Cohen's κ undefined or 0 | same; see limits |
| QG-03 | Clarity and distractor plausibility are in the rating sheets. Every one of the 10 held-out Newton MCQ items has key A. Injection items 13 and 14 are near-duplicates | `annotations/` |
| SAFE-01 | **0/18** violations: no ID, canary or topic leak; the forced-key attack did not force A (keys A, B, A); manual review agrees | `generation-injection.json`, `annotations/items-injection.csv` |
| PERF-02, generation | Development p50 3.9 s, p95 8.7 s; held-out p50 6.5 s, p95 8.2 s; grading p95 0.31 ms | result files |

### Findings for the product

1. **`count=10` MCQ exceeds the token budget.** On a development reproduction, 3 of 4 MCQ requests stopped with `finish_reason=length` at exactly `QUESTION_MAX_TOKENS=2048`. The contract allows `count` up to 10, so the default budget cannot satisfy the contract. Fix: raise the default (the setting allows up to 8192) or derive it from `count`, then rerun the development set.
2. **Searching without diacritics finds nothing.** `to_tsvector('simple')` with `plainto_tsquery` neither folds diacritics nor segments Vietnamese words. Fix: add `unaccent` to both the stored vector and the query.
3. **Natural-language queries often return nothing.** `plainto_tsquery` ANDs every word, so any word missing from the chunk ("là gì", "bao nhiêu") empties the result. Consider `websearch_to_tsquery` with OR fallback, or a ranked OR query.
4. **Generation does not retrieve by query.** `generate_drafts` calls the search with `query=None`, so the model always sees the first 12 chunks of the topic (at most 24,000 characters). Later parts of a long material never produce questions. RET-01 therefore measures the search RPC, not the context the generator uses.
5. **Answer-key position bias.** All 10 held-out Newton MCQ items have key A. Shuffle options server-side after normalization.

## Interpretation limits

- **No human rated anything.** Rater A is the AI assistant that wrote this protocol. Rater B is `deepseek-flash`, the same model that generated the items, so it is likely biased toward its own output. QG-02 is therefore an AI-rated estimate, not human-verified quality. The protocol in [annotation-guide.md](annotation-guide.md) is ready for two human raters.
- **The corpus was written by the same AI that rated it.** It is clean, factual school-level text, much easier than real student uploads (PDF scans, mixed formatting, long chapters). Held-out here means "not used while changing prompts"; it does not mean independent of the evaluator.
- **Kappa paradox.** Both raters accepted almost every item, so expected agreement approaches 1 and κ becomes undefined or 0 even at 98.75% raw agreement [14]. Report raw agreement until the set contains enough rejected items.
- Without adjudication, an item counts as acceptable only when both raters accept it. This is conservative.
- 80 items cannot support a claim of ≥95% acceptability: the Wilson lower bound is 93.3%.
- Each held-out generation ran once. Its `git_dirty=true` flag comes from result files written earlier in the same session, not from code; the code commit is `3f010ef`.
- The client supplies `priority` and `suggested_minutes` (PR #51 review), so recommendation reasonableness is not evaluated.
- GRD-C01 checks the Python grader. The database re-validates submissions in `submit_quiz_attempt`, and pgTAP covers that path.
- Latency was measured from one machine to the public DeepSeek API and does not represent production traffic.

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
14. Feinstein, A. R. & Cicchetti, D. V. (1990), "High agreement but low kappa: I. The problems of two paradoxes," *Journal of Clinical Epidemiology* 43(6). https://doi.org/10.1016/0895-4356(90)90158-L
