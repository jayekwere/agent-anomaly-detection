# Sequence baseline follow-up

Synthetic, targeted follow-up on fresh instances of a previously inspected family. No sequence-family examples are used in fitting or validation. Original v2 evidence is preserved; scores are not attack probabilities.

| Fresh batch | Detector | AP | Precision | Recall | False alerts/1,000 | Alerts | Recall @ 2% ranking budget |
|---|---|---:|---:|---:|---:|---:|---:|
| fresh_sequence | rules | 0.050 | 0.000 | 0.000 | 5.83 | 7 | 0.000 |
| fresh_sequence | robust_distance | 0.059 | 0.000 | 0.000 | 2.50 | 3 | 0.074 |
| fresh_sequence | isolation_forest | 0.053 | 0.000 | 0.000 | 3.33 | 4 | 0.037 |
| fresh_sequence | markov_deviance | 0.515 | 0.625 | 0.278 | 7.50 | 24 | 0.278 |
| fresh_mixed | rules | 0.378 | 0.800 | 0.207 | 2.50 | 15 | 0.259 |
| fresh_mixed | robust_distance | 0.472 | 0.765 | 0.224 | 3.33 | 17 | 0.276 |
| fresh_mixed | isolation_forest | 0.345 | 0.471 | 0.138 | 7.50 | 17 | 0.207 |
| fresh_mixed | markov_deviance | 0.182 | 0.462 | 0.103 | 5.83 | 13 | 0.138 |
| fresh_sequence_drift | rules | 0.038 | 0.000 | 0.000 | 3.33 | 4 | 0.000 |
| fresh_sequence_drift | robust_distance | 0.040 | 0.000 | 0.000 | 20.00 | 24 | 0.000 |
| fresh_sequence_drift | isolation_forest | 0.041 | 0.000 | 0.000 | 20.00 | 24 | 0.000 |
| fresh_sequence_drift | markov_deviance | 0.355 | 0.500 | 0.235 | 10.00 | 24 | 0.235 |

## Details

First-order, actor-scoped transition counts are fitted on unfiltered training events only. Add-one smoothing and the normalized conditional deviance formula were fixed before test generation. All four detectors use their own unlabelled validation 98th percentile, strict > ties, and the same 2% batch review cap. Ranking-budget recall ignores calibration and is reported separately.

### fresh_sequence: 54 positives in 1200 sessions

| Markov population | Recall | True positives | False positives |
|---|---:|---:|---:|
| batch | 0.429 | 9 | 4 |
| operator | 0.353 | 6 | 5 |
| reader | 0.000 | 0 | 0 |

- Markov minus rules recall: +0.278; paired actor-cluster bootstrap 95% interval [+0.145, +0.426].
- Markov minus robust_distance recall: +0.278; paired actor-cluster bootstrap 95% interval [+0.145, +0.426].
- Markov minus isolation_forest recall: +0.278; paired actor-cluster bootstrap 95% interval [+0.145, +0.426].

Count-preserving order control (one permutation per session; no relabelled efficacy claim):

- original_sequence: median original minus shuffled Markov score +1.134; original score higher in 100.0% of sessions.
- original_benign: median original minus shuffled Markov score +0.000; original score higher in 49.3% of sessions.

### fresh_mixed: 58 positives in 1200 sessions

| Markov population | Recall | True positives | False positives |
|---|---:|---:|---:|
| batch | 0.000 | 0 | 4 |
| operator | 0.053 | 1 | 1 |
| reader | 0.312 | 5 | 2 |

- Markov minus rules recall: -0.103; paired actor-cluster bootstrap 95% interval [-0.256, +0.040].
- Markov minus robust_distance recall: -0.121; paired actor-cluster bootstrap 95% interval [-0.246, +0.018].
- Markov minus isolation_forest recall: -0.034; paired actor-cluster bootstrap 95% interval [-0.159, +0.087].

### fresh_sequence_drift: 51 positives in 1200 sessions

| Markov population | Recall | True positives | False positives |
|---|---:|---:|---:|
| batch | 0.385 | 5 | 5 |
| operator | 0.500 | 7 | 7 |
| reader | 0.000 | 0 | 0 |

- Markov minus rules recall: +0.235; paired actor-cluster bootstrap 95% interval [+0.127, +0.375].
- Markov minus robust_distance recall: +0.235; paired actor-cluster bootstrap 95% interval [+0.127, +0.375].
- Markov minus isolation_forest recall: +0.235; paired actor-cluster bootstrap 95% interval [+0.127, +0.375].

## Limits

- Fresh instances of an already inspected synthetic family, not a blind family holdout.
- Length-normalized empirical transition deviance retains finite-sample and tool-composition effects.
- First-order transitions cannot distinguish sequences sharing transition counts.
- Training labels remain unused despite contamination; no production efficacy claim.
- Paired intervals resample tenant/actor clusters with fixed decisions; they do not include training or validation uncertainty, or rerun the batch cap in each resample.
- Per-session bootstrap intervals inherited from the original metrics assume independence; prefer the paired actor-cluster differences for this comparison.
- Shuffle score differences within rtol=1e-12 / atol=1e-12 count as numerical ties, consistent with artifact comparison precision.
- A shuffled session can still have unusual composition. One permutation is a diagnostic, not a permutation significance test.
- Unknown actors and sessions with fewer than two events reject explicitly. Unknown tools use a reserved smoothed bucket without updating fitted state.
- Full scenario/population results, thresholds, seeds, event hashes and source hashes are in results.json.
