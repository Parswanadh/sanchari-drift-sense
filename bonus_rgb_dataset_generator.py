"""
Synthetic optical-microscope wafer-inspection image-pair generator for the
Applied Materials "Drift-Sense" hackathon navigation-error-recovery task.

Generates paired (reference, search) 3-channel RGB images at two zoom levels
(100x reference = 1 nm/px, 10x search = 10 nm/px) representing optical
microscopy captures of DRAM and FinFET periodic semiconductor structures.

Physical Differences: Optical Microscopy vs SEM
----------------------------------------------
1. Thin-Film Color Contrast / Spectral Information:
   Unlike SEM grayscale images (where contrast arises purely from secondary-electron
   yield and surface topography), optical microscope images of semiconductor wafers
   exhibit vivid color contrast caused by thin-film optical interference across
   different material layers (silicon substrate, thermal SiO2 dielectric, polysilicon,
   and metal interconnect lines). This is the classic "color chart" effect documented
   by Pliskin & Esch (1967) and Pliskin & Conrad (1964).
2. Optical Sensor Noise (Per-Channel Poisson-Gaussian):
   Color CMOS/CCD sensors experience independent photon shot noise per spectral band
   (R, G, B) combined with electronic read noise in the read-out circuitry. We model
   independent Poisson shot noise and additive Gaussian read noise across each of the
   three color channels.
3. Optical Diffraction-Limited Point Spread Function (PSF):
   Optical imaging in the visible spectrum (400-700 nm) is diffraction-limited
   (Abbe limit d ~ lambda / 2NA), leading to larger spatial blur relative to focused
   electron beams. We model this with a diffraction PSF (Gaussian blur).
4. No Secondary-Electron Edge Halo:
   The bright edge-halo effect present in SEM due to beam-sidewall secondary-electron
   escape is omitted, as it is physically unique to electron microscopy.

Channel Ordering:
-----------------
Images are saved in standard RGB channel order (shape: 1000x1000x3, dtype: uint8).
When reading via PIL: Image.open() returns RGB (3 channels).
When reading via OpenCV: cv2.imread(path, cv2.IMREAD_COLOR) returns BGR (3 channels).

Full literature citations and documentation are maintained in BONUS_RGB.md.
"""

import argparse
import json
import math
import os
import random

import cv2
import numpy as np
from PIL import Image

# Reuse structural geometry constants and drawing helpers from the core generator
from dataset_generator import (
    CANVAS_SIZE,
    DRAM_BITLINE_WIDTH_RANGE,
    DRAM_H_PITCH_RANGE,
    DRAM_V_PITCH_RANGE,
    DRAM_VIA_RADIUS_FRAC,
    DRAM_WORDLINE_WIDTH_RANGE,
    FINFET_FIN_PITCH_RANGE,
    FINFET_FIN_WIDTH_RANGE,
    FINFET_GATE_COUNT_RANGE,
    FINFET_GATE_WIDTH_RANGE,
    IMAGE_SIZE,
    MARGIN,
    NOMINAL_SCALE_FACTOR,
    ROT_DEG_MAX,
    SEARCH_NATIVE,
    SITE_MARKER_PROB,
    _make_via_stamp,
    _odd_ksize,
)

# ---------------------------------------------------------------------------
# Optical Degradation Parameter Bounds
# ---------------------------------------------------------------------------

OPT_REF_BLUR_SIGMA_RANGE    = (0.8, 2.2)   # Optical diffraction blur (reference)
OPT_SEARCH_BLUR_SIGMA_RANGE = (1.2, 2.8)   # Optical diffraction blur (search)

# Per-channel sensor noise bounds
OPT_REF_POISSON_SCALE_RANGE = (0.015, 0.045)
OPT_REF_GAUSS_SIGMA_RANGE   = (1.5, 4.0)
OPT_SEARCH_NOISE_FACTOR_RANGE = (1.5, 3.0)

