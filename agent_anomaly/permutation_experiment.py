"""Predeclared count-preserving permutation evaluation with a single shared queue."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np

from . import correlate
from .combined_experiment import COMBINED, counts, make_batch, paired_differences
from .data import generate
from .detectors import budget
from .evaluation import measure
from .permutation import ConditionalPermutation, priority_order
from .population_experiment import POPULATION, PopulationComparison
from .sequence_experiment import chronological_check, digest

DEFAULT_PLAN = Path(__file__).resolve().parent / "plans/permutation-v1.json"
PERMUTATION = "conditional_permutation"


class PermutationComparison:
    def fit(self, train: list[dict], validation: list[dict], plan: dict) -> "PermutationComparison":
        self.base = PopulationComparison().fit(train, validation, plan)
        self.permutation = ConditionalPermutation(plan["permutation"])
        self.tie_seed = plan["tie_policy"]["seed"]
        self.review_budget = plan["review_budget"]
        _, validation_scores, _ = self.permutation.score(validation)
        self.thresholds = {
            **self.base.thresholds,
            PERMUTATION: float(
                np.quantile(validation_scores, plan["calibration"]["quantile"], method="higher")
            ),
        }
        self.frozen_state = digest(self.parameters())
        return self

    def parameters(self) -> dict:
        return {
            "base": self.base.parameters(),
            "permutation": dict(self.permutation.settings),
            "thresholds": dict(self.thresholds),
            "tie_seed": self.tie_seed,
            "review_budget": self.review_budget,
        }

    def score(self, events: list[dict]) -> tuple[list, dict, dict, list]:
        keys, scores, _ = self.base.score(events)
        permutation_keys, values, details = self.permutation.score(events)
        lookup = {key: i for i, key in enumerate(permutation_keys)}
        if set(keys) != set(permutation_keys):
            raise ValueError("permutation session alignment mismatch")
        scores[PERMUTATION] = np.array([values[lookup[key]] for key in keys])
        order = priority_order(keys, self.tie_seed)
        aligned_details = [details[lookup[keys[i]]] for i in order]
        keys = [keys[i] for i in order]
        scores = {name: value[order] for name, value in scores.items()}
        decisions = {}
        for name, value in scores.items():
            candidates = value > self.thresholds[name]
            decisions[name] = candidates & budget(
                np.where(candidates, value, -1e10), self.review_budget
            )
        if digest(self.parameters()) != self.frozen_state:
            raise ValueError("permutation inference changed frozen state")
        return keys, scores, decisions, aligned_details


def evaluate(model: PermutationComparison, events: list[dict], truth: dict, settings: dict) -> dict:
    keys, scores, decisions, details = model.score(events)
    labels = np.array([truth[key]["label"] for key in keys])
    reader = np.array(
        [
            truth[key]["population"] == "reader" and truth[key]["scenario"] == "sequence_shift"
            for key in keys
        ]
    )
    cap = int(len(keys) * model.review_budget)
    result = {
        "sessions": len(keys),
        "positives": int(labels.sum()),
        "events_sha256": digest(events),
        "models": {},
    }
    for name, value in scores.items():
        selected = decisions[name]
        ranked = budget(value, model.review_budget)
        m = measure(labels, value, selected)
        m["threshold_candidates"] = int((value > model.thresholds[name]).sum())
        m["reader_sequence"] = {
            "positives": int(reader.sum()),
            "detected": int((reader & selected).sum()),
            "missed": int((reader & ~selected).sum()),
        }
        m["full_budget_review"] = {
            **counts(ranked, labels),
            "reader_sequence_detected": int((reader & ranked).sum()),
            "reader_sequence_missed": int((reader & ~ranked).sum()),
        }
        for field in ["population", "scenario"]:
            m["by_" + field] = {}
            for group in sorted({truth[k][field] for k in keys}):
                mask = np.array([truth[key][field] == group for key in keys])
                m["by_" + field][group] = measure(labels[mask], value[mask], selected[mask])
        result["models"][name] = m
    selected, value = decisions[PERMUTATION], scores[PERMUTATION]
    candidates = value > model.thresholds[PERMUTATION]
    boundary = None
    if selected.any():
        boundary = int(value[selected].min())
    result["shared_queue"] = {
        "cap_sessions": cap,
        "unique_alerts": int(selected.sum()),
        "candidates": int(candidates.sum()),
        "suppressed_by_cap": int(candidates.sum() - selected.sum()),
        "selected_boundary_score": boundary,
        "boundary_candidate_ties": int((candidates & (value == boundary)).sum())
        if boundary is not None
        else 0,
        "boundary_ties_selected": int((selected & (value == boundary)).sum())
        if boundary is not None
        else 0,
        "score_ceiling_sessions": sum(d["score_at_monte_carlo_ceiling"] for d in details),
        "all_tools_identical_sessions": sum(d["all_tools_identical"] for d in details),
        "sampled_null_constant_sessions": sum(d["sampled_null_constant"] for d in details),
    }
    result["alert_changes"] = {}
    for name in ["rules", "markov_deviance", COMBINED, POPULATION]:
        result["alert_changes"][name] = {}
        for mode, current, reference in [
            ("calibrated", selected, decisions[name]),
            (
                "full_budget",
                budget(value, model.review_budget),
                budget(scores[name], model.review_budget),
            ),
        ]:
            gained, lost = current & ~reference, reference & ~current
            result["alert_changes"][name][mode] = {
                "gained": counts(gained, labels),
                "lost": counts(lost, labels),
                "reader_sequence_gained": int((reader & gained).sum()),
                "reader_sequence_lost": int((reader & lost).sum()),
            }
    aliases = {
        COMBINED: selected,
        "global_combined": decisions[COMBINED],
        **{k: v for k, v in decisions.items() if k not in [COMBINED, PERMUTATION]},
    }
    result["paired_recall_comparisons"] = {
        name: {
            "permutation_minus_reference_recall": c["combined_minus_reference_recall"],
            "cluster_bootstrap_95_interval": c["cluster_bootstrap_95_interval"],
        }
        for name, c in paired_differences(keys, labels, aliases, settings).items()
    }
    ranks = np.empty(len(keys), dtype=int)
    ranks[np.argsort(-value, kind="stable")] = np.arange(1, len(keys) + 1)
    result["reader_sequence_evidence"] = []
    for i in np.flatnonzero(reader):
        result["reader_sequence_evidence"].append(
            {
                "synthetic_session": keys[i][2],
                **details[i],
                "score": int(value[i]),
                "rank": int(ranks[i]),
                "alert": bool(selected[i]),
                "reason": "alert"
                if selected[i]
                else (
                    "shared_cap_or_boundary_tie" if candidates[i] else "below_validation_threshold"
                ),
                "global_combined_alert": bool(decisions[COMBINED][i]),
                "population_calibrated_alert": bool(decisions[POPULATION][i]),
            }
        )
    return result


def run(output: Path, plan_path: Path = DEFAULT_PLAN) -> dict:
    plan = json.loads(plan_path.read_text())
    train, _ = generate(**plan["training"])
    validation, _ = generate(**plan["validation"])
    model = PermutationComparison().fit(train, validation, plan)
    # All detector/threshold/tie choices are frozen before fresh test generation.
    result = {
        "schema_version": 6,
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
            raise ValueError("permutation partitions overlap")
        seen.update(keys)
        result["tests"][batch["name"]] = evaluate(model, events, truth, plan["paired_uncertainty"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    text = report(result)
    (output / "report.md").write_text(text)
    print(text.split("## Shared queue")[0])
    return result


def report(result: dict) -> str:
    lines = [
        "# Count-preserving permutation sequence baseline",
        "",
        "One global 2% review cap; count-conditioned within-session nulls; fresh instances of inspected synthetic families. "
        "Every comparator uses the same hash-priority tie policy in this study. No actor/population/scenario identity is used by the new statistic or its null RNG.",
        "",
        "| Fresh batch | Detector | AP | TP | FP | Precision | Recall | Alerts | Reader detected / total | Full-budget reader detected |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for batch, entry in result["tests"].items():
        for name, m in entry["models"].items():
            r = m["reader_sequence"]
            lines.append(
                f"| {batch} | {name} | {m['average_precision']:.3f} | {m['true_positives']} | {m['false_positives']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['alerts']} | {r['detected']} / {r['positives']} | {m['full_budget_review']['reader_sequence_detected']} |"
            )
    lines += ["", "## Shared queue, finite draws and reader evidence", ""]
    for batch, entry in result["tests"].items():
        q = entry["shared_queue"]
        lines += [
            f"### {batch}: {entry['positives']} positives / {entry['sessions']} sessions",
            "",
            f"Cap {q['cap_sessions']}; candidates {q['candidates']}; selected {q['unique_alerts']}; cap-suppressed {q['suppressed_by_cap']}. Score ceiling: {q['score_ceiling_sessions']} sessions. At boundary score {q['selected_boundary_score']}, {q['boundary_ties_selected']} of {q['boundary_candidate_ties']} candidate ties are selected.",
            f"Constant-tool sessions: {q['all_tools_identical_sessions']}; constant sampled null statistic: {q['sampled_null_constant_sessions']}.",
            "",
            "| Detector | Exactly-full-budget TP | FP | Reader detected | Reader missed |",
            "|---|---:|---:|---:|---:|",
        ]
        for name in ["rules", "markov_deviance", COMBINED, POPULATION, PERMUTATION]:
            f = entry["models"][name]["full_budget_review"]
            lines.append(
                f"| {name} | {f['true_positives']} | {f['false_positives']} | {f['reader_sequence_detected']} | {f['reader_sequence_missed']} |"
            )
        lines += [""]
        for reference, modes in entry["alert_changes"].items():
            for mode, c in modes.items():
                lines.append(
                    f"- {mode} versus {reference}: gain {c['gained']['true_positives']} true / {c['gained']['false_positives']} false; lose {c['lost']['true_positives']} true / {c['lost']['false_positives']} false. Reader gains/losses {c['reader_sequence_gained']}/{c['reader_sequence_lost']}."
                )
        for reference, c in entry["paired_recall_comparisons"].items():
            lines.append(
                f"- Permutation minus {reference} recall: {c['permutation_minus_reference_recall']:+.3f}; fixed-decision actor-cluster 95% interval {c['cluster_bootstrap_95_interval']}."
            )
        lines += [
            "",
            "| Reader session | Events | Tools | Statistic | MC p | Score | Rank | Outcome |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for e in entry["reader_sequence_evidence"]:
            lines.append(
                f"| {e['synthetic_session']} | {e['session_events']} | {e['distinct_tools']} | {e['observed_statistic']} | {e['monte_carlo_p']:.3f} | {e['score']} | {e['rank']} | {e['reason']} |"
            )
        lines += [""]
    lines += [
        "## Limits and leakage checks",
        "",
        *["- " + s for s in result["plan"]["limitations"]],
        "- The baseline fits no event model. Its only empirical threshold uses unlabelled validation. Labels enter only evaluation after scoring and alert decisions.",
        "- Null draws depend only on the canonical tool multiset and fixed master seed, never on observed order or other sessions. Counts and session length are preserved.",
        "- Work is bounded by 256 events per session and 25 million permutation cells per batch; malformed, duplicate, oversized and undersized sessions reject explicitly.",
        "- Conditional randomization tests order given counts. It deliberately cannot detect anomalies expressed solely in the conditioned-away information.",
        "- Full-budget reviews are separately reported counterfactuals; the operational queue applies a fixed validation threshold plus one global cap, without component or population quotas.",
        "- A Monte Carlo floor/ceiling tie is not certainty. Hash-based tie priority is deterministic, public and not an adversarially secure scheduling policy.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/permutation"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
