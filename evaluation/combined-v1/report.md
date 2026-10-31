# Rules plus sequence: one shared alert budget

Synthetic follow-up with fixed maximum fusion and fresh test instances. Each combined session appears once in the shared queue; component alert quotas are never added together. Original detectors and historical evidence are unchanged.

| Fresh batch | Detector | AP | Precision | Recall | False alerts/1,000 | Alerts | Recall @ equal 2% ranking budget |
|---|---|---:|---:|---:|---:|---:|---:|
| fresh_joint | rules | 0.201 | 0.357 | 0.081 | 7.50 | 14 | 0.129 |
| fresh_joint | robust_distance | 0.179 | 0.462 | 0.097 | 5.83 | 13 | 0.177 |
| fresh_joint | isolation_forest | 0.137 | 0.286 | 0.097 | 12.50 | 21 | 0.129 |
| fresh_joint | markov_deviance | 0.275 | 0.500 | 0.194 | 10.00 | 24 | 0.194 |
| fresh_joint | rules_plus_sequence | 0.393 | 0.579 | 0.177 | 6.67 | 19 | 0.194 |
| fresh_sequence_control | rules | 0.050 | 0.000 | 0.000 | 4.17 | 5 | 0.017 |
| fresh_sequence_control | robust_distance | 0.055 | 0.000 | 0.000 | 0.00 | 0 | 0.017 |
| fresh_sequence_control | isolation_forest | 0.049 | 0.000 | 0.000 | 5.00 | 6 | 0.017 |
| fresh_sequence_control | markov_deviance | 0.423 | 0.667 | 0.267 | 6.67 | 24 | 0.267 |
| fresh_sequence_control | rules_plus_sequence | 0.377 | 0.500 | 0.067 | 3.33 | 8 | 0.267 |
| fresh_nonsequence_control | rules | 0.432 | 0.800 | 0.254 | 3.33 | 20 | 0.270 |
| fresh_nonsequence_control | robust_distance | 0.398 | 0.778 | 0.222 | 3.33 | 18 | 0.238 |
| fresh_nonsequence_control | isolation_forest | 0.269 | 0.389 | 0.111 | 9.17 | 18 | 0.127 |
| fresh_nonsequence_control | markov_deviance | 0.142 | 0.333 | 0.095 | 10.00 | 18 | 0.095 |
| fresh_nonsequence_control | rules_plus_sequence | 0.417 | 0.778 | 0.222 | 3.33 | 18 | 0.270 |

## Shared queue, displacement and reader misses

Component scores are divided by their validation 98th percentiles. The maximum is calibrated again on validation, then frozen. Strict threshold ties are excluded and one global 2% cap is applied. Equal-budget ranking metrics ignore thresholds and are separate counterfactual reviews.

### fresh_joint: 62 positives in 1200 sessions

Shared cap 24; unique alerts 19; raw component-candidate union 52; above combined threshold 19; suppressed by cap 0.

| Dominant signal in selected queue | Alerts | True positives | False positives |
|---|---:|---:|---:|
| rules | 7 | 5 | 2 |
| sequence | 12 | 6 | 6 |
| numerical_tie | 0 | 0 | 0 |

| Detector | Reader sequence positives | Detected | Missed | Recall |
|---|---:|---:|---:|---:|
| rules | 9 | 0 | 9 | 0.000 |
| robust_distance | 9 | 0 | 9 | 0.000 |
| isolation_forest | 9 | 0 | 9 | 0.000 |
| markov_deviance | 9 | 0 | 9 | 0.000 |
| rules_plus_sequence | 9 | 0 | 9 | 0.000 |

Exactly-full-budget reviews (thresholds ignored; one shared top-24 ranking):

| Detector | True positives | False positives | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 8 | 16 | 0 | 9 |
| robust_distance | 11 | 13 | 0 | 9 |
| isolation_forest | 8 | 16 | 0 | 9 |
| markov_deviance | 12 | 12 | 0 | 9 |
| rules_plus_sequence | 12 | 12 | 0 | 9 |

