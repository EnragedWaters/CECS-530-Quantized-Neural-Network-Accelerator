# Visual walkthrough

An interactive companion to the notebooks and presentation. It connects the
numbers, proposed hardware, digit predictions, and memory limits in one place.

**[Start with the launchers](../ONE-CLICK-LAUNCHERS/README.md).** They handle setup
and open a local browser page on Windows, macOS, Linux, or WSL.

![Accelerator view showing a calculation across processing lanes](images/accelerator.png)

## Presentation route

Select **Start guided tour** for 13 short scenes. **Next →** sets up each example;
**Back** revisits it. The tour can be closed at any time to explore freely.

| View | What to show | Main point |
|---|---|---|
| Small numbers | Rounding, clipping, wide totals, bias, rescaling | Smaller numbers save storage but change how values are represented. INT8 products need INT32 totals. |
| Inside the accelerator | Step through the six-cycle example, then eight parallel answers | Lanes do multiply-adds; moving data also takes cycles. Narrow local reads leave lanes waiting. |
| A real digit | Inspect a pixel, hidden values, and ten scores | Both versions run the trained 784 → 64 → 10 network through our simulator. The biggest score chooses the digit. |
| Hardware limits | Baseline, more lanes, narrow connections, small buffer | Extra lanes help only when memory can feed them. Capacity and bandwidth are different limits. |

For a four-minute version: rounding → six-cycle example → parallel answers with
8 local bytes/cycle → a real digit's scores → hardware Baseline and Small buffer.
For a longer explanation, use every scene and pause for questions.

**Play, Step, Reset, speed, and the cycle slider** control the toy animation.
Space plays/pauses; arrow keys step when focus is outside an input or button.
**Full screen** hides browser chrome where supported; the browser's own full-screen
shortcut also works. Browser zoom can help on a projector.

## What the results mean

- Toy animation frames come from actual scheduling events. Playback speed changes
  the animation speed, not the modeled clock or cycle counts.
- Selecting a digit runs both matrix layers with its actual values. Independent
  numerical checks compare the scalar simulator with NumPy reference arithmetic.
  Image 8 is a useful example: the known digit is 5 and both models predict 6,
  even though the arithmetic checks pass.
- The gallery has **31 selected test images**: the original first 16 plus all
  15 FP32/INT8 disagreements. It is chosen to explain behavior, not estimate accuracy.
  The accuracy cards are the saved **10,000-image** result: 96.96% FP32 and 96.98% INT8.
- Training learned the weights. A separate 1,000-image calibration set selected
  the hidden scale before testing; that scale stays fixed while presenting.
  The demo does not learn from its gallery or adjust scales when images change.
- Integer bias, ReLU, and rescaling are calculated. They are outside the timing
  estimate, along with argmax, control, preprocessing, and bias/scale traffic.
  Final integer scores remain INT32; chart unit conversion is only for display.
- Hardware controls rerun the same scheduling rules with matched FP32/INT8
  settings. Baseline matrix stages take **19,204 / 8,025 cycles (2.393×)**.
  Changing the assumed clock changes time, not cycle counts. This is a high-level
  proposed accelerator, with no measured chip, power, or area result.
- Layers must fit in local memory. A failing configuration is shown as unavailable;
  tiling, overlapping transfers, broadcast reuse, and extra timing stages are not modeled.

## Setup help

The launchers find Python 3.10–3.14, create an isolated environment, install the
pinned NumPy version, and choose an available local port. Python 3.10–3.12 uses
NumPy 1.26.4; Python 3.13–3.14 uses NumPy 2.4.6.

Windows stores setup under `%LOCALAPPDATA%\QNNDemo\` to avoid long-path problems.
macOS/Linux/WSL use ignored `.demo-venv/` inside the repo. Environments are separated
by operating system and Python version. None changes the system's Python packages.
After moving a repo, rerun the launcher; it can recreate setup. To repair a broken
environment, remove only its demo environment directory and launch again.

On Debian/Ubuntu, a missing `venv`/`ensurepip` message usually needs the matching
`python3-venv` package installed first. A failed dependency installation needs an
internet connection and another launch. First setup should be done before class.

An already-configured Python can also run the app directly:

```sh
python -m pip install -r demo/requirements.txt
python -m demo --open --port 0
```

`--port 0` picks an available port; a fixed port such as `--port 8001` also works.
Use the launcher's `--no-browser` option when opening the address manually.
The app listens only on `127.0.0.1` and serves its own page and calculation routes.
Closing its terminal stops the server; closing the browser tab alone does not.

## Checks and provenance

```sh
python ONE-CLICK-LAUNCHERS/launch_demo.py --check
```

This sets up and runs the calculation, asset, HTTP, and launcher checks without
opening a browser. Developers can run `python -m unittest discover -s demo/tests -v`
in an environment with the runtime dependency installed.

The optional browser checks need Playwright and its Chromium browser, installed
in the same development environment:

```sh
python -m pip install -r demo/requirements.txt -r demo/requirements-dev.txt
python -m playwright install chromium
python -m demo.tests.browser_check
```

The browser checks block external requests and exercise playback, inference stages,
bad-setting recovery, all 13 tour scenes, and desktop/projector/mobile layouts.
With their default local server, backend connections are restricted to loopback too.
`--url http://127.0.0.1:PORT` checks an existing server; `--screenshots PATH` saves
actual browser captures. These tools are not required for presenting.

`runtime.py` preserves the numerical and scheduling definitions from notebooks
03 and 05; tests check notebook parity and the published timing sweeps.
`assets/metadata.json` records source results, scales, hashes, selected image IDs,
and expected predictions. Asset fingerprints are checked when the app starts.

Bundle preparation rebuilt calibrated integer weights from the verified FP32
weights and reproduced both published full-test prediction hashes before selecting
the 31 images. This one-time preparation is separate from normal launches.
To rebuild, `python -m demo.prepare_assets` downloads checksum-verified MNIST
archives as needed into the ignored cache and checks the full test set again.
Optional `--retrain` repeats notebook 05's training recipe. Use the reference
Python 3.12 / NumPy 1.26.4 environment for this reproduction step.

The submitted report, slides, notebooks, and result exports are retained as published.
