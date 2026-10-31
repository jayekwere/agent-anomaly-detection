"""Offline reproducible experiment CLI."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np

from .data import generate
from .detectors import Detectors, budget
from .evaluation import measure
from .features import NAMES, Features


def run(output: Path) -> None:
    f = Features()
    train, _ = generate(42, 0)
    train_keys, x, train_ends = f.transform(train, fit=True)
    model = Detectors().fit(x)
    validation, _ = generate(43, 2)
    vk, vx, ve = f.transform(validation)
    vs = model.scores(vx)
    thresholds = {name: float(np.quantile(s, 0.98, method="higher")) for name, s in vs.items()}
    preferred = "rules"  # Predeclared interpretability preference, not selected on test.
    result = {
        "schema_version": 2,
        "synthetic": True,
        "seed": 42,
        "preferred_detector": preferred,
        "features": NAMES,
        "thresholds": thresholds,
        "tests": {},
        "environment": {
            "python": platform.python_version(),
            **{p: importlib.metadata.version(p) for p in ["numpy", "scikit-learn"]},
        },
        "source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "training_feature_sha256": hashlib.sha256(x.astype("<f8").tobytes()).hexdigest(),
        "limitations": [
            "Synthetic ground truth is not confirmed malicious activity.",
            "Scores are not probabilities. Review caps can suppress true positives.",
            "Bootstrap intervals assume independent sessions; repeated actors violate that assumption.",
            "Session-end detection only; online incident latency is not measured.",
            "Sequence features are coarse and may miss unseen ordered patterns.",
            "No guaranteed future false positive rate; no production efficacy claim.",
        ],
    }
    for name, day, unseen, drift in [
        ("held_out", 4, False, False),
        ("unseen_sequence", 6, True, False),
        ("drift", 8, False, True),
    ]:
        events, truth = generate(44 + day, day, unseen=unseen, drift=drift)
        keys, tx, ends = f.transform(events)
        if not (max(train_ends) < min(ve) and max(ve) < min(ends)):
            raise ValueError("nonchronological partitions")
        if set(train_keys) & set(keys) or set(vk) & set(keys):
            raise ValueError("overlapping session partitions")
        y = np.array([truth[k]["label"] for k in keys])
        entry = {
            "sessions": len(keys),
            "positives": int(y.sum()),
            "models": {},
            "feature_sha256": hashlib.sha256(tx.astype("<f8").tobytes()).hexdigest(),
            "drift_fraction_outside_training_range": float(
                ((tx < x.min(axis=0)) | (tx > x.max(axis=0))).mean()
            ),
        }
        for detector, scores in model.scores(tx).items():
            candidates = scores > thresholds[detector]
            alerts = candidates & budget(np.where(candidates, scores, -1e10), 0.02)
            item = measure(y, scores, alerts)
            item["threshold_candidates"] = int(candidates.sum())
            item["by_group"] = {}
            for field in ["scenario", "population"]:
                for value in sorted({truth[k][field] for k in keys}):
                    mask = np.array([truth[k][field] == value for k in keys])
                    item["by_group"][field + ":" + value] = measure(
                        y[mask], scores[mask], alerts[mask]
                    )
            item["examples"] = []
            for category, mask in [
                ("false_positive", alerts & (y == 0)),
                ("false_negative", ~alerts & (y == 1)),
                ("alert", alerts & (y == 1)),
            ]:
                for i in np.flatnonzero(mask)[:2]:
                    item["examples"].append(
                        {
                            "kind": category,
                            "synthetic_session": keys[i][2],
                            "scenario": truth[keys[i]]["scenario"],
                            "score": float(scores[i]),
                            "evidence": dict(zip(NAMES, tx[i].tolist())),
                        }
                    )
            entry["models"][detector] = item
        result["tests"][name] = entry
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    lines = [
        "# Synthetic behavioral evaluation",
        "",
        "An anomaly requires analyst review. Scores are not probabilities.",
        "",
        "| Test | Detector | Precision | Recall | AP | False alerts/1,000 | Alerts |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for test, entry in result["tests"].items():
        for name, m in entry["models"].items():
            lines.append(
                f"| {test} | {name} | {m['precision']:.3f} | {m['recall']:.3f} | {m['average_precision']:.3f} | {m['false_alerts_per_1000_sessions']:.2f} | {m['alerts']} |"
            )
    lines += [
        "",
        "## Interpretation",
        "",
        "Rules are the predeclared operational reference. Compare held-out AP and budget recall before promoting a challenger. No detector is validated for production.",
        "",
        *result["limitations"],
        "",
        "Full per-population results and false-positive/negative evidence are in results.json.",
    ]
    lines += ["", "## Analyst review examples", ""]
    for test, entry in result["tests"].items():
        for example in entry["models"]["rules"]["examples"]:
            lines.append(
                f"- {test}: {example['kind']} in synthetic session {example['synthetic_session']} ({example['scenario']}); denial rate {example['evidence']['denial_rate']:.3f}, export rate {example['evidence']['export_rate']:.3f}, events/second {example['evidence']['events_per_second']:.3f}. Review policy and actor context before escalation."
            )
    lines += [
        "",
        "Evidence values describe observed behavior; they are not causal ML feature attributions.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:15]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
