"""
Unit tests for edge cases in depth processing.

Tests specific edge cases that may occur in real-world usage:
- All-zero depth frames
- All-maximum depth frames
- Mixed valid/invalid depth values

Feature: oak-d-lite-stereo-workflow
Requirements: 6.1, 6.2, 6.3
"""

import numpy as np
import pytest
from src.depth_processor import clip_depth, normalize_depth, downscale_depth


class TestAllZeroDepthFrames:
    """Test processing of depth frames with all-zero values."""
    
    def test_clip_all_zeros(self):
        """Test clipping with all-zero depth values."""
        depth_data = np.zeros((100, 100), dtype=np.int32)
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        
        assert np.all(depth_clipped == 0), "All values should remain 0"
        assert depth_clipped.shape == (100, 100), "Shape should be preserved"
    
    def test_normalize_all_zeros(self):
        """Test normalization with all-zero depth values."""
        depth_clipped = np.zeros((100, 100), dtype=np.int32)
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        
        assert np.all(depth_normalized == 0), "All values should remain 0"
        assert depth_normalized.dtype == np.uint8, "Output should be uint8"
        assert depth_normalized.shape == (100, 100), "Shape should be preserved"
    
    def test_downscale_all_zeros(self):
        """Test downscaling with all-zero depth values."""
        depth_normalized = np.zeros((100, 100), dtype=np.uint8)
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert np.all(depth_5x5 == 0), "All values should remain 0"
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"


class TestAllMaximumDepthFrames:
    """Test processing of depth frames with all-maximum values."""
    
    def test_clip_all_maximum_within_range(self):
        """Test clipping when all values are at maximum (5000mm)."""
        depth_data = np.full((100, 100), 5000, dtype=np.int32)
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        
        assert np.all(depth_clipped == 5000), "All values should remain 5000"
        assert depth_clipped.shape == (100, 100), "Shape should be preserved"
    
    def test_clip_all_maximum_exceeding_range(self):
        """Test clipping when all values exceed maximum (10000mm)."""
        depth_data = np.full((100, 100), 10000, dtype=np.int32)
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        
        assert np.all(depth_clipped == 5000), "All values should be clipped to 5000"
        assert depth_clipped.shape == (100, 100), "Shape should be preserved"
    
    def test_normalize_all_maximum(self):
        """Test normalization with all-maximum depth values (5000mm)."""
        depth_clipped = np.full((100, 100), 5000, dtype=np.int32)
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        
        assert np.all(depth_normalized == 255), "All values should be 255"
        assert depth_normalized.dtype == np.uint8, "Output should be uint8"
        assert depth_normalized.shape == (100, 100), "Shape should be preserved"
    
    def test_downscale_all_maximum(self):
        """Test downscaling with all-maximum depth values (255)."""
        depth_normalized = np.full((100, 100), 255, dtype=np.uint8)
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert np.all(depth_5x5 == 255), "All values should remain 255"
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"


