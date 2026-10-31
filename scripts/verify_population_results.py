"""Validate population calibration support, tenant boundaries and shared-budget accounting."""

import argparse
import json
import math
from pathlib import Path

try:
    from scripts.verify_combined_results import validate_data, DETECTORS
    from scripts.verify_sequence_results import compare_replay
except ModuleNotFoundError:
    from verify_combined_results import validate_data, DETECTORS
    from verify_sequence_results import compare_replay

POPULATION = "population_rules_plus_sequence"
BATCHES = {"fresh_population_joint", "fresh_population_sequence", "fresh_population_nonsequence"}


def validate(path: Path) -> dict:
    result = validate_data(json.loads(path.read_text()), DETECTORS | {POPULATION}, BATCHES, 5)
    settings = result["plan"]["population_calibration"]
    minimum = settings["minimum_validation_sessions"]
    parameters = result["parameters"]["population"]
    for p in parameters["profiles"]:
        if not all(
            math.isfinite(p[k]) and 0 <= p[k] <= 1 for k in ["read_fraction", "export_fraction"]
        ):
            raise ValueError("invalid training profile proportions")
        expected = (
            "read_dominant"
            if p["read_fraction"] >= settings["read_dominant_min_fraction"]
            else (
                "export_heavy"
                if p["export_fraction"] >= settings["export_heavy_min_fraction"]
                else "other"
            )
        )
        if p["group"] != expected:
            raise ValueError("profile contradicts training proportions")
    for r in parameters["references"]:
        if r["source"][0] != r["tenant"] or r["reference_sessions"] < minimum:
            raise ValueError("cross-tenant or insufficient calibration reference")
        if r["mode"] == "local":
            if (
                r["validation_sessions"] < minimum
                or r["source"][1] != r["group"]
                or r["reason"] is not None
            ):
                raise ValueError("invalid local calibration support")
        elif r["mode"] != "same_tenant_fallback" or r["source"][1] != "__tenant__":
            raise ValueError("invalid fallback reference")
        c = r["calibration"]
        values = [c["threshold"], *c["component_scales"].values()]
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("invalid calibration scale")
    for batch in result["tests"].values():
        model, q = batch["models"][POPULATION], batch["population_queue"]
        if q["unique_alerts"] != model["alerts"] or q["unique_alerts"] > q["cap_sessions"]:
            raise ValueError("population queue exceeds shared cap")
        if (
            q["candidates"] != model["threshold_candidates"]
            or q["candidates"] - q["unique_alerts"] != q["suppressed_by_shared_cap"]
        ):
            raise ValueError("population candidate suppression does not reconcile")
        for field, value in {
            "sessions": batch["sessions"],
            "positives": batch["positives"],
            "candidates": q["candidates"],
            "alerts": model["alerts"],
            "true_positives": model["true_positives"],
            "false_positives": model["false_positives"],
            "misses": model["false_negatives"],
        }.items():
            if sum(g[field] for g in q["groups"].values()) != value:
                raise ValueError("population group allocation does not reconcile")
        fallback = sum(
            g["sessions"]
            for g in q["groups"].values()
            if g["calibration_mode"] == "same_tenant_fallback"
        )
        if fallback != q["fallback_sessions"]:
            raise ValueError("fallback accounting does not reconcile")
        for reference, modes in batch["population_alert_changes"].items():
            for mode, change in modes.items():
                current = model if mode == "calibrated" else model["full_budget_review"]
                old = batch["models"][reference]
                old = old if mode == "calibrated" else old["full_budget_review"]
                for field in ["alerts", "true_positives", "false_positives"]:
                    if (
                        current[field] - old[field]
                        != change["gained"][field] - change["lost"][field]
                    ):
                        raise ValueError("population gained/lost accounting mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    actual = validate(args.actual)
    if args.reference:
        compare_replay(validate(args.reference), actual)
    print(
        "Population support, tenant isolation, shared-cap, reader accounting and reference checks passed."
    )


if __name__ == "__main__":
    main()
