"""
Pico W UDP receiver for the Sprint 2 hand-tracking app.

Upload this file to the Pico W as ``main.py`` using Thonny after filling in
your Wi-Fi credentials below.
"""

import gc
import machine
import network
import socket
import struct
import time


WIFI_SSID = "Starforge Guest"
WIFI_PASSWORD = "makerspace3111"

UDP_PORT = 5000
PACKET_HEADER = b"DPTH"
EXPECTED_PACKET_SIZE = 37
SOCKET_TIMEOUT_SECONDS = 1.0
STATUS_PRINT_EVERY = 10


led = machine.Pin("LED", machine.Pin.OUT)


def blink(count, on_ms=120, off_ms=120):
    for _ in range(count):
        led.on()
        time.sleep_ms(on_ms)
        led.off()
        time.sleep_ms(off_ms)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Wi-Fi already connected.")
        print("IP:", wlan.ifconfig()[0])
        return wlan

    print("Connecting to Wi-Fi:", WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > 20000:
            raise RuntimeError("Wi-Fi connection timed out after 20 seconds.")
        led.toggle()
        time.sleep_ms(200)

    led.off()
    print("Wi-Fi connected.")
    print("IP:", wlan.ifconfig()[0])
    return wlan


def parse_depth_packet(packet):
    if len(packet) != EXPECTED_PACKET_SIZE:
        raise ValueError("Bad packet size: {}".format(len(packet)))

    if packet[:4] != PACKET_HEADER:
        raise ValueError("Bad packet header: {}".format(packet[:4]))

    packet_id, timestamp = struct.unpack("<If", packet[4:12])
    matrix_bytes = packet[12:37]
    matrix = []
    for row_start in range(0, 25, 5):
        matrix.append(list(matrix_bytes[row_start:row_start + 5]))

    return packet_id, timestamp, matrix


def print_matrix(matrix):
    print("-" * 29)
    for row in matrix:
        print("[{:3d} {:3d} {:3d} {:3d} {:3d}]".format(*row))
    print("-" * 29)


def start_udp_server():
    addr = socket.getaddrinfo("0.0.0.0", UDP_PORT)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(addr)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)
    print("Listening for UDP on port", UDP_PORT)
    return sock


def run():
    wlan = connect_wifi()
    sock = start_udp_server()
    packet_count = 0
    last_packet_ms = time.ticks_ms()

    print("Ready. Point the PC app at Pico IP:", wlan.ifconfig()[0])
    blink(3, on_ms=60, off_ms=60)

    while True:
        try:
            packet, sender = sock.recvfrom(256)
        except OSError:
            if time.ticks_diff(time.ticks_ms(), last_packet_ms) > 10000:
                print("Waiting for packets...")
                last_packet_ms = time.ticks_ms()
            continue

        try:
            packet_id, timestamp, matrix = parse_depth_packet(packet)
        except Exception as exc:
            print("Packet parse error:", exc)
            continue

        packet_count += 1
        last_packet_ms = time.ticks_ms()
        led.toggle()

        print(
            "Packet #{} from {}:{} at {:.3f}".format(
                packet_id, sender[0], sender[1], timestamp
            )
        )

        if packet_count == 1 or packet_count % STATUS_PRINT_EVERY == 0:
            print_matrix(matrix)
            print("Free mem:", gc.mem_free())


try:
    run()
except Exception as exc:
    led.off()
    print("Fatal error:", exc)
    blink(8, on_ms=80, off_ms=80)
