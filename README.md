# Quantized Neural Network Accelerator

## 1. Project Overview

A Computer Architecture project comparing INT8 and FP32 neural-network
calculations.

The [arithmetic notebook](notebooks/02-quantized-arithmetic.ipynb) includes
explanations, examples, and 13 checks.

This project evaluates a small MNIST neural network with FP32 and INT8
arithmetic, then uses a software accelerator simulator to compare their modeled
execution under several hardware configurations.

> **Important:** Accelerator cycles, latency, throughput, and speedup in this
> project are **simulated/modeled results**, not measurements from physical
> accelerator hardware. The simulator is a simplified model; results depend on
> its scheduling, memory, lane, and clock assumptions.

## 2. Goal

The goal is to study the trade-offs between numerical accuracy, data movement,
and modeled performance when replacing FP32 operations with INT8 operations.
Both numerical evaluation and accelerator comparisons use the same MNIST
workload. The reported performance is intended to illustrate the modeled
design, not predict performance on a particular manufactured device.

## 3. Repository Structure

| Path | Purpose |
|---|---|
| `notebooks/02-quantized-arithmetic.ipynb` | Quantized arithmetic explanations, examples, and 13 checks |
| `notebooks/03-accelerator-model.ipynb` | Software accelerator model |
| `notebooks/04-mnist-workload copy.ipynb` | MNIST workload |
| `notebooks/05-int8-mnist-inference.ipynb` | INT8 MNIST inference and accuracy evaluation |
| `notebooks/06-results-and-graphs.ipynb` | Results, experiments, and graphs |
| `notebooks/mnist-cache/` | Cached MNIST dataset files |
| `docs/scope.md` | Project scope and evaluation metrics |
| `docs/reference-review.md` | Design context and comparisons with Brevitas and FINN |

## 4. Neural Network Workload

The workload is a small, fully connected neural network for classifying
28-by-28 MNIST images. Each image is flattened into 784 input values and passed
through two matrix layers:

| Layer | Matrix operation | MACs |
|---|---:|---:|
| 1 | `1 x 784 @ 784 x 64` | 50,176 |
| 2 | `1 x 64 @ 64 x 10` | 640 |
| **Total per image** |  | **50,816** |

The ten outputs correspond to the MNIST digit classes.

## 5. Quantization

The project compares an FP32 baseline with post-training INT8 inference. The
INT8 path uses INT8 weights and activations, performs INT8 multiplication, and
uses INT32 accumulation. The reported accuracies are evaluated on the MNIST
test workload:

- FP32 accuracy: **96.96%**
- INT8 accuracy: **96.99%**

These results show that the evaluated INT8 model retained accuracy in this
experiment. They do not establish that quantization will preserve accuracy for
other models, datasets, or quantization policies.

## 6. Accelerator Model

The software model evaluates the two matrix layers using configurable
processing lanes and external-memory bandwidth. It schedules loading,
computation, and storing as separate phases; lanes calculate separate outputs,
and an incomplete final lane group is allowed. The model accounts for operand
traffic and uses the selected bandwidth in its cycle estimates.

This is a simplified sequential matrix-accelerator model, not an RTL
implementation, cycle-accurate physical design, or FPGA/ASIC measurement.
Its modeled timing and traffic reflect the simulator's assumptions and should
not be interpreted as measured system performance.

## 7. Experimental Setup

The experiments compare FP32 and INT8 with matching workload and accelerator
assumptions. They include:

- Baseline performance with **8 lanes**.
- Lane scaling at **4, 8, 16, and 32 lanes**.
- Memory bandwidth sweeps at **8, 16, 32, 64, and 128 bytes/cycle**.
- Accuracy and external-memory traffic comparisons between FP32 and INT8.

The lane and bandwidth sweeps are simulator configurations. They are not
physical accelerator configurations or measurements.

## 8. Results

The baseline comparison uses 8 lanes. All cycle and latency values in this
table are **modeled**; external traffic is reported by the simulator.

| Metric | FP32 | INT8 |
|---|---:|---:|
| Accuracy | 96.96% | 96.99% |
| Modeled cycles | 19,204 | 8,025 |
| Modeled latency | 192.04 us | 80.25 us |
| External traffic | 206,952 bytes | 51,960 bytes |

Under these matching modeled assumptions, the INT8-to-FP32 modeled speedup is
**2.393x**. The highest observed modeled INT8 throughput in the tested sweep was
approximately **27,716 images/sec**, at **32 lanes** and **128 bytes/cycle**.
That throughput is a simulator estimate, not a measured hardware rate.

## 9. Key Findings

- In this evaluation, INT8 accuracy was close to the FP32 baseline.
- INT8 used fewer modeled cycles and fewer reported external-traffic bytes
  under the baseline configuration.
- Increasing lane count and memory bandwidth changed modeled throughput; the
  best observed tested configuration was not necessarily the most
  area-efficient or practical hardware design.
- These comparisons describe this workload and simulator. They do not account
  for all costs of implementing a real accelerator.

## 10. How to Run

To run the arithmetic notebook, open [Google Colab](https://colab.research.google.com/),
select **File → Upload notebook**, then **Runtime → Run all**. No package
installation is needed for that notebook.

The other project notebooks can be opened the same way:

1. Open [Google Colab](https://colab.research.google.com/).
2. Select **File → Upload notebook** and choose a notebook from `notebooks/`.
3. Use **Runtime → Run all** to execute that notebook.
4. For the experiment results, use the workload, INT8 inference, and results
  notebooks: `04-mnist-workload copy.ipynb`, `05-int8-mnist-inference.ipynb`,
  and `06-results-and-graphs.ipynb`.

[Project scope](docs/scope.md) · [Design references](docs/reference-review.md)

The scope document provides evaluation context, and the design references
document contains the architecture and quantization discussion.

## 11. Limitations

- Performance numbers are simulated/model-based and are not physical hardware
  measurements.
- The model is a simplified sequential matrix engine; it does not represent a
  complete processor, memory hierarchy, or fully streaming accelerator.
- Results depend on the modeled lane count, memory bandwidth, and scheduling
  assumptions.
- The evaluation covers one small MNIST network and does not establish
  generalization to other workloads.
- Accuracy and performance results do not include a comprehensive
  implementation-area, power, or physical-timing analysis.

## 12. Team Members

The project roster is not identified in the repository files. Add the team
members' names here.
