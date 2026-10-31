# Population-aware calibration: one shared queue

Training-derived tool-use strata and same-tenant validation references; no ground-truth population is used by the detector. All candidates compete for one 2% global cap. This is a targeted synthetic follow-up.

| Fresh batch | Detector | AP | TP | FP | Recall | Alerts | Reader-sequence detected / total | Equal-budget reader detected |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fresh_population_joint | rules | 0.160 | 4 | 9 | 0.077 | 13 | 0 / 13 | 0 |
| fresh_population_joint | robust_distance | 0.196 | 6 | 7 | 0.115 | 13 | 0 / 13 | 0 |
| fresh_population_joint | isolation_forest | 0.157 | 5 | 8 | 0.096 | 13 | 0 / 13 | 0 |
| fresh_population_joint | markov_deviance | 0.329 | 14 | 10 | 0.269 | 24 | 0 / 13 | 0 |
| fresh_population_joint | rules_plus_sequence | 0.371 | 8 | 7 | 0.154 | 15 | 0 / 13 | 0 |
| fresh_population_joint | population_rules_plus_sequence | 0.380 | 7 | 7 | 0.135 | 14 | 0 / 13 | 0 |
| fresh_population_sequence | rules | 0.058 | 0 | 3 | 0.000 | 3 | 0 / 13 | 0 |
| fresh_population_sequence | robust_distance | 0.063 | 1 | 2 | 0.016 | 3 | 0 / 13 | 0 |
| fresh_population_sequence | isolation_forest | 0.059 | 1 | 6 | 0.016 | 7 | 0 / 13 | 0 |
| fresh_population_sequence | markov_deviance | 0.677 | 19 | 5 | 0.302 | 24 | 0 / 13 | 0 |
| fresh_population_sequence | rules_plus_sequence | 0.642 | 12 | 4 | 0.190 | 16 | 0 / 13 | 0 |
| fresh_population_sequence | population_rules_plus_sequence | 0.659 | 10 | 2 | 0.159 | 12 | 0 / 13 | 0 |
| fresh_population_nonsequence | rules | 0.398 | 12 | 2 | 0.185 | 14 | 0 / 0 | 0 |
| fresh_population_nonsequence | robust_distance | 0.391 | 9 | 2 | 0.138 | 11 | 0 / 0 | 0 |
| fresh_population_nonsequence | isolation_forest | 0.269 | 6 | 14 | 0.092 | 20 | 0 / 0 | 0 |
| fresh_population_nonsequence | markov_deviance | 0.217 | 9 | 15 | 0.138 | 24 | 0 / 0 | 0 |
| fresh_population_nonsequence | rules_plus_sequence | 0.447 | 18 | 5 | 0.277 | 23 | 0 / 0 | 0 |
| fresh_population_nonsequence | population_rules_plus_sequence | 0.445 | 17 | 3 | 0.262 | 20 | 0 / 0 | 0 |

## Queues, reader misses and displacement

### fresh_population_joint

Shared cap 24; candidates 14; alerts 14; cap-suppressed 0; fallback sessions 0.

| Tenant / training-derived group | Sessions | Positives | Candidates | Alerts | TP | FP | Misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| synthetic-0/export_heavy | 192 | 6 | 5 | 5 | 2 | 3 | 4 |
| synthetic-0/other | 184 | 6 | 5 | 5 | 2 | 3 | 4 |
| synthetic-0/read_dominant | 224 | 10 | 2 | 2 | 2 | 0 | 8 |
| synthetic-1/export_heavy | 211 | 12 | 2 | 2 | 1 | 1 | 11 |
| synthetic-1/other | 200 | 7 | 0 | 0 | 0 | 0 | 7 |
| synthetic-1/read_dominant | 189 | 11 | 0 | 0 | 0 | 0 | 11 |

Exactly-full-budget results ignore thresholds and use one global top-24 ranking:

| Detector | TP | FP | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 6 | 18 | 0 | 13 |
| markov_deviance | 14 | 10 | 0 | 13 |
| rules_plus_sequence | 15 | 9 | 0 | 13 |
| population_rules_plus_sequence | 14 | 10 | 0 | 13 |

