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
from datetime import timedelta

try:
    import depthai as dai
except ImportError as e:
    print(f"Error: Failed to import depthai: {e}")
    sys.exit(1)

from src.performance_profiler import PerformanceProfiler
from src.calibration_manager import CalibrationManager
from src.config_persistence import ConfigPersistence
from src.optimized_renderer import OptimizedRenderer
from src.rolling_average import RollingAverageFilter
import src.hand_matrix as hand_matrix_lib
from src.hand_matrix import estimate_hand_depth, ExponentialSmoother


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

SMOOTHING_WINDOW = getattr(app_config, "SMOOTHING_WINDOW", 5)
TARGET_FPS = getattr(app_config, "TARGET_FPS", 30)
TEMPORAL_FILTER_FRAMES = 4

# Stereo depth quality
FRAME_SIZE = (640, 480)  # RGB size; depth is aligned to the RGB camera
# Depth is sent at half size: the 5x5 matrix does not need more, and full-size
# RGB + depth exceeds what a USB 2 connection can carry at 30 FPS.
DEPTH_SIZE = (320, 240)
STEREO_SUBPIXEL = getattr(app_config, "STEREO_SUBPIXEL", True)
STEREO_EXTENDED_DISPARITY = getattr(app_config, "STEREO_EXTENDED_DISPARITY", False)

# 5x5 matrix construction
RELIEF_SPAN_MM = getattr(app_config, "RELIEF_SPAN_MM", 150)
HAND_BAND_MM = getattr(app_config, "HAND_BAND_MM", 120)
MIN_CELL_COVERAGE = getattr(app_config, "MIN_CELL_COVERAGE", 0.15)
BBOX_SMOOTHING_ALPHA = getattr(app_config, "BBOX_SMOOTHING_ALPHA", 0.5)
HAND_DEPTH_SMOOTHING_ALPHA = getattr(app_config, "HAND_DEPTH_SMOOTHING_ALPHA", 0.3)


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
        self.bbox_smoother = ExponentialSmoother(BBOX_SMOOTHING_ALPHA)
        
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
    
    def calibrate_depth_range(self, depth_frame, hand_bbox=None, num_samples=30,
                              landmarks_px=None):
        """Auto-calibrate depth range.

        If a hand bbox is available, sample calibration from that ROI so the
        resulting range tracks the active hand depth. Otherwise, fallback to a
        center ROI.
        """
        global HAND_DEPTH_MIN, HAND_DEPTH_MAX
        
        depth_data = depth_frame.getFrame()
        h, w = depth_data.shape

        # Prefer depth at the landmarks: a bbox median mostly sees whatever is
        # behind the hand (between the fingers).
        landmark_depth = estimate_hand_depth(depth_data, landmarks_px) if landmarks_px else None
        if landmark_depth is not None:
            roi = np.array([landmark_depth])
        elif hand_bbox is not None:
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
        """Detect hand using MediaPipe on the RGB frame.

        Depth is aligned to the RGB camera at the same resolution, so landmark
        pixel coordinates index the depth frame directly.

        Returns:
            tuple: (bbox, landmarks_px, hand_detected, confidence, status)
                bbox is smoothed over frames; landmarks_px is a list of 21
                (x, y) pixel tuples in depth-frame coordinates.
        """
        h, w = rgb_frame.shape[:2]
        depth_h, depth_w = depth_frame.getHeight(), depth_frame.getWidth()
        scale_x, scale_y = depth_w / w, depth_h / h

        results = self.hands.process(cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB))

        if not results.multi_hand_landmarks:
            return self._no_hand()

        landmarks_px = []
        for lm in results.multi_hand_landmarks[0].landmark:
            px = int(np.clip(lm.x * w, 0, w - 1) * scale_x)
            py = int(np.clip(lm.y * h, 0, h - 1) * scale_y)
            landmarks_px.append((px, py))

        xs = [p[0] for p in landmarks_px]
        ys = [p[1] for p in landmarks_px]
        x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)

        # Add 10% padding to ensure full hand is enveloped
        pad_x = int((x_max - x_min) * 0.10)
        pad_y = int((y_max - y_min) * 0.10)
        raw_bbox = (
            max(0, x_min - pad_x),
            max(0, y_min - pad_y),
            min(depth_w - 1, x_max + pad_x),
            min(depth_h - 1, y_max + pad_y),
        )

        # MIN_HAND_AREA is in RGB pixels; the box is in depth pixels.
        rgb_area = (raw_bbox[2] - raw_bbox[0]) * (raw_bbox[3] - raw_bbox[1]) / (scale_x * scale_y)
        if rgb_area < MIN_HAND_AREA:
            return self._no_hand()

        # Smooth the box corners so the 5x5 grid does not jump every frame.
        x0, y0, x1, y1 = (int(round(v)) for v in self.bbox_smoother.update(raw_bbox))
        bbox = (x0, y0, max(1, x1 - x0), max(1, y1 - y0))

        self.detection_history.append(True)
        temporal_confidence = sum(self.detection_history) / len(self.detection_history)
        hand_detected = temporal_confidence >= 0.75
        if hand_detected:
            self.last_bbox = bbox

        # MediaPipe does not expose a per-frame score here; a detection is trusted.
        return bbox, landmarks_px, hand_detected, 1.0, "detected"

    def _no_hand(self):
        self.detection_history.append(False)
        self.bbox_smoother.reset()
        return None, None, False, 0.0, "no_detection"

    def close(self):
        """Release MediaPipe resources."""
        try:
            self.hands.close()
        except Exception:
            pass



