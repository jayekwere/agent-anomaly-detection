# Reader-sequence investigation and population-aware calibration

## Diagnosis on previously inspected evidence

The [reproducible investigation](../evaluation/population-v1/investigation.json) uses the old `combined-v1/fresh_joint` set. Its labels are diagnostic annotations only. No fresh held-out set is used to choose groups, cutoffs, seeds or model settings.

The nine historical reader-sequence anomalies have raw sequence scores **0.986–1.767**, with median **1.232**. Reader validation scores have median **0.444** and pooled 98th percentile **1.698**. Operator and batch sequence-anomaly medians are **2.184** and **2.193**. The old global fusion's effective sequence-only cutoff is about **2.354**, above every historical reader anomaly.

The trained median probability of another `case.read` after `case.read` is **0.641** for readers, versus **0.281** for operators and **0.247** for batch actors. This is consistent with a weak first-order signal for sorted reader sequences: repeated reads are already common, and the score is normalized per transition. This is a mechanism supported by the observed reference probabilities and score distributions, not a causal ablation or proof that every missed reader anomaly has the same cause.

The tails also overlap and differ between tenants. Each tenant has 207 reader validation sessions. Their raw sequence q98s are **1.486** and **2.120**. At or above those quantiles, tenant 0 has four benign sessions and one export-burst session; tenant 1 has four export-burst sessions and one benign session. Ground truth reveals this only after calibration. No contaminated session is removed or reweighted: the practical method does not know those labels. These few tail observations can mask sequence changes when reused for local calibration.

## Frozen method and leakage boundaries

The local design was committed as `9f4d047`, and the implementation/tests as `e331682`, before first fresh-test generation. [The packaged plan](../agent_anomaly/plans/population-v1.json) fixes all choices. Later edits add diagnostics, reporting, artifact validation and CI integration; no score, seed or operating parameter was retuned.

Training remains seed 42/day 0; validation remains seed 43/day 2, each with 1,200 unfiltered synthetic sessions. Existing detector implementations, generator and historical artifacts are unchanged.

1. From **training events only**, count tool use for each `(tenant, actor)`. Assign `read_dominant` if the `case.read` proportion is at least 0.5; otherwise `export_heavy` if `evidence.export` is at least 0.25; otherwise `other`.
2. Freeze that actor registry. Validation/test group lookup uses tenant and actor identity only. The detector never parses actor names, consumes annotated population/scenario labels, or recalculates membership from test behavior. These are behavioral proxies, not authenticated roles.
3. Within each **tenant × derived group**, use unlabelled validation component q98s to scale rules and sequence scores; take their maximum; divide by the group's validation combined q98. The final common threshold is strictly **greater than 1**.
4. Require at least 50 validation sessions and positive component scales. Sparse, missing or zero-scale groups use a recorded **same-tenant** pooled validation reference. Unknown actors and tenants without adequate validation support fail explicitly. No cross-tenant fallback exists.
5. Put every candidate into **one global queue capped at 24 unique sessions per 1,200**. There are no group quotas or component budgets. Exactly-full-budget counterfactual ranking also uses one global top 24.

All six actual groups have 181–212 validation sessions; no fallback occurs in these evaluated batches. Fallback behavior is tested separately. Reusing validation for scaling and local thresholds gives neither a future false-positive guarantee nor a fairness guarantee. The frozen profile can become stale after a role or policy change.

The effective sequence-only read-dominant cutoffs become **1.896** for tenant 0 and **2.924** for tenant 1. Population-aware calibration therefore does not uniformly lower reader thresholds: a small, contaminated local tail can make them higher. The exact component scales and combined thresholds are published.

## Fresh held-out design

The primary mixed set combines every session from two independently generated 600-session streams, seeds **9212601/9212602**, on day **22**. One stream supplies the existing non-sequence scenarios and one the existing reordered-sequence scenario, without label-based selection. Neutral namespaces prevent ID collisions. The sequence-only and non-sequence controls use seeds **9212603/9212604**, days **24/26**, with 1,200 sessions each. All periods follow prior experiments; IDs are disjoint and chronology is checked explicitly.

