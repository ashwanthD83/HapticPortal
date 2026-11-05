import machine
import pca9685
import time

i2c = machine.I2C(0, scl=machine.Pin(5), sda=machine.Pin(4))

boards = {
    0: pca9685.PCA9685(i2c, address=0x40), 
    1: pca9685.PCA9685(i2c, address=0x41), 
    2: pca9685.PCA9685(i2c, address=0x42), 
    3: pca9685.PCA9685(i2c, address=0x43)  
}

motor_map = {}
for i in range(25):
    motor_id = i + 1
    board_idx = i // 8            
    ch_fwd = (i % 8) * 2          
    ch_rev = ch_fwd + 1
    motor_map[motor_id] = (board_idx, ch_fwd, ch_rev)

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


run_motor_for_time(motor_id=1, speed=2048, run_time=2.0)

run_motor_for_time(motor_id=25, speed=-4095, run_time=0.5)