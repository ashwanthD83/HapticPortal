"""Temporal smoothing for the portal's normalized depth matrices."""

# pyright: reportMissingImports=false
from collections import deque

import numpy as np


class RollingAverageFilter:
    """Average each cell over the most recent frames, returning uint8 values."""

    def __init__(self, window_size=5):
        if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size < 1:
            raise ValueError("window_size must be a positive integer")
        self.window_size = window_size
        self.history = deque(maxlen=window_size)

    def update(self, new_array):
        sample = np.array(new_array, dtype=np.float32, copy=True)
        if self.history and sample.shape != self.history[0].shape:
            self.reset()
        self.history.append(sample)
        # Average available frames during startup; do not pad with zeros.
        average = np.mean(np.stack(self.history), axis=0)
        return np.clip(np.rint(average), 0, 255).astype(np.uint8)

    def reset(self):
        """Discard samples when tracking or depth calibration changes."""
        self.history.clear()
