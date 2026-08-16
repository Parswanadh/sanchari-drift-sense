"""
Synthetic wafer-inspection image-pair generator for the Applied Materials
"Drift-Sense" hackathon navigation-error-recovery task.

Generates paired (reference, search) grayscale SEM-like images at two zoom
levels (100x reference = 1 nm/px, 10x search = 10 nm/px) for a localization
benchmark.  Each pair carries a known ground-truth centre so algorithms can
be evaluated without real instrument access.

Physical structures mimicked
-----------------------------
* DRAM word-line / bit-line / via array:
    Periodic horizontal word-lines and vertical bit-lines forming a grid, with
    a small circular contact/via dot at every intersection -- the canonical
    repeating cell structure seen in DRAM arrays.
* FinFET parallel fin + gate structure:
    Dense parallel vertical fin lines (tight, uniform pitch, slight width jitter)
    crossed by one or two horizontal gate bars -- representative of FinFET active
    regions in logic nodes.
* SEM Poisson-Gaussian sensor noise:
    Real scanning-electron-microscope (SEM) detectors experience Poisson shot
    noise on the electron count signal combined with additive Gaussian read noise
    from amplifier circuitry.  The search image (lower magnification, fewer
    electrons per pixel dwell) is intentionally noisier than the reference.
* SEM secondary-electron edge brightening:
    At material edges the secondary-electron yield increases because the beam
    strikes the feature sidewall, producing a characteristic bright-edge halo
    that is the primary contrast mechanism in SEM images.  This is modelled by
    adding a fraction of the local gradient magnitude to the intensity map.

Full literature citations are maintained in citations.md (separate document).
"""

import argparse
import json
import math
import os
import random

import cv2
import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE_SIZE           = 1000
NOMINAL_SCALE_FACTOR = 10.0   # search covers 10x the physical area per axis

# DRAM geometry bounds (px at 1 nm/px)
DRAM_WORDLINE_WIDTH_RANGE = (6, 12)
DRAM_BITLINE_WIDTH_RANGE  = (5, 10)
DRAM_H_PITCH_RANGE        = (30, 60)
DRAM_V_PITCH_RANGE        = (28, 55)
DRAM_VIA_RADIUS_FRAC      = (0.25, 0.40)

# FinFET geometry bounds (px at 1 nm/px)
FINFET_FIN_WIDTH_RANGE    = (4, 8)
FINFET_FIN_PITCH_RANGE    = (18, 32)
FINFET_GATE_WIDTH_RANGE   = (8, 16)
FINFET_GATE_COUNT_RANGE   = (1, 2)

# Degradation parameter bounds
ROT_DEG_MAX              = 5.0
REF_BLUR_SIGMA_RANGE     = (0.5, 1.5)
SEARCH_BLUR_SIGMA_RANGE  = (0.8, 2.0)
EDGE_BRIGHT_WEIGHT_RANGE = (0.08, 0.25)

# Noise: reference (high-mag, lower noise)
REF_POISSON_SCALE_RANGE  = (0.02, 0.06)
REF_GAUSS_SIGMA_RANGE    = (1.5, 4.0)
SEARCH_NOISE_FACTOR_RANGE= (1.5, 3.0)   # search noise multiplier vs reference


# ---------------------------------------------------------------------------
# Fast periodic pattern drawing
# ---------------------------------------------------------------------------

def _make_via_stamp(radius):
    """
    Pre-compute a small boolean disk mask of the given radius.
    Used by _draw_dram_canvas to stamp vias efficiently without per-via
    full-canvas distance calculations.
    """
    d = radius * 2 + 1
    yy, xx = np.mgrid[-radius:radius+1, -radius:radius+1]
    return (yy**2 + xx**2) <= radius**2   # shape (d, d)