# Base RGB color palettes (in [0.0, 1.0] float RGB) representing thin-film
# interference colors for different semiconductor layers
PALETTES_DRAM = [
    {
        # Deep slate-blue oxide substrate, amber wordline, cyan bitline, gold via
        "substrate": np.array([0.18, 0.24, 0.38], dtype=np.float32),
        "wordline":  np.array([0.78, 0.58, 0.22], dtype=np.float32),
        "bitline":   np.array([0.25, 0.68, 0.72], dtype=np.float32),
        "via":       np.array([0.96, 0.88, 0.48], dtype=np.float32),
        "marker":    np.array([0.95, 0.92, 0.88], dtype=np.float32),
    },
    {
        # Violet dielectric substrate, copper wordline, green bitline, bright yellow via
        "substrate": np.array([0.30, 0.20, 0.42], dtype=np.float32),
        "wordline":  np.array([0.82, 0.45, 0.25], dtype=np.float32),
        "bitline":   np.array([0.30, 0.75, 0.45], dtype=np.float32),
        "via":       np.array([0.98, 0.90, 0.55], dtype=np.float32),
        "marker":    np.array([0.92, 0.95, 0.90], dtype=np.float32),
    },
]

PALETTES_FINFET = [
    {
        # Dark silicon greenish-gray substrate, terracotta fins, royal violet gates
        "substrate": np.array([0.18, 0.26, 0.22], dtype=np.float32),
        "fin":       np.array([0.72, 0.38, 0.26], dtype=np.float32),
        "gate":      np.array([0.36, 0.32, 0.78], dtype=np.float32),
        "marker":    np.array([0.92, 0.88, 0.50], dtype=np.float32),
    },
    {
        # Steel blue substrate, golden-orange fins, deep magenta gates
        "substrate": np.array([0.20, 0.28, 0.38], dtype=np.float32),
        "fin":       np.array([0.80, 0.55, 0.20], dtype=np.float32),
        "gate":      np.array([0.65, 0.25, 0.60], dtype=np.float32),
        "marker":    np.array([0.95, 0.92, 0.70], dtype=np.float32),
    },
]


# ---------------------------------------------------------------------------
# RGB Periodic Pattern Drawing
# ---------------------------------------------------------------------------

