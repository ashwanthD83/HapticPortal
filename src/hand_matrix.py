"""Turn an aligned depth frame plus MediaPipe landmarks into a 5x5 hand matrix.

Output convention (sent over UDP):
    0       = no hand in that cell (background, gap between fingers, no depth)
    1..255  = hand surface, higher = closer to the camera

Values are measured relative to the hand's own reference depth over a fixed
span (``span_mm``), so a flat hand gives a flat matrix and noise is not
stretched to the full 0-255 range.
"""

import cv2
import numpy as np


def estimate_hand_depth(depth, landmarks_px, patch_radius=3):
    """Robust reference depth (mm) of the hand, or None.

    Takes the median of valid depth in a small patch around each landmark,
    then the median across landmarks. Landmarks sit on the hand itself, so this
    ignores background pixels inside the bounding box.
    """
    if not landmarks_px:
        return None
    h, w = depth.shape
    samples = []
    for x, y in landmarks_px:
        x0, x1 = max(0, x - patch_radius), min(w, x + patch_radius + 1)
        y0, y1 = max(0, y - patch_radius), min(h, y + patch_radius + 1)
        patch = depth[y0:y1, x0:x1]
        valid = patch[patch > 0]
        if valid.size:
            # Fingertip patches can overlap background; the hand is the nearer
            # surface, so a low percentile picks it without chasing speckle.
            samples.append(float(np.percentile(valid, 30)))
    # Need a reasonable number of landmarks with depth to trust the estimate.
    if len(samples) < 5:
        return None
    return float(np.median(samples))


def build_hand_mask(depth, landmarks_px, hand_depth, band_mm, dilate_px):
    """Boolean mask of pixels that belong to the hand.

    A pixel is hand if it is inside the (dilated) convex hull of the landmarks
    AND its depth is within ``band_mm`` of the hand's reference depth.
    """
    h, w = depth.shape
    hull_mask = np.zeros((h, w), dtype=np.uint8)
    pts = np.array(landmarks_px, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillConvexPoly(hull_mask, cv2.convexHull(pts), 255)
    if dilate_px > 0:
        k = 2 * int(dilate_px) + 1
        hull_mask = cv2.dilate(hull_mask, np.ones((k, k), np.uint8))
    in_band = (depth > 0) & (np.abs(depth.astype(np.int32) - int(hand_depth)) <= band_mm)
    return (hull_mask > 0) & in_band


def hand_depth_matrix(depth, mask, bbox, hand_depth, span_mm,
                      min_coverage=0.15, grid=5):
    """Compute the grid x grid matrix over ``bbox`` using only masked pixels.

    Each cell is the median depth of its hand pixels, mapped so that
    ``hand_depth + span/2`` -> 1 and ``hand_depth - span/2`` -> 255.
    Cells with less than ``min_coverage`` hand pixels are 0.
    """
    out = np.zeros((grid, grid), dtype=np.uint8)
    if bbox is None:
        return out
    h, w = depth.shape
    x, y, bw, bh = bbox
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
    if x1 - x0 < grid or y1 - y0 < grid:
        return out

    xs = np.linspace(x0, x1, grid + 1).astype(int)
    ys = np.linspace(y0, y1, grid + 1).astype(int)
    far = hand_depth + span_mm / 2.0

    for i in range(grid):
        for j in range(grid):
            cell_d = depth[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            cell_m = mask[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            if cell_d.size == 0:
                continue
            vals = cell_d[cell_m]
            if vals.size < min_coverage * cell_d.size:
                continue
            closeness = (far - float(np.median(vals))) / span_mm
            out[i, j] = int(round(1 + 254 * min(1.0, max(0.0, closeness))))
    return out


class ExponentialSmoother:
    """Exponential moving average for scalars or small tuples/arrays."""

    def __init__(self, alpha):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.value = None

    def update(self, sample):
        sample = np.asarray(sample, dtype=np.float64)
        if self.value is None or self.value.shape != sample.shape:
            self.value = sample
        else:
            self.value = self.alpha * sample + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None


def bbox_from_landmarks(landmarks_px, frame_shape, pad=0.10):
    """(x, y, w, h) box around the landmarks with ``pad`` margin on each side."""
    h, w = frame_shape[:2]
    xs = [p[0] for p in landmarks_px]
    ys = [p[1] for p in landmarks_px]
    x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
    pad_x, pad_y = int((x_max - x_min) * pad), int((y_max - y_min) * pad)
    x0, y0 = max(0, x_min - pad_x), max(0, y_min - pad_y)
    x1, y1 = min(w - 1, x_max + pad_x), min(h - 1, y_max + pad_y)
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def compute_hand_matrix(depth, bbox, landmarks_px, hand_depth,
                        band_mm, span_mm, min_coverage):
    """Full matrix step used by the app. Returns (matrix_5x5, hand_mask)."""
    dilate_px = max(4, bbox[2] // 15)
    mask = build_hand_mask(depth, landmarks_px, hand_depth, band_mm, dilate_px)
    matrix = hand_depth_matrix(depth, mask, bbox, hand_depth, span_mm, min_coverage)
    return matrix, mask
