# Drift-Sense — Team Sanchari

**Navigation-Error Recovery for Wafer Inspection Tools** — Applied Materials hackathon submission.

Given a high-resolution **reference** image (100x zoom, 1 nm/px, 1000×1000) and a lower-resolution
**search** image (10x zoom, 10 nm/px, 1000×1000, covering 10x the physical area of the reference),
find where the reference pattern — shrunk by exactly ~10x — appears inside the search image, and
report its center `(x, y)`. If multiple regions match equally well (periodic DRAM/FinFET layouts),
report whichever is closest to the search image's center, per Applied Materials' own disambiguation
rule.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Tested on Python 3.14 with `numpy`, `opencv-python-headless`, `pillow`, `scipy`, `matplotlib`,
`scikit-image`. No GPU or deep-learning framework required — the localization approach is
classical computer vision (see below).

## Generate a sample image pair

```bash
.venv/bin/python dataset_generator.py --architecture dram --num-pairs 30 --out-dir data/sample --seed 42
```

- `--architecture {dram,finfet,both}` — DRAM-style (staggered word-line/bit-line/via array) or
  FinFET-style (parallel fin lines + gate bars). Both are generated with the same pipeline.
- `--num-pairs N` — number of image pairs to generate.
- `--out-dir DIR` — output directory; images land in `DIR/images/`, ground truth in
  `DIR/ground_truth.json`.
- `--seed S` — RNG seed for reproducibility (default 42).

Each pair models: independent Poisson (shot) + Gaussian (read) sensor noise per image (search
noisier than reference), independent small rotation per image, Gaussian blur (electron-beam PSF),
Sobel-gradient-based edge brightening (SEM secondary-electron edge contrast), and — on a
configurable fraction of pairs — a locally-unique site marker (mirroring the diagonal defect mark
in Applied Materials' own example screenshot), since a purely periodic layout with zero
distinguishing local content is genuinely unsolvable from a single crop, not just hard. Every
augmentation/noise/structural choice is cited against public literature in `citations.md`.

## Run localization on one pair

```bash
.venv/bin/python localize.py --reference data/sample/images/pair_0000_reference.png \
                              --search    data/sample/images/pair_0000_search.png
```

Prints a single line of JSON: `{"x": ..., "y": ..., "score": ..., "time_sec": ...}`. Add
`--diagnostics` for extra fields (`scale_factor`, `rotation_deg`, `periodic_ambiguity`, etc.)
useful for failure-mode analysis.

**Approach:** classical computer vision, not deep learning. Because the reference/search zoom
ratio is *known* (~10x) rather than unknown, the algorithm resizes the reference down by a narrow
band of scale factors around 1/10 and sweeps a small rotation band (rather than a blind
general-purpose multi-scale pyramid search), running normalized cross-correlation
(`cv2.matchTemplate`, `TM_CCOEFF_NORMED`) at each combination. It then runs non-max suppression on
the best-scoring correlation surface to extract the top local peaks — this is what makes highly
periodic DRAM/FinFET layouts tractable — and, among peaks within a small tolerance of the best
score, returns whichever is closest to the search image's center, directly implementing Applied
Materials' own stated tie-break rule for multi-match cases.

## Reproduce the accuracy numbers

```bash
.venv/bin/python eval_selftest.py --dataset-dir data/eval_set --out-dir results
```

Generates `results/eval_summary.json` (accuracy at multiple pixel tolerances, mean/median/p95
error and timing, broken down by architecture and by whether the site had a unique marker), plus
one annotated success example and one annotated **honest failure** example with a root-cause
writeup (`results/failure_notes.md`).

<!-- ACCURACY NUMBERS: current frozen run — regenerate via the command above before final submission if the dataset or algorithm change again. -->
Current frozen results (`data/eval_set`, n=30, mixed DRAM/FinFET): **86.7% of pairs within 3px**
of ground truth overall; **100% within 3px on sites with a locally-unique marker** (mean error
0.47px); pairs without a marker (purely periodic, no distinguishing local content) fail as
expected (~370px mean error) — a fundamental information-theoretic limit of template matching on
periodic layouts, not an algorithm bug. Mean inference time ≈1.25s per 1000×1000 pair on CPU. See
`results/eval_summary.json` and `results/failure_notes.md` for full detail.

## Repository contents

| File | Purpose |
|---|---|
| `dataset_generator.py` | Standalone synthetic dataset generator (DRAM/FinFET, noise, augmentation) |
| `localize.py` | Standalone inference script — the script Applied Materials will run on test data |
| `eval_selftest.py` | Self-evaluation harness: accuracy/timing across a generated test set |
| `citations.md` | Public literature justifying every augmentation/noise/structural choice |
| `requirements.txt` | `pip freeze` of the working environment |
| `data/eval_set/` | Frozen 30-pair self-evaluation dataset (both architectures) |
| `results/` | Frozen accuracy/timing summary, success example, honest-failure example |
