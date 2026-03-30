#!/usr/bin/env python3
"""
Calibration Manager for OAK-D Lite Hand Tracking

Handles real-time depth range adjustments with validation.
"""

import time
from typing import Tuple, Optional


class CalibrationManager:
    """Handle real-time depth range adjustments with validation."""
    
    def __init__(self, config_path: str, initial_min: int = 200, initial_max: int = 1200):
        self.config_path = config_path
        self.depth_min = initial_min
        self.depth_max = initial_max
        self.is_modified = False
        self.last_adjustment_time = 0.0
        
        # Validation constraints
        self.MIN_DEPTH_MIN = 50
        self.MAX_DEPTH_MIN = 2000
        self.MIN_DEPTH_MAX = 100
        self.MAX_DEPTH_MAX = 5000
        self.MIN_GAP = 50
    
    def increase_max(self, step: int = 50) -> Tuple[int, int]:
        """Increase HAND_DEPTH_MAX by step, return (min, max)."""
        self.depth_max = min(self.MAX_DEPTH_MAX, self.depth_max + step)
        self.validate_range()
        self.is_modified = True
        self.last_adjustment_time = time.time()
        return (self.depth_min, self.depth_max)
    
    def decrease_max(self, step: int = 50) -> Tuple[int, int]:
        """Decrease HAND_DEPTH_MAX by step, return (min, max)."""
        self.depth_max = max(self.MIN_DEPTH_MAX, self.depth_max - step)
        self.validate_range()
        self.is_modified = True
        self.last_adjustment_time = time.time()
        return (self.depth_min, self.depth_max)
    
    def increase_min(self, step: int = 50) -> Tuple[int, int]:
        """Increase HAND_DEPTH_MIN by step, return (min, max)."""
        self.depth_min = min(self.MAX_DEPTH_MIN, self.depth_min + step)
        self.validate_range()
        self.is_modified = True
        self.last_adjustment_time = time.time()
        return (self.depth_min, self.depth_max)
    
    def decrease_min(self, step: int = 50) -> Tuple[int, int]:
        """Decrease HAND_DEPTH_MIN by step, return (min, max)."""
        self.depth_min = max(self.MIN_DEPTH_MIN, self.depth_min - step)
        self.validate_range()
        self.is_modified = True
        self.last_adjustment_time = time.time()
        return (self.depth_min, self.depth_max)
    
    def validate_range(self) -> bool:
        """Ensure min < max and values within bounds."""
        # Clamp to valid ranges
        self.depth_min = max(self.MIN_DEPTH_MIN, min(self.MAX_DEPTH_MIN, self.depth_min))
        self.depth_max = max(self.MIN_DEPTH_MAX, min(self.MAX_DEPTH_MAX, self.depth_max))
        
        # Ensure min < max with minimum gap
        if self.depth_min >= self.depth_max - self.MIN_GAP:
            self.depth_min = self.depth_max - self.MIN_GAP
            # Re-clamp min if needed
            if self.depth_min < self.MIN_DEPTH_MIN:
                self.depth_min = self.MIN_DEPTH_MIN
                self.depth_max = self.depth_min + self.MIN_GAP
        
        return self.depth_min < self.depth_max
    
    def apply_to_globals(self, globals_dict: dict) -> None:
        """Update global HAND_DEPTH_MIN/MAX variables."""
        globals_dict['HAND_DEPTH_MIN'] = self.depth_min
        globals_dict['HAND_DEPTH_MAX'] = self.depth_max
    
    def get_adjustment_message(self, duration: float = 2.0) -> Optional[str]:
        """Get temporary message if recent adjustment."""
        if time.time() - self.last_adjustment_time < duration:
            return f"Range: {self.depth_min}-{self.depth_max}mm"
        return None
    
    def is_default(self) -> bool:
        """Check if using default values."""
        return self.depth_min == 200 and self.depth_max == 1200
    
    def reset_to_defaults(self) -> Tuple[int, int]:
        """Reset to default calibration values."""
        self.depth_min = 200
        self.depth_max = 1200
        self.is_modified = True
        self.last_adjustment_time = time.time()
        return (self.depth_min, self.depth_max)
