# Hand Tracking Sprint 2 Consolidated Guide

This is the single working reference for the current final script:
- `hand_tracking_sprint2.py`

The system now uses MediaPipe hand landmarks (not YOLO) plus OAK-D depth processing and optional UDP transmission.

## What It Does

`hand_tracking_sprint2.py` runs a real-time hand-tracking pipeline with:
- OAK-D RGB + depth streams
- MediaPipe 21-landmark hand detection
- Depth-region extraction and normalization to 5x5
- Optional UDP transmission of the smoothed 5x5 matrix
- On-screen profiling and calibration controls

## Required Runtime Pieces

Core script:
- `hand_tracking_sprint2.py`

Support modules used directly by sprint2:
- `src/depth_processor.py`
- `src/performance_profiler.py`
- `src/calibration_manager.py`
- `src/config_persistence.py`
- `src/optimized_renderer.py`

Config file:
- `config_hand_tracking.py`

Calibration reference (kept intentionally):
- `docs/CALIBRATION_GUIDE.md`

Launcher:
- `run_hand_tracking_sprint2.ps1`

## Dependencies

Install in your virtual environment:
- `depthai`
- `opencv-python`
- `numpy`
- `mediapipe`

The script includes a compatibility hint for MediaPipe + NumPy:
- `mediapipe==0.10.14`
- `numpy<2`

## Run

From project root:

```powershell
.\.venv\Scripts\Activate.ps1
python hand_tracking_sprint2.py
```

or use:

```powershell
.\run_hand_tracking_sprint2.ps1
```

## Controls

In the main app window:
- `q` quit
- `s` toggle UDP on/off
- `c` auto-calibrate depth range
- `r` reset depth range defaults
- `+` or `=` increase max depth
- `-` or `_` decrease max depth
- `[` decrease min depth
- `]` increase min depth
- `p` persist calibration to `config_hand_tracking.py`

## UDP Behavior

Default target in script:
- IP: `192.168.1.100`
- Port: `5000`

Packets are sent only when all are true:
- hand is detected
- confidence is high enough (`> 0.8`)
- UDP is currently enabled

## Window Outputs

The script renders four windows:
1. RGB camera with hand box
2. Colorized depth map
3. Hand region crop
4. 5x5 matrix display with FPS and UDP status

## Calibration and Persistence

- Runtime adjustments update active `HAND_DEPTH_MIN/HAND_DEPTH_MAX`
- Press `p` to write those values into `config_hand_tracking.py`
- Next run attempts to load saved values back in at startup

## Notes

- Sprint2 is the current final script.
- Older hand-tracking iterations and YOLO model assets were removed to reduce project clutter.
- The calibration guide in `docs/CALIBRATION_GUIDE.md` remains as the dedicated depth-calibration reference.
