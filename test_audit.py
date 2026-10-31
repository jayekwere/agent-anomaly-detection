import unittest

from agent_anomaly import correlate, normalize


class AuditTests(unittest.TestCase):
    def event(self, **changes):
        return dict(
            schema_version=1,
            tenant="synthetic",
            actor="agent",
            session="s",
            event_id="e",
            at="2026-01-01T00:00:00Z",
            tool="read",
            outcome="allowed",
            **changes,
        )

    def test_privacy(self):
        raw = self.event()
        raw["payload"] = "SECRET"
        self.assertNotIn("SECRET", repr(normalize(raw)))

    def test_invalid(self):
        for field, value in [
            ("at", None),
            ("at", "2026-01-01"),
            ("schema_version", 2),
            ("actor", ""),
            ("outcome", "oops"),
        ]:
            raw = self.event()
            raw[field] = value
            with self.assertRaises(ValueError):
                normalize(raw)

    def test_limits_duplicates_isolation(self):
        raw = self.event()
        with self.assertRaises(ValueError):
            correlate([raw, raw])
        with self.assertRaises(ValueError):
            correlate([raw], max_events=0)
        with self.assertRaises(ValueError):
            correlate([raw], max_session=0)
        other = dict(raw, tenant="other")
        self.assertEqual(len(correlate([raw, other])), 2)


class PipelineTests(unittest.TestCase):
    def test_out_of_order(self):
        rows = [
            AuditTests().event(),
            dict(AuditTests().event(), event_id="earlier", at="2025-01-01T00:00:00Z"),
        ]
        self.assertEqual(next(iter(correlate(rows).values()))[0].event_id, "earlier")

    def test_bad_types(self):
        for raw in [None, [], "bad"]:
            with self.assertRaises(ValueError):
                normalize(raw)

    def test_adapter(self):
        from agent_anomaly.ingestion import sentinel_v1

        wrapped = {
            "provider": "sentinel",
            "record": dict(
                seq=1,
                tenant="synthetic",
                actor="agent",
                action="tool.denied",
                outcome="denied",
                at="2026-01-01T00:00:00Z",
                detail={"tool": "admin.delete", "args": {"secret": "SECRET"}},
            ),
        }
        self.assertNotIn("SECRET", str(sentinel_v1(wrapped, "s")))

    def test_missing_model_and_nonfinite(self):
        import numpy as np

        from agent_anomaly.detectors import Detectors, budget

        with self.assertRaises(ValueError):
            Detectors().scores(np.ones((3, 8)))
        with self.assertRaises(ValueError):
            Detectors().fit(np.full((3, 8), np.nan))
        for value in [-1, 1.1, float("nan")]:
            with self.assertRaises(ValueError):
                budget([1, 2], value)
        self.assertEqual(int(budget([1, 1, 1], 0).sum()), 0)
        self.assertEqual(int(budget([1, 1, 1], 1).sum()), 3)

    def test_frozen_history_and_label_separation(self):
        import numpy as np

        from agent_anomaly.data import generate
        from agent_anomaly.detectors import Detectors
        from agent_anomaly.features import Features

        f = Features()
        rows, truth = generate(2, 0, count=50)
        _, x, _ = f.transform(rows, fit=True)
        model = Detectors().fit(x)
        test, _ = generate(3, 2, count=50)
        _, before, _ = f.transform(test)
        truth.clear()
        f.transform(list(reversed(test)))
        _, after, _ = f.transform(test)
        np.testing.assert_array_equal(before, after)
        self.assertTrue(all(np.isfinite(s).all() for s in model.scores(after).values()))

    def test_contaminated_training(self):
        from agent_anomaly.data import generate
        from agent_anomaly.detectors import Detectors
        from agent_anomaly.features import Features

        rows, _ = generate(9, 0, count=50, contamination=0.5)
        _, x, _ = Features().transform(rows, fit=True)
        self.assertEqual(len(Detectors().fit(x).scores(x)), 3)


class ArtifactTests(unittest.TestCase):
    def test_metrics_and_budget(self):
        import numpy as np
        from agent_anomaly.evaluation import measure

        y = np.array([0, 1, 0, 1])
        result = measure(y, np.array([0.0, 0.8, 0.1, 0.9]), np.array([False, True, False, True]))
        self.assertEqual(result["precision"], 1)
        self.assertEqual(result["recall"], 1)
        self.assertEqual(result["false_alerts_per_1000_sessions"], 0)

    def test_jsonl_rejection(self):
        import tempfile
        from pathlib import Path
        from agent_anomaly.ingestion import read_jsonl

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.jsonl"
            path.write_text('{"payload":"SECRET"}\n')
            with self.assertRaisesRegex(ValueError, "invalid audit input"):
                read_jsonl(path)
            with self.assertRaisesRegex(ValueError, "byte limit"):
                read_jsonl(path, max_bytes=2)

    def test_unseen_and_drift_generation(self):
        from agent_anomaly.data import generate
        from agent_anomaly.features import Features

        for unseen, drift in [(True, False), (False, True)]:
            rows, truth = generate(1, 0, count=30, contamination=1, unseen=unseen, drift=drift)
            keys, features, _ = Features().transform(rows, fit=True)
            self.assertEqual(len(keys), len(truth))
            self.assertEqual(features.shape, (30, 8))


class GeneratedArtifactTests(unittest.TestCase):
    def test_recorded_artifact_and_reject_corruption(self):
        import json
        import tempfile
        from pathlib import Path
        from agent_anomaly.artifacts import validate

        path = Path(__file__).parent / "evaluation/v2/results.json"
        data = validate(path)
        data["tests"]["held_out"]["models"]["rules"]["alerts"] = 1000
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                validate(bad)
