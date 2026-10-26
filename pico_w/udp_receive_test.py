import socket

# Listen on all available network interfaces on your laptop
UDP_IP = "0.0.0.0" 

# This MUST match the target port your Pico is sending data to
UDP_PORT = 1234    

# Create an IPv4 UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the IP and port
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for UDP packets on port {UDP_PORT}...")

try:
    while True:
        # Wait for data (1024 bytes buffer size)
        data, addr = sock.recvfrom(1024) 
        
        # Decode the byte payload to a string
        message = data.decode('utf-8')
        
        print(f"Received from {addr[0]}:{addr[1]} -> {message}")
        
except KeyboardInterrupt:
    print("\nStopping UDP listener.")
finally:
    sock.close()