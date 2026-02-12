# OAK-D Lite Stereo Workflow

A complete, production-ready workflow for calibrating and developing with the OAK-D Lite stereo camera on Windows. This project provides everything you need to get accurate depth data from your OAK-D Lite device, including a comprehensive calibration guide, depth capture scripts, and example code.

## Features

- **Complete Calibration Workflow**: Step-by-step guide for calibrating OAK-D Lite stereo cameras with EEPROM flashing
- **Real-time Depth Capture**: Production-ready script that outputs continuously updating 5x5 downscaled depth arrays
- **🆕 Hand Tracking**: Automatically detects and crops to hand region, ignoring background noise
- **🆕 Data Smoothing**: Rolling average filter eliminates flickering for stable output
- **🆕 UDP Networking**: Send depth data to Raspberry Pi Pico over WiFi automatically
- **🆕 Visual Depth Viewer**: See RGB camera feed with colorized depth map in real-time
- **Example Scripts**: Educational examples demonstrating basic depth capture and environment verification
- **Tested Package Versions**: Specific versions to avoid numpy 2.0 and OpenCV compatibility issues
- **Windows PowerShell Compatible**: All commands work seamlessly in PowerShell
- **Comprehensive Testing**: Unit tests and property-based tests for correctness verification
- **Detailed Documentation**: Troubleshooting guides and API reference

## Prerequisites

- **Python 3.11** (not 3.13 or other versions - required for package compatibility)
- **OAK-D Lite** stereo camera device from Luxonis
- **Windows** operating system with PowerShell
- **USB 3.0** port (recommended for best performance)
- **Git** for cloning repositories

## Installation

### 1. Create Virtual Environment

```powershell
# Create Python 3.11 virtual environment
python -m venv oak_env

# Activate virtual environment (PowerShell)
.\oak_env\Scripts\Activate.ps1
```

**Note**: If you encounter execution policy errors, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install Dependencies

```powershell
# Install required packages with exact versions
pip install -r requirements.txt
```

The `requirements.txt` includes:
- `opencv-contrib-python==4.7.0.72` - Last version before numpy 2.0 issues
- `numpy==1.24.4` - Last version before 2.0 breaking changes
- `depthai` - Latest stable for Python 3.11
- Testing libraries (pytest, hypothesis)

### 3. Verify Installation

```powershell
# Run environment verification script
python example_verify_environment.py
```

This script checks:
- Python version (must be 3.11)
- Package versions and compatibility
- ArUco dictionary support
- Overall environment status

## Calibration

Before capturing depth data, you must calibrate your OAK-D Lite device. This is a one-time process that stores calibration data in the device's EEPROM.

### Quick Calibration Steps

1. **Print Charuco Board**: Print a 9x6 Charuco board with 2.5cm squares (see [Calibration Guide](docs/CALIBRATION_GUIDE.md) for details)
2. **Clone DepthAI Repository**:
   ```powershell
   git clone https://github.com/luxonis/depthai.git
   cd depthai
   git submodule update --init --recursive
   ```
3. **Run Calibration**:
   ```powershell
   cd calibration
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```
4. **Follow On-Screen Instructions**: Capture 15-20 images at different positions and angles
5. **Flash to EEPROM**: When prompted, flash calibration data to device
6. **Verify**: Check that baseline distance matches expected value (~7.5cm for OAK-D Lite)

### Detailed Calibration Guide

For complete calibration instructions, troubleshooting, and best practices, see the [**Calibration Guide**](docs/CALIBRATION_GUIDE.md).

The guide covers:
- Detailed environment setup
- Charuco board specifications and printing
- Step-by-step calibration process
- EEPROM flashing and verification
- Common issues and solutions
- Calibration quality assessment

## Project Structure

```
oak-d-lite-stereo-workflow/
├── src/                          # Source code
│   ├── depth_processor.py        # Depth processing functions (clip, normalize, downscale)
│   ├── pipeline_builder.py       # DepthAI pipeline creation
│   └── __init__.py               # Package initialization
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   │   ├── test_pipeline.py      # Pipeline construction tests
│   │   ├── test_processing.py    # Depth processing tests
│   │   └── test_edge_cases.py    # Edge case tests
│   ├── property/                 # Property-based tests
│   │   ├── test_clipping_properties.py
│   │   ├── test_normalization_properties.py
│   │   ├── test_downscaling_properties.py
│   │   └── test_output_properties.py
│   └── integration/              # Integration tests (require hardware)
├── docs/                         # Documentation
│   └── CALIBRATION_GUIDE.md      # Detailed calibration guide
├── hand_tracking_udp.py          # 🆕 Hand tracking + smoothing + UDP (for Pico)
├── udp_receiver_test.py          # 🆕 Test UDP reception locally
├── depth_viewer_visual.py        # 🆕 Visual depth viewer (3 windows)
├── depth_capture_5x5.py          # Main depth capture script (5x5 output)
├── example_basic_depth.py        # Educational example (basic depth capture)
├── example_verify_environment.py # Environment verification script
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Test configuration
├── HAND_TRACKING_SETUP.md        # 🆕 Hand tracking setup guide
├── QUICK_REFERENCE.md            # 🆕 Quick reference card
└── README.md                     # This file
```

