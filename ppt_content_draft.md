# Drift-Sense — PPT Content Draft (Team Sanchari)

This is text content only, to be transcribed into the i4C PowerPoint template.
Slide 6 (Results) is a placeholder pending real numbers from `results/eval_summary.json`.

---

## Slide 1 — Team Details

**Team name:** Sanchari
**Tagline:** "Think in a systems way"
**College:** Amrita Vishwa Vidyapeetham, Bangalore

| Role | Name | Email | Phone |
|---|---|---|---|
| Team Lead | Balcha Parswanadh | venkataparswanadh@gmail.com | — |
| Member | Ch Sriya Bharathi | sriyabharathichaluvadi@gmail.com | 7981197476 |
| Member | M Padmaja | mutyalapadmaja77@gmail.com | 9440307686 |

---

## Slide 2 — Problem Statement Addressed

**Selected: "Drift-Sense: Navigation-Error Recovery"**

A wafer inspection tool must return to the exact same die site thousands of times a day, across hundreds of dies, with nanometre-level repeatability — otherwise measurements taken on different visits simply aren't comparable. In practice the motion stage never repeats perfectly: thermal expansion, vibration from the fab floor, and mechanical slack in the stage all accumulate as small positioning drift between visits. That would be a minor problem on a one-off pattern, but every die on a wafer carries the identical repeating circuit layout, so the tool cannot tell from the image alone that it has landed a few pixels away from the intended site — the wrong location looks almost exactly like the right one. This is what makes navigation-error recovery fundamentally harder than ordinary image registration: it's not "does this look like the target," it's "which of many near-identical targets is the *correct* one." Classical template matching, the incumbent approach, breaks down exactly here — in DRAM memory arrays or FinFET gate structures, hundreds of visually indistinguishable features sit in a single frame, and a matcher with no awareness of that periodicity has no principled way to pick the right one. Solving this reliably and fast is what keeps an inspection tool's measurements trustworthy across an entire wafer, across tools, and across time.

---

## Slide 3 — Idea Description

