# Presentation

Open **project-presentation.pptx** in PowerPoint to present or edit the slides.
**project-presentation.pdf** is the matching handout. No setup or internet is
needed to use either file.

The talk has 14 main slides, planned for 15 minutes, plus four hidden backups for
questions. The PDF includes all 18. [Speaker notes](speaker-notes.md) include the
presenter split, timing and a visual cue for each slide.

The Ocean Waves theme uses real MNIST digits, editable architecture diagrams and
charts from the checked results. The two real photos illustrate an FPGA board
and memory chips. [Photo credits and visual sources](visual-sources.md).

For the optional live demonstration, use the repo's
[one-click launcher](../ONE-CLICK-LAUNCHERS/README.md). The deck also embeds actual
demo captures in the backup slides, so those views remain available offline.

## Updating the slides

PowerPoint can edit the text, shapes and four charts directly. Numerical sources
are `../results/accelerator-results.json` and `../results/mnist-results.json`.
Keep matrix-stage estimates separate from full-test accuracy and whole-prediction
time. Keep the four backups hidden in the slideshow.

For a repeatable rebuild, `build_slides.py` supplies the layouts and
`slide-notes.json` supplies the notes, visual cues and timing. The existing deck
supplies the Ocean Waves master/theme. Rebuilding replaces manual edits on the
selected slides. Use a private Python environment with `python-pptx`, `Pillow`
and `numpy` installed:

```sh
python presentation/build_slides.py
python presentation/verify_slides.py
```

The builder runs from any directory. `--slides 9` or `--slides 8-14` rebuilds a
section. Update `speaker-notes.md` when the notes source changes. After slide
changes, export the PDF again with **hidden slides included**, then run the
checks. PDF checks also require Poppler's `pdftotext`; other checks run without it.
Inspect every exported page and rehearse on the actual presentation computer.
