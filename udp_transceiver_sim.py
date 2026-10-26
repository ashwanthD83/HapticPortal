import socket
import struct
import time
import random

PICO_IP = "192.168.1.100"
PICO_PORT = 5000

def create_depth_packet(packet_id):
    """Constructs a 37-byte packet matching the Pico's expected format."""
    header = b"DPTH"
    timestamp = time.time() % 1000.0  
    
    # random matrix values
    matrix_values = [random.randint(0, 255) for _ in range(25)]
    matrix_bytes = bytes(matrix_values)

    # <: little endian
    # 4s: 4 bytes for header (DPTH)
    # I: 4 bytes for unsigned int (packet_id) 
    # f: 4 bytes for a float (timestamp) 
    # 25s: 25 bytes for matrix data
    packet = struct.pack("<4sIf25s", header, packet_id, timestamp, matrix_bytes)
    
    return packet

def main():
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"sending UDP to {PICO_IP}:{PICO_PORT}...")
    
    packet_id = 1
    try:
        while True:
            packet = create_depth_packet(packet_id)
            sock.sendto(packet, (PICO_IP, PICO_PORT))
            
            print(f"sent packet #{packet_id} ({len(packet)} bytes)")
            packet_id += 1
            
            time.sleep(0.1) 
            
    except KeyboardInterrupt:
        print("\ntransmission stopped by user.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()