def _draw_dram_canvas(canvas, wl_width, bl_width,
                      h_pitch, v_pitch, via_radius):
    """
    Draw a DRAM word-line / bit-line / via pattern onto a float32 canvas
    IN-PLACE.  Pattern starts at pixel 0 and tiles by construction (the
    while-loops sweep the entire canvas).

    Via dots are stamped using a pre-computed disk mask rather than a
    per-via full-canvas distance check -- this is O(n_vias * stamp_area)
    instead of O(n_vias * H * W).
    """
    H, W = canvas.shape
    bright_line = 0.85
    bright_via  = 1.00

    # Horizontal word-lines
    y = 0
    while y < H:
        y0, y1 = max(0, y - wl_width//2), min(H, y + (wl_width+1)//2)
        canvas[y0:y1, :] = np.maximum(canvas[y0:y1, :], bright_line)
        y += h_pitch

    # Vertical bit-lines
    x = 0
    while x < W:
        x0, x1 = max(0, x - bl_width//2), min(W, x + (bl_width+1)//2)
        canvas[:, x0:x1] = np.maximum(canvas[:, x0:x1], bright_line)
        x += v_pitch

    # Via dots -- stamp a small pre-computed disk at each intersection
    stamp = _make_via_stamp(via_radius)
    r = via_radius
    ys_wl = list(range(0, H, h_pitch))
    xs_bl = list(range(0, W, v_pitch))
    for cy in ys_wl:
        for cx in xs_bl:
            # Clip stamp to canvas boundary
            sy0 = max(0, -cy + r);   sy1 = stamp.shape[0] - max(0, cy + r + 1 - H)
            sx0 = max(0, -cx + r);   sx1 = stamp.shape[1] - max(0, cx + r + 1 - W)
            iy0 = max(0, cy - r);    iy1 = min(H, cy + r + 1)
            ix0 = max(0, cx - r);    ix1 = min(W, cx + r + 1)
            if iy1 > iy0 and ix1 > ix0:
                sub_stamp = stamp[sy0:sy1, sx0:sx1]
                canvas[iy0:iy1, ix0:ix1][sub_stamp] = bright_via


def _draw_finfet_canvas(canvas, rng, fin_width, fin_pitch,
                        gate_width, n_gates):
    """
    Draw FinFET fins (vertical, periodic) and gate bars (horizontal)
    onto a float32 canvas IN-PLACE.

    Per-fin width jitter of +-1 px simulates line-edge roughness (LER).
    Gate positions are evenly spaced across the canvas height.
    """
    H, W = canvas.shape
    fin_bright  = 0.80
    gate_bright = 0.90

    x = fin_pitch // 2
    while x < W:
        jitter = rng.randint(-1, 1)
        fw = max(2, fin_width + jitter)
        x0, x1 = max(0, x - fw//2), min(W, x + (fw+1)//2)
        canvas[:, x0:x1] = np.maximum(canvas[:, x0:x1], fin_bright)
        x += fin_pitch

    for k in range(n_gates):
        gy = int((k + 1) * H / (n_gates + 1))
        g0, g1 = max(0, gy - gate_width//2), min(H, gy + (gate_width+1)//2)
        canvas[g0:g1, :] = np.maximum(canvas[g0:g1, :], gate_bright)


# ---------------------------------------------------------------------------
# Degradation helpers
# ---------------------------------------------------------------------------

def _rotate_image(img_f32, angle_deg):
    """Rotate float32 image about its centre; fill border with mean value."""
    H, W = img_f32.shape
    M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), angle_deg, 1.0)
    fill = float(img_f32.mean())
    return cv2.warpAffine(img_f32, M, (W, H),
                          flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,
                          borderValue=fill)


def _apply_edge_brightening(img_f32, weight):
    """
    Add a fraction of the Sobel gradient magnitude to mimic the
    secondary-electron edge-brightening contrast mechanism in real SEM images:
    sidewall interaction increases secondary-electron yield, producing bright
    halos at every material boundary.
    """
    img_u8 = (img_f32 * 255.0).clip(0, 255).astype(np.uint8)
    gx = cv2.Sobel(img_u8, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img_u8, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)
    gmax = grad.max()
    if gmax > 0.0:
        grad /= gmax
    return np.clip(img_f32 + weight * grad, 0.0, 1.0)


def _apply_sem_noise(img_f32, np_rng, poisson_scale, gauss_sigma):
    """
    Apply SEM-realistic Poisson shot noise + Gaussian read noise.

    Shot noise variance scales with local signal (Poisson property).
    Read noise is signal-independent (amplifier floor).
    Caller must advance np_rng separately for reference and search so
    their noise is statistically independent.
    """
    s = img_f32.astype(np.float64)
    H, W = s.shape
    shot = np_rng.standard_normal((H, W)) * np.sqrt(np.abs(s) * poisson_scale + 1e-9)
    read = np_rng.standard_normal((H, W)) * (gauss_sigma / 255.0)
    return np.clip(s + shot + read, 0.0, 1.0).astype(np.float32)


def _f32_to_uint8(img_f32):
    return (img_f32 * 255.0).clip(0, 255).astype(np.uint8)


def _odd_ksize(sigma):
    """Gaussian kernel size: at least 3, always odd."""
    return max(3, int(6 * sigma + 1) | 1)


# ---------------------------------------------------------------------------
# Per-pair parameter sampler
# ---------------------------------------------------------------------------

def _sample_params(arch, rng):
    """Draw all per-pair geometry and degradation parameters."""
    p = {}
    if arch == "dram":
        p["wl_width"]   = rng.randint(*DRAM_WORDLINE_WIDTH_RANGE)
        p["bl_width"]   = rng.randint(*DRAM_BITLINE_WIDTH_RANGE)
        p["h_pitch"]    = rng.randint(*DRAM_H_PITCH_RANGE)
        p["v_pitch"]    = rng.randint(*DRAM_V_PITCH_RANGE)
        min_pitch = min(p["h_pitch"], p["v_pitch"])
        p["via_radius"] = max(2, int(min_pitch * rng.uniform(*DRAM_VIA_RADIUS_FRAC)))
    else:
        p["fin_width"]  = rng.randint(*FINFET_FIN_WIDTH_RANGE)
        p["fin_pitch"]  = rng.randint(*FINFET_FIN_PITCH_RANGE)
        p["gate_width"] = rng.randint(*FINFET_GATE_WIDTH_RANGE)
        p["n_gates"]    = rng.randint(*FINFET_GATE_COUNT_RANGE)

    p["rot_ref"]             = rng.uniform(-ROT_DEG_MAX, ROT_DEG_MAX)
    p["rot_search"]          = rng.uniform(-ROT_DEG_MAX, ROT_DEG_MAX)
    p["blur_ref"]            = rng.uniform(*REF_BLUR_SIGMA_RANGE)
    p["blur_search"]         = rng.uniform(*SEARCH_BLUR_SIGMA_RANGE)
    p["edge_weight"]         = rng.uniform(*EDGE_BRIGHT_WEIGHT_RANGE)
    p["ref_poisson_scale"]   = rng.uniform(*REF_POISSON_SCALE_RANGE)
    p["ref_gauss_sigma"]     = rng.uniform(*REF_GAUSS_SIGMA_RANGE)
    p["search_noise_factor"] = rng.uniform(*SEARCH_NOISE_FACTOR_RANGE)
    return p


# ---------------------------------------------------------------------------
# Reference rendering
# ---------------------------------------------------------------------------

def _render_reference(arch, rng, np_rng, params):
    """Render 1000x1000 reference at 1 nm/px.  Returns float32 [0,1]."""
    canvas = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.float32)
    if arch == "dram":
        _draw_dram_canvas(canvas, params["wl_width"], params["bl_width"],
                          params["h_pitch"], params["v_pitch"], params["via_radius"])
    else:
        _draw_finfet_canvas(canvas, rng, params["fin_width"], params["fin_pitch"],
                            params["gate_width"], params["n_gates"])

    canvas = _rotate_image(canvas, params["rot_ref"])
    s = params["blur_ref"]
    canvas = cv2.GaussianBlur(canvas, (_odd_ksize(s), _odd_ksize(s)), s)
    canvas = _apply_edge_brightening(canvas, params["edge_weight"])
    canvas = _apply_sem_noise(canvas, np_rng,
                              params["ref_poisson_scale"], params["ref_gauss_sigma"])
    return canvas


# ---------------------------------------------------------------------------
# Search rendering
# ---------------------------------------------------------------------------

def _render_search(arch, rng, np_rng, params):
    """
    Render 1000x1000 search image at 10 nm/px and return (img_f32, true_x, true_y).

    Pipeline:
      1. Build a SEARCH_NATIVE x SEARCH_NATIVE (10000x10000 px at 1 nm/px)
         canvas -- exactly the physical area that the search FOV covers.
         Add MARGIN on each side so random crop placement always fits.
      2. Draw the SAME periodic pattern (same params) so it tiles naturally.
      3. Randomly select a crop origin; the reference FOV centre (cx, cy) is
         drawn randomly within the crop interior (keeping ref_half away from edges).
      4. INTER_AREA downsample 10000->1000 px = 10 nm/px effective resolution.
      5. true_x/y = (native_centre - crop_origin) / 10  in search pixels.
    """
    SEARCH_NATIVE = 10000   # 10 um at 1 nm/px
    MARGIN        = 1500    # safety border so crop always fits
    CANVAS_SIZE   = SEARCH_NATIVE + 2 * MARGIN  # 13000 x 13000

    big = np.zeros((CANVAS_SIZE, CANVAS_SIZE), dtype=np.float32)
    if arch == "dram":
        _draw_dram_canvas(big, params["wl_width"], params["bl_width"],
                          params["h_pitch"], params["v_pitch"], params["via_radius"])
    else:
        _draw_finfet_canvas(big, rng, params["fin_width"], params["fin_pitch"],
                            params["gate_width"], params["n_gates"])

    # Choose random crop origin within the valid interior
    crop_min = MARGIN // 2
    crop_max = CANVAS_SIZE - SEARCH_NATIVE - MARGIN // 2
    crop_ox = rng.randint(crop_min, crop_max)
    crop_oy = rng.randint(crop_min, crop_max)

    # Reference-FOV centre in native canvas coords -- random, inside crop
    ref_half = IMAGE_SIZE // 2   # 500 nm
    cx_nat = rng.randint(crop_ox + ref_half, crop_ox + SEARCH_NATIVE - ref_half)
    cy_nat = rng.randint(crop_oy + ref_half, crop_oy + SEARCH_NATIVE - ref_half)

    # Crop, rotate with search-specific angle, downsample
    crop = big[crop_oy: crop_oy + SEARCH_NATIVE,
               crop_ox: crop_ox + SEARCH_NATIVE].copy()
    crop = _rotate_image(crop, params["rot_search"])
    search_img = cv2.resize(crop, (IMAGE_SIZE, IMAGE_SIZE),
                            interpolation=cv2.INTER_AREA)

    # Ground-truth in search-image pixel coordinates
    true_x = (cx_nat - crop_ox) / NOMINAL_SCALE_FACTOR
    true_y = (cy_nat - crop_oy) / NOMINAL_SCALE_FACTOR

    s = params["blur_search"]
    search_img = cv2.GaussianBlur(search_img, (_odd_ksize(s), _odd_ksize(s)), s)
    search_img = _apply_edge_brightening(search_img, params["edge_weight"])

    nf = params["search_noise_factor"]
    search_img = _apply_sem_noise(search_img, np_rng,
                                  params["ref_poisson_scale"] * nf,
                                  params["ref_gauss_sigma"] * nf)
    return search_img, true_x, true_y


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------

def generate_dataset(architecture, num_pairs, out_dir, seed):
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Two separate RNGs: Python-level for geometry/placement, NumPy for noise.
    # Keeping them separate guarantees noise is never correlated with geometry
    # choices even if one path of code is modified independently.
    py_rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    if architecture == "dram":
        arch_list = ["dram"] * num_pairs
    elif architecture == "finfet":
        arch_list = ["finfet"] * num_pairs
    else:
        arch_list = ["dram" if i % 2 == 0 else "finfet" for i in range(num_pairs)]

    records = []

    for i in range(num_pairs):
        pair_id = f"pair_{i:04d}"
        arch    = arch_list[i]
        print(f"  {pair_id} ({arch}) ...", end=" ", flush=True)

        params = _sample_params(arch, py_rng)

        ref_f32                    = _render_reference(arch, py_rng, np_rng, params)
        search_f32, true_x, true_y = _render_search(arch, py_rng, np_rng, params)

        ref_fn    = f"{pair_id}_reference.png"
        search_fn = f"{pair_id}_search.png"
        Image.fromarray(_f32_to_uint8(ref_f32),    "L").save(os.path.join(images_dir, ref_fn))
        Image.fromarray(_f32_to_uint8(search_f32), "L").save(os.path.join(images_dir, search_fn))

        records.append({
            "pair_id":                pair_id,
            "architecture":           arch,
            "reference_path":         os.path.join("images", ref_fn),
            "search_path":            os.path.join("images", search_fn),
            "true_x":                 round(true_x, 4),
            "true_y":                 round(true_y, 4),
            "nominal_scale_factor":   NOMINAL_SCALE_FACTOR,
            "rotation_deg_reference": round(params["rot_ref"], 4),
            "rotation_deg_search":    round(params["rot_search"], 4),
            "seed_used":              seed,
        })
        print(f"true_x={true_x:.1f}  true_y={true_y:.1f}  ok")

    gt_path = os.path.join(out_dir, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nGround truth -> {gt_path}")
    return records


# ---------------------------------------------------------------------------
# Self-validation
# ---------------------------------------------------------------------------

def _validate(out_dir):
    """
    Load every PNG referenced in ground_truth.json and assert:
      - shape == (1000, 1000)
      - dtype == uint8
      - true_x, true_y in [0, 1000)
    Returns True iff all checks pass.
    """
    gt_path = os.path.join(out_dir, "ground_truth.json")
    if not os.path.exists(gt_path):
        print(f"[FAIL] {gt_path} not found"); return False

    with open(gt_path) as f:
        records = json.load(f)

    ok = True
    for rec in records:
        pid = rec["pair_id"]
        for kind in ("reference", "search"):
            path = os.path.join(out_dir, rec[f"{kind}_path"])
            img  = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"[FAIL] {pid}/{kind}: cannot load {path}"); ok = False; continue
            if img.shape != (IMAGE_SIZE, IMAGE_SIZE):
                print(f"[FAIL] {pid}/{kind}: shape {img.shape}"); ok = False
            if img.dtype != np.uint8:
                print(f"[FAIL] {pid}/{kind}: dtype {img.dtype}"); ok = False

        tx, ty = rec["true_x"], rec["true_y"]
        if not (0 <= tx < IMAGE_SIZE and 0 <= ty < IMAGE_SIZE):
            print(f"[FAIL] {pid}: true_x={tx}, true_y={ty} out of [0, {IMAGE_SIZE})"); ok = False

    if ok:
        print(f"[PASS] All {len(records)} pairs validated successfully.")
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Drift-Sense: synthetic SEM wafer-inspection image-pair generator."
    )
    parser.add_argument("--architecture", choices=["dram", "finfet", "both"],
                        default="dram")
    parser.add_argument("--num-pairs", type=int, required=True, metavar="N")
    parser.add_argument("--out-dir",   required=True, metavar="DIR")
    parser.add_argument("--seed",      type=int, default=42)
    args = parser.parse_args()

    if args.num_pairs < 1:
        parser.error("--num-pairs must be >= 1")

    print(f"architecture={args.architecture}  num_pairs={args.num_pairs}  "
          f"out_dir={args.out_dir}  seed={args.seed}\n")

    generate_dataset(args.architecture, args.num_pairs, args.out_dir, args.seed)

    print("\nValidating outputs ...")
    if not _validate(args.out_dir):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
