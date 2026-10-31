# Rules plus sequence with one shared review budget

## Fixed experiment

The local design was committed as `b10268c` before generating or scoring fresh test batches. The fusion implementation and leakage tests were committed as `089573c` before the first evaluation. See the [packaged plan](../agent_anomaly/plans/combined-v1.json). No score formula, smoothing, scale quantile, threshold, seed, budget or population weight was tuned after looking at test results. Later changes add reporting, artifact checks and CI integration.

Training (seed 42/day 0) and validation (43/day 2) remain unchanged: 1,200 synthetic sessions each. Training labels are discarded. The sequence model uses tenant/actor-scoped add-one-smoothed within-session transitions; rules retain their original feature definitions. The fitted models remain frozen. Actor recurrence intentionally measures future behavior of known actors.

The primary `fresh_joint` set has two complete independently generated streams: 600 non-sequence-generator sessions with seed 8112601 and 600 sequence-generator sessions with seed 8112602, both on day 16. Every benign and anomalous session is retained. Neutral stream prefixes namespace IDs without becoming scoring features. No ground truth selects mixture membership. The original generator is unchanged.

The primary set contains 62 anomalies: 13 denial probes, 10 export bursts, 9 frequency shifts and 30 sequence shifts. The separate sequence control uses seed 8112603/day 18 and the non-sequence control uses seed 8112604/day 20, with 1,200 sessions each. These periods and seeds are new relative to all earlier evaluations. Chronology, session disjointness and fitted-state fingerprints are checked; ground truth is used only after scoring and alert decisions.

This is targeted follow-up on inspected synthetic families, not blind family or production validation. The mixture is an experimental choice, not measured operational prevalence.

## Fusion and budget

Let `r` and `s` be the rules and sequence scores. Their unlabelled validation 98th percentiles are **1.5625** and **1.9964986029162488**. The fixed fusion is:

```text
combined_score = max(r / 1.5625, s / 1.9964986029162488)
```

The combined validation 98th percentile is **1.1789473684210525**. Scores must strictly exceed it, then a single stable top-k cap permits at most **24 unique sessions per 1,200-session batch**. There are no per-component quotas and no union of separately capped alerts. The maximum's score source is reported as descriptive signal dominance, not causal attribution or an attack probability. Calibration fails explicitly if a component scale is nonpositive.

Validation is reused to normalize scores and set the combined threshold. It is not used to optimize weights or measure independent false-positive guarantees. The higher threshold accounts operationally for the broader candidate union but can suppress correct component alerts. It is not a mathematical future false-positive-rate guarantee.

The equal-workload counterfactual reviews exactly the top 24 scores per detector, ignoring thresholds. It uses the same predeclared score and changes no model or weight. These results are reported separately from thresholded/capped operation; neither view is chosen after the fact as the sole favorable result.

## Primary results and actual workload

| Detector | AP | True alerts | False alerts | Total alerts | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| Rules | 0.201 | 5 | 9 | 14 | 0.357 | 0.081 |
| Sequence | 0.275 | 12 | 12 | 24 | 0.500 | 0.194 |
| Combined | 0.393 | 11 | 8 | 19 | 0.579 | 0.177 |

The combination improves ranking AP and precision in this sample, but **does not improve recall over standalone sequence**. At exactly 24 reviews, both sequence and combined find **12/62** positives (recall 0.194) with 12 false alerts; rules find **8/62**. The combined ranking exchanges five sequence-alone detections for five denial detections at that workload: it provides broader scenario coverage without a net increase in detected anomalies. It still detects no frequency-shift anomalies in the primary set.

The raw component-threshold candidate union contains 52 sessions. The combined threshold reduces that to 19; the 24-session cap suppresses **zero** further sessions. Thus the calibrated recall loss is caused by fusion thresholding, not an exhausted queue. The 19 selected alerts have rules as their dominant score in 7 cases (5 true, 2 false) and sequence in 12 (6 true, 6 false).

Versus standalone rules, calibrated combination gains 6 true / 4 false alerts and loses 0 true / 5 false alerts. Versus standalone sequence, it gains 5 true / 1 false and loses 6 true / 5 false. False alerts per 1,000 total sessions are 6.67 combined, 7.50 rules and 10.00 sequence.

The paired actor-cluster bootstrap recall difference is **+0.097 [0.037, 0.167]** versus rules and **-0.016 [-0.105, 0.077]** versus sequence. These descriptive intervals condition on fitted models, calibration and fixed alert decisions; they do not include training/calibration uncertainty or rerank the review queue within each resample.

## Reader anomalies remain missed

All **9 reader-sequence anomalies** in the primary set are missed by rules, sequence and combination, under both thresholded operation and exact 24-session review. Combining scores does not manufacture a missing reader signal. Examples in JSON include raw component scores, combined threshold, global score rank and reason for exclusion. For example, synthetic session `p1-16-39` has combined score **0.695**, below **1.179**, and global rank **213**. These examples do not support a claim that increasing the cap by a few alerts would solve the blind spot.

On the sequence-only control, combination and standalone sequence both miss **all 27 reader-sequence anomalies**. Under exact 24-review ranking, rules happen to flag **one** of those reader positives, while combination flags none: fusion can also discard an incidental reader detection. Under the frozen calibrated thresholds, none of the three detect a reader sequence in that control. The non-sequence control contains no reader-sequence positives; its reader-sequence recall is reported as unavailable.

## Control results prevent a blanket promotion claim

On the sequence-only control, calibrated combination finds **4/60** positives with 4 false alerts, while sequence alone finds **16/60** with 8 false alerts. The cap is not binding for combination: its stricter threshold leaves only eight alerts. Exactly-full-budget combination and sequence each find 16 positives with eight false alerts.

On the non-sequence control, calibrated combination finds **14/63**, versus **16/63** for rules, both with four false alerts. At an equal 24 reviews, both find 17 positives and seven false alerts, but the combination trades four denial detections for four export detections. AP is 0.417 combined versus 0.432 rules. These tradeoffs support keeping the existing reference unchanged and retaining this fusion as an evaluated candidate.

## Reproduce and verify

```sh
.venv/bin/python -m agent_anomaly.combined_experiment --output artifacts/combined
.venv/bin/python scripts/verify_combined_results.py artifacts/combined/results.json --reference evaluation/combined-v1/results.json
```

[Calculated report](../evaluation/combined-v1/report.md) and [full JSON](../evaluation/combined-v1/results.json) include every comparator, group count, reader miss, queue attribution, displacement count and paired interval. Tests cover overlapping/disjoint component peaks under one budget, strict ties, zero/small budgets, invalid calibration, label independence, frozen inference, stream deduplication and corrupted reader/queue accounting.

Historical v2/v3 artifacts and their runtime source files are untouched. The replay verifier requires every file in an archived source manifest to remain byte-identical, while allowing additional independent experiment modules to coexist. All other recorded metrics, thresholds, event hashes and metadata are still compared (Python version may differ; numeric tolerance remains 1e-12). A regression test rejects changed historical source and changed results.
