# Presentation notes

The PowerPoint is `project-presentation.pptx`. The PDF is a slide handout; speaker notes are embedded in the PowerPoint and repeated here.

The main talk uses slides 1–14 and is planned for 15 minutes. Slides 15–18 are hidden backups, outside that timing. In PowerPoint they remain available in the slide list or through the slideshow’s slide-selection menu.

Suggested split: Troy covers slides 1–8 (8 minutes 10 seconds); Tuong covers 9–14 (6 minutes 50 seconds). The split can change, but the professor requires both members to participate and understand the entire project. These timings are a rehearsal plan, not a measured presentation runtime.

Theme: Midnight Circuit — navy titles, light backgrounds, teal accents, blue FP32 charts, and warm orange INT8 charts. Text, diagrams, and chart data stay editable in PowerPoint. The PDF preserves the rendered layout.

## Timing plan

| Slide | Topic | Presenter | Time | Cumulative |
|---|---|---|---|---|
| 1 | Quantized Neural Network Accelerator | Troy Waters | 30 s | 0:30 |
| 2 | What we built and why | Troy Waters | 45 s | 1:15 |
| 3 | The workload: handwritten digits | Troy Waters | 60 s | 2:15 |
| 4 | Configure first. Test separately. | Troy Waters | 70 s | 3:25 |
| 5 | Keep the arithmetic in integer units | Troy Waters | 80 s | 4:45 |
| 6 | Our proposed matrix accelerator | Troy Waters | 75 s | 6:00 |
| 7 | One answer, six clock cycles | Troy Waters | 75 s | 7:15 |
| 8 | Verify computation, then assess accuracy | Troy Waters | 55 s | 8:10 |
| 9 | Accuracy stayed close in this run | Tuong Tran | 75 s | 9:25 |
| 10 | Smaller operands reduce matrix-stage cost | Tuong Tran | 65 s | 10:30 |
| 11 | More lanes eventually wait for data | Tuong Tran | 75 s | 11:45 |
| 12 | External bandwidth reduces transfer time | Tuong Tran | 65 s | 12:50 |
| 13 | The tradeoffs and limits still matter | Tuong Tran | 70 s | 14:00 |
| 14 | Balance precision with data supply | Tuong Tran | 60 s | 15:00 |

## Speaker notes

### 1. Quantized Neural Network Accelerator

Suggested presenter: Troy Waters · 30 seconds.

Our project studies a proposed accelerator for the matrix calculations inside a small digit-recognition network. We compare 32-bit floating-point values with 8-bit integers. The focus is the relationship between numerical precision, memory traffic, and the processing lanes that perform the calculations. This is a high-level software architecture model. We count its matrix-stage cycles and separately measure prediction accuracy; we did not build or measure a physical chip.

Reference details (not part of the spoken script): High-level software model · matching workload and resource assumptions

### 2. What we built and why

Suggested presenter: Troy Waters · 45 seconds.

The architecture question is whether smaller operands can reduce storage and execution costs while preserving useful predictions. We implemented checked arithmetic, a configurable cycle-stepped matrix engine, and a NumPy neural-network workload, then connected the experiment exports to the graphs. Brevitas informed our quantization choices, including separate scales for weights, activations, and biases. FINN informed our thinking about parallelism and memory organization. Those are design references: we did not install either framework or claim that our simple sequential engine reproduces FINN. Our contribution is the custom implementation and its verification and evaluation.

Reference details (not part of the spoken script): Design references: Brevitas and FINN · detailed links in the backup slides

### 3. The workload: handwritten digits

Suggested presenter: Troy Waters · 60 seconds.

MNIST is a collection of small grayscale pictures of handwritten digits, each supplied with a correct label from zero to nine. Each image has 28 by 28 pixels. We normalize the pixels to the range zero to one and flatten them into 784 inputs. Our network has 64 intermediate values and ten final digit scores. ReLU between the layers replaces negative values with zero. The largest output score selects the digit. The two matrix products require 50,176 and 640 multiply-accumulates, for 50,816 MACs per image. A MAC means multiply two operands and add the product to a running total. This prepared workload lets us connect an actual network to a manageable architecture model.

