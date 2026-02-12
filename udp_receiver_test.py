#!/usr/bin/env python3
"""
UDP Receiver Test Script

This script simulates a Raspberry Pi Pico receiving depth data.
Use this to test the UDP transmission before connecting to actual hardware.

Run this on the same computer or another device on your network.
"""

import socket
import struct
import time
import sys


def main():
    # Configuration - match these with hand_tracking_udp.py
    LISTEN_IP = "0.0.0.0"  # Listen on all interfaces
    LISTEN_PORT = 5000
    
    print("=" * 70)
    print("UDP Receiver Test (Simulating Raspberry Pi Pico)")
    print("=" * 70)
    print(f"\nListening on: {LISTEN_IP}:{LISTEN_PORT}")
    print("Waiting for depth data packets...\n")
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    packet_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Receive packet
            data, addr = sock.recvfrom(1024)
            
            # Parse packet
            if len(data) < 41:
                print(f"Invalid packet size: {len(data)} bytes")
                continue
            
            # Extract header
            header = data[0:4]
            if header != b"DPTH":
                print(f"Invalid header: {header}")
                continue
            
            # Extract packet ID and timestamp
            packet_id, timestamp = struct.unpack("<If", data[4:12])
            
            # Extract 5x5 depth array
            depth_data = data[12:37]
            depth_array = list(depth_data)
            
            # Reshape to 5x5
            depth_5x5 = [depth_array[i:i+5] for i in range(0, 25, 5)]
            
            packet_count += 1
            elapsed = time.time() - start_time
            fps = packet_count / elapsed if elapsed > 0 else 0
            
            # Display packet info
            print(f"\r[Packet #{packet_id}] From: {addr[0]}:{addr[1]} | "
                  f"Received: {packet_count} | FPS: {fps:.1f}", end="")
            
            # Display 5x5 array every 30 packets
            if packet_count % 30 == 0:
                print("\n\n5x5 Depth Array:")
                print("-" * 30)
                for row in depth_5x5:
                    print("  [", end="")
                    for val in row:
                        print(f"{val:3d}", end=" ")
                    print("]")
                print("-" * 30)
                print()
    
    except KeyboardInterrupt:
        print("\n\nShutdown requested")
    
    finally:
        sock.close()
        elapsed = time.time() - start_time
        avg_fps = packet_count / elapsed if elapsed > 0 else 0
        
        print(f"\n\nStatistics:")
        print(f"  Total packets received: {packet_count}")
        print(f"  Total time: {elapsed:.1f}s")
        print(f"  Average FPS: {avg_fps:.1f}")
        print("\nExiting.")


if __name__ == "__main__":
    main()
