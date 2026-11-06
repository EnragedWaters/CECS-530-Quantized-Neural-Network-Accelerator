# Quantized Neural Network Accelerator

A Computer Architecture project comparing 32-bit floating-point (FP32) and
8-bit integer (INT8) calculations in a small handwritten-digit recognition network.
We study prediction accuracy, memory use, and estimated accelerator performance.

The accelerator is a software model. Its timing covers matrix calculations and
data transfers; bias, activation, rescaling, and choosing the predicted digit
are outside the timing model.

## Notebooks

| Notebook | What it does |
|---|---|
| [02 — Quantized arithmetic](notebooks/02-quantized-arithmetic.ipynb) | Explains INT8 values, INT32 totals, rounding, and clipping, with checked examples. |
| [03 — Accelerator model](notebooks/03-accelerator-model.ipynb) | Models computation and data movement; compares precision, processing lanes, and bandwidth. |
| [04 — MNIST workload](notebooks/04-mnist-workload.ipynb) | Trains the FP32 digit-recognition network and checks its predictions and accuracy. |
| [05 — Quantized predictions](notebooks/05-int8-mnist-inference.ipynb) | Compares calibrated INT8 with FP32 and verifies 16 real images through the accelerator model. |
| [06 — Results and graphs](notebooks/06-results-and-graphs.ipynb) | Loads exported experiment results and calculates graphs and summaries. |

Each notebook contains its own code. The graph notebook also needs the two
result files exported by notebooks 03 and 05.
Notebook 05 includes a mixed-precision reference and an integer prediction core.
The integer core uses INT32 biases and an INT64 temporary for rescaling. Its scale
is chosen from 1,000 calibration images and stays fixed during testing.
Simulated INT8 results match the reference exactly; FP32 results match within a
stated tolerance. Notebook 06 reads exported results rather than rerunning experiments.

## Running a notebook

1. Open [Google Colab](https://colab.research.google.com/).
2. Select **File → Upload notebook** and choose a notebook from this repository.
3. Select **Runtime → Run all**.

Notebooks 04 and 05 download MNIST data as needed and train the network during
the run. Downloaded data stays in a local cache and is ignored by Git.

For the graphs, run notebooks 03 and 05 first. Their final cells export
`accelerator-results.json` and `mnist-results.json`; in Colab, each file downloads
to your computer. Run notebook 06 and select both files when prompted.

For a quick reproduction without retraining, use the checked
[timing export](results/accelerator-results.json) and
[MNIST export](results/mnist-results.json). A full checkout loads these files
automatically. Fresh exports replace these snapshots when publishing new results.

[Project scope](docs/scope.md) · [Design references](docs/reference-review.md) · [Project report](report/project-report.md) · [Presentation and speaker notes](presentation/speaker-notes.md)

## Team members

Tuong Tran · Troy Waters
