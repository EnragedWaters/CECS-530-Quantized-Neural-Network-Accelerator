const number = (label, value, note = "", active = false) =>
  `<div class="number-card ${active ? "active" : ""}"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
const fmt = (n, d = 3) =>
  Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
export const lessons = [
  {
    id: "rounding",
    chapter: "Smaller numbers",
    title: "How does 1.23 become an integer?",
    steps: 1,
    instruction:
      "Press “Convert 1.23” to store the value in steps of 0.1. Then compare the original and reconstructed values.",
    button: "Convert 1.23",
    act: (_, api) => api("/api/quantize", { value: 1.23, scale: 0.1 }),
    render: ({ step, data }) =>
      `<div class="number-story">${number("Original FP32", 1.23, "32 bits per operand")}<span class="arrow">→</span>${number("Stored INT8", step ? data.stored : "?", "8 bits per operand", !!step)}<span class="arrow">→</span>${number("Reconstructed", step ? fmt(data.reconstructed) : "?", "integer × 0.1")}</div><p class="caption">Scale 0.1 means one integer step represents 0.1.</p>`,
    explain: ({ data }) =>
      `What changed: 1.23 ÷ 0.1 is ${fmt(data.scaled)}. Rounding stores ${data.stored}; reconstructing gives ${fmt(data.reconstructed)}, a difference of ${fmt(data.error)}.`,
  },
];

function ready(data) {
  return data ? "" : '<p class="caption">Loading the checked calculation…</p>';
}
lessons.push(
  {
    id: "clipping",
    chapter: "Smaller numbers",
    title: "What if the value does not fit?",
    steps: 1,
    instruction:
      "Press “Try 200” to store 200 at scale 1. Watch what happens at the end of our INT8 range.",
    button: "Try 200",
    act: (_, api) => api("/api/quantize", { value: 200, scale: 1 }),
    render: ({ step, data }) =>
      `<div class="number-story">${number("Original value", 200, "scale 1")}<span class="arrow">→</span>${number("Stored INT8", step ? data.stored : "?", "allowed range −127 to 127", !!step)}</div><p class="caption">Our quantizer uses the symmetric INT8 range −127 to 127.</p>`,
    explain: ({ data }) =>
      `What changed: 200 cannot fit, so it is clipped to ${data.stored}. The difference is ${data.error}; clipping can lose much more detail than rounding.`,
  },
  {
    id: "adding",
    chapter: "Multiply and add",
    title: "How does a lane calculate an answer?",
    steps: 3,
    instruction:
      "Press “Add the next product” three times. A lane multiplies a pair of values and adds it to the running total.",
    button: "Add the next product",
    load: (api) => api("/api/simulate", { config: { lanes: 1 } }),
    act: () => undefined,
    render: ({ step, data }) =>
      !data
        ? ready(data)
        : `<div class="term-row">${data.trace
            .filter((e) => e.phase === "compute")
            .map(
              (e, i) =>
                `<div class="term ${i < step ? "revealed" : ""}">${e.macs[0].left} × ${e.macs[0].right}<strong>${i < step ? e.macs[0].product : "?"}</strong></div>`,
            )
            .join(
              '<span class="arrow">+</span>',
            )}</div><div class="running-total">Running total <strong>${step ? data.trace.filter((e) => e.phase === "compute")[step - 1].macs[0].accumulator : 0}</strong></div>`,
    explain: ({ step, data }) => {
      const op = data.trace.filter((e) => e.phase === "compute")[step - 1]
        .macs[0];
      return `What changed: ${op.accumulator_before} + (${op.left} × ${op.right}) = ${op.accumulator}. ${step === 3 ? "All three pairs have been added." : "The next pair will be added to this total."}`;
    },
  },
  {
    id: "wide",
    chapter: "Multiply and add",
    title: "Why does the answer need more room?",
    steps: 1,
    instruction:
      "Press “Multiply 127 × 127”. Both operands fit in INT8. Does their product fit too?",
    button: "Multiply 127 × 127",
    act: (_, api) => api("/api/quantize", { value: 127, scale: 1 }),
    render: ({ step, data }) =>
      `<div class="number-story">${number("INT8 operands", "127 × 127", "small values")}<span class="arrow">→</span>${number("INT32 total", step ? fmt(data.large_product, 0) : "?", "a wider answer", !!step)}</div><p class="caption">INT8 operands save space. INT32 gives their products and running total more room.</p>`,
    explain: ({ data }) =>
      `What changed: the product is ${fmt(data.large_product, 0)}, far above 127. Our accelerator keeps the running total in INT32 to avoid INT8 overflow.`,
  },
);

const computeEvents = (data) => data.trace.filter((e) => e.phase === "compute");
function machine(data, event, cycle) {
  if (!data) return ready(data);
  const phase = event?.phase || "ready";
  const names = {
    ready: "Ready to load",
    load_inputs: "Load inputs",
    load_weights: "Load weights",
    compute: "Multiply and add",
    store_outputs: "Store the answer",
  };
  const ops = event?.macs || [];
  const lanes = Array.from({ length: data.config.lanes }, (_, i) => {
    const op = ops.find((o) => o.lane === i),
      waiting = event?.waiting_lanes?.includes(i),
      unused = event?.unused_lanes?.includes(i);
    const status = op
      ? "Working"
      : waiting
        ? "Waiting"
        : unused
          ? "Unassigned"
          : phase === "store_outputs"
            ? "Stored"
            : "Ready";
    return `<div class="learning-lane ${op ? "working" : waiting ? "waiting" : ""}"><b>Lane ${i + 1}</b><strong>${op ? op.accumulator : phase === "store_outputs" ? data.output[0][i] : "—"}</strong><span>${status}</span></div>`;
  }).join("");
  return `<div class="machine-route"><div class="${phase.startsWith("load") || phase === "store_outputs" ? "current" : ""}"><b>External memory</b><span>inputs and weights</span></div><span class="arrow">⇄</span><div class="${phase === "compute" ? "current" : ""}"><b>Local buffer</b><span>nearby stored values</span></div><span class="arrow">→</span><div><b>Processing lanes</b><span>multiply-add workers</span></div></div><p class="cycle-state"><b>${names[phase]}</b><span>Clock cycle ${cycle} of ${data.metrics.total_cycles}</span></p><div class="learning-lanes" style="--count:${Math.min(data.config.lanes, 8)}">${lanes}</div>`;
}
lessons.push(
  {
    id: "cycles",
    chapter: "Inside the accelerator",
    title: "Where do the six clock cycles go?",
    steps: 6,
    instruction:
      "Press “Next clock cycle” to load inputs, load weights, calculate three products, then store the answer.",
    button: "Next clock cycle",
    load: (api) => api("/api/simulate", { config: { lanes: 1 } }),
    act: () => undefined,
    render: ({ step, data }) => machine(data, data?.trace[step - 1], step),
    explain: ({ step, data }) => {
      const e = data.trace[step - 1];
      if (e.phase === "compute") {
        const o = e.macs[0];
        return `What changed: ${o.accumulator_before} + (${o.left} × ${o.right}) = ${o.accumulator}. This clock cycle performed one multiply-add.`;
      }
      return `What changed: ${e.bytes} bytes ${e.phase === "store_outputs" ? "stored back to memory. The answer is " + data.output[0][0] + "." : "loaded into the local buffer."} Data movement also uses clock cycles.`;
    },
  },
  {
    id: "parallel",
    chapter: "Inside the accelerator",
    title: "How do eight lanes work together?",
    steps: 1,
    instruction:
      "Press “Run eight lanes” to calculate eight independent answers in parallel. Each lane owns one answer.",
    button: "Run eight lanes",
    load: (api) =>
      api("/api/simulate", { preset: "parallel", config: { lanes: 8 } }),
    act: () => undefined,
    render: ({ step, data }) =>
      machine(
        data,
        step ? computeEvents(data)[0] : null,
        step ? data.trace.indexOf(computeEvents(data)[0]) + 1 : 0,
      ),
    explain: ({ data }) =>
      `What changed: ${computeEvents(data)[0].macs.length} lanes performed a multiply-add in the same clock cycle. Each has its own running total.`,
  },
  {
    id: "waiting",
    chapter: "Inside the accelerator",
    title: "What if memory cannot feed every lane?",
    steps: 1,
    instruction:
      "Press “Narrow the local connection” to reduce local reads from 32 to 8 bytes per clock cycle. Watch the lane status labels.",
    button: "Narrow the local connection",
    load: async (api) => ({
      before: await api("/api/simulate", {
        preset: "parallel",
        config: { lanes: 8 },
      }),
    }),
    act: async (e, api) => ({
      ...e.data,
      after: await api("/api/simulate", {
        preset: "parallel",
        config: { lanes: 8, local_read_bytes_per_cycle: 8 },
      }),
    }),
    render: ({ step, data }) => {
      if (!data) return ready(data);
      const r = step ? data.after : data.before,
        e = computeEvents(r)[0];
      return machine(r, e, r.trace.indexOf(e) + 1);
    },
    explain: ({ data }) => {
      const e = computeEvents(data.after)[0];
      return `What changed: ${e.macs.length} lanes work; ${e.waiting_lanes.length} wait for data. The connection supplies only four INT8 operand pairs per clock cycle. Waiting lanes still have assigned work.`;
    },
  },
);

const cache = new Map();
function cached(api, path, body) {
  const key = path + JSON.stringify(body);
  if (!cache.has(key))
    cache.set(
      key,
      api(path, body).catch((error) => {
        cache.delete(key);
        throw error;
      }),
    );
  return cache.get(key);
}
const digit = (api) => cached(api, "/api/infer", { example_id: 0 });
const pipeline = (current) =>
  `<div class="network-pipeline">${["Pixels", "First layer", "Hidden values", "Second layer", "Digit scores"].map((name, i) => `<span class="${i === current ? "selected" : ""}">${name}</span>`).join('<b aria-hidden="true">→</b>')}</div>`;
function pixels(r, show = false) {
  if (!r) return ready(r);
  const i = r.pixels.findIndex((v) => v > 0 && v < 255),
    p = r.pixels;
  return `<div class="pixel-story"><div class="pixel-image" role="img" aria-label="Actual MNIST test image 0, known digit ${r.label}">${p.map((v, j) => `<i class="${show && j === i ? "picked" : ""}" style="background:rgb(${v},${v},${v})"></i>`).join("")}</div><div>${show ? `<p>Pixel ${Math.floor(i / 28)}, ${i % 28}</p><p class="fp">Normalized FP32: <b>${fmt(r.inputs_fp32[i], 4)}</b></p><p class="int">Stored INT8: <b>${r.inputs_int8[i]}</b></p>` : "<p>28 × 28 pixels = 784 inputs.</p><p>The model was trained beforehand.</p>"}</div></div>`;
}
function dot(r, which) {
  const d = r.inspection[which];
  return `<div class="dot-inspection"><p>INT8 output ${d.output_index} · ${d.term_count} input/weight pairs</p><div class="term-row">${d.terms.map((t) => `<div class="term revealed"><span>${t.input} × ${t.weight}</span><strong>${fmt(t.product, 0)}</strong></div>`).join('<span class="arrow">+</span>')}<span class="arrow">+ …</span></div><div class="dot-total">Full INT32 total <strong>${fmt(d.raw_total, 0)}</strong>${which === "second" ? `<span>+ learned bias ${fmt(d.bias, 0)} = score ${fmt(d.score, 0)}</span>` : ""}</div><p class="caption">Showing ${d.terms.length} of ${d.term_count} terms; the total includes every term.</p></div>`;
}
function hidden(r, step = 3) {
  const d = r.inspection.first;
  return `<div class="number-story">${number("Raw INT32", fmt(d.raw_total, 0), `+ learned bias ${fmt(d.bias, 0)}`)}<span class="arrow">→</span>${number(step >= 2 ? "After ReLU" : "After bias", step >= 1 ? fmt(step >= 2 ? d.relu_total : d.biased_total, 0) : "?", "negative values become 0", step === 1 || step === 2)}<span class="arrow">→</span>${number("Stored hidden INT8", step >= 3 ? d.stored_hidden : "?", "rescaled for the next layer", step === 3)}</div><p class="caption">One of 64 hidden values · bias, ReLU and rescaling are computed but untimed.</p>`;
}
function scoreChart(r, reveal = false) {
  const width = 720,
    height = 205,
    min = Math.min(0, ...r.fp32.scores, ...r.int8.scores_display),
    max = Math.max(0, ...r.fp32.scores, ...r.int8.scores_display),
    y = (v) => height - 24 - ((v - min) / (max - min)) * (height - 48),
    zero = y(0);
  const bars = [];
  for (let i = 0; i < 10; i++)
    for (const [offset, values, color, name, pred] of [
      [0, r.fp32.scores, "#287298", "FP32", r.fp32.prediction],
      [23, r.int8.scores_display, "#ad5934", "INT8", r.int8.prediction],
    ]) {
      const yy = y(values[i]),
        x = 23 + i * 69 + offset;
      bars.push(
        `<rect x="${x}" y="${Math.min(yy, zero)}" width="20" height="${Math.max(1, Math.abs(yy - zero))}" fill="${color}" ${reveal && i === pred ? 'stroke="#12394e" stroke-width="3"' : ""}><title>${name} digit ${i}: ${fmt(values[i], 4)}</title></rect>`,
      );
    }
  return `<svg class="learning-scores" viewBox="0 0 ${width} ${height}" role="img" aria-label="Ten FP32 and INT8 scores, not probabilities"><line x1="16" x2="708" y1="${zero}" y2="${zero}" stroke="#a6c4d1"/>${bars.join("")}${Array.from({ length: 10 }, (_, i) => `<text x="${44 + i * 69}" y="202" text-anchor="middle">${i}</text>`).join("")}</svg><div class="score-key"><span class="fp">● FP32</span><span class="int">● INT8 in comparable display units</span>${reveal ? `<b class="prediction-reveal">Predicted digit: FP32 ${r.fp32.prediction} · INT8 ${r.int8.prediction}</b>` : ""}</div><p class="caption">The largest score wins. INT8 uses raw INT32 scores; chart conversion is only for display.</p>`;
}
lessons.push(
  {
    id: "pixels",
    chapter: "A real prediction",
    title: "What does the network receive?",
    steps: 1,
    instruction:
      "Press “Inspect this pixel” to compare two representations of a real image value. This image has 784 input values.",
    button: "Inspect this pixel",
    load: digit,
    act: () => undefined,
    render: ({ step, data }) =>
      !data ? ready(data) : pipeline(0) + pixels(data, !!step),
    explain: ({ data }) =>
      `What changed: one actual pixel is highlighted. FP32 normalizes its byte value by 255; INT8 represents the input in steps of 1/127.`,
  },
  {
    id: "first",
    chapter: "A real prediction",
    title: "How are 784 inputs combined?",
    steps: 1,
    instruction:
      "Press “Show the first-layer calculation” to inspect one real output. Each of the 64 outputs combines 784 input/weight pairs.",
    button: "Show the first-layer calculation",
    load: digit,
    act: () => undefined,
    render: ({ step, data }) =>
      !data
        ? ready(data)
        : pipeline(1) +
          (step
            ? dot(data, "first")
            : '<p class="visual-prompt">784 inputs × learned weights → 64 running totals</p>'),
    explain: () =>
      `What changed: one complete output total is shown, alongside three of its 784 terms. The weights were learned during training.`,
  },
  {
    id: "hidden",
    chapter: "A real prediction",
    title: "How does a total become a hidden value?",
    steps: 3,
    instruction: ({ step }) =>
      [
        "Press “Add the learned bias” to add a learned offset to one total.",
        "Press “Apply ReLU” to keep positive values and replace negative values with zero.",
        "Press “Rescale to INT8” to express the hidden value in the next layer’s units.",
      ][step],
    button: ({ step }) =>
      ["Add the learned bias", "Apply ReLU", "Rescale to INT8"][step],
    load: digit,
    act: () => undefined,
    render: ({ step, data }) =>
      !data ? ready(data) : pipeline(2) + hidden(data, step),
    explain: ({ step, data }) => {
      const d = data.inspection.first;
      return [
        "",
        "What changed: the learned bias is added in the same units as the running total.",
        `What changed: ReLU keeps ${fmt(d.relu_total, 0)}. Negative totals would become zero; this selected value is ${d.biased_total < 0 ? "negative" : "already nonnegative"}.`,
        `What changed: rescaling stores ${d.stored_hidden} in INT8 for the second layer. The model’s calibrated scale stays fixed.`,
      ][step];
    },
  },
  {
    id: "second",
    chapter: "A real prediction",
    title: "How do 64 values become ten scores?",
    steps: 1,
    instruction:
      "Press “Show the ten scores” to inspect one second-layer calculation. Its 64 hidden inputs contribute to a score for one digit.",
    button: "Show the ten scores",
    load: digit,
    act: () => undefined,
    render: ({ step, data }) =>
      !data
        ? ready(data)
        : pipeline(3) +
          (step
            ? dot(data, "second")
            : '<p class="visual-prompt">64 hidden values × learned weights → ten digit scores</p>'),
    explain: () =>
      `What changed: the full sum and learned bias produce a digit score. The model performs one such calculation for each of ten digits.`,
  },
  {
    id: "scores",
    chapter: "A real prediction",
    title: "Which digit does the model choose?",
    steps: 1,
    instruction:
      "Press “Highlight the largest score” to reveal the predicted digit for each numerical format. These scores are not confidence percentages.",
    button: "Highlight the largest score",
    load: digit,
    act: () => undefined,
    render: ({ step, data }) =>
      !data ? ready(data) : pipeline(4) + scoreChart(data, !!step),
    explain: ({ data }) =>
      `What changed: the largest raw score chooses FP32 ${data.fp32.prediction} and INT8 ${data.int8.prediction}. Independent arithmetic checks pass for both calculations.`,
  },
  {
    id: "disagreement",
    chapter: "A real prediction",
    title: "Can quantization change the prediction?",
    steps: 1,
    instruction:
      "Press “Show a disagreement” to run an example where FP32 and INT8 choose different digits.",
    button: "Show a disagreement",
    act: async (_, api) => {
      const meta = await cached(api, "/api/meta");
      return cached(api, "/api/infer", {
        example_id: meta.examples.find((e) => e.disagreement).id,
      });
    },
    render: ({ step, data }) =>
      step
        ? `<p class="caption">Actual MNIST image ${data.example_id} · known digit ${data.label}</p>` +
          scoreChart(data, true)
        : '<p class="visual-prompt">Rounding may change the winning score.</p>',
    explain: ({ data }) =>
      `What changed: FP32 predicts ${data.fp32.prediction}; INT8 predicts ${data.int8.prediction}. Fifteen of the original 10,000 test predictions differed; this is one of them.`,
  },
);
