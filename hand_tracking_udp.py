#!/usr/bin/env python3
"""
OAK-D Lite Hand Tracking with UDP Transmission

This script:
1. Detects and crops to the user's hand (ignoring background)
2. Applies rolling average smoothing to stabilize depth values
3. Sends the 5x5 depth array via UDP to a Raspberry Pi Pico

Press 'q' to quit.
Press 's' to toggle UDP sending.
"""

import sys
import cv2
import numpy as np
import socket
import struct
import time
from collections import deque

try:
    import depthai as dai
except ImportError as e:
    print(f"Error: Failed to import depthai: {e}")
    print("Install with: pip install depthai")
    sys.exit(1)

from src.depth_processor import process_depth_frame


# ============================================================================
# Configuration
# ============================================================================

# UDP Configuration
PICO_IP = "192.168.1.100"  # Change this to your Pico's IP address
PICO_PORT = 5000           # Change this to match your Pico's listening port
UDP_ENABLED = True         # Start with UDP enabled

# Hand Detection Configuration
HAND_DEPTH_MIN = 200       # Minimum depth in mm (20cm)
HAND_DEPTH_MAX = 1500      # Maximum depth in mm (150cm)
MIN_HAND_AREA = 1000       # Minimum contour area to be considered a hand
MAX_HAND_AREA = 100000     # Maximum contour area

# Smoothing Configuration
SMOOTHING_WINDOW = 5       # Number of frames to average (higher = smoother but slower response)


# ============================================================================
# Rolling Average Filter
# ============================================================================

class RollingAverageFilter:
    """
    Implements a rolling average filter for smoothing 5x5 depth arrays.
    """
    
    def __init__(self, window_size=5):
        """
        Initialize the filter.
        
        Args:
            window_size: Number of frames to average
        """
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
    
    def update(self, new_array):
        """
        Add a new array and return the smoothed result.
        
        Args:
            new_array: New 5x5 numpy array
            
        Returns:
            Smoothed 5x5 numpy array
        """
        self.history.append(new_array.copy())
        
        if len(self.history) == 0:
            return new_array
        
        # Calculate average across all frames in history
        smoothed = np.mean(self.history, axis=0).astype(np.uint8)
        return smoothed
    
    def reset(self):
        """Clear the history buffer."""
        self.history.clear()


# ============================================================================
# Hand Detection
# ============================================================================

