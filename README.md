# Anomaly Detection on AI-Agent Access Behavior

An Isolation Forest experiment on synthetic agent-access sessions. The notebook compares two data generators and shows how feature design changes the reported results.

## Method and recorded results

The first generator included an obvious escalation, export and deletion sequence, plus a feature present only in injected attacks. It reported ROC-AUC around 0.99, but that feature made the experiment too easy to support a useful detection claim.

The revised generator removes that feature and places subtler anomalies within otherwise normal sessions. It uses escalation rate, export rate and transition entropy. The recorded ROC-AUC falls to about 0.75, with low precision/recall for the anomaly class and overlapping score distributions.

These are results recorded in the notebook, not measurements from live agent activity.

## Run it

Open `agent_anomaly_detection.ipynb` in Google Colab and run the cells in order. All data is generated in the notebook; no external dataset or API key is needed.

## Limitations

- The synthetic generator determines which behaviors the model can distinguish.
- The experiment supplies the true contamination rate, which would normally be unknown for real activity.
- Simple frequency and sequence-summary features leave many behaviors untested.
- Results do not establish detection quality on real agent sessions.

## Next steps

Evaluate on separate sessions, choose contamination and decision thresholds without the true anomaly rate, and report precision/recall across those choices. Richer sequence features and additional baselines can follow once that evaluation is in place.
