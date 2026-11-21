"""Check embedded slide data and visual provenance without opening a window.

Run: python presentation/verify_slides.py
Requires python-pptx, NumPy and Pillow. PDF checks also use Poppler's pdftotext.
These checks complement visual inspection; they cannot replace it.
"""

from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import unittest
import zipfile
from io import BytesIO

import numpy as np
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(name):
    return json.loads((ROOT / name).read_text())


def slide_text(slide):
    return "\n".join(sh.text for sh in slide.shapes if sh.has_text_frame)


def charts(slide):
    return [sh.chart for sh in slide.shapes if sh.has_chart]


class PresentationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deck = Presentation(HERE / "project-presentation.pptx")
        cls.a = read("results/accelerator-results.json")
        cls.m = read("results/mnist-results.json")
        cls.notes = read("presentation/slide-notes.json")

    def test_structure_notes_and_planned_time(self):
        self.assertEqual(len(self.deck.slides), 18)
        self.assertEqual(sum(n["seconds"] or 0 for n in self.notes), 900)
        self.assertEqual(sum(n["seconds"] for n in self.notes[:8]), 490)
        guide = (HERE / "speaker-notes.md").read_text()
        for index, (slide, note) in enumerate(zip(self.deck.slides, self.notes)):
            with self.subTest(slide=index + 1):
                self.assertEqual(slide._element.get("show"), "1" if index < 14 else "0")
                self.assertIn(note["notes"], slide.notes_slide.notes_text_frame.text)
                self.assertIn(
                    note["visual_cue"], slide.notes_slide.notes_text_frame.text
                )
                self.assertIn(note["notes"], guide)
                self.assertIn(note["title"], guide)
                title = next(sh for sh in slide.shapes if sh.name == "slide-title")
                self.assertEqual(" ".join(title.text.split()), note["title"])

    def test_accuracy_charts_use_full_test_counts(self):
        actual = charts(self.deck.slides[8])
        self.assertEqual(len(actual), 2)
        total = self.m["accuracy"]["test_images"]
        for chart, key in zip(actual, ["fp32_correct", "int8_correct"]):
            correct = self.m["accuracy"][key]
            self.assertEqual(chart.series[0].values, (correct, total - correct))
            self.assertFalse(chart.has_title)
            self.assertEqual(
                chart._chartSpace.xpath(".//c:holeSize")[0].get("val"), "76"
            )

    def test_sweep_charts_use_numerical_x_coordinates_and_exported_cycles(self):
        for index, rows, xkey, precisions in [
            (10, self.a["lane_sweep"], "lanes", ["fp32", "int8"]),
            (
                11,
                self.a["external_bandwidth_sweep"],
                "external_bytes_per_cycle",
                ["int8"],
            ),
        ]:
            chart = charts(self.deck.slides[index])[0]
            for series, precision in zip(chart.series, precisions):
                xs = series._element.xpath(
                    ".//c:xVal/c:numRef/c:numCache/c:pt/c:v/text()"
                )
                self.assertEqual(
                    list(map(float, xs)), [r["config"][xkey] for r in rows]
                )
                ys = [
                    self.a["clock_hz"] / r[precision + "_cycles"] / 1000 for r in rows
                ]
                for actual, expected in zip(series.values, ys):
                    self.assertAlmostEqual(actual, expected, places=10)
            self.assertIn("k image-equiv./s", slide_text(self.deck.slides[index]))

    def test_cycle_bars_keep_compute_and_transfer_proportions(self):
        slide = self.deck.slides[9]
        shapes = {sh.name: sh for sh in slide.shapes}
        maximum = sum(r["total_cycles"] for r in self.a["baseline_layers"]["fp32"])
        for precision in ("fp32", "int8"):
            rows = self.a["baseline_layers"][precision]
            compute = sum(r["compute_cycles"] for r in rows)
            total = sum(r["total_cycles"] for r in rows)
            for suffix, cycles in [("compute", compute), ("transfer", total - compute)]:
                self.assertLessEqual(
                    abs(
                        shapes[precision + "." + suffix].width
                        - Inches(6.85 * cycles / maximum)
                    ),
                    1,
                )
            self.assertIn(f"{total:,}", slide_text(slide))
        self.assertIn("2.393×", slide_text(slide))
        limits = slide_text(self.deck.slides[12])
        self.assertIn("UNTIMED", limits)
        self.assertIn("chip area + power", limits)
        metadata = self.m["quantization"]
        detail = slide_text(self.deck.slides[15])
        self.assertIn(f"{metadata['multiplier']:,}", detail)
        self.assertIn(f"{metadata['activation_scale']:.10f}", detail)
        row = next(r for r in self.m["verification"]["rows"] if r["image_index"] == 8)
        self.assertEqual(
            (row["label"], row["fp32_prediction"], row["int8_prediction"]), (5, 6, 6)
        )

    def test_original_photos_and_actual_project_pixels_are_embedded(self):
        embedded = {
            hashlib.sha256(sh.image.blob).hexdigest()
            for sl in self.deck.slides
            for sh in sl.shapes
            if sh.shape_type == 13
        }
        for source in read("presentation/assets/sources.json"):
            blob = (HERE / "assets" / source["file"]).read_bytes()
            digest = hashlib.sha256(blob).hexdigest()
            self.assertEqual(digest, source["sha256"])
            self.assertIn(digest, embedded)
            self.assertIn("Public domain", source["license"])
        with np.load(ROOT / "demo/assets/examples.npz", allow_pickle=False) as examples:
            for path in (HERE / "assets").glob("digit-*.png"):
                index = int(path.stem.split("-")[1])
                slot = list(examples["indices"]).index(index)
                original = Image.fromarray(examples["pixels"][slot].reshape(28, 28))
                expected = original.resize((280, 280), Image.Resampling.NEAREST)
                self.assertTrue(
                    np.array_equal(np.asarray(Image.open(path)), np.asarray(expected))
                )
        for source in read("presentation/assets/project-visuals.json"):
            digest = hashlib.sha256(
                (HERE / "assets" / source["file"]).read_bytes()
            ).hexdigest()
            self.assertEqual(source["sha256"], digest)
            self.assertIn(digest, embedded)

    def test_editability_packages_and_slide_bounds(self):
        self.assertEqual(sum(len(charts(sl)) for sl in self.deck.slides), 4)
        for i, slide in enumerate(self.deck.slides):
            self.assertGreaterEqual(sum(sh.has_text_frame for sh in slide.shapes), 3)
            for shape in slide.shapes:
                with self.subTest(slide=i + 1, shape=shape.name):
                    self.assertGreaterEqual(shape.left, -2)
                    self.assertGreaterEqual(shape.top, -2)
                    self.assertLessEqual(
                        shape.left + shape.width, self.deck.slide_width + 2
                    )
                    self.assertLessEqual(
                        shape.top + shape.height, self.deck.slide_height + 2
                    )
        with zipfile.ZipFile(HERE / "project-presentation.pptx") as z:
            self.assertIsNone(z.testzip())
            workbooks = [
                n
                for n in z.namelist()
                if n.startswith("ppt/embeddings/") and n.endswith(".xlsx")
            ]
            self.assertEqual(len(workbooks), 4)
            for name in workbooks:
                with zipfile.ZipFile(BytesIO(z.read(name))) as workbook:
                    self.assertIsNone(workbook.testzip())
            for name in z.namelist():
                if name.endswith(".rels"):
                    from lxml import etree

                    for rel in etree.fromstring(z.read(name)):
                        if rel.get("TargetMode") == "External":
                            self.assertTrue(rel.get("Type").endswith("/hyperlink"))

    @unittest.skipUnless(shutil.which("pdftotext"), "Install Poppler to check the PDF")
    def test_matching_pdf_includes_all_main_and_backup_slides(self):
        raw = subprocess.check_output(
            ["pdftotext", "-layout", str(HERE / "project-presentation.pdf"), "-"],
            text=True,
        )
        pages = raw.split("\f")
        if not pages[-1].strip():
            pages.pop()
        self.assertEqual(len(pages), 18)
        normalize = lambda text: re.sub(r"\s+", "", text)
        for page, note in zip(pages, self.notes):
            self.assertIn(normalize(note["title"]), normalize(page))
            self.assertNotIn("\ufffd", page)
        self.assertIn("96.96%", pages[8])
        self.assertIn("96.98%", pages[8])
        self.assertIn("19,204", pages[9])
        self.assertIn("8,025", pages[9])


if __name__ == "__main__":
    unittest.main(verbosity=2)
