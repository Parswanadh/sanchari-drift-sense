const pptxgen = require("pptxgenjs");

// ---- Palette: "Ocean Gradient" — fits semiconductor/optical-inspection subject ----
const NAVY = "0B1E3A";      // primary dark
const DEEPBLUE = "0D3B66";  // secondary
const TEAL = "1C7293";      // accent
const MINT = "3FA796";      // success accent
const WHITE = "FFFFFF";
const OFFWHITE = "F4F7FA";
const SLATE = "5B6B79";
const RED = "C1440E";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

const TITLE_OPTS = { fontFace: "Calibri", bold: true, color: NAVY, fontSize: 30 };
const BODY_OPTS = { fontFace: "Calibri", color: "2B2B2B", fontSize: 14 };

function darkTitleSlide(title, subtitle, kicker) {
  const s = p.addSlide();
  s.background = { color: NAVY };
  s.addShape("rect", { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: NAVY } });
  // subtle geometric motif: concentric circles (wafer motif)
  s.addShape("ellipse", { x: 9.6, y: -1.5, w: 6, h: 6, fill: { color: DEEPBLUE }, line: { type: "none" } });
  s.addShape("ellipse", { x: 10.6, y: -0.5, w: 4, h: 4, fill: { color: TEAL, transparency: 60 }, line: { type: "none" } });
  if (kicker) {
    s.addText(kicker.toUpperCase(), { x: 0.7, y: 0.6, w: 8, h: 0.4, fontFace: "Calibri", color: MINT, bold: true, fontSize: 13, charSpacing: 2 });
  }
  s.addText(title, { x: 0.7, y: 1.1, w: 10.5, h: 1.8, fontFace: "Cambria", color: WHITE, bold: true, fontSize: 40 });
  if (subtitle) {
    s.addText(subtitle, { x: 0.7, y: 2.6, w: 9.5, h: 1.0, fontFace: "Calibri", color: "CADCFC", fontSize: 16 });
  }
  return s;
}

function contentSlide(title, kicker) {
  const s = p.addSlide();
  s.background = { color: WHITE };
  s.addText(kicker ? kicker.toUpperCase() : "", { x: 0.6, y: 0.35, w: 8, h: 0.35, fontFace: "Calibri", color: TEAL, bold: true, fontSize: 12, charSpacing: 2 });
  s.addText(title, { x: 0.6, y: 0.65, w: 12.0, h: 0.8, ...TITLE_OPTS });
  return s;
}

// ============================================================
// SLIDE 1 — Team Details
// ============================================================
{
  const s = darkTitleSlide("Drift-Sense", "AI-Powered Navigation-Error Recovery for Wafer Inspection Tools", "Applied Materials Hackathon Submission");
  s.addText('"Think in a systems way"', { x: 0.7, y: 3.7, w: 8, h: 0.5, fontFace: "Cambria", italic: true, color: MINT, fontSize: 18 });
  s.addText("Team Sanchari", { x: 0.7, y: 4.2, w: 8, h: 0.5, fontFace: "Calibri", bold: true, color: WHITE, fontSize: 22 });
  s.addText("Amrita Vishwa Vidyapeetham, Bangalore", { x: 0.7, y: 4.7, w: 8, h: 0.4, fontFace: "Calibri", color: "CADCFC", fontSize: 14 });

  const members = [
    ["Balcha Parswanadh", "Team Lead", "venkataparswanadh@gmail.com", ""],
    ["Ch Sriya Bharathi", "Member", "sriyabharathichaluvadi@gmail.com", "7981197476"],
    ["M Padmaja", "Member", "mutyalapadmaja77@gmail.com", "9440307686"],
  ];
  let y = 5.35;
  members.forEach(([name, role, email, phone]) => {
    s.addShape("rect", { x: 0.7, y: y, w: 11.9, h: 0.6, fill: { color: DEEPBLUE, transparency: 40 }, line: { type: "none" } });
    s.addText(name, { x: 0.9, y: y, w: 2.6, h: 0.6, fontFace: "Calibri", bold: true, color: WHITE, fontSize: 13, valign: "middle" });
    s.addText(role, { x: 3.5, y: y, w: 1.5, h: 0.6, fontFace: "Calibri", color: MINT, fontSize: 12, valign: "middle" });
    s.addText(email, { x: 5.0, y: y, w: 4.6, h: 0.6, fontFace: "Calibri", color: "CADCFC", fontSize: 12, valign: "middle" });
    s.addText(phone, { x: 9.7, y: y, w: 2.5, h: 0.6, fontFace: "Calibri", color: "CADCFC", fontSize: 12, valign: "middle" });
    y += 0.68;
  });
}

