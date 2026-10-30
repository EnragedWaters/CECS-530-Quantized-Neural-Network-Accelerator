# Project scope

The project asks how INT8 neural-network computation compares with FP32 when
both run under matching accelerator assumptions.

## Proposed implementation

- Implement checked low-precision arithmetic and a matrix accelerator model.
- Describe the arithmetic units, local storage, data movement, and scheduling.
- Use an MNIST handwritten-digit network as the workload.
- Compare INT8 with FP32 using the same inputs and matching resource settings.

A high-level software model is sufficient. Clock frequency, processing-element
count, memory capacity, and bandwidth are design choices that need explicit
values and reasons. The model does not require a physical accelerator build.

## Evaluation

| Metric | What it describes |
|---|---|
| Execution cycles | Clock ticks spent computing and moving data |
| Estimated latency | Cycles divided by the assumed clock frequency |
| Throughput | Work completed per cycle or per estimated second |
| Speedup | Baseline time divided by quantized time under matching assumptions |
| Memory requirements | Storage capacity and data movement, reported separately |
| Accuracy | Correct predictions divided by the number of test images |

The evaluation will state which operations are timed and distinguish modeled
hardware performance from measured software runtime. Results will include
reproducible commands, settings, numerical checks, and explanations of limits.

## Development steps

1. Project scope and repository setup.
2. Quantized arithmetic with known-answer tests.
3. Accelerator scheduling and memory model with cycle checks.
4. MNIST workload, quantization, and accuracy evaluation.
5. Hardware experiments, graphs, and performance analysis.

The final submission includes source code, results, graphs, the architecture and
tradeoff analysis, a report, and a presentation. INT4, additional training runs,
and more detailed hardware timing are optional extensions.
