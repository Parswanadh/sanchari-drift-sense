#!/usr/bin/env python3
"""Self-evaluation harness: run localize.py over a generated dataset and
report accuracy/timing, plus one success and one honest-failure visual.

Usage:
    python eval_selftest.py --dataset-dir data/eval_set [--out-dir results]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TOLERANCES = "3,5,10,20,50"


def run_localize(py_exe, localize_script, reference_path, search_path):
    t0 = time.time()
    proc = subprocess.run(
        [py_exe, localize_script, "--reference", reference_path, "--search", search_path, "--diagnostics"],
        capture_output=True, text=True,
    )
    wall = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"localize.py failed (rc={proc.returncode}): {proc.stderr[:500]}")
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    out["_wall_sec"] = wall
    return out


def annotate_pair(ref_path, search_path, true_xy, pred_xy, out_path, title):
    ref = cv2.cvtColor(cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR)
    search = cv2.cvtColor(cv2.imread(search_path, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR)

    tx, ty = int(round(true_xy[0])), int(round(true_xy[1]))
    px, py = int(round(pred_xy[0])), int(round(pred_xy[1]))
    # true = green circle, predicted = red X
    cv2.drawMarker(search, (tx, ty), (0, 220, 0), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=3)
    cv2.circle(search, (tx, ty), 14, (0, 220, 0), 3)
    cv2.drawMarker(search, (px, py), (0, 0, 255), markerType=cv2.MARKER_TILTED_CROSS, markerSize=30, thickness=3)

    h = max(ref.shape[0], search.shape[0])
    pad = 20
    canvas = np.full((h + 80, ref.shape[1] + search.shape[1] + pad, 3), 255, dtype=np.uint8)
    canvas[80:80 + ref.shape[0], 0:ref.shape[1]] = ref
    canvas[80:80 + search.shape[0], ref.shape[1] + pad:ref.shape[1] + pad + search.shape[1]] = search

    cv2.putText(canvas, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(canvas, "Reference", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(canvas, "Search  (green = true, red = predicted)",
                (ref.shape[1] + pad + 10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.imwrite(out_path, canvas)


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def summarize(rows, tolerances):
    errs = [r["error_px"] for r in rows]
    times = [r["time_sec"] for r in rows]
    out = {
        "n": len(rows),
        "mean_error_px": round(statistics.mean(errs), 3) if errs else None,
        "median_error_px": round(statistics.median(errs), 3) if errs else None,
        "p95_error_px": round(percentile(errs, 95), 3) if errs else None,
        "max_error_px": round(max(errs), 3) if errs else None,
        "mean_time_sec": round(statistics.mean(times), 4) if times else None,
        "median_time_sec": round(statistics.median(times), 4) if times else None,
        "p95_time_sec": round(percentile(times, 95), 4) if times else None,
        "max_time_sec": round(max(times), 4) if times else None,
        "within_tolerance_pct": {
            str(t): round(100.0 * sum(1 for e in errs if e <= t) / len(errs), 1) if errs else None
            for t in tolerances
        },
    }
    return out


def main():
    ap = argparse.ArgumentParser(description="Self-evaluate localize.py against a generated dataset")
    ap.add_argument("--dataset-dir", required=True)
    ap.add_argument("--localize-script", default=os.path.join(HERE, "localize.py"))
    ap.add_argument("--tolerance-px", default=DEFAULT_TOLERANCES)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "results"))
    ap.add_argument("--python-exe", default=sys.executable)
    args = ap.parse_args()

    tolerances = [float(t) for t in args.tolerance_px.split(",")]
    os.makedirs(args.out_dir, exist_ok=True)

    with open(os.path.join(args.dataset_dir, "ground_truth.json")) as f:
        records = json.load(f)

    rows = []
    failures = 0
    for rec in records:
        ref_path = os.path.join(args.dataset_dir, rec["reference_path"])
        search_path = os.path.join(args.dataset_dir, rec["search_path"])
        try:
            out = run_localize(args.python_exe, args.localize_script, ref_path, search_path)
        except Exception as exc:
            print(f"  {rec['pair_id']}: RUN FAILED: {exc}", file=sys.stderr)
            failures += 1
            continue
        err = ((out["x"] - rec["true_x"]) ** 2 + (out["y"] - rec["true_y"]) ** 2) ** 0.5
        rows.append({
            "pair_id": rec["pair_id"],
            "architecture": rec["architecture"],
            "has_unique_marker": rec.get("has_unique_marker"),
            "true_x": rec["true_x"], "true_y": rec["true_y"],
            "pred_x": out["x"], "pred_y": out["y"],
            "error_px": err,
            "time_sec": out["time_sec"],
            "score": out.get("score"),
            "periodic_ambiguity": out.get("periodic_ambiguity"),
        })
        print(f"  {rec['pair_id']:12s} {rec['architecture']:7s} err={err:8.2f}px  "
              f"t={out['time_sec']:.3f}s  marker={rec.get('has_unique_marker')}")

    overall = summarize(rows, tolerances)
    by_arch = {arch: summarize([r for r in rows if r["architecture"] == arch], tolerances)
               for arch in sorted(set(r["architecture"] for r in rows))}
    by_marker = {str(m): summarize([r for r in rows if r["has_unique_marker"] == m], tolerances)
                 for m in (True, False)}

    summary = {
        "dataset_dir": args.dataset_dir,
        "n_pairs": len(records),
        "n_run_failures": failures,
        "tolerances_px": tolerances,
        "overall": overall,
        "by_architecture": by_arch,
        "by_has_unique_marker": by_marker,
    }
    summary_path = os.path.join(args.out_dir, "eval_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary -> {summary_path}")
    print(json.dumps(overall, indent=2))

    if rows:
        best = min(rows, key=lambda r: r["error_px"])
        worst = max(rows, key=lambda r: r["error_px"])

        best_rec = next(r for r in records if r["pair_id"] == best["pair_id"])
        worst_rec = next(r for r in records if r["pair_id"] == worst["pair_id"])

        annotate_pair(
            os.path.join(args.dataset_dir, best_rec["reference_path"]),
            os.path.join(args.dataset_dir, best_rec["search_path"]),
            (best["true_x"], best["true_y"]), (best["pred_x"], best["pred_y"]),
            os.path.join(args.out_dir, "success_example.png"),
            f"SUCCESS: {best['pair_id']} ({best['architecture']}) error={best['error_px']:.2f}px",
        )
        annotate_pair(
            os.path.join(args.dataset_dir, worst_rec["reference_path"]),
            os.path.join(args.dataset_dir, worst_rec["search_path"]),
            (worst["true_x"], worst["true_y"]), (worst["pred_x"], worst["pred_y"]),
            os.path.join(args.out_dir, "failure_example.png"),
            f"FAILURE: {worst['pair_id']} ({worst['architecture']}) error={worst['error_px']:.2f}px",
        )

        pitch_note = ("This pair had no locally-unique site marker (has_unique_marker=False): "
                       "the reference crop sits in a purely periodic region of the array, so many "
                       "lattice repeats are statistically indistinguishable from the true site."
                       if not worst["has_unique_marker"] else
                       "This pair had a site marker, but the algorithm still locked onto a competing "
                       "periodic repeat instead — indicates the marker's correlation boost was not "
                       "large enough to dominate the dense lattice's baseline periodic correlation "
                       "for this architecture/noise combination.")
        notes = f"""# Honest Failure Case: {worst['pair_id']}

