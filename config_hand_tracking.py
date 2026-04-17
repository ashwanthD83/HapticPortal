"""
Hand tracking configuration shared by the PC app.

The Sprint 2 app reads these values at startup. Depth calibration can also be
saved back into this file from the running app.
"""

# ============================================================================
# Network Configuration
# ============================================================================

PICO_IP = "192.168.1.100"
PICO_PORT = 5000
UDP_ENABLED_AT_START = True


# ============================================================================
# Hand Detection Configuration
# ============================================================================

HAND_DEPTH_MIN = 1029
HAND_DEPTH_MAX = 1529

MIN_HAND_AREA = 1000
MAX_HAND_AREA = 100000


# ============================================================================
# Smoothing Configuration
# ============================================================================

SMOOTHING_WINDOW = 5


# ============================================================================
# Advanced Configuration
# ============================================================================

MORPH_KERNEL_SIZE = 5
BBOX_PADDING = 20

SHOW_RAW_VALUES = True
SHOW_SMOOTHED_VALUES = True
CELL_SIZE = 50


# ============================================================================
# Network Advanced Configuration
# ============================================================================

UDP_BUFFER_SIZE = 1024
UDP_TIMEOUT = None

INCLUDE_TIMESTAMP = True
INCLUDE_PACKET_ID = True


# ============================================================================
# Performance Configuration
# ============================================================================

TARGET_FPS = 30
FRAME_DELAY = 1.0 / TARGET_FPS if TARGET_FPS > 0 else 0

QUEUE_MAX_SIZE = 4
QUEUE_BLOCKING = False


# ============================================================================
# Debug Configuration
# ============================================================================

DEBUG_MODE = False
VERBOSE_LOGGING = False
SHOW_FPS = True

SHOW_HAND_MASK = False
SHOW_CONTOURS = False


# ============================================================================
# Validation
# ============================================================================

def validate_config():
    """Validate configuration values and return a list of issues."""
    errors = []

    if HAND_DEPTH_MIN >= HAND_DEPTH_MAX:
        errors.append("HAND_DEPTH_MIN must be less than HAND_DEPTH_MAX")

    if HAND_DEPTH_MIN < 0:
        errors.append("HAND_DEPTH_MIN must be positive")

    if MIN_HAND_AREA >= MAX_HAND_AREA:
        errors.append("MIN_HAND_AREA must be less than MAX_HAND_AREA")

    if SMOOTHING_WINDOW < 1:
        errors.append("SMOOTHING_WINDOW must be at least 1")

    if SMOOTHING_WINDOW > 20:
        errors.append("SMOOTHING_WINDOW > 20 may cause excessive lag")

    if not PICO_IP:
        errors.append("PICO_IP must be set")

    if PICO_PORT < 1 or PICO_PORT > 65535:
        errors.append("PICO_PORT must be between 1 and 65535")

    return errors


# ============================================================================
# Helper Functions
# ============================================================================

def print_config():
    """Print the current configuration."""
    print("=" * 70)
    print("Hand Tracking Configuration")
    print("=" * 70)
    print("\nNetwork:")
    print(f"  Pico IP: {PICO_IP}")
    print(f"  Pico Port: {PICO_PORT}")
    print(f"  UDP Enabled: {UDP_ENABLED_AT_START}")
    print("\nHand Detection:")
    print(f"  Depth Range: {HAND_DEPTH_MIN}-{HAND_DEPTH_MAX}mm")
    print(f"  Area Range: {MIN_HAND_AREA}-{MAX_HAND_AREA} pixels")
    print("\nSmoothing:")
    print(f"  Window Size: {SMOOTHING_WINDOW} frames")
    print("\nPerformance:")
    print(f"  Target FPS: {TARGET_FPS}")
    print("=" * 70)


def get_config_dict():
    """Return the config as a dictionary."""
    return {
        "network": {
            "pico_ip": PICO_IP,
            "pico_port": PICO_PORT,
            "udp_enabled": UDP_ENABLED_AT_START,
        },
        "hand_detection": {
            "depth_min": HAND_DEPTH_MIN,
            "depth_max": HAND_DEPTH_MAX,
            "area_min": MIN_HAND_AREA,
            "area_max": MAX_HAND_AREA,
        },
        "smoothing": {
            "window_size": SMOOTHING_WINDOW,
        },
        "performance": {
            "target_fps": TARGET_FPS,
        },
    }


errors = validate_config()

if __name__ == "__main__":
    print_config()
    if errors:
        print("\nConfiguration issues:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nConfiguration is valid.")
