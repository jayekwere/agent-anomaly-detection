import copy
import unittest
import numpy as np
from evaluate import evaluate, sessions, threshold_from_budget


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.parts = [sessions(seed, normal=120, anomalous=10) for seed in (42, 43, 44)]

    def test_independent_session_ids(self):
        for i in range(3):
            for j in range(i): self.assertFalse(set(self.parts[i]["ids"]) & set(self.parts[j]["ids"]))

    def test_repeated_session_ids_are_rejected(self):
        with self.assertRaises(ValueError): evaluate(self.parts[0], self.parts[0], self.parts[2])

    def test_labels_never_change_fit_or_threshold(self):
        original = evaluate(*self.parts)
        changed = copy.deepcopy(self.parts)
        for part in changed: part["y"] = 1 - part["y"]
        replay = evaluate(*changed)
        for name in original["models"]:
            self.assertEqual(original["models"][name]["thresholdFromUnlabelledValidation"],
                             replay["models"][name]["thresholdFromUnlabelledValidation"])
            self.assertEqual(original["models"][name]["test"]["alertFraction"],
                             replay["models"][name]["test"]["alertFraction"])

    def test_test_features_cannot_change_threshold(self):
        original = evaluate(*self.parts)
        changed = copy.deepcopy(self.parts)
        changed[2]["x"] *= 100
        replay = evaluate(*changed)
        for name in original["models"]:
            self.assertEqual(original["models"][name]["thresholdFromUnlabelledValidation"],
                             replay["models"][name]["thresholdFromUnlabelledValidation"])

    def test_ties_do_not_exceed_budget(self):
        scores = np.array([0, 1, 1, 1, 1, 1, 2, 3, 4, 5])
        threshold = threshold_from_budget(scores, 0.2)
        self.assertLessEqual(float((scores > threshold).mean()), 0.2)

    def test_invalid_budget_fails(self):
        for budget in (0, 1, -1):
            with self.assertRaises(ValueError): threshold_from_budget(np.array([0, 1]), budget)


if __name__ == "__main__": unittest.main()
