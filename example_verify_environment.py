#!/usr/bin/env python3
"""
Environment verification script for the OAK-D Lite workflow.

This version keeps output ASCII-only so it prints cleanly in Windows consoles.
"""

import platform
import sys


PASS = "[PASS]"
FAIL = "[FAIL]"


def check_python_version():
    """Check whether the interpreter is Python 3.11."""
    print("=" * 60)
    print("Python Version Check")
    print("=" * 60)

    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    print(f"Current Python version: {version_str}")
    print(f"Platform: {platform.system()} {platform.release()}")

    if version_info.major == 3 and version_info.minor == 11:
        print(f"{PASS} Python 3.11 detected")
        return True

    print(f"{FAIL} Python 3.11 required, but found {version_str}")
    print("  Please create a virtual environment with Python 3.11")
    return False


def check_package_versions():
    """Verify required package versions."""
    print("\n" + "=" * 60)
    print("Package Version Check")
    print("=" * 60)

    packages_ok = True

    try:
        import cv2

        opencv_version = cv2.__version__
        print(f"opencv-contrib-python: {opencv_version}")

        if opencv_version.startswith("4.7.0"):
            print(f"{PASS} opencv-contrib-python 4.7.0.x detected")
        else:
            print(f"{FAIL} opencv-contrib-python 4.7.0.72 recommended, found {opencv_version}")
            print("  Consider: pip install opencv-contrib-python==4.7.0.72")
            packages_ok = False
    except ImportError:
        print(f"{FAIL} opencv-contrib-python not found")
        print("  Install: pip install opencv-contrib-python==4.7.0.72")
        packages_ok = False

    try:
        import numpy as np

        numpy_version = np.__version__
        print(f"numpy: {numpy_version}")

        major_version = int(numpy_version.split(".")[0])
        if numpy_version.startswith("1.24"):
            print(f"{PASS} numpy 1.24.x detected")
        elif major_version >= 2:
            print(f"{FAIL} numpy 1.24.4 recommended, found {numpy_version} (2.0+ may cause issues)")
            print("  Consider: pip install numpy==1.24.4")
            packages_ok = False
        else:
            print(f"{PASS} numpy {numpy_version} detected (pre-2.0)")
    except ImportError:
        print(f"{FAIL} numpy not found")
        print("  Install: pip install numpy==1.24.4")
        packages_ok = False

    try:
        import depthai as dai

        print(f"depthai: {dai.__version__}")
        print(f"{PASS} depthai detected")
    except ImportError:
        print(f"{FAIL} depthai not found")
        print("  Install: pip install depthai")
        packages_ok = False

    return packages_ok


def check_aruco_compatibility():
    """Test cv2.aruco dictionary compatibility."""
    print("\n" + "=" * 60)
    print("ArUco Compatibility Check")
    print("=" * 60)

    try:
        import cv2

        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            print(f"{PASS} cv2.aruco.getPredefinedDictionary works")
            print("  Successfully loaded DICT_4X4_50 dictionary")
            print("  Using OpenCV 4.7+ API")
            return aruco_dict is not None
        except AttributeError:
            aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
            print(f"{PASS} cv2.aruco.Dictionary_get works")
            print("  Successfully loaded DICT_4X4_50 dictionary")
            print("  Using OpenCV < 4.7 API")
            print(f"  Dictionary contains {aruco_dict.bytesList.shape[0]} markers")
            return aruco_dict is not None

    except AttributeError as e:
        print(f"{FAIL} ArUco dictionary access failed")
        print(f"  Error: {e}")
        print("  This may indicate an incompatible OpenCV version")
        return False
    except Exception as e:
        print(f"{FAIL} ArUco compatibility test failed")
        print(f"  Error: {e}")
        return False


def display_summary(python_ok, packages_ok, aruco_ok):
    """Display the overall environment status."""
    print("\n" + "=" * 60)
    print("Environment Status Summary")
    print("=" * 60)

    all_ok = python_ok and packages_ok and aruco_ok

    print(f"Python 3.11:           {PASS if python_ok else FAIL}")
    print(f"Package Versions:      {PASS if packages_ok else FAIL}")
    print(f"ArUco Compatibility:   {PASS if aruco_ok else FAIL}")

    print("\n" + "=" * 60)
    if all_ok:
        print(f"{PASS} Environment is correctly configured!")
        print("  You can proceed with calibration and depth capture.")
    else:
        print(f"{FAIL} Environment has issues that need to be resolved.")
        print("  Please follow the recommendations above.")
    print("=" * 60)

    return all_ok


def main():
    """Main verification routine."""
    print("\nOAK-D Lite Stereo Workflow - Environment Verification")
    print("This script checks your Python environment configuration\n")

    python_ok = check_python_version()
    packages_ok = check_package_versions()
    aruco_ok = check_aruco_compatibility()

    all_ok = display_summary(python_ok, packages_ok, aruco_ok)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
