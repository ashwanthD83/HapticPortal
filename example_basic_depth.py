#!/usr/bin/env python3
"""
OAK-D Lite Basic Depth Capture Example

This is a simplified educational example that demonstrates the basic workflow
for capturing depth data from an OAK-D Lite stereo camera. Unlike the full
depth_capture_5x5.py script, this example:

- Does NOT downscale the depth map to 5x5
- Shows raw depth values at the center point of the frame
- Includes detailed comments explaining each step
- Focuses on understanding the basic depth capture workflow

This script is ideal for learning how the OAK-D Lite depth pipeline works
before moving on to more complex processing.

Requirements:
- Python 3.11
- opencv-contrib-python==4.7.0.72
- numpy==1.24.4
- depthai (latest stable)
- Calibrated OAK-D Lite device

Usage:
    python example_basic_depth.py

Press Ctrl+C to exit.

Validates Requirements: 5.1, 5.2, 5.3, 6.1, 9.2, 9.4
"""

import sys
import time

# Import required libraries
# - depthai: Interface with OAK-D Lite hardware
# - numpy: Array operations for depth data
try:
    import depthai as dai
    import numpy as np
except ImportError as e:
    print(f"Error: Failed to import required module: {e}")
    print("\nPlease ensure you have installed the required packages:")
    print("  pip install opencv-contrib-python==4.7.0.72")
    print("  pip install numpy==1.24.4")
    print("  pip install depthai")
    sys.exit(1)


def create_basic_pipeline():
    """
    Create a simple DepthAI pipeline for stereo depth capture.
    
    This function demonstrates the basic components needed for depth capture:
    
    1. Pipeline: Container for all processing nodes
    2. MonoCamera nodes: Capture grayscale images from left and right cameras
    3. StereoDepth node: Computes depth map from stereo image pair
    4. XLinkOut node: Streams depth data from device to host computer
    
    Returns:
        dai.Pipeline: Configured pipeline ready for device initialization
    """
    # Step 1: Create the pipeline container
    # The pipeline holds all processing nodes and their connections
    pipeline = dai.Pipeline()
    
    # Step 2: Create left and right mono camera nodes
    # The OAK-D Lite has two grayscale cameras for stereo vision
    print("Creating camera nodes...")
    mono_left = pipeline.create(dai.node.MonoCamera)
    mono_right = pipeline.create(dai.node.MonoCamera)
    
    # Step 3: Configure the left camera
    # - Resolution: 400p (640x400 pixels) - good balance of speed and quality
    # - Socket: LEFT - specifies which physical camera to use
    mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
    
    # Step 4: Configure the right camera (same settings as left)
    mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
    
    # Step 5: Create the stereo depth node
    # This node performs stereo matching to compute depth from the two camera images
    print("Creating stereo depth node...")
    stereo = pipeline.create(dai.node.StereoDepth)
    
    # Step 6: Configure stereo depth settings
    # - ACCURACY preset: Optimizes for accuracy over speed
    # - Left-right check: Validates depth by checking consistency between cameras
    # - Extended disparity: Disabled (not needed for most use cases)
    # - Subpixel: Disabled (faster processing, slightly less accurate)
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.ACCURACY)
    stereo.setLeftRightCheck(True)
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(False)
    
    # Step 7: Link camera outputs to stereo depth inputs
    # This connects the camera image streams to the stereo processing node
    print("Linking camera outputs to stereo depth node...")
    mono_left.out.link(stereo.left)
    mono_right.out.link(stereo.right)
    
    # Step 8: Create output node to stream depth data to host
    # XLinkOut sends data from the device to your Python script
    print("Creating output stream...")
    xout_depth = pipeline.create(dai.node.XLinkOut)
    xout_depth.setStreamName("depth")  # Name used to access this stream
    stereo.depth.link(xout_depth.input)
    
    print("Pipeline created successfully!\n")
    return pipeline


