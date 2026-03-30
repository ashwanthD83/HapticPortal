"""
Depth processing module for OAK-D Lite stereo workflow.

This module provides functions to process raw depth frames into normalized,
downscaled 5x5 arrays suitable for analysis.

Processing pipeline:
1. Clip depth values to 0-5000mm range
2. Normalize to 0-255 uint8 range
3. Downscale to 5x5 using area interpolation
"""

import numpy as np
import cv2


def clip_depth(depth_data, max_mm):
    """
    Clip depth values to the range [0, max_mm].
    
    Args:
        depth_data: numpy array of depth values in millimeters
        max_mm: maximum depth value in millimeters (e.g., 5000)
    
    Returns:
        numpy array with values clipped to [0, max_mm]
    """
    return np.clip(depth_data, 0, max_mm)


def normalize_depth(depth_clipped, max_value):
    """
    Normalize clipped depth values to 0-255 uint8 range.
    
    Args:
        depth_clipped: numpy array with depth values in range [0, max_value]
        max_value: maximum depth value used for normalization (e.g., 5000)
    
    Returns:
        numpy array with values normalized to [0, 255] as uint8
    """
    normalized = (depth_clipped / max_value * 255).astype(np.uint8)
    return normalized


def downscale_depth(depth_normalized, target_size):
    """
    Downscale normalized depth array to target size using area interpolation.
    
    Args:
        depth_normalized: numpy array with normalized depth values (uint8)
        target_size: tuple (width, height) for target dimensions (e.g., (5, 5))
    
    Returns:
        numpy array downscaled to target_size
    """
    return cv2.resize(depth_normalized, target_size, interpolation=cv2.INTER_AREA)


def process_depth_frame(depth_frame, max_mm=5000, target_size=(5, 5)):
    """
    Process a depth frame through the complete pipeline.
    
    Orchestrates the full processing pipeline:
    1. Extract depth data from frame
    2. Clip to 0-max_mm range
    3. Normalize to 0-255 uint8
    4. Downscale to target_size
    
    Args:
        depth_frame: DepthAI depth frame object with getFrame() method
        max_mm: clipping/normalization max depth in millimeters
        target_size: tuple (width, height) output size

    Returns:
        numpy array of shape target_size with normalized depth values (uint8)
    """
    # Extract depth data as numpy array
    depth_data = depth_frame.getFrame()
    
    # Clip to configured depth range
    depth_clipped = clip_depth(depth_data, max_mm)
    
    # Normalize to 0-255 uint8
    depth_normalized = normalize_depth(depth_clipped, max_mm)
    
    # Downscale to target grid
    depth_5x5 = downscale_depth(depth_normalized, target_size)
    
    return depth_5x5
