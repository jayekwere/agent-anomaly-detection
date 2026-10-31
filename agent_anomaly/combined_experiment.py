"""Predeclared shared-budget rules-plus-sequence evaluation on fresh instances."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np

from . import correlate
from .data import generate
from .evaluation import measure
from .detectors import budget
from .fusion import RulesSequenceFusion
from .sequence_experiment import FrozenComparison, chronological_check, digest

DEFAULT_PLAN = Path(__file__).resolve().parent / "plans/combined-v1.json"
COMBINED = "rules_plus_sequence"


def make_batch(batch: dict) -> tuple[list[dict], dict]:
    """Mix whole independent streams, never select sessions using ground truth."""
    events, truth = [], {}
    for stream, settings in enumerate(batch["parts"]):
        rows, labels = generate(**settings)
        prefix = f"p{stream}-"
        for row in rows:
            row["session"] = prefix + row["session"]
            row["event_id"] = prefix + row["event_id"]
        events.extend(rows)
        truth.update(
            {
                (tenant, actor, prefix + session): value
                for (tenant, actor, session), value in labels.items()
            }
        )
    return events, truth


class CombinedComparison:
    def fit(self, train: list[dict], validation: list[dict], plan: dict) -> "CombinedComparison":
        self.base = FrozenComparison().fit(train, validation, plan)
        _, scores = self.base.score(validation)
        self.fusion = RulesSequenceFusion().fit(scores, plan["calibration"]["quantile"])
        self.review_budget = plan["review_budget"]
        self.thresholds = {**self.base.thresholds, COMBINED: self.fusion.threshold}
        self.frozen_state = digest(self.parameters())
        return self

    def parameters(self) -> dict:
        return {
            "thresholds": dict(self.thresholds),
            "fusion": self.fusion.parameters(),
            "sequence_training_fingerprint": self.base.sequence.fingerprint(),
            "review_budget": self.review_budget,
        }

    def score(
        self, events: list[dict]
    ) -> tuple[list, dict[str, np.ndarray], dict[str, np.ndarray]]:
        keys, scores = self.base.score(events)
        scores[COMBINED] = self.fusion.score(scores)
        decisions = {
            name: self.base.alerts(name, s) for name, s in scores.items() if name != COMBINED
        }
        decisions[COMBINED] = self.fusion.alerts(scores[COMBINED], self.review_budget)
        if digest(self.parameters()) != self.frozen_state:
            raise ValueError("evaluation modified fitted state or calibration")
        return keys, scores, decisions


def counts(mask: np.ndarray, labels: np.ndarray) -> dict:
    tp = int(labels[mask].sum())
    return {
        "alerts": int(mask.sum()),
        "true_positives": tp,
        "false_positives": int(mask.sum()) - tp,
    }


def paired_differences(keys: list, labels: np.ndarray, decisions: dict, settings: dict) -> dict:
    scopes = sorted({k[:2] for k in keys})
    groups = [np.array([i for i, k in enumerate(keys) if k[:2] == scope]) for scope in scopes]
    rng = np.random.default_rng(settings["seed"])
    samples = {name: [] for name in decisions if name != COMBINED}
    for _ in range(settings["replicates"]):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        positives = int(labels[idx].sum())
        if not positives:
            continue
        combined_hits = int(labels[idx][decisions[COMBINED][idx]].sum())
        for name in samples:
            hits = int(labels[idx][decisions[name][idx]].sum())
            samples[name].append((combined_hits - hits) / positives)
    return {
        name: {
            "combined_minus_reference_recall": float(
                (labels[decisions[COMBINED]].sum() - labels[decisions[name]].sum())
                / max(1, int(labels.sum()))
            ),
            "cluster_bootstrap_95_interval": np.quantile(values, [0.025, 0.975]).tolist()
            if values
            else None,
        }
        for name, values in samples.items()
    }


def evaluate_batch(
    model: CombinedComparison, events: list[dict], truth: dict, settings: dict
) -> dict:
    keys, scores, decisions = model.score(events)
    labels = np.array([truth[k]["label"] for k in keys])
    reader_sequence = np.array(
        [
            truth[k]["population"] == "reader" and truth[k]["scenario"] == "sequence_shift"
            for k in keys
        ]
    )
    result = {
        "sessions": len(keys),
        "positives": int(labels.sum()),
        "events_sha256": digest(events),
        "models": {},
    }
    for name, s in scores.items():
        m = measure(labels, s, decisions[name])
        m["threshold_candidates"] = int((s > model.thresholds[name]).sum())
        for field in ["population", "scenario"]:
            m["by_" + field] = {}
            for value in sorted({truth[k][field] for k in keys}):
                mask = np.array([truth[k][field] == value for k in keys])
                m["by_" + field][value] = measure(labels[mask], s[mask], decisions[name][mask])
        detected = int((decisions[name] & reader_sequence).sum())
        ranked = budget(s, model.review_budget)
        m["full_budget_review"] = {
            **counts(ranked, labels),
            "reader_sequence_detected": int((ranked & reader_sequence).sum()),
            "reader_sequence_missed": int((reader_sequence & ~ranked).sum()),
            "by_scenario": {
                scenario: counts(
                    ranked & np.array([truth[k]["scenario"] == scenario for k in keys]), labels
                )
                for scenario in sorted({truth[k]["scenario"] for k in keys})
            },
        }
        m["reader_sequence"] = {
            "positives": int(reader_sequence.sum()),
            "detected": detected,
            "missed": int(reader_sequence.sum()) - detected,
            "recall": detected / int(reader_sequence.sum()) if reader_sequence.any() else None,
        }
        result["models"][name] = m
    selected = decisions[COMBINED]
    fusion_scores = scores[COMBINED]
    rules_scaled = scores["rules"] / model.fusion.scales["rules"]
    seq_scaled = scores["markov_deviance"] / model.fusion.scales["markov_deviance"]
    tied = np.isclose(rules_scaled, seq_scaled, rtol=1e-12, atol=1e-12)
    result["shared_queue"] = {
        "cap_sessions": int(len(keys) * model.review_budget),
        "unique_alerts": int(selected.sum()),
        "component_candidate_union": int(((rules_scaled > 1) | (seq_scaled > 1)).sum()),
        "combined_threshold_candidates": int((fusion_scores > model.fusion.threshold).sum()),
        "excluded_by_combined_threshold": int(
            ((rules_scaled > 1) | (seq_scaled > 1)).sum()
            - (fusion_scores > model.fusion.threshold).sum()
        ),
        "suppressed_by_shared_cap": int(
            (fusion_scores > model.fusion.threshold).sum() - selected.sum()
        ),
        "dominance": {
            name: counts(selected & mask, labels)
            for name, mask in [
                ("rules", (rules_scaled > seq_scaled) & ~tied),
                ("sequence", (seq_scaled > rules_scaled) & ~tied),
                ("numerical_tie", tied),
            ]
        },
    }
    result["alert_changes"] = {}
    for reference in ["rules", "markov_deviance"]:
        gained = selected & ~decisions[reference]
        lost = decisions[reference] & ~selected
        result["alert_changes"][reference] = {
            "gained": counts(gained, labels),
            "lost": counts(lost, labels),
            "reader_sequence_gained": int((gained & reader_sequence).sum()),
            "reader_sequence_lost": int((lost & reader_sequence).sum()),
        }
    result["full_budget_alert_changes"] = {}
    combined_ranked = budget(scores[COMBINED], model.review_budget)
    for reference in ["rules", "markov_deviance"]:
        reference_ranked = budget(scores[reference], model.review_budget)
        result["full_budget_alert_changes"][reference] = {
            "gained": counts(combined_ranked & ~reference_ranked, labels),
            "lost": counts(reference_ranked & ~combined_ranked, labels),
        }
    result["paired_recall_comparisons"] = paired_differences(keys, labels, decisions, settings)
    ranks = np.empty(len(keys), dtype=int)
    ranks[np.argsort(-fusion_scores, kind="stable")] = np.arange(1, len(keys) + 1)
    result["missed_reader_sequence_examples"] = [
        {
            "synthetic_session": keys[i][2],
            "rules_score": float(scores["rules"][i]),
            "sequence_score": float(scores["markov_deviance"][i]),
            "combined_score": float(fusion_scores[i]),
            "combined_threshold": model.fusion.threshold,
            "global_score_rank": int(ranks[i]),
            "reason": "shared_budget_suppression"
            if fusion_scores[i] > model.fusion.threshold
            else "below_combined_threshold",
            "standalone_rules_alert": bool(decisions["rules"][i]),
            "standalone_sequence_alert": bool(decisions["markov_deviance"][i]),
        }
        for i in np.flatnonzero(reader_sequence & ~selected)[:5]
    ]
    return result


def run(output: Path, plan_path: Path = DEFAULT_PLAN) -> dict:
    plan = json.loads(plan_path.read_text())
    train, _ = generate(**plan["training"])
    validation, _ = generate(**plan["validation"])
    model = CombinedComparison().fit(train, validation, plan)
    # All learned state, score scales, thresholds and fusion choices are fixed here.
    result = {
        "schema_version": 4,
        "synthetic": True,
        "plan": plan,
        "plan_sha256": digest(plan),
        "training_events_sha256": digest(train),
        "validation_events_sha256": digest(validation),
        "parameters": copy.deepcopy(model.parameters()),
        "environment": {
            "python": platform.python_version(),
            **{p: importlib.metadata.version(p) for p in ["numpy", "scikit-learn"]},
        },
        "source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "tests": {},
    }
    seen = set(correlate(train)) | set(correlate(validation))
    for batch in plan["test_batches"]:
        events, truth = make_batch(batch)
        chronological_check(train, validation, events)
        keys = set(correlate(events))
        if keys & seen:
            raise ValueError("test partitions overlap")
        seen.update(keys)
        result["tests"][batch["name"]] = evaluate_batch(
            model, events, truth, plan["paired_uncertainty"]
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    text = report(result)
    (output / "report.md").write_text(text)
    print(text.split("## Shared queue")[0])
    return result


def report(result: dict) -> str:
    lines = [
        "# Rules plus sequence: one shared alert budget",
        "",
        "Synthetic follow-up with fixed maximum fusion and fresh test instances. "
        "Each combined session appears once in the shared queue; component alert quotas are never added together. "
        "Original detectors and historical evidence are unchanged.",
        "",
        "| Fresh batch | Detector | AP | Precision | Recall | False alerts/1,000 | Alerts | Recall @ equal 2% ranking budget |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for batch, entry in result["tests"].items():
        for name, m in entry["models"].items():
            lines.append(
                f"| {batch} | {name} | {m['average_precision']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['false_alerts_per_1000_sessions']:.2f} | {m['alerts']} | {m['budgets']['0.02']['recall']:.3f} |"
            )
    lines += [
        "",
        "## Shared queue, displacement and reader misses",
        "",
        "Component scores are divided by their validation 98th percentiles. The maximum is calibrated again on validation, then frozen. "
        "Strict threshold ties are excluded and one global 2% cap is applied. Equal-budget ranking metrics ignore thresholds and are separate counterfactual reviews.",
        "",
    ]
    for batch, entry in result["tests"].items():
        q = entry["shared_queue"]
        lines += [
            f"### {batch}: {entry['positives']} positives in {entry['sessions']} sessions",
            "",
            f"Shared cap {q['cap_sessions']}; unique alerts {q['unique_alerts']}; raw component-candidate union {q['component_candidate_union']}; above combined threshold {q['combined_threshold_candidates']}; suppressed by cap {q['suppressed_by_shared_cap']}.",
            "",
            "| Dominant signal in selected queue | Alerts | True positives | False positives |",
            "|---|---:|---:|---:|",
        ]
        for name, c in q["dominance"].items():
            lines.append(
                f"| {name} | {c['alerts']} | {c['true_positives']} | {c['false_positives']} |"
            )
        lines += [
            "",
            "| Detector | Reader sequence positives | Detected | Missed | Recall |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, m in entry["models"].items():
            r = m["reader_sequence"]
            recall_text = f"{r['recall']:.3f}" if r["recall"] is not None else "n/a"
            lines.append(
                f"| {name} | {r['positives']} | {r['detected']} | {r['missed']} | {recall_text} |"
            )
        lines += [""]
        lines += [
            "Exactly-full-budget reviews (thresholds ignored; one shared top-24 ranking):",
            "",
            "| Detector | True positives | False positives | Reader-sequence detected | Reader-sequence missed |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, m in entry["models"].items():
            full = m["full_budget_review"]
            lines.append(
                f"| {name} | {full['true_positives']} | {full['false_positives']} | {full['reader_sequence_detected']} | {full['reader_sequence_missed']} |"
            )
        lines += [""]
        for ref, change in entry["alert_changes"].items():
            gained, lost = change["gained"], change["lost"]
            lines.append(
                f"- Versus {ref}: gain {gained['true_positives']} true / {gained['false_positives']} false alerts; lose {lost['true_positives']} true / {lost['false_positives']} false alerts. Reader-sequence gains/losses: {change['reader_sequence_gained']}/{change['reader_sequence_lost']}."
            )
        for ref, comparison in entry["paired_recall_comparisons"].items():
            interval = comparison["cluster_bootstrap_95_interval"]
            lines.append(
                f"- Combined minus {ref} recall: {comparison['combined_minus_reference_recall']:+.3f}; paired actor-cluster bootstrap 95% interval {interval} (fixed fitted models and decisions)."
            )
        lines += [""]
        for example in entry["missed_reader_sequence_examples"]:
            lines.append(
                f"- Missed reader sequence {example['synthetic_session']}: {example['reason']}; combined score {example['combined_score']:.3f}, threshold {example['combined_threshold']:.3f}, global rank {example['global_score_rank']}."
            )
        lines += [""]
    lines += [
        "## Limits",
        "",
        *["- " + limit for limit in result["plan"]["limitations"]],
        "- Dominance is the component providing the maximum normalized score, not a causal feature attribution. Numerical ties use rtol/atol 1e-12 for reporting only.",
        "- Reader-sequence reporting uses ground truth after alerts are fixed; population/scenario information never selects the operating point.",
        "- Known-actor, completed-session evaluation only. A global budget can preserve original sequence blind spots or displace correct standalone alerts.",
        "- Complete population/scenario metrics and missed-reader evidence are in results.json.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/combined"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
