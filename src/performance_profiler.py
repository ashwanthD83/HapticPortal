#!/usr/bin/env python3
"""
Performance Profiler for OAK-D Lite Hand Tracking

Measures and tracks execution time for each pipeline stage.
"""

import time
from collections import deque
from typing import Dict, Optional, List


class PerformanceProfiler:
    """Measure and track execution time for each pipeline stage."""
    
    def __init__(self):
        self.stage_times: Dict[str, deque] = {}
        self.frame_times: deque = deque(maxlen=30)
        self.current_stage_start: Optional[float] = None
        self.current_stage_name: Optional[str] = None
        self.frame_start_time: Optional[float] = None
    
    def start_stage(self, stage_name: str) -> None:
        """Begin timing a processing stage."""
        self.current_stage_name = stage_name
        self.current_stage_start = time.perf_counter()
    
    def end_stage(self, stage_name: str) -> float:
        """End timing and return duration in milliseconds."""
        if self.current_stage_start is None:
            return 0.0
        
        end_time = time.perf_counter()
        duration_ms = (end_time - self.current_stage_start) * 1000.0
        
        # Initialize deque for this stage if needed
        if stage_name not in self.stage_times:
            self.stage_times[stage_name] = deque(maxlen=30)
        
        self.stage_times[stage_name].append(duration_ms)
        
        self.current_stage_start = None
        self.current_stage_name = None
        
        return duration_ms
    
    def start_frame(self) -> None:
        """Mark the start of a new frame."""
        self.frame_start_time = time.perf_counter()
    
    def end_frame(self) -> float:
        """Mark frame end and return total frame time."""
        if self.frame_start_time is None:
            return 0.0
        
        end_time = time.perf_counter()
        frame_time_ms = (end_time - self.frame_start_time) * 1000.0
        
        self.frame_times.append(frame_time_ms)
        self.frame_start_time = None
        
        return frame_time_ms
    
    def get_average_time(self, stage_name: str) -> float:
        """Get average time for a stage over last 30 frames."""
        if stage_name not in self.stage_times or len(self.stage_times[stage_name]) == 0:
            return 0.0
        
        times = list(self.stage_times[stage_name])
        return sum(times) / len(times)
    
    def get_peak_time(self, stage_name: str) -> float:
        """Get peak time for a stage over last 30 frames."""
        if stage_name not in self.stage_times or len(self.stage_times[stage_name]) == 0:
            return 0.0
        
        return max(self.stage_times[stage_name])
    
    def get_current_fps(self) -> float:
        """Calculate current FPS from frame times."""
        if len(self.frame_times) == 0:
            return 0.0
        
        avg_frame_time_ms = sum(self.frame_times) / len(self.frame_times)
        
        if avg_frame_time_ms <= 0:
            return 0.0
        
        fps = 1000.0 / avg_frame_time_ms
        return fps
    
    def get_average_frame_time(self) -> float:
        """Get average frame time over last 30 frames."""
        if len(self.frame_times) == 0:
            return 0.0
        
        return sum(self.frame_times) / len(self.frame_times)
    
    def get_peak_frame_time(self) -> float:
        """Get peak frame time over last 30 frames."""
        if len(self.frame_times) == 0:
            return 0.0
        
        return max(self.frame_times)
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get comprehensive performance statistics."""
        stats = {}
        
        for stage_name in self.stage_times:
            if len(self.stage_times[stage_name]) > 0:
                times = list(self.stage_times[stage_name])
                stats[stage_name] = {
                    'average_ms': sum(times) / len(times),
                    'peak_ms': max(times),
                    'min_ms': min(times),
                    'sample_count': len(times)
                }
        
        # Add frame stats
        if len(self.frame_times) > 0:
            frame_times_list = list(self.frame_times)
            stats['frame'] = {
                'average_ms': sum(frame_times_list) / len(frame_times_list),
                'peak_ms': max(frame_times_list),
                'min_ms': min(frame_times_list),
                'sample_count': len(frame_times_list),
                'fps': self.get_current_fps()
            }
        
        return stats
