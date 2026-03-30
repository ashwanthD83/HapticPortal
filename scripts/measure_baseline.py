#!/usr/bin/env python3
"""
Baseline Performance Measurement Script

Runs the hand tracking system for 300 frames and records timing data.
Calculates mean, median, 95th percentile for each stage.
"""

import sys
import json
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.performance_profiler import PerformanceProfiler


def calculate_percentile(values, percentile):
    """Calculate percentile of a list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100.0)
    return sorted_values[min(index, len(sorted_values) - 1)]


def analyze_baseline(profiler, num_frames=300):
    """Analyze baseline performance metrics."""
    print(f"\n{'='*70}")
    print("BASELINE PERFORMANCE METRICS")
    print(f"{'='*70}\n")
    
    stats = profiler.get_stats()
    
    # Frame statistics
    if 'frame' in stats:
        frame_stats = stats['frame']
        frame_times = list(profiler.frame_times)
        
        print("Frame Processing:")
        print(f"  Average: {frame_stats['average_ms']:.2f}ms")
        print(f"  Median: {calculate_percentile(frame_times, 50):.2f}ms")
        print(f"  95th percentile: {calculate_percentile(frame_times, 95):.2f}ms")
        print(f"  Peak: {frame_stats['peak_ms']:.2f}ms")
        print(f"  Min: {frame_stats['min_ms']:.2f}ms")
        print(f"  FPS: {frame_stats['fps']:.2f}")
        print()
    
    # Stage statistics
    print("Stage Breakdown:")
    for stage_name in sorted(stats.keys()):
        if stage_name == 'frame':
            continue
        
        stage_stats = stats[stage_name]
        stage_times = list(profiler.stage_times[stage_name])
        
        print(f"\n  {stage_name}:")
        print(f"    Average: {stage_stats['average_ms']:.2f}ms")
        print(f"    Median: {calculate_percentile(stage_times, 50):.2f}ms")
        print(f"    95th percentile: {calculate_percentile(stage_times, 95):.2f}ms")
        print(f"    Peak: {stage_stats['peak_ms']:.2f}ms")
        print(f"    Min: {stage_stats['min_ms']:.2f}ms")
    
    # Save to file
    baseline_data = {
        'num_frames': num_frames,
        'frame': {
            'average_ms': frame_stats['average_ms'] if 'frame' in stats else 0,
            'median_ms': calculate_percentile(frame_times, 50) if 'frame' in stats else 0,
            'percentile_95_ms': calculate_percentile(frame_times, 95) if 'frame' in stats else 0,
            'peak_ms': frame_stats['peak_ms'] if 'frame' in stats else 0,
            'min_ms': frame_stats['min_ms'] if 'frame' in stats else 0,
            'fps': frame_stats['fps'] if 'frame' in stats else 0
        },
        'stages': {}
    }
    
    for stage_name in stats.keys():
        if stage_name == 'frame':
            continue
        
        stage_stats = stats[stage_name]
        stage_times = list(profiler.stage_times[stage_name])
        
        baseline_data['stages'][stage_name] = {
            'average_ms': stage_stats['average_ms'],
            'median_ms': calculate_percentile(stage_times, 50),
            'percentile_95_ms': calculate_percentile(stage_times, 95),
            'peak_ms': stage_stats['peak_ms'],
            'min_ms': stage_stats['min_ms']
        }
    
    # Save to JSON
    output_file = Path(__file__).parent.parent / 'baseline_metrics.json'
    with open(output_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Baseline metrics saved to: {output_file}")
    print(f"{'='*70}\n")
    
    return baseline_data


if __name__ == "__main__":
    print("This script should be run after collecting 300 frames of data.")
    print("Run hand_tracking_visual.py and let it run for ~10 seconds, then use this")
    print("script to analyze the profiler data.")
