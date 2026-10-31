# Sequence baseline: a targeted follow-up

The v2 experiment's transition feature measured whether a pair had appeared during training. Once most tool pairs had occurred, it could not distinguish common transitions from unusually concentrated ones. This follow-up adds a frequency-sensitive first-order transition baseline without changing the generator, original features, existing detectors, or recorded v2 results.

## Fixed design and leakage boundaries

The local design was committed as `7a67dcf` before the first fresh test generation. The unchanged plan now lives in [the packaged experiment contract](../agent_anomaly/plans/sequence-v1.json). The baseline implementation and leakage tests were also committed before the first fresh test run. No model, smoothing, threshold rule, review budget or seed was changed after viewing results. Later changes add packaging, reporting and artifact checks.

- Training remains seed 42/day 0, and validation seed 43/day 2: 1,200 sessions each, unfiltered and with contamination. Ground-truth mappings are discarded immediately. No sequence-family examples appear in these partitions.
- The smoothed transition counts are scoped to `(tenant, actor)`, include only within-session pairs, and are frozen before validation/test scoring. There is no sharing across actors or tenants. Existing statistical/ML methods receive the same eight features and training data as v2.
- Validation-only 98th percentiles use `method="higher"`, strict `>` ties and the same cap of floor(0.02 × sessions) per detector. Labels do not determine fitting, thresholds, seeds, session grouping or alignment.
- Fresh sequence: seed **7312026**, day **10**, 1,200 sessions, 54 reordered sequences. Fresh mixed: seed **7312027**, day **12**, 1,200 sessions, 58 anomalies. Fresh sequence with timing drift: seed **7312028**, day **14**, 1,200 sessions, 51 reordered sequences. All begin after the previous v2 test periods. Their event identities, timestamps and hashes are recorded; chronology and session disjointness are checked explicitly.
- All three batches and all four detectors are reported. There is no new preferred detector selection from these test results. This is fresh-instance testing of an already inspected family, **not a blind unseen-family claim**.

## Score definition

For one fitted tenant/actor, let `C(a,b)` be the training transition count, `C(a)` its outgoing total, and `K` the fitted vocabulary size plus one reserved unknown bucket. With fixed add-one smoothing:

```text
P_train(b | a) = (C(a,b) + 1) / (C(a) + K)
P_session(b | a) = c(a,b) / c(a)
score = 2 / transitions * sum_observed c(a,b) * log(P_session(b | a) / P_train(b | a))
```

The score measures conditional transition divergence from the training reference, averaged per transition. It uses empirical frequencies within the session being scored, without learning from any other validation/test session. It is not a malicious-activity probability or a calibrated chi-squared significance test. Longer or more varied sessions have different finite-sample behavior; normalization does not eliminate all length/composition effects.

Unknown tools map to the reserved bucket without growing the model. Unknown actors or sessions shorter than two events reject explicitly; this known-actor experiment does not evaluate cold-start detection. Schema validation and event/session limits apply before model fitting or scoring.

## What the fresh evidence shows

On **fresh_sequence**, Markov finds **15 of 54** anomalies with **9 false alerts**, precision **0.625**, recall **0.278**, and AP **0.515**. The original three detectors each have zero recall at their frozen calibrated thresholds. The paired actor-cluster bootstrap recall improvement is **+0.278**, with a descriptive 95% interval **[+0.145, +0.426]** against each comparator, conditional on these fitted models and alert decisions.

The Markov detector uses 24 alerts, versus 7 for rules, 3 for robust distance, and 4 for Isolation Forest. This workload difference matters. At an equal **24-session ranking budget**, recalls are **0.000**, **0.074**, **0.037**, and **0.278**, respectively. The new method therefore improves this sequence comparison under both reported operating views, while calibrated false alerts rise to **7.50 per 1,000 sessions** versus 5.83, 2.50 and 3.33 for the existing methods. The denominator includes all sessions; this is not a benign-only false-positive rate.

The gain is uneven: Markov recalls **9/21 batch** and **6/17 operator** sequence anomalies, but **0/16 reader** sequence anomalies. It still misses **39/54** positives overall. These blind spots remain in the report.

On **fresh_mixed**, Markov AP is **0.182**, below rules **0.378**, robust distance **0.472** and Isolation Forest **0.345**. Its recall is **0.103**, versus **0.207**, **0.224** and **0.138**. Tool transitions alone do not directly observe denial outcomes or elapsed time. This method remains a specialized sequence baseline, not a general replacement or a tested combined detector.

On **fresh_sequence_drift**, Markov AP is **0.355** and recall **0.235**, with **12 false alerts** among 24 alerts. Existing detectors again have zero calibrated recall. The Markov score ignores timestamps after ordering, so timing changes do not themselves add evidence to it.

## Count-preserving order diagnostic

For each primary-test session, one fixed random permutation changes only the tool order; event IDs, actor/tenant scope, timestamps, outcomes, length and tool multiset remain unchanged. In all 54 original sequence anomalies, the original Markov score exceeds the shuffled score; the median difference is **+1.134**. For original benign sessions the median difference is approximately zero and **49.4%** have a higher original score. This supports order sensitivity, rather than a claim based solely on tool counts. It is one permutation, not a permutation significance test; the shuffled sessions are not relabelled and scored as attack efficacy evidence.

## Reproduce and interpret

From a source checkout with the pinned dependencies installed:

```sh
.venv/bin/python -m agent_anomaly.sequence_experiment --output artifacts/sequence
.venv/bin/python scripts/verify_sequence_results.py artifacts/sequence/results.json --reference evaluation/sequence-v1/results.json
```

The second command validates count, budget, subgroup and metric invariants, then compares the entire result, including thresholds, event/source hashes and paired intervals, to recorded evidence (only the Python version may differ). CI repeats the experiment twice on Python 3.12 and 3.13 and checks both deterministic equality and agreement with this recorded result.

[Calculated report](../evaluation/sequence-v1/report.md) and [machine-readable results](../evaluation/sequence-v1/results.json) contain all comparisons, population/scenario metrics and uncertainty settings. Paired intervals resample tenant/actor clusters, hold decisions fixed, and omit training/calibration uncertainty and reapplication of the batch cap. Original per-session intervals still assume independent sessions. First-order models also cannot distinguish different sequences with identical transition counts. The research remains synthetic, targeted and limited; no real-world efficacy or production promotion is established.

A first cross-platform CI comparison found a one-session roundoff discrepancy in the benign shuffle diagnostic. Differences within relative/absolute tolerance `1e-12` now count as numerical ties (the same tolerance used for artifact comparison); a regression test covers this case. Detection scores used for ranking/calibration, thresholds, all detection metrics and paired recall intervals were verified unchanged. This is a reporting reproducibility correction, not a retuned detector.
