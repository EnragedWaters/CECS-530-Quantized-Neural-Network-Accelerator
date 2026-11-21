"""Rebuild editable slide visuals from checked results and the speaking-note source.

Requires python-pptx. Run from any directory; the current deck supplies its native
Ocean Waves theme. --slides 1-7 updates a section; the default rebuilds all slides.
Photos, dataset images and actual demo captures are embedded, never linked.
"""

from pathlib import Path
import argparse
import json
from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
A = json.loads((ROOT / "results/accelerator-results.json").read_text())
M = json.loads((ROOT / "results/mnist-results.json").read_text())
NOTES = json.loads((HERE / "slide-notes.json").read_text())
P = Presentation(HERE / "project-presentation.pptx")
P.core_properties.subject = "CECS 530: visual architecture and FP32/INT8 evaluation"
W, H = 13.333333, 7.5
BG = "EFF8FB"
NAVY = "12394E"
INK = "18394C"
MUTED = "4C6D7B"
TEAL = "187A75"
BLUE = "2B7296"
ORANGE = "AB5A35"
BLUE_LIGHT = "CEE4EE"
ORANGE_LIGHT = "F0D8C5"
LINE = "B9D6DF"
WHITE = "FFFFFF"
PALE = "DCEEF3"
FONT = "Arial"
TITLES = [
    "Quantized Neural Network Accelerator",
    "Smaller numbers. Three questions.",
    "One image becomes ten scores",
    "Learn → calibrate → freeze → test",
    "Add the bias. Then rescale.",
    "Our matrix engine, one stage at a time",
    "A hand-checkable six-cycle schedule",
    "Correct arithmetic can still guess wrong",
    "Accuracy stayed almost unchanged",
    "Less data, fewer matrix-stage cycles",
    "Feed the lanes before adding more",
    "Faster loading leaves compute unchanged",
    "The timing boundary matters",
    "Precision and data supply belong together",
    "Backup · operand supply limits",
    "Backup · integer bias and rescaling",
    "Backup · actual demo views",
    "Backup · sources and photo credits",
]
LAYOUT = []


def color(c):
    return RGBColor.from_string(c)


def flat(shape):
    shape._element.spPr.append(OxmlElement("a:effectLst"))
    for r in shape._element.xpath("./p:style/a:effectRef"):
        r.set("idx", "0")
    return shape


def box(s, x, y, w, h, fill=WHITE, stroke=None, radius=True):
    sh = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    sh.fill.solid()
    sh.fill.fore_color.rgb = color(fill)
    if radius:
        sh.adjustments[0] = 0.08
    if stroke:
        sh.line.color.rgb = color(stroke)
        sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    return flat(sh)


