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
