# Quick Reference Card

## Files Created

| File | Purpose |
|------|---------|
| `hand_tracking_udp.py` | Main script with hand tracking, smoothing, and UDP |
| `udp_receiver_test.py` | Test UDP reception before connecting Pico |
| `HAND_TRACKING_SETUP.md` | Complete setup and troubleshooting guide |

## Quick Commands

```powershell
# Test UDP locally (2 terminals)
python udp_receiver_test.py    # Terminal 1
python hand_tracking_udp.py    # Terminal 2

# Run with Pico
python hand_tracking_udp.py

# Run original scripts
python depth_capture_5x5.py         # Console output only
python depth_viewer_visual.py       # Visual windows
python example_basic_depth.py       # Educational example
python example_verify_environment.py # Check setup
```

## Configuration Checklist

- [ ] Set `PICO_IP` in `hand_tracking_udp.py`
- [ ] Set `PICO_PORT` in `hand_tracking_udp.py`
- [ ] Adjust `HAND_DEPTH_MIN` and `HAND_DEPTH_MAX` if needed
- [ ] Test with `udp_receiver_test.py` first
- [ ] Verify Pico is on network: `ping <PICO_IP>`

## Controls

| Key | Action |
|-----|--------|
| `s` | Toggle UDP sending ON/OFF |
| `q` | Quit application |

## Key Features

### ✅ Task 3.1: Hand Tracking
- Automatically detects hand in depth range 200-1500mm
- Crops depth map to hand region only
- Ignores background noise
- Shows green box when hand detected

### ✅ Task 3.2: Data Smoothing
- Rolling average filter (5-frame window)
- Eliminates flickering
- Configurable smoothing strength
- Shows both raw and smoothed values

### ✅ Task 3.3: UDP Networking
- Sends 5x5 array to Pico automatically
- 41-byte packet format
- Packet ID and timestamp included
- Toggle on/off with 's' key

## Packet Format (41 bytes)

```
[0-3]   "DPTH" header
[4-7]   Packet ID (uint32)
[8-11]  Timestamp (float32)
[12-36] 5x5 depth array (25 x uint8)
```

## Common Settings

### For Close-Range Tracking (0-50cm)
```python
HAND_DEPTH_MIN = 50
HAND_DEPTH_MAX = 500
```

### For Medium-Range Tracking (20-150cm)
```python
HAND_DEPTH_MIN = 200
HAND_DEPTH_MAX = 1500
```

### For Far-Range Tracking (50-300cm)
```python
HAND_DEPTH_MIN = 500
HAND_DEPTH_MAX = 3000
```

### More Smoothing (Slower Response)
```python
SMOOTHING_WINDOW = 10
```

### Less Smoothing (Faster Response)
```python
SMOOTHING_WINDOW = 3
```

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Hand not detected | Increase `HAND_DEPTH_MAX` to 2000 |
| Background detected | Decrease `HAND_DEPTH_MAX` to 1000 |
| Values flickering | Increase `SMOOTHING_WINDOW` to 10 |
| Slow response | Decrease `SMOOTHING_WINDOW` to 3 |
| UDP not sending | Press 's' key to toggle on |
| Packets not received | Check `PICO_IP` is correct |

## Network Setup

### Find Your Pico's IP
On Pico (MicroPython):
```python
import network
wlan = network.WLAN(network.STA_IF)
print(wlan.ifconfig()[0])  # Prints IP address
```

### Test Network Connection
On PC:
```powershell
ping <PICO_IP>
```

## Example Pico Receiver (MicroPython)

```python
import socket
import struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 5000))

while True:
    data, addr = sock.recvfrom(1024)
    if len(data) == 41 and data[0:4] == b'DPTH':
        depth_array = list(data[12:37])
        # Use depth_array (25 values, row-major)
        center = depth_array[12]  # Center cell
        print(f"Center depth: {center}")
```

## Performance Metrics

- **Frame Rate**: ~30 FPS typical
- **Packet Rate**: ~30 packets/sec (when hand detected)
- **Latency**: <50ms typical (local network)
- **Packet Size**: 41 bytes
- **Bandwidth**: ~1.2 KB/sec

## What Each Script Does

### hand_tracking_udp.py ⭐ (NEW)
- Hand detection + smoothing + UDP
- Best for Pico integration
- Shows raw vs smoothed comparison

### depth_viewer_visual.py
- Visual depth viewer
- 3 windows (RGB, depth, combined)
- No hand tracking or UDP

### depth_capture_5x5.py
- Console output only
- No visualization
- Simple depth capture

### example_basic_depth.py
- Educational example
- Shows center point depth
- Detailed comments

## Tips

1. **Always test with `udp_receiver_test.py` first**
2. **Adjust depth range for your use case**
3. **Start with default smoothing (5 frames)**
4. **Use 's' key to toggle UDP without restarting**
5. **Check network with ping before blaming code**

## Support Files

- `HAND_TRACKING_SETUP.md` - Full setup guide
- `README.md` - Project overview
- `CALIBRATION_GUIDE.md` - Camera calibration