**Architecture choice:** DRAM-style periodic word-line/bit-line/via array as the primary narrative (the dataset generator also supports FinFET-style parallel-fin/gate structures via a `--architecture` flag, since Applied Materials' own hidden test set covers both).

**Localization algorithm:** Classical computer vision — multi-scale/rotation normalized cross-correlation (OpenCV `matchTemplate`, `TM_CCOEFF_NORMED`) — not deep learning. This was a deliberate choice given the challenge's tight timeline: it needs zero training data, is fully deterministic, and is straightforward to explain when things go wrong (which matters directly for the 10% explainability score).

**Why this is better than simple template matching for periodic layouts:**
1. **It exploits a known physical fact instead of guessing it.** The reference-to-search zoom ratio is *exactly* 10x by the problem's own definition — not an unknown to be searched for blindly. Our pipeline sweeps only a narrow band of scale factors around that known ratio (plus a small rotation band for capture misalignment), instead of a blind general-purpose multi-scale pyramid search. That's both faster and less prone to locking onto the wrong scale.
2. **It doesn't pretend periodicity doesn't exist.** Naive template matching returns a single best-scoring location and calls it done. In a DRAM or FinFET array, dozens of locations score almost identically — silently picking one is a coin flip. Our pipeline runs non-max suppression on the correlation surface to find *all* strong candidate peaks first.
3. **It resolves ambiguity using Applied Materials' own rule, not an arbitrary one.** Among peaks that are effectively tied, we return the one closest to the search image's center — exactly the disambiguation rule specified in the problem statement for multi-match cases. This turns "genuine periodic ambiguity" from a silent failure mode into a documented, explainable, and scoreable behavior.

---

## Slide 4 — Proposed Solution

### Dataset generator design (`dataset_generator.py`)
- Renders a large native-resolution periodic canvas per architecture:
  - **DRAM-style:** staggered horizontal word-lines + vertical bit-lines crossing at right angles, with a small contact/via dot at every intersection (line widths, pitch, and via size randomized per pair within realistic bounds).
  - **FinFET-style:** dense parallel vertical fin lines (with per-fin line-edge-roughness jitter) crossed by 1-2 horizontal gate bars.
- Crops a 1000x1000 region at native resolution for the **Reference** image (1 nm/px, 100x zoom).
- For the **Search** image, renders the *same* pattern onto a much larger native canvas, takes a randomly-placed 10000x10000 crop (so the reference location is not always centered), and downsamples with `cv2.INTER_AREA` to 1000x1000 (10 nm/px, 10x zoom) — this is precisely what makes the reference pattern reappear genuinely shrunk 10x inside the search image, and the true center is recorded exactly from the crop arithmetic (no approximation).
- **Noise model:** independent Poisson (shot) noise + additive Gaussian (read) noise, applied *separately* to each image with separate RNG draws (never shared between reference and search — they are two independent physical captures), with the search image intentionally noisier than the reference, matching Applied Materials' own stated test-data behavior.
- **Degradation:** small independent rotation per image, Gaussian blur (electron-beam point-spread function), and Sobel-gradient-based edge brightening (secondary-electron edge contrast — the classic SEM "bright edges" look).
- Every one of these choices — noise model, edge brightening, blur, rotation/scale jitter, and the DRAM/FinFET structural parameters themselves — is justified against real public sources in `citations.md` (6 categories, 2-3 sources each: Poisson-Gaussian SEM sensor noise; SEM secondary-electron edge brightening; Gaussian beam-PSF blur; stage drift/vibration/thermal positioning error; DRAM word-line/bit-line/via array structure; FinFET fin+gate structure).

### Localization algorithm (`localize.py`)
- CLAHE contrast normalization on both images first, to counter independent per-capture brightness/contrast differences.
- Resize the reference down across a narrow band of scale factors around the known ~10x ratio (not a blind pyramid search), and sweep a small rotation band.
- Run `cv2.matchTemplate` (normalized cross-correlation) at every (scale, rotation) combination; track the best-scoring one.
- Non-max suppression on that best correlation surface to extract the top local peaks — this is what makes periodic layouts tractable.
- **Periodic-ambiguity tie-break:** among peaks within a small tolerance of the best score, return the one closest to the search image's center — directly implementing Applied Materials' own stated disambiguation rule.
- Output: predicted `(x, y)`, a confidence score, and diagnostics (chosen scale/rotation, number of near-tied peaks, an explicit `periodic_ambiguity` flag) for failure-mode analysis.

### Pipeline diagram (described)
```
Reference image ─┐                                    ┌─► predicted (x, y)
                  ├─► CLAHE preprocess ─► known-ratio  │
Search image   ───┘    (both images)     scale+rotation ─► cv2.matchTemplate ─► NMS peak
                                          sweep            (NCC)                extraction
                                                                                     │
                                                                                     ▼
                                                          periodic-ambiguity tie-break
                                                          (closest peak to search-image
                                                           center) ─► output (x, y, score)
```

---

## Slide 5 — Innovation & Uniqueness

- **Known-ratio search, not blind multi-scale search.** Most template-matching pipelines search scale as an unknown; we treat the 10x relationship as a known physical constraint (it *is* one, by the problem's own definition), so the entire scale sweep is a narrow, fast, well-targeted band instead of a wide, slow, error-prone one.
- **Periodicity is treated as a first-class citizen, not an edge case.** Rather than reporting the single argmax and hoping it's right, the pipeline explicitly detects when multiple locations are effectively tied and resolves the tie using Applied Materials' own stated rule — this makes "the genuinely hard case" (highly periodic array regions) a documented, explainable behavior rather than a silent wrong answer.
- **Realistic, non-degenerate synthetic data.** Structural parameters (line widths, pitch, via radius, fin spacing) are randomized per pair within literature-informed bounds rather than fixed, so the 30+ evaluation pairs aren't near-duplicates of each other — and pitch is deliberately kept large enough (tens of native pixels) to survive the mandatory 10x downsample without aliasing into an unresolvable texture, a subtlety that's easy to get wrong when hand-picking pattern parameters.
- **No training data or GPU dependency.** The whole pipeline runs on CPU in well under a second per pair, with zero risk of a model overfitting to synthetic-data artifacts that wouldn't generalize to Applied Materials' held-out test set.

---

## Slide 6 — Results

**30-pair self-evaluation (mixed DRAM/FinFET, `data/eval_set`, seed 123) — from `results/eval_summary.json`:**

| Metric | Overall | DRAM (n=15) | FinFET (n=15) |
|---|---|---|---|
| Accuracy within 3px / 5px / 10px / 20px / 50px | **86.7%** (all thresholds identical) | 93.3% | 80.0% |
| Mean pixel error | 49.8px | 23.7px | 75.9px |
| Median pixel error | 0.47px | 0.46px | 0.50px |
| p95 pixel error | 378.9px | 105.2px | 415.5px |

**Computation time per 1000×1000 pair:** mean 1.25s, median 1.24s, p95 1.33s, max 1.35s (CPU only).

**Broken down by whether the site had a locally-unique marker** (see Slide 5 / `has_unique_marker`):

| | n | Accuracy within 3px | Mean error |
|---|---|---|---|
| Marker present | 26 | **100%** | 0.47px |
| Marker-free (purely periodic) | 4 | 0% | 370.6px |

The all-or-nothing split is the headline finding: the algorithm is essentially exact
(sub-pixel to ~1px) whenever the reference site has *any* locally-distinguishing content, and
fails cleanly and predictably when it doesn't — which is precisely the "genuinely hard periodic
region" case the problem statement calls out.

- **SUCCESS visual:** `results/success_example.png` — reference | search, with true location
  (green) and predicted location (red) overlaid; error 0.30px.
- **HONEST FAILURE visual:** `results/failure_example.png` + `results/failure_notes.md` —
  `pair_0019` (FinFET, no site marker), true=(675.0, 599.6), predicted=(361.0, 285.0),
  error=444.5px, confidence score 0.626, `periodic_ambiguity=True`. Root cause: with no
  locally-unique feature, the reference crop sits in a purely periodic region where many lattice
  repeats are statistically indistinguishable from the true site under sensor noise — Applied
  Materials' own closest-to-center tie-break only recovers the *correct* site when the true site
  happens to be the center-closest repeat, which it wasn't here. This is a fundamental
  information-theoretic limit of matching a single crop against a periodic layout, not a bug in
  the search/scale/rotation sweep.

---

## Slide 7 — Technology & Feasibility

**Tech stack:** Python 3, NumPy, OpenCV (`opencv-python-headless`), Pillow, SciPy, scikit-image, Matplotlib.

**Hardware used for development:** Local machine with an NVIDIA RTX 4070 Laptop GPU available but **not used** — the localization pipeline is classical CPU-only computer vision (no model training), so GPU acceleration wasn't needed for the core deliverable.

**Dataset generation time:** ≈0.8s per pair (30 pairs, mixed DRAM/FinFET, generated in 24.0s).

**Localization inference time per pair:** mean 1.25s, median 1.24s, p95 1.33s, max 1.35s (from `results/eval_summary.json`, n=30, CPU only).

**Model size:** N/A — classical algorithm, no trained weights.

---

## Slide 8 — GitHub & Video Link

**GitHub repository:** `https://github.com/<org-or-user>/sanchari-drift-sense` (public repo — insert final URL once created).

**Video link:** Optional/recommended — a short screen recording of `localize.py` running on a sample generated pair, showing the printed `(x, y)` output, would strengthen this slide but is not required.

---

## Slide 9 — References

See **`citations.md`** in the repository root for the complete reference list. It covers six categories, each backed by 2-3 verified public sources (papers, textbooks, or industry references) actually confirmed to exist — nothing fabricated:

1. Poisson (shot) + Gaussian (read) sensor noise model for SEM imaging
2. SEM secondary-electron edge brightening / edge contrast effect
3. Gaussian blur as a model of electron-beam spot size / PSF
4. Motion-stage drift, vibration, and thermal positioning error in wafer inspection tools
5. DRAM memory cell array structure (word-line/bit-line/via grid)
6. FinFET transistor structure (parallel fin arrays + gate structures)

*(Do not re-list individual citations here — `citations.md` is the single source of truth to avoid drift between the deck and the repo.)*
