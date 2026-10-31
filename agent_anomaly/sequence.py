"""First-order transition deviance against frozen, tenant/actor-scoped training counts.

This is a descriptive divergence score, not a calibrated attack probability or a
chi-squared test. Empirical session probabilities require no labels or fitting
on other evaluation sessions. Session boundaries are never linked by a bigram.
"""

from collections import Counter
import hashlib
import json
import math

import numpy as np

from . import correlate

_UNKNOWN = "<unknown>"  # Cannot collide with a schema-valid tool token.


class MarkovDeviance:
    def __init__(self, smoothing: float = 1.0) -> None:
        if not math.isfinite(smoothing) or smoothing <= 0:
            raise ValueError("smoothing must be finite and positive")
        self.smoothing = smoothing
        self._vocabulary: dict[tuple[str, str], frozenset[str]] = {}
        self._pairs: dict[tuple[str, str], Counter] = {}
        self._rows: dict[tuple[str, str], Counter] = {}

    def fit(self, events: list[dict]) -> "MarkovDeviance":
        groups = correlate(events)
        if not groups or not any(len(group) > 1 for group in groups.values()):
            raise ValueError("training requires within-session transitions")
        vocab, pairs, rows = {}, {}, {}
        for key, group in groups.items():
            scope = key[:2]
            tools = [event.tool for event in group]
            vocab.setdefault(scope, set()).update(tools)
            transitions = list(zip(tools, tools[1:]))
            pairs.setdefault(scope, Counter()).update(transitions)
            rows.setdefault(scope, Counter()).update(a for a, _ in transitions)
        self._vocabulary = {scope: frozenset(tools) for scope, tools in vocab.items()}
        self._pairs, self._rows = pairs, rows
        return self

    def score(self, events: list[dict]) -> tuple[list, np.ndarray]:
        if not self._vocabulary:
            raise ValueError("sequence model has not been fitted")
        groups = correlate(events)
        keys, scores = [], []
        for key, group in sorted(groups.items(), key=lambda kv: kv[1][-1].at):
            scope = key[:2]
            if scope not in self._vocabulary:
                raise ValueError("sequence model has no training reference for actor scope")
            if len(group) < 2:
                raise ValueError("sequence scoring requires at least two events per session")
            vocab = self._vocabulary[scope]
            tools = [e.tool if e.tool in vocab else _UNKNOWN for e in group]
            observed = Counter(zip(tools, tools[1:]))
            outgoing = Counter(tools[:-1])
            n = len(tools) - 1
            score = 0.0
            for (a, b), count in observed.items():
                empirical = count / outgoing[a]
                reference = (self._pairs[scope].get((a, b), 0) + self.smoothing) / (
                    self._rows[scope].get(a, 0) + self.smoothing * (len(vocab) + 1)
                )
                score += 2 * count / n * math.log(empirical / reference)
            keys.append(key)
            scores.append(max(0.0, score))  # Roundoff near the KL lower bound.
        return keys, np.asarray(scores, dtype=float)

    def fingerprint(self) -> str:
        """Content identity for leakage checks; publishes no raw event payloads."""
        state = {"smoothing": self.smoothing, "scopes": []}
        for scope in sorted(self._vocabulary):
            state["scopes"].append(
                {
                    "scope": scope,
                    "vocabulary": sorted(self._vocabulary[scope]),
                    "pairs": sorted((a, b, count) for (a, b), count in self._pairs[scope].items()),
                }
            )
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