## Available Scripts

| Script | Purpose | Best For |
|--------|---------|----------|
| **hand_tracking_udp.py** 🆕 | Hand detection + smoothing + UDP | Pico integration, production use |
| **depth_viewer_visual.py** 🆕 | Visual depth viewer (3 windows) | Understanding depth data, demos |
| **udp_receiver_test.py** 🆕 | Test UDP reception | Testing before Pico connection |
| **depth_capture_5x5.py** | Console 5x5 output | Simple depth monitoring |
| **example_basic_depth.py** | Educational example | Learning the basics |
| **example_verify_environment.py** | Environment check | Setup verification |

## Usage

### 🆕 Hand Tracking with UDP (Recommended for Pico Integration)

**NEW!** Advanced script with hand detection, smoothing, and UDP transmission to Raspberry Pi Pico:

```powershell
python hand_tracking_udp.py
```

**Features:**
- ✅ **Hand Tracking**: Automatically detects and crops to your hand (ignores background)
- ✅ **Data Smoothing**: Rolling average filter eliminates flickering
- ✅ **UDP Networking**: Sends stable 5x5 depth data to Pico over WiFi
- Shows both raw and smoothed values side-by-side
- Toggle UDP on/off with 's' key

**Setup:** Edit `PICO_IP` and `PICO_PORT` in the script, then see [HAND_TRACKING_SETUP.md](HAND_TRACKING_SETUP.md) for complete guide.

**Test UDP locally first:**
```powershell
# Terminal 1
python udp_receiver_test.py

# Terminal 2  
python hand_tracking_udp.py
```

### Basic Depth Capture (5x5 Array)

The main depth capture script outputs a continuously updating 5x5 downscaled depth array:

```powershell
# Run the production depth capture script
python depth_capture_5x5.py
```

**Output Example**:
```
==================================================
OAK-D Lite Depth Capture - 5x5 Downscaled Output
==================================================
Frame: 142

Depth Array (5x5) - Values: 0 (far) to 255 (near):
--------------------------------------------------
  [ 45  47  48  46  44 ]
  [ 46  48 120 122  47 ]
  [ 47 121 255 123  48 ]
  [ 46  49 122 121  47 ]
  [ 45  47  48  46  44 ]
--------------------------------------------------

Press Ctrl+C to exit
```

**Understanding the Values**:
- Values range from 0 (far/5+ meters) to 255 (near/0 meters)
- Higher values = closer objects
- Lower values = farther objects
- Move your hand in front of the camera to see values change in real-time

### Visual Depth Viewer

See live RGB camera feed with colorized depth map:

```powershell
python depth_viewer_visual.py
```

**Shows 3 windows:**
- RGB Camera - Live color feed
- Depth Map - Colorized depth (blue=far, red=near)
- Combined View - Both feeds with 5x5 overlay

Perfect for visualizing depth data and understanding how the camera sees your hand!

### Educational Examples

#### Example 1: Basic Depth Capture (No Downscaling)

Learn the fundamentals of depth capture without downscaling:

```powershell
python example_basic_depth.py
```

This example:
- Shows raw depth values at the center point
- Displays frame statistics (min, max, average depth)
- Includes detailed comments explaining each step
- Ideal for understanding the depth pipeline

#### Example 2: Environment Verification

Verify your Python environment is correctly configured:

```powershell
python example_verify_environment.py
```

This script checks:
- Python version (must be 3.11)
- Package versions (opencv, numpy, depthai)
- ArUco dictionary compatibility
- Overall environment status

### Programmatic Usage

Use the depth processing functions in your own code:

```python
import depthai as dai
from src.depth_processor import process_depth_frame
from src.pipeline_builder import create_stereo_pipeline

# Create pipeline and device
pipeline = create_stereo_pipeline()
with dai.Device(pipeline) as device:
    depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
    
    while True:
        depth_frame = depth_queue.get()
        if depth_frame is not None:
            # Process frame to 5x5 array
            depth_5x5 = process_depth_frame(depth_frame)
            print(depth_5x5)
```

## Testing

The project includes comprehensive unit tests and property-based tests to verify correctness.

### Run All Tests

```powershell
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest --cov=src tests/
```

### Run Specific Test Suites

```powershell
# Run only unit tests
pytest tests/unit/

# Run only property-based tests
pytest tests/property/

# Run only integration tests (requires hardware)
pytest tests/integration/ -m hardware
```

### Test Categories

**Unit Tests** (`tests/unit/`):
- Pipeline construction and configuration
- Depth processing functions (clip, normalize, downscale)
- Edge cases (zero values, maximum values, mixed data)
- Error handling

