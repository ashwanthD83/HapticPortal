import numpy as np
import pytest

from src.rolling_average import RollingAverageFilter


def test_update_averages_available_samples_and_returns_uint8():
    smoother = RollingAverageFilter(window_size=3)

    first = smoother.update(np.array([[10, 20]], dtype=np.uint8))
    second = smoother.update(np.array([[20, 31]], dtype=np.uint8))

    np.testing.assert_array_equal(first, [[10, 20]])
    np.testing.assert_array_equal(second, [[15, 26]])
    assert second.dtype == np.uint8


def test_update_uses_only_most_recent_window():
    smoother = RollingAverageFilter(window_size=2)
    smoother.update(np.array([[0]], dtype=np.uint8))
    smoother.update(np.array([[20]], dtype=np.uint8))

    result = smoother.update(np.array([[40]], dtype=np.uint8))

    np.testing.assert_array_equal(result, [[30]])


def test_update_resets_history_when_input_shape_changes():
    smoother = RollingAverageFilter(window_size=2)
    smoother.update(np.array([[0]], dtype=np.uint8))

    result = smoother.update(np.array([[100, 200]], dtype=np.uint8))

    np.testing.assert_array_equal(result, [[100, 200]])


@pytest.mark.parametrize("window_size", [0, -1, 1.5, True])
def test_invalid_window_size_raises(window_size):
    with pytest.raises(ValueError, match="positive integer"):
        RollingAverageFilter(window_size=window_size)


def test_reset_discards_history():
    smoother = RollingAverageFilter(window_size=2)
    smoother.update(np.array([[0]], dtype=np.uint8))
    smoother.reset()

    result = smoother.update(np.array([[100]], dtype=np.uint8))

    np.testing.assert_array_equal(result, [[100]])