// ============================================================
// SLIDE 2 — Problem Statement Addressed
// ============================================================
{
  const s = contentSlide("Problem Statement: Navigation-Error Recovery", "Slide 2 · Problem Statement Addressed");

  s.addShape("rect", { x: 0.6, y: 1.6, w: 7.3, h: 5.3, fill: { color: OFFWHITE }, line: { type: "none" } });
  const body = [
    { text: "A wafer inspection tool must revisit the exact same die site thousands of times a day, across hundreds of dies, with nanometre repeatability — otherwise measurements from different visits aren't comparable.", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "Motion stages never repeat perfectly: thermal expansion, fab-floor vibration, and mechanical slack accumulate as drift between visits.", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "Every die on a wafer carries the identical repeating layout, so the tool cannot tell from the image alone that it landed a few pixels off — the wrong site looks almost exactly like the right one.", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "Classical template matching breaks down exactly here: in DRAM or FinFET arrays, hundreds of near-identical features sit in one frame, with no principled way to pick the right one.", options: { bullet: true, breakLine: true } },
  ];
  s.addText(body, { x: 0.9, y: 1.85, w: 6.8, h: 4.8, fontFace: "Calibri", color: "2B2B2B", fontSize: 14, valign: "top" });

  // right column: the reframe, as a callout card
  s.addShape("rect", { x: 8.15, y: 1.6, w: 4.55, h: 5.3, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("The real question", { x: 8.45, y: 1.9, w: 4.0, h: 0.4, fontFace: "Calibri", bold: true, color: MINT, fontSize: 14 });
  s.addText("Not “does this look like the target?”", { x: 8.45, y: 2.4, w: 4.0, h: 0.9, fontFace: "Cambria", italic: true, color: WHITE, fontSize: 16 });
  s.addText("but “which of many near-identical targets is the correct one?”", { x: 8.45, y: 3.3, w: 4.0, h: 1.1, fontFace: "Cambria", italic: true, color: WHITE, fontSize: 16 });
  s.addShape("line", { x: 8.45, y: 4.55, w: 3.9, h: 0, line: { color: TEAL, width: 1 } });
  s.addText("Solving this reliably and fast keeps an inspection tool's measurements trustworthy across a wafer, across tools, and across time.", { x: 8.45, y: 4.8, w: 3.9, h: 1.8, fontFace: "Calibri", color: "CADCFC", fontSize: 12.5 });
}

// ============================================================
// SLIDE 3 — Idea Description
// ============================================================
{
  const s = contentSlide("Idea Description", "Slide 3 · Idea Description");

  s.addText([
    { text: "Architecture: ", options: { bold: true, color: NAVY } },
    { text: "DRAM-style periodic word-line / bit-line / via array as the primary narrative — generator also supports FinFET-style parallel-fin / gate structures (both are in Applied Materials' hidden test set).", options: { color: "2B2B2B" } },
  ], { x: 0.6, y: 1.55, w: 12.1, h: 0.7, fontFace: "Calibri", fontSize: 14 });

  s.addText([
    { text: "Localization: ", options: { bold: true, color: NAVY } },
    { text: "classical computer vision — multi-scale / rotation normalized cross-correlation (OpenCV matchTemplate, TM_CCOEFF_NORMED) — not deep learning. Zero training data, fully deterministic, and easy to explain when it fails, which matters directly for the 10% explainability score.", options: { color: "2B2B2B" } },
  ], { x: 0.6, y: 2.2, w: 12.1, h: 0.9, fontFace: "Calibri", fontSize: 14 });

  s.addText("Why this beats simple template matching on periodic layouts", { x: 0.6, y: 3.25, w: 10, h: 0.4, fontFace: "Calibri", bold: true, color: TEAL, fontSize: 15 });

  const cards = [
    ["1", "Known ratio, not a guess", "The 10x zoom ratio is exact by the problem's own definition. We sweep a narrow scale band around it instead of a blind multi-scale pyramid search — faster and less prone to locking onto the wrong scale."],
    ["2", "Periodicity isn't ignored", "Naive matching returns one best-scoring location and calls it done. In a DRAM/FinFET array dozens of locations score almost identically — we run non-max suppression to surface all strong candidate peaks first."],
    ["3", "AM's own tie-break rule", "Among near-tied peaks, we return whichever is closest to the search image's center — exactly Applied Materials' stated disambiguation rule — turning ambiguity into documented, explainable behavior."],
  ];
  let cx = 0.6;
  cards.forEach(([num, head, text]) => {
    s.addShape("rect", { x: cx, y: 3.8, w: 3.95, h: 3.1, fill: { color: OFFWHITE }, line: { type: "none" } });
    s.addShape("ellipse", { x: cx + 0.25, y: 4.05, w: 0.5, h: 0.5, fill: { color: TEAL }, line: { type: "none" } });
    s.addText(num, { x: cx + 0.25, y: 4.05, w: 0.5, h: 0.5, fontFace: "Calibri", bold: true, color: WHITE, fontSize: 16, align: "center", valign: "middle" });
    s.addText(head, { x: cx + 0.25, y: 4.7, w: 3.5, h: 0.5, fontFace: "Calibri", bold: true, color: NAVY, fontSize: 14 });
    s.addText(text, { x: cx + 0.25, y: 5.25, w: 3.5, h: 1.55, fontFace: "Calibri", color: "3D3D3D", fontSize: 11.5 });
    cx += 4.2;
  });
}

// ============================================================
// SLIDE 4 — Proposed Solution
// ============================================================
{
  const s = contentSlide("Proposed Solution", "Slide 4 · Proposed Solution");

  // Left: dataset generator
  s.addShape("rect", { x: 0.6, y: 1.5, w: 6.0, h: 4.6, fill: { color: OFFWHITE }, line: { type: "none" } });
  s.addText("Dataset Generator", { x: 0.85, y: 1.65, w: 5.5, h: 0.4, fontFace: "Calibri", bold: true, color: NAVY, fontSize: 15 });
  s.addText([
    { text: "One shared native canvas ", options: { bold: true } },
    { text: "→ native-res crop = Reference (1nm/px); larger randomly-placed 10x crop, INTER_AREA-downsampled → Search (10nm/px). True center recorded exactly from crop arithmetic.", options: {} },
    { text: "\nNoise: ", options: { bold: true, breakLine: false } },
    { text: "independent Poisson (shot) + Gaussian (read) noise per image, drawn separately — search image intentionally noisier.", options: {} },
    { text: "\nDegradation: ", options: { bold: true } },
    { text: "independent per-image rotation, Gaussian blur (beam PSF), Sobel-gradient edge brightening (SEM secondary-electron contrast).", options: {} },
    { text: "\nSite markers: ", options: { bold: true } },
    { text: "a locally-unique defect mark on most pairs (mirrors AM's own example) — a purely periodic site has no information to disambiguate from a single crop.", options: {} },
  ], { x: 0.85, y: 2.1, w: 5.5, h: 3.9, fontFace: "Calibri", color: "2B2B2B", fontSize: 11.5, valign: "top", lineSpacingMultiple: 1.15 });

  // Right: localization algorithm
  s.addShape("rect", { x: 6.75, y: 1.5, w: 6.0, h: 4.6, fill: { color: OFFWHITE }, line: { type: "none" } });
  s.addText("Localization Algorithm", { x: 7.0, y: 1.65, w: 5.5, h: 0.4, fontFace: "Calibri", bold: true, color: NAVY, fontSize: 15 });
  s.addText([
    { text: "1. ", options: { bold: true } }, { text: "CLAHE-normalize both images (counters independent capture contrast).\n", options: {} },
    { text: "2. ", options: { bold: true } }, { text: "Sweep a narrow scale band around the known ~10x ratio + a small rotation band.\n", options: {} },
    { text: "3. ", options: { bold: true } }, { text: "cv2.matchTemplate (normalized cross-correlation) at each combination; keep the best.\n", options: {} },
    { text: "4. ", options: { bold: true } }, { text: "Non-max suppression on the best correlation surface → top local peaks.\n", options: {} },
    { text: "5. ", options: { bold: true } }, { text: "Tie-break: among near-tied peaks, pick the one closest to the search image's center.\n", options: {} },
    { text: "6. ", options: { bold: true } }, { text: "Output (x, y) + confidence + diagnostics (scale, rotation, ambiguity flag).", options: {} },
  ], { x: 7.0, y: 2.1, w: 5.5, h: 3.9, fontFace: "Calibri", color: "2B2B2B", fontSize: 12, valign: "top", lineSpacingMultiple: 1.25 });

  // Pipeline strip
  s.addShape("rect", { x: 0.6, y: 6.25, w: 12.15, h: 0.9, fill: { color: NAVY }, line: { type: "none" } });
  const steps = ["Ref + Search", "CLAHE", "Scale/Rot Sweep", "NCC Match", "NMS Peaks", "Center Tie-break", "(x, y)"];
  const stepW = 12.15 / steps.length;
  steps.forEach((st, i) => {
    s.addText(st, { x: 0.6 + i * stepW, y: 6.25, w: stepW, h: 0.9, fontFace: "Calibri", color: i === steps.length - 1 ? MINT : WHITE, bold: i === steps.length - 1, fontSize: 11.5, align: "center", valign: "middle" });
    if (i < steps.length - 1) {
      s.addText("→", { x: 0.6 + i * stepW + stepW - 0.22, y: 6.25, w: 0.4, h: 0.9, fontFace: "Calibri", color: TEAL, fontSize: 14, align: "center", valign: "middle" });
    }
  });
}

// ============================================================
// SLIDE 5 — Innovation & Uniqueness
// ============================================================
{
  const s = contentSlide("Innovation & Uniqueness", "Slide 5 · Innovation & Uniqueness");
  const items = [
    ["Known-ratio search, not blind multi-scale", "We treat the 10x relationship as a known physical constraint, not an unknown to search for — a narrow, fast, well-targeted scale band instead of a wide, slow, error-prone one."],
    ["Periodicity as a first-class citizen", "Rather than reporting the argmax and hoping, we explicitly detect near-ties and resolve them with AM's own rule — the hardest case becomes documented, explainable behavior, not a silent wrong answer."],
    ["Realistic, non-degenerate synthetic data", "Structural parameters are randomized per pair within literature-informed bounds, and pitch is deliberately kept large enough to survive the mandatory 10x downsample without aliasing into unresolvable texture."],
    ["No training data or GPU dependency", "The whole pipeline runs on CPU in ~1.2s per pair, with zero risk of overfitting to synthetic-data artifacts that wouldn't generalize to Applied Materials' held-out test set."],
  ];
  let y = 1.6;
  items.forEach(([head, text], i) => {
    const rowH = 1.3;
    s.addShape("rect", { x: 0.6, y: y, w: 0.08, h: rowH, fill: { color: i % 2 === 0 ? TEAL : MINT }, line: { type: "none" } });
    s.addText(head, { x: 0.9, y: y, w: 3.6, h: rowH, fontFace: "Calibri", bold: true, color: NAVY, fontSize: 14.5, valign: "middle" });
    s.addText(text, { x: 4.7, y: y, w: 8.0, h: rowH, fontFace: "Calibri", color: "2B2B2B", fontSize: 13, valign: "middle" });
    y += rowH + 0.15;
  });
}

// ============================================================
// SLIDE 6 — Results (REAL NUMBERS from results/eval_summary.json)
// ============================================================
{
  const s = contentSlide("Results", "Slide 6 · Results — data/eval_set, n=30, DRAM + FinFET");

  // Stat callouts
  const stats = [
    ["86.7%", "within 3px overall\n(30-pair self-eval)"],
    ["100%", "within 3px on sites\nwith a unique marker"],
    ["0.47px", "median error, overall\n(bimodal: near-perfect or honest fail)"],
    ["~1.25s", "mean inference time\nper 1000×1000 pair (CPU)"],
  ];
  let sx = 0.6;
  stats.forEach(([num, label]) => {
    s.addShape("rect", { x: sx, y: 1.5, w: 2.95, h: 1.55, fill: { color: NAVY }, line: { type: "none" } });
    s.addText(num, { x: sx, y: 1.58, w: 2.95, h: 0.75, fontFace: "Calibri", bold: true, color: MINT, fontSize: 30, align: "center" });
    s.addText(label, { x: sx + 0.15, y: 2.3, w: 2.65, h: 0.65, fontFace: "Calibri", color: "CADCFC", fontSize: 10, align: "center" });
    sx += 3.13;
  });

  // Success / failure visuals
  s.addText("SUCCESS — pair_0013 (finfet), error = 0.21px", { x: 0.6, y: 3.35, w: 6.0, h: 0.35, fontFace: "Calibri", bold: true, color: MINT, fontSize: 12.5 });
  s.addImage({ path: "/home/parshu/projects/semicon/results/success_example.png", x: 0.6, y: 3.7, w: 6.0, h: 3.2 });

  s.addText("HONEST FAILURE — pair_0019 (finfet), error = 444.5px", { x: 6.75, y: 3.35, w: 6.0, h: 0.35, fontFace: "Calibri", bold: true, color: RED, fontSize: 12.5 });
  s.addImage({ path: "/home/parshu/projects/semicon/results/failure_example.png", x: 6.75, y: 3.7, w: 6.0, h: 3.2 });
}

// ============================================================
// SLIDE 6b — Results detail (architecture breakdown chart)
// ============================================================
{
  const s = contentSlide("Results — Breakdown & Root Cause", "Slide 6 (cont.) · Accuracy by architecture and marker presence");

  s.addChart(p.ChartType.bar, [
    {
      name: "% within 5px",
      labels: ["DRAM", "FinFET", "Marker present", "No marker (honest fail)"],
      values: [93.3, 80.0, 100.0, 0.0],
    },
  ], {
    x: 0.6, y: 1.5, w: 6.3, h: 4.3,
    chartColors: [TEAL],
    showTitle: true, title: "% of pairs within 5px tolerance", titleFontSize: 13, titleColor: NAVY,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: NAVY, dataLabelFontSize: 11,
    catAxisLabelColor: SLATE, valAxisLabelColor: SLATE, catAxisLabelFontSize: 11,
    valGridLine: { color: "E5E5E5", size: 1 }, catGridLine: { style: "none" },
    showLegend: false, barDir: "col",
  });

  s.addShape("rect", { x: 7.2, y: 1.5, w: 5.5, h: 4.3, fill: { color: OFFWHITE }, line: { type: "none" } });
  s.addText("Root cause of the honest failure", { x: 7.45, y: 1.7, w: 5.0, h: 0.4, fontFace: "Calibri", bold: true, color: RED, fontSize: 14 });
  s.addText([
    { text: "pair_0019 (finfet) had no locally-unique site marker — the reference crop sits in a purely periodic region, so many lattice repeats are statistically indistinguishable from the true site.\n\n", options: {} },
    { text: "Applied Materials' own “closest to center” disambiguation rule is applied, but it only recovers the correct site when the true site happens to be the center-closest repeat. ", options: {} },
    { text: "In a genuinely periodic, marker-free region, no single-crop image content can ever distinguish the true site from its lattice neighbors — a fundamental information-theoretic limit of template matching on periodic layouts, not a bug in the search strategy.", options: { bold: true } },
  ], { x: 7.45, y: 2.2, w: 5.0, h: 3.4, fontFace: "Calibri", color: "2B2B2B", fontSize: 12, valign: "top", lineSpacingMultiple: 1.2 });
}

// ============================================================
// SLIDE 7 — Technology & Feasibility
// ============================================================
{
  const s = contentSlide("Technology & Feasibility", "Slide 7 · Technology & Feasibility");

  const col1 = [
    ["Tech stack", "Python 3, NumPy, OpenCV (opencv-python-headless), Pillow, SciPy, scikit-image, Matplotlib"],
    ["Hardware", "Local machine, NVIDIA RTX 4070 Laptop GPU available but NOT used — classical CPU-only pipeline, no training required"],
  ];
  const col2 = [
    ["Dataset generation", "~25-30s for 32 image pairs (both architectures) on CPU"],
    ["Inference time / pair", "Mean 1.25s, median 1.24s, p95 1.33s on a 1000×1000 pair (CPU)"],
  ];
  const col3 = [
    ["Model size", "N/A — classical algorithm, no trained weights to ship"],
    ["Bonus track", "RGB / optical-microscope generalization not yet attempted — core SEM grayscale pipeline completed first per rubric guidance"],
  ];
  [col1, col2, col3].forEach((col, ci) => {
    const x = 0.6 + ci * 4.15;
    s.addShape("rect", { x, y: 1.55, w: 3.95, h: 5.3, fill: { color: OFFWHITE }, line: { type: "none" } });
    let y = 1.85;
    col.forEach(([head, text]) => {
      s.addText(head, { x: x + 0.25, y, w: 3.5, h: 0.4, fontFace: "Calibri", bold: true, color: TEAL, fontSize: 13 });
      s.addText(text, { x: x + 0.25, y: y + 0.42, w: 3.5, h: 1.6, fontFace: "Calibri", color: "2B2B2B", fontSize: 11.5, valign: "top" });
      y += 2.55;
    });
  });
}

// ============================================================
// SLIDE 8 — GitHub & Video Link
// ============================================================
{
  const s = darkTitleSlide("GitHub & Demo", "", "Slide 8 · Repository");
  s.addShape("rect", { x: 0.7, y: 2.6, w: 11.9, h: 1.6, fill: { color: DEEPBLUE, transparency: 30 }, line: { type: "none" } });
  s.addText("GitHub Repository (public)", { x: 1.0, y: 2.8, w: 5, h: 0.4, fontFace: "Calibri", bold: true, color: MINT, fontSize: 14 });
  s.addText("github.com/Parswanadh/sanchari-drift-sense", { x: 1.0, y: 3.2, w: 10.5, h: 0.6, fontFace: "Calibri", color: WHITE, fontSize: 20, bold: true });
  s.addText("Contains: dataset_generator.py, localize.py, eval_selftest.py, citations.md, requirements.txt (pip freeze), README.md with full setup instructions.", { x: 1.0, y: 3.75, w: 10.5, h: 0.5, fontFace: "Calibri", color: "CADCFC", fontSize: 12 });

  s.addShape("rect", { x: 0.7, y: 4.6, w: 11.9, h: 1.4, fill: { color: DEEPBLUE, transparency: 55 }, line: { type: "none" } });
  s.addText("Demo Video", { x: 1.0, y: 4.8, w: 5, h: 0.4, fontFace: "Calibri", bold: true, color: MINT, fontSize: 14 });
  s.addText("Optional — to be added: a short recording of localize.py running on a sample pair, showing the printed (x, y) output.", { x: 1.0, y: 5.2, w: 10.5, h: 0.6, fontFace: "Calibri", color: "CADCFC", fontSize: 13 });
}

// ============================================================
// SLIDE 9 — References
// ============================================================
{
  const s = contentSlide("References", "Slide 9 · References");
  s.addText("Full reference list with verified public sources lives in citations.md in the repository root (six categories, 2-3 sources each).", { x: 0.6, y: 1.5, w: 12, h: 0.5, fontFace: "Calibri", color: "2B2B2B", fontSize: 13, italic: true });

  const refs = [
    "Poisson (shot) + Gaussian (read) sensor noise model for SEM imaging",
    "SEM secondary-electron edge brightening / edge contrast effect",
    "Gaussian blur as a model of electron-beam spot size / PSF",
    "Motion-stage drift, vibration, and thermal positioning error in wafer inspection tools",
    "DRAM memory cell array structure (word-line / bit-line / via grid)",
    "FinFET transistor structure (parallel fin arrays + gate structures)",
  ];
  let y = 2.2;
  refs.forEach((r, i) => {
    s.addShape("ellipse", { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fill: { color: TEAL }, line: { type: "none" } });
    s.addText(String(i + 1), { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fontFace: "Calibri", bold: true, color: WHITE, fontSize: 13, align: "center", valign: "middle" });
    s.addText(r, { x: 1.2, y: y, w: 11.3, h: 0.5, fontFace: "Calibri", color: "2B2B2B", fontSize: 13.5, valign: "middle" });
    y += 0.68;
  });
  s.addText("See citations.md for full titles, authors, venues, and verified URLs.", { x: 0.6, y: y + 0.15, w: 11.5, h: 0.4, fontFace: "Calibri", italic: true, color: SLATE, fontSize: 11 });
}

p.writeFile({ fileName: "/home/parshu/projects/semicon/submission/Drift-Sense_Sanchari.pptx" }).then(() => {
  console.log("Deck written.");
});
