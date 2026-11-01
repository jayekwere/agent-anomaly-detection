"""Validate finite permutation evidence, shared-budget ties and reader recovery accounting."""

import argparse
import json
import math
from pathlib import Path

try:
    from scripts.verify_sequence_results import compare_replay
except ModuleNotFoundError:
    from verify_sequence_results import compare_replay

PERMUTATION = "conditional_permutation"
DETECTORS = {
    "rules",
    "robust_distance",
    "isolation_forest",
    "markov_deviance",
    "rules_plus_sequence",
    "population_rules_plus_sequence",
    PERMUTATION,
}
BATCHES = {"fresh_permutation_joint", "fresh_permutation_sequence", "fresh_permutation_nonsequence"}


def validate(path: Path) -> dict:
    r = json.loads(path.read_text())
    if r.get("schema_version") != 6 or r.get("synthetic") is not True or set(r["tests"]) != BATCHES:
        raise ValueError("invalid permutation experiment contract")
    b = r["plan"]["permutation"]["replicates"]
    threshold = r["parameters"]["thresholds"][PERMUTATION]
    if not 0 <= threshold <= b:
        raise ValueError("invalid permutation calibration threshold")
    for batch in r["tests"].values():
        n, positives = batch["sessions"], batch["positives"]
        cap = math.floor(n * r["plan"]["review_budget"])
        if set(batch["models"]) != DETECTORS:
            raise ValueError("missing permutation comparator")
        for m in batch["models"].values():
            tp, fp, fn = (
                m[field] for field in ["true_positives", "false_positives", "false_negatives"]
            )
            if (
                min(tp, fp, fn) < 0
                or tp + fn != positives
                or tp + fp != m["alerts"]
                or fp > n - positives
            ):
                raise ValueError("inconsistent confusion counts")
            if not m["alerts"] <= m["threshold_candidates"] <= n or m["alerts"] != min(
                cap, m["threshold_candidates"]
            ):
                raise ValueError("shared review cap does not reconcile")
            for field, value in {
                "precision": tp / max(1, tp + fp),
                "recall": tp / max(1, positives),
                "false_alerts_per_1000_sessions": fp * 1000 / n,
            }.items():
                if not math.isclose(m[field], value, abs_tol=1e-12):
                    raise ValueError("incorrect operating metric")
            for field in ["average_precision", "roc_auc"]:
                if not math.isfinite(m[field]) or not 0 <= m[field] <= 1:
                    raise ValueError("invalid ranking metric")
            for grouping in ["by_population", "by_scenario"]:
                for field in ["alerts", "true_positives", "false_positives", "false_negatives"]:
                    if sum(g[field] for g in m[grouping].values()) != m[field]:
                        raise ValueError("subgroup accounting does not reconcile")
            reader = m["reader_sequence"]
            if (
                min(reader["detected"], reader["missed"]) < 0
                or reader["detected"] + reader["missed"] != reader["positives"]
                or reader["detected"] > tp
            ):
                raise ValueError("reader recovery does not reconcile")
            full = m["full_budget_review"]
            if full["alerts"] != cap or full["true_positives"] + full["false_positives"] != cap:
                raise ValueError("full-budget workload does not reconcile")
            if (
                full["reader_sequence_detected"] + full["reader_sequence_missed"]
                != reader["positives"]
            ):
                raise ValueError("full-budget reader accounting does not reconcile")
        m, q = batch["models"][PERMUTATION], batch["shared_queue"]
        if (
            q["cap_sessions"] != cap
            or q["unique_alerts"] != m["alerts"]
            or q["candidates"] != m["threshold_candidates"]
            or q["suppressed_by_cap"] != q["candidates"] - m["alerts"]
        ):
            raise ValueError("permutation queue does not reconcile")
        if not 0 <= q["boundary_ties_selected"] <= q["boundary_candidate_ties"] <= q["candidates"]:
            raise ValueError("invalid boundary-tie accounting")
        evidence = batch["reader_sequence_evidence"]
        if (
            len(evidence) != m["reader_sequence"]["positives"]
            or sum(e["alert"] for e in evidence) != m["reader_sequence"]["detected"]
        ):
            raise ValueError("reader evidence does not reconcile")
        if len({e["synthetic_session"] for e in evidence}) != len(evidence):
            raise ValueError("duplicate reader evidence")
        for e in evidence:
            if not 0 <= e["null_exceedances"] <= b or e["score"] != b - e["null_exceedances"]:
                raise ValueError("invalid Monte Carlo exceedance count")
            if not math.isclose(
                e["monte_carlo_p"], (1 + e["null_exceedances"]) / (b + 1), abs_tol=1e-12
            ):
                raise ValueError("invalid Monte Carlo p value")
            if e["alert"] and e["score"] <= threshold:
                raise ValueError("reader below threshold was alerted")
            if e["reason"] == "shared_cap_or_boundary_tie" and e["score"] <= threshold:
                raise ValueError("incorrect reader suppression reason")
            if e["all_tools_identical"] and (e["score"] != 0 or e["monte_carlo_p"] != 1):
                raise ValueError("constant-tool ordering evidence is invalid")
        for ref, modes in batch["alert_changes"].items():
            for mode, change in modes.items():
                current = m if mode == "calibrated" else m["full_budget_review"]
                old = batch["models"][ref]
                old = old if mode == "calibrated" else old["full_budget_review"]
                for field in ["alerts", "true_positives", "false_positives"]:
                    if (
                        current[field] - old[field]
                        != change["gained"][field] - change["lost"][field]
                    ):
                        raise ValueError("gained/lost alerts do not reconcile")
    return r


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    actual = validate(args.actual)
    if args.reference:
        compare_replay(validate(args.reference), actual)
    print("Permutation reader evidence, finite draws, shared queue and reference checks passed.")


if __name__ == "__main__":
    main()
