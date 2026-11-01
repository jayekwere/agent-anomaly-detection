# Count-preserving permutation sequence baseline

One global 2% review cap; count-conditioned within-session nulls; fresh instances of inspected synthetic families. Every comparator uses the same hash-priority tie policy in this study. No actor/population/scenario identity is used by the new statistic or its null RNG.

| Fresh batch | Detector | AP | TP | FP | Precision | Recall | Alerts | Reader detected / total | Full-budget reader detected |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fresh_permutation_joint | rules | 0.262 | 9 | 4 | 0.692 | 0.141 | 13 | 0 / 12 | 0 |
| fresh_permutation_joint | robust_distance | 0.296 | 13 | 4 | 0.765 | 0.203 | 17 | 0 / 12 | 0 |
| fresh_permutation_joint | isolation_forest | 0.218 | 9 | 10 | 0.474 | 0.141 | 19 | 0 / 12 | 0 |
| fresh_permutation_joint | markov_deviance | 0.258 | 14 | 10 | 0.583 | 0.219 | 24 | 0 / 12 | 0 |
| fresh_permutation_joint | rules_plus_sequence | 0.431 | 12 | 5 | 0.706 | 0.188 | 17 | 0 / 12 | 0 |
| fresh_permutation_joint | population_rules_plus_sequence | 0.463 | 11 | 4 | 0.733 | 0.172 | 15 | 0 / 12 | 0 |
| fresh_permutation_joint | conditional_permutation | 0.494 | 23 | 1 | 0.958 | 0.359 | 24 | 8 / 12 | 8 |
| fresh_permutation_sequence | rules | 0.052 | 0 | 4 | 0.000 | 0.000 | 4 | 0 / 18 | 0 |
| fresh_permutation_sequence | robust_distance | 0.062 | 0 | 1 | 0.000 | 0.000 | 1 | 0 / 18 | 0 |
| fresh_permutation_sequence | isolation_forest | 0.053 | 0 | 3 | 0.000 | 0.000 | 3 | 0 / 18 | 0 |
| fresh_permutation_sequence | markov_deviance | 0.668 | 21 | 3 | 0.875 | 0.339 | 24 | 0 / 18 | 0 |
| fresh_permutation_sequence | rules_plus_sequence | 0.611 | 7 | 1 | 0.875 | 0.113 | 8 | 0 / 18 | 0 |
| fresh_permutation_sequence | population_rules_plus_sequence | 0.572 | 6 | 2 | 0.750 | 0.097 | 8 | 0 / 18 | 0 |
| fresh_permutation_sequence | conditional_permutation | 0.937 | 23 | 1 | 0.958 | 0.371 | 24 | 5 / 18 | 5 |
| fresh_permutation_nonsequence | rules | 0.408 | 14 | 4 | 0.778 | 0.233 | 18 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | robust_distance | 0.457 | 12 | 5 | 0.706 | 0.200 | 17 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | isolation_forest | 0.311 | 7 | 7 | 0.500 | 0.117 | 14 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | markov_deviance | 0.095 | 4 | 16 | 0.200 | 0.067 | 20 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | rules_plus_sequence | 0.383 | 13 | 4 | 0.765 | 0.217 | 17 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | population_rules_plus_sequence | 0.361 | 14 | 4 | 0.778 | 0.233 | 18 | 0 / 0 | 0 |
| fresh_permutation_nonsequence | conditional_permutation | 0.066 | 4 | 20 | 0.167 | 0.067 | 24 | 0 / 0 | 0 |

## Shared queue, finite draws and reader evidence

### fresh_permutation_joint: 64 positives / 1200 sessions

Cap 24; candidates 55; selected 24; cap-suppressed 31. Score ceiling: 29 sessions. At boundary score 499, 24 of 29 candidate ties are selected.
Constant-tool sessions: 0; constant sampled null statistic: 0.

| Detector | Exactly-full-budget TP | FP | Reader detected | Reader missed |
|---|---:|---:|---:|---:|
| rules | 11 | 13 | 0 | 12 |
| markov_deviance | 14 | 10 | 0 | 12 |
| rules_plus_sequence | 16 | 8 | 0 | 12 |
| population_rules_plus_sequence | 15 | 9 | 0 | 12 |
| conditional_permutation | 23 | 1 | 8 | 4 |

