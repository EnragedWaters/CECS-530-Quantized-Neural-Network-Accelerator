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


class InspectionTests(unittest.TestCase):
    def test_terms_totals_biases_and_rescaling_match_independent_arithmetic(self):
        import numpy as np

        bundle = load_bundle()
        model = bundle["int8"]
        for image_id in (0, 8, 158):
            result = predict_example(
                image_id, AcceleratorConfig(8, 262144, 32, 32), bundle
            )
            for layer, inputs, weights, bias in (
                ("first", result["inputs_int8"], model["w1"], model["b1"]),
                ("second", result["int8"]["hidden"], model["w2"], model["b2"]),
            ):
                d = result["inspection"][layer]
                j = d["output_index"]
                expected = sum(int(v) * int(w) for v, w in zip(inputs, weights[:, j]))
                self.assertEqual(d["raw_total"], expected)
                self.assertEqual(d["bias"], int(bias[j]))
                self.assertEqual(d["term_count"], len(inputs))
                self.assertEqual(len(d["terms"]), 3)
                for term in d["terms"]:
                    self.assertEqual(
                        term["product"],
                        int(inputs[term["index"]]) * int(weights[term["index"], j]),
                    )
            d = result["inspection"]["first"]
            j = d["output_index"]
            self.assertEqual(d["biased_total"], d["raw_total"] + d["bias"])
            self.assertEqual(d["relu_total"], max(0, d["biased_total"]))
            numerator = d["relu_total"] * model["multiplier"]
            denominator = 1 << model["shift"]
            q, rem = divmod(numerator, denominator)
            expected = min(
                127,
                q + int(2 * rem > denominator or (2 * rem == denominator and q % 2)),
            )
            self.assertEqual(d["stored_hidden"], expected)
            self.assertEqual(d["stored_hidden"], result["int8"]["hidden"][j])
            self.assertEqual(
                result["inspection"]["second"]["score"], result["int8"]["scores"][0]
            )


if __name__ == "__main__":
    unittest.main()