def _draw_dram_rgb_canvas(canvas, wl_width, bl_width, h_pitch, v_pitch, via_radius, palette):
    """
    Draw a 3-channel RGB DRAM pattern onto float32 (H, W, 3) canvas IN-PLACE.
    Tiles horizontal word-lines, vertical bit-lines, and intersecting contact vias
    with realistic thin-film spectral colors.
    """
    H, W, _ = canvas.shape
    canvas[:, :] = palette["substrate"]

    wl_color  = palette["wordline"]
    bl_color  = palette["bitline"]
    via_color = palette["via"]

    # Horizontal word-lines
    y = 0
    while y < H:
        y0, y1 = max(0, y - wl_width // 2), min(H, y + (wl_width + 1) // 2)
        canvas[y0:y1, :] = wl_color
        y += h_pitch

    # Vertical bit-lines
    x = 0
    while x < W:
        x0, x1 = max(0, x - bl_width // 2), min(W, x + (bl_width + 1) // 2)
        canvas[:, x0:x1] = bl_color
        x += v_pitch

    # Via dots stamped at intersections
    stamp = _make_via_stamp(via_radius)
    r = via_radius
    ys_wl = list(range(0, H, h_pitch))
    xs_bl = list(range(0, W, v_pitch))
    for cy in ys_wl:
        for cx in xs_bl:
            sy0 = max(0, -cy + r);   sy1 = stamp.shape[0] - max(0, cy + r + 1 - H)
            sx0 = max(0, -cx + r);   sx1 = stamp.shape[1] - max(0, cx + r + 1 - W)
            iy0 = max(0, cy - r);    iy1 = min(H, cy + r + 1)
            ix0 = max(0, cx - r);    ix1 = min(W, cx + r + 1)
            if iy1 > iy0 and ix1 > ix0:
                sub_stamp = stamp[sy0:sy1, sx0:sx1]
                canvas[iy0:iy1, ix0:ix1][sub_stamp] = via_color


def _draw_finfet_rgb_canvas(canvas, rng, fin_width, fin_pitch, gate_width, n_gates, palette):
    """
    Draw 3-channel RGB FinFET fins and gate bars onto float32 (H, W, 3) canvas IN-PLACE.
    """
    H, W, _ = canvas.shape
    canvas[:, :] = palette["substrate"]

    fin_color  = palette["fin"]
    gate_color = palette["gate"]

    x = fin_pitch // 2
    while x < W:
        jitter = rng.randint(-1, 1)
        fw = max(2, fin_width + jitter)
        x0, x1 = max(0, x - fw // 2), min(W, x + (fw + 1) // 2)
        canvas[:, x0:x1] = fin_color
        x += fin_pitch

    for k in range(n_gates):
        gy = int((k + 1) * H / (n_gates + 1))
        g0, g1 = max(0, gy - gate_width // 2), min(H, gy + (gate_width + 1) // 2)
        canvas[g0:g1, :] = gate_color


def _stamp_rgb_site_marker(canvas, cy, cx, rng, extent, marker_color):
    """
    Stamp one small locally-unique marker (defect / scratch / dust particulate)
    onto the 3-channel float32 canvas at (cy, cx).
    """
    length = rng.randint(int(extent * 0.5), int(extent * 0.9))
    angle = rng.uniform(0, math.pi)
    dx = math.cos(angle) * length / 2.0
    dy = math.sin(angle) * length / 2.0
    pt0 = (int(cx - dx), int(cy - dy))
    pt1 = (int(cx + dx), int(cy + dy))
    thickness = rng.randint(60, 90)
    col = (float(marker_color[0]), float(marker_color[1]), float(marker_color[2]))
    cv2.line(canvas, pt0, pt1, col, thickness, lineType=cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Degradation Helpers for 3-Channel Optical Images
# ---------------------------------------------------------------------------

def _rotate_rgb_image(img_f32, angle_deg):
    """Rotate (H, W, 3) float32 image about its centre; fill border with mean RGB."""
    H, W, _ = img_f32.shape
    M = cv2.getRotationMatrix2D((W / 2.0, H / 2.0), angle_deg, 1.0)
    fill = tuple(float(img_f32[:, :, c].mean()) for c in range(3))
    return cv2.warpAffine(img_f32, M, (W, H),
                          flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,
                          borderValue=fill)


def _apply_optical_rgb_noise(img_f32, np_rng, poisson_scales, gauss_sigmas):
    """
    Apply per-channel optical sensor noise:
    - Photon shot noise per color channel (Poisson-like variance scaling)
    - Gaussian electronic read noise per color channel
    """
    s = img_f32.astype(np.float64)
    H, W, C = s.shape
    out = np.zeros_like(s)
    for c in range(C):
        shot = np_rng.standard_normal((H, W)) * np.sqrt(np.abs(s[:, :, c]) * poisson_scales[c] + 1e-9)
        read = np_rng.standard_normal((H, W)) * (gauss_sigmas[c] / 255.0)
        out[:, :, c] = np.clip(s[:, :, c] + shot + read, 0.0, 1.0)
    return out.astype(np.float32)


def _f32_rgb_to_uint8(img_f32):
    return (img_f32 * 255.0).clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Per-Pair Parameter Sampler
# ---------------------------------------------------------------------------

def _sample_rgb_params(arch, py_rng):
    """Draw all per-pair geometry, color palette, and degradation parameters."""
    p = {}
    if arch == "dram":
        p["wl_width"]   = py_rng.randint(*DRAM_WORDLINE_WIDTH_RANGE)
        p["bl_width"]   = py_rng.randint(*DRAM_BITLINE_WIDTH_RANGE)
        p["h_pitch"]    = py_rng.randint(*DRAM_H_PITCH_RANGE)
        p["v_pitch"]    = py_rng.randint(*DRAM_V_PITCH_RANGE)
        min_pitch = min(p["h_pitch"], p["v_pitch"])
        p["via_radius"] = max(2, int(min_pitch * py_rng.uniform(*DRAM_VIA_RADIUS_FRAC)))
        base_pal = py_rng.choice(PALETTES_DRAM)
    else:
        p["fin_width"]  = py_rng.randint(*FINFET_FIN_WIDTH_RANGE)
        p["fin_pitch"]  = py_rng.randint(*FINFET_FIN_PITCH_RANGE)
        p["gate_width"] = py_rng.randint(*FINFET_GATE_WIDTH_RANGE)
        p["n_gates"]    = py_rng.randint(*FINFET_GATE_COUNT_RANGE)
        base_pal = py_rng.choice(PALETTES_FINFET)

    # Slight per-pair chromatic perturbation to mimic oxide thickness variation
    pal = {}
    for k, v in base_pal.items():
        delta = np.array([py_rng.uniform(-0.04, 0.04) for _ in range(3)], dtype=np.float32)
        pal[k] = np.clip(v + delta, 0.05, 0.98)
    p["palette"] = pal

    p["has_marker"]          = py_rng.random() < SITE_MARKER_PROB
    p["rot_ref"]             = py_rng.uniform(-ROT_DEG_MAX, ROT_DEG_MAX)
    p["rot_search"]          = py_rng.uniform(-ROT_DEG_MAX, ROT_DEG_MAX)
    p["blur_ref"]            = py_rng.uniform(*OPT_REF_BLUR_SIGMA_RANGE)
    p["blur_search"]         = py_rng.uniform(*OPT_SEARCH_BLUR_SIGMA_RANGE)

    # Per-channel independent noise parameters
    p["ref_poisson_scales"]  = [py_rng.uniform(*OPT_REF_POISSON_SCALE_RANGE) for _ in range(3)]
    p["ref_gauss_sigmas"]    = [py_rng.uniform(*OPT_REF_GAUSS_SIGMA_RANGE) for _ in range(3)]
    p["search_noise_factor"] = py_rng.uniform(*OPT_SEARCH_NOISE_FACTOR_RANGE)
    return p


# ---------------------------------------------------------------------------
# Reference + Search Rendering (RGB)
# ---------------------------------------------------------------------------

def _render_rgb_pair(arch, py_rng, np_rng, params):
    """
    Build one shared native-resolution 3-channel RGB canvas, then derive the
    reference crop (100x zoom) and search crop (10x zoom, downsampled) from it.

    Returns (ref_rgb_f32, search_rgb_f32, true_x, true_y).
    """
    big = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.float32)
    if arch == "dram":
        _draw_dram_rgb_canvas(big, params["wl_width"], params["bl_width"],
                              params["h_pitch"], params["v_pitch"], params["via_radius"],
                              params["palette"])
    else:
        _draw_finfet_rgb_canvas(big, py_rng, params["fin_width"], params["fin_pitch"],
                                params["gate_width"], params["n_gates"],
                                params["palette"])

    crop_min = MARGIN // 2
    crop_max = CANVAS_SIZE - SEARCH_NATIVE - MARGIN // 2
    crop_ox = py_rng.randint(crop_min, crop_max)
    crop_oy = py_rng.randint(crop_min, crop_max)

    ref_half = IMAGE_SIZE // 2
    max_drift_native = 2000
    center_x = crop_ox + SEARCH_NATIVE // 2
    center_y = crop_oy + SEARCH_NATIVE // 2
    lo_x = max(crop_ox + ref_half, center_x - max_drift_native)
    hi_x = min(crop_ox + SEARCH_NATIVE - ref_half, center_x + max_drift_native)
    lo_y = max(crop_oy + ref_half, center_y - max_drift_native)
    hi_y = min(crop_oy + SEARCH_NATIVE - ref_half, center_y + max_drift_native)
    cx_nat = py_rng.randint(lo_x, hi_x)
    cy_nat = py_rng.randint(lo_y, hi_y)

    # Stamp marker onto the SHARED canvas
    if params["has_marker"]:
        _stamp_rgb_site_marker(big, cy_nat, cx_nat, py_rng, extent=ref_half,
                               marker_color=params["palette"]["marker"])

    # Reference crop (native resolution)
    ref_img = big[cy_nat - ref_half: cy_nat + ref_half,
                  cx_nat - ref_half: cx_nat + ref_half].copy()
    ref_img = _rotate_rgb_image(ref_img, params["rot_ref"])
    s = params["blur_ref"]
    ref_img = cv2.GaussianBlur(ref_img, (_odd_ksize(s), _odd_ksize(s)), s)
    ref_img = _apply_optical_rgb_noise(ref_img, np_rng,
                                       params["ref_poisson_scales"],
                                       params["ref_gauss_sigmas"])

    # Search crop (10x wider area, downsampled)
    crop = big[crop_oy: crop_oy + SEARCH_NATIVE,
               crop_ox: crop_ox + SEARCH_NATIVE].copy()

    px_local = float(cx_nat - crop_ox)
    py_local = float(cy_nat - crop_oy)
    angle = params["rot_search"]
    if angle != 0:
        M = cv2.getRotationMatrix2D((SEARCH_NATIVE / 2.0, SEARCH_NATIVE / 2.0), angle, 1.0)
        rotated_pt = M @ np.array([px_local, py_local, 1.0])
        px_local, py_local = float(rotated_pt[0]), float(rotated_pt[1])

    crop = _rotate_rgb_image(crop, angle)
    search_img = cv2.resize(crop, (IMAGE_SIZE, IMAGE_SIZE),
                            interpolation=cv2.INTER_AREA)

    true_x = px_local / NOMINAL_SCALE_FACTOR
    true_y = py_local / NOMINAL_SCALE_FACTOR

    s = params["blur_search"]
    search_img = cv2.GaussianBlur(search_img, (_odd_ksize(s), _odd_ksize(s)), s)

    nf = params["search_noise_factor"]
    search_poisson = [scale * nf for scale in params["ref_poisson_scales"]]
    search_gauss   = [sigma * nf for sigma in params["ref_gauss_sigmas"]]
    search_img = _apply_optical_rgb_noise(search_img, np_rng,
                                          search_poisson,
                                          search_gauss)

    return ref_img, search_img, true_x, true_y


# ---------------------------------------------------------------------------
# Main Generation Loop
# ---------------------------------------------------------------------------

def generate_rgb_dataset(architecture, num_pairs, out_dir, seed):
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

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
        print(f"  {pair_id} ({arch}) [RGB] ...", end=" ", flush=True)

        params = _sample_rgb_params(arch, py_rng)
        ref_f32, search_f32, true_x, true_y = _render_rgb_pair(arch, py_rng, np_rng, params)

        ref_fn    = f"{pair_id}_reference.png"
        search_fn = f"{pair_id}_search.png"

        # Save standard 3-channel RGB PNG images
        Image.fromarray(_f32_rgb_to_uint8(ref_f32),    "RGB").save(os.path.join(images_dir, ref_fn))
        Image.fromarray(_f32_rgb_to_uint8(search_f32), "RGB").save(os.path.join(images_dir, search_fn))

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
            "has_unique_marker":      params["has_marker"],
        })
        print(f"true_x={true_x:.1f}  true_y={true_y:.1f}  ok")

    gt_path = os.path.join(out_dir, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nGround truth -> {gt_path}")
    return records


# ---------------------------------------------------------------------------
# Self-Validation
# ---------------------------------------------------------------------------

def _validate_rgb(out_dir):
    """
    Load every RGB PNG referenced in ground_truth.json and assert:
      - shape == (1000, 1000, 3) (genuine 3-channel RGB)
      - dtype == uint8
      - true_x, true_y in [0, 1000)
      - non-trivial color variance across channels (not grayscale saved as RGB)
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
            img = cv2.imread(path, cv2.IMREAD_COLOR)  # loads as (1000, 1000, 3)
            if img is None:
                print(f"[FAIL] {pid}/{kind}: cannot load {path}"); ok = False; continue
            if img.shape != (IMAGE_SIZE, IMAGE_SIZE, 3):
                print(f"[FAIL] {pid}/{kind}: shape {img.shape} != (1000, 1000, 3)"); ok = False
            if img.dtype != np.uint8:
                print(f"[FAIL] {pid}/{kind}: dtype {img.dtype}"); ok = False

            # Verify genuine color information (std between channels > 0)
            rg_diff = float(np.std(img[:, :, 0].astype(float) - img[:, :, 1].astype(float)))
            gb_diff = float(np.std(img[:, :, 1].astype(float) - img[:, :, 2].astype(float)))
            if rg_diff < 1.0 and gb_diff < 1.0:
                print(f"[FAIL] {pid}/{kind}: image appears monochromatic/grayscale saved as RGB"); ok = False

        tx, ty = rec["true_x"], rec["true_y"]
        if not (0 <= tx < IMAGE_SIZE and 0 <= ty < IMAGE_SIZE):
            print(f"[FAIL] {pid}: true_x={tx}, true_y={ty} out of [0, {IMAGE_SIZE})"); ok = False

    if ok:
        print(f"[PASS] All {len(records)} RGB pairs validated successfully (genuine 3-channel color).")
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Drift-Sense: synthetic optical-microscope (RGB) wafer-inspection image-pair generator."
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

    generate_rgb_dataset(args.architecture, args.num_pairs, args.out_dir, args.seed)

    print("\nValidating RGB outputs ...")
    if not _validate_rgb(args.out_dir):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