def text(
    s, value, x, y, w, h, size=24, c=INK, bold=False, align=PP_ALIGN.LEFT, name=None
):
    sh = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    sh.name = name or ("text." + str(len(s.shapes)))
    tf = sh.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(str(value).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color(c)
        p.alignment = align
        p.line_spacing = 1.05
        p.space_after = Pt(2)
    LAYOUT.append(
        {
            "slide": list(P.slides).index(s) + 1,
            "text": str(value),
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "size": size,
        }
    )
    return sh


def line(s, x1, y1, x2, y2, c=LINE, width=2):
    sh = s.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    sh.line.color.rgb = color(c)
    sh.line.width = Pt(width)
    return flat(sh)


def arrow(s, x, y, w=0.42, h=0.28, c=TEAL, both=False):
    sh = s.shapes.add_shape(
        MSO_SHAPE.LEFT_RIGHT_ARROW if both else MSO_SHAPE.RIGHT_ARROW,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    sh.fill.solid()
    sh.fill.fore_color.rgb = color(c)
    sh.line.fill.background()
    return flat(sh)


def circle(s, x, y, d, fill=WHITE, stroke=LINE):
    sh = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color(fill)
    sh.line.color.rgb = color(stroke)
    return flat(sh)


def picture(s, name, x, y, w, h, cover=False):
    path = HERE / "assets" / name
    if cover:
        image = s.shapes.add_picture(
            str(path), Inches(x), Inches(y), width=Inches(w), height=Inches(h)
        )
        image.crop_left = image.crop_right = image.crop_top = image.crop_bottom = 0
        iw, ih = image.image.size
        ratio = iw / ih
        target = w / h
        if ratio > target:
            image.crop_left = image.crop_right = (1 - target / ratio) / 2
        else:
            image.crop_top = image.crop_bottom = (1 - ratio / target) / 2
    else:
        from PIL import Image

        with Image.open(path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        ww, hh = iw * scale, ih * scale
        image = s.shapes.add_picture(
            str(path),
            Inches(x + (w - ww) / 2),
            Inches(y + (h - hh) / 2),
            width=Inches(ww),
            height=Inches(hh),
        )
    image.name = "image." + name
    return image


def icon(s, kind, x, y, c=TEAL):
    if kind == "clock":
        circle(s, x, y, 0.72, WHITE, c)
        line(s, x + 0.36, y + 0.36, x + 0.36, y + 0.13, c, 3)
        line(s, x + 0.36, y + 0.36, x + 0.55, y + 0.44, c, 3)
    elif kind == "memory":
        box(s, x, y + 0.12, 0.9, 0.5, WHITE, c, False)
        for k in range(4):
            box(s, x + 0.09 + k * 0.19, y + 0.23, 0.12, 0.22, c, radius=False)
        for k in range(5):
            box(s, x + 0.08 + k * 0.15, y + 0.62, 0.04, 0.12, c, radius=False)
    else:
        circle(s, x, y, 0.75, WHITE, c)
        circle(s, x + 0.16, y + 0.16, 0.43, WHITE, c)
        circle(s, x + 0.29, y + 0.29, 0.17, c, c)


def fresh(index, section="PROJECT", dark=False):
    s = P.slides[index - 1]
    rids = set()
    for sh in list(s.shapes):
        rids.update(sh._element.xpath(".//@r:embed|.//@r:link|.//@r:id"))
        s.shapes._spTree.remove(sh._element)
    for rid in rids:
        if rid in s.part.rels:
            s.part.drop_rel(rid)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = color(NAVY if dark else BG)
    if index >= 15:
        s._element.set("show", "0")
    else:
        s._element.set("show", "1")
    wave = s.shapes.add_shape(
        MSO_SHAPE.WAVE, 0, Inches(7.13), P.slide_width, Inches(0.37)
    )
    wave.fill.solid()
    wave.fill.fore_color.rgb = color("175675" if dark else "D2E9EE")
    wave.line.fill.background()
    flat(wave)
    text(
        s,
        "CECS 530  /  " + section,
        0.60,
        0.20,
        11,
        0.25,
        12,
        TEAL if not dark else "ACE6D8",
        True,
    )
    text(
        s,
        f"{index:02d} / 14" if index <= 14 else f"BACKUP {index-14} / 4",
        11.6,
        7.13,
        1.1,
        0.25,
        12,
        MUTED if not dark else "C0DDE7",
        align=PP_ALIGN.RIGHT,
    )
    if index > 1:
        text(
            s,
            TITLES[index - 1],
            0.60,
            0.66,
            12.1,
            0.62,
            32,
            NAVY if not dark else WHITE,
            True,
            name="slide-title",
        )
    record = NOTES[index - 1]
    meta = (
        "Backup; outside the main timing."
        if index > 14
        else f"Suggested presenter: {record['presenter']}. Planned time: {record['seconds']} seconds."
    )
    s.notes_slide.notes_text_frame.text = (
        meta
        + "\n\nVisual cue: "
        + record["visual_cue"]
        + "\n\n"
        + record["notes"]
        + "\n\nReference details:\n"
        + record["reference"]
    )
    return s


def add_reference(s, value):
    s.notes_slide.notes_text_frame.text += "\n" + value


def s1():
    s = fresh(1, "FALL 2026 · TOPIC 15", True)
    text(
        s,
        "Quantized Neural\nNetwork Accelerator",
        0.75,
        1.6,
        7.3,
        1.7,
        44,
        WHITE,
        True,
        name="slide-title",
    )
    text(
        s, "Smaller numbers.\nA balanced data path.", 0.80, 3.65, 7, 1.05, 29, "C0DDE7"
    )
    text(s, "Troy Waters · Tuong Tran", 0.80, 5.35, 7, 0.45, 24, WHITE)
    text(s, "High-level software architecture model", 0.80, 6.15, 8, 0.4, 18, "ACE6D8")
    # Actual dataset images introduce the workload rather than a decorative stock photo.
    for j, image in enumerate([0, 1, 3, 4]):
        x = 8.65 + (j % 2) * 1.70
        y = 1.60 + (j // 2) * 1.85
        box(s, x - 0.10, y - 0.10, 1.55, 1.55, WHITE, radius=True)
        picture(s, f"digit-{image}.png", x, y, 1.35, 1.35)
    text(
        s,
        "Real MNIST test images",
        8.45,
        5.75,
        4,
        0.4,
        18,
        "C0DDE7",
        align=PP_ALIGN.CENTER,
    )


def s2():
    s = fresh(2, "THE QUESTION")
    picture(s, "fpga-board.jpg", 0.65, 1.65, 4.65, 3.55, True)
    text(s, "FPGA prototype board · hardware context", 0.65, 5.38, 4.65, 0.6, 16, MUTED)
    for j, (kind, label, question, c) in enumerate(
        [
            ("target", "Accuracy", "Same predictions?", BLUE),
            ("memory", "Memory", "Fewer bytes?", TEAL),
            ("clock", "Execution", "Fewer cycles?", ORANGE),
        ]
    ):
        x = 5.65 + j * 2.35
        icon(s, kind, x + 0.6, 1.95, c)
        text(s, label, x, 3.05, 2.3, 0.45, 25, c, True, PP_ALIGN.CENTER)
        text(s, question, x, 3.65, 2.3, 0.7, 20, INK, False, PP_ALIGN.CENTER)
    box(s, 5.65, 5.05, 6.95, 1.15, WHITE, LINE)
    text(s, "Our contribution", 5.90, 5.20, 6.3, 0.3, 18, TEAL, True)
    text(s, "Arithmetic → cycle model → checked results", 5.90, 5.64, 6.35, 0.42, 21)
    add_reference(
        s,
        "Real photo: WillWare, Fpgaboard.jpg (2010), public domain. Source and original: presentation/visual-sources.md. It depicts an FPGA prototyping board, not hardware built or measured in this project.",
    )


def s3():
    s = fresh(3, "THE WORKLOAD")
    for j, image in enumerate([0, 1, 2, 3, 4, 5]):
        picture(s, f"digit-{image}.png", 0.70 + j * 1.0, 1.65, 0.78, 0.78)
    text(s, "MNIST: labeled 28 × 28 grayscale digits", 0.70, 2.60, 9, 0.45, 23)
    for x, value, label, c in [
        (0.8, "784", "pixel inputs", BLUE),
        (4.9, "64", "hidden values", TEAL),
        (9.0, "10", "digit scores", ORANGE),
    ]:
        box(s, x, 3.50, 3.45, 1.70, WHITE, LINE)
        text(s, value, x + 0.15, 3.70, 3.15, 0.70, 46, c, True, PP_ALIGN.CENTER)
        text(s, label, x + 0.15, 4.55, 3.15, 0.40, 23, INK, False, PP_ALIGN.CENTER)
    arrow(s, 4.32, 4.06)
    arrow(s, 8.42, 4.06)
    text(s, "ReLU", 8.42, 4.70, 0.55, 0.3, 14, MUTED, align=PP_ALIGN.CENTER)
    text(
        s,
        "50,816 multiply-adds per image",
        0.8,
        6.08,
        11.65,
        0.45,
        26,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )


def s4():
    s = fresh(4, "CONFIGURE BEFORE TESTING")
    stages = [
        ("LEARN", "54,000", "training", BLUE),
        ("CALIBRATE", "1,000", "choose scale", TEAL),
        ("FREEZE", "Locked", "weights + scale", NAVY),
        ("TEST", "10,000", "separate images", ORANGE),
    ]
    for j, (label, value, sub, c) in enumerate(stages):
        x = 0.68 + j * 3.17
        box(s, x, 2.20, 2.65, 2.55, WHITE, LINE)
        text(s, label, x + 0.15, 2.44, 2.35, 0.32, 18, c, True, PP_ALIGN.CENTER)
        text(s, value, x + 0.15, 3.08, 2.35, 0.68, 35, c, True, PP_ALIGN.CENTER)
        text(s, sub, x + 0.15, 4.05, 2.35, 0.40, 21, INK, False, PP_ALIGN.CENTER)
        if j < 3:
            arrow(s, x + 2.75, 3.35, 0.30, 0.25)
    text(
        s,
        "+ 5,000 validation images monitor training",
        0.72,
        5.34,
        11.8,
        0.45,
        22,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    box(s, 2.3, 6.08, 8.7, 0.55, PALE)
    text(
        s,
        "Test images never choose the calibration scale.",
        2.45,
        6.17,
        8.4,
        0.33,
        21,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )


def s5():
    s = fresh(5, "INTEGER UNITS")
    text(
        s,
        "Illustrative values",
        0.8,
        1.48,
        11.7,
        0.35,
        18,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    stages = [
        ("MATRIX TOTAL", "20", "× 0.01 = 0.20", BLUE),
        ("ADD BIAS +4", "24", "× 0.01 = 0.24", TEAL),
        ("RESCALE ÷4", "6", "× 0.04 = 0.24", ORANGE),
    ]
    for j, (label, value, represented, c) in enumerate(stages):
        x = 0.8 + j * 4.18
        box(s, x, 2.05, 3.50, 2.8, WHITE, LINE)
        text(s, label, x + 0.20, 2.32, 3.1, 0.40, 19, c, True, PP_ALIGN.CENTER)
        text(s, value, x + 0.20, 3.0, 3.1, 0.90, 55, c, True, PP_ALIGN.CENTER)
        text(s, represented, x + 0.20, 4.20, 3.1, 0.4, 22, INK, False, PP_ALIGN.CENTER)
        if j < 2:
            arrow(s, x + 3.65, 3.35, 0.33, 0.25)
    text(
        s,
        "Rescaling preserves the represented value: 0.24",
        0.8,
        5.40,
        11.7,
        0.42,
        25,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        "INT8 operands → INT32 total + bias → INT64 rescale → INT8 hidden",
        0.8,
        6.24,
        11.7,
        0.42,
        20,
        MUTED,
        align=PP_ALIGN.CENTER,
    )


def s6():
    s = fresh(6, "PROPOSED ARCHITECTURE")
    for x, w, label, detail in [
        (0.7, 2.45, "External memory", "inputs + weights"),
        (4.05, 3.15, "Local buffer", "256 KiB resident stage"),
        (8.1, 4.5, "Processing lanes", "independent output totals"),
    ]:
        box(s, x, 2.10, w, 2.5, WHITE, LINE)
        text(
            s,
            "External\nmemory" if x < 1 else label,
            x + 0.15,
            2.30 if x < 1 else 2.42,
            w - 0.30,
            0.95 if x < 1 else 0.46,
            24 if x < 1 else 25,
            NAVY,
            True,
            PP_ALIGN.CENTER,
        )
        text(
            s,
            detail,
            x + 0.15,
            3.55 if x < 1 else 3.15,
            w - 0.30,
            0.75,
            20,
            MUTED,
            align=PP_ALIGN.CENTER,
        )
    arrow(s, 3.28, 3.12, 0.55, 0.40, both=True)
    arrow(s, 7.34, 3.12, 0.55, 0.40)
    for j in range(8):
        box(s, 8.45 + j * 0.48, 4.00, 0.35, 0.30, TEAL, radius=False)
    text(
        s,
        "32 B/cycle\nload + store",
        2.80,
        4.95,
        2.25,
        0.8,
        19,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        "32 B/cycle\noperand reads",
        6.55,
        4.95,
        2.25,
        0.8,
        19,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        "8 lanes · one MAC per lane/cycle · assumed 100 MHz",
        0.8,
        6.25,
        11.7,
        0.45,
        23,
        NAVY,
        True,
        PP_ALIGN.CENTER,
    )


def s7():
    s = fresh(7, "ONE KNOWN ANSWER")
    text(
        s,
        "2 × 4 + 3 × 5 + 1 × 6 = 29",
        0.75,
        1.55,
        11.85,
        0.65,
        34,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )
    labels = [
        ("Load", "inputs", BLUE),
        ("Load", "weights", BLUE),
        ("MAC 1", "8", TEAL),
        ("MAC 2", "23", TEAL),
        ("MAC 3", "29", TEAL),
        ("Store", "29", ORANGE),
    ]
    for j, (label, value, c) in enumerate(labels):
        x = 0.75 + j * 2.13
        circle(s, x + 0.53, 2.62, 0.60, c, c)
        text(
            s, str(j + 1), x + 0.53, 2.70, 0.60, 0.32, 21, WHITE, True, PP_ALIGN.CENTER
        )
        box(s, x, 3.48, 1.80, 1.50, WHITE, LINE)
        text(s, label, x + 0.10, 3.70, 1.6, 0.35, 20, c, True, PP_ALIGN.CENTER)
        text(s, value, x + 0.10, 4.20, 1.6, 0.45, 26, c, True, PP_ALIGN.CENTER)
        if j < 5:
            arrow(s, x + 1.88, 4.03, 0.20, 0.2)
    text(
        s,
        "Six sequential cycles = 60 ns at the assumed 100 MHz",
        0.75,
        5.75,
        11.85,
        0.55,
        26,
        NAVY,
        True,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        "One INT8 lane · load, compute and store do not overlap",
        0.75,
        6.43,
        11.85,
        0.35,
        18,
        MUTED,
        align=PP_ALIGN.CENTER,
    )


GENERATORS = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7}


def donut(s, correct, total, x, y, c):
    data = CategoryChartData()
    data.categories = ["Correct", "Incorrect"]
    data.add_series("Test images", [correct, total - correct])
    chart = s.shapes.add_chart(
        XL_CHART_TYPE.DOUGHNUT, Inches(x), Inches(y), Inches(3.55), Inches(3.55), data
    ).chart
    chart.has_legend = False
    chart.has_title = False
    hole = chart._chartSpace.xpath(".//c:holeSize")[0]
    hole.set("val", "76")
    for point, fill in zip(chart.series[0].points, [c, PALE]):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = color(fill)
        point.format.line.fill.background()
    return chart


def xy(s, rows, xkey, precisions, x, y, w, h, xmax, ymax, xunit, yunit):
    data = XyChartData()
    for label, precision, c in precisions:
        series = data.add_series(label)
        for row in rows:
            series.add_data_point(
                row["config"][xkey], A["clock_hz"] / row[precision + "_cycles"] / 1000
            )
    chart = s.shapes.add_chart(
        XL_CHART_TYPE.XY_SCATTER_LINES, Inches(x), Inches(y), Inches(w), Inches(h), data
    ).chart
    chart.has_title = False
    chart.has_legend = False
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = True
        chart.legend.font.name = FONT
        chart.legend.font.size = Pt(17)
    for axis in (chart.category_axis, chart.value_axis):
        axis.tick_labels.font.name = FONT
        axis.tick_labels.font.size = Pt(18)
        axis.tick_labels.font.color.rgb = color(MUTED)
        axis.format.line.color.rgb = color(LINE)
    chart.category_axis.minimum_scale = 0
    chart.category_axis.maximum_scale = xmax
    chart.category_axis.major_unit = xunit
    chart.value_axis.minimum_scale = 0
    chart.value_axis.maximum_scale = ymax
    chart.value_axis.major_unit = yunit
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = color(LINE)
    for series, (_, _, c) in zip(chart.series, precisions):
        series.format.line.color.rgb = color(c)
        series.format.line.width = Pt(3)
        series.marker.style = XL_MARKER_STYLE.CIRCLE
        series.marker.size = 8
        series.marker.format.fill.solid()
        series.marker.format.fill.fore_color.rgb = color(c)
        series.marker.format.line.color.rgb = color(c)
    return chart


def s8():
    s = fresh(8, "TWO DIFFERENT CHECKS")
    picture(s, "digit-8.png", 0.85, 2.03, 2.55, 2.55)
    text(s, "Known digit: 5", 0.75, 4.85, 2.75, 0.45, 24, INK, True, PP_ALIGN.CENTER)
    arrow(s, 3.65, 3.1, 0.55, 0.40)
    for y, label, c in [(1.95, "FP32", BLUE), (4.0, "INT8", ORANGE)]:
        circle(s, 4.55, y, 1.3, WHITE, c)
        text(s, "6", 4.55, y + 0.18, 1.3, 0.85, 42, c, True, PP_ALIGN.CENTER)
        text(s, label, 6.05, y + 0.36, 1.35, 0.45, 25, c, True)
    circle(s, 9.5, 2.38, 1.25, WHITE, TEAL)
    line(s, 9.78, 3.02, 9.98, 3.23, TEAL, 4)
    line(s, 9.98, 3.23, 10.48, 2.70, TEAL, 4)
    text(
        s,
        "Calculation matches\nthe reference",
        8.0,
        4.13,
        4.2,
        1.0,
        26,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        "16 images × 2 layers × 2 formats checked",
        0.75,
        6.15,
        11.8,
        0.50,
        25,
        NAVY,
        True,
        PP_ALIGN.CENTER,
    )
    add_reference(
        s,
        "Image: actual MNIST test image 8, from the checked demo bundle. Its known label is 5; both archived reference predictions are 6. The error is classification, not arithmetic.",
    )


def s9():
    s = fresh(9, "FULL TEST SET · 10,000 IMAGES")
    total = M["accuracy"]["test_images"]
    for x, label, key, c in [
        (1.40, "FP32", "fp32_correct", BLUE),
        (8.12, "INT8", "int8_correct", ORANGE),
    ]:
        correct = M["accuracy"][key]
        text(s, label, x, 1.55, 3.55, 0.5, 27, c, True, PP_ALIGN.CENTER)
        donut(s, correct, total, x, 2.08, c)
        text(
            s,
            f"{100*correct/total:.2f}%",
            x + 0.40,
            3.42,
            2.75,
            0.65,
            26,
            c,
            True,
            PP_ALIGN.CENTER,
        )
        text(
            s,
            f"{correct:,} / {total:,} correct",
            x - 0.20,
            5.75,
            3.95,
            0.45,
            23,
            INK,
            True,
            PP_ALIGN.CENTER,
        )
    text(
        s,
        "15 changed predictions · two more correct overall",
        0.8,
        6.50,
        11.7,
        0.42,
        24,
        TEAL,
        True,
        PP_ALIGN.CENTER,
    )


def s10():
    s = fresh(10, "MATCHED BASELINE")
    fp = A["baseline_layers"]["fp32"]
    q = A["baseline_layers"]["int8"]
    totals = {
        p: sum(v["total_cycles"] for v in A["baseline_layers"][p])
        for p in ("fp32", "int8")
    }
    comp = {
        p: sum(v["compute_cycles"] for v in A["baseline_layers"][p])
        for p in ("fp32", "int8")
    }
    maxbar = 6.85
    text(s, "Cycles for one image’s two matrix stages", 0.75, 1.57, 9.7, 0.4, 23, MUTED)
    for y, p, c, light in [
        (2.45, "fp32", BLUE, BLUE_LIGHT),
        (3.80, "int8", ORANGE, ORANGE_LIGHT),
    ]:
        text(s, p.upper(), 0.75, y + 0.12, 1.0, 0.42, 22, c, True)
        cw = maxbar * comp[p] / totals["fp32"]
        tw = maxbar * (totals[p] - comp[p]) / totals["fp32"]
        box(s, 2.0, y, cw, 0.65, c, radius=False).name = p + ".compute"
        box(s, 2.0 + cw, y, tw, 0.65, light, radius=False).name = p + ".transfer"
        text(s, f"{totals[p]:,}", 2.1 + cw + tw, y + 0.12, 1.4, 0.45, 23, c, True)
        text(
            s,
            f"{comp[p]:,} compute + {totals[p]-comp[p]:,} transfer",
            2.0,
            y + 0.77,
            7.2,
            0.35,
            18,
            MUTED,
        )
    picture(s, "ram-module.jpg", 10.45, 1.78, 1.62, 2.45)
    text(
        s,
        "Memory chips\nstore operand bytes",
        10.05,
        4.37,
        2.5,
        0.55,
        15,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    text(
        s, f"{totals['fp32']/totals['int8']:.3f}×", 0.8, 5.57, 4.0, 0.75, 43, TEAL, True
    )
    text(s, "matrix-stage speedup", 0.8, 6.40, 5, 0.37, 21, INK)
    text(s, "≈75% less matrix storage + traffic", 5.45, 5.85, 6.8, 0.7, 25, TEAL, True)
    add_reference(
        s,
        "Real photo: László Szalai (Beyond silence), DDR RAM-1.jpg (2007), public domain. It illustrates physical memory packaging; neither its capacity nor its speed is a parameter of our model. Photo sources: presentation/visual-sources.md.",
    )


def s11():
    s = fresh(11, "LOCAL OPERAND SUPPLY")
    text(s, "Same 32-byte/cycle local connection", 0.75, 1.63, 5.3, 0.52, 22, MUTED)
    for y, label, active, c in [
        (2.53, "FP32 · 8 bytes per pair", 4, BLUE),
        (4.00, "INT8 · 2 bytes per pair", 8, ORANGE),
    ]:
        text(s, label, 0.78, y, 5.05, 0.38, 22, c, True)
        for j in range(8):
            box(
                s,
                0.8 + j * 0.55,
                y + 0.60,
                0.43,
                0.53,
                c if j < active else PALE,
                LINE,
                False,
            )
        text(s, f"{active} of 8 lanes working", 0.78, y + 1.13, 5.0, 0.35, 18, c, True)
    xy(
        s,
        A["lane_sweep"],
        "lanes",
        [("FP32", "fp32", BLUE), ("INT8", "int8", ORANGE)],
        6.13,
        2.20,
        6.55,
        3.85,
        32,
        25,
        8,
        5,
    )
    text(s, "Matrix-stage rate (k image-equiv./s)", 6.38, 1.65, 6.1, 0.35, 18, MUTED)
    text(s, "● FP32", 7.4, 6.03, 1.9, 0.30, 17, BLUE)
    text(s, "● INT8", 9.5, 6.03, 1.9, 0.30, 17, ORANGE)
    text(s, "Processing lanes", 7.7, 6.35, 3.7, 0.35, 18, MUTED, align=PP_ALIGN.CENTER)
    text(
        s, "16 → 32 lanes: no further INT8 gain", 0.78, 6.55, 10.2, 0.36, 23, TEAL, True
    )
    add_reference(
        s,
        "The left diagram shows the actual baseline: eight physical lanes and 32 local bytes/cycle. The right sweep increases physical lanes with both bandwidths fixed. Rates are thousand image-equivalents/s for matrix stages only.",
    )


def s12():
    s = fresh(12, "EXTERNAL TRANSFERS")
    rows = A["external_bandwidth_sweep"]
    compute = 3200
    first = rows[0]["int8_cycles"] - compute
    last = rows[-1]["int8_cycles"] - compute
    text(
        s,
        "32 lanes · local reads fixed at 32 B/cycle",
        0.75,
        1.53,
        11.7,
        0.42,
        23,
        MUTED,
    )
    xy(
        s,
        rows,
        "external_bytes_per_cycle",
        [("INT8", "int8", ORANGE)],
        0.65,
        2.45,
        8.2,
        3.70,
        128,
        30,
        32,
        5,
    )
    text(s, "INT8 matrix-stage rate (k image-equiv./s)", 0.95, 2.08, 7.5, 0.35, 18, ORANGE)
    text(
        s,
        "External bandwidth (bytes/cycle)",
        1.7,
        6.32,
        6.2,
        0.35,
        18,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    icon(s, "clock", 10.22, 2.18, TEAL)
    text(s, f"{compute:,}", 9.2, 3.18, 3.1, 0.65, 40, TEAL, True, PP_ALIGN.CENTER)
    text(
        s,
        "compute cycles\nat every point",
        9.2,
        3.96,
        3.1,
        0.85,
        23,
        INK,
        False,
        PP_ALIGN.CENTER,
    )
    text(
        s,
        f"{first:,} → {last:,}",
        8.9,
        5.32,
        3.8,
        0.48,
        29,
        ORANGE,
        True,
        PP_ALIGN.CENTER,
    )
    text(s, "transfer cycles", 9.2, 5.99, 3.1, 0.4, 22, MUTED, align=PP_ALIGN.CENTER)
    add_reference(
        s,
        "Graph rates are thousand image-equivalents/s for matrix stages. External bandwidth changes load/store time; local operand bandwidth still caps compute. At the two endpoint configurations the INT8 total is 9,695 versus 3,608 cycles.",
    )


def s13():
    s = fresh(13, "WHAT THE ESTIMATE COUNTS")
    stages = [
        ("Matrix 1", "+ transfers", True),
        ("Bias · ReLU", "rescale", False),
        ("Matrix 2", "+ transfers", True),
        ("Bias", "select digit", False),
    ]
    for j, (top, bottom, timed) in enumerate(stages):
        x = 0.72 + j * 3.19
        fill = TEAL if timed else WHITE
        c = WHITE if timed else MUTED
        box(s, x, 2.05, 2.65, 1.58, fill, LINE)
        text(s, top, x + 0.15, 2.31, 2.35, 0.43, 24, c, True, PP_ALIGN.CENTER)
        text(s, bottom, x + 0.15, 2.98, 2.35, 0.40, 21, c, False, PP_ALIGN.CENTER)
        text(
            s,
            "TIMED" if timed else "UNTIMED",
            x + 0.15,
            3.89,
            2.35,
            0.35,
            18,
            TEAL if timed else MUTED,
            True,
            PP_ALIGN.CENTER,
        )
        if j < 3:
            arrow(s, x + 2.77, 2.69, 0.30, 0.23)
    for x, large, small in [
        (0.8, "34 hidden clips", "out of 640,000 values"),
        (5.0, "Extra numeric work", "calibration + checks"),
        (9.2, "Not measured", "chip area + power"),
    ]:
        line(s, x, 5.10, x + 3.3, 5.10, LINE, 2)
        text(s, large, x, 5.42, 3.3, 0.65, 25, TEAL, True)
        text(s, small, x, 6.18, 3.3, 0.60, 20, MUTED)


def s14():
    s = fresh(14, "THE TAKEAWAY", True)
    acc = 100 * M["accuracy"]["int8_correct"] / M["accuracy"]["test_images"]
    total = {
        p: sum(v["total_cycles"] for v in A["baseline_layers"][p])
        for p in ("fp32", "int8")
    }
    values = [
        ("target", f"{acc:.2f}%", "INT8 test accuracy", "BCDDEB"),
        (
            "clock",
            f"{total['fp32']/total['int8']:.3f}×",
            "matrix-stage speedup",
            "ACE6D8",
        ),
        ("memory", "≈75%", "less matrix traffic", "FFD09D"),
    ]
    for j, (kind, value, label, c) in enumerate(values):
        x = 0.85 + j * 4.18
        icon(s, kind, x + 1.20, 2.22, TEAL)
        text(s, value, x, 3.48, 3.55, 0.9, 43, c, True, PP_ALIGN.CENTER)
        text(s, label, x, 4.65, 3.55, 0.65, 22, WHITE, False, PP_ALIGN.CENTER)
    text(
        s,
        "Smaller operands need a balanced data path.",
        0.8,
        6.10,
        11.8,
        0.55,
        28,
        WHITE,
        True,
        PP_ALIGN.CENTER,
    )


def s15():
    s = fresh(15, "REFERENCE · LANE SUPPLY")
    picture(s, "demo-lanes.png", 0.70, 1.53, 11.95, 3.75)
    text(
        s,
        "32 B/cycle ÷ 8 B/pair = 4 FP32 MACs/cycle",
        0.80,
        5.53,
        11.8,
        0.42,
        24,
        BLUE,
        True,
    )
    text(
        s,
        "32 B/cycle ÷ 2 B/pair = 16 INT8 MACs/cycle; limited to 8 installed lanes",
        0.80,
        6.14,
        11.8,
        0.48,
        22,
        ORANGE,
        True,
    )
    add_reference(
        s,
        "Actual headless capture of demo step 3 at source f2fe21e, with identical hardware/workload and only precision changing. Screenshot is software output, not a physical accelerator photograph. The second layer’s ten outputs still create output-group tails as described in the original notes.",
    )


def s16():
    s = fresh(16, "REFERENCE · INTEGER CORE")
    text(
        s,
        "bias_INT32 = round(bias_FP32 / (input_scale × weight_scale))",
        0.75,
        1.63,
        11.8,
        0.55,
        23,
        NAVY,
        True,
    )
    labels = [
        "INT32 total",
        "ReLU",
        "INT64 product",
        "Round + shift",
        "Clip 0–127",
        "INT8 hidden",
    ]
    for j, label in enumerate(labels):
        x = 0.75 + j * 2.12
        box(s, x, 2.78, 1.80, 1.45, WHITE, LINE)
        text(s, label, x + 0.1, 3.08, 1.60, 0.85, 21, TEAL, True, PP_ALIGN.CENTER)
        if j < 5:
            arrow(s, x + 1.87, 3.36, 0.20, 0.20)
    text(s, "Hidden scale: 0.1018513807", 0.8, 4.98, 11.7, 0.45, 25, INK)
    text(
        s,
        "Multiplier 464,594 / 2³⁰ · ties-to-even rounding",
        0.8,
        5.60,
        11.7,
        0.45,
        25,
        INK,
    )
    text(
        s,
        "Final scores remain INT32; argmax uses those raw scores.",
        0.8,
        6.31,
        11.7,
        0.40,
        22,
        MUTED,
    )


def s17():
    s = fresh(17, "REFERENCE · CHECKED SOFTWARE OUTPUT")
    text(
        s,
        "Actual MNIST image 0 · both formats predict 7",
        0.75,
        1.55,
        11.8,
        0.4,
        23,
        TEAL,
        True,
    )
    picture(s, "demo-scores.png", 0.70, 2.12, 11.95, 3.95)
    text(
        s,
        "Actual demo capture · verified arithmetic · software model",
        0.75,
        6.35,
        11.8,
        0.42,
        21,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    add_reference(
        s,
        "Actual headless capture of demo step 4, image 0, at repository source f2fe21e. No values were edited into this image. The archived notebook checks/reproduction procedure remain in the original speaking notes and report.",
    )


def linked(s, label, url, x, y, w, size=20):
    sh = text(s, label, x, y, w, 0.48, size, BLUE)
    sh.text_frame.paragraphs[0].runs[0].hyperlink.address = url


def s18():
    s = fresh(18, "REFERENCE · DESIGN AND VISUALS")
    text(s, "Design references", 0.75, 1.66, 5.65, 0.40, 25, TEAL, True)
    for y, title, url in [
        (2.35, "Brevitas · quantization choices", "https://github.com/Xilinx/brevitas"),
        (3.16, "FINN · architecture and parallelism", "https://github.com/Xilinx/finn"),
        (3.97, "Umuroglu et al. · FINN (2017)", "https://arxiv.org/abs/1612.07119"),
        (
            4.78,
            "Jacob et al. · integer inference (2018)",
            "https://arxiv.org/abs/1712.05877",
        ),
    ]:
        linked(s, title, url, 0.78, y, 5.75)
    text(s, "Real photographs", 7.10, 1.66, 5.5, 0.40, 25, TEAL, True)
    linked(
        s,
        "FPGA board · WillWare · public domain",
        "https://commons.wikimedia.org/wiki/File:Fpgaboard.jpg",
        7.1,
        2.35,
        5.5,
    )
    linked(
        s,
        "RAM · László Szalai · public domain",
        "https://commons.wikimedia.org/wiki/File:DDR_RAM-1.jpg",
        7.1,
        3.16,
        5.5,
    )
    text(s, "Project images and captures", 7.1, 4.1, 5.5, 0.40, 23, TEAL, True)
    text(s, "Verified MNIST pixels + actual demo views", 7.1, 4.78, 5.5, 0.8, 21, INK)
    text(
        s,
        "Exact numerical sources: the two checked JSON exports",
        0.78,
        6.03,
        11.8,
        0.40,
        23,
        NAVY,
        True,
    )
    text(
        s,
        "Full photo provenance and links: presentation/visual-sources.md",
        0.78,
        6.57,
        11.8,
        0.35,
        18,
        MUTED,
    )
    add_reference(
        s,
        "Photographer releases, original-file URLs and SHA-256 hashes: presentation/assets/sources.json and presentation/visual-sources.md. Neither photograph depicts our proposed accelerator. All other visuals are actual project data/captures or native PowerPoint diagrams; no AI-generated bitmap images are included.",
    )


GENERATORS.update(
    {
        8: s8,
        9: s9,
        10: s10,
        11: s11,
        12: s12,
        13: s13,
        14: s14,
        15: s15,
        16: s16,
        17: s17,
        18: s18,
    }
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slides", default="1-18")
    args = parser.parse_args()
    selected = []
    for part in args.slides.split(","):
        if "-" in part:
            a, b = map(int, part.split("-"))
            selected.extend(range(a, b + 1))
        else:
            selected.append(int(part))
    for index in selected:
        GENERATORS[index]()
    P.save(HERE / "project-presentation.pptx")
    audit = ROOT / "_local/visual-presentation"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "layout.json").write_text(json.dumps(LAYOUT, indent=2))
    print("Built editable slides:", selected)


if __name__ == "__main__":
    main()