class TestMixedValidInvalidDepthValues:
    """Test processing of depth frames with mixed valid/invalid values."""
    
    def test_clip_mixed_negative_and_positive(self):
        """Test clipping with mix of negative and positive values."""
        depth_data = np.array([
            [-100, 0, 1000, 5000, 10000],
            [-500, 500, 2500, 7500, 15000],
            [0, 1000, 3000, 5000, 8000]
        ], dtype=np.int32)
        
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        
        # Verify negative values are clipped to 0
        assert depth_clipped[0, 0] == 0, "Negative values should be clipped to 0"
        assert depth_clipped[1, 0] == 0, "Negative values should be clipped to 0"
        
        # Verify values within range are preserved
        assert depth_clipped[0, 2] == 1000, "Valid values should be preserved"
        assert depth_clipped[1, 2] == 2500, "Valid values should be preserved"
        
        # Verify values exceeding max are clipped to max
        assert depth_clipped[0, 4] == 5000, "Exceeding values should be clipped to 5000"
        assert depth_clipped[1, 4] == 5000, "Exceeding values should be clipped to 5000"
        assert depth_clipped[2, 4] == 5000, "Exceeding values should be clipped to 5000"
    
    def test_normalize_mixed_values(self):
        """Test normalization with mixed depth values."""
        depth_clipped = np.array([
            [0, 1250, 2500, 3750, 5000],
            [500, 1500, 2500, 3500, 4500],
            [0, 0, 5000, 5000, 0]
        ], dtype=np.int32)
        
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        
        # Verify normalization formula: (value / 5000) * 255
        assert depth_normalized[0, 0] == 0, "0mm should normalize to 0"
        assert depth_normalized[0, 4] == 255, "5000mm should normalize to 255"
        
        # Check approximate values for intermediate depths
        # 2500mm should normalize to ~127-128
        assert 126 <= depth_normalized[0, 2] <= 128, "2500mm should normalize to ~127"
        
        assert depth_normalized.dtype == np.uint8, "Output should be uint8"
    
    def test_downscale_mixed_values(self):
        """Test downscaling with mixed depth values."""
        # Create a pattern with distinct regions
        depth_normalized = np.zeros((100, 100), dtype=np.uint8)
        depth_normalized[0:50, 0:50] = 0      # Top-left: zero
        depth_normalized[0:50, 50:100] = 255  # Top-right: maximum
        depth_normalized[50:100, 0:50] = 128  # Bottom-left: mid-range
        depth_normalized[50:100, 50:100] = 64 # Bottom-right: low-range
        
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"
        
        # Verify that downscaling produces reasonable averaged values
        # The exact values depend on INTER_AREA interpolation, but should be within range
        assert np.all(depth_5x5 >= 0), "All values should be >= 0"
        assert np.all(depth_5x5 <= 255), "All values should be <= 255"
    
    def test_clip_sparse_invalid_values(self):
        """Test clipping with sparse invalid values in mostly valid data."""
        # Create mostly valid data with some invalid values
        depth_data = np.random.randint(1000, 4000, size=(50, 50), dtype=np.int32)
        
        # Add some invalid values
        depth_data[0, 0] = -1000  # Negative
        depth_data[10, 10] = 10000  # Exceeding max
        depth_data[25, 25] = -500  # Negative
        depth_data[40, 40] = 8000  # Exceeding max
        
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        
        # Verify invalid values are clipped
        assert depth_clipped[0, 0] == 0, "Negative should be clipped to 0"
        assert depth_clipped[25, 25] == 0, "Negative should be clipped to 0"
        assert depth_clipped[10, 10] == 5000, "Exceeding should be clipped to 5000"
        assert depth_clipped[40, 40] == 5000, "Exceeding should be clipped to 5000"
        
        # Verify valid values are preserved
        assert np.all(depth_clipped[1:10, 1:10] >= 1000), "Valid values should be preserved"
        assert np.all(depth_clipped[1:10, 1:10] <= 4000), "Valid values should be preserved"


class TestEdgeCaseIntegration:
    """Test complete processing pipeline with edge case inputs."""
    
    def test_pipeline_with_all_zeros(self):
        """Test complete pipeline with all-zero input."""
        depth_data = np.zeros((100, 100), dtype=np.int32)
        
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert np.all(depth_5x5 == 0), "All values should be 0"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"
    
    def test_pipeline_with_all_maximum(self):
        """Test complete pipeline with all-maximum input."""
        depth_data = np.full((100, 100), 10000, dtype=np.int32)
        
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert np.all(depth_5x5 == 255), "All values should be 255"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"
    
    def test_pipeline_with_mixed_values(self):
        """Test complete pipeline with mixed valid/invalid values."""
        # Create mixed data
        depth_data = np.random.randint(-1000, 10000, size=(100, 100), dtype=np.int32)
        
        depth_clipped = clip_depth(depth_data, max_mm=5000)
        depth_normalized = normalize_depth(depth_clipped, max_value=5000)
        depth_5x5 = downscale_depth(depth_normalized, target_size=(5, 5))
        
        assert depth_5x5.shape == (5, 5), "Output should be 5x5"
        assert np.all(depth_5x5 >= 0), "All values should be >= 0"
        assert np.all(depth_5x5 <= 255), "All values should be <= 255"
        assert depth_5x5.dtype == np.uint8, "Output should be uint8"