- calibrated versus rules: gain 23 true / 1 false; lose 9 true / 4 false. Reader gains/losses 8/0.
- full_budget versus rules: gain 23 true / 1 false; lose 11 true / 13 false. Reader gains/losses 8/0.
- calibrated versus markov_deviance: gain 13 true / 1 false; lose 4 true / 10 false. Reader gains/losses 8/0.
- full_budget versus markov_deviance: gain 13 true / 1 false; lose 4 true / 10 false. Reader gains/losses 8/0.
- calibrated versus rules_plus_sequence: gain 22 true / 1 false; lose 11 true / 5 false. Reader gains/losses 8/0.
- full_budget versus rules_plus_sequence: gain 18 true / 1 false; lose 11 true / 8 false. Reader gains/losses 8/0.
- calibrated versus population_rules_plus_sequence: gain 23 true / 1 false; lose 11 true / 4 false. Reader gains/losses 8/0.
- full_budget versus population_rules_plus_sequence: gain 19 true / 1 false; lose 11 true / 9 false. Reader gains/losses 8/0.
- Permutation minus global_combined recall: +0.172; fixed-decision actor-cluster 95% interval [0.0, 0.3433258928571428].
- Permutation minus rules recall: +0.219; fixed-decision actor-cluster 95% interval [0.03910714285714287, 0.405670385952076].
- Permutation minus robust_distance recall: +0.156; fixed-decision actor-cluster 95% interval [-0.016289682539682538, 0.32569142125480144].
- Permutation minus isolation_forest recall: +0.219; fixed-decision actor-cluster 95% interval [0.06812746691432552, 0.38085016835016827].
- Permutation minus markov_deviance recall: +0.141; fixed-decision actor-cluster 95% interval [0.02836016096579477, 0.24691358024691357].
- Permutation minus population_rules_plus_sequence recall: +0.188; fixed-decision actor-cluster 95% interval [0.013597222222222222, 0.3610862068965517].

| Reader session | Events | Tools | Statistic | MC p | Score | Rank | Outcome |
|---|---:|---:|---:|---:|---:|---:|---|
| p1-28-500 | 18 | 2 | 142 | 0.002 | 499 | 2 | alert |
| p1-28-414 | 25 | 4 | 287 | 0.002 | 499 | 3 | alert |
| p1-28-595 | 32 | 3 | 408 | 0.002 | 499 | 4 | alert |
| p1-28-76 | 11 | 3 | 40 | 0.002 | 499 | 5 | alert |
| p1-28-32 | 21 | 5 | 190 | 0.002 | 499 | 16 | alert |
| p1-28-356 | 16 | 4 | 100 | 0.002 | 499 | 19 | alert |
| p1-28-150 | 21 | 3 | 166 | 0.002 | 499 | 21 | alert |
| p1-28-592 | 30 | 5 | 452 | 0.002 | 499 | 24 | alert |
| p1-28-332 | 15 | 3 | 88 | 0.002 | 499 | 25 | shared_cap_or_boundary_tie |
| p1-28-554 | 31 | 2 | 337 | 0.002 | 499 | 27 | shared_cap_or_boundary_tie |
| p1-28-461 | 20 | 3 | 194 | 0.002 | 499 | 28 | shared_cap_or_boundary_tie |
| p1-28-235 | 21 | 4 | 155 | 0.002 | 499 | 29 | shared_cap_or_boundary_tie |

### fresh_permutation_sequence: 62 positives / 1200 sessions

Cap 24; candidates 93; selected 24; cap-suppressed 69. Score ceiling: 56 sessions. At boundary score 499, 24 of 56 candidate ties are selected.
Constant-tool sessions: 1; constant sampled null statistic: 1.

| Detector | Exactly-full-budget TP | FP | Reader detected | Reader missed |
|---|---:|---:|---:|---:|
| rules | 1 | 23 | 0 | 18 |
| markov_deviance | 21 | 3 | 0 | 18 |
| rules_plus_sequence | 20 | 4 | 0 | 18 |
| population_rules_plus_sequence | 17 | 7 | 0 | 18 |
| conditional_permutation | 23 | 1 | 5 | 13 |

