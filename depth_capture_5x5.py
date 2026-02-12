#!/usr/bin/env python3
"""
OAK-D Lite Depth Capture Script - 5x5 Downscaled Output

This script captures stereo depth data from an OAK-D Lite device and displays
a continuously updating 5x5 downscaled depth array. The output responds to
hand movement and provides a simplified view of the depth scene.

Requirements:
- Python 3.11
- opencv-contrib-python==4.7.0.72
- numpy==1.24.4
- depthai (latest stable)
- Calibrated OAK-D Lite device

Usage:
    python depth_capture_5x5.py

Press Ctrl+C to exit.

Validates Requirements: 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 8.4, 9.2, 9.4
"""

import sys
import os
import time

try:
    import depthai as dai
    import numpy as np
    import cv2
except ImportError as e:
    print(f"Error: Failed to import required module: {e}")
    print("\nPlease ensure you have installed the required packages:")
    print("  pip install opencv-contrib-python==4.7.0.72")
    print("  pip install numpy==1.24.4")
    print("  pip install depthai")
    sys.exit(1)

# Import local modules
try:
    from src.pipeline_builder import create_stereo_pipeline
    from src.depth_processor import process_depth_frame
except ImportError as e:
    print(f"Error: Failed to import local modules: {e}")
    print("\nPlease ensure you are running from the project root directory")
    print("and that src/pipeline_builder.py and src/depth_processor.py exist.")
    sys.exit(1)


def clear_console():
    """Clear the console for cleaner output display."""
    # ANSI escape sequence for clearing console
    print("\033[H\033[J", end="")


def display_depth_array(depth_5x5, frame_count):
    """
    Display the 5x5 depth array with formatting.
    
    Args:
        depth_5x5: numpy array of shape (5, 5) with depth values (0-255)
        frame_count: current frame number for display
    """
    clear_console()
    print("=" * 50)
    print("OAK-D Lite Depth Capture - 5x5 Downscaled Output")
    print("=" * 50)
    print(f"Frame: {frame_count}")
    print("\nDepth Array (5x5) - Values: 0 (far) to 255 (near):")
    print("-" * 50)
    
    # Display array with nice formatting
    for row in depth_5x5:
        print("  [", end="")
        for i, val in enumerate(row):
            if i > 0:
                print(" ", end="")
            print(f"{val:3d}", end="")
        print(" ]")
    
    print("-" * 50)
    print("\nPress Ctrl+C to exit")
    print()


def main():
    """
    Main function to initialize device, capture depth frames, and display output.
    
    This function:
    1. Creates a DepthAI stereo pipeline
    2. Initializes the OAK-D Lite device
    3. Captures depth frames in a continuous loop
    4. Processes frames through the depth processing pipeline
    5. Displays the 5x5 downscaled depth array
    6. Handles errors and graceful shutdown
    """
    device = None
    frame_count = 0
    
    try:
        print("Initializing OAK-D Lite device...")
        print("Please ensure your device is connected via USB.")
        print()
        
        # Create stereo pipeline (Requirement 5.1, 5.2, 5.3)
        pipeline = create_stereo_pipeline()
        
        # Initialize device with pipeline
        try:
            device = dai.Device(pipeline)
            print("Device initialized successfully!")
            print("Starting depth capture...\n")
            time.sleep(1)  # Brief pause before starting capture
        except RuntimeError as e:
            print(f"Error: Failed to initialize device: {e}")
            print("\nTroubleshooting steps:")
            print("1. Check that the OAK-D Lite is connected via USB")
            print("2. Try a different USB port (preferably USB 3.0)")
            print("3. Verify the device appears in Device Manager (Windows)")
            print("4. Try unplugging and replugging the device")
            print("5. Ensure no other application is using the device")
            return 1
        
        # Get output queue for depth frames
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        # Main capture loop (Requirement 7.1, 7.2, 7.3, 7.4)
        while True:
            # Get depth frame from queue
            depth_frame = depth_queue.get()
            
            if depth_frame is None:
                continue
            
            frame_count += 1
            
            # Process depth frame (Requirement 6.1, 6.2, 6.3, 6.4)
            try:
                depth_5x5 = process_depth_frame(depth_frame)
            except Exception as e:
                print(f"Error processing depth frame: {e}")
                continue
            
            # Display output (Requirement 7.1, 7.2)
            display_depth_array(depth_5x5, frame_count)
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.033)  # ~30 FPS
    
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C (Requirement 7.4)
        print("\n\nShutdown requested by user.")
        print("Cleaning up...")
    
    except Exception as e:
        # Handle unexpected errors
        print(f"\n\nUnexpected error occurred: {e}")
        print("Please check your device connection and try again.")
        return 1
    
    finally:
        # Ensure device is properly closed
        if device is not None:
            try:
                device.close()
                print("Device closed successfully.")
            except Exception as e:
                print(f"Warning: Error closing device: {e}")
        
        print(f"\nTotal frames captured: {frame_count}")
        print("Exiting.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
