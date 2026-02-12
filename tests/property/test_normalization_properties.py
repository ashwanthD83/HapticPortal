"""
Property-based tests for depth normalization functionality.

Feature: oak-d-lite-stereo-workflow
"""

import numpy as np
from hypothesis import given, strategies as st
from src.depth_processor import normalize_depth


# Feature: oak-d-lite-stereo-workflow, Property 2: Normalization range and type
@given(
    width=st.integers(min_value=10, max_value=1000),
    height=st.integers(min_value=10, max_value=1000)
)
def test_normalization_range_and_type(width, height):
    """
    **Validates: Requirements 6.2**
    
    Property: For any clipped depth array (values in range [0, 5000]), after 
    normalization, all values should be in the range [0, 255] and the array 
    dtype should be uint8.
    
    This test generates random clipped depth arrays with values in the valid 
    range [0, 5000] and verifies that normalization produces values in [0, 255] 
    with uint8 dtype.
    """
    # Generate random clipped depth data with values in range [0, 5000]
    depth_clipped = np.random.randint(0, 5001, size=(height, width), dtype=np.int32)
    
    # Apply normalization with max_value=5000
    depth_normalized = normalize_depth(depth_clipped, max_value=5000)
    
    # Verify all values are within range [0, 255]
    assert np.all(depth_normalized >= 0), "All values should be >= 0"
    assert np.all(depth_normalized <= 255), "All values should be <= 255"
    
    # Verify dtype is uint8
    assert depth_normalized.dtype == np.uint8, f"Array dtype should be uint8, got {depth_normalized.dtype}"
