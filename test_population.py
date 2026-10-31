"""Training-only profiles, within-tenant calibration and one shared cap."""

import copy
import json
import unittest

import numpy as np

from agent_anomaly.data import generate
from agent_anomaly.population import PopulationCalibration
from agent_anomaly.population_experiment import DEFAULT_PLAN, PopulationComparison
from agent_anomaly.sequence_experiment import digest
from test_sequence import events


def settings(minimum=2):
    return {
        "read_dominant_min_fraction": 0.5,
        "export_heavy_min_fraction": 0.25,
        "minimum_validation_sessions": minimum,
    }


def fixture():
    train = events(["case.read"] * 8 + ["case.list"] * 2, actor="opaque", session="s1")
    train += events(["case.write"] * 8 + ["case.read"] * 2, actor="reader-looking", session="s2")
    train += events(
        ["evidence.export"] * 8 + ["case.read"] * 2, actor="opaque-export", session="s3"
    )
    keys = [
        ("synthetic", actor, f"v{i}")
        for actor in ["opaque", "reader-looking", "opaque-export"]
        for i in range(3)
    ]
    scores = {
        "rules": np.array([1.0, 2.0, 3.0] * 3),
        "markov_deviance": np.array([0.5, 0.8, 1.2, 2.0, 3.0, 4.0, 2.0, 3.0, 4.0]),
    }
    return train, keys, scores


class PopulationTests(unittest.TestCase):
    def test_groups_use_training_tools_not_actor_names(self):
        train, keys, scores = fixture()
        model = PopulationCalibration().fit(train, keys, scores, settings())
        self.assertEqual(model.profiles[("synthetic", "opaque")], "read_dominant")
        self.assertEqual(model.profiles[("synthetic", "reader-looking")], "other")
        self.assertEqual(model.profiles[("synthetic", "opaque-export")], "export_heavy")
        probe = {"rules": np.array([0.0, 0.0]), "markov_deviance": np.array([1.5, 1.5])}
        scored, _, _ = model.score([keys[0], keys[3]], probe)
        self.assertGreater(scored[0], scored[1])
        self.assertGreater(scored[0], 1.0)
        self.assertLess(scored[1], 1.0)

    def test_validation_labels_and_test_tools_never_assign_groups(self):
        train, keys, scores = fixture()
        for row in train:
            row["population"] = "FAKE"
            row["label"] = 1
        model = PopulationCalibration().fit(train, keys, scores, settings())
        before = digest(model.parameters())
        model.score(keys, {"rules": np.ones(9) * 100, "markov_deviance": np.ones(9) * 200})
        self.assertEqual(before, digest(model.parameters()))
        self.assertEqual(model.groups(keys)[0], ("synthetic", "read_dominant"))

    def test_cross_tenant_calibration_isolation(self):
        train, keys, scores = fixture()
        other_train = [dict(r, tenant="other") for r in train]
        other_keys = [("other", a, s) for _, a, s in keys]
        both = {name: np.r_[s, s * 100] for name, s in scores.items()}
        first = PopulationCalibration().fit(train, keys, scores, settings())
        second = PopulationCalibration().fit(
            train + other_train, keys + other_keys, both, settings()
        )
        np.testing.assert_array_equal(first.score(keys, scores)[0], second.score(keys, scores)[0])

    def test_sparse_and_missing_groups_fall_back_within_tenant(self):
        train, keys, scores = fixture()
        keep = [0, 1, 2, 3]
        model = PopulationCalibration().fit(
            train,
            [keys[i] for i in keep],
            {name: s[keep] for name, s in scores.items()},
            settings(),
        )
        for group in ["other", "export_heavy"]:
            ref = model.references[("synthetic", group)]
            self.assertEqual(ref["mode"], "same_tenant_fallback")
            self.assertEqual(ref["source"], ("synthetic", "__tenant__"))
        self.assertEqual(model.references[("synthetic", "export_heavy")]["validation_sessions"], 0)
        self.assertEqual(
            model.score([keys[8]], {"rules": np.array([1.0]), "markov_deviance": np.array([1.0])})[
                2
            ],
            ["same_tenant_fallback"],
        )

    def test_zero_group_scale_uses_documented_fallback(self):
        train, keys, scores = fixture()
        scores["rules"][:3] = 0
        model = PopulationCalibration().fit(train, keys, scores, settings())
        self.assertEqual(
            model.references[("synthetic", "read_dominant")]["reason"], "nonpositive_group_scale"
        )

    def test_unknown_scope_and_insufficient_tenant_reject(self):
        train, keys, scores = fixture()
        model = PopulationCalibration().fit(train, keys, scores, settings())
        for scope in [("other", "opaque", "s"), ("synthetic", "unknown", "s")]:
            with self.assertRaisesRegex(ValueError, "unknown actor scope"):
                model.score([scope], {"rules": np.ones(1), "markov_deviance": np.ones(1)})
        with self.assertRaisesRegex(ValueError, "insufficient validation"):
            PopulationCalibration().fit(
                train, keys[:1], {k: a[:1] for k, a in scores.items()}, settings()
            )
        with self.assertRaises(ValueError):
            PopulationCalibration().fit(train, keys, scores, settings(0))
        with self.assertRaises(ValueError):
            PopulationCalibration().fit([], keys, scores, settings())
        with self.assertRaisesRegex(ValueError, "not been fitted"):
            PopulationCalibration().score(keys, scores)

    def test_shared_budget_is_not_added_across_groups(self):
        model = PopulationCalibration()
        scores = np.r_[np.ones(50) * 3, np.ones(50) * 2]
        self.assertEqual(int(model.alerts(scores, 0.02).sum()), 2)
        self.assertFalse(model.alerts(np.ones(100), 0.02).any())
        self.assertFalse(model.alerts(scores, 0).any())
        for bad in [float("nan"), -1, 2]:
            with self.assertRaises(ValueError):
                model.alerts(scores, bad)


class PopulationLeakageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, _ = generate(42, 0)
        cls.validation, _ = generate(43, 2)
        cls.plan = json.loads(DEFAULT_PLAN.read_text())
        cls.model = PopulationComparison().fit(cls.train, cls.validation, cls.plan)

    def test_inference_profiles_and_thresholds_are_frozen(self):
        frozen = digest(self.model.parameters())
        keys, scores, decisions = self.model.score(self.validation)
        changed = copy.deepcopy(self.validation)
        for row in changed:
            row["tool"] = "brand.new"
            row["population"] = "reader"
            row["scenario"] = "sequence_shift"
            row["label"] = 1
        self.model.score(changed)
        replay_keys, replay, replay_decisions = self.model.score(self.validation)
        self.assertEqual(keys, replay_keys)
        for name in scores:
            np.testing.assert_array_equal(scores[name], replay[name])
            np.testing.assert_array_equal(decisions[name], replay_decisions[name])
        self.assertEqual(frozen, digest(self.model.parameters()))

    def test_ground_truth_cannot_change_fit_or_calibration(self):
        train, val = copy.deepcopy(self.train), copy.deepcopy(self.validation)
        for row in train + val:
            row["label"] = 999
            row["population"] = "reader"
            row["scenario"] = "sequence_shift"
        other = PopulationComparison().fit(train, val, self.plan)
        self.assertEqual(digest(self.model.parameters()), digest(other.parameters()))

    def test_predeclared_freshness(self):
        parts = [p for batch in self.plan["test_batches"] for p in batch["parts"]]
        self.assertTrue(all(p["day"] > 20 for p in parts))
        self.assertFalse({8112601, 8112602, 8112603, 8112604, 42, 43} & {p["seed"] for p in parts})
        self.assertEqual(self.plan["review_budget"], 0.02)
