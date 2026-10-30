# Quantized Neural Network Accelerator

A CECS 530 Computer Architecture project studying how reduced numerical precision
affects neural-network computation, memory traffic, and prediction accuracy.

The proposed system is a high-level accelerator model for matrix multiplication,
using INT8 arithmetic and an FP32 baseline on an MNIST digit-recognition workload.
The model will make its compute and memory assumptions explicit.

This initial revision defines the [project scope](docs/scope.md). Arithmetic,
the accelerator simulator, the workload, and evaluated results will be introduced
in separate, tested steps.

The evaluation will cover cycles, estimated latency, throughput, speedup, memory
requirements, and accuracy. Hardware times will be estimates under stated
assumptions, separate from the Python program's measured runtime.