def display_depth_info(depth_frame, frame_count):
    """
    Display information about the captured depth frame.
    
    This function shows:
    - Frame dimensions (width x height)
    - Depth value at the center point
    - Depth data type and range
    
    Args:
        depth_frame: DepthAI depth frame object
        frame_count: Current frame number
    """
    # Extract the depth data as a numpy array
    # Each pixel contains a depth value in millimeters (mm)
    depth_data = depth_frame.getFrame()
    
    # Get frame dimensions
    height, width = depth_data.shape
    
    # Calculate center point coordinates
    center_y = height // 2
    center_x = width // 2
    
    # Get depth value at center point (in millimeters)
    center_depth_mm = depth_data[center_y, center_x]
    
    # Convert to centimeters and meters for easier reading
    center_depth_cm = center_depth_mm / 10.0
    center_depth_m = center_depth_mm / 1000.0
    
    # Get some statistics about the depth frame
    min_depth = np.min(depth_data)
    max_depth = np.max(depth_data)
    mean_depth = np.mean(depth_data)
    
    # Clear console and display information
    print("\033[H\033[J", end="")  # ANSI escape code to clear console
    print("=" * 70)
    print("OAK-D Lite Basic Depth Capture Example")
    print("=" * 70)
    print(f"Frame: {frame_count}")
    print(f"Resolution: {width} x {height} pixels")
    print()
    
    print("Center Point Depth:")
    print(f"  Position: ({center_x}, {center_y})")
    print(f"  Depth: {center_depth_mm:.0f} mm  |  {center_depth_cm:.1f} cm  |  {center_depth_m:.2f} m")
    print()
    
    print("Frame Statistics:")
    print(f"  Minimum depth: {min_depth:.0f} mm ({min_depth/1000:.2f} m)")
    print(f"  Maximum depth: {max_depth:.0f} mm ({max_depth/1000:.2f} m)")
    print(f"  Average depth: {mean_depth:.0f} mm ({mean_depth/1000:.2f} m)")
    print()
    
    print("Understanding the values:")
    print("  - Depth is measured in millimeters (mm)")
    print("  - Smaller values = closer to camera")
    print("  - Larger values = farther from camera")
    print("  - 0 or very large values may indicate invalid/uncertain depth")
    print()
    
    print("Try moving your hand in front of the camera to see values change!")
    print()
    print("=" * 70)
    print("Press Ctrl+C to exit")
    print()


def main():
    """
    Main function - orchestrates the depth capture workflow.
    
    Workflow:
    1. Create the stereo pipeline
    2. Initialize the OAK-D Lite device
    3. Get the depth output queue
    4. Loop: capture frames and display depth information
    5. Handle shutdown gracefully
    """
    device = None
    frame_count = 0
    
    try:
        # Step 1: Display startup information
        print("\n" + "=" * 70)
        print("OAK-D Lite Basic Depth Capture Example")
        print("=" * 70)
        print("\nThis example demonstrates basic depth capture without downscaling.")
        print("It shows raw depth values at the center point of the frame.\n")
        
        print("Initializing OAK-D Lite device...")
        print("Please ensure your device is connected via USB.\n")
        
        # Step 2: Create the stereo pipeline
        pipeline = create_basic_pipeline()
        
        # Step 3: Initialize the device with our pipeline
        # This uploads the pipeline to the device and starts processing
        try:
            device = dai.Device(pipeline)
            print("✓ Device initialized successfully!")
            print("✓ Starting depth capture...\n")
            time.sleep(1)  # Brief pause to let device stabilize
        except RuntimeError as e:
            print(f"✗ Error: Failed to initialize device: {e}")
            print("\nTroubleshooting steps:")
            print("1. Check that the OAK-D Lite is connected via USB")
            print("2. Try a different USB port (preferably USB 3.0)")
            print("3. Verify the device appears in Device Manager (Windows)")
            print("4. Try unplugging and replugging the device")
            print("5. Ensure no other application is using the device")
            return 1
        
        # Step 4: Get the output queue for depth frames
        # The queue buffers frames from the device
        # - name="depth": matches the stream name we set in create_basic_pipeline()
        # - maxSize=4: keep up to 4 frames in buffer
        # - blocking=False: don't wait if queue is empty, return None instead
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        # Step 5: Main capture loop
        # This runs continuously until user presses Ctrl+C
        print("Capturing depth frames...\n")
        while True:
            # Get the next depth frame from the queue
            # This is a non-blocking call - returns None if no frame available
            depth_frame = depth_queue.get()
            
            # Skip if no frame available yet
            if depth_frame is None:
                continue
            
            # Increment frame counter
            frame_count += 1
            
            # Display depth information for this frame
            try:
                display_depth_info(depth_frame, frame_count)
            except Exception as e:
                print(f"Error displaying depth info: {e}")
                continue
            
            # Small delay to prevent excessive CPU usage
            # This limits display updates to approximately 30 FPS
            time.sleep(0.033)
    
    except KeyboardInterrupt:
        # User pressed Ctrl+C - graceful shutdown
        print("\n\n" + "=" * 70)
        print("Shutdown requested by user")
        print("=" * 70)
    
    except Exception as e:
        # Unexpected error occurred
        print(f"\n\nUnexpected error: {e}")
        print("Please check your device connection and try again.")
        return 1
    
    finally:
        # Step 6: Cleanup - always close the device properly
        if device is not None:
            try:
                device.close()
                print("✓ Device closed successfully")
            except Exception as e:
                print(f"Warning: Error closing device: {e}")
        
        print(f"\nTotal frames captured: {frame_count}")
        print("Exiting.\n")
    
    return 0


if __name__ == "__main__":
    # Entry point - run main function and exit with its return code
    sys.exit(main())
