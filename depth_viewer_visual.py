#!/usr/bin/env python3
"""
OAK-D Lite Visual Depth Viewer

This script provides a visual interface showing:
- Live RGB camera feed
- Colorized depth map
- 5x5 depth array overlay
- Combined visualization

Press 'q' to quit.
"""

import sys
import cv2
import numpy as np

try:
    import depthai as dai
except ImportError as e:
    print(f"Error: Failed to import depthai: {e}")
    print("Install with: pip install depthai")
    sys.exit(1)

from src.depth_processor import process_depth_frame


def create_visual_pipeline():
    """
    Create pipeline with RGB camera, depth, and preview outputs.
    """
    pipeline = dai.Pipeline()
    
    # Create RGB camera for visual feed
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(640, 400)
    cam_rgb.setInterleaved(False)
    cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
    
    # Create mono cameras for stereo depth
    mono_left = pipeline.create(dai.node.MonoCamera)
    mono_right = pipeline.create(dai.node.MonoCamera)
    
    mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
    
    mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
    
    # Create stereo depth node
    stereo = pipeline.create(dai.node.StereoDepth)
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
    stereo.setLeftRightCheck(True)
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(False)
    
    # Link cameras to stereo
    mono_left.out.link(stereo.left)
    mono_right.out.link(stereo.right)
    
    # Create outputs
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)
    
    xout_depth = pipeline.create(dai.node.XLinkOut)
    xout_depth.setStreamName("depth")
    stereo.depth.link(xout_depth.input)
    
    return pipeline


def colorize_depth(depth_frame, max_depth=5000):
    """
    Convert depth map to colorized visualization.
    """
    depth_data = depth_frame.getFrame()
    
    # Ensure we're working with a numpy array
    if not isinstance(depth_data, np.ndarray):
        depth_data = np.array(depth_data)
    
    # Clip and normalize (explicit dtype to avoid numpy version issues)
    depth_clipped = np.clip(depth_data, 0, max_depth).astype(np.float32)
    depth_normalized = (depth_clipped / float(max_depth) * 255.0).astype(np.uint8)
    
    # Apply colormap (TURBO: blue=far, red=near)
    depth_colorized = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
    
    return depth_colorized, depth_normalized


def draw_5x5_overlay(image, depth_5x5, position="top-right"):
    """
    Draw 5x5 depth array as overlay on image.
    """
    h, w = image.shape[:2]
    cell_size = 60
    grid_size = 5 * cell_size
    padding = 20
    
    # Calculate position
    if position == "top-right":
        start_x = w - grid_size - padding
        start_y = padding
    elif position == "top-left":
        start_x = padding
        start_y = padding
    elif position == "bottom-right":
        start_x = w - grid_size - padding
        start_y = h - grid_size - padding
    else:  # bottom-left
        start_x = padding
        start_y = h - grid_size - padding
    
    # Draw semi-transparent background
    overlay = image.copy()
    cv2.rectangle(overlay, 
                  (start_x - 10, start_y - 10),
                  (start_x + grid_size + 10, start_y + grid_size + 10),
                  (0, 0, 0), -1)
    image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
    
    # Draw grid and values
    for i in range(5):
        for j in range(5):
            x = start_x + j * cell_size
            y = start_y + i * cell_size
            
            # Get value with explicit int conversion
            value = int(depth_5x5[i, j])
            
            # Color based on value (closer = warmer)
            if value > 200:
                color = (0, 0, 255)  # Red - very close
            elif value > 150:
                color = (0, 165, 255)  # Orange - close
            elif value > 100:
                color = (0, 255, 255)  # Yellow - medium
            elif value > 50:
                color = (0, 255, 0)  # Green - far
            else:
                color = (255, 0, 0)  # Blue - very far
            
            # Draw cell
            cv2.rectangle(image, (x, y), (x + cell_size, y + cell_size), (100, 100, 100), 1)
            
            # Draw value
            text = str(value)
            font_scale = 0.6
            thickness = 2
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            text_x = x + (cell_size - text_w) // 2
            text_y = y + (cell_size + text_h) // 2
            
            cv2.putText(image, text, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    # Add title
    cv2.putText(image, "5x5 Depth Array", 
               (start_x, start_y - 15),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return image


def create_combined_view(rgb_frame, depth_colorized, depth_5x5):
    """
    Create a combined view with RGB, depth map, and 5x5 overlay.
    """
    # Ensure same size
    h, w = rgb_frame.shape[:2]
    depth_resized = cv2.resize(depth_colorized, (w, h))
    
    # Create RGB with 5x5 overlay
    rgb_with_overlay = rgb_frame.copy()
    rgb_with_overlay = draw_5x5_overlay(rgb_with_overlay, depth_5x5, "top-right")
    
    # Create depth with 5x5 overlay
    depth_with_overlay = depth_resized.copy()
    depth_with_overlay = draw_5x5_overlay(depth_with_overlay, depth_5x5, "top-right")
    
    # Stack horizontally
    combined = np.hstack([rgb_with_overlay, depth_with_overlay])
    
    # Add labels
    cv2.putText(combined, "RGB Camera", (20, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(combined, "Depth Map", (w + 20, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Add instructions
    instructions = "Press 'q' to quit | Blue=Far, Red=Near"
    cv2.putText(combined, instructions, (20, h - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return combined


def main():
    """
    Main visualization loop.
    """
    print("=" * 70)
    print("OAK-D Lite Visual Depth Viewer")
    print("=" * 70)
    print("\nInitializing device...")
    
    try:
        # Create pipeline and device
        pipeline = create_visual_pipeline()
        device = dai.Device(pipeline)
        
        print("✓ Device initialized!")
        print("\nOpening windows...")
        print("  - RGB Camera: Live color feed")
        print("  - Depth Map: Colorized depth (blue=far, red=near)")
        print("  - Combined View: Both feeds with 5x5 overlay")
        print("\nPress 'q' in any window to quit\n")
        
        # Get output queues
        rgb_queue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        # Create windows
        cv2.namedWindow("RGB Camera", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Depth Map", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Combined View", cv2.WINDOW_NORMAL)
        
        frame_count = 0
        
        while True:
            # Get frames
            rgb_frame_data = rgb_queue.get()
            depth_frame_data = depth_queue.get()
            
            if rgb_frame_data is None or depth_frame_data is None:
                continue
            
            frame_count += 1
            
            # Process RGB frame
            rgb_frame = rgb_frame_data.getCvFrame()
            
            # Process depth frame
            depth_colorized, _ = colorize_depth(depth_frame_data)
            depth_5x5 = process_depth_frame(depth_frame_data)
            
            # Create visualizations
            rgb_display = rgb_frame.copy()
            depth_display = depth_colorized.copy()
            combined_display = create_combined_view(rgb_frame, depth_colorized, depth_5x5)
            
            # Add frame counter
            cv2.putText(rgb_display, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(depth_display, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display windows
            cv2.imshow("RGB Camera", rgb_display)
            cv2.imshow("Depth Map", depth_display)
            cv2.imshow("Combined View", combined_display)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
    
    except RuntimeError as e:
        print(f"\n✗ Error: Failed to initialize device: {e}")
        print("\nTroubleshooting:")
        print("1. Check that OAK-D Lite is connected via USB")
        print("2. Try a different USB port (USB 3.0 recommended)")
        print("3. Ensure no other application is using the device")
        return 1
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1
    
    finally:
        cv2.destroyAllWindows()
        print("\nWindows closed. Exiting.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
