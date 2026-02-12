"""
Property-based tests for depth downscaling functionality.

Feature: oak-d-lite-stereo-workflow
"""

import numpy as np
from hypothesis import given, strategies as st
from src.depth_processor import downscale_depth


# Feature: oak-d-lite-stereo-workflow, Property 3: Downscaling dimensions
@given(
    width=st.integers(min_value=10, max_value=1000),
    height=st.integers(min_value=10, max_value=1000)
)
def test_downscaling_dimensions(width, height):
    """
    **Validates: Requirements 6.3**
    
    Property: For any normalized depth array (uint8, any dimensions), after 
    downscaling with target size (5, 5) using cv2.resize with INTER_AREA 
    interpolation, the resulting array shape should be exactly (5, 5).
    
    This test generates random normalized depth arrays with various dimensions 
    and verifies that downscaling always produces a (5, 5) output shape.
    """
    # Generate random normalized depth data with values in range [0, 255]
    depth_normalized = np.random.randint(0, 256, size=(height, width), dtype=np.uint8)
    
    # Apply downscaling to target size (5, 5)
    depth_downscaled = downscale_depth(depth_normalized, target_size=(5, 5))
    
    # Verify output shape is exactly (5, 5)
    assert depth_downscaled.shape == (5, 5), f"Output shape should be (5, 5), got {depth_downscaled.shape}"
