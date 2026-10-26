import network
import socket
import time

WIFI_SSID = "TamuFabLab_STUDENT"
WIFI_PASSWORD = "TFL_Student609"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('YOUR_SSID', 'YOUR_PASSWORD')

# 2. Create the UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 3. Send a UDP packet
while True:
    target_ip = '10.246.64.31'
    target_port = 1234
    udp_socket.sendto(b"Hello from Pico W!", (target_ip, target_port))
    time.sleep(1)