"""Real digits must agree with the archived experiment and independent arithmetic."""
import unittest
from demo.bundle import load_bundle
from demo.experiment import predict_example
from demo.runtime import AcceleratorConfig

class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bundle=load_bundle()
    def test_every_bundled_example_matches_published_predictions(self):
        config=AcceleratorConfig(8,262144,32,32)
        for e in self.bundle['metadata']['examples']:
            r=predict_example(e['id'],config,self.bundle)
            self.assertEqual(r['fp32']['prediction'],e['fp32_prediction'],e['id'])
            self.assertEqual(r['int8']['prediction'],e['int8_prediction'],e['id'])
            self.assertTrue(all(r['verification'].values()))
            self.assertEqual(r['fp32']['metrics']['total_cycles'],19204)
            self.assertEqual(r['int8']['metrics']['total_cycles'],8025)
    def test_wrong_guess_is_still_verified(self):
        r=predict_example(8,AcceleratorConfig(8,262144,32,32),self.bundle)
        self.assertEqual(r['label'],5);self.assertEqual(r['int8']['prediction'],6)
        self.assertTrue(r['verification']['integer_exact'])
    def test_unknown_example_rejected(self):
        with self.assertRaises(ValueError):predict_example(-1,AcceleratorConfig(),self.bundle)

if __name__=='__main__':unittest.main()