Reference details (not part of the spoken script): Source: MNIST test archive · network dimensions and counts from mnist-results.json

### 4. Configure first. Test separately.

Suggested presenter: Troy Waters · 70 seconds.

We split the original training archive into 54,000 training images, 5,000 validation images, and 1,000 calibration images. A separate archive contains the 10,000 test images. Training learns the weights and biases; validation monitors learning. After training, calibration chooses the hidden activation scale without using correct-answer labels or updating weights. A scale tells us what each stored integer represents. We observe the largest nonnegative first-layer value on those calibration inputs, divide by 127, and freeze that scale. The input scale comes directly from the known zero-to-one pixel range. The test images then grade the configured model. The correction here was which images choose the scale. Both the earlier and corrected versions kept it fixed while predicting; the earlier version incorrectly used the test set to choose it.

Reference details (not part of the spoken script): Source: notebook 05 data split and calibration procedure · seed 530

### 5. Keep the arithmetic in integer units

Suggested presenter: Troy Waters · 80 seconds.

The network already has learned biases, which are offsets added to each layer's matrix result. We did not invent new biases. We convert them once to INT32 in the same units as the integer products. In this illustrative example, integer 20 with scale 0.01 represents 0.20. A learned bias of 0.04 becomes integer four in those units, so the addition is 20 plus four equals 24. If the next layer uses scale 0.04, that result becomes integer six: both represent 0.24. That is rescaling, rather than a simple cast. Our actual hidden conversion uses integer multiplier 464,594 and a 30-bit shift with ties-to-even rounding. The multiplication uses an INT64 temporary, the hidden values are stored as INT8, and final scores remain INT32. Floating point is still used during training, calibration, and conversion of prepared pixels at the input boundary.

Reference details (not part of the spoken script): Illustrative values above · actual rescaling uses multiplier 464,594 and shift 30

### 6. Our proposed matrix accelerator

Suggested presenter: Troy Waters · 75 seconds.

An accelerator is hardware specialized for a kind of computation. Our proposed machine specializes in matrix multiply-accumulate operations. External memory holds inputs and weights. A local buffer holds one resident matrix stage, and the lanes calculate separate output dot products. The baseline has eight lanes, 256 KiB of local storage, and 32 bytes per cycle for both local operand reads and external transfers. The clock is assumed to be 100 MHz. The buffer fits the largest FP32 stage without tiling, which keeps both precision cases comparable. Each lane can issue one MAC per cycle if data is available. Load, compute, and store phases do not overlap. We reload weights for every layer and image. Dedicated result-write ports and the absence of banking conflicts are simplifying assumptions, and equal lane counts do not imply equal physical area or power.

Reference details (not part of the spoken script): Assumptions: one MAC/lane/cycle · sequential load/compute/store · no tiling or banking conflicts

### 7. One answer, six clock cycles

Suggested presenter: Troy Waters · 75 seconds.

Before using the neural network, we check a calculation we can do by hand: two times four, plus three times five, plus one times six, equals 29. With one INT8 lane, the three input bytes load in one cycle and the three weight bytes load in another. There are three compute cycles because the lane performs one MAC per cycle. The four-byte INT32 result then stores in one cycle. That gives six cycles, or 60 nanoseconds at the assumed 100 MHz clock. The general model rounds the input, weight, and output transfers separately, then adds the scheduler's compute cycles. Larger matrices may stall if the local read budget cannot supply every lane. This example demonstrates that our simulator counts an explicit schedule while performing the arithmetic; it does not just assign a speedup factor to INT8.

Reference details (not part of the spoken script): Source: notebook 03 known-answer trace · one-lane INT8 example at the assumed 100 MHz

