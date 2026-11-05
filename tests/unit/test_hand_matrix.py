import numpy as np
import pytest

from src.hand_matrix import (
    ExponentialSmoother,
    build_hand_mask,
    estimate_hand_depth,
    hand_depth_matrix,
)

H, W = 480, 640
BBOX = (200, 100, 200, 200)  # x, y, w, h
HAND_MM = 500
SPAN = 150


def make_scene(hand_mm=HAND_MM, background_mm=1500, noise_mm=0, seed=0):
    """Flat square 'hand' inside BBOX on a far background."""
    rng = np.random.default_rng(seed)
    depth = np.full((H, W), background_mm, dtype=np.uint16)
    x, y, w, h = BBOX
    depth[y:y + h, x:x + w] = hand_mm
    if noise_mm:
        depth = (depth + rng.normal(0, noise_mm, depth.shape)).clip(1).astype(np.uint16)
    # Real bboxes are built from the landmark extent, so landmarks reach the edges.
    landmarks = [(x + (w - 1) * i // 4, y + (h - 1) * j // 4) for i in range(5) for j in range(5)][:21]
    landmarks += [(x + w - 1, y + h - 1)]
    return depth, landmarks


def matrix_for(depth, landmarks, bbox=BBOX):
    hand_mm = estimate_hand_depth(depth, landmarks)
    mask = build_hand_mask(depth, landmarks, hand_mm, band_mm=120, dilate_px=10)
    return hand_depth_matrix(depth, mask, bbox, hand_mm, SPAN), hand_mm


def test_hand_depth_ignores_background():
    depth, landmarks = make_scene()
    assert estimate_hand_depth(depth, landmarks) == pytest.approx(HAND_MM)


def test_hand_depth_none_without_valid_pixels():
    depth, landmarks = make_scene()
    depth[:] = 0
    assert estimate_hand_depth(depth, landmarks) is None


def test_flat_hand_gives_flat_mid_matrix():
    depth, landmarks = make_scene()
    matrix, _ = matrix_for(depth, landmarks)
    np.testing.assert_array_equal(matrix, np.full((5, 5), 128))


def test_background_cells_are_zero():
    depth, landmarks = make_scene()
    # Box twice as wide as the hand: right-hand cells are pure background.
    wide = (BBOX[0], BBOX[1], BBOX[2] * 2, BBOX[3])
    matrix, _ = matrix_for(depth, landmarks, bbox=wide)
    assert (matrix[:, :2] > 0).all()
    assert (matrix[:, 3:] == 0).all()


def test_closer_part_of_hand_gives_higher_values():
    depth, landmarks = make_scene()
    x, y, w, h = BBOX
    depth[y:y + h, x:x + w] = np.linspace(560, 440, w, dtype=np.uint16)[None, :]
    matrix, _ = matrix_for(depth, landmarks)
    assert (np.diff(matrix.astype(int), axis=1) > 0).all()


def test_sensor_noise_is_not_amplified():
    """Old code stretched noise to 0-255; now 5 mm noise moves cells only a few levels."""
    frames = []
    for seed in range(10):
        depth, landmarks = make_scene(noise_mm=5, seed=seed)
        frames.append(matrix_for(depth, landmarks)[0].astype(int))
    spread = np.ptp(np.stack(frames), axis=0)
    assert spread.max() <= 4


def test_empty_bbox_returns_zeros():
    depth, _ = make_scene()
    np.testing.assert_array_equal(
        hand_depth_matrix(depth, np.ones_like(depth, bool), None, HAND_MM, SPAN),
        np.zeros((5, 5)),
    )


def test_exponential_smoother():
    s = ExponentialSmoother(0.5)
    assert s.update(10.0) == 10.0
    assert s.update(20.0) == 15.0
    s.reset()
    assert s.update(4.0) == 4.0
    with pytest.raises(ValueError):
        ExponentialSmoother(0)
