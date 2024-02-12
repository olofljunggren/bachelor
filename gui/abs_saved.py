import asyncio
import qtm
import os
import csv
from rplidar import RPLidar
import math
from datetime import datetime
import time
import single_instance_with_monitor
import os
import signal
import sys
import logging
import threading

X = 0
Y = 0
ANGLE = 0
IP = "192.168.0.50"
LIDAR_PORT = '/dev/ttyUSB0'
DATA_DIR = os.path.abspath('data')
DATA_FILE = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + "_abs_points" + ".csv"
POS_FILE = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + "pos_" + ".csv"
TIME_TO_RUN = 10000  # in seconds

def on_packet(packet):
    global X 
    global Y
    global ANGLE

    X = int(packet.get_6d_euler()[1][0][0].x)
    Y = int(packet.get_6d_euler()[1][0][0].y)
    ANGLE = int(packet.get_6d_euler()[1][0][1].a3)

    print(packet.get_6d_euler())

    #with open(os.path.join(DATA_DIR, POS_FILE), 'w', newline='') as csvfile:
    #    csv_writer = csv.writer(csvfile)
    #    csv_writer.writerows([[X, Y, ANGLE, str(time.time())]])

def process_scan(scan):
    logging.debug(f"Processing scan: {scan}")
    angle_rad = math.radians(scan[1])
    distance = scan[2]
    if 150 <= distance <= 5000:
        abs_x = X + distance * math.cos(angle_rad + math.radians(ANGLE))
        abs_y = Y + distance * math.sin(angle_rad + math.radians(ANGLE))
        return abs_x, abs_y, str(time.time())

def lidar_capture(lidar):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, DATA_FILE), 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['X', 'Y', "TIME"])

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < TIME_TO_RUN:
            scan_data = lidar.iter_scans()
            for scan in scan_data:
                abs_points = [process_scan(s) for s in scan]
                filtered_items = list(filter(lambda item: item is not None, abs_points))
                csv_writer.writerows(filtered_items)

async def setup():
    """ Main function """
    connection = await qtm.connect(IP)
    if connection is None:
        return

    await connection.stream_frames(components=["6deuler", "3d"], on_packet=on_packet)

async def position_and_rotation_capture():
    try:
        asyncio.ensure_future(setup())
        asyncio.get_event_loop().run_forever()
    except Exception as e:
        pass

def main():

    lidar = RPLidar(LIDAR_PORT)

    try:
        
        T2 = threading.Thread(target=lidar_capture, args=(lidar,))
        T2.start()

        T = threading.Thread(target=position_and_rotation_capture)
        T.start()

    except:
        lidar.stop_motor()
        lidar.stop()
        lidar.disconnect()
    finally:
        lidar.stop_motor()
        lidar.stop()
        lidar.disconnect()

if __name__ == "__main__":
    try:
        os.setsid()
    except OSError:
        pass
    single_instance_with_monitor.run_with_lock_and_monitor(main())