def detect_hand_region(depth_frame):
    """
    Detect the hand region in the depth frame and return a cropped region.
    
    Args:
        depth_frame: Raw depth frame from camera
        
    Returns:
        tuple: (hand_mask, hand_bbox, hand_detected)
            - hand_mask: Binary mask of hand region
            - hand_bbox: Bounding box (x, y, w, h) or None
            - hand_detected: Boolean indicating if hand was found
    """
    depth_data = depth_frame.getFrame()
    h, w = depth_data.shape
    
    # Create mask for hand depth range
    hand_mask = np.zeros((h, w), dtype=np.uint8)
    hand_mask[(depth_data >= HAND_DEPTH_MIN) & (depth_data <= HAND_DEPTH_MAX)] = 255
    
    # Morphological operations to clean up noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    hand_mask = cv2.morphologyEx(hand_mask, cv2.MORPH_CLOSE, kernel)
    hand_mask = cv2.morphologyEx(hand_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(hand_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return hand_mask, None, False
    
    # Find largest contour within size constraints
    valid_contours = [c for c in contours 
                     if MIN_HAND_AREA < cv2.contourArea(c) < MAX_HAND_AREA]
    
    if not valid_contours:
        return hand_mask, None, False
    
    # Get largest valid contour
    largest_contour = max(valid_contours, key=cv2.contourArea)
    
    # Get bounding box
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Expand bounding box slightly for better coverage
    padding = 20
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(depth_data.shape[1] - x, w + 2 * padding)
    h = min(depth_data.shape[0] - y, h + 2 * padding)
    
    return hand_mask, (x, y, w, h), True


def crop_depth_to_hand(depth_frame, hand_bbox):
    """
    Crop the depth frame to the hand region and process to 5x5.
    
    Args:
        depth_frame: Raw depth frame
        hand_bbox: Bounding box (x, y, w, h)
        
    Returns:
        5x5 depth array focused on hand region
    """
    if hand_bbox is None:
        # No hand detected, use full frame
        return process_depth_frame(depth_frame)
    
    x, y, w, h = hand_bbox
    depth_data = depth_frame.getFrame()
    
    # Crop to hand region
    hand_region = depth_data[y:y+h, x:x+w]
    
    # Clip to hand depth range
    hand_clipped = np.clip(hand_region, HAND_DEPTH_MIN, HAND_DEPTH_MAX)
    
    # Normalize to 0-255
    depth_range = HAND_DEPTH_MAX - HAND_DEPTH_MIN
    hand_normalized = ((hand_clipped - HAND_DEPTH_MIN) / depth_range * 255).astype(np.uint8)
    
    # Downscale to 5x5
    hand_5x5 = cv2.resize(hand_normalized, (5, 5), interpolation=cv2.INTER_AREA)
    
    return hand_5x5


# ============================================================================
# UDP Networking
# ============================================================================

class UDPSender:
    """
    Handles UDP transmission of 5x5 depth arrays.
    """
    
    def __init__(self, target_ip, target_port):
        """
        Initialize UDP sender.
        
        Args:
            target_ip: IP address of Raspberry Pi Pico
            target_port: Port number on Pico
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.enabled = UDP_ENABLED
        self.packet_count = 0
        self.last_send_time = 0
        
        print(f"UDP Sender initialized: {target_ip}:{target_port}")
    
    def send_depth_array(self, depth_5x5):
        """
        Send 5x5 depth array via UDP.
        
        Packet format:
        - Header: 4 bytes "DPTH"
        - Packet ID: 4 bytes (uint32)
        - Timestamp: 8 bytes (double)
        - Data: 25 bytes (5x5 uint8 array, row-major order)
        Total: 41 bytes
        
        Args:
            depth_5x5: 5x5 numpy array of uint8 depth values
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Create packet
            header = b"DPTH"
            packet_id = self.packet_count
            timestamp = time.time()
            
            # Flatten 5x5 array to 25 bytes (row-major order)
            data = depth_5x5.flatten().tobytes()
            
            # Pack into binary format
            packet = header + struct.pack("<If", packet_id, timestamp) + data
            
            # Send packet
            self.socket.sendto(packet, (self.target_ip, self.target_port))
            
            self.packet_count += 1
            self.last_send_time = time.time()
            
            return True
            
        except Exception as e:
            print(f"UDP send error: {e}")
            return False
    
    def toggle(self):
        """Toggle UDP sending on/off."""
        self.enabled = not self.enabled
        status = "ENABLED" if self.enabled else "DISABLED"
        print(f"UDP sending {status}")
        return self.enabled
    
    def close(self):
        """Close the UDP socket."""
        self.socket.close()


# ============================================================================
# Visualization
# ============================================================================

def draw_hand_detection(image, hand_bbox, hand_detected):
    """
    Draw hand detection visualization on image.
    """
    if hand_detected and hand_bbox is not None:
        x, y, w, h = hand_bbox
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(image, "HAND DETECTED", (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        cv2.putText(image, "NO HAND DETECTED", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    return image


def draw_5x5_grid(image, depth_5x5, smoothed_5x5, position=(20, 100)):
    """
    Draw both raw and smoothed 5x5 grids side by side.
    """
    x_start, y_start = position
    cell_size = 50
    
    # Draw raw values
    cv2.putText(image, "Raw", (x_start, y_start - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    for i in range(5):
        for j in range(5):
            x = x_start + j * cell_size
            y = y_start + i * cell_size
            
            value = depth_5x5[i, j]
            color = (100, 100, 100)
            
            cv2.rectangle(image, (x, y), (x + cell_size, y + cell_size), color, 1)
            cv2.putText(image, str(value), (x + 10, y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Draw smoothed values
    x_smooth = x_start + 6 * cell_size
    cv2.putText(image, "Smoothed", (x_smooth, y_start - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    for i in range(5):
        for j in range(5):
            x = x_smooth + j * cell_size
            y = y_start + i * cell_size
            
            value = smoothed_5x5[i, j]
            color = (0, 150, 0)
            
            cv2.rectangle(image, (x, y), (x + cell_size, y + cell_size), color, 1)
            cv2.putText(image, str(value), (x + 10, y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return image


def draw_status_info(image, udp_sender, frame_count, hand_detected):
    """
    Draw status information on image.
    """
    h, w = image.shape[:2]
    
    # Frame counter
    cv2.putText(image, f"Frame: {frame_count}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # UDP status
    udp_status = "ON" if udp_sender.enabled else "OFF"
    udp_color = (0, 255, 0) if udp_sender.enabled else (0, 0, 255)
    cv2.putText(image, f"UDP: {udp_status} | Packets: {udp_sender.packet_count}", 
               (10, h - 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, udp_color, 2)
    
    # Target info
    cv2.putText(image, f"Target: {udp_sender.target_ip}:{udp_sender.target_port}", 
               (10, h - 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Instructions
    cv2.putText(image, "Press 'q' to quit | 's' to toggle UDP", 
               (10, h - 5),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return image


# ============================================================================
# Pipeline Creation
# ============================================================================

def create_pipeline():
    """Create DepthAI pipeline with RGB and depth outputs."""
    pipeline = dai.Pipeline()
    
    # RGB camera
    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(640, 400)
    cam_rgb.setInterleaved(False)
    cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
    
    # Mono cameras
    mono_left = pipeline.create(dai.node.MonoCamera)
    mono_right = pipeline.create(dai.node.MonoCamera)
    
    mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
    
    mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
    
    # Stereo depth
    stereo = pipeline.create(dai.node.StereoDepth)
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
    stereo.setLeftRightCheck(True)
    
    mono_left.out.link(stereo.left)
    mono_right.out.link(stereo.right)
    
    # Outputs
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)
    
    xout_depth = pipeline.create(dai.node.XLinkOut)
    xout_depth.setStreamName("depth")
    stereo.depth.link(xout_depth.input)
    
    return pipeline


# ============================================================================
# Main Loop
# ============================================================================

def main():
    """Main application loop."""
    print("=" * 70)
    print("OAK-D Lite Hand Tracking with UDP Transmission")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Pico IP: {PICO_IP}")
    print(f"  Pico Port: {PICO_PORT}")
    print(f"  Hand Depth Range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
    print(f"  Smoothing Window: {SMOOTHING_WINDOW} frames")
    print(f"\nInitializing device...")
    
    try:
        # Create pipeline and device
        pipeline = create_pipeline()
        device = dai.Device(pipeline)
        
        print("✓ Device initialized!")
        
        # Initialize UDP sender
        udp_sender = UDPSender(PICO_IP, PICO_PORT)
        
        # Initialize smoothing filter
        smoother = RollingAverageFilter(window_size=SMOOTHING_WINDOW)
        
        # Get queues
        rgb_queue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        # Create window
        cv2.namedWindow("Hand Tracking + UDP", cv2.WINDOW_NORMAL)
        
        print("\n✓ Ready! Wave your hand in front of the camera.")
        print("  Press 's' to toggle UDP sending")
        print("  Press 'q' to quit\n")
        
        frame_count = 0
        
        while True:
            # Get frames
            rgb_frame_data = rgb_queue.get()
            depth_frame_data = depth_queue.get()
            
            if rgb_frame_data is None or depth_frame_data is None:
                continue
            
            frame_count += 1
            
            # Get RGB frame
            rgb_frame = rgb_frame_data.getCvFrame()
            
            # Detect hand
            hand_mask, hand_bbox, hand_detected = detect_hand_region(depth_frame_data)
            
            # Crop depth to hand region
            if hand_detected:
                depth_5x5_raw = crop_depth_to_hand(depth_frame_data, hand_bbox)
            else:
                depth_5x5_raw = process_depth_frame(depth_frame_data)
            
            # Apply smoothing
            depth_5x5_smoothed = smoother.update(depth_5x5_raw)
            
            # Send via UDP (only if hand detected)
            if hand_detected and udp_sender.enabled:
                udp_sender.send_depth_array(depth_5x5_smoothed)
            
            # Visualize
            display = rgb_frame.copy()
            display = draw_hand_detection(display, hand_bbox, hand_detected)
            display = draw_5x5_grid(display, depth_5x5_raw, depth_5x5_smoothed)
            display = draw_status_info(display, udp_sender, frame_count, hand_detected)
            
            cv2.imshow("Hand Tracking + UDP", display)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                udp_sender.toggle()
    
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
    
    except RuntimeError as e:
        print(f"\n✗ Error: Failed to initialize device: {e}")
        print("\nTroubleshooting:")
        print("1. Check that OAK-D Lite is connected via USB")
        print("2. Try a different USB port")
        print("3. Ensure no other application is using the device")
        return 1
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if 'udp_sender' in locals():
            udp_sender.close()
        cv2.destroyAllWindows()
        print(f"\nTotal frames: {frame_count}")
        print(f"Total packets sent: {udp_sender.packet_count if 'udp_sender' in locals() else 0}")
        print("Exiting.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
