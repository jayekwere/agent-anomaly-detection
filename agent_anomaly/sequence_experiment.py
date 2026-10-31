"""Predeclared follow-up experiment, separate from immutable v2 evidence."""

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
from .detectors import Detectors, budget
from .evaluation import measure
from .features import Features
from .sequence import MarkovDeviance

DEFAULT_PLAN = Path(__file__).resolve().parent / "plans/sequence-v1.json"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def chronological_check(*partitions: list[dict]) -> None:
    groups = [correlate(rows) for rows in partitions]
    if any(set(groups[i]) & set(groups[j]) for i in range(len(groups)) for j in range(i)):
        raise ValueError("overlapping session partitions")
    for earlier, later in zip(groups, groups[1:]):
        if not earlier or not later:
            raise ValueError("empty experiment partition")
        if max(e.at for group in earlier.values() for e in group) >= min(
            e.at for group in later.values() for e in group
        ):
            raise ValueError("nonchronological partitions")


class FrozenComparison:
    """No labels accepted by training, calibration, or score methods."""

    def fit(self, train: list[dict], validation: list[dict], plan: dict) -> "FrozenComparison":
        chronological_check(train, validation)
        self.features = Features()
        _, x, _ = self.features.transform(train, fit=True)
        self.existing = Detectors().fit(x)
        self.sequence = MarkovDeviance(plan["sequence_model"]["additive_smoothing"]).fit(train)
        self.review_budget = plan["review_budget"]
        _, scores = self.score(validation)
        self.thresholds = {
            name: float(np.quantile(s, plan["calibration"]["quantile"], method="higher"))
            for name, s in scores.items()
        }
        self.training_fingerprint = self.sequence.fingerprint()
        return self

    def score(self, events: list[dict]) -> tuple[list, dict[str, np.ndarray]]:
        keys, x, _ = self.features.transform(events)
        sequence_keys, sequence_scores = self.sequence.score(events)
        if keys != sequence_keys:
            raise ValueError("detector session alignment mismatch")
        scores = self.existing.scores(x)
        scores["markov_deviance"] = sequence_scores
        return keys, scores

    def alerts(self, name: str, scores: np.ndarray) -> np.ndarray:
        candidates = scores > self.thresholds[name]
        return candidates & budget(np.where(candidates, scores, -1e10), self.review_budget)


def paired_recall_intervals(
    keys: list, labels: np.ndarray, alerts: dict[str, np.ndarray], settings: dict
) -> dict:
    """Resample actor clusters with fixed fitted models, thresholds and alert decisions."""
    scopes = sorted({key[:2] for key in keys})
    indices = [np.array([i for i, key in enumerate(keys) if key[:2] == scope]) for scope in scopes]
    rng = np.random.default_rng(settings["seed"])
    samples = {name: [] for name in alerts if name != "markov_deviance"}
    for _ in range(settings["replicates"]):
        idx = np.concatenate([indices[i] for i in rng.integers(0, len(scopes), len(scopes))])
        positives = int(labels[idx].sum())
        if not positives:
            continue
        new_hits = int(labels[idx][alerts["markov_deviance"][idx]].sum())
        for name in samples:
            hits = int(labels[idx][alerts[name][idx]].sum())
            samples[name].append((new_hits - hits) / positives)
    return {
        name: {
            "markov_minus_reference_recall": float(
                (labels[alerts["markov_deviance"]].sum() - labels[alerts[name]].sum())
                / max(1, int(labels.sum()))
            ),
            "cluster_bootstrap_95_interval": np.quantile(values, [0.025, 0.975]).tolist()
            if values
            else None,
        }
        for name, values in samples.items()
    }


def order_control(events: list[dict], seed: int) -> list[dict]:
    """Permute only tool assignments inside each session, keeping event identity/time/outcome."""
    groups: dict[tuple, list[int]] = {}
    for i, row in enumerate(events):
        groups.setdefault((row["tenant"], row["actor"], row["session"]), []).append(i)
    output = copy.deepcopy(events)
    rng = np.random.default_rng(seed)
    for key in sorted(groups):
        idx = groups[key]
        tools = rng.permutation([events[i]["tool"] for i in idx])
        for i, tool in zip(idx, tools):
            output[i]["tool"] = str(tool)
    return output