**Property-Based Tests** (`tests/property/`):
- Depth clipping bounds (all values in [0, 5000])
- Normalization range and type (all values in [0, 255], dtype uint8)
- Downscaling dimensions (output shape exactly (5, 5))
- Output type verification (numpy.ndarray)

**Integration Tests** (`tests/integration/`):
- End-to-end depth capture workflow
- Device connection and initialization
- Real-time frame processing
- **Note**: Requires connected OAK-D Lite device

### Test Coverage

The test suite maintains >80% code coverage for all testable components. Run coverage report:

```powershell
pytest --cov=src --cov-report=html tests/
```

Open `htmlcov/index.html` to view detailed coverage report.

## Troubleshooting

### Common Issues and Solutions

#### "No module named 'cv2.aruco'"
**Problem**: ArUco module not available in OpenCV installation.

**Solution**:
- Ensure `opencv-contrib-python` is installed (not `opencv-python`)
- Reinstall with correct version:
  ```powershell
  pip uninstall opencv-python opencv-contrib-python
  pip install opencv-contrib-python==4.7.0.72
  ```

#### "numpy.multiarray error" or "_ARRAY_API error"
**Problem**: Incompatible numpy version (likely 2.0+).

**Solution**:
- Downgrade to numpy 1.24.4:
  ```powershell
  pip install numpy==1.24.4
  ```
- Reinstall opencv after numpy downgrade:
  ```powershell
  pip install --force-reinstall opencv-contrib-python==4.7.0.72
  ```

#### "Device not found" or "Failed to initialize device"
**Problem**: Cannot connect to OAK-D Lite device.

**Solution**:
1. Check USB connection (use USB 3.0 port if available)
2. Try a different USB cable or port
3. Verify device appears in Device Manager (Windows)
4. Ensure no other application is using the device
5. Try unplugging and replugging the device
6. Restart your computer if issues persist

#### "Calibration not persisting" or "Baseline verification fails"
**Problem**: Calibration data not stored correctly in EEPROM.

**Solution**:
1. Ensure EEPROM write completed successfully during calibration
2. Check device permissions
3. Verify calibration with:
   ```powershell
   python -c "import depthai as dai; device = dai.Device(); print(device.readCalibration())"
   ```
4. Reflash calibration if needed

#### ArUco markers not detected during calibration
**Problem**: Charuco board markers not recognized.

**Solution**:
1. Ensure good lighting (no glare or shadows)
2. Verify board is printed at correct scale (measure squares with ruler - should be 2.5cm)
3. Check ArUco dictionary matches (DICT_4X4_50)
4. Try different distances (30cm - 100cm from camera)
5. Ensure board is flat and not warped

### Additional Help

For more detailed troubleshooting, see:
- [Calibration Guide](docs/CALIBRATION_GUIDE.md) - Comprehensive calibration troubleshooting
- [DepthAI Documentation](https://docs.luxonis.com/) - Official Luxonis documentation
- [DepthAI GitHub Issues](https://github.com/luxonis/depthai/issues) - Community support

## Package Versions

This project uses specific package versions to avoid compatibility issues with numpy 2.0 and OpenCV:

| Package | Version | Reason |
|---------|---------|--------|
| **Python** | 3.11 | Required for package compatibility; 3.13 has limited support |
| **opencv-contrib-python** | 4.7.0.72 | Last version before numpy 2.0 compatibility issues |
| **numpy** | 1.24.4 | Last version before 2.0 breaking changes (_ARRAY_API) |
| **depthai** | Latest stable | Compatible with Python 3.11 and above packages |
| **hypothesis** | ≥6.0.0 | Property-based testing framework |
| **pytest** | ≥7.0.0 | Test runner |

### Why These Versions?

- **numpy 2.0+** introduces breaking changes with `_ARRAY_API` that cause compatibility issues
- **opencv-contrib-python 4.8+** requires numpy 2.0+, creating a dependency conflict
- **Python 3.13** has limited package support as of this project's creation
- These versions are tested and known to work together seamlessly

### Upgrading Packages

**Warning**: Upgrading to newer versions may introduce compatibility issues. If you must upgrade:

1. Test thoroughly in a separate virtual environment
2. Check for numpy 2.0 compatibility issues
3. Verify ArUco dictionary support still works
4. Run the full test suite to catch regressions

## Documentation

- [Calibration Guide](docs/CALIBRATION_GUIDE.md) - Detailed calibration instructions
- [Design Document](.kiro/specs/oak-d-lite-stereo-workflow/design.md) - Architecture and design decisions
- [Requirements](.kiro/specs/oak-d-lite-stereo-workflow/requirements.md) - Feature requirements

## License

This project is provided as-is for educational and development purposes.

## Attribution

- OAK-D Lite camera by [Luxonis](https://luxonis.com/)
- DepthAI library by [Luxonis](https://github.com/luxonis/depthai)
