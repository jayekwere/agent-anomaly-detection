"""Count-conditioned randomization of adjacent-repeat deviation; no label/model fitting."""

from collections import Counter
import hashlib
import json

import numpy as np

from . import correlate


class ConditionalPermutation:
    def __init__(self, settings: dict) -> None:
        self.settings = {
            k: settings[k]
            for k in ["replicates", "seed", "max_session_events", "max_permutation_cells_per_batch"]
        }
        if any(type(v) is not int for v in self.settings.values()):
            raise ValueError("permutation settings require integers")
        if (
            not 1 <= self.settings["replicates"] <= 9999
            or not 2 <= self.settings["max_session_events"] <= 10000
            or self.settings["max_permutation_cells_per_batch"] < 1
        ):
            raise ValueError("invalid permutation work limits")

    def encode(self, tools: list[str]) -> tuple[np.ndarray, np.ndarray, int]:
        counts = sorted(Counter(tools).items())
        vocabulary = {tool: i for i, (tool, _) in enumerate(counts)}
        observed = np.array([vocabulary[t] for t in tools], dtype=np.int32)
        canonical = np.repeat(
            np.arange(len(counts), dtype=np.int32), [count for _, count in counts]
        )
        payload = json.dumps([self.settings["seed"], counts], separators=(",", ":")).encode()
        seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
        return observed, canonical, seed

    def null_orders(self, tools: list[str]) -> np.ndarray:
        if not 2 <= len(tools) <= self.settings["max_session_events"]:
            raise ValueError("session exceeds permutation length bounds")
        _, canonical, seed = self.encode(tools)
        rng = np.random.default_rng(seed)
        # Each row is independently shuffled, including repeated tool codes.
        return rng.permuted(
            np.broadcast_to(canonical, (self.settings["replicates"], len(tools))), axis=1
        )

    def score(self, events: list[dict]) -> tuple[list, np.ndarray, list[dict]]:
        groups = correlate(events)
        b = self.settings["replicates"]
        if not groups:
            raise ValueError("permutation scoring requires sessions")
        if any(not 2 <= len(g) <= self.settings["max_session_events"] for g in groups.values()):
            raise ValueError("session exceeds permutation length bounds")
        if (
            sum(len(g) for g in groups.values()) * b
            > self.settings["max_permutation_cells_per_batch"]
        ):
            raise ValueError("permutation batch work limit exceeded")
        keys, scores, details = [], [], []
        for key, group in sorted(groups.items(), key=lambda item: (item[1][-1].at, item[0])):
            tools = [e.tool for e in group]
            observed, canonical, _ = self.encode(tools)
            counts = np.bincount(canonical)
            expected_scaled = int((counts * (counts - 1)).sum())
            n = len(tools)
            repeats = int((observed[:-1] == observed[1:]).sum())
            statistic = abs(n * repeats - expected_scaled)
            null = self.null_orders(tools)
            null_repeats = (null[:, :-1] == null[:, 1:]).sum(axis=1)
            null_statistics = np.abs(n * null_repeats - expected_scaled)
            exceedances = int((null_statistics >= statistic).sum())
            keys.append(key)
            scores.append(b - exceedances)
            details.append(
                {
                    "session_events": n,
                    "distinct_tools": len(counts),
                    "observed_equal_adjacent_pairs": repeats,
                    "observed_statistic": statistic,
                    "null_exceedances": exceedances,
                    "monte_carlo_p": (1 + exceedances) / (b + 1),
                    "null_statistic_min": int(null_statistics.min()),
                    "null_statistic_max": int(null_statistics.max()),
                    "sampled_null_constant": bool(np.ptp(null_statistics) == 0),
                    "all_tools_identical": len(counts) == 1,
                    "score_at_monte_carlo_ceiling": exceedances == 0,
                }
            )
        return keys, np.asarray(scores, dtype=np.int64), details


def priority_order(keys: list, seed: int) -> list[int]:
    def priority(i: int) -> tuple[str, tuple]:
        payload = json.dumps([seed, keys[i]], separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest(), keys[i]

    return sorted(range(len(keys)), key=priority)
