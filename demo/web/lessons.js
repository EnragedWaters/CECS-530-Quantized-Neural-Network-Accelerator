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
