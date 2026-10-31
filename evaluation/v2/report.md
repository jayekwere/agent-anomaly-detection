# Synthetic behavioral evaluation

An anomaly requires analyst review. Scores are not probabilities.

| Test | Detector | Precision | Recall | AP | False alerts/1,000 | Alerts |
|---|---|---:|---:|---:|---:|---:|
| held_out | rules | 0.786 | 0.172 | 0.384 | 2.50 | 14 |
| held_out | robust_distance | 0.733 | 0.172 | 0.389 | 3.33 | 15 |
| held_out | isolation_forest | 0.412 | 0.109 | 0.253 | 8.33 | 17 |
| unseen_sequence | rules | 0.125 | 0.019 | 0.058 | 5.83 | 8 |
| unseen_sequence | robust_distance | 0.000 | 0.000 | 0.049 | 1.67 | 2 |
| unseen_sequence | isolation_forest | 0.000 | 0.000 | 0.050 | 4.17 | 5 |
| drift | rules | 0.500 | 0.122 | 0.242 | 5.00 | 12 |
| drift | robust_distance | 0.417 | 0.204 | 0.290 | 11.67 | 24 |
| drift | isolation_forest | 0.458 | 0.224 | 0.272 | 10.83 | 24 |

## Interpretation

Rules are the predeclared operational reference. Compare held-out AP and budget recall before promoting a challenger. No detector is validated for production.

Synthetic ground truth is not confirmed malicious activity.
Scores are not probabilities. Review caps can suppress true positives.
Bootstrap intervals assume independent sessions; repeated actors violate that assumption.
Session-end detection only; online incident latency is not measured.
Sequence features are coarse and may miss unseen ordered patterns.
No guaranteed future false positive rate; no production efficacy claim.

Full per-population results and false-positive/negative evidence are in results.json.

## Analyst review examples

- held_out: false_positive in synthetic session 4-182 (benign); denial rate 0.000, export rate 0.812, events/second 0.233. Review policy and actor context before escalation.
- held_out: false_positive in synthetic session 4-979 (benign); denial rate 0.000, export rate 0.182, events/second 0.228. Review policy and actor context before escalation.
- held_out: false_negative in synthetic session 4-11 (export_burst); denial rate 0.028, export rate 0.583, events/second 1.082. Review policy and actor context before escalation.
- held_out: false_negative in synthetic session 4-37 (export_burst); denial rate 0.000, export rate 0.400, events/second 0.288. Review policy and actor context before escalation.
- held_out: alert in synthetic session 4-54 (denial_probe); denial rate 0.333, export rate 0.185, events/second 0.614. Review policy and actor context before escalation.
- held_out: alert in synthetic session 4-77 (denial_probe); denial rate 0.471, export rate 0.441, events/second 0.319. Review policy and actor context before escalation.
- unseen_sequence: false_positive in synthetic session 6-48 (benign); denial rate 0.000, export rate 0.800, events/second 1.333. Review policy and actor context before escalation.
- unseen_sequence: false_positive in synthetic session 6-106 (benign); denial rate 0.000, export rate 0.071, events/second 0.280. Review policy and actor context before escalation.
- unseen_sequence: false_negative in synthetic session 6-7 (sequence_shift); denial rate 0.000, export rate 0.077, events/second 0.294. Review policy and actor context before escalation.
- unseen_sequence: false_negative in synthetic session 6-12 (sequence_shift); denial rate 0.000, export rate 0.029, events/second 0.839. Review policy and actor context before escalation.
- unseen_sequence: alert in synthetic session 6-100 (sequence_shift); denial rate 0.000, export rate 0.083, events/second 0.266. Review policy and actor context before escalation.
- drift: false_positive in synthetic session 8-90 (benign); denial rate 0.357, export rate 0.000, events/second 0.516. Review policy and actor context before escalation.
- drift: false_positive in synthetic session 8-222 (benign); denial rate 0.333, export rate 0.083, events/second 0.457. Review policy and actor context before escalation.
- drift: false_negative in synthetic session 8-105 (frequency_shift); denial rate 0.028, export rate 0.389, events/second 3.247. Review policy and actor context before escalation.
- drift: false_negative in synthetic session 8-115 (frequency_shift); denial rate 0.000, export rate 0.083, events/second 8.069. Review policy and actor context before escalation.
- drift: alert in synthetic session 8-181 (denial_probe); denial rate 0.343, export rate 0.514, events/second 0.448. Review policy and actor context before escalation.
- drift: alert in synthetic session 8-611 (denial_probe); denial rate 0.455, export rate 0.273, events/second 0.650. Review policy and actor context before escalation.

Evidence values describe observed behavior; they are not causal ML feature attributions.
