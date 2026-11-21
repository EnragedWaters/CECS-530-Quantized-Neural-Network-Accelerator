"""Run real bundled digits through both simulated matrix stages.

Every prediction is calculated here, not read from the saved accuracy table.
The independent NumPy path checks the scalar simulator's answer. Cycles cover
matrix stages and transfers, while biases and rescaling remain untimed.
"""

import numpy as np
from . import runtime as core


def stage_summary(runs, clock_hz=100_000_000):
    metrics = [r.metrics for r in runs]
    total = sum(m["total_cycles"] for m in metrics)
    compute = sum(m["compute_cycles"] for m in metrics)
    return {
        "total_cycles": total,
        "compute_cycles": compute,
        "transfer_cycles": total - compute,
        "latency_us": total / clock_hz * 1e6,
        "stage_images_per_second": clock_hz / total,
        "resident_bytes": max(m["scratchpad_required_bytes"] for m in metrics),
        "external_bytes": sum(m["external_bytes_transferred"] for m in metrics),
        "layers": metrics,
    }


def add_bias(raw, bias):
    total = np.asarray(raw, dtype=np.int64) + bias.astype(np.int64)
    if np.any(total < -(2**31)) or np.any(total > 2**31 - 1):
        raise OverflowError("Biased total exceeds INT32.")
    return total.astype(np.int32)


def predict_example(example_id, config, bundle):
    if type(example_id) is not int:
        raise ValueError("Choose an example from the gallery.")
    positions = np.flatnonzero(bundle["indices"] == example_id)
    if not len(positions):
        raise ValueError("This example is not in the offline gallery.")
    position = int(positions[0])
    pixels = bundle["pixels"][position : position + 1]
    x = pixels.astype(np.float32) / np.float32(255)
    settings = bundle["metadata"]["quantization"]
    qx = core.quantize_int8(x, settings["input_scale"])
    fp = bundle["fp32"]
    integer = bundle["int8"]
    # Use identical scheduling, actual inputs, and actual weights for both formats.
    fp1 = core.simulate_matmul(
        x.tolist(), fp["w1"].tolist(), config, precision="fp32", record_trace=False
    )
    hidden_fp = np.maximum(
        np.asarray(fp1.output, dtype=np.float32) + fp["b1"], np.float32(0)
    )
    fp2 = core.simulate_matmul(
        hidden_fp.tolist(),
        fp["w2"].tolist(),
        config,
        precision="fp32",
        record_trace=False,
    )
    scores_fp = np.asarray(fp2.output, dtype=np.float32) + fp["b2"]
    int1 = core.simulate_matmul(
        qx.tolist(),
        integer["w1"].tolist(),
        config,
        precision="int8",
        record_trace=False,
    )
    biased = add_bias(int1.output, integer["b1"])
    hidden_int, clipped = core.requantize_relu_integer(
        biased, integer["multiplier"], integer["shift"]
    )
    int2 = core.simulate_matmul(
        hidden_int.tolist(),
        integer["w2"].tolist(),
        config,
        precision="int8",
        record_trace=False,
    )
    scores_int = add_bias(int2.output, integer["b2"])
    reference_int = core.forward_integer_int8(qx, integer)
    ref_hidden, ref_scores = core.forward_fp32(x, fp)
    int_ok = bool(
        np.array_equal(scores_int, reference_int["scores"])
        and np.array_equal(hidden_int, reference_int["hidden"])
    )
    fp_ok = bool(
        np.allclose(scores_fp, ref_scores, rtol=1e-5, atol=1e-4)
        and np.allclose(hidden_fp, ref_hidden, rtol=1e-5, atol=1e-4)
    )
    if not (int_ok and fp_ok):
        raise ValueError(
            "Simulator result differs from its independent numerical reference."
        )
    # Dequantization is for the plot only; argmax above uses the raw INT32 scores.
    display_scores = scores_int.astype(np.float64) * (
        settings["activation_scale"] * settings["w2_scale"]
    )
    return {
        "example_id": example_id,
        "label": int(bundle["labels"][position]),
        "pixels": pixels[0].tolist(),
        "inputs_fp32": x[0].tolist(),
        "inputs_int8": qx[0].tolist(),
        "fp32": {
            "prediction": int(scores_fp.argmax(1)[0]),
            "hidden": hidden_fp[0].tolist(),
            "scores": scores_fp[0].tolist(),
            "metrics": stage_summary([fp1, fp2]),
        },
        "int8": {
            "prediction": int(scores_int.argmax(1)[0]),
            "hidden": hidden_int[0].tolist(),
            "hidden_display": (
                hidden_int.astype(np.float64) * settings["activation_scale"]
            )[0].tolist(),
            "scores": scores_int[0].tolist(),
            "scores_display": display_scores[0].tolist(),
            "clipped": clipped,
            "metrics": stage_summary([int1, int2]),
        },
        "verification": {"integer_exact": int_ok, "fp32_within_tolerance": fp_ok},
        "quantization": settings,
    }


# Timing sweeps use fixed dimensions and no zero-skipping. Cache identical
# configurations so changing only the clock never repeats matrix work.
from functools import lru_cache
from dataclasses import replace


@lru_cache(maxsize=256)
def dimension_metrics(config, precision):
    runs = [
        core.simulate_matmul(
            [[0] * inner],
            [[0] * columns for _ in range(inner)],
            config,
            precision=precision,
            record_trace=False,
        )
        for inner, columns in ((784, 64), (64, 10))
    ]
    return stage_summary(runs)


def hardware_experiment(config, clock_hz):
    def measure(machine, precision):
        try:
            metrics = dict(dimension_metrics(machine, precision))
            metrics.update(
                latency_us=metrics["total_cycles"] / clock_hz * 1e6,
                stage_images_per_second=clock_hz / metrics["total_cycles"],
            )
            return metrics
        except ValueError as error:
            return {"error": str(error)}

    results = {p: measure(config, p) for p in ("fp32", "int8")}
    speedup = (
        None
        if any("error" in r for r in results.values())
        else results["fp32"]["total_cycles"] / results["int8"]["total_cycles"]
    )
    lane_rows = [
        {
            "value": n,
            **{p: measure(replace(config, lanes=n), p) for p in ("fp32", "int8")},
        }
        for n in (4, 8, 16, 32)
    ]
    bandwidth_rows = [
        {
            "value": n,
            **{
                p: measure(replace(config, lanes=32, external_bytes_per_cycle=n), p)
                for p in ("fp32", "int8")
            },
        }
        for n in (8, 16, 32, 64, 128)
    ]
    return {
        "clock_hz": clock_hz,
        "results": results,
        "speedup": speedup,
        "lane_sweep": lane_rows,
        "external_sweep": bandwidth_rows,
        "bandwidth_sweep_lanes": 32,
        "local_supply": {
            "fp32": config.local_read_bytes_per_cycle // 8,
            "int8": config.local_read_bytes_per_cycle // 2,
        },
    }
