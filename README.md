# Agent Anomaly Detection

Isolation Forest experiments on synthetic access sessions. The current evaluation separates training, threshold selection and testing, and compares the model with a simple sensitive-action-rate baseline.

## Method

Three independently generated sets use seeds 42, 43 and 44. Each contains 2,000 normal and 100 subtly altered sessions, with disjoint session IDs. Features are action frequencies, transition entropy and session length. Normal sessions can include sensitive actions too; there is no attack-only indicator.

The scaler and forest fit only the training features. The forest uses `contamination="auto"`, and its built-in binary prediction threshold is not used. A chosen **2% review budget** sets the threshold from unlabelled validation scores, excluding ties at that threshold. Labels are used only to measure results, not to fit or choose a threshold. The held-out test set is scored once with that fixed threshold. The simple baseline uses the same selection rule.

## Recorded results

Local execution on October 27, 2026, Python 3.14.6 with pinned dependencies: **6 regression tests passed**, including rejection of overlapping session IDs and checks that changing test features or labels cannot change the selected threshold. [Full results](evaluation/results.json) include source/feature hashes, versions and confusion matrices.

| Held-out test result | ROC-AUC | Average precision | Precision | Recall |
| --- | ---: | ---: | ---: | ---: |
| isolationForest | 0.7290 | 0.1062 | 0.1429 | 0.0700 |
| sensitiveActionRate | 0.8288 | 0.1849 | 0.2258 | 0.0700 |

Isolation Forest found **7 of 100 anomalies**, with **42 false alerts** and 93 misses. The simple baseline found the same 7, with 24 false alerts. The model did not beat that baseline. Its test alert rate was 2.33%; a validation review budget does not guarantee a fixed rate on later data.

## Reproduce

Python 3.12+:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
python evaluate.py
```

The [CI workflow](.github/workflows/evaluation.yml) runs regression tests on Python 3.12/3.13 and the full generated evaluation on Python 3.12. It retains the measured output for 14 days. No external dataset or account credentials are needed.

## Earlier experiments and limits

The saved notebook is historical: its easier generator scored about 0.99 ROC-AUC, and a revised generator scored about 0.75. Those experiments fitted and evaluated on the same samples and supplied the true synthetic contamination rate. They are not held-out performance claims.

The current script removes those evaluation shortcuts. It still uses one synthetic generator family, so disjoint sessions do not establish performance on real users, changing behavior or unseen attack families. The generator's labels are not proof of malicious intent. The low recall and false-alert count remain part of the result, not issues hidden by the passing regression tests.
