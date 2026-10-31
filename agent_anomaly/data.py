"""Overlapping synthetic populations with independent scenario ground truth."""

from datetime import UTC, datetime, timedelta

import numpy as np

TOOLS = ("case.read", "case.list", "case.write", "evidence.export", "admin.delete")
SCENARIOS = ("benign", "denial_probe", "export_burst", "frequency_shift", "sequence_shift")


def generate(
    seed: int,
    day: int,
    count: int = 1200,
    contamination: float = 0.05,
    unseen: bool = False,
    drift: bool = False,
) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(seed)
    events, truth = [], {}
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)
    for i in range(count):
        population = str(rng.choice(["reader", "operator", "batch"]))
        scenario = "benign"
        if rng.random() < contamination:
            scenario = "sequence_shift" if unseen else str(rng.choice(SCENARIOS[1:4]))
        key = ("synthetic-" + str(i % 2), population + "-" + str(i % 12), f"{day}-{i}")
        truth[key] = {
            "label": int(scenario != "benign"),
            "scenario": scenario,
            "population": population,
        }
        n = int(rng.integers(10, 40))
        weights = {
            "reader": [0.65, 0.25, 0.06, 0.03, 0.01],
            "operator": [0.3, 0.2, 0.3, 0.15, 0.05],
            "batch": [0.25, 0.2, 0.1, 0.4, 0.05],
        }[population]
        tools = rng.choice(TOOLS, n, p=weights).tolist()
        spacing = float(rng.uniform(0.5, 5)) * (0.6 if drift else 1)
        denial = float(rng.beta(1, 30))
        if scenario == "denial_probe":
            denial = float(rng.uniform(0.15, 0.6))
        if scenario == "export_burst":
            tools = rng.choice(TOOLS, n, p=[0.2, 0.1, 0.1, 0.55, 0.05]).tolist()
        if scenario == "frequency_shift":
            spacing *= 0.2
        if scenario == "sequence_shift":
            tools = sorted(tools)
        for j, tool in enumerate(tools):
            at = start + timedelta(seconds=i * 60 + j * spacing)
            events.append(
                dict(
                    schema_version=1,
                    tenant=key[0],
                    actor=key[1],
                    session=key[2],
                    event_id=f"{day}-{i}-{j}",
                    at=at.isoformat(),
                    tool=tool,
                    outcome="denied" if rng.random() < denial else "allowed",
                )
            )
    return events, truth
