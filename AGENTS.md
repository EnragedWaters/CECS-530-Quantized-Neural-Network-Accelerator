# Repository guide

This is the CECS 530 Quantized Neural Network Accelerator project. The notebooks,
report, and presentation contain the published semester work. The browser demo
explains that work with actual calculations and the same timing assumptions.

## Folder layout

- `ONE-CLICK-LAUNCHERS/`: presenter entry point. Keep Windows/macOS/Linux launchers
  together; `launch_demo.py` resolves the repo from its own file location.
- `demo/`: local Python server, checked arithmetic/scheduler, browser UI, bundled
  model/examples, tests, and the detailed demo guide. No CDN or Node runtime.
  `learning.js` handles navigation; `lessons.js` contains the six presentation
  stops and optional explanations. `explore.html` keeps full controls separate.
- `notebooks/`: independently runnable notebooks 02–06; retain that independence.
- `results/`: the two published experiment exports used by the report and graphs.
- `report/` and `presentation/`: submitted deliverables and speaking guide.
- `SUBMISSION/`: only the report PDF and PowerPoint with the `group-15` filenames.
  Refresh these copies from `report/project-report.pdf` and
  `presentation/project-presentation.pptx` whenever those deliverables change;
  verify byte-for-byte equality. Keep preparation notes and archives in `_local/`.
- `docs/`: public scope and design references. Other planning belongs in `_local/`.
- `_local/`, `ROADMAP.md`, environments, caches, and prototypes are ignored/private.
  Earlier scripts/data were moved together into `_local/legacy-prototype/`;
  the current demo must not depend on them.

## Working rules

Keep the README's first-run instructions suitable for a teammate who has no WSL
or notebook experience. A downloaded and extracted repo must work through its
launcher without Git, training, or dataset downloads. First setup may install
NumPy; later launches must work offline. Use private environments, not global
package installs. Windows uses a short local cache to avoid path-length failures.

Preserve the submitted artifacts unless a requested change specifically affects
them. Quantization uses fixed calibration scales, INT32 biases/accumulation, and
an INT64 rescaling temporary. Final INT32 scores choose the digit before any
display conversion. Timing covers matrix work and transfers only. Do not silently
add bias/activation/rescaling timing, tiling, overlap, or hardware-measurement claims.

Run `python -m unittest discover -s demo/tests -v` after calculation/server/launcher
changes. For browser changes, also run `python -m demo.tests.browser_check` with
the optional development dependencies installed; see `demo/README.md`. Verify
offline behavior, invalid-setting recovery, and projector/mobile layouts when affected.
Keep the runtime and asset checks matched to the notebook/result sources.

Use small commits with plain-English titles and short descriptions. Commit/push/
merge actions follow the user's current authorization; these notes add none.
Keep class messages and private planning out of staged files. Do not submit to Canvas.

## File links

For native Windows VS Code with WSL execution, user-facing clickable links use
`/C:/Users/...`, preserving the actual path spelling. Shell commands still use
`/mnt/c/...`. A Remote WSL/Linux editor uses Linux paths instead. Prefer Markdown
companions for report/slide links; do not assume the editor opens binary documents.

## Visual learning interface

The demo supplements the existing PowerPoint. Keep the default path to six short
stops; deeper arithmetic explanations belong in Steps → Extra explanations, and
custom settings/gallery/sweeps belong in Explore. Each action reveals one clear
change, followed by its explanation. Keep the instruction, visual, result and next
action together at laptop size. Reveal predictions only at the largest-score step.
The main lane comparison holds eight lanes and the baseline 32-byte/cycle local
connection fixed: FP32 feeds four lanes, INT8 feeds all eight. Bandwidth changes
belong to the separately labeled optional experiment.

Inspection fields come from the already-checked simulation, not recreated browser
arithmetic. Selected terms must be labeled as a subset of the full dot product.
Run browser checks with `headless=True` (the default), background servers, and no
`--open`. Do not open foreground windows or change the user's focused tab. Do not
turn this slide companion into a lecture or modify submitted slides to add it.

## Presentation editing

The visual Ocean Waves deck has 14 main slides plus four hidden backups; its
PDF includes all 18. Preserve the planned 900-second talk and detailed notes.
`presentation/build_slides.py` builds native editable diagrams/charts using the
checked JSON exports and `slide-notes.json`. Update the Markdown speaking guide
when changing notes, then regenerate and inspect the matching PDF. See
`presentation/README.md` for authoring commands and the rebuild behavior.

Use relevant real photographs with documented reuse permission; no AI-generated
bitmap imagery. Keep original photo bytes and record creator, source, license,
purpose and SHA-256 under `presentation/assets/` and `visual-sources.md`. Actual
project pixels/captures have their own provenance manifest. Hardware photos are
context and must not imply that our accelerator was physically built or measured.

Run `python presentation/verify_slides.py` after deck changes. Check every main
and backup slide visually for wrapping, chart labels, contrast and picture crops.
Keep rendering headless and preserve the ignored original presentation backup.
These presentation changes do not authorize changing numerical results or the
report; normal commit/push authorization still comes from the current request.
