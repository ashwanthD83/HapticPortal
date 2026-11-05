import network
import socket
import time

import struct

def decode_depth_packet(packet):
    # Unpack the 37-byte payload using the exact same little-endian format string
    unpacked_data = struct.unpack("<4sIf25s", packet)
    
    # Extract and format the individual components
    header = unpacked_data[0].decode('utf-8')  # Converts b'DPTH' back to 'DPTH'
    packet_id = unpacked_data[1]               # Standard integer
    timestamp = unpacked_data[2]               # Float
    
    # Convert the 25 matrix bytes back into a standard Python list of integers
    matrix_values = list(unpacked_data[3])
    
    return header, packet_id, timestamp, matrix_values

WIFI_SSID = "TamuFabLab_STUDENT"
WIFI_PASSWORD = "TFL_Student609"

# 1. Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while not wlan.isconnected():
    time.sleep(1)
    
# Print the Pico's IP address so you know where to send the data
pico_ip = wlan.ifconfig()[0]
print(f"Connected! Pico IP Address: {pico_ip}")

# 2. Create the UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to all network interfaces on port 1234
udp_socket.bind(('0.0.0.0', 1234))

print("Listening for incoming UDP packets...")

# 3. Receive Data
while True:
    packet, addr = udp_socket.recvfrom(1024)
    
    # Verify the packet is exactly the expected 37 bytes (4 + 4 + 4 + 25) before unpacking
    if len(packet) == 37:
        header, p_id, timestamp, matrix = decode_depth_packet(packet)
        
        if header == "DPTH":
            print(f"Received Packet {p_id} from {addr[0]}")
            print(f"Timestamp: {timestamp:.2f}")
            print(f"Matrix Data: {matrix}")
    else:
        print(f"Ignored malformed packet of length {len(packet)}")