def run(output: Path, plan_path: Path = DEFAULT_PLAN) -> dict:
    plan = json.loads(plan_path.read_text())
    train, _ = generate(**plan["training"])
    validation, _ = generate(**plan["validation"])
    model = FrozenComparison().fit(train, validation, plan)
    # Freeze the complete comparison before any fresh test batch is generated.
    frozen_thresholds = dict(model.thresholds)
    result = {
        "schema_version": 3,
        "synthetic": True,
        "plan": plan,
        "plan_sha256": digest(plan),
        "training_events_sha256": digest(train),
        "validation_events_sha256": digest(validation),
        "sequence_training_fingerprint": model.training_fingerprint,
        "thresholds": frozen_thresholds,
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
    seen_keys = set(correlate(train)) | set(correlate(validation))
    for batch in plan["test_batches"]:
        events, truth = generate(**{k: v for k, v in batch.items() if k != "name"})
        chronological_check(train, validation, events)
        keys, scores = model.score(events)
        if seen_keys & set(keys):
            raise ValueError("overlapping test batches")
        seen_keys.update(keys)
        labels = np.array([truth[key]["label"] for key in keys])
        decisions = {name: model.alerts(name, s) for name, s in scores.items()}
        entry = {
            "sessions": len(keys),
            "positives": int(labels.sum()),
            "events_sha256": digest(events),
            "models": {},
        }
        for name, s in scores.items():
            metrics = measure(labels, s, decisions[name])
            metrics["threshold_candidates"] = int((s > frozen_thresholds[name]).sum())
            metrics["by_population"] = {}
            for population in sorted({truth[key]["population"] for key in keys}):
                mask = np.array([truth[key]["population"] == population for key in keys])
                metrics["by_population"][population] = measure(
                    labels[mask], s[mask], decisions[name][mask]
                )
            metrics["by_scenario"] = {}
            for scenario in sorted({truth[key]["scenario"] for key in keys}):
                mask = np.array([truth[key]["scenario"] == scenario for key in keys])
                metrics["by_scenario"][scenario] = measure(
                    labels[mask], s[mask], decisions[name][mask]
                )
            entry["models"][name] = metrics
        entry["paired_recall_comparisons"] = paired_recall_intervals(
            keys, labels, decisions, plan["paired_uncertainty"]
        )
        if batch["name"] == "fresh_sequence":
            shuffled_keys, shuffled = model.score(
                order_control(events, plan["order_control"]["seed"])
            )
            if shuffled_keys != keys:
                raise ValueError("permutation session alignment mismatch")
            diagnostic = {}
            for category, mask in [
                ("original_sequence", labels == 1),
                ("original_benign", labels == 0),
            ]:
                delta = scores["markov_deviance"][mask] - shuffled["markov_deviance"][mask]
                diagnostic[category] = {
                    "sessions": int(mask.sum()),
                    "median_original_minus_shuffled_score": float(np.median(delta)),
                    "fraction_original_score_higher": float((delta > 0).mean()),
                }
            entry["order_control_unlabelled_score_diagnostic"] = diagnostic
        if (
            model.thresholds != frozen_thresholds
            or model.sequence.fingerprint() != model.training_fingerprint
        ):
            raise ValueError("evaluation changed fitted state or thresholds")
        result["tests"][batch["name"]] = entry
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "report.md").write_text(report(result))
    print(report(result).split("## Details")[0])
    return result


def report(result: dict) -> str:
    lines = [
        "# Sequence baseline follow-up",
        "",
        "Synthetic, targeted follow-up on fresh instances of a previously inspected family. "
        "No sequence-family examples are used in fitting or validation. "
        "Original v2 evidence is preserved; scores are not attack probabilities.",
        "",
        "| Fresh batch | Detector | AP | Precision | Recall | False alerts/1,000 | Alerts | Recall @ 2% ranking budget |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for batch, entry in result["tests"].items():
        for name, m in entry["models"].items():
            lines.append(
                f"| {batch} | {name} | {m['average_precision']:.3f} | {m['precision']:.3f} | "
                f"{m['recall']:.3f} | {m['false_alerts_per_1000_sessions']:.2f} | {m['alerts']} | "
                f"{m['budgets']['0.02']['recall']:.3f} |"
            )
    lines += [
        "",
        "## Details",
        "",
        "First-order, actor-scoped transition counts are fitted on unfiltered training events only. "
        "Add-one smoothing and the normalized conditional deviance formula were fixed before test generation. "
        "All four detectors use their own unlabelled validation 98th percentile, strict > ties, "
        "and the same 2% batch review cap. Ranking-budget recall ignores calibration and is reported separately.",
        "",
    ]
    for batch, entry in result["tests"].items():
        lines += [
            f"### {batch}: {entry['positives']} positives in {entry['sessions']} sessions",
            "",
        ]
        lines += [
            "| Markov population | Recall | True positives | False positives |",
            "|---|---:|---:|---:|",
        ]
        for population, m in entry["models"]["markov_deviance"]["by_population"].items():
            lines.append(
                f"| {population} | {m['recall']:.3f} | {m['true_positives']} | {m['false_positives']} |"
            )
        lines += [""]
        for name, comparison in entry["paired_recall_comparisons"].items():
            lo, hi = comparison["cluster_bootstrap_95_interval"]
            lines.append(
                f"- Markov minus {name} recall: {comparison['markov_minus_reference_recall']:+.3f}; paired actor-cluster bootstrap 95% interval [{lo:+.3f}, {hi:+.3f}]."
            )
        if "order_control_unlabelled_score_diagnostic" in entry:
            lines += [
                "",
                "Count-preserving order control (one permutation per session; no relabelled efficacy claim):",
                "",
            ]
            for name, diagnostic in entry["order_control_unlabelled_score_diagnostic"].items():
                lines.append(
                    f"- {name}: median original minus shuffled Markov score {diagnostic['median_original_minus_shuffled_score']:+.3f}; original score higher in {diagnostic['fraction_original_score_higher']:.1%} of sessions."
                )
        lines += [""]
    lines += [
        "## Limits",
        "",
        *["- " + limit for limit in result["plan"]["limitations"]],
        "- Paired intervals resample tenant/actor clusters with fixed decisions; they do not include training or validation uncertainty, or rerun the batch cap in each resample.",
        "- Per-session bootstrap intervals inherited from the original metrics assume independence; prefer the paired actor-cluster differences for this comparison.",
        "- A shuffled session can still have unusual composition. One permutation is a diagnostic, not a permutation significance test.",
        "- Unknown actors and sessions with fewer than two events reject explicitly. Unknown tools use a reserved smoothed bucket without updating fitted state.",
        "- Full scenario/population results, thresholds, seeds, event hashes and source hashes are in results.json.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/sequence"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
