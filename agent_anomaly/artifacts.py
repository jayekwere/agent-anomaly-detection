"""Validate report invariants before publication or CI artifact retention."""

import json
import math
from pathlib import Path


def validate(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get("schema_version") != 2 or data.get("synthetic") is not True:
        raise ValueError("invalid experiment artifact")
    for entry in data["tests"].values():
        n = entry["sessions"]
        for result in entry["models"].values():
            if result["alerts"] > math.floor(n * 0.02):
                raise ValueError("alert budget exceeded")
            if result["true_positives"] + result["false_positives"] != result["alerts"]:
                raise ValueError("inconsistent confusion counts")
            if result["true_positives"] + result["false_negatives"] != entry["positives"]:
                raise ValueError("inconsistent positives")
            for field in ("precision", "recall", "average_precision", "roc_auc"):
                if not math.isfinite(result[field]) or not 0 <= result[field] <= 1:
                    raise ValueError("invalid metric")
    return data