### 8. Verify computation, then assess accuracy

Suggested presenter: Troy Waters · 55 seconds.

We checked actual image values and trained weights through both simulated layers on the first 16 test images. The second layer receives the simulated first-layer result after the required bias and activation steps. Integer products match wider independent calculations exactly. FP32 results match with a fixed tolerance because NumPy and our sequential multiply-add model can use different summation orders. The largest final-score difference was about 0.0000038. Every sampled prediction matches its numerical reference. Image eight is especially useful: its known digit is five, but both versions guess six. The simulator is still correct because it reproduces the network's calculation. Classification accuracy is a separate measurement on all 10,000 images. Tuong will now discuss that accuracy and the performance tradeoffs.

Reference details (not part of the spoken script): Source: mnist-results.json verification rows · FP32 rtol 1e−5 / atol 1e−4

### 9. Accuracy stayed close in this run

Suggested presenter: Tuong Tran · 75 seconds.

On all 10,000 test images, FP32 correctly classified 9,696 and the calibrated integer version correctly classified 9,698. That is 96.96 percent versus 96.98 percent, a difference of only 0.02 percentage points. There were 15 different predictions between the two versions. The net gain of two correct answers does not mean only two predictions changed, and it does not show that INT8 is inherently more accurate. Quantization changes rounding and can move close scores in either direction. The mixed-precision reference and the integer core selected the same digits on this run, even though their arithmetic representations differ. This is one small network with one fixed training recipe, so the supported conclusion is that this calibrated representation retained similar accuracy for this workload.

Reference details (not part of the spoken script): Source: mnist-results.json accuracy counts · full 10,000-image test set

### 10. Smaller operands reduce matrix-stage cost

Suggested presenter: Tuong Tran · 65 seconds.

The baseline matrix stages require 19,204 cycles for FP32 and 8,025 for INT8. The ratio is 2.393. The darker bar segments show computation: 12,736 FP32 cycles versus 6,400 INT8 cycles. The lighter segments show transfers: 6,468 versus 1,625 cycles. Both formats have the same one-MAC-per-lane issue rule. Smaller integer operands reduce transfer cost and allow more MACs through the same local read budget. Resident matrix storage falls from 204,096 to 51,216 bytes, while external traffic per image falls from 206,952 to 51,960 bytes, both reductions of about 75 percent. Outputs remain 32 bits, so these totals do not drop by exactly fourfold. Bias and scale metadata are excluded from the matrix-only counts. These timing estimates also exclude bias, activation, rescaling, and digit selection.

Reference details (not part of the spoken script): Baseline: 8 lanes / 32 B per cycle buses / 100 MHz · matrix stages only; biases and scales excluded from traffic

### 11. More lanes eventually wait for data

Suggested presenter: Tuong Tran · 75 seconds.

This experiment changes only lane count while keeping both bandwidths at 32 bytes per cycle. INT8 improves from four to eight to 16 lanes, but 32 lanes give the same cycle count as 16. Each INT8 MAC needs two one-byte operands. A 32-byte local read budget therefore supplies at most 16 MACs per cycle. FP32 needs two four-byte operands, so the same connection supplies at most four MACs per cycle. This explains why the FP32 curve is nearly flat and why the INT8 curve eventually plateaus. Output grouping also matters: the second layer has ten outputs. With eight lanes, it needs a group of eight and then a group of two, with unused lanes in the final group. More arithmetic hardware does not automatically improve execution when data supply or the schedule limits it.

Reference details (not part of the spoken script): Source: accelerator-results.json lane_sweep · both bandwidths fixed at 32 B/cycle

### 12. External bandwidth reduces transfer time

Suggested presenter: Tuong Tran · 65 seconds.

