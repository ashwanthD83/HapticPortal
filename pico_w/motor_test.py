import machine
import pca9685

# Initialize I2C on the Pico
i2c = machine.I2C(0, scl=machine.Pin(5), sda=machine.Pin(4))

# Initialize all four boards on the I2C bus
pca_1 = pca9685.PCA9685(i2c, address=0x40)
pca_2 = pca9685.PCA9685(i2c, address=0x41)
pca_3 = pca9685.PCA9685(i2c, address=0x42)
pca_4 = pca9685.PCA9685(i2c, address=0x43)

# Move Motor 25 (PCA 4, Channels 0 & 1) at ~50% speed
pca_4.duty(0, 2048) 
pca_4.duty(1, 0)