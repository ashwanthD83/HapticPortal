# Hand Tracking + UDP Setup Guide

## Overview

The `hand_tracking_udp.py` script provides three key features:

1. **Hand Tracking**: Automatically detects and crops to your hand, ignoring background
2. **Data Smoothing**: Rolling average filter eliminates flickering
3. **UDP Networking**: Sends stable 5x5 depth data to Raspberry Pi Pico over WiFi

## Quick Start

### Step 1: Configure Your Pico's IP Address

Edit `hand_tracking_udp.py` and change these lines:

```python
PICO_IP = "192.168.1.100"  # Change to your Pico's IP
PICO_PORT = 5000           # Change if your Pico uses a different port
```

### Step 2: Test UDP Locally (Optional)

Before connecting to your Pico, test the UDP transmission:

**Terminal 1 - Start the receiver:**
```powershell
python udp_receiver_test.py
```

**Terminal 2 - Start the hand tracker:**
```powershell
python hand_tracking_udp.py
```

You should see packets being received in Terminal 1!

### Step 3: Run with Your Pico

Once your Pico is on the network and listening:

```powershell
python hand_tracking_udp.py
```

## Configuration Options

### Hand Detection Settings

In `hand_tracking_udp.py`, adjust these values:

```python
# Hand depth range (in millimeters)
HAND_DEPTH_MIN = 200       # Closest distance (20cm)
HAND_DEPTH_MAX = 1500      # Farthest distance (150cm)

# Hand size constraints
MIN_HAND_AREA = 1000       # Minimum pixels for hand detection
MAX_HAND_AREA = 100000     # Maximum pixels
```

**Tips:**
- If hand isn't detected: Increase `HAND_DEPTH_MAX` or decrease `MIN_HAND_AREA`
- If background is detected as hand: Decrease `HAND_DEPTH_MAX` or increase `MIN_HAND_AREA`
- Adjust depth range based on your use case (closer/farther)

### Smoothing Settings

```python
SMOOTHING_WINDOW = 5       # Number of frames to average
```

**Tips:**
- Higher value (7-10): Smoother but slower response
- Lower value (3-5): Faster response but more jitter
- Default (5): Good balance for most use cases

### UDP Settings

```python
PICO_IP = "192.168.1.100"  # Your Pico's IP address
PICO_PORT = 5000           # Port your Pico is listening on
UDP_ENABLED = True         # Start with UDP enabled
```

## Controls

While running:
- **'s' key**: Toggle UDP sending ON/OFF
- **'q' key**: Quit the application

## UDP Packet Format

The script sends 41-byte packets:

```
Byte 0-3:   Header "DPTH" (4 bytes)
Byte 4-7:   Packet ID (uint32, little-endian)
Byte 8-11:  Timestamp (float32, little-endian)
Byte 12-36: 5x5 depth array (25 bytes, uint8, row-major order)
```

### Example Pico Receiver Code (MicroPython)

```python
import socket
import struct

# Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 5000))

while True:
    data, addr = sock.recvfrom(1024)
    
    # Parse packet
    if len(data) == 41 and data[0:4] == b'DPTH':
        packet_id, timestamp = struct.unpack('<If', data[4:12])
        depth_array = list(data[12:37])
        
        # Reshape to 5x5
        depth_5x5 = [depth_array[i:i+5] for i in range(0, 25, 5)]
        
        # Use depth_5x5 for your application
        print(f"Packet {packet_id}: {depth_5x5[2][2]}")  # Center value
```

## Visualization

The display window shows:

**Top Section:**
- Green box: Hand detected and tracked
- Red text: No hand detected (using full frame)

**Middle Section:**
- Left grid: Raw 5x5 values (before smoothing)
- Right grid: Smoothed 5x5 values (after rolling average)

**Bottom Section:**
- UDP status (ON/OFF)
- Packet count
- Target IP and port
- Controls

## Troubleshooting

### Hand Not Detected

**Problem**: "NO HAND DETECTED" shown even with hand in view

**Solutions:**
1. Adjust depth range:
   ```python
   HAND_DEPTH_MIN = 100   # Try closer
   HAND_DEPTH_MAX = 2000  # Try farther
   ```

2. Check lighting - ensure good ambient light

3. Move hand to different distances from camera