- calibrated versus rules_plus_sequence: gain 2 true / 3 false; lose 3 true / 3 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules_plus_sequence: gain 1 true / 3 false; lose 2 true / 2 false. Reader-sequence gains/losses 0/0.
- calibrated versus rules: gain 4 true / 1 false; lose 1 true / 3 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules: gain 9 true / 1 false; lose 1 true / 9 false. Reader-sequence gains/losses 0/0.
- calibrated versus markov_deviance: gain 3 true / 5 false; lose 10 true / 8 false. Reader-sequence gains/losses 0/0.
- full_budget versus markov_deviance: gain 4 true / 6 false; lose 4 true / 6 false. Reader-sequence gains/losses 0/0.
- Population minus global_combined recall: -0.019; paired actor-cluster 95% interval [-0.12263694951664876, 0.08085714285714282].
- Population minus rules recall: +0.058; paired actor-cluster 95% interval [-0.02002801120448179, 0.1467298497267759].
- Population minus robust_distance recall: +0.019; paired actor-cluster 95% interval [-0.09466681574239713, 0.13400641025641022].
- Population minus isolation_forest recall: +0.038; paired actor-cluster 95% interval [-0.09201902748414376, 0.15384615384615385].
- Population minus markov_deviance recall: -0.135; paired actor-cluster 95% interval [-0.2982456140350877, 0.023295454545454522].

- Reader-sequence p1-22-20: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 0.875, calibrated score 0.462, global rank 417.
- Reader-sequence p1-22-30: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.509, calibrated score 0.796, global rank 48.
- Reader-sequence p1-22-43: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.312, calibrated score 0.449, global rank 452.
- Reader-sequence p1-22-150: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.168, calibrated score 0.616, global rank 158.
- Reader-sequence p1-22-157: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.544, calibrated score 0.528, global rank 281.

### fresh_population_sequence

Shared cap 24; candidates 12; alerts 12; cap-suppressed 0; fallback sessions 0.

| Tenant / training-derived group | Sessions | Positives | Candidates | Alerts | TP | FP | Misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| synthetic-0/export_heavy | 183 | 11 | 3 | 3 | 3 | 0 | 8 |
| synthetic-0/other | 215 | 12 | 2 | 2 | 2 | 0 | 10 |
| synthetic-0/read_dominant | 202 | 8 | 0 | 0 | 0 | 0 | 8 |
| synthetic-1/export_heavy | 217 | 11 | 5 | 5 | 4 | 1 | 7 |
| synthetic-1/other | 199 | 16 | 2 | 2 | 1 | 1 | 15 |
| synthetic-1/read_dominant | 184 | 5 | 0 | 0 | 0 | 0 | 5 |

Exactly-full-budget results ignore thresholds and use one global top-24 ranking:

| Detector | TP | FP | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 1 | 23 | 0 | 13 |
| markov_deviance | 19 | 5 | 0 | 13 |
| rules_plus_sequence | 18 | 6 | 0 | 13 |
| population_rules_plus_sequence | 19 | 5 | 0 | 13 |

- calibrated versus rules_plus_sequence: gain 0 true / 0 false; lose 2 true / 2 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules_plus_sequence: gain 4 true / 0 false; lose 3 true / 1 false. Reader-sequence gains/losses 0/0.
- calibrated versus rules: gain 10 true / 2 false; lose 0 true / 3 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules: gain 18 true / 2 false; lose 0 true / 20 false. Reader-sequence gains/losses 0/0.
- calibrated versus markov_deviance: gain 0 true / 0 false; lose 9 true / 3 false. Reader-sequence gains/losses 0/0.
- full_budget versus markov_deviance: gain 3 true / 0 false; lose 3 true / 0 false. Reader-sequence gains/losses 0/0.
- Population minus global_combined recall: -0.032; paired actor-cluster 95% interval [-0.08056756756756757, 0.0].
- Population minus rules recall: +0.159; paired actor-cluster 95% interval [0.06297123015873016, 0.25410949690610707].
- Population minus robust_distance recall: +0.143; paired actor-cluster 95% interval [0.061995192307692314, 0.23728813559322035].
- Population minus isolation_forest recall: +0.143; paired actor-cluster 95% interval [0.061995192307692314, 0.23728813559322035].
- Population minus markov_deviance recall: -0.143; paired actor-cluster 95% interval [-0.23408583603896105, -0.05996398559423775].

