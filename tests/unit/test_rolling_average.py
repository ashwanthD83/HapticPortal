"""Verify averaging, window eviction, and fresh tracking sessions."""

import numpy as np
import pytest

from src.rolling_average import RollingAverageFilter


def test_average_and_window_eviction():
    smoother = RollingAverageFilter(3)
    for value, expected in [(0, 0), (0, 0), (90, 30), (180, 90)]:
        result = smoother.update(np.full((5, 5), value, dtype=np.uint8))
        np.testing.assert_array_equal(result, np.full((5, 5), expected))
        assert result.dtype == np.uint8


def test_cells_are_independent_and_input_is_copied():
    smoother = RollingAverageFilter(2)
    sample = np.array([[0, 100], [200, 250]], dtype=np.uint8)
    smoother.update(sample)
    sample[:] = 0
    result = smoother.update(np.array([[100, 200], [100, 250]], dtype=np.uint8))
    np.testing.assert_array_equal(result, [[50, 150], [150, 250]])


def test_reset_starts_with_new_sample():
    smoother = RollingAverageFilter(5)
    smoother.update(np.full((5, 5), 255, dtype=np.uint8))
    smoother.reset()
    np.testing.assert_array_equal(smoother.update(np.zeros((5, 5))), np.zeros((5, 5)))


@pytest.mark.parametrize('window', [0, -1, 1.5, True])
def test_invalid_window(window):
    with pytest.raises(ValueError):
        RollingAverageFilter(window)
