"""Frozen training-derived behavioral strata, with same-tenant validation calibration."""

from collections import Counter

import numpy as np

from . import correlate
from .detectors import budget
from .fusion import RulesSequenceFusion, components


class PopulationCalibration:
    def fit(
        self,
        train: list[dict],
        validation_keys: list,
        validation_scores: dict,
        settings: dict,
        quantile: float = 0.98,
    ) -> "PopulationCalibration":
        read_cut, export_cut = (
            settings[k] for k in ["read_dominant_min_fraction", "export_heavy_min_fraction"]
        )
        minimum = settings["minimum_validation_sessions"]
        if (
            type(minimum) is not int
            or minimum < 2
            or not all(np.isfinite(x) and 0 <= x <= 1 for x in [read_cut, export_cut])
        ):
            raise ValueError("invalid population calibration settings")
        counters: dict[tuple, Counter] = {}
        for key, events in correlate(train).items():
            counters.setdefault(key[:2], Counter()).update(e.tool for e in events)
        if not counters:
            raise ValueError("population calibration requires training events")
        self.profiles, self.training_proportions = {}, {}
        for scope, counts in counters.items():
            n = sum(counts.values())
            read, export = counts["case.read"] / n, counts["evidence.export"] / n
            group = (
                "read_dominant"
                if read >= read_cut
                else "export_heavy"
                if export >= export_cut
                else "other"
            )
            self.profiles[scope] = group
            self.training_proportions[scope] = {"read_fraction": read, "export_fraction": export}
        a, b = components(validation_scores)
        if len(validation_keys) != len(a) or len(set(validation_keys)) != len(validation_keys):
            raise ValueError("invalid validation session alignment")
        groups = self.groups(validation_keys)
        self.references, self.calibrators = {}, {}
        self.minimum, self.quantile = minimum, quantile
        for tenant in sorted({k[0] for k in self.profiles}):
            tenant_mask = np.array([key[0] == tenant for key in validation_keys])
            if int(tenant_mask.sum()) < minimum:
                raise ValueError("tenant has insufficient validation support")
            pooled = RulesSequenceFusion().fit(
                {"rules": a[tenant_mask], "markov_deviance": b[tenant_mask]}, quantile
            )
            self.calibrators[(tenant, "__tenant__")] = pooled
            for group in sorted({g for (t, _), g in self.profiles.items() if t == tenant}):
                key = (tenant, group)
                mask = np.array([value == key for value in groups])
                count = int(mask.sum())
                source, reason = (tenant, "__tenant__"), "sparse_validation_group"
                if count >= minimum:
                    try:
                        local = RulesSequenceFusion().fit(
                            {"rules": a[mask], "markov_deviance": b[mask]}, quantile
                        )
                    except ValueError:
                        reason = "nonpositive_group_scale"
                    else:
                        self.calibrators[key] = local
                        source, reason = key, None
                self.references[key] = {
                    "source": source,
                    "mode": "local" if reason is None else "same_tenant_fallback",
                    "reason": reason,
                    "validation_sessions": count,
                    "reference_sessions": count if reason is None else int(tenant_mask.sum()),
                }
        return self

    def groups(self, keys: list) -> list[tuple[str, str]]:
        if not hasattr(self, "profiles"):
            raise ValueError("population groups have not been fitted")
        result = []
        for key in keys:
            if key[:2] not in self.profiles:
                raise ValueError("unknown actor scope for frozen population profile")
            result.append((key[0], self.profiles[key[:2]]))
        return result

    def score(self, keys: list, scores: dict) -> tuple[np.ndarray, list, list]:
        if not hasattr(self, "references"):
            raise ValueError("population calibration has not been fitted")
        a, b = components(scores)
        if len(keys) != len(a):
            raise ValueError("invalid population score alignment")
        groups = self.groups(keys)
        result = np.empty(len(keys), dtype=float)
        modes = []
        for group in sorted(set(groups)):
            mask = np.array([g == group for g in groups])
            reference = self.references[group]
            calibrator = self.calibrators[reference["source"]]
            result[mask] = (
                calibrator.score({"rules": a[mask], "markov_deviance": b[mask]})
                / calibrator.threshold
            )
        if not np.isfinite(result).all():
            raise ValueError("nonfinite population score")
        modes = [self.references[group]["mode"] for group in groups]
        return result, groups, modes

    def alerts(self, scores: np.ndarray, fraction: float) -> np.ndarray:
        scores = np.asarray(scores, dtype=float)
        if scores.ndim != 1 or not np.isfinite(scores).all() or not 0 <= fraction <= 1:
            raise ValueError("invalid population scores or budget")
        candidates = scores > 1.0
        return candidates & budget(np.where(candidates, scores, -1e10), fraction)

    def parameters(self) -> dict:
        if not hasattr(self, "references"):
            raise ValueError("population calibration has not been fitted")
        return {
            "minimum_validation_sessions": self.minimum,
            "quantile": self.quantile,
            "profiles": [
                {
                    "tenant": t,
                    "actor": a,
                    "group": self.profiles[(t, a)],
                    **self.training_proportions[(t, a)],
                }
                for t, a in sorted(self.profiles)
            ],
            "references": [
                {
                    "tenant": t,
                    "group": g,
                    **self.references[(t, g)],
                    "calibration": self.calibrators[self.references[(t, g)]["source"]].parameters(),
                }
                for t, g in sorted(self.references)
            ],
        }
