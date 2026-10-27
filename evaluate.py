"""Evaluate synthetic sessions held out from fitting and threshold selection."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import importlib.metadata
import platform
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

ACTIONS = ("read", "list", "api", "write", "request", "escalate", "export", "delete")
WEIGHTS = np.array([0.28, 0.24, 0.24, 0.12, 0.06, 0.03, 0.02, 0.01])


def sessions(seed, normal=2000, anomalous=100):
    rng = np.random.default_rng(seed)
    ids, features, labels = [], [], []
    for index in range(normal + anomalous):
        length = int(rng.integers(8, 20))
        actions = rng.choice(len(ACTIONS), size=length, p=WEIGHTS)
        label = index >= normal
        if label:
            for _ in range(int(rng.integers(1, 3))):
                actions[rng.integers(length)] = rng.choice([4, 5, 6], p=[0.25, 0.4, 0.35])
        counts = np.bincount(actions, minlength=len(ACTIONS)) / length
        transitions = actions[:-1] * len(ACTIONS) + actions[1:]
        _, frequencies = np.unique(transitions, return_counts=True)
        probabilities = frequencies / frequencies.sum()
        entropy = float(-(probabilities * np.log2(probabilities)).sum())
        features.append(np.r_[counts, entropy, length])
        labels.append(int(label))
        ids.append(f"seed-{seed}-session-{index}")
    return {"ids": ids, "x": np.array(features), "y": np.array(labels)}


def threshold_from_budget(scores, alert_budget=0.02):
    if not 0 < alert_budget < 1:
        raise ValueError("alert budget must be between zero and one")
    # The budget is an operational choice, not the generator's anomaly rate.
    # Ties are excluded so a large tied group cannot exceed the budget.
    return float(np.quantile(scores, 1 - alert_budget, method="higher"))


def metrics(labels, scores, threshold):
    predicted = scores > threshold
    return {"rocAUC": float(roc_auc_score(labels, scores)),
            "averagePrecision": float(average_precision_score(labels, scores)),
            "precision": float(precision_score(labels, predicted, zero_division=0)),
            "recall": float(recall_score(labels, predicted, zero_division=0)),
            "alertFraction": float(predicted.mean()),
            "confusionMatrixTNFPFNTP": confusion_matrix(labels, predicted, labels=[0, 1]).ravel().tolist()}


def evaluate(train, validation, test, alert_budget=0.02):
    all_ids = [set(part["ids"]) for part in (train, validation, test)]
    if any(all_ids[i] & all_ids[j] for i in range(3) for j in range(i)):
        raise ValueError("session IDs overlap between partitions")
    scaler = StandardScaler().fit(train["x"])
    forest = IsolationForest(n_estimators=300, contamination="auto", random_state=42, n_jobs=2)
    forest.fit(scaler.transform(train["x"]))
    scores = {"isolationForest": (-forest.score_samples(scaler.transform(validation["x"])),
                                    -forest.score_samples(scaler.transform(test["x"]))),
              "sensitiveActionRate": (validation["x"][:, 5:7].sum(axis=1), test["x"][:, 5:7].sum(axis=1))}
    models = {}
    for name, (validation_scores, test_scores) in scores.items():
        threshold = threshold_from_budget(validation_scores, alert_budget)
        models[name] = {"thresholdFromUnlabelledValidation": threshold,
                        "validation": metrics(validation["y"], validation_scores, threshold),
                        "test": metrics(test["y"], test_scores, threshold)}
    return {"schemaVersion": 1, "seeds": {"train": 42, "validation": 43, "test": 44},
            "validationAlertBudget": alert_budget, "forestContamination": "auto",
            "partitions": [{"name": name, "sessions": len(p["ids"]), "anomaliesForEvaluationOnly": int(p["y"].sum()),
                             "featureSHA256": hashlib.sha256(p["x"].astype("<f8").tobytes()).hexdigest()}
                            for name, p in zip(("train", "validation", "test"), (train, validation, test))],
            "models": models,
            "limits": ["Synthetic sessions from one generator family, not real incident data",
                       "Disjoint generated sessions do not establish generalization to real users or unseen attack families",
                       "A validation alert budget does not guarantee a future false-positive rate",
                       "Training data may contain anomalies; their labels are never passed to fitting or threshold selection",
                       "Saved notebook results used in-sample evaluation and are historical only"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evaluation/results.json")
    args = parser.parse_args()
    result = evaluate(sessions(42), sessions(43), sessions(44))
    result["executedAtUTC"] = datetime.now(timezone.utc).isoformat()
    result["sourceSHA256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["environment"] = {"python": platform.python_version(), **{name: importlib.metadata.version(name) for name in ("numpy", "scikit-learn", "scipy", "joblib", "threadpoolctl")}}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for name, item in result["models"].items(): print(name, json.dumps(item["test"]))
    return 0


if __name__ == "__main__": raise SystemExit(main())
