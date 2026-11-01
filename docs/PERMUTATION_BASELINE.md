# Count-preserving permutation sequence baseline

## Fixed design

The local plan was committed as `4632b68`, and implementation/leakage tests as `e539312`, before generating the fresh test data. See [the packaged contract](../agent_anomaly/plans/permutation-v1.json). No statistic, draw count, seed, threshold policy, tie priority or review budget was tuned after seeing these results. Subsequent edits add reporting, artifact checks and CI integration.

The baseline compares order against randomized order **within the same tool multiset**. It needs no training fit and uses no actor/population/scenario identity. Training seed 42/day 0 remains available only to fit the existing comparators. Unlabelled validation seed 43/day 2 calibrates the new score's operating threshold. Existing detector implementations and earlier recorded evidence are unchanged.

The primary set is 1,200 sessions from complete independent 600-session streams, seeds **10112601/10112602**, day **28**. One supplies the existing non-sequence behavior families and the other the reordered-tool family. There is no label-based sampling. The sequence-only and non-sequence controls use **10112603/day 30** and **10112604/day 32**, 1,200 sessions each. Neutral stream prefixes prevent event/session ID collisions. Dates and seeds follow all prior evaluations, and chronology/disjointness are checked.

This is targeted follow-up on inspected synthetic ordering failures, not blind attack-family validation. Every comparator is evaluated on the same new instances and common tie policy.

## Count-conditioned statistic and null

For a session with `n` tools, count equal adjacent pairs `R` and each tool's frequency `c(t)`. Uniform random order conditional on the multiset has expected equal-adjacent count `sum c(t)*(c(t)-1)/n`. The two-sided statistic is:

```text
T_observed = abs(n * R - sum_tool c(t) * (c(t) - 1))
```

It flags unusually clustered or unusually alternating tool use. Integer arithmetic makes equality and null-exceedance ties exact. It does not count alphabetical inversions or directly match the generator's sorting operation.

Draw **499 independent permutations** of the canonical tool-code multiset. Only tool assignments to positions change; the source audit records are never edited. Length and all tool counts remain exact. Timestamps define the observed event order, and outcomes, actor names, IDs, payloads and labels do not enter the new statistic or random seed.

The per-multiset RNG seed is SHA-256 of the fixed master seed **20261101** plus sorted `(tool, count)` pairs. The null does not depend on observed order, session identity, processing order or other test sessions. The same bag reuses the same deterministic null in any partition; this is a fixed randomization reference, not learning from other validation/test sessions.

Let `E` be the number of null statistics at least as large as the observed statistic:

```text
score = 499 - E
diagnostic_MC_p = (1 + E) / 500
```

The correction prevents zero p values. Scores range 0–499, and 499 corresponds to the **Monte Carlo floor p=0.002**, not certainty or an attack probability. The integer score saturates; finite resolution is part of the evidence.

The frozen validation 98th percentile is **480**, with strict `score > 480` candidates. That corresponds to diagnostic p below 0.04 in this fixed draw grid; it is a measured unlabelled validation quantile, not a chosen theoretical significance level or guaranteed future false-positive rate.

Scoring rejects sessions below two or above 256 events and batches exceeding 25 million permutation cells. Schema validation, duplicate rejection and standard event bounds run before randomization. Constant-tool sessions supply no order evidence: score 0, p=1. Tests cover this structural limitation.

## One shared queue and common tie treatment

All populations and tool patterns compete for **one global cap of 24 unique sessions per 1,200**. There are no component/population quotas. For this new comparison only, all seven detectors pre-order sessions by a fixed SHA-256 identity priority (seed **9005**), then apply stable descending-score selection. IDs affect only tie priority, never scores or null draws. The priority is public and is not a secure adversarial scheduler.

The shared tie policy is needed because finite null draws can leave many sessions at score 499. Earlier experiments retain their original ordering and artifacts; direct comparisons here use the new common policy on identical fresh data. AP averages score ties; the review policy resolves them explicitly. Exactly-full-budget reviews are reported separately and ignore thresholds.

## Primary fresh result: reader recovery under the cap

The mixed set contains **64 anomalies**:

| Detector | AP | TP | FP | Precision | Recall | Reader sequence detected |
|---|---:|---:|---:|---:|---:|---:|
| Rules | 0.262 | 9 | 4 | 0.692 | 0.141 | 0/12 |
| Markov sequence | 0.258 | 14 | 10 | 0.583 | 0.219 | 0/12 |
| Global fusion | 0.431 | 12 | 5 | 0.706 | 0.188 | 0/12 |
| Population-calibrated fusion | 0.463 | 11 | 4 | 0.733 | 0.172 | 0/12 |
| Conditional permutation | 0.494 | 23 | 1 | 0.958 | 0.359 | **8/12** |

