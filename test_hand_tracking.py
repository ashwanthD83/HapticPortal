#!/usr/bin/env python3
"""
Test script to diagnose hand tracking issues
"""

import sys

print("Testing hand tracking components...")
print("=" * 60)

# Test 1: Import basic modules
print("\n1. Testing basic imports...")
try:
    import cv2
    print(f"   ✓ OpenCV: {cv2.__version__}")
except Exception as e:
    print(f"   ✗ OpenCV failed: {e}")
    sys.exit(1)

try:
    import numpy as np
    print(f"   ✓ NumPy: {np.__version__}")
except Exception as e:
    print(f"   ✗ NumPy failed: {e}")
    sys.exit(1)

try:
    import depthai as dai
    print(f"   ✓ DepthAI: {dai.__version__}")
except Exception as e:
    print(f"   ✗ DepthAI failed: {e}")
    sys.exit(1)

# Test 2: Import local modules
print("\n2. Testing local imports...")
try:
    from src.depth_processor import process_depth_frame
    print("   ✓ depth_processor imported")
except Exception as e:
    print(f"   ✗ depth_processor failed: {e}")
    sys.exit(1)

# Test 3: Test hand tracking script import
print("\n3. Testing hand_tracking_visual import...")
try:
    import hand_tracking_visual
    print("   ✓ hand_tracking_visual imported")
except Exception as e:
    print(f"   ✗ hand_tracking_visual failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check device availability
print("\n4. Checking for OAK-D Lite device...")
try:
    devices = dai.Device.getAllAvailableDevices()
    if devices:
        print(f"   ✓ Found {len(devices)} device(s)")
        for i, dev in enumerate(devices):
            print(f"     Device {i+1}: {dev.getMxId()}")
    else:
        print("   ⚠ No devices found (this is OK if device not connected)")
except Exception as e:
    print(f"   ⚠ Could not check devices: {e}")

print("\n" + "=" * 60)
print("✓ All tests passed!")
print("\nIf you're seeing an error when running hand_tracking_visual.py,")
print("please share the exact error message.")
print("=" * 60)
