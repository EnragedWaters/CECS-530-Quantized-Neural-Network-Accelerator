"""Checked arithmetic and cycle simulation for the visual walkthrough.

The algorithms follow notebooks 03 and 05. Those notebooks remain standalone;
parity tests check this small reusable runtime against their definitions.
Only trace descriptions are enriched for animation; scheduling is unchanged.
"""
from dataclasses import asdict, dataclass, replace
import math
import struct
import numpy as np

INT8_MIN, INT8_MAX = -128, 127
INT32_MIN, INT32_MAX = -(2**31), 2**31 - 1


def fp32(value):
    """Round to IEEE binary32 using Python's standard library."""
    return struct.unpack("f", struct.pack("f", value))[0]


def fp32_mac(accumulator, left, right):
    """Separate rounded FP32 multiply and add; fused multiply-add is not modeled."""
    return fp32(accumulator + fp32(left * right))


def matrix_shape(matrix):
    """Reject empty or ragged matrices rather than silently truncating data."""
    if not matrix or not matrix[0]:
        raise ValueError("A matrix must have at least one row and column.")
    columns = len(matrix[0])
    if any(len(row) != columns for row in matrix):
        raise ValueError("All matrix rows must have the same length.")
    return len(matrix), columns


def multiplication_shape(left, right):
    rows, inner = matrix_shape(left)
    right_rows, columns = matrix_shape(right)
    if inner != right_rows:
        raise ValueError("Left columns must equal right rows.")
    return rows, inner, columns


def validate_int8(value):
    if type(value) is not int:
        raise TypeError("INT8 operands must be integers, not floats or booleans.")
    if not INT8_MIN <= value <= INT8_MAX:
        raise ValueError(f"Operand {value} is outside the signed INT8 range.")


def checked_mac(accumulator, left, right):
    """One multiply-and-add; flag overflow rather than use Python's wider integers."""
    validate_int8(left)
    validate_int8(right)
    if type(accumulator) is not int:
        raise TypeError("The accumulator must be an integer.")
    if not INT32_MIN <= accumulator <= INT32_MAX:
        raise OverflowError("Initial accumulator is outside the INT32 range.")
    result = accumulator + left * right
    if not INT32_MIN <= result <= INT32_MAX:
        raise OverflowError("INT32 accumulation overflow.")
    return result


@dataclass(frozen=True)
class AcceleratorConfig:
    lanes: int = 4
    scratchpad_bytes: int = 4096
    local_read_bytes_per_cycle: int = 8
    external_bytes_per_cycle: int = 4

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if self.local_read_bytes_per_cycle < 2:
            raise ValueError("The local read bus must support at least one INT8 operand pair.")


@dataclass
class SimulationResult:
    output: list[list[int | float]]
    config: AcceleratorConfig
    metrics: dict
    trace: list[dict]