4. Reduce minimum area:
   ```python
   MIN_HAND_AREA = 500  # Lower threshold
   ```

### Background Detected as Hand

**Problem**: Background objects detected instead of hand

**Solutions:**
1. Narrow depth range:
   ```python
   HAND_DEPTH_MAX = 1000  # Only detect close objects
   ```

2. Increase minimum area:
   ```python
   MIN_HAND_AREA = 2000  # Require larger objects
   ```

3. Position hand closer to camera

### Values Still Flickering

**Problem**: Smoothed values still jump around

**Solutions:**
1. Increase smoothing window:
   ```python
   SMOOTHING_WINDOW = 10  # More averaging
   ```

2. Check if hand is moving too fast

3. Ensure stable lighting conditions

### UDP Not Sending

**Problem**: Packet count stays at 0

**Solutions:**
1. Press 's' to toggle UDP on

2. Verify Pico IP address is correct:
   ```python
   PICO_IP = "192.168.1.100"  # Check this!
   ```

3. Ensure Pico is on same network

4. Check firewall settings (Windows may block UDP)

5. Test with `udp_receiver_test.py` first

### Network Issues

**Problem**: Packets not reaching Pico

**Solutions:**
1. Verify Pico IP with ping:
   ```powershell
   ping 192.168.1.100
   ```

2. Check Pico is listening on correct port

3. Ensure both devices on same WiFi network

4. Try disabling Windows Firewall temporarily

5. Check router settings (some routers block UDP)

## Performance Tips

### Optimize Frame Rate

- Close other applications using camera
- Use USB 3.0 port for OAK-D Lite
- Reduce smoothing window if lag is noticeable

### Reduce Network Latency

- Use wired connection for PC if possible
- Ensure strong WiFi signal for Pico
- Reduce network traffic on same network
- Consider increasing UDP buffer size on Pico

### Battery Life (for Pico)

- Only send packets when hand is detected (already implemented)
- Reduce frame rate if needed (add delay in main loop)
- Use lower resolution depth map (already optimized at 5x5)

## Advanced Configuration

### Change Packet Rate

Add a delay in the main loop:

```python
# In main() loop, after cv2.imshow()
time.sleep(0.033)  # ~30 FPS
# or
time.sleep(0.016)  # ~60 FPS
```

### Add Packet Validation

Modify UDP sender to include checksum:

```python
import hashlib

# In send_depth_array()
checksum = hashlib.md5(data).digest()[:4]
packet = header + struct.pack("<If", packet_id, timestamp) + data + checksum
```

### Multiple Pico Targets

Send to multiple Picos:

```python
PICO_TARGETS = [
    ("192.168.1.100", 5000),
    ("192.168.1.101", 5000),
]

for ip, port in PICO_TARGETS:
    self.socket.sendto(packet, (ip, port))
```

## Integration with Your Project

### Getting Hand Position

The bounding box gives you hand location:

```python
if hand_detected and hand_bbox:
    x, y, w, h = hand_bbox
    center_x = x + w // 2
    center_y = y + h // 2
    # Use center_x, center_y for positioning
```

### Getting Specific Depth Values

Access individual cells in the 5x5 array:

```python
# Center cell
center_depth = depth_5x5_smoothed[2, 2]

# Top-left corner
top_left = depth_5x5_smoothed[0, 0]

# Average of all cells
avg_depth = np.mean(depth_5x5_smoothed)
```

### Gesture Detection

Use depth patterns for gestures:

```python
# Detect "push" gesture (hand moving closer)
if center_depth > 200:  # Hand is close
    print("Push detected!")

# Detect "wave" gesture (hand moving side to side)
left_avg = np.mean(depth_5x5_smoothed[:, 0:2])
right_avg = np.mean(depth_5x5_smoothed[:, 3:5])
if abs(left_avg - right_avg) > 50:
    print("Wave detected!")
```

## Next Steps

1. **Test locally** with `udp_receiver_test.py`
2. **Calibrate hand detection** by adjusting depth range
3. **Tune smoothing** for your use case
4. **Connect to Pico** and verify packets received
5. **Integrate** with your Pico application

## Support

For issues:
1. Check this troubleshooting guide
2. Review configuration settings
3. Test with receiver script first
4. Verify network connectivity

Happy tracking! 🖐️
