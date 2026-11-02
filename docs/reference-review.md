# Brevitas and FINN design references

Reviewed November 2, 2026. This review informs our custom Python model. It does
not establish numerical equivalence with Brevitas or hardware equivalence with
FINN; neither framework was installed or executed for this review.

## What each reference contributes

**Brevitas** helps define the numbers: quantization of weights, activations, and
biases, their scales, and post-training quantization versus quantization-aware
training. Its guide explicitly separates quantization from actual inference
acceleration. Our first workload comparison can use post-training quantization:
train an FP32 baseline, then quantize that same model.
[Getting-started guide](https://xilinx.github.io/brevitas/v0.13.4/getting_started.html).

**FINN** helps reason about hardware: network-specific streaming layers,
parallelism, weight storage, and verification. Our committed model is a simpler
sequential matrix engine with a shared operand-read budget. We will describe
that design explicitly and use FINN to explain its limitations.
[FINN overview](https://xilinx.github.io/finn/).

## Quantization choices to make explicit

| Topic | Reference finding | Proposed project baseline |
|---|---|---|
| Number format | Bit width, signedness, scale, and zero point are separate choices. | Record all of them; the label “INT8” is insufficient. |
| Weight range | Brevitas includes a signed, narrow-range, per-tensor 8-bit weight quantizer. | Keep −127 through 127, zero point 0, with one scale per weight matrix. |
| ReLU outputs | Brevitas' activation tutorial contrasts signed quantization with unsigned 0–255 outputs. | Our draft uses 0–127 after ReLU. Keep this simple signed baseline initially and acknowledge its smaller positive range. |
| Calibration | Brevitas activation examples can initialize learned scales from runtime statistics. | Our draft freezes a maximum-based scale from separate calibration data; it is a different policy. |
| Bias | The tutorial's INT32 bias scale is input scale × weight scale. | Keep that scale relationship and checked INT32 accumulation. |

Sources: [quantizer anatomy](https://xilinx.github.io/brevitas/v0.13.4/tutorials/anatomy_quantizer.html),
[8-bit quantizer definitions](https://github.com/Xilinx/brevitas/blob/8a252b84025b2209955dbf321b03eb38c608cdcc/src/brevitas/quant/scaled_int.py),
[activation tutorial](https://xilinx.github.io/brevitas/v0.13.4/tutorials/quant_activation_overview.html),
and [bias example](https://xilinx.github.io/brevitas/v0.13.4/getting_started.html#weights-activations-biases-quantization).

Our arithmetic already uses ties-to-even rounding, clipping, and wider totals.
A direct Brevitas numerical comparison would need matching ranges, scales,
rounding, and evaluation state; similar names do not prove identical results.
Unsigned activations remain an extension because our current scalar MAC checks
both operands as signed INT8.

## Hardware differences that matter

| FINN reference | Our model and consequence |
|---|---|
| Processing elements (PE) work on outputs in parallel; SIMD works on multiple inputs per dot-product step. | Our lanes calculate separate outputs with one MAC each cycle. We do not implement a configurable SIMD datapath. |
| FINN's matrix-vector unit requires dimensions divisible by PE and SIMD. | Our scheduler allows a partially occupied final group. Ten outputs on eight lanes therefore do not directly match a FINN PE=8 configuration. |
| FINN supports internal parameter storage and external weight modes. | Our model reloads weights for each layer and image. Transfer costs follow that assumption. |
| Layers can be composed as a streaming dataflow design. | Our load, compute, and store phases run separately. Results describe this sequential schedule. |

Sources: [folding constraints](https://github.com/Xilinx/finn/blob/38c42bf95abbdad493db0b0f5053060074698908/docs/finn/reference/folding-constraints.rst),
[memory modes](https://github.com/Xilinx/finn/blob/38c42bf95abbdad493db0b0f5053060074698908/docs/finn/reference/mem-modes.rst),
and [FINN architecture overview](https://xilinx.github.io/finn/).

FINN's analysis also reports the slowest node and a pessimistic critical-path
latency separately. Our summed matrix-stage latency must not be presented as
FINN streaming throughput or complete prediction latency.
[Performance-analysis implementation](https://github.com/Xilinx/finn/blob/38c42bf95abbdad493db0b0f5053060074698908/src/finn/analysis/fpgadataflow/dataflow_performance.py).

## What stays and what changes

Keep the arithmetic aid, MNIST data inspection, and checked sequential model.
Before adding INT8 inference, publish the exact numerical policy and its
calibration procedure. The architecture explanation should name its shared-read
budget, output-group scheduling, weight reloads, dedicated output-write ports,
and assumed clock. These are our design assumptions, not settings prescribed by
Brevitas or FINN.

Continue verifying answers independently before interpreting performance.
FINN's verification flow provides a useful example of checking functionality at
successive representations. Our checks remain our own tests.
[Verification guide](https://github.com/Xilinx/finn/blob/38c42bf95abbdad493db0b0f5053060074698908/docs/finn/verification.rst).

The existing Colab approach remains suitable for the professor-approved
high-level model. Using the full FINN toolchain, generating FPGA hardware, and adding
quantization-aware training are optional extensions. The next code increment remains the FP32 prediction baseline,
with quantization added afterward under the documented policy.

Original repositories:
[https://github.com/Xilinx/brevitas](https://github.com/Xilinx/brevitas)
and [https://github.com/Xilinx/finn](https://github.com/Xilinx/finn).
