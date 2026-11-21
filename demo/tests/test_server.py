"""Exercise the real loopback HTTP interface without a browser or external requests."""

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from demo.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, path, payload):
        request = Request(
            self.url + path,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
        )
        return urlopen(request)

    def test_static_page_and_small_live_calculation(self):
        with urlopen(self.url) as response:
            self.assertIn(b"Inside our accelerator", response.read())
        with self.post(
            "/api/simulate", json.dumps({"config": {"lanes": 1}})
        ) as response:
            r = json.load(response)
        self.assertEqual(r["output"], [[29]])
        self.assertEqual(r["metrics"]["total_cycles"], 6)

    def test_precision_comparison_keeps_hardware_and_workload_fixed(self):
        runs = {}
        for precision in ("fp32", "int8"):
            with self.post(
                "/api/simulate",
                json.dumps(
                    {
                        "preset": "parallel",
                        "precision": precision,
                        "config": {"lanes": 8, "local_read_bytes_per_cycle": 32},
                    }
                ),
            ) as response:
                runs[precision] = json.load(response)
        self.assertEqual(runs["fp32"]["config"], runs["int8"]["config"])
        self.assertEqual(runs["fp32"]["left"], runs["int8"]["left"])
        self.assertEqual(runs["fp32"]["right"], runs["int8"]["right"])
        self.assertEqual(runs["fp32"]["output"], runs["int8"]["output"])
        self.assertEqual(runs["int8"]["output"], [[29] * 8])
        for precision, active, waiting, pair_bytes in [
            ("fp32", 4, 4, 8),
            ("int8", 8, 0, 2),
        ]:
            run = runs[precision]
            event = next(e for e in run["trace"] if e["phase"] == "compute")
            self.assertEqual(len(event["macs"]), active)
            self.assertEqual(len(event["waiting_lanes"]), waiting)
            self.assertEqual(
                run["metrics"]["local_operand_bytes_read"] // run["metrics"]["macs"],
                pair_bytes,
            )

    def test_quantization_clipping_and_integer_units(self):
        with self.post(
            "/api/quantize", json.dumps({"value": 200, "scale": 1})
        ) as response:
            q = json.load(response)
        self.assertEqual(q["stored"], 127)
        self.assertTrue(q["clipped"])
        self.assertEqual(q["large_product"], 16129)
        self.assertEqual(q["biased_total"], 24)
        self.assertEqual(q["rescaled"], 6)

    def test_private_paths_are_not_served(self):
        for path in ("/../.git/config", "/_local/README.md", "/assets/network.npz"):
            with self.assertRaises(HTTPError) as e:
                urlopen(self.url + path)
            self.assertEqual(e.exception.code, 404)

    def test_real_prediction_and_hardware_routes_work_without_downloads(self):
        from unittest.mock import patch

        with patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("No dataset downloads during a demo"),
        ):
            with self.post("/api/infer", json.dumps({"example_id": 8})) as response:
                result = json.load(response)
            self.assertEqual(result["label"], 5)
            self.assertEqual(result["int8"]["prediction"], 6)
            self.assertTrue(result["verification"]["integer_exact"])
            with self.post(
                "/api/hardware", json.dumps({"config": {"scratchpad_bytes": 65536}})
            ) as response:
                result = json.load(response)
            self.assertIn("error", result["results"]["fp32"])
            self.assertEqual(result["results"]["int8"]["total_cycles"], 8025)
            self.assertIsNone(result["speedup"])

    def test_invalid_settings_are_readable_errors(self):
        for payload in ('{"config":{"lanes":0}}', '{"config":{"lanes":NaN}}', "[]"):
            with self.assertRaises(HTTPError) as e:
                self.post("/api/simulate", payload)
            self.assertEqual(e.exception.code, 400)
            self.assertIn("error", json.loads(e.exception.read()))


if __name__ == "__main__":
    unittest.main()
