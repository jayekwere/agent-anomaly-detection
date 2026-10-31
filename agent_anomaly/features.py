"""Causal session features. Ground truth and raw payloads are never inputs."""

from collections import Counter

import numpy as np

from . import correlate

NAMES = (
    "denial_rate",
    "export_rate",
    "privileged_rate",
    "events_per_second",
    "tool_diversity",
    "transition_surprise",
    "actor_tool_novelty",
    "actor_rate_change",
)


class Features:
    def __init__(self) -> None:
        self.tools = {}
        self.transitions = Counter()
        self.rates = {}

    def transform(self, events: list[dict], fit: bool = False) -> tuple[list, np.ndarray, list]:
        groups = correlate(events)
        rows, keys, ends = [], [], []
        for key, group in sorted(groups.items(), key=lambda kv: kv[1][-1].at):
            scope = key[:2]
            tools = [e.tool for e in group]
            n = len(group)
            duration = max(1.0, (group[-1].at - group[0].at).total_seconds())
            rate = n / duration
            known = self.tools.get(scope, set())
            pairs = list(zip(tools, tools[1:]))
            rows.append(
                [
                    sum(e.outcome == "denied" for e in group) / n,
                    sum(t == "evidence.export" for t in tools) / n,
                    sum(t == "admin.delete" for t in tools) / n,
                    rate,
                    len(set(tools)) / n,
                    sum(self.transitions[(scope, p)] == 0 for p in pairs) / max(1, len(pairs)),
                    sum(t not in known for t in tools) / n,
                    abs(rate - self.rates.get(scope, rate)),
                ]
            )
            keys.append(key)
            ends.append(group[-1].at)
            if fit:
                self.tools.setdefault(scope, set()).update(tools)
                self.transitions.update((scope, p) for p in pairs)
                self.rates[scope] = rate
        return keys, np.asarray(rows, dtype=float), ends