def simulate_matmul(left, right, config=None, *, record_trace=True, precision="int8"):
    config = config or AcceleratorConfig()
    rows, inner, columns = multiplication_shape(left, right)
    if precision not in ("int8", "fp32"):
        raise ValueError("Supported precisions are int8 and fp32.")
    operand_bytes = 1 if precision == "int8" else 4
    pair_bytes = 2 * operand_bytes
    if config.local_read_bytes_per_cycle < pair_bytes:
        raise ValueError(f"{precision} requires {pair_bytes} local read bytes per MAC.")
    for matrix in (left, right):
        for row in matrix:
            for value in row:
                if precision == "int8":
                    validate_int8(value)
                elif not math.isfinite(float(value)):
                    raise ValueError("FP32 operands must be finite.")
    if precision == "fp32":
        left = [[fp32(value) for value in row] for row in left]
        right = [[fp32(value) for value in row] for row in right]

    input_bytes = rows * inner * operand_bytes
    weight_bytes = inner * columns * operand_bytes
    output_bytes = rows * columns * 4  # INT32 or FP32 outputs, no INT8 requantization.
    required = input_bytes + weight_bytes + output_bytes
    if required > config.scratchpad_bytes:
        raise ValueError(
            f"Resident matrices need {required} scratchpad bytes; "
            f"only {config.scratchpad_bytes} provided. Tiling is not implemented yet."
        )

    output = [[0 if precision == "int8" else 0.0] * columns for _ in range(rows)]
    trace = []
    cycle = 0
    phase_cycles = {}

    def transfer(phase, byte_count):
        nonlocal cycle
        start = cycle
        remaining = byte_count
        while remaining:
            moved = min(remaining, config.external_bytes_per_cycle)
            cycle += 1
            if record_trace:
                trace.append({"cycle": cycle, "phase": phase, "bytes": moved,
                              "phase_total_bytes": byte_count,
                              "phase_moved_bytes": byte_count - remaining + moved})
            remaining -= moved
        phase_cycles[phase] = cycle - start

    transfer("load_inputs", input_bytes)
    transfer("load_weights", weight_bytes)
    compute_start = cycle
    blocked_lane_cycles = 0
    mac_count = 0
    outputs = [(row, column) for row in range(rows) for column in range(columns)]
    macs_per_cycle = min(config.lanes, config.local_read_bytes_per_cycle // pair_bytes)
    mac = checked_mac if precision == "int8" else fp32_mac

    for group_start in range(0, len(outputs), config.lanes):
        jobs = outputs[group_start:group_start + config.lanes]
        progress = [0] * len(jobs)
        cursor = 0
        while any(k < inner for k in progress):
            cycle += 1
            ready = []
            for offset in range(len(jobs)):
                lane = (cursor + offset) % len(jobs)
                if progress[lane] < inner:
                    ready.append(lane)
            issued = ready[:macs_per_cycle]
            blocked_lane_cycles += len(ready) - len(issued)
            operations = []
            for lane in issued:
                row, column = jobs[lane]
                k = progress[lane]
                a, b = left[row][k], right[k][column]
                before = output[row][column]
                output[row][column] = mac(before, a, b)
                progress[lane] += 1
                mac_count += 1
                if record_trace:
                    operations.append({
                        "lane": lane, "output": [row, column], "k": k,
                        "left": a, "right": b,
                        "product": fp32(a * b) if precision == "fp32" else a * b,
                        "accumulator_before": before,
                        "accumulator": output[row][column],
                        "finished": progress[lane] == inner,
                    })
            cursor = (issued[-1] + 1) % len(jobs)
            if record_trace:
                trace.append({"cycle": cycle, "phase": "compute", "macs": operations,
                              "group_start": group_start, "active_lanes": issued,
                              "waiting_lanes": ready[len(issued):],
                              "unused_lanes": list(range(len(jobs), config.lanes)),
                              "finished_lanes": [lane for lane in range(len(jobs))
                                                 if progress[lane] == inner]})

    phase_cycles["compute"] = cycle - compute_start
    transfer("store_outputs", output_bytes)
    compute_cycles = phase_cycles["compute"]
    metrics = {
        "precision": precision,
        "rows": rows, "inner": inner, "columns": columns,
        "macs": mac_count, "total_cycles": cycle,
        **{f"{phase}_cycles": count for phase, count in phase_cycles.items()},
        "input_bytes": input_bytes, "weight_bytes": weight_bytes,
        "output_bytes": output_bytes, "scratchpad_required_bytes": required,
        "external_bytes_transferred": input_bytes + weight_bytes + output_bytes,
        "local_operand_bytes_read": pair_bytes * mac_count,
        "bandwidth_blocked_lane_cycles": blocked_lane_cycles,
        "compute_lane_utilization": mac_count / (compute_cycles * config.lanes),
        "macs_per_total_cycle": mac_count / cycle,
    }
    return SimulationResult(output, config, metrics, trace)


def quantize_weight_matrix(weights):
    weights = np.asarray(weights, dtype=np.float32)
    max_abs = np.max(np.abs(weights))
    scale = float(max_abs / 127.0) if max_abs else 1.0

    scaled = weights / scale
    clipped = np.clip(scaled, -127, 127)
    quantized = np.rint(clipped).astype(np.int8)
    return quantized, scale


def quantize_int8(values, scale):
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Quantization scale must be finite and positive.")
    values = np.asarray(values, dtype=np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError("Quantization values must be finite.")
    return np.rint(np.clip(values / scale, -127, 127)).astype(np.int8)


def first_layer_int8(values, weights, bias, *, input_scale, weight_scale):
    quantized_inputs = quantize_int8(values, input_scale)
    totals = quantized_inputs.astype(np.int32) @ weights.astype(np.int32)
    linear = totals.astype(np.float32) * (input_scale * weight_scale) + bias
    return totals, linear


def calibrate_activation_scale(calibration_values, weights, bias, *, input_scale, weight_scale):
    _, linear = first_layer_int8(
        calibration_values, weights, bias,
        input_scale=input_scale, weight_scale=weight_scale,
    )
    maximum = float(np.maximum(linear, np.float32(0)).max())
    return maximum / 127.0 if maximum else 1.0


def quantize_bias_int32(bias, scale):
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Bias scale must be finite and positive.")
    bias = np.asarray(bias, dtype=np.float64)
    if not np.all(np.isfinite(bias)):
        raise ValueError("Bias values must be finite.")
    rounded = np.rint(bias / scale)
    limits = np.iinfo(np.int32)
    if np.any(rounded < limits.min) or np.any(rounded > limits.max):
        raise OverflowError("Quantized bias does not fit INT32.")
    return rounded.astype(np.int32)


def checked_integer_linear(values, weights, bias):
    if values.dtype != np.int8 or weights.dtype != np.int8 or bias.dtype != np.int32:
        raise TypeError("Expected INT8 operands and INT32 bias.")
    if (values.ndim != 2 or weights.ndim != 2 or bias.ndim != 1
            or values.shape[1] != weights.shape[0] or weights.shape[1] != len(bias)):
        raise ValueError("Layer dimensions do not match.")
    if np.any(values == -128) or np.any(weights == -128):
        raise ValueError("This model uses the narrow signed range -127 through 127.")
    # Absolute bounds cover every partial sum in any accumulation order.
    bound = 127 * np.abs(weights.astype(np.int64)).sum(axis=0)
    bias64 = bias.astype(np.int64)
    limits = np.iinfo(np.int32)
    if (np.any(bound > limits.max) or np.any(bias64 + bound > limits.max)
            or np.any(bias64 - bound < limits.min)):
        raise OverflowError("Layer cannot be guaranteed to accumulate and add bias in INT32.")
    raw = values.astype(np.int32) @ weights.astype(np.int32)
    return raw, raw + bias


def requantize_relu_integer(accumulators, multiplier, shift):
    if accumulators.dtype.kind != "i":
        raise TypeError("Rescaling requires signed integer totals.")
    if (not isinstance(multiplier, (int, np.integer))
            or not isinstance(shift, (int, np.integer))
            or not 0 < multiplier < 2**31 or not 1 <= shift <= 62):
        raise ValueError("Invalid integer rescaling multiplier or shift.")
    multiplier, shift = int(multiplier), int(shift)
    positive = np.maximum(accumulators.astype(np.int64), 0)
    if np.any(positive > np.iinfo(np.int64).max // multiplier):
        raise OverflowError("Rescaling multiply would exceed INT64.")
    products = positive * multiplier
    quotient = products >> shift
    remainder = products & ((1 << shift) - 1)
    halfway = 1 << (shift - 1)
    round_up = (remainder > halfway) | ((remainder == halfway) & ((quotient & 1) != 0))
    rounded = quotient + round_up
    clipped = int(np.count_nonzero(rounded > 127))
    return np.minimum(rounded, 127).astype(np.int8), clipped


def forward_integer_int8(values, model):
    raw1, biased1 = checked_integer_linear(values, model["w1"], model["b1"])
    hidden, clipped = requantize_relu_integer(biased1, model["multiplier"], model["shift"])
    raw2, scores = checked_integer_linear(hidden, model["w2"], model["b2"])
    return {"raw1": raw1, "biased1": biased1, "hidden": hidden,
            "raw2": raw2, "scores": scores, "hidden_clipped_values": clipped}


def forward_fp32(inputs, model):
    hidden = np.maximum(inputs @ model["w1"] + model["b1"], np.float32(0))
    logits = hidden @ model["w2"] + model["b2"]
    return hidden, logits
