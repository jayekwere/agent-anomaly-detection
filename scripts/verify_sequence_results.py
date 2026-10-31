"""Validate fresh experiment artifacts and compare a replay with recorded evidence."""

import argparse
import json
import math
from pathlib import Path


DETECTORS = {"rules", "robust_distance", "isolation_forest", "markov_deviance"}
BATCHES = {"fresh_sequence", "fresh_mixed", "fresh_sequence_drift"}


def validate(path: Path) -> dict:
    result = json.loads(path.read_text())
    if result.get("schema_version") != 3 or result.get("synthetic") is not True:
        raise ValueError("incorrect sequence experiment contract")
    if set(result["tests"]) != BATCHES or set(result["thresholds"]) != DETECTORS:
        raise ValueError("missing planned comparator or batch")
    fraction = result["plan"]["review_budget"]
    for batch in result["tests"].values():
        if set(batch["models"]) != DETECTORS:
            raise ValueError("missing detector")
        n, positives = batch["sessions"], batch["positives"]
        for metrics in batch["models"].values():
            tp, fp, fn = (
                metrics[field] for field in ["true_positives", "false_positives", "false_negatives"]
            )
            if not (0 <= tp <= positives <= n and 0 <= fp <= n - positives and fn >= 0):
                raise ValueError("invalid confusion counts")
            if tp + fn != positives or tp + fp != metrics["alerts"]:
                raise ValueError("inconsistent confusion counts")
            if not metrics["alerts"] <= metrics["threshold_candidates"] <= n:
                raise ValueError("invalid threshold candidate count")
            if metrics["alerts"] > math.floor(n * fraction):
                raise ValueError("review cap exceeded")
            expected = {
                "precision": tp / max(1, tp + fp),
                "recall": tp / max(1, positives),
                "false_alerts_per_1000_sessions": fp * 1000 / n,
            }
            for field, value in expected.items():
                if not math.isclose(metrics[field], value, abs_tol=1e-12):
                    raise ValueError("inconsistent calculated metric")
            for field in ["precision", "recall", "average_precision", "roc_auc"]:
                if not math.isfinite(metrics[field]) or not 0 <= metrics[field] <= 1:
                    raise ValueError("invalid ranking or operating metric")
            for grouping in ["by_population", "by_scenario"]:
                for field in ["true_positives", "false_positives", "false_negatives", "alerts"]:
                    if sum(m[field] for m in metrics[grouping].values()) != metrics[field]:
                        raise ValueError("subgroup counts do not reconcile")
    return result


def compare(expected: object, actual: object, path: str = "root") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError("artifact keys differ")
        for key in expected:
            compare(expected[key], actual[key], path + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError("artifact lengths differ")
        for i, (a, b) in enumerate(zip(expected, actual)):
            compare(a, b, path + "/" + str(i))
    elif isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not math.isclose(
            expected, actual, abs_tol=1e-12, rel_tol=1e-12
        ):
            raise ValueError(
                f"artifact numbers differ at {path}: expected {expected}, actual {actual}"
            )
    elif expected != actual:
        raise ValueError("artifact values differ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    actual = validate(args.actual)
    if args.reference:
        expected = validate(args.reference)
        # Python versions legitimately differ; dependency versions must match.
        expected["environment"].pop("python")
        actual["environment"].pop("python")
        compare(expected, actual)
    print("Sequence artifact invariants and requested reference comparison passed.")


if __name__ == "__main__":
    main()
