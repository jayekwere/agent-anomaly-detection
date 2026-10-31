"""Unsupervised fit, validation calibration, and explicit review caps."""

import numpy as np
from sklearn.ensemble import IsolationForest


def budget(scores: np.ndarray, fraction: float) -> np.ndarray:
    scores = np.asarray(scores)
    if scores.ndim != 1 or not np.isfinite(scores).all() or not 0 <= fraction <= 1:
        raise ValueError("invalid scores or budget")
    k = int(len(scores) * fraction)
    selected = np.zeros(len(scores), dtype=bool)
    selected[np.argsort(-scores, kind="stable")[:k]] = True
    return selected


class Detectors:
    def fit(self, x: np.ndarray) -> "Detectors":
        if x.ndim != 2 or x.shape[1] != 8 or len(x) < 2 or not np.isfinite(x).all():
            raise ValueError("invalid training features")
        self.center = np.median(x, axis=0)
        self.scale = np.maximum(np.quantile(x, 0.75, axis=0) - np.quantile(x, 0.25, axis=0), 0.05)
        self.forest = IsolationForest(n_estimators=200, random_state=42, n_jobs=1).fit(x)
        return self

    def scores(self, x: np.ndarray) -> dict[str, np.ndarray]:
        if not hasattr(self, "forest"):
            raise ValueError("model has not been fitted")
        if x.ndim != 2 or x.shape[1] != 8 or not len(x) or not np.isfinite(x).all():
            raise ValueError("invalid scoring features")
        return {
            "rules": np.maximum.reduce([x[:, 0] / 0.2, x[:, 1] / 0.5, x[:, 2] / 0.15]),
            "robust_distance": np.maximum((x - self.center) / self.scale, 0).mean(axis=1),
            "isolation_forest": -self.forest.score_samples(x),
        }