- calibrated versus rules: gain 23 true / 1 false; lose 0 true / 4 false. Reader gains/losses 5/0.
- full_budget versus rules: gain 23 true / 1 false; lose 1 true / 23 false. Reader gains/losses 5/0.
- calibrated versus markov_deviance: gain 17 true / 1 false; lose 15 true / 3 false. Reader gains/losses 5/0.
- full_budget versus markov_deviance: gain 17 true / 1 false; lose 15 true / 3 false. Reader gains/losses 5/0.
- calibrated versus rules_plus_sequence: gain 21 true / 1 false; lose 5 true / 1 false. Reader gains/losses 5/0.
- full_budget versus rules_plus_sequence: gain 17 true / 1 false; lose 14 true / 4 false. Reader gains/losses 5/0.
- calibrated versus population_rules_plus_sequence: gain 21 true / 1 false; lose 4 true / 2 false. Reader gains/losses 5/0.
- full_budget versus population_rules_plus_sequence: gain 18 true / 1 false; lose 12 true / 7 false. Reader gains/losses 5/0.
- Permutation minus global_combined recall: +0.258; fixed-decision actor-cluster 95% interval [0.1111111111111111, 0.3999503968253967].
- Permutation minus rules recall: +0.371; fixed-decision actor-cluster 95% interval [0.269520757020757, 0.47058823529411764].
- Permutation minus robust_distance recall: +0.371; fixed-decision actor-cluster 95% interval [0.269520757020757, 0.47058823529411764].
- Permutation minus isolation_forest recall: +0.371; fixed-decision actor-cluster 95% interval [0.269520757020757, 0.47058823529411764].
- Permutation minus markov_deviance recall: +0.032; fixed-decision actor-cluster 95% interval [-0.14394409937888197, 0.22263655462184864].
- Permutation minus population_rules_plus_sequence recall: +0.274; fixed-decision actor-cluster 95% interval [0.11971153846153848, 0.4198457223001402].

| Reader session | Events | Tools | Statistic | MC p | Score | Rank | Outcome |
|---|---:|---:|---:|---:|---:|---:|---|
| p0-30-1148 | 20 | 3 | 194 | 0.002 | 499 | 4 | alert |
| p0-30-865 | 35 | 5 | 466 | 0.002 | 499 | 7 | alert |
| p0-30-415 | 36 | 5 | 690 | 0.002 | 499 | 11 | alert |
| p0-30-1179 | 26 | 4 | 304 | 0.002 | 499 | 16 | alert |
| p0-30-747 | 34 | 4 | 466 | 0.002 | 499 | 17 | alert |
| p0-30-371 | 24 | 4 | 188 | 0.002 | 499 | 25 | shared_cap_or_boundary_tie |
| p0-30-236 | 10 | 2 | 22 | 0.038 | 481 | 93 | shared_cap_or_boundary_tie |
| p0-30-274 | 19 | 5 | 154 | 0.002 | 499 | 26 | shared_cap_or_boundary_tie |
| p0-30-24 | 12 | 3 | 48 | 0.004 | 498 | 57 | shared_cap_or_boundary_tie |
| p0-30-515 | 16 | 4 | 58 | 0.004 | 498 | 58 | shared_cap_or_boundary_tie |
| p0-30-230 | 35 | 3 | 566 | 0.002 | 499 | 34 | shared_cap_or_boundary_tie |
| p0-30-463 | 13 | 3 | 38 | 0.014 | 493 | 66 | shared_cap_or_boundary_tie |
| p0-30-73 | 17 | 2 | 43 | 0.016 | 492 | 70 | shared_cap_or_boundary_tie |
| p0-30-799 | 21 | 2 | 195 | 0.002 | 499 | 38 | shared_cap_or_boundary_tie |
| p0-30-572 | 20 | 4 | 106 | 0.002 | 499 | 44 | shared_cap_or_boundary_tie |
| p0-30-902 | 37 | 4 | 731 | 0.002 | 499 | 45 | shared_cap_or_boundary_tie |
| p0-30-550 | 28 | 4 | 358 | 0.002 | 499 | 47 | shared_cap_or_boundary_tie |
| p0-30-876 | 11 | 3 | 30 | 0.018 | 491 | 71 | shared_cap_or_boundary_tie |

### fresh_permutation_nonsequence: 60 positives / 1200 sessions

Cap 24; candidates 31; selected 24; cap-suppressed 7. Score ceiling: 1 sessions. At boundary score 484, 5 of 5 candidate ties are selected.
Constant-tool sessions: 1; constant sampled null statistic: 1.