- Versus rules: gain 6 true / 4 false alerts; lose 0 true / 5 false alerts. Reader-sequence gains/losses: 0/0.
- Versus markov_deviance: gain 5 true / 1 false alerts; lose 6 true / 5 false alerts. Reader-sequence gains/losses: 0/0.
- Combined minus rules recall: +0.097; paired actor-cluster bootstrap 95% interval [0.03736897274633123, 0.16666666666666666] (fixed fitted models and decisions).
- Combined minus robust_distance recall: +0.081; paired actor-cluster bootstrap 95% interval [0.0, 0.16129032258064516] (fixed fitted models and decisions).
- Combined minus isolation_forest recall: +0.081; paired actor-cluster bootstrap 95% interval [-0.015755208333333333, 0.17124999999999999] (fixed fitted models and decisions).
- Combined minus markov_deviance recall: -0.016; paired actor-cluster bootstrap 95% interval [-0.1052327955891362, 0.07675814751286443] (fixed fitted models and decisions).

- Missed reader sequence p1-16-39: below_combined_threshold; combined score 0.695, threshold 1.179, global rank 213.
- Missed reader sequence p1-16-77: below_combined_threshold; combined score 0.617, threshold 1.179, global rank 320.
- Missed reader sequence p1-16-94: below_combined_threshold; combined score 0.494, threshold 1.179, global rank 553.
- Missed reader sequence p1-16-104: below_combined_threshold; combined score 0.609, threshold 1.179, global rank 334.
- Missed reader sequence p1-16-156: below_combined_threshold; combined score 0.663, threshold 1.179, global rank 260.

### fresh_sequence_control: 60 positives in 1200 sessions

Shared cap 24; unique alerts 8; raw component-candidate union 50; above combined threshold 8; suppressed by cap 0.

| Dominant signal in selected queue | Alerts | True positives | False positives |
|---|---:|---:|---:|
| rules | 1 | 0 | 1 |
| sequence | 7 | 4 | 3 |
| numerical_tie | 0 | 0 | 0 |

| Detector | Reader sequence positives | Detected | Missed | Recall |
|---|---:|---:|---:|---:|
| rules | 27 | 0 | 27 | 0.000 |
| robust_distance | 27 | 0 | 27 | 0.000 |
| isolation_forest | 27 | 0 | 27 | 0.000 |
| markov_deviance | 27 | 0 | 27 | 0.000 |
| rules_plus_sequence | 27 | 0 | 27 | 0.000 |

Exactly-full-budget reviews (thresholds ignored; one shared top-24 ranking):

| Detector | True positives | False positives | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 1 | 23 | 1 | 26 |
| robust_distance | 1 | 23 | 0 | 27 |
| isolation_forest | 1 | 23 | 0 | 27 |
| markov_deviance | 16 | 8 | 0 | 27 |
| rules_plus_sequence | 16 | 8 | 0 | 27 |

- Versus rules: gain 4 true / 3 false alerts; lose 0 true / 4 false alerts. Reader-sequence gains/losses: 0/0.
- Versus markov_deviance: gain 0 true / 1 false alerts; lose 12 true / 5 false alerts. Reader-sequence gains/losses: 0/0.
- Combined minus rules recall: +0.067; paired actor-cluster bootstrap 95% interval [0.0, 0.15266596045197742] (fixed fitted models and decisions).
- Combined minus robust_distance recall: +0.067; paired actor-cluster bootstrap 95% interval [0.0, 0.15266596045197742] (fixed fitted models and decisions).
- Combined minus isolation_forest recall: +0.067; paired actor-cluster bootstrap 95% interval [0.0, 0.15266596045197742] (fixed fitted models and decisions).
- Combined minus markov_deviance recall: -0.200; paired actor-cluster bootstrap 95% interval [-0.32049120234604106, -0.08158333333333341] (fixed fitted models and decisions).

