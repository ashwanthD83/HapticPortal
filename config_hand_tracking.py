"""
Hand Tracking Configuration File

Edit these values to customize the hand tracking behavior.
Then import this file in hand_tracking_udp.py
"""

# ============================================================================
# Network Configuration
# ============================================================================

# Raspberry Pi Pico Network Settings
PICO_IP = "192.168.1.100"      # Change to your Pico's IP address
PICO_PORT = 5000               # Change to your Pico's listening port
UDP_ENABLED_AT_START = True    # Start with UDP enabled (True) or disabled (False)


# ============================================================================
# Hand Detection Configuration
# ============================================================================

# Depth Range (in millimeters)
# Objects within this range will be considered as potential hands
HAND_DEPTH_MIN = 200           # Minimum depth (20cm) - closer objects ignored
HAND_DEPTH_MAX = 1500          # Maximum depth (150cm) - farther objects ignored

# Hand Size Constraints (in pixels)
# Helps filter out noise and non-hand objects
MIN_HAND_AREA = 1000           # Minimum contour area to be considered a hand
MAX_HAND_AREA = 100000         # Maximum contour area (prevents detecting walls, etc.)


# ============================================================================
# Smoothing Configuration
# ============================================================================

# Rolling Average Window Size
# Higher values = smoother but slower response
# Lower values = faster response but more jitter
SMOOTHING_WINDOW = 5           # Number of frames to average (recommended: 3-10)


# ============================================================================
# Presets (Uncomment one to use)
# ============================================================================

# # PRESET 1: Close Range Tracking (0-50cm)
# # Use for: Close-up hand gestures, finger tracking
# HAND_DEPTH_MIN = 50
# HAND_DEPTH_MAX = 500
# SMOOTHING_WINDOW = 3  # Faster response for quick movements

# # PRESET 2: Medium Range Tracking (20-150cm) - DEFAULT
# # Use for: General hand tracking, most applications
# HAND_DEPTH_MIN = 200
# HAND_DEPTH_MAX = 1500
# SMOOTHING_WINDOW = 5  # Balanced smoothing

# # PRESET 3: Far Range Tracking (50-300cm)
# # Use for: Full body tracking, large movements
# HAND_DEPTH_MIN = 500
# HAND_DEPTH_MAX = 3000
# SMOOTHING_WINDOW = 7  # More smoothing for stability

# # PRESET 4: Ultra Smooth (for stable output)
# # Use for: When stability is more important than responsiveness
# SMOOTHING_WINDOW = 10

# # PRESET 5: Ultra Responsive (for quick movements)
# # Use for: Fast hand movements, gaming
# SMOOTHING_WINDOW = 2


# ============================================================================
# Advanced Configuration
# ============================================================================

# Morphological Operations (for noise reduction)
MORPH_KERNEL_SIZE = 5          # Size of morphological kernel (3, 5, or 7)

# Bounding Box Padding
BBOX_PADDING = 20              # Pixels to add around detected hand

# Display Configuration
SHOW_RAW_VALUES = True         # Show raw (unsmoothed) values
SHOW_SMOOTHED_VALUES = True    # Show smoothed values
CELL_SIZE = 50                 # Size of each cell in 5x5 grid display


# ============================================================================
# Network Advanced Configuration
# ============================================================================

# UDP Socket Configuration
UDP_BUFFER_SIZE = 1024         # UDP receive buffer size
UDP_TIMEOUT = None             # Socket timeout (None = blocking)

# Packet Configuration
INCLUDE_TIMESTAMP = True       # Include timestamp in packets
INCLUDE_PACKET_ID = True       # Include packet ID in packets


# ============================================================================
# Performance Configuration
# ============================================================================

# Frame Rate Limiting
TARGET_FPS = 30                # Target frames per second (0 = unlimited)
FRAME_DELAY = 1.0 / TARGET_FPS if TARGET_FPS > 0 else 0

# Queue Configuration
QUEUE_MAX_SIZE = 4             # Maximum frames in queue
QUEUE_BLOCKING = False         # Block when queue is full


# ============================================================================
# Debug Configuration
# ============================================================================

# Debug Output
DEBUG_MODE = False             # Enable debug output
VERBOSE_LOGGING = False        # Enable verbose logging
SHOW_FPS = True                # Show FPS counter

# Visualization
SHOW_HAND_MASK = False         # Show binary hand mask (debug window)
SHOW_CONTOURS = False          # Draw all contours (debug)


# ============================================================================
# Validation
# ============================================================================

def validate_config():
    """Validate configuration values."""
    errors = []
    
    # Validate depth range
    if HAND_DEPTH_MIN >= HAND_DEPTH_MAX:
        errors.append("HAND_DEPTH_MIN must be less than HAND_DEPTH_MAX")
    
    if HAND_DEPTH_MIN < 0:
        errors.append("HAND_DEPTH_MIN must be positive")
    
    # Validate area constraints
    if MIN_HAND_AREA >= MAX_HAND_AREA:
        errors.append("MIN_HAND_AREA must be less than MAX_HAND_AREA")
    
    # Validate smoothing window
    if SMOOTHING_WINDOW < 1:
        errors.append("SMOOTHING_WINDOW must be at least 1")
    
    if SMOOTHING_WINDOW > 20:
        errors.append("Warning: SMOOTHING_WINDOW > 20 may cause excessive lag")
    
    # Validate network config
    if not PICO_IP:
        errors.append("PICO_IP must be set")
    
    if PICO_PORT < 1 or PICO_PORT > 65535:
        errors.append("PICO_PORT must be between 1 and 65535")
    
    return errors


# ============================================================================
# Helper Functions
# ============================================================================

def print_config():
    """Print current configuration."""
    print("=" * 70)
    print("Hand Tracking Configuration")
    print("=" * 70)
    print(f"\nNetwork:")
    print(f"  Pico IP: {PICO_IP}")
    print(f"  Pico Port: {PICO_PORT}")
    print(f"  UDP Enabled: {UDP_ENABLED_AT_START}")
    print(f"\nHand Detection:")
    print(f"  Depth Range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
    print(f"  Area Range: {MIN_HAND_AREA}-{MAX_HAND_AREA} pixels")
    print(f"\nSmoothing:")
    print(f"  Window Size: {SMOOTHING_WINDOW} frames")
    print(f"\nPerformance:")
    print(f"  Target FPS: {TARGET_FPS}")
    print("=" * 70)


def get_config_dict():
    """Get configuration as dictionary."""
    return {
        'network': {
            'pico_ip': PICO_IP,
            'pico_port': PICO_PORT,
            'udp_enabled': UDP_ENABLED_AT_START,
        },
        'hand_detection': {
            'depth_min': HAND_DEPTH_MIN,
            'depth_max': HAND_DEPTH_MAX,
            'area_min': MIN_HAND_AREA,
            'area_max': MAX_HAND_AREA,
        },
        'smoothing': {
            'window_size': SMOOTHING_WINDOW,
        },
        'performance': {
            'target_fps': TARGET_FPS,
        }
    }


# ============================================================================
# Auto-validation on import
# ============================================================================

if __name__ == "__main__":
    # If run directly, print config and validate
    print_config()
    
    errors = validate_config()
    if errors:
        print("\n⚠️  Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration is valid!")
else:
    # If imported, validate silently
    errors = validate_config()
    if errors:
        print("⚠️  Configuration warnings:")
        for error in errors:
            print(f"  - {error}")
