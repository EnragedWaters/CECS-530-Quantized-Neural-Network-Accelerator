"""Real digits must agree with the archived experiment and independent arithmetic."""

import unittest
from demo.bundle import load_bundle
from demo.experiment import predict_example
from demo.runtime import AcceleratorConfig


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()

    def test_every_bundled_example_matches_published_predictions(self):
        config = AcceleratorConfig(8, 262144, 32, 32)
        for e in self.bundle["metadata"]["examples"]:
            r = predict_example(e["id"], config, self.bundle)
            self.assertEqual(r["fp32"]["prediction"], e["fp32_prediction"], e["id"])
            self.assertEqual(r["int8"]["prediction"], e["int8_prediction"], e["id"])
            self.assertTrue(all(r["verification"].values()))
            self.assertEqual(r["fp32"]["metrics"]["total_cycles"], 19204)
            self.assertEqual(r["int8"]["metrics"]["total_cycles"], 8025)

    def test_wrong_guess_is_still_verified(self):
        r = predict_example(8, AcceleratorConfig(8, 262144, 32, 32), self.bundle)
        self.assertEqual(r["label"], 5)
        self.assertEqual(r["int8"]["prediction"], 6)
        self.assertTrue(r["verification"]["integer_exact"])

    def test_unknown_example_rejected(self):
        with self.assertRaises(ValueError):
            predict_example(-1, AcceleratorConfig(), self.bundle)


class HardwareTests(unittest.TestCase):
    def test_baseline_and_sweeps_match_archived_cycles(self):
        import json
        from pathlib import Path
        from demo.experiment import hardware_experiment

        saved = json.loads(
            (
                Path(__file__).resolve().parents[2] / "results/accelerator-results.json"
            ).read_text(encoding="utf-8")
        )
        r = hardware_experiment(AcceleratorConfig(8, 262144, 32, 32), 100_000_000)
        self.assertAlmostEqual(r["speedup"], 19204 / 8025)
        for actual, expected in zip(r["lane_sweep"], saved["lane_sweep"]):
            for p in ("fp32", "int8"):
                self.assertEqual(actual[p]["total_cycles"], expected[p + "_cycles"])
        for actual, expected in zip(
            r["external_sweep"], saved["external_bandwidth_sweep"]
        ):
            for p in ("fp32", "int8"):
                self.assertEqual(actual[p]["total_cycles"], expected[p + "_cycles"])

    def test_clock_changes_time_not_cycles(self):
        from demo.experiment import hardware_experiment

        a = hardware_experiment(AcceleratorConfig(8, 262144, 32, 32), 100_000_000)
        b = hardware_experiment(AcceleratorConfig(8, 262144, 32, 32), 200_000_000)
        self.assertEqual(
            a["results"]["int8"]["total_cycles"], b["results"]["int8"]["total_cycles"]
        )
        self.assertEqual(
            a["results"]["int8"]["latency_us"] / 2, b["results"]["int8"]["latency_us"]
        )

    def test_invalid_format_does_not_become_zero_cycles(self):
        from demo.experiment import hardware_experiment

        r = hardware_experiment(AcceleratorConfig(8, 65536, 32, 32), 100_000_000)
        self.assertIn("error", r["results"]["fp32"])
        self.assertNotIn("error", r["results"]["int8"])
        self.assertIsNone(r["speedup"])
        r = hardware_experiment(AcceleratorConfig(8, 262144, 2, 32), 100_000_000)
        self.assertIn("error", r["results"]["fp32"])
        self.assertNotIn("error", r["results"]["int8"])


if __name__ == "__main__":
    unittest.main()