- Reader-sequence p0-24-245: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.552, calibrated score 0.531, global rank 306.
- Reader-sequence p0-24-465: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.378, calibrated score 0.471, global rank 426.
- Reader-sequence p0-24-542: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 0.919, calibrated score 0.485, global rank 402.
- Reader-sequence p0-24-646: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 1.293, calibrated score 0.682, global rank 129.
- Reader-sequence p0-24-807: missed, below_group_calibrated_threshold; group read_dominant, raw sequence score 0.709, calibrated score 0.243, global rank 940.

### fresh_population_nonsequence

Shared cap 24; candidates 20; alerts 20; cap-suppressed 0; fallback sessions 0.

| Tenant / training-derived group | Sessions | Positives | Candidates | Alerts | TP | FP | Misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| synthetic-0/export_heavy | 188 | 11 | 2 | 2 | 1 | 1 | 10 |
| synthetic-0/other | 211 | 16 | 5 | 5 | 4 | 1 | 12 |
| synthetic-0/read_dominant | 201 | 14 | 5 | 5 | 5 | 0 | 9 |
| synthetic-1/export_heavy | 197 | 8 | 4 | 4 | 3 | 1 | 5 |
| synthetic-1/other | 207 | 10 | 1 | 1 | 1 | 0 | 9 |
| synthetic-1/read_dominant | 196 | 6 | 3 | 3 | 3 | 0 | 3 |

Exactly-full-budget results ignore thresholds and use one global top-24 ranking:

| Detector | TP | FP | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 13 | 11 | 0 | 0 |
| markov_deviance | 9 | 15 | 0 | 0 |
| rules_plus_sequence | 19 | 5 | 0 | 0 |
| population_rules_plus_sequence | 18 | 6 | 0 | 0 |

- calibrated versus rules_plus_sequence: gain 0 true / 0 false; lose 1 true / 2 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules_plus_sequence: gain 0 true / 1 false; lose 1 true / 0 false. Reader-sequence gains/losses 0/0.
- calibrated versus rules: gain 7 true / 1 false; lose 2 true / 0 false. Reader-sequence gains/losses 0/0.
- full_budget versus rules: gain 8 true / 4 false; lose 3 true / 9 false. Reader-sequence gains/losses 0/0.
- calibrated versus markov_deviance: gain 10 true / 0 false; lose 2 true / 12 false. Reader-sequence gains/losses 0/0.
- full_budget versus markov_deviance: gain 10 true / 1 false; lose 1 true / 10 false. Reader-sequence gains/losses 0/0.
- Population minus global_combined recall: -0.015; paired actor-cluster 95% interval [-0.04802227342549923, 0.0].
- Population minus rules recall: +0.077; paired actor-cluster 95% interval [-0.013901215512251592, 0.17608166922683044].
- Population minus robust_distance recall: +0.123; paired actor-cluster 95% interval [0.015625, 0.22882051282051272].
- Population minus isolation_forest recall: +0.169; paired actor-cluster 95% interval [0.07692307692307693, 0.27480715287517526].
- Population minus markov_deviance recall: +0.123; paired actor-cluster 95% interval [0.030997596153846157, 0.22786617262423706].


## Limits and leakage boundaries

- Targeted fresh instances of inspected synthetic families, not blind family validation.
- Training-derived behavioral strata are proxies, not authenticated roles or ground-truth populations.
- Calibration reuses unlabelled validation for component scaling and within-group thresholds; no guaranteed false-positive rate or fairness guarantee.
- Small per-group tails and contaminated validation can produce unstable thresholds and persistent reader misses.
- A single queue can displace other populations; there are no per-group quotas.
- Profiles are frozen and can become stale after role or policy changes; unknown actors reject, and sparse groups use recorded same-tenant fallback.
- Paired intervals hold fitted models and alert decisions fixed; no training/calibration or reranking uncertainty is included.
- Validation and test group assignment is a frozen lookup by tenant/actor into training-only profiles; actor names and evaluation population labels are never parsed.
- Sparse/zero-scale strata use only their own tenant validation pool; unsupported actors/tenants reject explicitly. Fallback mode and support counts are published.
- Group thresholds select candidates; they do not allocate independent alert budgets or reserve review slots for readers.
- Annotated population/scenario labels are used only for evaluation breakdowns after alert decisions. No policy or seed is retuned after results.
- Scores are relative deviations, not attack probabilities. The general reference remains unchanged.
