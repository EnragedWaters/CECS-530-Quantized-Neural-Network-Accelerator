# Repository guide

This is the CECS 530 Quantized Neural Network Accelerator project. The notebooks,
report, and presentation contain the published semester work. The browser demo
explains that work with actual calculations and the same timing assumptions.

## Folder layout

- `ONE-CLICK-LAUNCHERS/`: presenter entry point. Keep Windows/macOS/Linux launchers
  together; `launch_demo.py` resolves the repo from its own file location.
- `demo/`: local Python server, checked arithmetic/scheduler, browser UI, bundled
  model/examples, tests, and the detailed demo guide. No CDN or Node runtime.
- `notebooks/`: independently runnable notebooks 02–06; retain that independence.
- `results/`: the two published experiment exports used by the report and graphs.
- `report/` and `presentation/`: submitted deliverables and speaking guide.
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