Here we fix 32 lanes and vary external bandwidth from eight to 128 bytes per cycle. The local read budget remains 32 bytes per cycle. The INT8 compute portion stays at 3,200 cycles, while transfer time falls from 6,495 to 408 cycles. Total time therefore falls from 9,695 to 3,608 cycles. The highest tested matrix-stage rate is about 27,716 image-equivalents per second at 128 external bytes per cycle. This sweep improves loading and storing; it does not remove the separate 16-MAC-per-cycle local read cap during computation. The two bandwidths affect different phases. This is a modeled rate for the matrix stages, not complete predictions per second, and it does not establish that the highest-bandwidth design is the best physical implementation.

Reference details (not part of the spoken script): Source: accelerator-results.json external_bandwidth_sweep · 32 lanes / 32 B/cycle local reads

### 13. The tradeoffs and limits still matter

Suggested presenter: Tuong Tran · 70 seconds.

The similar accuracy does not eliminate tradeoffs. Quantization rounds values, and 34 of the 640,000 test hidden values were clipped. We need calibration, scale metadata, converted biases, rescaling logic, and overflow checks. More lanes can also sit idle behind a bandwidth limit. Our numerical experiment covers one small fully connected MNIST network and one training recipe. The 16-image simulator check demonstrates integration; it is not a second full-test accuracy measurement. Our timing excludes the additional steps needed for a complete prediction. We do not model physical timing closure, area, energy, memory banking, overlap, or persistent weight reuse. The next extension should account for the excluded operations before claiming a whole-inference speedup. Wider workload studies, tiling, unsigned activations, and INT4 would be further work.

Reference details (not part of the spoken script): Scope: one MNIST MLP / one recipe · no physical area, power, or achieved-clock measurements

### 14. Balance precision with data supply

Suggested presenter: Tuong Tran · 60 seconds.

The main result is that calibrated INT8 retained similar accuracy while reducing the modeled cost of the network's matrix stages. At the baseline assumptions we observed 96.98 percent accuracy, a 2.393-times matrix-stage speedup, and roughly 75 percent lower matrix storage and external traffic. We implemented the numerical path and scheduling model ourselves, verified real network calculations, and connected exported experiment results to the graphs. The scaling studies show that precision, lane count, local reads, external transfers, and scheduling have to be considered together. Our conclusion is specific to this workload and high-level model. The backup slides contain bandwidth calculations, integer details, execution evidence, and sources for questions.

Reference details (not part of the spoken script): Baseline estimates: 8 lanes / 32 B/cycle buses / assumed 100 MHz · accuracy covers 10,000 test images

### 15. Operand supply limits

Backup; outside the main timing.

The MAC supply limit is local bytes per cycle divided by bytes per operand pair. The actual issue rate also cannot exceed the lane count. This does not model SIMD within a dot product. Output-group barriers matter: the ten-output layer takes two 64-step groups at eight INT8 lanes, not the idealized 640/8 = 80 cycles. This is a scheduler assumption; it is not FINN folding behavior. At 16 lanes all ten outputs fit at once. FP32 has a four-MAC/cycle bus cap, so group tails and arbitration produce the reported 192 versus 160 second-layer compute cycles.

Reference details (not part of the spoken script): A MAC reads two operands · local read budget = 32 bytes/cycle

### 16. Integer bias and rescaling

Backup; outside the main timing.

Both biases were learned during FP32 training. The first is converted using input scale times first weight scale; the second uses hidden scale times second weight scale. They are stored as INT32, not INT8. A conservative weight-sum bound covers partial sums and bias addition before the NumPy integer products. The scalar simulator checks each MAC as well. Integer rescaling approximates the positive ratio input_scale × weight1_scale / hidden_scale. ReLU removes negative totals, a checked INT64 product holds the multiplication, quotient and remainder implement ties-to-even rounding, and clipping produces the next INT8 hidden array. Output scores all share one positive scale, so argmax can operate directly on INT32 scores.

Reference details (not part of the spoken script): Source: mnist-results.json quantization metadata · range −127…127 / zero point 0

