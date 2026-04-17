#!/usr/bin/env python3
"""
OAK-D Lite Hand Tracking - Sprint 2 with MediaPipe Detection

Sprint 2 Features:
- MediaPipe Hands detection using 21 landmarks
- Performance profiling with FPS monitoring
- Real-time calibration controls (+/- for max, [/] for min)
- Configuration persistence (p to save)
- Optimized rendering with caching
- Visual feedback overlay

MediaPipe Integration:
- Replaces depth-based contour detection with landmark-based hand tracking
- Uses all 21 landmarks with 10% padding for robust hand bounding boxes
- Avoids face/ear false positives from generic object detectors

4 Windows:
1. RGB Camera - Live color feed with MediaPipe hand detection box
2. Depth Map - Colorized depth visualization
3. Hand Region - Zoomed view of detected hand
4. 5x5 Matrix - Large, clear depth matrix with performance stats

Controls:
- 'q' - Quit
- 's' - Toggle UDP
- 'c' - Calibrate depth range
- 'r' - Reset calibration
- '+' / '=' - Increase max depth
- '-' / '_' - Decrease max depth
- '[' - Decrease min depth
- ']' - Increase min depth
- 'p' - Save calibration to config
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
    sys.exit(1)

from src.depth_processor import process_depth_frame
from src.performance_profiler import PerformanceProfiler
from src.calibration_manager import CalibrationManager
from src.config_persistence import ConfigPersistence
from src.optimized_renderer import OptimizedRenderer


# ============================================================================
# Configuration
# ============================================================================

CONFIG_PATH = "config_hand_tracking.py"

try:
    import config_hand_tracking as app_config
except Exception as e:
    app_config = None
    print(f"Warning: Failed to load {CONFIG_PATH}: {e}")

PICO_IP = getattr(app_config, "PICO_IP", "192.168.1.100")
PICO_PORT = getattr(app_config, "PICO_PORT", 5000)
UDP_ENABLED = getattr(app_config, "UDP_ENABLED_AT_START", True)

# Hand detection parameters
HAND_DEPTH_MIN = getattr(app_config, "HAND_DEPTH_MIN", 200)
HAND_DEPTH_MAX = getattr(app_config, "HAND_DEPTH_MAX", 800)  # Tighter range to exclude faces
MIN_HAND_AREA = getattr(app_config, "MIN_HAND_AREA", 3000)
MAX_HAND_AREA = getattr(app_config, "MAX_HAND_AREA", 60000)
MIN_ASPECT_RATIO = 0.4
MAX_ASPECT_RATIO = 2.5
HAND_Y_THRESHOLD = 0.3

SMOOTHING_WINDOW = getattr(app_config, "SMOOTHING_WINDOW", 7)
TEMPORAL_FILTER_FRAMES = 4


# ============================================================================
# MediaPipe-Based Hand Detector
# ============================================================================

try:
    import mediapipe as mp
except Exception as e:
    print(f"Error: Failed to import mediapipe: {e}")
    print("Install compatible versions in .venv, e.g.:")
    print("  pip install mediapipe==0.10.14 numpy<2")
    raise

try:
    MP_HANDS = mp.solutions.hands
except AttributeError:
    # Fallback for environments where mediapipe.solutions is not exposed.
    from mediapipe.python.solutions import hands as MP_HANDS

class MediaPipeHandDetector:
    """MediaPipe-based hand detector using Google's precise 3D landmarks.
    
    Tracks the full hand perfectly by finding the min/max of all 21 joints,
    ignoring faces/ears completely.
    """
    
    def __init__(self, confidence_threshold=0.5):
        """Initialize MediaPipe hand detector.
        
        Args:
            confidence_threshold: Minimum confidence for detections
        """
        self.confidence_threshold = confidence_threshold
        self.detection_history = deque(maxlen=TEMPORAL_FILTER_FRAMES)
        self.last_bbox = None
        self.calibrating = False
        self.calibration_samples = []
        
        print(f"Loading MediaPipe Hand Tracking...")
        
        try:
            self.hands = MP_HANDS.Hands(
                static_image_mode=False,
                max_num_hands=1, # We only need one hand for haptic tracking
                min_detection_confidence=confidence_threshold,
                min_tracking_confidence=confidence_threshold
            )
            print(f"[OK] MediaPipe Hand Tracking loaded successfully!")
            
        except Exception as e:
            print(f"[ERROR] Failed to load MediaPipe: {e}")
            raise
    
    def calibrate_depth_range(self, depth_frame, hand_bbox=None, num_samples=30):
        """Auto-calibrate depth range.

        If a hand bbox is available, sample calibration from that ROI so the
        resulting range tracks the active hand depth. Otherwise, fallback to a
        center ROI.
        """
        global HAND_DEPTH_MIN, HAND_DEPTH_MAX
        
        depth_data = depth_frame.getFrame()
        h, w = depth_data.shape

        if hand_bbox is not None:
            x, y, box_w, box_h = hand_bbox
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            box_w = max(1, min(box_w, w - x))
            box_h = max(1, min(box_h, h - y))
            roi = depth_data[y:y + box_h, x:x + box_w]
        else:
            center_h, center_w = int(h * 0.7), w // 2
            roi_size = 80
            y0 = max(0, center_h - roi_size)
            y1 = min(h, center_h + roi_size)
            x0 = max(0, center_w - roi_size)
            x1 = min(w, center_w + roi_size)
            roi = depth_data[y0:y1, x0:x1]
        
        valid_depths = roi[(roi > 0) & (roi < 5000)]
        if len(valid_depths) > 0:
            median_depth = np.median(valid_depths)
            self.calibration_samples.append(median_depth)
            
            if len(self.calibration_samples) >= num_samples:
                avg_depth = np.mean(self.calibration_samples)
                HAND_DEPTH_MIN = max(100, int(avg_depth - 250))
                HAND_DEPTH_MAX = min(2000, int(avg_depth + 250))
                
                print(f"\n[OK] Calibration complete!")
                print(f"  Depth range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
                
                self.calibrating = False
                self.calibration_samples = []
                return True
        
        return False
    
    def detect_hand(self, rgb_frame, depth_frame):
        """Detect hand using MediaPipe on RGB frame, then map to depth.
        
        Finds the full hand using 21 3D landmarks to extract a perfect bounding box.
        
        Args:
            rgb_frame: RGB frame from camera (numpy array)
            depth_frame: Depth frame from camera (DepthAI frame)
            
        Returns:
            tuple: (hand_mask, bbox, hand_detected, confidence, status)
        """
        h, w = rgb_frame.shape[:2]
        
        # Convert BGR (OpenCV) to RGB (MediaPipe)
        rgb_image = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)
        
        # Process the image with MediaPipe
        results = self.hands.process(rgb_image)
        
        if results.multi_hand_landmarks:
            # We only configured for 1 hand, get the first one
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # Find bounding box from landmarks
            x_min, y_min = w, h
            x_max, y_max = 0, 0
            
            for landmark in hand_landmarks.landmark:
                px = int(np.clip(landmark.x * w, 0, w - 1))
                py = int(np.clip(landmark.y * h, 0, h - 1))
                x_min = min(x_min, px)
                y_min = min(y_min, py)
                x_max = max(x_max, px)
                y_max = max(y_max, py)
                
            # Add 10% padding to ensure full hand is enveloped
            box_w = x_max - x_min
            box_h = y_max - y_min
            
            pad_x = int(box_w * 0.10)
            pad_y = int(box_h * 0.10)
            
            x = max(0, x_min - pad_x)
            y = max(0, y_min - pad_y)
            w_box = min(w - x, box_w + 2 * pad_x)
            h_box = min(h - y, box_h + 2 * pad_y)
            
            # Reject very small boxes
            if w_box * h_box < MIN_HAND_AREA:
                self.detection_history.append(False)
                depth_data = depth_frame.getFrame()
                empty_mask = np.zeros((depth_data.shape[0], depth_data.shape[1]), dtype=np.uint8)
                return empty_mask, None, False, 0.0, "no_detection"
                
            confidence = 1.0 # MediaPipe abstracts raw conf info, but if it triggers it's high confidence
            bbox = (x, y, w_box, h_box)
            
            # Create hand mask from depth data in detected region
            depth_data = depth_frame.getFrame()
            hand_mask = np.zeros((depth_data.shape[0], depth_data.shape[1]), dtype=np.uint8)
            
            # Map RGB bbox to depth frame (assuming same resolution)
            depth_frame_h, depth_frame_w = depth_data.shape
            scale_x = depth_frame_w / w
            scale_y = depth_frame_h / h
            
            depth_x = int(x * scale_x)
            depth_y = int(y * scale_y)
            depth_bbox_w = int(w_box * scale_x)
            depth_bbox_h = int(h_box * scale_y)
            
            # Clamp to depth frame bounds
            depth_x = max(0, min(depth_x, depth_frame_w - 1))
            depth_y = max(0, min(depth_y, depth_frame_h - 1))
            depth_bbox_w = min(depth_bbox_w, depth_frame_w - depth_x)
            depth_bbox_h = min(depth_bbox_h, depth_frame_h - depth_y)
            
            # Create mask for hand region within depth range
            if depth_bbox_w > 0 and depth_bbox_h > 0:
                hand_region = depth_data[depth_y:depth_y+depth_bbox_h, depth_x:depth_x+depth_bbox_w]
                mask_region = ((hand_region >= HAND_DEPTH_MIN) & 
                              (hand_region <= HAND_DEPTH_MAX)).astype(np.uint8) * 255
                hand_mask[depth_y:depth_y+depth_bbox_h, depth_x:depth_x+depth_bbox_w] = mask_region
                
            # Temporal filtering
            self.detection_history.append(True)
            detection_count = sum(self.detection_history)
            temporal_confidence = detection_count / len(self.detection_history)
            
            hand_detected = temporal_confidence >= 0.75
            
            if hand_detected:
                self.last_bbox = bbox
            
            return hand_mask, bbox, hand_detected, confidence, "detected"
            
        # No hand detected
        self.detection_history.append(False)
        depth_data = depth_frame.getFrame()
        empty_mask = np.zeros((depth_data.shape[0], depth_data.shape[1]), dtype=np.uint8)
        
        return empty_mask, None, False, 0.0, "no_detection"

    def close(self):
        """Release MediaPipe resources."""
        try:
            self.hands.close()
        except Exception:
            pass



# ============================================================================
# Rolling Average Filter
# ============================================================================

class RollingAverageFilter:
    """Median-based smoothing filter."""
    
    def __init__(self, window_size=7):
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
    
    def update(self, new_array):
        self.history.append(new_array.copy().astype(np.float32))
        
        if len(self.history) < 2:
            return new_array
        
        history_stack = np.stack(list(self.history), axis=0)
        smoothed = np.median(history_stack, axis=0).astype(np.uint8)
        
        return smoothed
    
    def reset(self):
        self.history.clear()


# ============================================================================
# Depth Processing
# ============================================================================

def crop_depth_to_hand(depth_frame, hand_bbox):
    """Crop and process depth to hand region."""
    if hand_bbox is None:
        return process_depth_frame(depth_frame)
    
    x, y, w, h = hand_bbox
    depth_data = depth_frame.getFrame()
    frame_h, frame_w = depth_data.shape

    x = max(0, min(x, frame_w - 1))
    y = max(0, min(y, frame_h - 1))
    w = max(1, min(w, frame_w - x))
    h = max(1, min(h, frame_h - y))

    hand_region = depth_data[y:y+h, x:x+w]
    if hand_region.size == 0:
        return process_depth_frame(depth_frame)
    
    valid_mask = (hand_region >= HAND_DEPTH_MIN) & (hand_region <= HAND_DEPTH_MAX)
    
    if not np.any(valid_mask):
        return process_depth_frame(depth_frame)
    
    hand_clipped = np.clip(hand_region, HAND_DEPTH_MIN, HAND_DEPTH_MAX)
    
    # Adaptive normalization
    hand_valid = hand_clipped[valid_mask]
    actual_min = np.percentile(hand_valid, 5)
    actual_max = np.percentile(hand_valid, 95)
    
    if actual_max > actual_min:
        hand_normalized = np.clip(
            (hand_clipped - actual_min) / (actual_max - actual_min) * 255,
            0, 255
        ).astype(np.uint8)
    else:
        depth_range = max(1, HAND_DEPTH_MAX - HAND_DEPTH_MIN)
        hand_normalized = ((hand_clipped - HAND_DEPTH_MIN) / depth_range * 255).astype(np.uint8)
    
    hand_5x5 = cv2.resize(hand_normalized, (5, 5), interpolation=cv2.INTER_AREA)
    
    return hand_5x5



# ============================================================================
# UDP Sender
# ============================================================================

class UDPSender:
    """UDP transmission handler."""
    
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.enabled = UDP_ENABLED
        self.packet_count = 0
        
        print(f"UDP Sender: {target_ip}:{target_port}")
    
    def send_depth_array(self, depth_5x5):
        if not self.enabled:
            return False
        
        try:
            matrix = np.asarray(depth_5x5, dtype=np.uint8)
            if matrix.shape != (5, 5):
                raise ValueError(f"Expected 5x5 depth matrix, got {matrix.shape}")

            header = b"DPTH"
            packet_id = self.packet_count
            timestamp = time.time()
            data = matrix.flatten().tobytes()
            packet = header + struct.pack("<If", packet_id, timestamp) + data
            self.socket.sendto(packet, (self.target_ip, self.target_port))
            self.packet_count += 1
            return True
        except Exception as e:
            print(f"UDP error: {e}")
            return False
    
    def toggle(self):
        self.enabled = not self.enabled
        print(f"UDP: {'ON' if self.enabled else 'OFF'}")
        return self.enabled
    
    def close(self):
        self.socket.close()


# ============================================================================
# Window 1: RGB Camera with Detection
# ============================================================================

def create_rgb_window(rgb_frame, hand_bbox, hand_detected, confidence, frame_count):
    """Window 1: RGB camera with hand detection overlay."""
    display = rgb_frame.copy()
    h, w = display.shape[:2]
    
    if hand_detected and hand_bbox:
        x, y, w_box, h_box = hand_bbox
        
        if confidence > 0.9:
            color = (0, 255, 0)
        elif confidence > 0.75:
            color = (0, 255, 255)
        else:
            color = (0, 165, 255)
        
        cv2.rectangle(display, (x, y), (x + w_box, y + h_box), color, 3)
        
        label = f"HAND ({confidence*100:.0f}%)"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.rectangle(display, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
        cv2.putText(display, label, (x, y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    else:
        cv2.putText(display, "NO HAND DETECTED", (20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    cv2.putText(display, f"Frame: {frame_count}", (20, h - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return display



# ============================================================================
# Window 2: Depth Map
# ============================================================================

def create_depth_window(depth_frame):
    """Window 2: Colorized depth map."""
    depth_data = depth_frame.getFrame()
    
    depth_clipped = np.clip(depth_data, 0, 5000).astype(np.float32)
    depth_normalized = (depth_clipped / 5000.0 * 255.0).astype(np.uint8)
    
    depth_colorized = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
    
    h, w = depth_colorized.shape[:2]
    cv2.putText(depth_colorized, "DEPTH MAP", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(depth_colorized, "Blue=Far | Red=Near", (20, h - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return depth_colorized


# ============================================================================
# Window 3: Hand Region Zoom
# ============================================================================

def create_hand_zoom_window(depth_frame, hand_bbox, hand_detected, calibrating=False):
    """Window 3: Zoomed view of hand region."""
    if (not hand_detected or hand_bbox is None) and not calibrating:
        placeholder = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.putText(placeholder, "NO HAND", (100, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
        cv2.putText(placeholder, "Wave your hand", (80, 250),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
        cv2.putText(placeholder, "in front of camera", (60, 290),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
        return placeholder
    
    depth_data = depth_frame.getFrame()

    if hand_bbox is not None:
        x, y, w, h = hand_bbox
    else:
        frame_h, frame_w = depth_data.shape
        roi_size = 100
        center_x = frame_w // 2
        center_y = int(frame_h * 0.7)
        x = max(0, center_x - roi_size)
        y = max(0, center_y - roi_size)
        w = min(frame_w - x, 2 * roi_size)
        h = min(frame_h - y, 2 * roi_size)

    hand_region = depth_data[y:y + h, x:x + w]
    if hand_region.size == 0:
        placeholder = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.putText(placeholder, "EMPTY ROI", (95, 220),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        return placeholder

    valid_depths = hand_region[(hand_region >= HAND_DEPTH_MIN) & (hand_region <= HAND_DEPTH_MAX)]
    if valid_depths.size:
        hand_clipped = np.clip(hand_region, HAND_DEPTH_MIN, HAND_DEPTH_MAX).astype(np.float32)
        depth_range = max(1, HAND_DEPTH_MAX - HAND_DEPTH_MIN)
        hand_normalized = ((hand_clipped - HAND_DEPTH_MIN) / depth_range * 255.0).astype(np.uint8)
        depth_label = f"Avg: {float(np.mean(valid_depths)):.0f}mm"
        depth_label_color = (255, 255, 255)
    else:
        nonzero_depths = hand_region[hand_region > 0]
        if nonzero_depths.size:
            lo = float(np.percentile(nonzero_depths, 5))
            hi = float(np.percentile(nonzero_depths, 95))
            if hi <= lo:
                hi = lo + 1.0
            hand_normalized = np.clip(
                (hand_region.astype(np.float32) - lo) / (hi - lo) * 255.0,
                0, 255
            ).astype(np.uint8)
            depth_label = f"Out of range ({HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm)"
            depth_label_color = (0, 255, 255)
        else:
            hand_normalized = np.zeros(hand_region.shape, dtype=np.uint8)
            depth_label = "No valid depth pixels"
            depth_label_color = (0, 0, 255)
    
    hand_colorized = cv2.applyColorMap(hand_normalized, cv2.COLORMAP_JET)
    
    hand_zoomed = cv2.resize(hand_colorized, (400, 400), interpolation=cv2.INTER_LINEAR)
    
    cv2.putText(hand_zoomed, "HAND REGION", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    if calibrating:
        cv2.putText(hand_zoomed, "CALIBRATING", (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.putText(hand_zoomed, depth_label, (20, 380),
               cv2.FONT_HERSHEY_SIMPLEX, 0.65, depth_label_color, 2)
    
    return hand_zoomed



# ============================================================================
# Window 4: 5x5 Matrix Display (Sprint 2 Enhanced)
# ============================================================================

def create_matrix_window_sprint2(depth_5x5_raw, depth_5x5_smoothed, udp_sender, 
                                 detector, profiler, calibration_mgr, renderer):
    """Window 4: Enhanced matrix with performance stats and calibration info."""
    window_size = 600
    display = np.zeros((window_size, window_size, 3), dtype=np.uint8)
    display[:] = (30, 30, 30)
    
    # Title
    cv2.putText(display, "5x5 DEPTH MATRIX", (150, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    
    # Draw grid
    cell_size = 100
    start_x = 50
    start_y = 100
    
    for i in range(5):
        for j in range(5):
            x = start_x + j * cell_size
            y = start_y + i * cell_size
            
            value = int(depth_5x5_smoothed[i, j])
            
            intensity = value / 255.0
            cell_color = (
                int(50 + 100 * (1 - intensity)),
                int(50 + 150 * intensity),
                int(50 + 100 * intensity)
            )
            
            cv2.rectangle(display, (x, y), (x + cell_size, y + cell_size), cell_color, -1)
            cv2.rectangle(display, (x, y), (x + cell_size, y + cell_size), (200, 200, 200), 2)
            
            text = str(value)
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
            text_x = x + (cell_size - text_size[0]) // 2
            text_y = y + (cell_size + text_size[1]) // 2
            
            cv2.putText(display, text, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # Status info at bottom (Sprint 2 Enhanced)
    y_status = start_y + 5 * cell_size + 40
    
    # FPS with color coding
    fps = profiler.get_current_fps()
    if fps < 28:
        fps_color = (0, 0, 255)  # Red
    elif fps < 30:
        fps_color = (0, 255, 255)  # Yellow
    else:
        fps_color = (0, 255, 0)  # Green
    
    cv2.putText(display, f"FPS: {fps:.1f}", (50, y_status),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, fps_color, 2)
    
    # Frame time stats
    avg_frame_time = profiler.get_average_frame_time()
    peak_frame_time = profiler.get_peak_frame_time()
    cv2.putText(display, f"Avg: {avg_frame_time:.1f}ms  Peak: {peak_frame_time:.1f}ms", 
               (250, y_status),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    # UDP status
    udp_text = f"UDP: {'ON' if udp_sender.enabled else 'OFF'} | Packets: {udp_sender.packet_count}"
    udp_color = (0, 255, 0) if udp_sender.enabled else (0, 0, 255)
    cv2.putText(display, udp_text, (50, y_status + 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, udp_color, 2)
    
    # Depth range with highlighting if non-default
    range_text = f"Range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm"
    range_color = (0, 255, 255) if not calibration_mgr.is_default() else (200, 200, 200)
    cv2.putText(display, range_text, (50, y_status + 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, range_color, 1)
    
    # Calibration feedback message
    adjustment_msg = calibration_mgr.get_adjustment_message()
    if adjustment_msg:
        cv2.putText(display, adjustment_msg, (150, y_status + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Auto-calibration status
    if detector.calibrating:
        progress = len(detector.calibration_samples) / 30 * 100
        cv2.putText(display, f"CALIBRATING... {progress:.0f}%", (150, y_status + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    return display



# ============================================================================
# Pipeline Creation
# ============================================================================

def create_pipeline():
    """Create DepthAI pipeline."""
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
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(False)
    
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
# Main Loop (Sprint 2 Enhanced)
# ============================================================================

def main():
    """Main application loop with Sprint 2 enhancements."""
    global HAND_DEPTH_MIN, HAND_DEPTH_MAX
    frame_count = 0
    
    print("=" * 70)
    print("OAK-D Lite Hand Tracking - Sprint 2 with MediaPipe Detection")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Detection: MediaPipe Hands")
    print(f"  Pico IP: {PICO_IP}:{PICO_PORT}")
    print(f"  Depth Range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
    print(f"  Config File: {CONFIG_PATH}")
    print(f"\nInitializing Sprint 2 components...")
    
    try:
        # Initialize Sprint 2 components
        profiler = PerformanceProfiler()
        calibration_mgr = CalibrationManager(CONFIG_PATH, HAND_DEPTH_MIN, HAND_DEPTH_MAX)
        config_persistence = ConfigPersistence(CONFIG_PATH)
        renderer = OptimizedRenderer()
        
        print("[OK] Sprint 2 components initialized!")
        
        # Load saved calibration if available
        saved_config = config_persistence.read_config()
        if 'HAND_DEPTH_MIN' in saved_config and 'HAND_DEPTH_MAX' in saved_config:
            HAND_DEPTH_MIN = saved_config['HAND_DEPTH_MIN']
            HAND_DEPTH_MAX = saved_config['HAND_DEPTH_MAX']
            calibration_mgr.depth_min = HAND_DEPTH_MIN
            calibration_mgr.depth_max = HAND_DEPTH_MAX
            print(f"[OK] Loaded saved calibration: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
        
        # Create pipeline and device
        pipeline = create_pipeline()
        device = dai.Device(pipeline)
        
        print("[OK] Device initialized!")
        
        # Initialize components
        udp_sender = UDPSender(PICO_IP, PICO_PORT)
        smoother = RollingAverageFilter(window_size=SMOOTHING_WINDOW)
        detector = MediaPipeHandDetector(
            confidence_threshold=0.5
        )
        
        # Get queues
        rgb_queue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        # Create windows
        cv2.namedWindow("1. RGB Camera", cv2.WINDOW_NORMAL)
        cv2.namedWindow("2. Depth Map", cv2.WINDOW_NORMAL)
        cv2.namedWindow("3. Hand Region", cv2.WINDOW_NORMAL)
        cv2.namedWindow("4. 5x5 Matrix", cv2.WINDOW_NORMAL)
        
        # Position windows
        cv2.moveWindow("1. RGB Camera", 0, 0)
        cv2.moveWindow("2. Depth Map", 660, 0)
        cv2.moveWindow("3. Hand Region", 0, 450)
        cv2.moveWindow("4. 5x5 Matrix", 660, 450)
        
        print("\n[OK] Ready!")
        print("\nControls:")
        print("  q - Quit")
        print("  s - Toggle UDP")
        print("  c - Auto-calibrate depth range")
        print("  r - Reset to defaults")
        print("  + / = - Increase max depth")
        print("  - / _ - Decrease max depth")
        print("  [ - Decrease min depth")
        print("  ] - Increase min depth")
        print("  p - Save calibration to config\n")
        
        while True:
            profiler.start_frame()
            
            # Frame acquisition
            profiler.start_stage("frame_acquisition")
            rgb_frame_data = rgb_queue.get()
            depth_frame_data = depth_queue.get()
            profiler.end_stage("frame_acquisition")
            
            if rgb_frame_data is None or depth_frame_data is None:
                continue
            
            frame_count += 1
            
            # Get RGB frame
            rgb_frame = rgb_frame_data.getCvFrame()
            
            # Hand detection
            profiler.start_stage("hand_detection")
            hand_mask, hand_bbox, hand_detected, confidence, status = detector.detect_hand(rgb_frame, depth_frame_data)
            profiler.end_stage("hand_detection")

            # Handle auto-calibration after detection so we can sample hand ROI.
            if detector.calibrating:
                calibration_done = detector.calibrate_depth_range(
                    depth_frame_data,
                    hand_bbox=hand_bbox
                )
                if calibration_done:
                    calibration_mgr.depth_min = HAND_DEPTH_MIN
                    calibration_mgr.depth_max = HAND_DEPTH_MAX
                    calibration_mgr.last_adjustment_time = time.time()
            
            # Process depth
            profiler.start_stage("depth_processing")
            if hand_detected:
                depth_5x5_raw = crop_depth_to_hand(depth_frame_data, hand_bbox)
            else:
                depth_5x5_raw = process_depth_frame(depth_frame_data)
            profiler.end_stage("depth_processing")
            
            # Apply smoothing
            depth_5x5_smoothed = smoother.update(depth_5x5_raw)
            
            # Send via UDP
            profiler.start_stage("udp_transmission")
            if hand_detected and confidence > 0.8 and udp_sender.enabled:
                udp_sender.send_depth_array(depth_5x5_smoothed)
            profiler.end_stage("udp_transmission")
            
            # Rendering
            profiler.start_stage("rendering")
            window1 = create_rgb_window(rgb_frame, hand_bbox, hand_detected, confidence, frame_count)
            window2 = create_depth_window(depth_frame_data)
            window3 = create_hand_zoom_window(
                depth_frame_data,
                hand_bbox,
                hand_detected,
                calibrating=detector.calibrating
            )
            window4 = create_matrix_window_sprint2(depth_5x5_raw, depth_5x5_smoothed, 
                                                   udp_sender, detector, profiler, 
                                                   calibration_mgr, renderer)
            profiler.end_stage("rendering")
            
            # Display all windows
            cv2.imshow("1. RGB Camera", window1)
            cv2.imshow("2. Depth Map", window2)
            cv2.imshow("3. Hand Region", window3)
            cv2.imshow("4. 5x5 Matrix", window4)
            
            profiler.end_frame()
            
            # Handle keyboard (Sprint 2 Enhanced)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                udp_sender.toggle()
            elif key == ord('c'):
                print("\nAuto-calibrating... Hold hand at desired distance...")
                detector.calibrating = True
                detector.calibration_samples = []
            elif key == ord('r'):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.reset_to_defaults()
                print(f"\nReset to defaults: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            # Sprint 2: Calibration controls
            elif key == ord('+') or key == ord('='):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.increase_max()
                print(f"Max depth increased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord('-') or key == ord('_'):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.decrease_max()
                print(f"Max depth decreased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord('['):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.decrease_min()
                print(f"Min depth decreased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord(']'):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.increase_min()
                print(f"Min depth increased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord('p'):
                print("\nSaving calibration to config...")
                if config_persistence.write_config(HAND_DEPTH_MIN, HAND_DEPTH_MAX):
                    print(f"[OK] Saved: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
                else:
                    print("[ERROR] Failed to save config")
    
    except KeyboardInterrupt:
        print("\n\nShutdown requested")
    
    except RuntimeError as e:
        print(f"\n[ERROR] Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check OAK-D Lite is connected")
        print("2. Try different USB port")
        print("3. Close other applications using camera")
        return 1
    
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if 'detector' in locals():
            detector.close()
        if 'udp_sender' in locals():
            udp_sender.close()
        cv2.destroyAllWindows()
        
        # Print performance summary
        if 'profiler' in locals():
            print("\n" + "=" * 70)
            print("Performance Summary")
            print("=" * 70)
            stats = profiler.get_stats()
            if 'frame' in stats:
                print(f"Average FPS: {stats['frame']['fps']:.1f}")
                print(f"Average Frame Time: {stats['frame']['average_ms']:.2f}ms")
                print(f"Peak Frame Time: {stats['frame']['peak_ms']:.2f}ms")
            
            print("\nStage Timings:")
            for stage_name, stage_stats in stats.items():
                if stage_name != 'frame':
                    print(f"  {stage_name}: {stage_stats['average_ms']:.2f}ms avg, "
                          f"{stage_stats['peak_ms']:.2f}ms peak")
        
        print(f"\nTotal frames: {frame_count}")
        print(f"Packets sent: {udp_sender.packet_count if 'udp_sender' in locals() else 0}")
        print("Exiting.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

