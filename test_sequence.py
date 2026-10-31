"""Sequence mechanics and leakage boundaries, without fresh held-out labels."""

from collections import Counter
import copy
from datetime import UTC, datetime, timedelta
import json
import math
import unittest

import numpy as np

from agent_anomaly.data import generate
from agent_anomaly.sequence import MarkovDeviance
from agent_anomaly.sequence_experiment import (
    DEFAULT_PLAN,
    FrozenComparison,
    chronological_check,
    order_control,
    paired_recall_intervals,
)


def events(tools, session="s", tenant="synthetic", actor="agent", day=0):
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)
    return [
        dict(
            schema_version=1,
            tenant=tenant,
            actor=actor,
            session=session,
            event_id=f"{session}-{i}",
            at=(start + timedelta(seconds=i)).isoformat(),
            tool=tool,
            outcome="allowed",
        )
        for i, tool in enumerate(tools)
    ]


class SequenceTests(unittest.TestCase):
    def test_exact_smoothed_score_and_no_cross_session_pairs(self):
        train = events(["a", "b"], "s1") + events(["a", "b"], "s2")
        model = MarkovDeviance().fit(train)
        self.assertAlmostEqual(model.score(events(["a", "b"]))[1][0], 2 * math.log(5 / 3))
        # No fabricated b->a transition between the two training sessions.
        self.assertAlmostEqual(model.score(events(["b", "a"]))[1][0], 2 * math.log(3))

    def test_same_histogram_different_order(self):
        train = events(["a", "b"] * 20)
        model = MarkovDeviance().fit(train)
        alternating = model.score(events(["a", "b"] * 4))[1][0]
        blocked = model.score(events(["a"] * 4 + ["b"] * 4))[1][0]
        self.assertGreater(blocked, alternating)

    def test_no_cross_tenant_or_actor_reference(self):
        model = MarkovDeviance().fit(events(["a", "b"] * 4))
        for change in [{"tenant": "other"}, {"actor": "other"}]:
            with self.assertRaisesRegex(ValueError, "no training reference"):
                model.score(events(["a", "b"], **change))

    def test_fit_scope_isolation(self):
        base = events(["a", "b"] * 4)
        extra = events(["b"] * 10, tenant="other")
        first = MarkovDeviance().fit(base)
        second = MarkovDeviance().fit(base + extra)
        np.testing.assert_array_equal(first.score(base)[1], second.score(base)[1])

    def test_explicit_failures(self):
        with self.assertRaisesRegex(ValueError, "not been fitted"):
            MarkovDeviance().score(events(["a", "b"]))
        for value in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                MarkovDeviance(value)
        for train in [[], events(["a"])]:
            with self.assertRaisesRegex(ValueError, "training requires"):
                MarkovDeviance().fit(train)
        model = MarkovDeviance().fit(events(["a", "b"]))
        with self.assertRaisesRegex(ValueError, "at least two events"):
            model.score(events(["a"]))

    def test_frozen_unknown_bucket_and_input_order(self):
        train = events(["a", "b"] * 4)
        model = MarkovDeviance().fit(train)
        fingerprint = model.fingerprint()
        probe = events(["new.tool", "new.tool", "a", "b"])
        first = model.score(probe)[1]
        second = model.score(list(reversed(probe)))[1]
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.isfinite(first).all())
        self.assertEqual(fingerprint, model.fingerprint())

    def test_refit_replaces_history(self):
        model = MarkovDeviance().fit(events(["a", "b"] * 4))
        other = events(["c", "d"] * 4)
        model.fit(other)
        self.assertEqual(model.fingerprint(), MarkovDeviance().fit(other).fingerprint())


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, _ = generate(42, 0, count=1200)
        cls.validation, _ = generate(43, 2, count=90)
        cls.plan = json.loads(DEFAULT_PLAN.read_text())
        cls.model = FrozenComparison().fit(cls.train, cls.validation, cls.plan)

    def test_labels_cannot_change_thresholds(self):
        train, val = copy.deepcopy(self.train), copy.deepcopy(self.validation)
        for row in train + val:
            row["label"] = 999
            row["scenario"] = "SECRET_GROUND_TRUTH"
        other = FrozenComparison().fit(train, val, self.plan)
        self.assertEqual(self.model.thresholds, other.thresholds)
        self.assertEqual(self.model.training_fingerprint, other.training_fingerprint)

    def test_test_changes_cannot_change_fit_or_calibration(self):
        thresholds = dict(self.model.thresholds)
        fingerprint = self.model.sequence.fingerprint()
        # Use only validation fixtures for this regression, never fresh test labels.
        before_keys, before = self.model.score(self.validation)
        probe = copy.deepcopy(self.validation)
        for row in probe:
            row["tool"] = "brand.new"
        self.model.score(probe)
        keys, after = self.model.score(self.validation)
        self.assertEqual(before_keys, keys)
        for name in before:
            np.testing.assert_array_equal(before[name], after[name])
        self.assertEqual(thresholds, self.model.thresholds)
        self.assertEqual(fingerprint, self.model.sequence.fingerprint())

    def test_chronology_and_overlap_rejected_before_fitting(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            FrozenComparison().fit(self.train, self.train, self.plan)
        with self.assertRaisesRegex(ValueError, "nonchronological"):
            chronological_check(self.validation, self.train)
        with self.assertRaisesRegex(ValueError, "empty"):
            chronological_check([], self.validation)

    def test_order_control_preserves_all_nontool_fields_and_histograms(self):
        before = events(["a", "b", "c"] * 10)
        after = order_control(before, 12)
        self.assertEqual(Counter(e["tool"] for e in before), Counter(e["tool"] for e in after))
        self.assertNotEqual([e["tool"] for e in before], [e["tool"] for e in after])
        for a, b in zip(before, after):
            self.assertEqual(
                {k: v for k, v in a.items() if k != "tool"},
                {k: v for k, v in b.items() if k != "tool"},
            )
        self.assertEqual(after, order_control(before, 12))

    def test_paired_cluster_interval_same_decisions(self):
        keys = [("t", "a", "s1"), ("t", "a", "s2"), ("t", "b", "s3")]
        y = np.array([1, 0, 1])
        alerts = np.array([True, False, False])
        result = paired_recall_intervals(
            keys, y, {"rules": alerts, "markov_deviance": alerts}, {"seed": 9, "replicates": 30}
        )
        self.assertEqual(result["rules"]["markov_minus_reference_recall"], 0)
        self.assertEqual(result["rules"]["cluster_bootstrap_95_interval"], [0.0, 0.0])


class SequenceArtifactTests(unittest.TestCase):
    def test_recorded_results_and_corruptions(self):
        from pathlib import Path
        import tempfile
        from scripts.verify_sequence_results import compare, validate

        source = Path(__file__).parent / "evaluation/sequence-v1/results.json"
        data = validate(source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for mutation in ["budget", "missing_detector", "group_counts"]:
                bad = copy.deepcopy(data)
                metrics = bad["tests"]["fresh_sequence"]["models"]["markov_deviance"]
                if mutation == "budget":
                    metrics["alerts"] = 1000
                elif mutation == "missing_detector":
                    del bad["tests"]["fresh_sequence"]["models"]["rules"]
                else:
                    metrics["by_population"]["reader"]["false_positives"] += 1
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    validate(path)
        compare(data, copy.deepcopy(data))
        bad = copy.deepcopy(data)
        bad["thresholds"]["markov_deviance"] += 0.01
        with self.assertRaisesRegex(ValueError, "numbers differ"):
            compare(data, bad)

    def test_declared_test_periods_and_seeds_are_fresh(self):
        plan = json.loads(DEFAULT_PLAN.read_text())
        self.assertTrue(all(batch["day"] > 8 for batch in plan["test_batches"]))
        self.assertFalse({42, 43, 48, 50, 52} & {b["seed"] for b in plan["test_batches"]})
        self.assertEqual(plan["sequence_model"]["additive_smoothing"], 1.0)


class NumericalDiagnosticTests(unittest.TestCase):
    def test_near_equal_shuffle_scores_are_ties(self):
        from agent_anomaly.sequence_experiment import order_score_diagnostic

        original = np.array([1.0, 2.0, 3.0])
        shuffled = np.array([1.0 - 2e-16, 2.0 + 1e-15, 2.0])
        result = order_score_diagnostic(original, shuffled)
        self.assertEqual(result["fraction_original_score_higher"], 1 / 3)
        self.assertEqual(result["median_original_minus_shuffled_score"], 0.0)
