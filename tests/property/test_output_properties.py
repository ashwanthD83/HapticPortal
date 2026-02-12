"""
Property-based tests for output type verification.

Feature: oak-d-lite-stereo-workflow
"""

import numpy as np
from hypothesis import given, strategies as st
from src.depth_processor import process_depth_frame


class MockDepthFrame:
    """Mock DepthAI depth frame for testing."""
    
    def __init__(self, depth_data):
        self._depth_data = depth_data
    
    def getFrame(self):
        """Return the depth data as numpy array."""
        return self._depth_data


# Feature: oak-d-lite-stereo-workflow, Property 4: Output type verification
@given(
    width=st.integers(min_value=10, max_value=1000),
    height=st.integers(min_value=10, max_value=1000)
)
def test_output_type_verification(width, height):
    """
    **Validates: Requirements 6.4**
    
    Property: For any processed depth data, the final output should be an 
    instance of numpy.ndarray.
    
    This test generates random depth frames with various dimensions and 
    verifies that the complete processing pipeline always returns a 
    numpy.ndarray instance.
    """
    # Generate random depth data with values in range [-1000, 10000]
    depth_data = np.random.randint(-1000, 10000, size=(height, width), dtype=np.int32)
    
    # Create mock depth frame
    mock_frame = MockDepthFrame(depth_data)
    
    # Process through complete pipeline
    result = process_depth_frame(mock_frame)
    
    # Verify output is numpy.ndarray instance
    assert isinstance(result, np.ndarray), f"Output should be numpy.ndarray, got {type(result)}"
