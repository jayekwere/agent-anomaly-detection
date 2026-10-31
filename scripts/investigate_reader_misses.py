"""Reproduce diagnosis on the already inspected combined-v1 evidence, never fresh holdouts."""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from agent_anomaly import correlate
from agent_anomaly.combined_experiment import CombinedComparison, DEFAULT_PLAN, make_batch
from agent_anomaly.data import generate
from agent_anomaly.sequence_experiment import digest


def investigate() -> dict:
    plan = json.loads(DEFAULT_PLAN.read_text())
    train, train_truth = generate(**plan["training"])
    validation, validation_truth = generate(**plan["validation"])
    model = CombinedComparison().fit(train, validation, plan)
    keys, validation_scores, _ = model.score(validation)
    historical, truth = make_batch(plan["test_batches"][0])
    old_keys, old_scores, old_decisions = model.score(historical)
    pairs, outgoing, vocab, populations = {}, {}, {}, {}
    for key, group in correlate(train).items():
        scope = key[:2]
        tools = [e.tool for e in group]
        pairs.setdefault(scope, Counter()).update(zip(tools, tools[1:]))
        outgoing.setdefault(scope, Counter()).update(tools[:-1])
        vocab.setdefault(scope, set()).update(tools)
        populations[scope] = train_truth[key]["population"]
    result = {
        "synthetic": True,
        "historical_experiment": "combined-v1/fresh_joint",
        "purpose": "Post-hoc diagnosis on previously inspected evidence; annotations only aggregate outputs, never fit/calibrate the detector.",
        "training_events_sha256": digest(train),
        "validation_events_sha256": digest(validation),
        "historical_events_sha256": digest(historical),
        "global_fusion": model.fusion.parameters(),
        "populations": {},
    }
    for population in ["reader", "operator", "batch"]:
        mask = np.array([validation_truth[k]["population"] == population for k in keys])
        old_mask = np.array(
            [
                truth[k]["population"] == population and truth[k]["scenario"] == "sequence_shift"
                for k in old_keys
            ]
        )
        seq = old_scores["markov_deviance"][old_mask]
        read_probabilities = [
            (pairs[scope][("case.read", "case.read")] + 1)
            / (outgoing[scope]["case.read"] + len(vocab[scope]) + 1)
            for scope in populations
            if populations[scope] == population
        ]
        result["populations"][population] = {
            "validation_sessions": int(mask.sum()),
            "validation_sequence_score_median": float(
                np.median(validation_scores["markov_deviance"][mask])
            ),
            "validation_sequence_score_q98": float(
                np.quantile(validation_scores["markov_deviance"][mask], 0.98, method="higher")
            ),
            "training_median_probability_read_after_read": float(np.median(read_probabilities)),
            "historical_sequence_anomalies": int(old_mask.sum()),
            "historical_sequence_score_min_median_max": [
                float(seq.min()),
                float(np.median(seq)),
                float(seq.max()),
            ],
            "historical_combined_detections": int(
                old_decisions["rules_plus_sequence"][old_mask].sum()
            ),
        }
    result["validation_reader_tenant_tails"] = {}
    for tenant in sorted({key[0] for key in keys}):
        mask = np.array(
            [key[0] == tenant and validation_truth[key]["population"] == "reader" for key in keys]
        )
        threshold = float(
            np.quantile(validation_scores["markov_deviance"][mask], 0.98, method="higher")
        )
        tail = mask & (validation_scores["markov_deviance"] >= threshold)
        result["validation_reader_tenant_tails"][tenant] = {
            "sessions": int(mask.sum()),
            "sequence_q98": threshold,
            "at_or_above_q98_scenarios": dict(
                Counter(validation_truth[keys[i]]["scenario"] for i in np.flatnonzero(tail))
            ),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/reader-investigation.json"))
    args = parser.parse_args()
    result = investigate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["populations"], indent=2))


if __name__ == "__main__":
    main()
