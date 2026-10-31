"""Shared-budget and reader-miss invariants for the combined experiment."""

import argparse
import json
import math
from pathlib import Path

# Also support direct execution as `python scripts/verify_combined_results.py`.
try:
    from scripts.verify_sequence_results import compare_replay
except ModuleNotFoundError:
    from verify_sequence_results import compare_replay

COMBINED = "rules_plus_sequence"
DETECTORS = {"rules", "robust_distance", "isolation_forest", "markov_deviance", COMBINED}
BATCHES = {"fresh_joint", "fresh_sequence_control", "fresh_nonsequence_control"}


def validate(path: Path) -> dict:
    return validate_data(json.loads(path.read_text()))


def validate_data(
    result: dict, detectors: set = DETECTORS, batches: set = BATCHES, schema_version: int = 4
) -> dict:
    if (
        result.get("schema_version") != schema_version
        or result.get("synthetic") is not True
        or set(result["tests"]) != batches
    ):
        raise ValueError("invalid combined experiment contract")
    fraction = result["plan"]["review_budget"]
    for batch in result["tests"].values():
        if set(batch["models"]) != detectors:
            raise ValueError("missing comparator")
        n, positives = batch["sessions"], batch["positives"]
        cap = math.floor(n * fraction)
        for m in batch["models"].values():
            tp, fp, fn = (m[k] for k in ["true_positives", "false_positives", "false_negatives"])
            if (
                min(tp, fp, fn) < 0
                or tp + fn != positives
                or tp + fp != m["alerts"]
                or fp > n - positives
            ):
                raise ValueError("invalid confusion counts")
            if not m["alerts"] <= m["threshold_candidates"] <= n or m["alerts"] > cap:
                raise ValueError("shared budget or threshold count invalid")
            for field, value in {
                "precision": tp / max(1, tp + fp),
                "recall": tp / max(1, positives),
                "false_alerts_per_1000_sessions": fp * 1000 / n,
            }.items():
                if not math.isclose(m[field], value, abs_tol=1e-12):
                    raise ValueError("inconsistent operating metric")
            for field in ["average_precision", "roc_auc"]:
                if not math.isfinite(m[field]) or not 0 <= m[field] <= 1:
                    raise ValueError("invalid ranking metric")
            for grouping in ["by_population", "by_scenario"]:
                for field in ["alerts", "true_positives", "false_positives", "false_negatives"]:
                    if sum(g[field] for g in m[grouping].values()) != m[field]:
                        raise ValueError("subgroup counts do not reconcile")
            r = m["reader_sequence"]
            if min(r["detected"], r["missed"]) < 0 or r["detected"] + r["missed"] != r["positives"]:
                raise ValueError("reader sequence misses do not reconcile")
            if r["positives"] > positives or r["detected"] > tp:
                raise ValueError("reader sequence count exceeds all positives")
            if r["positives"] == 0:
                if r["recall"] is not None:
                    raise ValueError("reader recall requires positives")
            elif not math.isclose(r["recall"], r["detected"] / r["positives"], abs_tol=1e-12):
                raise ValueError("invalid reader recall")
            full = m["full_budget_review"]
            if full["alerts"] != cap or full["true_positives"] + full["false_positives"] != cap:
                raise ValueError("full-budget review does not reconcile")
            if full["reader_sequence_detected"] + full["reader_sequence_missed"] != r["positives"]:
                raise ValueError("full-budget reader misses do not reconcile")
            for field in ["alerts", "true_positives", "false_positives"]:
                if sum(g[field] for g in full["by_scenario"].values()) != full[field]:
                    raise ValueError("full-budget scenario counts do not reconcile")
        q, combined = batch["shared_queue"], batch["models"][COMBINED]
        if q["unique_alerts"] != combined["alerts"] or q["cap_sessions"] != cap:
            raise ValueError("shared queue count does not match detector")
        if q["combined_threshold_candidates"] != combined["threshold_candidates"]:
            raise ValueError("candidate counts do not match detector")
        if (
            q["component_candidate_union"] - q["combined_threshold_candidates"]
            != q["excluded_by_combined_threshold"]
        ):
            raise ValueError("combined threshold exclusions do not reconcile")
        if q["combined_threshold_candidates"] - q["unique_alerts"] != q["suppressed_by_shared_cap"]:
            raise ValueError("shared cap suppression does not reconcile")
        for field in ["alerts", "true_positives", "false_positives"]:
            if sum(c[field] for c in q["dominance"].values()) != combined[field]:
                raise ValueError("shared signal dominance does not reconcile")
        for name, change in batch["alert_changes"].items():
            reference = batch["models"][name]
            for field in ["alerts", "true_positives", "false_positives"]:
                if (
                    combined[field] - reference[field]
                    != change["gained"][field] - change["lost"][field]
                ):
                    raise ValueError("gained/lost alerts do not reconcile")
            if (
                combined["reader_sequence"]["detected"] - reference["reader_sequence"]["detected"]
                != change["reader_sequence_gained"] - change["reader_sequence_lost"]
            ):
                raise ValueError("reader gains/losses do not reconcile")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    actual = validate(args.actual)
    if args.reference:
        compare_replay(validate(args.reference), actual)
    print("Combined shared-budget, reader-miss and requested reference checks passed.")


if __name__ == "__main__":
    main()