# ============================================================================
# Depth Processing
# ============================================================================

def compute_hand_matrix(depth_data, bbox, landmarks_px, hand_depth):
    """Build the 5x5 matrix from hand pixels only. Returns (matrix_5x5, hand_mask)."""
    return hand_matrix_lib.compute_hand_matrix(
        depth_data, bbox, landmarks_px, hand_depth,
        HAND_BAND_MM, RELIEF_SPAN_MM, MIN_CELL_COVERAGE,
    )


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
        sx, sy = w / DEPTH_SIZE[0], h / DEPTH_SIZE[1]  # bbox is in depth pixels
        x, y, w_box, h_box = (int(hand_bbox[0] * sx), int(hand_bbox[1] * sy),
                              int(hand_bbox[2] * sx), int(hand_bbox[3] * sy))

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

def colorize_depth(depth_mm, near_mm, far_mm):
    """Colorize depth so near = red, far = blue, no-depth = black."""
    d = depth_mm.astype(np.float32)
    scaled = np.clip((far_mm - d) / max(1.0, far_mm - near_mm), 0, 1)
    colored = cv2.applyColorMap((scaled * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    colored[depth_mm == 0] = 0
    return colored


def create_depth_window(depth_frame, hand_bbox=None):
    """Window 2: Colorized depth map."""
    depth_data = depth_frame.getFrame()
    depth_colorized = colorize_depth(depth_data, 200, 2000)
    scale = FRAME_SIZE[0] / depth_colorized.shape[1]
    depth_colorized = cv2.resize(depth_colorized, FRAME_SIZE, interpolation=cv2.INTER_NEAREST)

    if hand_bbox is not None:
        x, y, bw, bh = (int(v * scale) for v in hand_bbox)
        cv2.rectangle(depth_colorized, (x, y), (x + bw, y + bh), (255, 255, 255), 2)

    h = depth_colorized.shape[0]
    cv2.putText(depth_colorized, "DEPTH MAP", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(depth_colorized, "Red=Near  Blue=Far  Black=No depth", (20, h - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return depth_colorized


# ============================================================================
# Window 3: Hand Region Zoom
# ============================================================================

def create_hand_zoom_window(depth_frame, hand_bbox, hand_mask, hand_depth,
                            status_text, calibrating=False):
    """Window 3: The hand pixels used for the matrix, with the 5x5 grid drawn."""
    if hand_bbox is None or hand_mask is None or hand_depth is None:
        placeholder = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.putText(placeholder, status_text, (30, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 100, 100), 2)
        if calibrating:
            cv2.putText(placeholder, "CALIBRATING", (20, 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        return placeholder

    depth_data = depth_frame.getFrame()
    x, y, bw, bh = hand_bbox
    region = depth_data[y:y + bh, x:x + bw]
    region_mask = hand_mask[y:y + bh, x:x + bw]

    half_span = RELIEF_SPAN_MM / 2.0
    colored = colorize_depth(region, hand_depth - half_span, hand_depth + half_span)
    colored[~region_mask] = 0

    zoomed = cv2.resize(colored, (400, 400), interpolation=cv2.INTER_NEAREST)
    for k in range(1, 5):
        cv2.line(zoomed, (k * 80, 0), (k * 80, 400), (90, 90, 90), 1)
        cv2.line(zoomed, (0, k * 80), (400, k * 80), (90, 90, 90), 1)

    cv2.putText(zoomed, "HAND PIXELS", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    if calibrating:
        cv2.putText(zoomed, "CALIBRATING", (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(zoomed, f"Hand at {hand_depth:.0f}mm", (20, 380),
               cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    return zoomed

# ============================================================================
# Window 4: 5x5 Matrix Display (Sprint 2 Enhanced)
# ============================================================================

def create_matrix_window_sprint2(depth_5x5_raw, depth_5x5_smoothed, udp_sender,
                                 detector, profiler, calibration_mgr, renderer,
                                 status_text=""):
    """Window 4: Enhanced matrix with performance stats and calibration info."""
    window_size = 600
    display = np.zeros((window_size, window_size, 3), dtype=np.uint8)
    display[:] = (30, 30, 30)
    
    # Title
    cv2.putText(display, "5x5 DEPTH MATRIX", (150, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(display, status_text, (50, 85),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    # Draw grid
    cell_size = 100
    start_x = 50
    start_y = 100
    
    for i in range(5):
        for j in range(5):
            x = start_x + j * cell_size
            y = start_y + i * cell_size
            
            value = int(depth_5x5_smoothed[i, j])
            
            if value == 0:
                cell_color = (45, 45, 45)  # no hand in this cell
            else:
                intensity = value / 255.0  # higher = closer
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

def configure_stereo(stereo):
    """Shared StereoDepth settings for accurate close-range hand depth."""
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.ACCURACY)
    stereo.setLeftRightCheck(True)
    # Subpixel gives ~8x finer depth steps; without it a hand at 1 m is only
    # resolved in ~35 mm steps, which is coarser than the hand's own relief.
    stereo.setSubpixel(STEREO_SUBPIXEL)
    # Extended disparity lets the hand come closer than ~35 cm (costs FPS).
    stereo.setExtendedDisparity(STEREO_EXTENDED_DISPARITY)
    # Align depth to the RGB camera so MediaPipe pixel coordinates line up.
    stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
    stereo.setOutputSize(*DEPTH_SIZE)

    if STEREO_SUBPIXEL:
        # 3 fractional bits keeps max disparity under the median filter's
        # limit (the preset's 5 bits silently disables the median filter).
        stereo.setSubpixelFractionalBits(3)
    cfg = stereo.initialConfig
    cfg.setMedianFilter(dai.StereoDepthConfig.MedianFilter.KERNEL_5x5)
    # Speckle/spatial/temporal post-filters are left off: on the OAK-D Lite
    # they dropped the pipeline to 3-9 FPS. Smoothing is done on the host.
    pp = cfg.postProcessing
    pp.speckleFilter.enable = False
    pp.spatialFilter.enable = False
    pp.temporalFilter.enable = False
    pp.thresholdFilter.minRange = 150
    pp.thresholdFilter.maxRange = 2500


class FrameSource:
    """Returns time-matched (rgb_frame, depth_frame) pairs."""

    def __init__(self, get_pair):
        self._get_pair = get_pair

    def get(self):
        return self._get_pair()


def create_pipeline():
    """Create DepthAI pipeline. Returns (pipeline, frame_source or None)."""
    pipeline = dai.Pipeline()
    width, height = FRAME_SIZE

    if hasattr(dai.node, "XLinkOut"):
        # depthai v2 API
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        cam_rgb.setPreviewSize(width, height)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)

        mono_left = pipeline.create(dai.node.MonoCamera)
        mono_right = pipeline.create(dai.node.MonoCamera)
        mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
        mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
        mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
        mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)

        stereo = pipeline.create(dai.node.StereoDepth)
        configure_stereo(stereo)
        mono_left.out.link(stereo.left)
        mono_right.out.link(stereo.right)

        xout_rgb = pipeline.create(dai.node.XLinkOut)
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)
        xout_depth = pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName("depth")
        stereo.depth.link(xout_depth.input)
        return pipeline, None

    # depthai v3 API
    cam_rgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    rgb_output = cam_rgb.requestOutput(FRAME_SIZE, fps=TARGET_FPS)
    mono_left = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    mono_right = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
    left_output = mono_left.requestOutput(FRAME_SIZE, type=dai.ImgFrame.Type.GRAY8, fps=TARGET_FPS)
    right_output = mono_right.requestOutput(FRAME_SIZE, type=dai.ImgFrame.Type.GRAY8, fps=TARGET_FPS)

    stereo = pipeline.create(dai.node.StereoDepth)
    configure_stereo(stereo)
    left_output.link(stereo.left)
    right_output.link(stereo.right)

    # Pair RGB and depth by timestamp so the hand box matches the depth frame.
    sync = pipeline.create(dai.node.Sync)
    sync.setSyncThreshold(timedelta(milliseconds=int(500 / TARGET_FPS)))
    rgb_output.link(sync.inputs["rgb"])
    stereo.depth.link(sync.inputs["depth"])
    sync_queue = sync.out.createOutputQueue(maxSize=4, blocking=False)

    def get_pair():
        group = sync_queue.get()
        return group["rgb"], group["depth"]

    return pipeline, FrameSource(get_pair)


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
        pipeline, frames = create_pipeline()
        if hasattr(dai.Device, "getOutputQueue"):
            device = dai.Device(pipeline)
            rgb_queue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
            frames = FrameSource(lambda: (rgb_queue.get(), depth_queue.get()))
        else:
            pipeline.start()
        
        print("[OK] Device initialized!")
        
        # Initialize components
        udp_sender = UDPSender(PICO_IP, PICO_PORT)
        smoother = RollingAverageFilter(window_size=SMOOTHING_WINDOW)
        hand_depth_smoother = ExponentialSmoother(HAND_DEPTH_SMOOTHING_ALPHA)
        empty_matrix = np.zeros((5, 5), dtype=np.uint8)
        sent_release = True  # an all-zero packet has been sent since the hand was lost
        last_status_kind = None
        detector = MediaPipeHandDetector(
            confidence_threshold=0.5
        )
        
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
            rgb_frame_data, depth_frame_data = frames.get()
            profiler.end_stage("frame_acquisition")
            
            if rgb_frame_data is None or depth_frame_data is None:
                continue
            
            frame_count += 1
            
            # Get RGB frame
            rgb_frame = rgb_frame_data.getCvFrame()
            
            # Hand detection
            profiler.start_stage("hand_detection")
            hand_bbox, landmarks_px, hand_detected, confidence, status = detector.detect_hand(rgb_frame, depth_frame_data)
            profiler.end_stage("hand_detection")

            # Handle auto-calibration after detection so we can sample hand ROI.
            if detector.calibrating:
                calibration_done = detector.calibrate_depth_range(
                    depth_frame_data,
                    hand_bbox=hand_bbox,
                    landmarks_px=landmarks_px
                )
                if calibration_done:
                    calibration_mgr.depth_min = HAND_DEPTH_MIN
                    calibration_mgr.depth_max = HAND_DEPTH_MAX
                    calibration_mgr.last_adjustment_time = time.time()
                    smoother.reset()
            
            # Process depth: only pixels that belong to the hand are used.
            profiler.start_stage("depth_processing")
            depth_data = depth_frame_data.getFrame()
            hand_mask = None
            hand_depth = None
            hand_valid = False
            if not hand_detected:
                status_text = "NO HAND - show your hand to the camera"
            else:
                raw_hand_depth = estimate_hand_depth(depth_data, landmarks_px)
                if raw_hand_depth is None:
                    status_text = "NO DEPTH ON HAND - too close or poorly lit?"
                elif not (HAND_DEPTH_MIN <= raw_hand_depth <= HAND_DEPTH_MAX):
                    status_text = (f"HAND AT {raw_hand_depth:.0f}mm - outside "
                                   f"{HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm, press 'c'")
                else:
                    hand_depth = float(hand_depth_smoother.update(raw_hand_depth))
                    depth_5x5_raw, hand_mask = compute_hand_matrix(
                        depth_data, hand_bbox, landmarks_px, hand_depth
                    )
                    hand_valid = True
                    status_text = f"HAND AT {hand_depth:.0f}mm"
            profiler.end_stage("depth_processing")

            # Report why the matrix is empty (status category only, not every mm).
            if hand_valid:
                status_kind = "ok"
            elif "outside" in status_text:
                status_kind = "out_of_range"
            else:
                status_kind = status_text.split(" - ")[0]
            if status_kind != last_status_kind:
                print(f"[status] {status_text}")
                last_status_kind = status_kind

            # Smooth only real hand frames; start fresh whenever the hand is lost.
            if hand_valid:
                depth_5x5_smoothed = smoother.update(depth_5x5_raw)
            else:
                smoother.reset()
                hand_depth_smoother.reset()
                depth_5x5_raw = depth_5x5_smoothed = empty_matrix

            # Send via UDP (one all-zero packet when the hand is lost, so the
            # actuators release instead of holding the last shape).
            profiler.start_stage("udp_transmission")
            if udp_sender.enabled:
                if hand_valid:
                    udp_sender.send_depth_array(depth_5x5_smoothed)
                    sent_release = False
                elif not sent_release:
                    sent_release = udp_sender.send_depth_array(empty_matrix)
            profiler.end_stage("udp_transmission")
            
            # Rendering
            profiler.start_stage("rendering")
            window1 = create_rgb_window(rgb_frame, hand_bbox, hand_detected, confidence, frame_count)
            window2 = create_depth_window(depth_frame_data, hand_bbox if hand_detected else None)
            window3 = create_hand_zoom_window(
                depth_frame_data,
                hand_bbox,
                hand_mask,
                hand_depth,
                status_text,
                calibrating=detector.calibrating
            )
            window4 = create_matrix_window_sprint2(depth_5x5_raw, depth_5x5_smoothed,
                                                   udp_sender, detector, profiler,
                                                   calibration_mgr, renderer,
                                                   status_text=status_text)
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
                smoother.reset()
                print(f"\nReset to defaults: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            # Sprint 2: Calibration controls
            elif key == ord('+') or key == ord('='):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.increase_max()
                smoother.reset()
                print(f"Max depth increased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord('-') or key == ord('_'):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.decrease_max()
                smoother.reset()
                print(f"Max depth decreased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord('['):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.decrease_min()
                smoother.reset()
                print(f"Min depth decreased: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
            elif key == ord(']'):
                HAND_DEPTH_MIN, HAND_DEPTH_MAX = calibration_mgr.increase_min()
                smoother.reset()
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
        if 'pipeline' in locals() and not hasattr(dai.Device, "getOutputQueue"):
            if pipeline.isRunning():
                pipeline.stop()
        if 'device' in locals():
            device.close()
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
