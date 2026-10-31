"""Metrics for session-level review; scores are not attack probabilities."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from .detectors import budget


def measure(y: np.ndarray, scores: np.ndarray, alerts: np.ndarray) -> dict:
    y = np.asarray(y, dtype=int)
    tp = int(y[alerts].sum())
    fp = int(alerts.sum()) - tp
    result = {
        "precision": tp / max(1, int(alerts.sum())),
        "recall": tp / max(1, int(y.sum())),
        "false_alerts_per_1000_sessions": fp * 1000 / len(y),
        "alerts": int(alerts.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": int(y.sum()) - tp,
        "average_precision": float(average_precision_score(y, scores)) if y.sum() else None,
        "roc_auc": float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
    }
    result["budgets"] = {}
    for fraction in (0.01, 0.02, 0.05):
        selected = budget(scores, fraction)
        hits = int(y[selected].sum())
        result["budgets"][str(fraction)] = {
            "precision": hits / max(1, int(selected.sum())),
            "recall": hits / max(1, int(y.sum())),
            "alerts": int(selected.sum()),
        }
    rng = np.random.default_rng(900)
    samples = []
    for _ in range(300):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].sum():
            samples.append(float(y[idx][alerts[idx]].sum() / y[idx].sum()))
    result["recall_bootstrap_95_interval"] = (
        np.quantile(samples, [0.025, 0.975]).tolist() if samples else None
    )
    return result
