import struct
from machine import UART, Pin
import machine
import pca9685
import time

i2c = machine.I2C(0, scl=machine.Pin(5), sda=machine.Pin(4))

boards = {
    0: pca9685.PCA9685(i2c, address=0x40), 
    1: pca9685.PCA9685(i2c, address=0x41), 
}

motor_map = {}
for i in range(9):
    motor_id = i + 1
    board_idx = i // 8            
    ch_fwd = (i % 8) * 2          
    ch_rev = ch_fwd + 1
    motor_map[motor_id] = (board_idx, ch_fwd, ch_rev)

dist_map = {}
for i in range(1, 10):
    dist_map[i] = 0

def update_motor_distances(matrix_values):
    print()
    


def run_motor_for_time(motor_id, speed, run_time):
    if motor_id not in motor_map:
        print(f"Error: Motor {motor_id} not found in map.")
        return
        
    board_idx, ch_fwd, ch_rev = motor_map[motor_id]
    pca = boards[board_idx]
    
    print(f"Starting Motor {motor_id} on Board {hex(0x40 + board_idx)} (Ch {ch_fwd}/{ch_rev}) for {run_time}s...")
    
    if speed > 0:
        pca.duty(ch_fwd, speed)
        pca.duty(ch_rev, 0)
    elif speed < 0:
        pca.duty(ch_fwd, 0)
        pca.duty(ch_rev, abs(speed))
    else:
        pca.duty(ch_fwd, 0)
        pca.duty(ch_rev, 0)
        
    time.sleep(run_time)
    
    pca.duty(ch_fwd, 0)
    pca.duty(ch_rev, 0)
    
    print(f"Motor {motor_id} stopped.")

uart = UART(1, baudrate=9600, tx=Pin(0), rx=Pin(1))

while True:
    # Wait until a full 36-byte matrix packet has arrived
    if uart.any() >= 40:
        data = uart.read(40)
        
        # Unpack the bytes back into a tuple of 9 integers
        unpacked_struct = struct.unpack("<4s9i", data)
        if(unpacked_struct == b"DPTH"):
            matrix_values = unpacked_struct[1:]
            print(f"Received Matrix: {matrix_values}")
        else:
            print("Misaligned packet, clearing buffer...")
            uart.read()