| Detector | Exactly-full-budget TP | FP | Reader detected | Reader missed |
|---|---:|---:|---:|---:|
| rules | 15 | 9 | 0 | 0 |
| markov_deviance | 5 | 19 | 0 | 0 |
| rules_plus_sequence | 16 | 8 | 0 | 0 |
| population_rules_plus_sequence | 16 | 8 | 0 | 0 |
| conditional_permutation | 4 | 20 | 0 | 0 |

- calibrated versus rules: gain 2 true / 20 false; lose 12 true / 4 false. Reader gains/losses 0/0.
- full_budget versus rules: gain 2 true / 20 false; lose 13 true / 9 false. Reader gains/losses 0/0.
- calibrated versus markov_deviance: gain 4 true / 20 false; lose 4 true / 16 false. Reader gains/losses 0/0.
- full_budget versus markov_deviance: gain 4 true / 20 false; lose 5 true / 19 false. Reader gains/losses 0/0.
- calibrated versus rules_plus_sequence: gain 2 true / 20 false; lose 11 true / 4 false. Reader gains/losses 0/0.
- full_budget versus rules_plus_sequence: gain 2 true / 20 false; lose 14 true / 8 false. Reader gains/losses 0/0.
- calibrated versus population_rules_plus_sequence: gain 2 true / 20 false; lose 12 true / 4 false. Reader gains/losses 0/0.
- full_budget versus population_rules_plus_sequence: gain 2 true / 19 false; lose 14 true / 7 false. Reader gains/losses 0/0.
- Permutation minus global_combined recall: -0.150; fixed-decision actor-cluster 95% interval [-0.25895593869731803, -0.03417592051431913].
- Permutation minus rules recall: -0.167; fixed-decision actor-cluster 95% interval [-0.30428332318928786, -0.03506933744221885].
- Permutation minus robust_distance recall: -0.133; fixed-decision actor-cluster 95% interval [-0.2272840119165839, -0.042697568389057756].
- Permutation minus isolation_forest recall: -0.050; fixed-decision actor-cluster 95% interval [-0.15, 0.04770277935337488].
- Permutation minus markov_deviance recall: +0.000; fixed-decision actor-cluster 95% interval [-0.09284615384615386, 0.09571886446886445].
- Permutation minus population_rules_plus_sequence recall: -0.167; fixed-decision actor-cluster 95% interval [-0.30099056603773583, -0.03736013986013991].

| Reader session | Events | Tools | Statistic | MC p | Score | Rank | Outcome |
|---|---:|---:|---:|---:|---:|---:|---|

## Limits and leakage checks

- Conditional exchangeability of tool order is plausible for this IID benign synthetic generator, but legitimate real workflows have structured order and may alert.
- The repeated-run statistic is targeted to previously inspected ordering failures; fresh instances are not blind family validation.
- Conditioning on counts deliberately removes volume, denial, frequency and composition signals; constant-tool or weakly informative sessions may remain undetectable.
- 499 null draws give p resolution 1/500 and a saturated integer score; ties and the shared budget can exclude real anomalies.
- Diagnostic Monte Carlo p values are conditional randomization evidence, not attack probabilities or real-world false-positive guarantees.
- All detectors share the same label-free tie policy in this study; tie priorities differ from earlier studies, which remain untouched.
- Paired bootstrap intervals condition on fitted models, fixed null draws and fixed alert decisions; they omit calibration, Monte Carlo and reranking uncertainty.
- The baseline fits no event model. Its only empirical threshold uses unlabelled validation. Labels enter only evaluation after scoring and alert decisions.
- Null draws depend only on the canonical tool multiset and fixed master seed, never on observed order or other sessions. Counts and session length are preserved.
- Work is bounded by 256 events per session and 25 million permutation cells per batch; malformed, duplicate, oversized and undersized sessions reject explicitly.
- Conditional randomization tests order given counts. It deliberately cannot detect anomalies expressed solely in the conditioned-away information.
- Full-budget reviews are separately reported counterfactuals; the operational queue applies a fixed validation threshold plus one global cap, without component or population quotas.
- A Monte Carlo floor/ceiling tie is not certainty. Hash-based tie priority is deterministic, public and not an adversarially secure scheduling policy.