- Missed reader sequence p0-18-90: below_combined_threshold; combined score 0.471, threshold 1.179, global rank 605.
- Missed reader sequence p0-18-96: below_combined_threshold; combined score 0.743, threshold 1.179, global rank 136.
- Missed reader sequence p0-18-129: below_combined_threshold; combined score 0.570, threshold 1.179, global rank 397.
- Missed reader sequence p0-18-134: below_combined_threshold; combined score 0.603, threshold 1.179, global rank 336.
- Missed reader sequence p0-18-141: below_combined_threshold; combined score 0.710, threshold 1.179, global rank 183.

### fresh_nonsequence_control: 63 positives in 1200 sessions

Shared cap 24; unique alerts 18; raw component-candidate union 37; above combined threshold 18; suppressed by cap 0.

| Dominant signal in selected queue | Alerts | True positives | False positives |
|---|---:|---:|---:|
| rules | 12 | 11 | 1 |
| sequence | 6 | 3 | 3 |
| numerical_tie | 0 | 0 | 0 |

| Detector | Reader sequence positives | Detected | Missed | Recall |
|---|---:|---:|---:|---:|
| rules | 0 | 0 | 0 | n/a |
| robust_distance | 0 | 0 | 0 | n/a |
| isolation_forest | 0 | 0 | 0 | n/a |
| markov_deviance | 0 | 0 | 0 | n/a |
| rules_plus_sequence | 0 | 0 | 0 | n/a |

Exactly-full-budget reviews (thresholds ignored; one shared top-24 ranking):

| Detector | True positives | False positives | Reader-sequence detected | Reader-sequence missed |
|---|---:|---:|---:|---:|
| rules | 17 | 7 | 0 | 0 |
| robust_distance | 15 | 9 | 0 | 0 |
| isolation_forest | 8 | 16 | 0 | 0 |
| markov_deviance | 6 | 18 | 0 | 0 |
| rules_plus_sequence | 17 | 7 | 0 | 0 |

- Versus rules: gain 3 true / 3 false alerts; lose 5 true / 3 false alerts. Reader-sequence gains/losses: 0/0.
- Versus markov_deviance: gain 11 true / 0 false alerts; lose 3 true / 8 false alerts. Reader-sequence gains/losses: 0/0.
- Combined minus rules recall: -0.032; paired actor-cluster bootstrap 95% interval [-0.10857572115384616, 0.04220196759259237] (fixed fitted models and decisions).
- Combined minus robust_distance recall: +0.000; paired actor-cluster bootstrap 95% interval [-0.09742247679241556, 0.10251350540216084] (fixed fitted models and decisions).
- Combined minus isolation_forest recall: +0.111; paired actor-cluster bootstrap 95% interval [0.0, 0.22687831768068595] (fixed fitted models and decisions).
- Combined minus markov_deviance recall: +0.127; paired actor-cluster bootstrap 95% interval [0.00698529411764708, 0.24817307692307683] (fixed fitted models and decisions).


## Limits

- Fresh instances of already inspected synthetic families; not blind family validation.
- Maximum fusion can favor one component's extreme tail and displace useful alerts from the other.
- A shared global cap and global calibration provide no reader-specific recall guarantee.
- Validation is reused for unsupervised score scaling and threshold calibration; this is not an independent false-positive-rate guarantee.
- Actor-cluster bootstrap intervals condition on fitted models and fixed alert decisions and omit training/calibration and reranking uncertainty.
- No automatic promotion, malicious-activity probability, or production efficacy claim.
- Dominance is the component providing the maximum normalized score, not a causal feature attribution. Numerical ties use rtol/atol 1e-12 for reporting only.
- Reader-sequence reporting uses ground truth after alerts are fixed; population/scenario information never selects the operating point.
- Known-actor, completed-session evaluation only. A global budget can preserve original sequence blind spots or displace correct standalone alerts.
- Complete population/scenario metrics and missed-reader evidence are in results.json.