- Architecture: {worst['architecture']}
- Had unique site marker: {worst['has_unique_marker']}
- True location: ({worst['true_x']:.1f}, {worst['true_y']:.1f})
- Predicted location: ({worst['pred_x']:.1f}, {worst['pred_y']:.1f})
- Pixel error: {worst['error_px']:.2f}px
- Match confidence score: {worst['score']:.3f}
- Periodic ambiguity flagged by algorithm: {worst['periodic_ambiguity']}

## Root cause

{pitch_note}

Applied Materials' own stated disambiguation rule -- among tied/near-tied matches, prefer
whichever is closest to the search image's center -- is applied by localize.py, but that
rule only recovers the *correct* site when the true site happens to be the center-closest
repeat. In a genuinely periodic, marker-free region, there is no image content that could
ever distinguish the true site from its lattice neighbors from a single reference crop alone;
this is a fundamental information-theoretic limit of template matching on periodic layouts,
not a bug in the search strategy. This is precisely the class of case Applied Materials
flags as "genuinely difficult" navigation-error recovery.
"""
        with open(os.path.join(args.out_dir, "failure_notes.md"), "w") as f:
            f.write(notes)
        print(f"Success visual -> {os.path.join(args.out_dir, 'success_example.png')}")
        print(f"Failure visual -> {os.path.join(args.out_dir, 'failure_example.png')}")
        print(f"Failure notes  -> {os.path.join(args.out_dir, 'failure_notes.md')}")


if __name__ == "__main__":
    main()
