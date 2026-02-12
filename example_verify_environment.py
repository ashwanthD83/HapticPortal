#!/usr/bin/env python3
"""
Environment Verification Script for OAK-D Lite Stereo Workflow

This script verifies that the Python environment is correctly configured
with the required package versions and compatibility.

Validates Requirements: 1.5, 5.5, 9.2, 9.4
"""

import sys
import platform


def check_python_version():
    """Check if Python version is 3.11"""
    print("=" * 60)
    print("Python Version Check")
    print("=" * 60)
    
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    print(f"Current Python version: {version_str}")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    if version_info.major == 3 and version_info.minor == 11:
        print("✓ Python 3.11 detected - PASS")
        return True
    else:
        print(f"✗ Python 3.11 required, but found {version_str} - FAIL")
        print("  Please create a virtual environment with Python 3.11")
        return False


def check_package_versions():
    """Verify required package versions"""
    print("\n" + "=" * 60)
    print("Package Version Check")
    print("=" * 60)
    
    packages_ok = True
    
    # Check OpenCV
    try:
        import cv2
        opencv_version = cv2.__version__
        print(f"opencv-contrib-python: {opencv_version}")
        
        if opencv_version.startswith("4.7.0"):
            print("✓ opencv-contrib-python 4.7.0.x detected - PASS")
        else:
            print(f"✗ opencv-contrib-python 4.7.0.72 recommended, found {opencv_version} - WARNING")
            print("  Consider: pip install opencv-contrib-python==4.7.0.72")
            packages_ok = False
    except ImportError:
        print("✗ opencv-contrib-python not found - FAIL")
        print("  Install: pip install opencv-contrib-python==4.7.0.72")
        packages_ok = False
    
    # Check NumPy
    try:
        import numpy as np
        numpy_version = np.__version__
        print(f"numpy: {numpy_version}")
        
        major_version = int(numpy_version.split('.')[0])
        if numpy_version.startswith("1.24"):
            print("✓ numpy 1.24.x detected - PASS")
        elif major_version >= 2:
            print(f"✗ numpy 1.24.4 recommended, found {numpy_version} (2.0+ may cause issues) - WARNING")
            print("  Consider: pip install numpy==1.24.4")
            packages_ok = False
        else:
            print(f"✓ numpy {numpy_version} detected (pre-2.0) - PASS")
    except ImportError:
        print("✗ numpy not found - FAIL")
        print("  Install: pip install numpy==1.24.4")
        packages_ok = False
    
    # Check DepthAI
    try:
        import depthai as dai
        depthai_version = dai.__version__
        print(f"depthai: {depthai_version}")
        print("✓ depthai detected - PASS")
    except ImportError:
        print("✗ depthai not found - FAIL")
        print("  Install: pip install depthai")
        packages_ok = False
    
    return packages_ok


def check_aruco_compatibility():
    """Test cv2.aruco dictionary compatibility"""
    print("\n" + "=" * 60)
    print("ArUco Compatibility Check")
    print("=" * 60)
    
    try:
        import cv2
        
        # Try the newer API first (OpenCV 4.7+)
        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            print("✓ cv2.aruco.getPredefinedDictionary works - PASS")
            print(f"  Successfully loaded DICT_4X4_50 dictionary")
            print(f"  Using OpenCV 4.7+ API")
            return True
        except AttributeError:
            # Fall back to older API (OpenCV < 4.7)
            aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
            print("✓ cv2.aruco.Dictionary_get works - PASS")
            print(f"  Successfully loaded DICT_4X4_50 dictionary")
            print(f"  Using OpenCV < 4.7 API")
            print(f"  Dictionary contains {aruco_dict.bytesList.shape[0]} markers")
            return True
        
    except AttributeError as e:
        print(f"✗ ArUco dictionary access failed - FAIL")
        print(f"  Error: {e}")
        print("  This may indicate an incompatible OpenCV version")
        return False
    except Exception as e:
        print(f"✗ ArUco compatibility test failed - FAIL")
        print(f"  Error: {e}")
        return False


def display_summary(python_ok, packages_ok, aruco_ok):
    """Display overall environment status"""
    print("\n" + "=" * 60)
    print("Environment Status Summary")
    print("=" * 60)
    
    all_ok = python_ok and packages_ok and aruco_ok
    
    print(f"Python 3.11:           {'✓ PASS' if python_ok else '✗ FAIL'}")
    print(f"Package Versions:      {'✓ PASS' if packages_ok else '✗ FAIL/WARNING'}")
    print(f"ArUco Compatibility:   {'✓ PASS' if aruco_ok else '✗ FAIL'}")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ Environment is correctly configured!")
        print("  You can proceed with calibration and depth capture.")
    else:
        print("✗ Environment has issues that need to be resolved.")
        print("  Please follow the recommendations above.")
    print("=" * 60)
    
    return all_ok


def main():
    """Main verification routine"""
    print("\nOAK-D Lite Stereo Workflow - Environment Verification")
    print("This script checks your Python environment configuration\n")
    
    # Run all checks
    python_ok = check_python_version()
    packages_ok = check_package_versions()
    aruco_ok = check_aruco_compatibility()
    
    # Display summary
    all_ok = display_summary(python_ok, packages_ok, aruco_ok)
    
    # Exit with appropriate code
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
