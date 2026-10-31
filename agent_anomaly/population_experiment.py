"""Fresh shared-budget evaluation of training-derived population calibration."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np

from . import correlate
from .combined_experiment import (
    COMBINED,
    CombinedComparison,
    counts,
    evaluate_batch,
    make_batch,
    paired_differences,
)
from .data import generate
from .detectors import budget
from .population import PopulationCalibration
from .sequence_experiment import chronological_check, digest

DEFAULT_PLAN = Path(__file__).resolve().parent / "plans/population-v1.json"
POPULATION = "population_rules_plus_sequence"


class PopulationComparison:
    def fit(self, train: list[dict], validation: list[dict], plan: dict) -> "PopulationComparison":
        self.global_model = CombinedComparison().fit(train, validation, plan)
        keys, scores, _ = self.global_model.score(validation)
        self.population = PopulationCalibration().fit(
            train, keys, scores, plan["population_calibration"], plan["calibration"]["quantile"]
        )
        self.thresholds = {**self.global_model.thresholds, POPULATION: 1.0}
        self.fusion = self.global_model.fusion
        self.review_budget = plan["review_budget"]
        self.frozen_state = digest(self.parameters())
        return self

    def parameters(self) -> dict:
        return {
            "global": self.global_model.parameters(),
            "population": self.population.parameters(),
            "thresholds": self.thresholds,
            "review_budget": self.review_budget,
        }

    def score(self, events: list[dict]) -> tuple[list, dict, dict]:
        keys, scores, decisions = self.global_model.score(events)
        scores[POPULATION], _, _ = self.population.score(keys, scores)
        decisions[POPULATION] = self.population.alerts(scores[POPULATION], self.review_budget)
        if digest(self.parameters()) != self.frozen_state:
            raise ValueError("population inference changed frozen reference state")
        return keys, scores, decisions


def evaluate_population(
    model: PopulationComparison, events: list[dict], truth: dict, settings: dict
) -> dict:
    # Reuse the original metric/accounting implementation for all six comparators.
    result = evaluate_batch(model, events, truth, settings)
    keys, scores, decisions = model.score(events)
    labels = np.array([truth[k]["label"] for k in keys])
    selected = decisions[POPULATION]
    reader = np.array(
        [
            truth[k]["population"] == "reader" and truth[k]["scenario"] == "sequence_shift"
            for k in keys
        ]
    )
    _, groups, modes = model.population.score(keys, scores)
    result["population_queue"] = {
        "cap_sessions": int(len(keys) * model.review_budget),
        "unique_alerts": int(selected.sum()),
        "candidates": int((scores[POPULATION] > 1).sum()),
        "suppressed_by_shared_cap": int((scores[POPULATION] > 1).sum() - selected.sum()),
        "fallback_sessions": modes.count("same_tenant_fallback"),
        "groups": {},
    }
    for group in sorted(set(groups)):
        mask = np.array([g == group for g in groups])
        reference = model.population.references[group]
        result["population_queue"]["groups"]["/".join(group)] = {
            "sessions": int(mask.sum()),
            "positives": int(labels[mask].sum()),
            "candidates": int(((scores[POPULATION] > 1) & mask).sum()),
            **counts(selected & mask, labels),
            "misses": int((labels.astype(bool) & mask & ~selected).sum()),
            "calibration_mode": reference["mode"],
            "validation_sessions": reference["validation_sessions"],
        }
    result["population_alert_changes"] = {}
    ranked = budget(scores[POPULATION], model.review_budget)
    for name in [COMBINED, "rules", "markov_deviance"]:
        reference_ranked = budget(scores[name], model.review_budget)
        result["population_alert_changes"][name] = {}
        for mode, current, reference in [
            ("calibrated", selected, decisions[name]),
            ("full_budget", ranked, reference_ranked),
        ]:
            gained, lost = current & ~reference, reference & ~current
            result["population_alert_changes"][name][mode] = {
                "gained": counts(gained, labels),
                "lost": counts(lost, labels),
                "reader_sequence_gained": int((gained & reader).sum()),
                "reader_sequence_lost": int((lost & reader).sum()),
            }
    # Reuse the paired cluster engine, explicitly rename its target and reference.
    aliases = {
        COMBINED: selected,
        "global_combined": decisions[COMBINED],
        **{k: v for k, v in decisions.items() if k not in [COMBINED, POPULATION]},
    }
    result["population_paired_recall_comparisons"] = {
        name: {
            "population_minus_reference_recall": value["combined_minus_reference_recall"],
            "cluster_bootstrap_95_interval": value["cluster_bootstrap_95_interval"],
        }
        for name, value in paired_differences(keys, labels, aliases, settings).items()
    }
    ranks = np.empty(len(keys), dtype=int)
    ranks[np.argsort(-scores[POPULATION], kind="stable")] = np.arange(1, len(keys) + 1)
    result["population_reader_examples"] = []
    for status, mask in [("detected", reader & selected), ("missed", reader & ~selected)]:
        for i in np.flatnonzero(mask)[:5]:
            result["population_reader_examples"].append(
                {
                    "status": status,
                    "synthetic_session": keys[i][2],
                    "training_derived_group": groups[i][1],
                    "sequence_score": float(scores["markov_deviance"][i]),
                    "global_score": float(scores[COMBINED][i]),
                    "population_score": float(scores[POPULATION][i]),
                    "population_threshold": 1.0,
                    "global_rank_population_score": int(ranks[i]),
                    "reason": "alert"
                    if selected[i]
                    else (
                        "shared_cap_suppression"
                        if scores[POPULATION][i] > 1
                        else "below_group_calibrated_threshold"
                    ),
                    "global_combined_alert": bool(decisions[COMBINED][i]),
                }
            )
    return result


def run(output: Path, plan_path: Path = DEFAULT_PLAN) -> dict:
    plan = json.loads(plan_path.read_text())
    train, _ = generate(**plan["training"])
    validation, _ = generate(**plan["validation"])
    model = PopulationComparison().fit(train, validation, plan)
    # Frozen groups and validation references precede any fresh test generation.
    result = {
        "schema_version": 5,
        "synthetic": True,
        "plan": plan,
        "plan_sha256": digest(plan),
        "parameters": copy.deepcopy(model.parameters()),
        "training_events_sha256": digest(train),
        "validation_events_sha256": digest(validation),
        "source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "environment": {
            "python": platform.python_version(),
            **{p: importlib.metadata.version(p) for p in ["numpy", "scikit-learn"]},
        },
        "tests": {},
    }
    seen = set(correlate(train)) | set(correlate(validation))
    for batch in plan["test_batches"]:
        events, truth = make_batch(batch)
        chronological_check(train, validation, events)
        keys = set(correlate(events))
        if keys & seen:
            raise ValueError("population experiment partitions overlap")
        seen.update(keys)
        result["tests"][batch["name"]] = evaluate_population(
            model, events, truth, plan["paired_uncertainty"]
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "report.md").write_text(report(result))
    print(report(result).split("## Queues")[0])
    return result


def report(result: dict) -> str:
    lines = [
        "# Population-aware calibration: one shared queue",
        "",
        "Training-derived tool-use strata and same-tenant validation references; no ground-truth population is used by the detector. "
        "All candidates compete for one 2% global cap. This is a targeted synthetic follow-up.",
        "",
        "| Fresh batch | Detector | AP | TP | FP | Recall | Alerts | Reader-sequence detected / total | Equal-budget reader detected |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for batch, entry in result["tests"].items():
        for name, m in entry["models"].items():
            r = m["reader_sequence"]
            lines.append(
                f"| {batch} | {name} | {m['average_precision']:.3f} | {m['true_positives']} | {m['false_positives']} | {m['recall']:.3f} | {m['alerts']} | {r['detected']} / {r['positives']} | {m['full_budget_review']['reader_sequence_detected']} |"
            )
    lines += ["", "## Queues, reader misses and displacement", ""]
    for batch, entry in result["tests"].items():
        queue = entry["population_queue"]
        lines += [
            f"### {batch}",
            "",
            f"Shared cap {queue['cap_sessions']}; candidates {queue['candidates']}; alerts {queue['unique_alerts']}; cap-suppressed {queue['suppressed_by_shared_cap']}; fallback sessions {queue['fallback_sessions']}.",
            "",
            "| Tenant / training-derived group | Sessions | Positives | Candidates | Alerts | TP | FP | Misses |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for group, m in queue["groups"].items():
            lines.append(
                f"| {group} | {m['sessions']} | {m['positives']} | {m['candidates']} | {m['alerts']} | {m['true_positives']} | {m['false_positives']} | {m['misses']} |"
            )
        lines += [
            "",
            "Exactly-full-budget results ignore thresholds and use one global top-24 ranking:",
            "",
            "| Detector | TP | FP | Reader-sequence detected | Reader-sequence missed |",
            "|---|---:|---:|---:|---:|",
        ]
        for name in ["rules", "markov_deviance", COMBINED, POPULATION]:
            f = entry["models"][name]["full_budget_review"]
            lines.append(
                f"| {name} | {f['true_positives']} | {f['false_positives']} | {f['reader_sequence_detected']} | {f['reader_sequence_missed']} |"
            )
        lines += [""]
        for reference, modes in entry["population_alert_changes"].items():
            for mode, change in modes.items():
                gained, lost = change["gained"], change["lost"]
                lines.append(
                    f"- {mode} versus {reference}: gain {gained['true_positives']} true / {gained['false_positives']} false; lose {lost['true_positives']} true / {lost['false_positives']} false. Reader-sequence gains/losses {change['reader_sequence_gained']}/{change['reader_sequence_lost']}."
                )
        for reference, c in entry["population_paired_recall_comparisons"].items():
            lines.append(
                f"- Population minus {reference} recall: {c['population_minus_reference_recall']:+.3f}; paired actor-cluster 95% interval {c['cluster_bootstrap_95_interval']}."
            )
        lines += [""]
        for e in entry["population_reader_examples"]:
            lines.append(
                f"- Reader-sequence {e['synthetic_session']}: {e['status']}, {e['reason']}; group {e['training_derived_group']}, raw sequence score {e['sequence_score']:.3f}, calibrated score {e['population_score']:.3f}, global rank {e['global_rank_population_score']}."
            )
        lines += [""]
    lines += [
        "## Limits and leakage boundaries",
        "",
        *["- " + item for item in result["plan"]["limitations"]],
        "- Validation and test group assignment is a frozen lookup by tenant/actor into training-only profiles; actor names and evaluation population labels are never parsed.",
        "- Sparse/zero-scale strata use only their own tenant validation pool; unsupported actors/tenants reject explicitly. Fallback mode and support counts are published.",
        "- Group thresholds select candidates; they do not allocate independent alert budgets or reserve review slots for readers.",
        "- Annotated population/scenario labels are used only for evaluation breakdowns after alert decisions. No policy or seed is retuned after results.",
        "- Scores are relative deviations, not attack probabilities. The general reference remains unchanged.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/population"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
