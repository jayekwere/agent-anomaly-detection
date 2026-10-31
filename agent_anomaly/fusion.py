"""Validation-scaled maximum fusion with one threshold and one shared alert cap."""

import numpy as np

from .detectors import budget

COMPONENTS = ("rules", "markov_deviance")


def components(scores: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    try:
        a, b = (np.asarray(scores[name], dtype=float) for name in COMPONENTS)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("missing or invalid fusion component") from exc
    if (
        a.ndim != 1
        or b.shape != a.shape
        or not len(a)
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
    ):
        raise ValueError("invalid fusion component shape or values")
    return a, b


class RulesSequenceFusion:
    def fit(
        self, validation_scores: dict[str, np.ndarray], quantile: float = 0.98
    ) -> "RulesSequenceFusion":
        if not np.isfinite(quantile) or not 0 < quantile < 1:
            raise ValueError("invalid calibration quantile")
        arrays = components(validation_scores)
        scales = [float(np.quantile(a, quantile, method="higher")) for a in arrays]
        if min(scales) <= 0:
            raise ValueError("fusion calibration scales must be positive")
        self.scales = dict(zip(COMPONENTS, scales))
        self.quantile = quantile
        self.threshold = float(
            np.quantile(self.score(validation_scores), quantile, method="higher")
        )
        return self

    def score(self, scores: dict[str, np.ndarray]) -> np.ndarray:
        if not hasattr(self, "scales"):
            raise ValueError("fusion has not been calibrated")
        a, b = components(scores)
        fused = np.maximum(a / self.scales[COMPONENTS[0]], b / self.scales[COMPONENTS[1]])
        if not np.isfinite(fused).all():
            raise ValueError("nonfinite fused score")
        return fused

    def alerts(self, scores: np.ndarray, review_budget: float) -> np.ndarray:
        if not hasattr(self, "threshold"):
            raise ValueError("fusion has not been calibrated")
        scores = np.asarray(scores, dtype=float)
        # Validate before replacing values with the candidate sentinel.
        if scores.ndim != 1 or not np.isfinite(scores).all() or not 0 <= review_budget <= 1:
            raise ValueError("invalid fusion scores or budget")
        candidates = scores > self.threshold
        return candidates & budget(np.where(candidates, scores, -1e10), review_budget)

    def parameters(self) -> dict:
        if not hasattr(self, "threshold"):
            raise ValueError("fusion has not been calibrated")
        return {
            "component_scales": dict(self.scales),
            "threshold": self.threshold,
            "quantile": self.quantile,
            "combination": "maximum",
        }
