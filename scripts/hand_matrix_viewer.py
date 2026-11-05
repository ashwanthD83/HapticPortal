#!/usr/bin/env python3
"""See exactly how a hand becomes the 5x5 depth matrix.

Runs the same code the app uses (src/hand_matrix.py) on test input and shows,
for each case: the depth image, the pixels counted as hand, and the matrix.

Usage (from the project root):
    python scripts/hand_matrix_viewer.py synthetic
        Fake hands with a known right answer (flat, tilted, curled, far away).

    python scripts/hand_matrix_viewer.py capture
        Opens the camera. Hold your hand up, press SPACE to save a frame
        (saved under captures/), q to quit. The saved frame is then shown.

    python scripts/hand_matrix_viewer.py replay captures/<folder>
        Re-run the matrix on a saved frame (e.g. after changing settings).

Matrix values: 0 = no hand in that cell, 1-255 = hand, higher = closer.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config_hand_tracking as cfg  # noqa: E402
from src.hand_matrix import (  # noqa: E402
    bbox_from_landmarks,
    compute_hand_matrix,
    estimate_hand_depth,
)

SPAN_MM = getattr(cfg, "RELIEF_SPAN_MM", 150)
BAND_MM = getattr(cfg, "HAND_BAND_MM", 120)
COVERAGE = getattr(cfg, "MIN_CELL_COVERAGE", 0.15)
DEPTH_W, DEPTH_H = 320, 240  # same depth size the app uses
FOCAL_PX = 216.0             # OAK-D Lite at 320 px wide (73 deg HFOV)
BASELINE_MM = 75.0
OUT_DIR = ROOT / "verification_output"


# ----------------------------------------------------------------------------
# Running the real matrix code
# ----------------------------------------------------------------------------

def run_matrix(depth, landmarks):
    """Same steps as the app (minus frame-to-frame smoothing)."""
    hand_depth = estimate_hand_depth(depth, landmarks)
    if hand_depth is None:
        return None
    bbox = bbox_from_landmarks(landmarks, depth.shape)
    matrix, mask = compute_hand_matrix(
        depth, bbox, landmarks, hand_depth, BAND_MM, SPAN_MM, COVERAGE
    )
    return {"hand_depth": hand_depth, "bbox": bbox, "matrix": matrix, "mask": mask}


# ----------------------------------------------------------------------------
# Synthetic hands
# ----------------------------------------------------------------------------

# MediaPipe landmark order: 0 wrist, then 4 joints each for thumb, index,
# middle, ring, pinky (base -> tip). Open right hand, palm to camera, fingers up.
# Units: mm in the hand's own plane, origin at the palm centre.
HAND_TEMPLATE_MM = np.array([
    (0, 85),                                          # wrist
    (-35, 70), (-60, 45), (-75, 20), (-85, 0),        # thumb
    (-30, -10), (-35, -45), (-37, -65), (-38, -85),   # index
    (-5, -15), (-5, -55), (-5, -78), (-5, -98),       # middle
    (20, -10), (24, -45), (26, -66), (28, -84),       # ring
    (40, 0), (48, -28), (52, -45), (55, -60),         # pinky
], dtype=np.float32)
FINGERS = [[0, 1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
PALM = [0, 1, 5, 9, 13, 17]
FINGER_WIDTH_MM = 17


def synthetic_hand(distance_mm, background_mm, plane_fn, curl_mm=0.0, noise=True, seed=0):
    """Render a depth image (uint16 mm) of a hand plus its 21 landmarks.

    plane_fn(x_mm, y_mm) -> extra depth (mm) across the hand (e.g. a tilt).
    curl_mm: how much closer each finger joint gets toward the tip.
    """
    rng = np.random.default_rng(seed)
    px_per_mm = FOCAL_PX / distance_mm
    centre = np.array([DEPTH_W / 2, DEPTH_H / 2 + 10])
    landmarks = [tuple(int(v) for v in centre + p * px_per_mm) for p in HAND_TEMPLATE_MM]

    hand_mask = np.zeros((DEPTH_H, DEPTH_W), np.uint8)
    offset = np.zeros((DEPTH_H, DEPTH_W), np.float32)  # finger curl, mm
    cv2.fillConvexPoly(hand_mask, cv2.convexHull(np.array([landmarks[i] for i in PALM])), 255)
    width_px = max(2, int(FINGER_WIDTH_MM * px_per_mm))
    for finger in FINGERS:
        for k in range(len(finger) - 1):
            a, b = landmarks[finger[k]], landmarks[finger[k + 1]]
            cv2.line(hand_mask, a, b, 255, width_px)
            cv2.line(offset, a, b, float(-curl_mm * (k + 1)), width_px)

    ys, xs = np.mgrid[0:DEPTH_H, 0:DEPTH_W]
    x_mm = (xs - centre[0]) / px_per_mm
    y_mm = (ys - centre[1]) / px_per_mm
    depth = np.full((DEPTH_H, DEPTH_W), float(background_mm), np.float32)
    hand = hand_mask > 0
    depth[hand] = distance_mm + plane_fn(x_mm, y_mm)[hand] + offset[hand]

    if noise:
        # Stereo depth error grows with distance squared (~0.15 px disparity noise).
        sigma = 0.15 * depth ** 2 / (FOCAL_PX * BASELINE_MM)
        depth += rng.normal(0, 1, depth.shape) * sigma
        depth[rng.random(depth.shape) < 0.03] = 0  # random holes, like real stereo
    return np.clip(depth, 0, 65535).astype(np.uint16), landmarks


SYNTHETIC_CASES = [
    ("Flat open hand, 50 cm",
     "Hand cells ~128 everywhere (flat). Gaps between fingers and outside = 0.",
     dict(distance_mm=500, background_mm=1500, plane_fn=lambda x, y: 0 * x)),
    ("Tilted: thumb side 60 mm closer",
     "Left columns high, right columns low (smooth left->right gradient).",
     dict(distance_mm=500, background_mm=1500, plane_fn=lambda x, y: 0.6 * x)),
    ("Fingers curled toward camera",
     "Top rows (fingers) higher than bottom rows (palm).",
     dict(distance_mm=500, background_mm=1500, plane_fn=lambda x, y: 0 * x, curl_mm=20)),
    ("Flat hand at 1.3 m (too far)",
     "Should be flat ~128 but noise makes it uneven: why 35-70 cm is best.",
     dict(distance_mm=1300, background_mm=2500, plane_fn=lambda x, y: 0 * x)),
]


# ----------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------

def depth_to_color(depth, near, far):
    """Near = red, far = blue, no depth = black (RGB for matplotlib)."""
    scaled = np.clip((far - depth.astype(np.float32)) / max(1.0, far - near), 0, 1)
    img = cv2.applyColorMap((scaled * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    img[depth == 0] = 0
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def draw_grid(ax, bbox):
    x, y, w, h = bbox
    for k in range(6):
        ax.plot([x + w * k / 5] * 2, [y, y + h], color="white", lw=0.8)
        ax.plot([x, x + w], [y + h * k / 5] * 2, color="white", lw=0.8)


def draw_matrix(ax, matrix):
    shown = np.ma.masked_equal(matrix.astype(float), 0)
    ax.set_facecolor("#3a3a3a")
    ax.imshow(shown, cmap="viridis", vmin=1, vmax=255)
    for i in range(5):
        for j in range(5):
            v = int(matrix[i, j])
            ax.text(j, i, str(v), ha="center", va="center", fontsize=11,
                    color="#bbbbbb" if v == 0 else ("black" if v > 150 else "white"),
                    fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])


def render(cases, out_path, show):
    """cases: list of dicts with title, note, depth, landmarks, result, rgb(optional)."""
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    has_rgb = any(c.get("rgb") is not None for c in cases)
    ncols = 4 if has_rgb else 3
    fig, axes = plt.subplots(len(cases), ncols, figsize=(4.2 * ncols, 3.6 * len(cases)),
                             squeeze=False)
    for row, case in zip(axes, cases):
        res = case["result"]
        col = 0
        if has_rgb:
            rgb = case.get("rgb")
            if rgb is not None:
                row[0].imshow(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                sx = rgb.shape[1] / case["depth"].shape[1]
                sy = rgb.shape[0] / case["depth"].shape[0]
                lx, ly = zip(*case["landmarks"])
                row[0].scatter(np.array(lx) * sx, np.array(ly) * sy, s=10, c="lime")
            row[0].set_title("Camera + landmarks", fontsize=10)
            col = 1

        ax_depth, ax_mask, ax_mat = row[col], row[col + 1], row[col + 2]
        depth = case["depth"]
        if res is None:
            ax_depth.imshow(depth_to_color(depth, 200, 2000))
            ax_mat.text(0.5, 0.5, "No depth on hand\n(too close / no texture?)",
                        ha="center", va="center")
        else:
            hd = res["hand_depth"]
            ax_depth.imshow(depth_to_color(depth, hd - 300, hd + 1200))
            draw_grid(ax_depth, res["bbox"])
            lx, ly = zip(*case["landmarks"])
            ax_depth.scatter(lx, ly, s=8, c="white")

            relief = depth_to_color(depth, hd - SPAN_MM / 2, hd + SPAN_MM / 2)
            relief[~res["mask"]] = 0
            x, y, w, h = res["bbox"]
            ax_mask.imshow(relief[y:y + h, x:x + w], extent=(x, x + w, y + h, y))
            draw_grid(ax_mask, res["bbox"])
            draw_matrix(ax_mat, res["matrix"])
            in_range = cfg.HAND_DEPTH_MIN <= hd <= cfg.HAND_DEPTH_MAX
            ax_mat.set_xlabel(
                f"hand at {hd:.0f} mm" + ("" if in_range else
                f"  (app would IGNORE: outside {cfg.HAND_DEPTH_MIN}-{cfg.HAND_DEPTH_MAX})"),
                fontsize=9, color="black" if in_range else "red")

        ax_depth.set_title(f"{case['title']}\nDepth (red=near) + 5x5 grid", fontsize=10)
        ax_mask.set_title("Pixels counted as hand\n(black = ignored)", fontsize=10)
        ax_mat.set_title("5x5 matrix (sent to Pico)\n" + case.get("note", ""), fontsize=9,
                         wrap=True)
        for ax in (ax_depth, ax_mask):
            ax.set_xticks([]); ax.set_yticks([])

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    print(f"\nSaved: {out_path}")
    if show:
        plt.show()


def print_case(case):
    print(f"\n=== {case['title']} ===")
    if case.get("note"):
        print(f"Expected: {case['note']}")
    res = case["result"]
    if res is None:
        print("No valid depth on the hand landmarks.")
        return
    print(f"Hand depth: {res['hand_depth']:.0f} mm   bbox: {res['bbox']}")
    for row in res["matrix"]:
        print("  " + " ".join(f"{int(v):4d}" for v in row))


# ----------------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------------

def mode_synthetic(show):
    cases = []
    for title, note, kwargs in SYNTHETIC_CASES:
        depth, landmarks = synthetic_hand(**kwargs)
        case = dict(title=title, note=note, depth=depth, landmarks=landmarks,
                    result=run_matrix(depth, landmarks))
        print_case(case)
        cases.append(case)
    render(cases, OUT_DIR / "hand_matrix_synthetic.png", show)


def load_capture(folder):
    folder = Path(folder)
    depth = np.load(folder / "depth.npy")
    landmarks = [tuple(p) for p in json.loads((folder / "landmarks.json").read_text())]
    rgb = cv2.imread(str(folder / "rgb.png"))
    return depth, landmarks, rgb


def mode_replay(folder, show):
    depth, landmarks, rgb = load_capture(folder)
    case = dict(title=f"Capture {Path(folder).name}", note="", depth=depth,
                landmarks=landmarks, rgb=rgb, result=run_matrix(depth, landmarks))
    print_case(case)
    render([case], Path(folder) / "hand_matrix.png", show)


def mode_capture(show):
    import hand_tracking_sprint2 as app  # starts MediaPipe; needs depthai

    pipeline, frames = app.create_pipeline()
    pipeline.start()
    detector = app.MediaPipeHandDetector(0.5)
    saved = None
    print("\nHold your hand 35-70 cm from the camera. SPACE = save frame, q = quit.")
    try:
        while True:
            rgb_msg, depth_msg = frames.get()
            rgb = rgb_msg.getCvFrame()
            depth = depth_msg.getFrame()
            bbox, landmarks, detected, _, _ = detector.detect_hand(rgb, depth_msg)

            preview = rgb.copy()
            sx, sy = rgb.shape[1] / depth.shape[1], rgb.shape[0] / depth.shape[0]
            if landmarks:
                for x, y in landmarks:
                    cv2.circle(preview, (int(x * sx), int(y * sy)), 3, (0, 255, 0), -1)
                hd = estimate_hand_depth(depth, landmarks)
                msg = f"Hand at {hd:.0f} mm - SPACE to save" if hd else "Hand found, no depth"
            else:
                msg = "No hand"
            cv2.putText(preview, msg, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("Capture (SPACE = save, q = quit)", preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" ") and landmarks:
                saved = ROOT / "captures" / time.strftime("%Y%m%d_%H%M%S")
                saved.mkdir(parents=True, exist_ok=True)
                np.save(saved / "depth.npy", depth)
                cv2.imwrite(str(saved / "rgb.png"), rgb)
                (saved / "landmarks.json").write_text(json.dumps([list(p) for p in landmarks]))
                print(f"Saved capture: {saved}")
                break
    finally:
        pipeline.stop()
        detector.close()
        cv2.destroyAllWindows()

    if saved:
        mode_replay(saved, show)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["synthetic", "capture", "replay"])
    parser.add_argument("folder", nargs="?", help="capture folder (replay mode)")
    parser.add_argument("--no-show", action="store_true", help="only save the PNG")
    args = parser.parse_args()

    if args.mode == "synthetic":
        mode_synthetic(not args.no_show)
    elif args.mode == "capture":
        mode_capture(not args.no_show)
    else:
        if not args.folder:
            parser.error("replay needs a capture folder, e.g. captures/20261105_183000")
        mode_replay(args.folder, not args.no_show)


if __name__ == "__main__":
    main()
