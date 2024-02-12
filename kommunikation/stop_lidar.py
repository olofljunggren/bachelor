
from rplidar import RPLidar
import time

def main():
    #time.sleep(5)
    LIDAR_PORT = '/dev/ttyUSB0'
    lidar = RPLidar(LIDAR_PORT)
    lidar.connect()
    lidar.start_motor()
    lidar.stop_motor()
    lidar.stop()
    lidar.disconnect()

main()