### 17. Results and checks

Backup; outside the main timing.

This is a real saved output from the notebook, rendered locally for a readable record. It is not physical hardware timing. A fresh run trains the FP32 model again with seed 530, eight epochs, 64 hidden values, batch size 128, and learning rate 0.001. The dataset files are verified before decoding. Notebook 03 exports hardware-case cycles, notebook 05 exports full-test counts and real-value checks, and notebook 06 loads both files to build the graphs. Archived JSON snapshots reproduce the plots without retraining. Numerical libraries can cause small retraining differences. The local isolated runs and the separate Colab graph-input check are described in the report.

Reference details (not part of the spoken script): Saved notebook 05 output · local rendering, not a screenshot of physical hardware or Colab execution

### 18. Sources

Backup; outside the main timing.

Brevitas and FINN are design references, not installed runtime dependencies or benchmark opponents. Their numerical and architectural behavior is not claimed equivalent to ours. The archived accelerator and MNIST JSON files are the direct sources for every plotted number in this deck. The report contains the full pinned-source comparison and project source link. Native chart data is embedded in the PowerPoint, so the slideshow does not depend on a network connection or a separate spreadsheet.

Reference details (not part of the spoken script): Source snapshot for the numerical results: project commit 568ebe3 · complete references in the report

## Questions to practice

| Question | Short answer |
|---|---|
| What is the accelerator? | A proposed matrix engine with parallel MAC lanes and constrained memory access, evaluated in a software model. |
| Is MNIST the AI model? | MNIST is the labeled image dataset. Our trained 784–64–10 network is the model. |
| Why use separate calibration images? | They choose the numerical scale before the final test. Test images should not configure the evaluated representation. |
| Are biases INT8? | No. We quantize learned biases to INT32 in product-scale units. Rescaling also uses an INT64 temporary. |
| Why do INT8 operands need INT32 totals? | Even 127 × 127 = 16,129 exceeds signed INT8. Dot products add many products, so the totals need a wider checked representation. |
| Why can FP32 differ slightly from NumPy? | Floating-point summation order can differ. We use a fixed tolerance and still require the same predicted digits on the sampled images. |
| Why did INT8 accuracy increase slightly? | Quantization can alter close score rankings in either direction. Two net additional correct answers do not establish an inherent accuracy improvement. |
| Is 2.393× the whole-network speedup? | No. It is the ratio of matrix-stage cycles, including their transfers. Several other inference operations remain untimed. |
| Why not use 32 lanes? | The 32-byte local bus supplies only 16 INT8 operand pairs per cycle. More lanes alone cannot exceed that supply. |
| Why simulate only 16 images? | That sample checks integration through the scalar cycle model. The numerical accuracy run still covers all 10,000 test images. |
| Do zero-filled timing sweeps invalidate the results? | No: this fixed schedule has no zero-skipping. Real-value checks independently verify the arithmetic and chaining. |
| What about PNGs or large pictures? | Decoding, resizing, transparency, and other preprocessing are outside the prepared MNIST workload. |
| What about power, area, or real clock frequency? | They were not measured or synthesized. Equal lane counts do not prove equal silicon cost. |
| Did we run Brevitas or FINN? | No. They were references for design choices; our implementation and evaluation are custom. |

## Rehearsal checks

- Time the 14-slide talk aloud, including the handoff. Aim for about 15 minutes.
- Practice explaining the integer-units example without reading the notes verbatim.
- Keep matrix-stage timing separate from full-test accuracy and complete prediction time.
- Both presenters practice questions about every section.
- Open the PowerPoint in the actual presentation setup and check the font/chart layout. The supplied PDF is a fallback handout.
- Use the prepared charts and outputs during the timed talk; running training live is unnecessary.

Numerical sources: `results/accelerator-results.json`, `results/mnist-results.json`, and the project report. All values describe the checked source snapshot at commit 568ebe3.
