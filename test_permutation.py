"""Conditional null invariants, identity/order independence and shared-budget leakage tests."""

import copy
import json
import unittest

import numpy as np

from agent_anomaly.data import generate
from agent_anomaly.detectors import budget
from agent_anomaly.permutation import ConditionalPermutation, priority_order
from agent_anomaly.permutation_experiment import DEFAULT_PLAN, PermutationComparison
from agent_anomaly.sequence_experiment import digest
from test_sequence import events


def settings(**updates):
    result = {
        "replicates": 39,
        "seed": 20261101,
        "max_session_events": 256,
        "max_permutation_cells_per_batch": 25000000,
    }
    result.update(updates)
    return result


class PermutationTests(unittest.TestCase):
    def test_every_null_row_preserves_the_exact_multiset(self):
        model = ConditionalPermutation(settings())
        tools = ["a"] * 8 + ["b"] * 5 + ["c"] * 2
        null = model.null_orders(tools)
        self.assertEqual(null.shape, (39, 15))
        for row in null:
            np.testing.assert_array_equal(np.bincount(row), [8, 5, 2])

    def test_observed_order_and_identity_do_not_select_the_null(self):
        model = ConditionalPermutation(settings())
        tools = ["a"] * 8 + ["b"] * 5 + ["c"] * 2
        np.testing.assert_array_equal(
            model.null_orders(tools), model.null_orders(list(reversed(tools)))
        )
        first = model.score(events(tools))[1:]
        changed = events(tools, tenant="other", actor="opaque", session="different")
        for row in changed:
            row["label"] = 999
            row["population"] = "reader"
            row["scenario"] = "SECRET"
        second = model.score(changed)[1:]
        np.testing.assert_array_equal(first[0], second[0])
        self.assertEqual(first[1], second[1])
        self.assertNotIn("SECRET", str(second))

    def test_exact_integer_statistic_and_finite_draw_p(self):
        model = ConditionalPermutation(settings())
        _, score, details = model.score(events(["a", "a", "b", "b"]))
        d = details[0]
        self.assertEqual(d["observed_equal_adjacent_pairs"], 2)
        self.assertEqual(d["observed_statistic"], abs(4 * 2 - 4))
        self.assertEqual(int(score[0]), 39 - d["null_exceedances"])
        self.assertEqual(d["monte_carlo_p"], (1 + d["null_exceedances"]) / 40)
        null = model.null_orders(["a", "a", "b", "b"])
        stats = np.abs(4 * (null[:, :-1] == null[:, 1:]).sum(axis=1) - 4)
        self.assertEqual(d["null_exceedances"], int((stats >= 4).sum()))

    def test_constant_tool_sessions_cannot_supply_order_evidence(self):
        _, score, details = ConditionalPermutation(settings()).score(events(["a"] * 20))
        self.assertEqual(score.tolist(), [0])
        self.assertEqual(details[0]["monte_carlo_p"], 1.0)
        self.assertTrue(details[0]["all_tools_identical"])
        self.assertTrue(details[0]["sampled_null_constant"])

    def test_same_bag_can_have_different_order_scores(self):
        model = ConditionalPermutation(settings(replicates=499))
        clustered = ["a"] * 10 + ["b"] * 10
        # This ordering is near the expected adjacent-repeat count of 9.
        ordinary = list("aabbaabbaabbaabbaabb")
        self.assertEqual(sorted(clustered), sorted(ordinary))
        clustered_score = model.score(events(clustered))[1][0]
        ordinary_score = model.score(events(ordinary))[1][0]
        self.assertGreater(clustered_score, ordinary_score)

    def test_scoring_one_session_is_independent_of_other_sessions(self):
        model = ConditionalPermutation(settings())
        a = events(["a"] * 8 + ["b"] * 5, session="a")
        b = events(["c", "d"] * 8, session="b", actor="other", day=1)
        keys, scores, details = model.score(a + b)
        self.assertEqual(
            int(scores[keys.index(("synthetic", "agent", "a"))]), int(model.score(a)[1][0])
        )
        self.assertEqual(details[keys.index(("synthetic", "agent", "a"))], model.score(a)[2][0])
        np.testing.assert_array_equal(model.score(a)[1], model.score(list(reversed(a)))[1])

    def test_explicit_bounded_failures(self):
        for data in [[], events(["a"]), events(["a"] * 257)]:
            with self.assertRaises(ValueError):
                ConditionalPermutation(settings()).score(data)
        with self.assertRaisesRegex(ValueError, "work limit"):
            ConditionalPermutation(settings(max_permutation_cells_per_batch=1)).score(
                events(["a", "b"])
            )
        for value in [0, 10000, True, 2.5]:
            with self.assertRaises(ValueError):
                ConditionalPermutation(settings(replicates=value))

    def test_one_cap_with_deterministic_identity_tie_priority(self):
        keys = [("t", "a", f"s{i}") for i in range(100)]
        order = priority_order(keys, 9005)
        chosen = [keys[order[i]] for i in np.flatnonzero(budget(np.ones(100) * 499, 0.02))]
        self.assertEqual(len(chosen), 2)
        reversed_keys = list(reversed(keys))
        self.assertEqual(
            [keys[i] for i in order],
            [reversed_keys[i] for i in priority_order(reversed_keys, 9005)],
        )


class PermutationLeakageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, _ = generate(42, 0)
        cls.validation, _ = generate(43, 2, count=120)
        cls.plan = json.loads(DEFAULT_PLAN.read_text())
        cls.plan["permutation"]["replicates"] = (
            19  # Unit fixture only; fresh experiment remains 499.
        )
        cls.model = PermutationComparison().fit(cls.train, cls.validation, cls.plan)

    def test_raw_label_fields_cannot_change_fit_or_thresholds(self):
        train, val = copy.deepcopy(self.train), copy.deepcopy(self.validation)
        for row in train + val:
            row["label"] = 1
            row["population"] = "reader"
            row["scenario"] = "sequence_shift"
        replay = PermutationComparison().fit(train, val, self.plan)
        self.assertEqual(digest(self.model.parameters()), digest(replay.parameters()))

    def test_test_changes_do_not_refit_or_recalibrate(self):
        before = digest(self.model.parameters())
        keys, scores, decisions, details = self.model.score(self.validation)
        altered = copy.deepcopy(self.validation)
        for row in altered:
            row["tool"] = "novel.tool"
        self.model.score(altered)
        replay_keys, replay, replay_decisions, replay_details = self.model.score(self.validation)
        self.assertEqual(keys, replay_keys)
        self.assertEqual(details, replay_details)
        for name in scores:
            np.testing.assert_array_equal(scores[name], replay[name])
            np.testing.assert_array_equal(decisions[name], replay_decisions[name])
            self.assertLessEqual(int(decisions[name].sum()), 2)
        self.assertEqual(before, digest(self.model.parameters()))

    def test_predeclared_test_seeds_and_dates_are_new(self):
        plan = json.loads(DEFAULT_PLAN.read_text())
        parts = [p for b in plan["test_batches"] for p in b["parts"]]
        self.assertTrue(all(p["day"] > 26 for p in parts))
        self.assertFalse({42, 43, 9212601, 9212602, 9212603, 9212604} & {p["seed"] for p in parts})
        self.assertEqual(plan["permutation"]["replicates"], 499)
        self.assertEqual(plan["review_budget"], 0.02)


class PermutationArtifactTests(unittest.TestCase):
    def test_corrupt_p_values_cap_and_reader_recovery_are_rejected(self):
        from pathlib import Path
        import tempfile
        from scripts.verify_permutation_results import validate

        data = validate(Path(__file__).parent / "evaluation/permutation-v1/results.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for corruption in ["p_value", "reader", "cap", "ties"]:
                bad = copy.deepcopy(data)
                batch = bad["tests"]["fresh_permutation_joint"]
                if corruption == "p_value":
                    batch["reader_sequence_evidence"][0]["monte_carlo_p"] = 0.0
                elif corruption == "reader":
                    batch["models"]["conditional_permutation"]["reader_sequence"]["missed"] += 1
                elif corruption == "cap":
                    batch["shared_queue"]["cap_sessions"] = 48
                else:
                    batch["shared_queue"]["boundary_ties_selected"] = 1000
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    validate(path)