At exactly 24 reviews, permutation still finds **23 true / 1 false**, versus Markov **14/10**, global fusion **16/8**, population fusion **15/9**, and rules **11/13**. The observed gain therefore persists at equal workload.

There are **55 threshold candidates**, but only 24 can be reviewed. **29 sessions tie at the maximum score 499; 24 are selected.** All 12 reader-sequence anomalies are at that ceiling, so four readers are missed because of the shared cap and deterministic tie priority, not because their order lacks a signal at the calibrated threshold. Publishing the 8/12 recovery, rather than the pre-cap candidate count, preserves the workload constraint.

A selected benign session also occupies that maximum-score group. Even p=0.002 conditional randomization evidence is not confirmation of an attack. False alerts per 1,000 total sessions are **0.83** here, versus 8.33 for Markov and 4.17 for global fusion. These are synthetic observed counts, not future-rate guarantees.

The conditional actor-cluster bootstrap recall difference versus Markov is **+0.141 [0.028, 0.247]**. Versus calibrated global fusion it is **+0.172 [0.000, 0.343]**. Intervals hold fitted models, null draws, tie priorities and decisions fixed and omit calibration, Monte Carlo and reranking uncertainty.

## Controls and false-alert tradeoffs

The sequence-only control contains **62 anomalies**, including 18 reader sequences. Permutation finds **23 true / 1 false**, precision 0.958 and recall 0.371, versus Markov **21/3** and global fusion **7/1** under their frozen thresholds. AP is **0.937** versus Markov 0.668. This favorable ranking result depends on the very ordered synthetic anomaly family and exchangeable benign generator.

Reader recovery is **5/18**. All 18 pass the threshold, but 13 are excluded by the shared cap or boundary-score ties. There are **93 candidates**, including **56 at score 499**, for only 24 slots. At full review workload, Markov finds 21 true / 3 false and global fusion 20/4, while permutation remains 23/1. The aggregate recall difference versus Markov has descriptive interval **[-0.144, +0.223]**: this control alone does not establish a precise expected gain. One whole-batch constant-tool session has no ordering evidence; it is not an explanation for the above-threshold reader misses.

The **non-sequence control reverses the benefit**. Among 60 anomalies, permutation finds only **4 true / 20 false**, precision 0.167, recall 0.067 and AP **0.066**. Rules find **14 true / 4 false**, and global fusion 13/4. At exactly 24 reviews, rules find 15/9 and global fusion 16/8 versus permutation 4/20. Permutation generates **16.67 false alerts per 1,000 total sessions**. Conditioning on tool counts deliberately discards composition, while the statistic ignores denial outcomes and elapsed-time changes; any non-sequence detections are incidental order evidence, not verified coverage of those behaviors.

This is a specialized sequence baseline. It is not a tested fusion with rules, and it does not replace the general reference.

## Leakage checks, null assumptions and limits

- No label, scenario, annotated population or actor-name parsing enters the new statistic, null RNG or validation threshold. Labels are read only after all score/alert decisions for evaluation.
- Null permutations preserve exact counts and length. Unit tests verify every generated null row, the integer statistic, corrected p formula, identity/order-independent null draws, and independence from other sessions.
- Thresholds, legacy fitted models and tie policy are fixed before test generation. Label-field perturbation and future-feature changes cannot alter fitted state or calibration. New dates/seeds and disjoint IDs are asserted.
- Reader evidence lists every reader-sequence session, its statistic, null exceedances, p value, score, review rank, selected status and exclusion reason. Group/scenario metrics, gained/lost alerts and boundary ties are calculated from actual decisions.
- The null assumes **exchangeable order conditional on counts**. This fits the benign generator's IID tool draws. Real legitimate workflows often contain runs or intentional alternating sequences, so real false-alert behavior could be substantially worse. No real-workflow validation is supplied.
- One fixed seed and 499 draws establish reproducibility, not Monte Carlo convergence or seed robustness. Saturation and shared-budget priority can exclude real anomalies. No settings were changed to improve those outcomes after seeing the data.
- Counts-only or constant-tool anomalies remain unobservable to a count-conditioned order detector. Unknown identities are allowed by the new statistic itself; existing comparators still require supported known actors for this paired experiment.

## Reproduce

```sh
.venv/bin/python -m agent_anomaly.permutation_experiment --output artifacts/permutation
.venv/bin/python scripts/verify_permutation_results.py artifacts/permutation/results.json --reference evaluation/permutation-v1/results.json
```

[Calculated report](../evaluation/permutation-v1/report.md) and [complete results](../evaluation/permutation-v1/results.json) contain all seven comparators, all controls, scenario/population breakdowns, fixed-model uncertainty, source/event hashes and full reader evidence. CI runs the experiment twice, checks agreement with recorded results on Python 3.12/3.13, and replays prior evidence unchanged. Runtime needs no network after installing pinned dependencies.
