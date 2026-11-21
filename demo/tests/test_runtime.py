"""Check the animation runtime against the original standalone notebook code."""
import ast
import json
import math
import random
import struct
import unittest
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import numpy as np
from demo import runtime as core

ROOT = Path(__file__).resolve().parents[2]

def notebook_reference():
    namespace = dict(__name__=core.__name__, asdict=asdict, dataclass=dataclass,
                     replace=replace, math=math, struct=struct, np=np,
                     INT8_MIN=-128, INT8_MAX=127,
                     INT32_MIN=-(2**31), INT32_MAX=2**31-1)
    nb = json.loads((ROOT/'notebooks/03-accelerator-model.ipynb').read_text())
    for c in nb['cells']:
        if c.get('id') not in ('helpers', 'simulator'):
            continue
        source = ''.join(c['source'])
        definitions = [n for n in ast.parse(source).body
                       if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<notebook reference>', 'exec'), namespace)
    return namespace

class RuntimeTests(unittest.TestCase):
    def test_six_cycles_and_answer(self):
        r = core.simulate_matmul([[2,3,1]], [[4],[5],[6]], core.AcceleratorConfig(1,262144,32,32))
        self.assertEqual(r.output, [[29]])
        self.assertEqual(r.metrics['total_cycles'], 6)
        self.assertEqual([e['phase'] for e in r.trace], ['load_inputs','load_weights','compute','compute','compute','store_outputs'])

    def test_random_configs_match_notebook(self):
        ref = notebook_reference()
        rng = random.Random(530)
        for precision in ('int8','fp32'):
            for lanes in (1,4,8,16):
                for bandwidth in (8,32):
                    left = [[rng.randint(-9,9) for _ in range(5)]]
                    right = [[rng.randint(-9,9) for _ in range(10)] for _ in range(5)]
                    config = core.AcceleratorConfig(lanes,262144,bandwidth,16)
                    actual = core.simulate_matmul(left,right,config,precision=precision)
                    expected = ref['simulate_matmul'](left,right,config,precision=precision)
                    self.assertEqual(actual.output, expected.output)
                    self.assertEqual(actual.metrics, expected.metrics)

    def test_trace_distinguishes_waiting_from_unused(self):
        r = core.simulate_matmul([[2]], [[3]*10],core.AcceleratorConfig(8,4096,8,32))
        events = [e for e in r.trace if e['phase']=='compute']
        self.assertEqual(events[0]['waiting_lanes'], [4,5,6,7])
        self.assertEqual(events[-1]['unused_lanes'], [2,3,4,5,6,7])
        self.assertEqual(events[0]['macs'][0]['accumulator_before'],0)

    def test_fp32_trace_product_has_actual_rounding(self):
        r = core.simulate_matmul([[1.1]],[[1.2]],core.AcceleratorConfig(1,4096,32,32),precision='fp32')
        op = next(e for e in r.trace if e['phase']=='compute')['macs'][0]
        self.assertEqual(op['product'],core.fp32(op['left']*op['right']))
        self.assertEqual(op['product'],op['accumulator'])

    def test_published_baseline_cycles(self):
        saved=json.loads((ROOT/'results/accelerator-results.json').read_text())
        config=core.AcceleratorConfig(**saved['base_config'])
        for precision,total in [('fp32',19204),('int8',8025)]:
            runs=[core.simulate_matmul([[0]*n],[[0]*m for _ in range(n)],config,precision=precision,record_trace=False) for n,m in [(784,64),(64,10)]]
            self.assertEqual(sum(r.metrics['total_cycles'] for r in runs),total)
            for actual,expected in zip(runs,saved['baseline_layers'][precision]):
                for key in actual.metrics:self.assertEqual(actual.metrics[key],expected[key])

    def test_capacity_and_precision_errors(self):
        with self.assertRaisesRegex(ValueError,'need'):
            core.simulate_matmul([[2,3,1]],[[4]*8,[5]*8,[6]*8],core.AcceleratorConfig(8,58,32,32))
        with self.assertRaisesRegex(ValueError,'local read'):
            core.simulate_matmul([[1]],[[2]],core.AcceleratorConfig(1,4096,2,32),precision='fp32')
        with self.assertRaises(OverflowError):core.checked_mac(2**31-1,1,1)

    def test_integer_units_and_rounding(self):
        bias=core.quantize_bias_int32(np.array([.04]),.01)
        self.assertEqual(bias.tolist(),[4])
        hidden,clipped=core.requantize_relu_integer(np.array([[24,-1]],dtype=np.int32),1,2)
        self.assertEqual(hidden.tolist(),[[6,0]])
        self.assertEqual(clipped,0)
        self.assertEqual(core.quantize_int8([.5,1.5,200],1).tolist(),[0,2,127])

if __name__=='__main__':unittest.main()
