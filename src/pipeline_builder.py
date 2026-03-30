"""
DepthAI Pipeline Builder for OAK-D Lite Stereo Workflow

This module provides functions to create and configure DepthAI pipelines
for stereo depth capture using the OAK-D Lite device.

Requirements: 5.1, 5.2, 5.3, 5.4
"""

import depthai as dai


def create_stereo_pipeline():
    """
    Create a DepthAI pipeline configured for stereo depth capture.
    
    This function creates a complete pipeline with:
    - Left and right MonoCamera nodes (400p resolution)
    - StereoDepth node with HIGH_ACCURACY preset
    - XLinkOut node for streaming depth data to host
    
    The pipeline uses the calibration data stored in the device EEPROM
    to compute accurate depth maps from the stereo camera pair.
    
    Returns:
        dai.Pipeline: Configured DepthAI pipeline ready for device initialization
        
    Requirements:
        - 5.1: Create left and right MonoCamera nodes
        - 5.2: Create StereoDepth node with HIGH_ACCURACY preset
        - 5.3: Link camera outputs to stereo inputs
        - 5.4: Create XLinkOut node for depth stream
    """
    pipeline = dai.Pipeline()
    
    # Create left and right mono cameras (Requirement 5.1)
    mono_left = pipeline.create(dai.node.MonoCamera)
    mono_right = pipeline.create(dai.node.MonoCamera)
    
    # Configure left camera (CAM_B is the left camera on OAK-D Lite)
    mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
    
    # Configure right camera (CAM_C is the right camera on OAK-D Lite)
    mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
    
    # Create stereo depth node with ACCURACY preset (Requirement 5.2)
    stereo = pipeline.create(dai.node.StereoDepth)
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.ACCURACY)
    stereo.setLeftRightCheck(True)
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(False)
    
    # Link camera outputs to stereo inputs (Requirement 5.3)
    mono_left.out.link(stereo.left)
    mono_right.out.link(stereo.right)
    
    # Create XLinkOut node for depth stream (Requirement 5.4)
    xout_depth = pipeline.create(dai.node.XLinkOut)
    xout_depth.setStreamName("depth")
    stereo.depth.link(xout_depth.input)
    
    return pipeline
