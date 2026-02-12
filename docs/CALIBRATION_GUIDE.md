# OAK-D Lite Calibration Guide

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Charuco Board Preparation](#charuco-board-preparation)
3. [Calibration Execution](#calibration-execution)
4. [Troubleshooting](#troubleshooting)

---

## Environment Setup

This section guides you through setting up a Python 3.11 virtual environment with the exact package versions required for the OAK-D Lite stereo workflow. These specific versions are critical to avoid compatibility issues with numpy 2.0 and deprecated DepthAI API calls.

### Prerequisites

- **Python 3.11** (NOT Python 3.13 or other versions)
- **Windows PowerShell** (or PowerShell Core)
- **Git** for cloning the DepthAI repository
- **OAK-D Lite device** connected via USB

### Step 1: Verify Python Version

Before creating the virtual environment, verify you have Python 3.11 installed:

```powershell
python --version
```

Expected output: `Python 3.11.x`

If you don't have Python 3.11, download it from [python.org](https://www.python.org/downloads/) and install it. Make sure to check "Add Python to PATH" during installation.

### Step 2: Create Virtual Environment

Create a new Python 3.11 virtual environment in your project directory:

```powershell
python -m venv oak_env
```

This creates a new directory called `oak_env` containing an isolated Python environment.

### Step 3: Activate Virtual Environment

Activate the virtual environment using PowerShell:

```powershell
.\oak_env\Scripts\Activate.ps1
```

**Note**: If you encounter an execution policy error, run this command first:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again. You should see `(oak_env)` appear at the beginning of your command prompt, indicating the environment is active.

### Step 4: Upgrade pip

Ensure you have the latest version of pip:

```powershell
python -m pip install --upgrade pip
```

### Step 5: Install Required Packages

Install the required packages with exact versions to ensure compatibility:

```powershell
pip install opencv-contrib-python==4.7.0.72
pip install numpy==1.24.4
pip install depthai
```

**Why These Specific Versions?**

- `opencv-contrib-python==4.7.0.72`: Last version before numpy 2.0 compatibility issues. Includes ArUco marker detection required for calibration.
- `numpy==1.24.4`: Last version before 2.0 breaking changes that cause `_ARRAY_API` errors.
- `depthai`: Latest stable version compatible with Python 3.11. This is the core library for interfacing with OAK devices.

**Important**: Do NOT install `opencv-python` (without "contrib"). The calibration process requires `opencv-contrib-python` for ArUco marker detection.

### Step 6: Verify Package Installation

Verify all packages are installed correctly:

```powershell
pip list
```

You should see:
- `opencv-contrib-python` version 4.7.0.72
- `numpy` version 1.24.4
- `depthai` (latest version)

Test that the packages can be imported:

```powershell
python -c "import cv2; import numpy; import depthai; print('All packages imported successfully')"
```

Expected output: `All packages imported successfully`

### Step 7: Clone DepthAI Repository

Clone the official DepthAI repository, which contains the calibration scripts:

```powershell
git clone https://github.com/luxonis/depthai.git
cd depthai
```

### Step 8: Initialize Git Submodules

The DepthAI repository uses git submodules for some dependencies. Initialize them:

```powershell
git submodule update --init --recursive
```

This command downloads all required submodules. It may take a few minutes depending on your internet connection.

### Step 9: Verify Repository Structure

Verify the calibration directory exists:

```powershell
cd calibration
ls
```

You should see files including `calibrate.py`, which is the main calibration script.

### Environment Setup Complete

Your environment is now ready for OAK-D Lite calibration! The virtual environment includes:

- ✅ Python 3.11 with isolated package environment
- ✅ OpenCV with ArUco marker detection support
- ✅ NumPy 1.24.4 (avoiding 2.0 compatibility issues)
- ✅ DepthAI library for OAK device communication
- ✅ Official calibration scripts from DepthAI repository

### Deactivating the Environment

When you're done working, you can deactivate the virtual environment:

```powershell
deactivate
```

To reactivate it later, simply run:

```powershell
.\oak_env\Scripts\Activate.ps1
```

### Troubleshooting Environment Setup

**Issue: "python: command not found"**
- Ensure Python 3.11 is installed and added to PATH
- Try using `python3` instead of `python`
- Restart PowerShell after installing Python

**Issue: "pip install fails with network error"**
- Check your internet connection
- Try using a different network or VPN
- Use `pip install --proxy <proxy_url>` if behind a corporate proxy

**Issue: "Cannot import cv2.aruco"**
- Ensure you installed `opencv-contrib-python`, not `opencv-python`
- Uninstall both and reinstall: `pip uninstall opencv-python opencv-contrib-python && pip install opencv-contrib-python==4.7.0.72`

**Issue: "numpy version conflict"**
- Uninstall numpy and reinstall the correct version: `pip uninstall numpy && pip install numpy==1.24.4`
- Check for other packages that might have installed numpy 2.0 as a dependency

**Issue: "Git submodule update fails"**
- Ensure git is installed and accessible from PowerShell
- Check network connectivity
- Try cloning with HTTPS instead of SSH if you encounter authentication issues

---

**Next Steps**: Proceed to [Charuco Board Preparation](#charuco-board-preparation) to prepare your calibration target.

## Charuco Board Preparation

A Charuco board is a calibration pattern that combines a chessboard with ArUco markers. It's more robust than a traditional chessboard because the ArUco markers allow for partial board detection and precise corner localization. This section guides you through the specifications, printing, and verification of your calibration board.

### Charuco Board Specifications

For OAK-D Lite calibration, use the following exact specifications:

- **Board Dimensions**: 9x6 (9 columns × 6 rows of squares)
- **Square Size**: 2.5 cm (25 mm) per square
- **ArUco Dictionary**: DICT_4X4_50 (cv2.aruco.DICT_4X4_50)
- **Marker Size**: Automatically calculated by calibrate.py based on square size
- **Total Board Size**: 22.5 cm × 15 cm (9 squares × 2.5 cm, 6 squares × 2.5 cm)

**Why These Specifications?**

- **9x6 dimensions**: Provides sufficient corners for accurate calibration while fitting on standard A4/Letter paper
- **2.5 cm squares**: Large enough for clear detection at typical calibration distances (30-100 cm)
- **DICT_4X4_50**: A 4×4 bit ArUco dictionary with 50 unique markers, providing good detection reliability

### Generating the Charuco Board

The DepthAI calibration script can generate a Charuco board image for you. From the `depthai/calibration` directory:

```powershell
python calibrate.py -s 2.5 -brd CHARUCO_9x6 --create-board
```

This command creates a Charuco board image file with the correct specifications. The `--create-board` flag generates the board without starting calibration.

**Parameters Explained**:
- `-s 2.5`: Sets square size to 2.5 cm
- `-brd CHARUCO_9x6`: Specifies 9×6 Charuco board layout
- `--create-board`: Generates board image only (doesn't start calibration)

The generated image will be saved in the current directory as `charuco_board.png` or similar.

### Printing the Charuco Board

Follow these steps to print your calibration board correctly:

#### Step 1: Print Settings

- **Paper Size**: A4 or Letter (standard printer paper)
- **Orientation**: Landscape
- **Scale**: 100% (NO scaling - "Actual Size" or "Do not scale")
- **Color**: Black and white is sufficient
- **Quality**: Normal or high quality (avoid draft mode)

**Critical**: Ensure your printer is set to "Actual Size" or "100% scale". Any scaling will invalidate the 2.5 cm square size, leading to incorrect calibration.

#### Step 2: Print the Board

Print the generated `charuco_board.png` image using your preferred method:

**Option A: Using Windows Photo Viewer**
1. Open `charuco_board.png` in Windows Photo Viewer
2. Click Print (Ctrl+P)
3. Select your printer
4. Set "Fit picture to frame" to OFF
5. Print

**Option B: Using a Web Browser**
1. Open `charuco_board.png` in a web browser
2. Press Ctrl+P to print
3. Disable "Fit to page" or similar scaling options
4. Set scale to 100%
5. Print

**Option C: Using Python Script**
```powershell
# Print directly from Python (if you have a configured printer)
python -c "import cv2; img = cv2.imread('charuco_board.png'); cv2.imshow('Print Me', img); cv2.waitKey(0)"
```

#### Step 3: Mount the Board

For best calibration results, mount the printed board on a rigid, flat surface:

- **Recommended**: Glue or tape the printout to cardboard, foam board, or acrylic sheet
- **Alternative**: Use a clipboard to hold the board flat
- **Avoid**: Holding the board by hand (causes warping and movement)

A flat, rigid board ensures accurate corner detection and prevents calibration errors from board deformation.

### Verifying the Charuco Board

Before calibrating, verify your printed board is correct:

#### Verification Step 1: Measure Square Size

Use a ruler to measure the squares on your printed board:

1. Measure the width of one square: Should be exactly 2.5 cm (25 mm)
2. Measure multiple squares to verify consistency
3. Measure both horizontally and vertically

**If measurements are incorrect**:
- Check printer scaling settings (must be 100%)
- Regenerate the board image
- Try a different printer or print service

#### Verification Step 2: Check Board Dimensions

Count the squares:
- **Horizontally**: Should have 9 squares across
- **Vertically**: Should have 6 squares down
- **Total board size**: Approximately 22.5 cm × 15 cm

#### Verification Step 3: Inspect Print Quality

Examine the printed board for quality issues:

- ✅ **Sharp edges**: Square borders should be crisp and clear
- ✅ **High contrast**: Black squares should be solid black, white squares should be clean white
- ✅ **No smudging**: ArUco markers should be clearly defined
- ✅ **Flat surface**: No wrinkles, folds, or warping

**If quality is poor**:
- Reprint with higher quality settings
- Use fresh ink/toner
- Try a different printer
- Consider professional printing services

#### Verification Step 4: Test ArUco Detection

You can test if the ArUco markers are detectable before running full calibration:

```powershell
python -c "import cv2; import numpy as np; img = cv2.imread('charuco_board.png'); dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50); corners, ids, rejected = cv2.aruco.detectMarkers(img, dictionary); print(f'Detected {len(ids) if ids is not None else 0} markers')"
```

Expected output: `Detected 24 markers` (or similar, depending on board layout)

If no markers are detected, check print quality and regenerate the board.

### Charuco Board Best Practices

**Lighting Conditions**:
- Use even, diffuse lighting (avoid direct sunlight or harsh shadows)
- Avoid glare or reflections on the board surface
- Ensure the board is well-lit but not overexposed

**Board Positioning During Calibration**:
- Start at 30-50 cm from the camera
- Move the board to various distances (30 cm to 1 meter)
- Tilt the board at different angles (0° to 45°)
- Cover all areas of the camera's field of view
- Keep the board flat and stable during each capture

**Common Mistakes to Avoid**:
- ❌ Printing with scaling enabled (invalidates square size)
- ❌ Using a warped or bent board (causes calibration errors)
- ❌ Poor lighting (prevents marker detection)
- ❌ Moving the board during image capture (causes blur)
- ❌ Capturing images from only one distance or angle (poor calibration coverage)

### Alternative: Pre-printed Charuco Boards

If you don't have access to a quality printer, consider these alternatives:

1. **Professional Printing Services**: Upload `charuco_board.png` to a print shop and request printing at actual size on rigid material
2. **Online Calibration Board Vendors**: Some companies sell pre-printed calibration boards with guaranteed accuracy
3. **University/Makerspace Printers**: Often have high-quality printers available for use

Ensure any pre-printed board matches the exact specifications (9×6, 2.5 cm squares, DICT_4X4_50).

### Charuco Board Preparation Complete

Your calibration board is now ready! You should have:

- ✅ A printed 9×6 Charuco board with 2.5 cm squares
- ✅ Board mounted on a rigid, flat surface
- ✅ Verified square size measurements (2.5 cm)
- ✅ Confirmed ArUco marker detection
- ✅ Good print quality with sharp edges and high contrast

---

**Next Steps**: Proceed to [Calibration Execution](#calibration-execution) to calibrate your OAK-D Lite device.

## Calibration Execution

This section guides you through running the calibration process, capturing calibration images, flashing the calibration data to EEPROM, and verifying the results. The calibration process computes the intrinsic and extrinsic parameters of your OAK-D Lite's stereo cameras, which are essential for accurate depth perception.

### Prerequisites

Before starting calibration, ensure you have:

- ✅ Python 3.11 virtual environment activated (see [Environment Setup](#environment-setup))
- ✅ All required packages installed (opencv-contrib-python, numpy, depthai)
- ✅ DepthAI repository cloned with submodules initialized
- ✅ Printed and mounted 9×6 Charuco board with 2.5 cm squares (see [Charuco Board Preparation](#charuco-board-preparation))
- ✅ OAK-D Lite device connected via USB
- ✅ Good lighting conditions (even, diffuse lighting without glare)

### Step 1: Navigate to Calibration Directory

Ensure you're in the DepthAI calibration directory with your virtual environment activated:

```powershell
cd depthai\calibration
```

Verify you're in the correct directory:

```powershell
ls calibrate.py
```

You should see the `calibrate.py` file listed.

### Step 2: Run Calibration Command

Start the calibration process with the correct parameters for your 9×6 Charuco board with 2.5 cm squares:

```powershell
python calibrate.py -s 2.5 -brd CHARUCO_9x6
```

**Command Parameters Explained**:
- `calibrate.py`: The main calibration script from the DepthAI repository
- `-s 2.5`: Specifies the square size as 2.5 cm (25 mm)
- `-brd CHARUCO_9x6`: Specifies the board type as Charuco with 9 columns and 6 rows

**Important**: These parameters must match your printed board exactly. Using incorrect parameters will result in inaccurate calibration.

### Step 3: Calibration Interface Overview

When the calibration script starts, you'll see:

1. **Live camera feeds**: Left and right camera views displayed in windows
2. **Detected markers**: ArUco markers highlighted with green outlines
3. **Detected corners**: Charuco corners marked with colored dots
4. **Instructions**: On-screen text guiding you through the process
5. **Capture counter**: Number of image pairs captured so far

**What You Should See**:
- Both left and right camera feeds showing your Charuco board
- Green rectangles around detected ArUco markers
- Colored dots at detected Charuco corners
- Text indicating "Press SPACE to capture" or similar

**If markers are not detected**:
- Adjust lighting (avoid glare and shadows)
- Move the board closer or farther from the camera (try 40-60 cm)
- Ensure the board is flat and fully visible in both camera views
- Check that the board is printed at the correct scale (measure squares)

### Step 4: Image Capture Process

The calibration quality depends on capturing diverse, high-quality image pairs. Follow these best practices:

#### Capture Strategy

Capture at least **15-20 image pairs** covering:

1. **Various Distances**:
   - Close: 30-40 cm from camera
   - Medium: 50-70 cm from camera
   - Far: 80-100 cm from camera

2. **Various Angles**:
   - Straight on (0° tilt)
   - Tilted left/right (15-30°)
   - Tilted up/down (15-30°)
   - Rotated clockwise/counterclockwise (15-45°)

3. **Various Positions**:
   - Center of field of view
   - Left side of field of view
   - Right side of field of view
   - Top of field of view
   - Bottom of field of view
   - Corners of field of view

#### Capture Procedure

For each image pair:

1. **Position the board**: Hold or place the board in the desired position and angle
2. **Wait for detection**: Ensure ArUco markers and corners are detected (green outlines visible)
3. **Hold steady**: Keep the board completely still for 1-2 seconds
4. **Press SPACE**: Capture the image pair when the board is stable and well-detected
5. **Wait for confirmation**: Look for visual or text confirmation that the image was captured
6. **Move to next position**: Reposition the board for the next capture

**Tips for Successful Captures**:
- ✅ Keep the board flat and rigid (no bending or warping)
- ✅ Ensure the entire board is visible in both camera views
- ✅ Hold the board steady during capture (no motion blur)
- ✅ Capture from diverse positions and angles (good coverage)
- ✅ Wait for all markers to be detected before capturing
- ❌ Don't capture multiple images from the same position
- ❌ Don't move the board during capture
- ❌ Don't capture if markers are not detected or partially visible

#### Monitoring Capture Quality

As you capture images, the script may display:

- **Capture count**: "Captured 5/15 images" or similar
- **Detection quality**: Number of corners detected per image
- **Coverage indicators**: Visual feedback on field-of-view coverage

**Good calibration coverage** means:
- Images from all areas of the field of view
- Images from multiple distances (near, medium, far)
- Images from multiple angles (straight, tilted, rotated)
- At least 15-20 high-quality image pairs

### Step 5: Complete Calibration Computation

After capturing sufficient images (typically 15-20 pairs), the script will:

1. **Process images**: Compute stereo calibration parameters
2. **Display results**: Show calibration quality metrics
3. **Calculate reprojection error**: Display RMS (Root Mean Square) error

**Calibration Quality Metrics**:

- **RMS Error < 0.5 pixels**: Excellent calibration
- **RMS Error < 1.0 pixels**: Good calibration (acceptable for most applications)
- **RMS Error < 1.5 pixels**: Fair calibration (may work but consider recalibrating)
- **RMS Error > 1.5 pixels**: Poor calibration (recalibration recommended)

**Example Output**:
```
Calibration complete!
RMS reprojection error: 0.42 pixels
Baseline distance: 7.5 cm
```

**If RMS error is too high**:
- Recapture images with better coverage
- Ensure board is flat and measurements are correct
- Check lighting conditions
- Verify board is printed at correct scale

### Step 6: Flash Calibration to EEPROM

After successful calibration, the script will prompt you to flash the calibration data to the device's EEPROM (non-volatile memory). This stores the calibration permanently on the device.

**Flashing Process**:

1. **Prompt**: The script will ask "Flash calibration to EEPROM? (y/n)"
2. **Confirm**: Type `y` and press Enter to proceed
3. **Flashing**: The script writes calibration data to device EEPROM
4. **Verification**: The script reads back the data to verify successful write

**Example Output**:
```
Flash calibration to EEPROM? (y/n): y
Flashing calibration to device...
Calibration flashed successfully!
Verifying EEPROM data...
EEPROM verification passed.
```

**Important Notes**:
- Flashing to EEPROM is **permanent** (overwrites previous calibration)
- The device will use this calibration for all future depth computations
- You can recalibrate and reflash at any time if needed
- EEPROM data persists even when the device is powered off

**If flashing fails**:
- Check USB connection (try a different port or cable)
- Ensure no other applications are using the device
- Verify device permissions (may require administrator rights on Windows)
- Try restarting the device (unplug and replug USB)

### Step 7: Verify Baseline Distance

The baseline distance is the physical distance between the left and right camera sensors. Verifying this value ensures the calibration is physically accurate.

**Expected Baseline for OAK-D Lite**: Approximately **7.5 cm** (75 mm)

**Verification Steps**:

1. **Check calibration output**: Look for "Baseline distance" in the calibration results
2. **Compare to expected value**: Should be close to 7.5 cm (±0.5 cm tolerance)
3. **Physical measurement** (optional): Measure the distance between camera lenses with a ruler

**Example Output**:
```
Baseline distance: 7.5 cm
```

**Baseline Verification Results**:

- **7.0 - 8.0 cm**: ✅ Correct (within expected range for OAK-D Lite)
- **6.5 - 7.0 cm or 8.0 - 8.5 cm**: ⚠️ Acceptable but verify physical measurement
- **< 6.5 cm or > 8.5 cm**: ❌ Incorrect (recalibration recommended)

**If baseline is incorrect**:
- Verify square size parameter (-s 2.5) matches printed board
- Measure printed squares with a ruler to confirm 2.5 cm
- Check for board warping or bending during calibration
- Recalibrate with correct parameters and flat board

### Step 8: Test Calibrated Device

After flashing calibration to EEPROM, test that the device produces accurate depth data:

**Quick Test Script**:

```powershell
python -c "import depthai as dai; device = dai.Device(); calib = device.readCalibration(); print(f'Baseline: {calib.getBaselineDistance():.2f} cm')"
```

Expected output: `Baseline: 7.50 cm` (or similar)

This confirms the calibration is stored in EEPROM and can be read by the device.

**Visual Depth Test** (optional):

Run a simple depth visualization to verify depth accuracy:

```powershell
# Navigate back to depthai root directory
cd ..

# Run depth preview example
python examples/StereoDepth/depth_preview.py
```

This displays a live depth map. Test by:
- Moving your hand closer/farther from the camera
- Observing depth values change appropriately
- Checking that depth is consistent across the field of view

### Calibration Execution Complete

Your OAK-D Lite is now calibrated! You should have:

- ✅ Captured 15-20 high-quality calibration image pairs
- ✅ Achieved RMS reprojection error < 1.0 pixels
- ✅ Flashed calibration data to device EEPROM
- ✅ Verified baseline distance (~7.5 cm for OAK-D Lite)
- ✅ Confirmed calibration persists in EEPROM

The calibration data is now permanently stored on your device and will be used automatically for all depth computations.

### Recalibration

You can recalibrate your device at any time by repeating this process. Recalibration may be needed if:

- Device is dropped or physically damaged
- Depth accuracy degrades over time
- Device is used in significantly different environmental conditions
- Initial calibration quality was poor (high RMS error)

To recalibrate, simply run the calibration command again:

```powershell
python calibrate.py -s 2.5 -brd CHARUCO_9x6
```

The new calibration will overwrite the previous EEPROM data.

### Calibration Best Practices Summary

**For Best Results**:
- ✅ Use a flat, rigid Charuco board printed at correct scale
- ✅ Capture 15-20 diverse image pairs (various distances, angles, positions)
- ✅ Ensure good, even lighting without glare or shadows
- ✅ Keep board steady during each capture (no motion blur)
- ✅ Aim for RMS error < 1.0 pixels
- ✅ Verify baseline distance matches expected value (~7.5 cm)
- ✅ Test depth output after calibration

**Common Mistakes to Avoid**:
- ❌ Using incorrect square size parameter
- ❌ Capturing images from limited positions/angles (poor coverage)
- ❌ Moving board during capture (motion blur)
- ❌ Using warped or bent calibration board
- ❌ Poor lighting conditions (glare, shadows, low light)
- ❌ Accepting high RMS error without recalibrating

---

**Next Steps**: Proceed to [Troubleshooting](#troubleshooting) for solutions to common calibration issues.

## Troubleshooting

This section provides solutions to common issues encountered during OAK-D Lite calibration and depth capture. Issues are organized by category with step-by-step diagnostic and resolution procedures.

### ArUco Marker Detection Failures

**Symptom**: Calibration script does not detect ArUco markers on the Charuco board, or detection is intermittent.

**Visual Indicators**:
- No green rectangles around ArUco markers in camera feed
- Message: "No markers detected" or similar
- Charuco corners not highlighted
- Unable to capture calibration images

#### Solution 1: Check Lighting Conditions

Poor lighting is the most common cause of detection failures.

**Steps**:
1. **Assess current lighting**:
   - Look for glare or reflections on the board surface
   - Check for harsh shadows across the board
   - Verify the board is not in direct sunlight

2. **Improve lighting**:
   - Use diffuse, even lighting (overhead room lights work well)
   - Avoid direct sunlight or bright spotlights
   - Position the board to eliminate glare and reflections
   - If using a lamp, bounce light off a wall or ceiling for diffuse lighting

3. **Test detection**:
   - Move the board slightly to find optimal lighting angle
   - Observe if markers become detected with better lighting
   - Capture a test image when markers are consistently detected

**Expected Result**: Green rectangles appear around all ArUco markers in both camera feeds.

#### Solution 2: Verify Board Print Scale

Incorrect print scaling can prevent marker detection or cause calibration errors.

**Steps**:
1. **Measure square size**:
   - Use a ruler to measure one square on the printed board
   - Measure multiple squares to verify consistency
   - Expected measurement: Exactly 2.5 cm (25 mm) per square

2. **If measurements are incorrect**:
   - Check printer settings (must be "Actual Size" or "100% scale")
   - Disable "Fit to page" or "Scale to fit" options
   - Regenerate the board image: `python calibrate.py -s 2.5 -brd CHARUCO_9x6 --create-board`
   - Reprint with correct scaling settings

3. **Verify print quality**:
   - Check that ArUco markers have sharp, clear edges
   - Ensure high contrast (solid black on clean white)
   - Look for smudging or ink bleeding that could obscure markers

**Expected Result**: Squares measure exactly 2.5 cm, and markers are sharp and clear.

#### Solution 3: Adjust Camera Distance

Markers may not be detected if the board is too close or too far from the camera.

**Steps**:
1. **Start at optimal distance**:
   - Position the board 40-60 cm from the camera
   - Ensure the entire board is visible in both camera feeds
   - Check that the board fills approximately 50-70% of the frame

2. **Test different distances**:
   - If no detection at 40-60 cm, try 30-40 cm (closer)
   - If still no detection, try 60-80 cm (farther)
   - Observe detection quality at each distance

3. **Find the sweet spot**:
   - Detection should work across a range of distances (30-100 cm)
   - If detection only works at one specific distance, check board print quality

**Expected Result**: Markers are detected consistently across a range of distances (30-100 cm).

#### Solution 4: Verify ArUco Dictionary

The calibration script must use the correct ArUco dictionary matching the printed board.

**Steps**:
1. **Confirm dictionary in use**:
   - The default for CHARUCO_9x6 is DICT_4X4_50
   - This should match the board generated by `calibrate.py`

2. **Test dictionary compatibility**:
   ```powershell
   python -c "import cv2; dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50); print(f'Dictionary loaded: {dictionary.bytesList.shape[0]} markers')"
   ```
   - Expected output: `Dictionary loaded: 50 markers`

3. **If using a custom board**:
   - Ensure the board was generated with the same dictionary
   - Regenerate the board using the calibration script
   - Do not mix boards from different sources or dictionaries

**Expected Result**: Dictionary loads successfully and matches the printed board.

#### Solution 5: Check Board Flatness

A warped or bent board can prevent accurate marker detection.

**Steps**:
1. **Inspect board physically**:
   - Look for wrinkles, folds, or bending
   - Check if the board is mounted on a rigid surface
   - Verify the board lies completely flat

2. **Improve board rigidity**:
   - Mount the printout on cardboard, foam board, or acrylic
   - Use a clipboard to hold the board flat
   - Avoid holding the board by hand (causes warping)

3. **Test with flat board**:
   - Position the flat board in front of the camera
   - Verify markers are detected consistently
   - Capture calibration images with the rigid board

**Expected Result**: Board is completely flat and rigid, markers detected consistently.

### Camera Swap Issues

**Symptom**: Left and right cameras appear swapped, or depth map is inverted/incorrect.

**Visual Indicators**:
- Depth increases when objects move closer (inverted depth)
- Stereo rectification appears incorrect
- Baseline distance is negative or unexpected
- Depth map shows artifacts or inconsistencies

#### Solution 1: Verify Camera Configuration

Ensure the pipeline correctly assigns left and right cameras.

**Steps**:
1. **Check camera socket assignments** in your code:
   ```python
   mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
   mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
   ```

2. **Verify stereo node connections**:
   ```python
   mono_left.out.link(stereo.left)
   mono_right.out.link(stereo.right)
   ```

3. **Test with corrected configuration**:
   - Run the depth capture script
   - Observe if depth values are now correct
   - Move your hand closer/farther to verify depth changes appropriately

**Expected Result**: Depth increases as objects move farther away, decreases as they move closer.

#### Solution 2: Check Device Orientation

The OAK-D Lite has a specific orientation for correct camera assignment.

**Steps**:
1. **Identify camera positions**:
   - Look at the front of the OAK-D Lite device
   - Left camera is on the left side (from device's perspective)
   - Right camera is on the right side (from device's perspective)

2. **Verify USB connection orientation**:
   - Ensure the device is not upside down
   - USB port should be on the bottom or back of the device
   - Camera lenses should face forward

3. **Test orientation**:
   - Run a simple camera preview to verify left/right assignment
   - Check that left camera shows left field of view
   - Check that right camera shows right field of view

**Expected Result**: Left and right cameras correspond to correct physical positions.

#### Solution 3: Recalibrate with Correct Orientation

If cameras were swapped during calibration, recalibration is required.

**Steps**:
1. **Verify device orientation** before starting calibration:
   - Ensure device is right-side up
   - Check that USB cable is not forcing an awkward orientation
   - Position device on a stable surface

2. **Run calibration** with correct orientation:
   ```powershell
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```

3. **Verify baseline distance** after calibration:
   - Should be positive (~7.5 cm for OAK-D Lite)
   - Negative baseline indicates swapped cameras

4. **Flash to EEPROM** if calibration is correct:
   - Confirm baseline is positive and expected value
   - Flash calibration to device
   - Test depth output

**Expected Result**: Baseline distance is positive (~7.5 cm), depth map is correct.

#### Solution 4: Check for Firmware Issues

Outdated firmware can cause camera assignment issues.

**Steps**:
1. **Check current firmware version**:
   ```powershell
   python -c "import depthai as dai; device = dai.Device(); print(f'Firmware version: {device.getDeviceInfo().version}')"
   ```

2. **Update firmware if needed**:
   - Visit [Luxonis firmware releases](https://github.com/luxonis/depthai-python/releases)
   - Follow firmware update instructions for your device
   - Reboot device after firmware update

3. **Test after firmware update**:
   - Run depth capture script
   - Verify cameras are correctly assigned
   - Check depth map accuracy

**Expected Result**: Firmware is up to date, cameras function correctly.

### EEPROM Verification Failures

**Symptom**: Calibration data cannot be written to or read from device EEPROM.

**Visual Indicators**:
- Error message: "Failed to write to EEPROM"
- Error message: "EEPROM verification failed"
- Calibration does not persist after device reboot
- Baseline distance cannot be read from device

#### Solution 1: Check Device Permissions

Windows may require administrator permissions to write to device EEPROM.

**Steps**:
1. **Close all applications** using the OAK-D Lite device:
   - Close any running depth capture scripts
   - Close DepthAI Viewer or other device applications
   - Check Task Manager for processes using the device

2. **Run PowerShell as Administrator**:
   - Right-click PowerShell icon
   - Select "Run as Administrator"
   - Navigate to calibration directory
   - Activate virtual environment

3. **Retry calibration and EEPROM flash**:
   ```powershell
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```
   - Complete calibration process
   - Flash to EEPROM when prompted
   - Verify successful write

**Expected Result**: EEPROM write succeeds with administrator permissions.

#### Solution 2: Check USB Connection

Poor USB connection can cause EEPROM write failures.

**Steps**:
1. **Try a different USB port**:
   - Prefer USB 3.0 ports (usually blue)
   - Avoid USB hubs (connect directly to computer)
   - Try ports on the back of the computer (often more reliable)

2. **Try a different USB cable**:
   - Use a high-quality USB 3.0 cable
   - Ensure cable is not damaged or worn
   - Try a shorter cable (< 1 meter) if possible

3. **Check Device Manager** (Windows):
   - Open Device Manager (Win+X, then M)
   - Look for OAK-D Lite under "Universal Serial Bus devices"
   - Check for yellow warning icons indicating driver issues
   - Update drivers if needed

4. **Restart the device**:
   - Unplug USB cable from device
   - Wait 5 seconds
   - Replug USB cable
   - Wait for device to be recognized
   - Retry EEPROM write

**Expected Result**: Stable USB connection, EEPROM write succeeds.

#### Solution 3: Verify Device is Not in Use

Only one application can access the device at a time.

**Steps**:
1. **Check for running processes**:
   - Open Task Manager (Ctrl+Shift+Esc)
   - Look for Python processes or DepthAI applications
   - End any processes using the OAK-D Lite device

2. **Check for background services**:
   - Some applications may leave background services running
   - Restart computer if unsure
   - Retry EEPROM write after restart

3. **Test device availability**:
   ```powershell
   python -c "import depthai as dai; device = dai.Device(); print('Device available')"
   ```
   - Expected output: `Device available`
   - If error occurs, device is in use or not connected

**Expected Result**: Device is available, EEPROM write succeeds.

#### Solution 4: Check DepthAI Version Compatibility

Outdated or incompatible DepthAI versions can cause EEPROM issues.

**Steps**:
1. **Check current DepthAI version**:
   ```powershell
   pip show depthai
   ```
   - Note the version number

2. **Update DepthAI to latest stable version**:
   ```powershell
   pip install --upgrade depthai
   ```

3. **Verify compatibility**:
   - Check [DepthAI release notes](https://github.com/luxonis/depthai-python/releases)
   - Ensure version is compatible with Python 3.11
   - Ensure version supports EEPROM write for OAK-D Lite

4. **Retry calibration** with updated DepthAI:
   ```powershell
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```

**Expected Result**: Updated DepthAI version, EEPROM write succeeds.

#### Solution 5: Manual EEPROM Write

If automatic EEPROM write fails, try manual write using DepthAI API.

**Steps**:
1. **Save calibration data to file** during calibration:
   - Calibration script should save to `calibration.json` or similar
   - Note the file location

2. **Manually write to EEPROM**:
   ```powershell
   python -c "import depthai as dai; import json; device = dai.Device(); calib = dai.CalibrationHandler('calibration.json'); device.flashCalibration(calib); print('EEPROM write complete')"
   ```

3. **Verify EEPROM data**:
   ```powershell
   python -c "import depthai as dai; device = dai.Device(); calib = device.readCalibration(); print(f'Baseline: {calib.getBaselineDistance():.2f} cm')"
   ```
   - Expected output: `Baseline: 7.50 cm` (or similar)

**Expected Result**: Calibration data successfully written to EEPROM manually.

### Common Error Messages and Solutions

This section provides quick solutions to frequently encountered error messages.

#### Error: "No module named 'cv2.aruco'"

**Cause**: `opencv-python` installed instead of `opencv-contrib-python`, or ArUco module not available.

**Solution**:
```powershell
# Uninstall both opencv packages
pip uninstall opencv-python opencv-contrib-python -y

# Reinstall opencv-contrib-python with correct version
pip install opencv-contrib-python==4.7.0.72
```

**Verification**:
```powershell
python -c "import cv2.aruco; print('ArUco module available')"
```

---

#### Error: "numpy.multiarray error" or "_ARRAY_API error"

**Cause**: NumPy 2.0+ installed, which has breaking changes incompatible with OpenCV 4.7.0.72.

**Solution**:
```powershell
# Downgrade numpy to 1.24.4
pip uninstall numpy -y
pip install numpy==1.24.4

# Reinstall opencv-contrib-python after numpy downgrade
pip install --force-reinstall opencv-contrib-python==4.7.0.72
```

**Verification**:
```powershell
pip show numpy
# Should show version 1.24.4
```

---

#### Error: "Device not found" or "No OAK device detected"

**Cause**: Device not connected, USB connection issue, or driver problem.

**Solution**:
1. **Check physical connection**:
   - Verify USB cable is securely connected
   - Try a different USB port (prefer USB 3.0)
   - Try a different USB cable

2. **Check Device Manager** (Windows):
   - Open Device Manager (Win+X, then M)
   - Look for OAK-D Lite under "Universal Serial Bus devices"
   - Update drivers if yellow warning icon appears

3. **Restart device**:
   - Unplug USB cable
   - Wait 5 seconds
   - Replug USB cable
   - Wait for device recognition

4. **Test device detection**:
   ```powershell
   python -c "import depthai as dai; devices = dai.Device.getAllAvailableDevices(); print(f'Found {len(devices)} device(s)')"
   ```

---

#### Error: "Calibration RMS error too high"

**Cause**: Poor calibration image quality, insufficient coverage, or incorrect board parameters.

**Solution**:
1. **Verify board parameters**:
   - Confirm square size: 2.5 cm (measure with ruler)
   - Confirm board dimensions: 9×6
   - Ensure board is flat and rigid

2. **Improve image capture**:
   - Capture more images (20-25 instead of 15)
   - Cover all areas of field of view
   - Include various distances (30-100 cm)
   - Include various angles (0-45° tilt)
   - Ensure good lighting (no glare or shadows)

3. **Recalibrate**:
   ```powershell
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```
   - Follow best practices for image capture
   - Aim for RMS error < 1.0 pixels

---

#### Error: "Failed to flash calibration to EEPROM"

**Cause**: Device permissions, USB connection issue, or device in use by another application.

**Solution**:
1. **Run as Administrator**:
   - Close PowerShell
   - Right-click PowerShell icon
   - Select "Run as Administrator"
   - Retry calibration

2. **Check device availability**:
   - Close all applications using the device
   - Check Task Manager for Python processes
   - Restart device (unplug/replug USB)

3. **Try different USB port**:
   - Use USB 3.0 port (usually blue)
   - Connect directly to computer (avoid hubs)
   - Try port on back of computer

See [EEPROM Verification Failures](#eeprom-verification-failures) for detailed troubleshooting.

---

#### Error: "Execution policy error" when activating virtual environment

**Cause**: PowerShell execution policy prevents running scripts.

**Solution**:
```powershell
# Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Retry activation
.\oak_env\Scripts\Activate.ps1
```

**Verification**:
- Command prompt should show `(oak_env)` prefix
- Virtual environment is now active

---

#### Error: "Git submodule update failed"

**Cause**: Network connectivity issue, git configuration problem, or authentication failure.

**Solution**:
1. **Check network connectivity**:
   - Verify internet connection
   - Try accessing github.com in a browser
   - Check if behind a corporate firewall or proxy

2. **Retry submodule update**:
   ```powershell
   git submodule update --init --recursive
   ```

3. **Use HTTPS instead of SSH** (if authentication fails):
   ```powershell
   git config --global url."https://github.com/".insteadOf git@github.com:
   git submodule update --init --recursive
   ```

4. **Manual clone** (if submodule update continues to fail):
   - Check `.gitmodules` file for submodule URLs
   - Manually clone each submodule to the correct directory

---

#### Error: "Depth values are all zero" or "No depth data"

**Cause**: Device not calibrated, calibration not loaded, or stereo pipeline misconfigured.

**Solution**:
1. **Verify calibration exists**:
   ```powershell
   python -c "import depthai as dai; device = dai.Device(); calib = device.readCalibration(); print(f'Baseline: {calib.getBaselineDistance():.2f} cm')"
   ```
   - Should output baseline distance (~7.5 cm)
   - If error occurs, device is not calibrated

2. **Recalibrate device** if needed:
   ```powershell
   python calibrate.py -s 2.5 -brd CHARUCO_9x6
   ```

3. **Check pipeline configuration**:
   - Verify stereo node is created and linked
   - Verify cameras are configured correctly
   - Check that depth output is connected to XLinkOut

4. **Test with example script**:
   ```powershell
   cd depthai
   python examples/StereoDepth/depth_preview.py
   ```
   - If example works, issue is in your custom script
   - If example fails, recalibrate device

---

#### Error: "ImportError: DLL load failed" (Windows)

**Cause**: Missing Visual C++ redistributables or incompatible Python version.

**Solution**:
1. **Install Visual C++ Redistributables**:
   - Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
   - Install both x64 and x86 versions
   - Restart computer after installation

2. **Verify Python version**:
   ```powershell
   python --version
   ```
   - Should be Python 3.11.x
   - If not, install Python 3.11 and recreate virtual environment

3. **Reinstall depthai**:
   ```powershell
   pip uninstall depthai -y
   pip install depthai
   ```

---

### Additional Resources

**Official Documentation**:
- [DepthAI Documentation](https://docs.luxonis.com/)
- [DepthAI Python API Reference](https://docs.luxonis.com/projects/api/en/latest/)
- [OAK-D Lite Hardware Documentation](https://docs.luxonis.com/projects/hardware/en/latest/pages/DM9095/)

**Community Support**:
- [DepthAI GitHub Discussions](https://github.com/luxonis/depthai/discussions)
- [Luxonis Community Forum](https://discuss.luxonis.com/)
- [DepthAI Discord Server](https://discord.gg/luxonis)

**Calibration Resources**:
- [Camera Calibration Theory](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)
- [Charuco Board Detection](https://docs.opencv.org/4.x/df/d4a/tutorial_charuco_detection.html)
- [Stereo Calibration Best Practices](https://docs.luxonis.com/projects/api/en/latest/tutorials/calibration/)

**Troubleshooting Tips**:
- Always verify package versions match requirements (opencv-contrib-python==4.7.0.72, numpy==1.24.4)
- Use Python 3.11 (not 3.13 or other versions)
- Ensure good lighting and flat calibration board
- Capture diverse calibration images (various distances, angles, positions)
- Run PowerShell as Administrator for EEPROM operations
- Check USB connection and try different ports/cables
- Close other applications using the device before calibration

---

**End of Calibration Guide**

For depth capture implementation, see the `depth_capture_5x5.py` script and associated documentation in the project repository.
