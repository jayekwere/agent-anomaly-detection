"""Frozen fusion calibration, shared caps, stream identity and leakage regression tests."""

import copy
import json
import unittest

import numpy as np

from agent_anomaly.combined_experiment import CombinedComparison, DEFAULT_PLAN, make_batch
from agent_anomaly.data import generate
from agent_anomaly.fusion import RulesSequenceFusion
from agent_anomaly.sequence_experiment import digest


class FusionTests(unittest.TestCase):
    def validation(self):
        return {
            "rules": np.array([1.0, 2.0, 4.0, 8.0]),
            "markov_deviance": np.array([10.0, 20.0, 40.0, 80.0]),
        }

    def test_exact_validation_scaling_and_combined_threshold(self):
        model = RulesSequenceFusion().fit(self.validation(), 0.5)
        self.assertEqual(model.scales, {"rules": 4.0, "markov_deviance": 40.0})
        self.assertEqual(model.threshold, 1.0)
        score = model.score(
            {"rules": np.array([8.0, 1.0]), "markov_deviance": np.array([10.0, 60.0])}
        )
        np.testing.assert_array_equal(score, [2.0, 1.5])

    def test_disjoint_component_peaks_share_one_cap(self):
        model = RulesSequenceFusion().fit(self.validation())
        rules, sequence = np.ones(100), np.ones(100)
        rules[:10], sequence[10:20] = 80.0, 800.0
        scores = model.score({"rules": rules, "markov_deviance": sequence})
        alerts = model.alerts(scores, 0.02)
        self.assertEqual(int((scores > model.threshold).sum()), 20)
        self.assertEqual(int(alerts.sum()), 2)

    def test_overlapping_signals_are_not_double_counted(self):
        model = RulesSequenceFusion().fit(self.validation())
        rules, sequence = np.ones(100), np.ones(100)
        rules[:2], sequence[:2] = 80.0, 800.0
        selected = model.alerts(model.score({"rules": rules, "markov_deviance": sequence}), 0.02)
        self.assertEqual(np.flatnonzero(selected).tolist(), [0, 1])

    def test_threshold_and_budget_ties_and_edges(self):
        model = RulesSequenceFusion().fit(self.validation())
        self.assertFalse(model.alerts(np.full(100, model.threshold), 0.02).any())
        self.assertFalse(model.alerts(np.ones(100) * 10, 0).any())
        self.assertEqual(int(model.alerts(np.ones(100) * 10, 1).sum()), 100)
        self.assertFalse(model.alerts(np.ones(10) * 10, 0.02).any())
        for budget in [-1, 2, float("nan")]:
            with self.assertRaises(ValueError):
                model.alerts(np.ones(10), budget)

    def test_explicit_invalid_calibration(self):
        for value in [-1, 0, 1, float("nan")]:
            with self.assertRaises(ValueError):
                RulesSequenceFusion().fit(self.validation(), value)
        for scores in [
            {},
            {"rules": [1], "markov_deviance": [1, 2]},
            {"rules": [0], "markov_deviance": [1]},
            {"rules": [float("inf")], "markov_deviance": [1]},
        ]:
            with self.assertRaises(ValueError):
                RulesSequenceFusion().fit(scores)
        for action in [
            lambda m: m.score(self.validation()),
            lambda m: m.parameters(),
            lambda m: m.alerts(np.ones(3), 0.02),
        ]:
            with self.assertRaisesRegex(ValueError, "not been calibrated"):
                action(RulesSequenceFusion())

    def test_inference_never_recalibrates(self):
        model = RulesSequenceFusion().fit(self.validation())
        frozen = copy.deepcopy(model.parameters())
        model.score({"rules": np.array([8000.0, 0.0]), "markov_deviance": np.array([0.0, 80000.0])})
        self.assertEqual(model.parameters(), frozen)


class CombinedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, _ = generate(42, 0)
        cls.validation, _ = generate(43, 2, count=120)
        cls.plan = json.loads(DEFAULT_PLAN.read_text())
        cls.model = CombinedComparison().fit(cls.train, cls.validation, cls.plan)

    def test_test_data_cannot_change_combination_or_thresholds(self):
        before = digest(self.model.parameters())
        keys, scores, decisions = self.model.score(self.validation)
        changed = copy.deepcopy(self.validation)
        for row in changed:
            row["tool"] = "novel.tool"
            row["label"] = 999
            row["scenario"] = "sequence_shift"
        self.model.score(changed)
        replay_keys, replay, replay_decisions = self.model.score(self.validation)
        self.assertEqual(keys, replay_keys)
        for name in scores:
            np.testing.assert_array_equal(scores[name], replay[name])
            np.testing.assert_array_equal(decisions[name], replay_decisions[name])
        self.assertEqual(before, digest(self.model.parameters()))

    def test_label_fields_do_not_affect_fit_scales_or_thresholds(self):
        train, validation = copy.deepcopy(self.train), copy.deepcopy(self.validation)
        for row in train + validation:
            row["label"] = 1
            row["population"] = "reader"
        replay = CombinedComparison().fit(train, validation, self.plan)
        self.assertEqual(replay.parameters(), self.model.parameters())

    def test_score_rejects_tampered_calibration(self):
        model = copy.deepcopy(self.model)
        model.thresholds["rules_plus_sequence"] += 0.1
        with self.assertRaisesRegex(ValueError, "modified fitted state"):
            model.score(self.validation)

    def test_no_labels_used_to_select_generator_stream_sessions(self):
        batch = {
            "parts": [
                {"seed": 1, "day": 4, "count": 25, "unseen": False},
                {"seed": 2, "day": 4, "count": 25, "unseen": True},
            ]
        }
        rows, truth = make_batch(batch)
        self.assertEqual(len(truth), 50)
        self.assertEqual(len({(r["tenant"], r["event_id"]) for r in rows}), len(rows))
        for stream, settings in enumerate(batch["parts"]):
            original_rows, original_truth = generate(**settings)
            self.assertEqual(
                {(t, a, f"p{stream}-" + s): v for (t, a, s), v in original_truth.items()},
                {key: v for key, v in truth.items() if key[2].startswith(f"p{stream}-")},
            )
            copied = [r for r in rows if r["session"].startswith(f"p{stream}-")]
            for r in copied:
                r = dict(r)
                r["session"] = r["session"][3:]
                r["event_id"] = r["event_id"][3:]
                self.assertEqual(r, original_rows.pop(0))
            self.assertEqual(len(original_rows), 0)

    def test_declared_freshness_and_one_budget(self):
        parts = [part for batch in self.plan["test_batches"] for part in batch["parts"]]
        old = {42, 43, 48, 50, 52, 7312026, 7312027, 7312028}
        self.assertFalse(old & {p["seed"] for p in parts})
        self.assertTrue(all(p["day"] > 14 for p in parts))
        self.assertTrue(
            all(sum(p["count"] for p in b["parts"]) == 1200 for b in self.plan["test_batches"])
        )
        self.assertEqual(self.plan["review_budget"], 0.02)
