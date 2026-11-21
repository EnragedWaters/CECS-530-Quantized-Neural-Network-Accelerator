"""Check that packaged weights, calibration, and examples match the report."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from demo.bundle import ASSETS, load_bundle
from demo import runtime as core

ROOT = Path(__file__).resolve().parents[2]


class BundleTests(unittest.TestCase):
    def test_bundle_matches_published_settings_and_predictions(self):
        b = load_bundle()
        saved = json.loads(
            (ROOT / "results/mnist-results.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            b["metadata"]["fp32_parameter_sha256"], saved["fp32_parameter_sha256"]
        )
        self.assertEqual(b["metadata"]["quantization"], saved["quantization"])
        inputs = b["pixels"].astype(np.float32) / np.float32(255)
        _, scores = core.forward_fp32(inputs, b["fp32"])
        actual = core.forward_integer_int8(
            core.quantize_int8(inputs, 1 / 127), b["int8"]
        )
        self.assertEqual(
            scores.argmax(1).tolist(),
            [e["fp32_prediction"] for e in b["metadata"]["examples"]],
        )
        self.assertEqual(
            actual["scores"].argmax(1).tolist(),
            [e["int8_prediction"] for e in b["metadata"]["examples"]],
        )
        self.assertEqual(sum(e["disagreement"] for e in b["metadata"]["examples"]), 15)
        self.assertTrue(set(range(16)) <= set(b["indices"].tolist()))
        self.assertEqual(b["int8"]["multiplier"], 464594)
        self.assertFalse(b["fp32"]["w1"].flags.writeable)

    def test_modified_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for p in ASSETS.iterdir():
                shutil.copyfile(p, Path(d) / p.name)
            with (Path(d) / "network.npz").open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(ValueError, "asset changed"):
                load_bundle(d)


if __name__ == "__main__":
    unittest.main()