The models, registry and validation references are frozen before any test generation. Fingerprints detect inference-time reference changes. Ground-truth mappings are used only after decisions for evaluation and group breakdowns. This is targeted testing on fresh instances of known synthetic families, not blind family generalization.

## Outcome: no reader recovery

The primary mixed set contains **52 anomalies**, including **13 reader-sequence anomalies**:

| Detector | AP | TP | FP | Recall | Alerts |
|---|---:|---:|---:|---:|---:|
| Rules | 0.160 | 4 | 9 | 0.077 | 13 |
| Sequence | 0.329 | 14 | 10 | 0.269 | 24 |
| Global fusion | 0.371 | 8 | 7 | 0.154 | 15 |
| Population-calibrated fusion | 0.380 | 7 | 7 | 0.135 | 14 |

The population-calibrated method misses **all 13 reader-sequence anomalies**, as does global fusion. At exactly 24 reviews, population calibration finds **14 true / 10 false**, versus global fusion's **15 true / 9 false**, still with zero reader-sequence detections. The small AP increase does not establish an operating-point benefit or solve the target failure.

At the frozen operating point, population calibration gains two true and three false alerts versus global fusion, while losing three true and three false alerts. Its paired actor-cluster recall difference is **-0.019**, with descriptive 95% interval **[-0.123, +0.081]**. At equal workload, it loses two true detections and gains one, with an extra false alert. The queue still has only 14 candidates, so the shared cap suppresses none; reader misses are below-threshold failures, not occupied review slots.

An example, synthetic session `p1-22-30`, has raw sequence score **1.509**, calibrated score **0.796** against threshold **1**, and rank **48** in the global queue. Other published examples rank substantially lower. Filling the permitted top 24 does not recover the missed reader sequences in this sample.

## Controls and tradeoffs

- **Sequence-only control:** 63 anomalies, including 13 reader sequences. Population calibration finds **10 true / 2 false**, versus global fusion **12 true / 4 false**. Precision rises from 0.750 to 0.833 while recall falls from 0.190 to 0.159. At exactly 24 reviews it finds 19 true / 5 false versus 18 / 6 for global fusion. All 13 reader sequences remain missed under both views.
- **Non-sequence control:** 65 anomalies, with no reader-sequence positives. Population calibration finds **17 true / 3 false**, versus global fusion **18 / 5**. Precision improves, recall falls, and AP is 0.445 versus 0.447. At exactly 24 reviews population calibration finds 18 / 6 versus global fusion 19 / 5. Reader-sequence recall is unavailable here, not an evaluated zero-success cohort.
- All three population-calibrated queues remain below the shared cap (14, 12 and 20 alerts); no candidate is suppressed by the cap. The report also exposes alert allocation and misses for every tenant/derived group, plus gains/losses against rules, sequence and global fusion.

The existing general reference remains unchanged. This specific population-calibration policy fails its reader-recovery objective on these fresh sets. Evidence points to score overlap, local tail contamination and first-order feature limitations, rather than a problem solved by reallocating a few review slots. This does not establish that every possible population-aware method would fail.

## Reproduce and verify

```sh
.venv/bin/python -m scripts.investigate_reader_misses --output artifacts/reader-investigation.json
.venv/bin/python -m agent_anomaly.population_experiment --output artifacts/population
.venv/bin/python scripts/verify_population_results.py artifacts/population/results.json --reference evaluation/population-v1/results.json
```

[Calculated report](../evaluation/population-v1/report.md) and [full JSON](../evaluation/population-v1/results.json) contain all six detectors, source/event hashes, group/reference support, fallback accounting, reader misses and ranks, per-population/scenario metrics, workload and paired uncertainty. Paired intervals resample actor clusters with fixed fitted models/decisions; they omit calibration/training uncertainty and reranking. Legacy per-session intervals retain their independence limitation.

Regression tests cover label-field perturbation, name-agnostic profiles, frozen inference, tenant isolation under changed foreign calibration scores, sparse/missing/zero-scale fallbacks, unsupported actors, minimum support, one shared cap, invalid settings and corrupted group/reader accounting. CI repeats and compares artifacts on Python 3.12/3.13, replays earlier experiments without rewriting archived results, and verifies the historical investigation. No cloud account or credentials are required.
