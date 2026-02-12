"""
Property-based tests for depth clipping functionality.

Feature: oak-d-lite-stereo-workflow
"""

import numpy as np
from hypothesis import given, strategies as st
from src.depth_processor import clip_depth


# Feature: oak-d-lite-stereo-workflow, Property 1: Depth clipping bounds
@given(
    width=st.integers(min_value=10, max_value=1000),
    height=st.integers(min_value=10, max_value=1000)
)
def test_depth_clipping_bounds(width, height):
    """
    **Validates: Requirements 6.1**
    
    Property: For any depth frame data (numpy array), after applying the 
    clipping operation with max_mm=5000, all values in the resulting array 
    should be within the range [0, 5000].
    
    This test generates random depth arrays with values outside the valid 
    range [-1000, 10000] and verifies that clipping constrains all values 
    to [0, 5000].
    """
    # Generate random depth data with values outside valid range
    depth_data = np.random.randint(-1000, 10000, size=(height, width), dtype=np.int32)
    
    # Apply clipping with max_mm=5000
    depth_clipped = clip_depth(depth_data, max_mm=5000)
    
    # Verify all values are within bounds [0, 5000]
    assert np.all(depth_clipped >= 0), "All values should be >= 0"
    assert np.all(depth_clipped <= 5000), "All values should be <= 5000"
