import machine
from machine import Pin
import time
import micropython_pca9685 as pca9685

stby_1 = Pin(6, Pin.OUT, value=1)
stby_2 = Pin(7, Pin.OUT, value=1)
stby_3 = Pin(8, Pin.OUT, value=1)

i2c = machine.I2C(0, scl=Pin(5), sda=Pin(4))
pca = pca9685.PCA9685(i2c, address=0x40)
pca.frequency = 1000

motor_map = {
    1: (0, 1),
    2: (2, 3),
    3: (4, 5),
    4: (8, 9),
    5: (10, 11),
    6: (12, 13),
    7: (14, 15)
}

current_speeds = [0] * 7

def set_motor(motor_id, speed):
    if motor_id not in motor_map:
        return
    
    # checks speed bounds
    speed = max(-4095, min(4095, int(speed)))
    current_speeds[motor_id - 1] = speed
    
    ch_fwd, ch_rev = motor_map[motor_id]
    #converts to 16bit which is the format that pca board wants
    duty_16bit = min(65535, abs(speed) * 16)
    
    # chooses channel based on direction
    if speed > 0:
        pca.channels[ch_fwd].duty_cycle = duty_16bit
        pca.channels[ch_rev].duty_cycle = 0
    elif speed < 0:
        pca.channels[ch_fwd].duty_cycle = 0
        pca.channels[ch_rev].duty_cycle = duty_16bit
    else:
        pca.channels[ch_fwd].duty_cycle = 0
        pca.channels[ch_rev].duty_cycle = 0

def stop_all():
    for m_id in range(1, 8):
        set_motor(m_id, 0)

print("=== 7-Motor USB Console Controller ===")
print("Commands:")
print("  <id> <speed>         -> Set single motor (e.g., '1 2048' or '4 -3000')")
print("  <s1> <s2> ... <s7>   -> Set all 7 motors at once (7 space-separated speeds)")
print("  all <speed>          -> Set all 7 motors to the same speed (e.g., 'all 2000')")
print("  stop                 -> Stop all motors")
print("  q                    -> Stop motors and quit\n")

try:
    while True:
        cmd = input("Motor Cmd > ").strip().lower()

        if not cmd:
            continue

        if cmd == "q":
            break
        elif cmd == "stop":
            stop_all()
            print("All motors stopped.")
        elif cmd.startswith("all "):
            try:
                spd = int(cmd.split()[1])
                for m_id in range(1, 8):
                    set_motor(m_id, spd)
                print(f"All motors set -> {current_speeds}")
            except (IndexError, ValueError):
                print("Usage: all <speed> (e.g., all 2048)")
        else:
            parts = cmd.split()
            try:
                if len(parts) == 2:
                    # parts[0] is first argument, parts[1] is second
                    m_id = int(parts[0])
                    spd = int(parts[1])
                    if 1 <= m_id <= 7:
                        set_motor(m_id, spd)
                        print(f"Motor {m_id} set to {current_speeds[m_id - 1]} | All: {current_speeds}")
                    else:
                        print("Motor ID must be between 1 and 7.")
                # sets all motors with different speeds
                elif len(parts) == 7:
                    for idx, val in enumerate(parts):
                        set_motor(idx + 1, int(val))
                    print(f"Updated all 7 motors -> {current_speeds}")
                else:
                    print("Invalid format. Enter '<id> <speed>', 7 speeds, 'all <speed>', or 'stop'.")
            except ValueError:
                print("Invalid numbers. Example: 2 2500")

except KeyboardInterrupt:
    print("\nInterrupted by user.")
finally:
    stop_all()
    print("All motors stopped. Program exited.")

