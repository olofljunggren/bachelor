from rplidar import RPLidar
import time
from utils import *
import json
import os
import csv

# Initiate variables

DATA_DIR = "data/input"
POS_FILE = "untitled.csv"

LIDAR_PORT = '/dev/ttyUSB0'
lidar = None
isRecording = False
isAutonomous = False
measurement_list = []
connection = ""
threshold = 100
counter = 0
crash_point_counter = 0
obstacle_point_counter_left = 0
obstacle_point_counter_right = 0
start_time_obstacle = time.time()

lidar_capture_channel = ""
collision_detection_channel = ""
obstacle_detection_channel = ""
com_message_channel = ""

def main():

    """
    This function connects to the server, creates necessary channels, initializes the RPLidar device,
    and handles the lidar scans for obstacle and collision detection.
    """

    global connection
    global lidar
    connection = connect_to_server("localhost")

    global lidar_capture_channel
    lidar_capture_channel = create_channel(connection, "lidar_capture")

    global collision_detection_channel    
    collision_detection_channel = create_channel(connection, "collision_detection")

    global obstacle_detection_channel    
    obstacle_detection_channel = create_channel(connection, "obstacle_detection")

    global com_message_channel
    com_message_channel = create_channel(connection, "com_message")

    lidar = RPLidar(LIDAR_PORT)
    lidar.connect()
    lidar.start_motor()

    retries = 0
    while(retries < 5):
        try:
            scan_data = lidar.iter_scans()
            for scan in scan_data:
                handle_scan(scan)
            retries = 0

        except KeyboardInterrupt:
            break
        
        except Exception as e:
            time.sleep(1)
            print("Tappade anslutningen, försöker igen...")
            print(e)
            retries += 1
            try:
                lidar = RPLidar(LIDAR_PORT)
                lidar.connect()
                lidar.start_motor()
            except Exception as e2:
                print(e2)
    if lidar != None:
        lidar.stop_motor()
        lidar.stop()
        lidar.disconnect()

def process_scan(scan):
    """
    Process the given scan data and return the distance, angle, and timestamp 
    if the distance is within the range of 150 to 6000. Otherwise, return None.
    """
    angle = scan[1]
    distance = scan[2]
    if 150 <= distance <= 6000:
        return [distance, angle, str(time.time())]

def detect_collision(scan):
    """
    Determines if there is a collision detected based on the given scan data.
    """
    angle = scan[1]
    distance = scan[2]
    if (150 <= distance <= 350) and ((340 <= angle <= 360) or (0 <= angle <= 20)):
        return True
    else:
        return False

def detect_obstacle(scan):
    """
    Detects if an obstacle is within a specific range and angle from the scan data.

    Args:
        scan (tuple): A tuple containing the scan data (index, angle, distance)

    Returns:
        tuple: A tuple containing the direction of the obstacle ("left" or "right"), 
               the distance to the obstacle, and the angle of the obstacle.
               If no obstacle is detected, returns (None, None, None).
    """
    angle = scan[1]
    distance = scan[2]
    if (350 <= distance <= 700) and (340 <= angle <= 360):
        return "left", distance, angle
    elif (350 <= distance <= 700) and (0 <= angle <= 20):
        return "right", distance, angle
    else:
        return None, None, None

def handle_scan(scan):

    """
    Handles the incoming LIDAR scan data, processes the data, and takes appropriate actions based on the scan results.
    This includes recording the LIDAR data, detecting collisions, and detecting obstacles in autonomous mode.
    """

    global isRecording
    global measurement_list
    global DATA_DIR
    global POS_FILE
    global threshold
    global counter
    global connection
    global lidar_capture_channel
    global crash_point_counter
    global collision_detection_channel
    global start_time_obstacle
    global com_message_channel
    global obstacle_detection_channel
    global obstacle_point_counter_left
    global obstacle_point_counter_right
    global isAutonomous

    message = None
    if counter > threshold:
        message = get_latest_message("lidar_capture", connection, lidar_capture_channel)
        counter = 0

    if not message is None:
        data_capture = json.loads(message)
        if data_capture["action"] == "start":
            print(data_capture["id"])
            POS_FILE = data_capture["id"] + "_lidar" + ".csv"
            isRecording = True
            send_message("com_message", f'Spelar in till {POS_FILE}', connection, com_message_channel)

        elif data_capture["action"] == "stop":
            isRecording = False
            send_message("com_message", "Slutar spela in lidardata", connection, com_message_channel)

        elif data_capture["action"] == "manual":
            isAutonomous = False

        elif data_capture["action"] == "autonomous":
            isAutonomous = True

    if (isRecording):
        for s in scan:
            point = process_scan(s)
            if point is not None:
                #print(point)
                measurement_list.append(point)

    elif measurement_list:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, POS_FILE), 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(measurement_list)
        measurement_list = []
    else:
        for data in scan:
            # Crash handling
            collided = detect_collision(data)
            if collided:
                crash_point_counter += 1
                if crash_point_counter > 30:
                    crash_point_counter = 0
                    send_message("collision_detection", "crash", connection, collision_detection_channel)
                    send_message("com_message", "Bilen har kolliderat!", connection, com_message_channel)
                    break

            # Obstacle handling
            zone, distance, angle = detect_obstacle(data)
            if isAutonomous and zone == "left":
                obstacle_point_counter_left += 1
                if obstacle_point_counter_left+obstacle_point_counter_right > 30:
                    if obstacle_point_counter_left > obstacle_point_counter_right:
                        send_message("obstacle_detection", f"left:{distance}:{angle}", connection, collision_detection_channel)
                    else:
                        send_message("obstacle_detection", f"right:{distance}:{angle}", connection, collision_detection_channel)
                    send_message("com_message", "Bilen hittade ett hinder!", connection, com_message_channel)
                    obstacle_point_counter_left = 0
                    obstacle_point_counter_right = 0
                    break
            if isAutonomous and zone == "right":
                obstacle_point_counter_right += 1
                if obstacle_point_counter_left+obstacle_point_counter_right > 10:
                    if obstacle_point_counter_left > obstacle_point_counter_right:
                        send_message("obstacle_detection", f"left:{distance}:{angle}", connection, collision_detection_channel)
                    else:
                        send_message("obstacle_detection", f"right:{distance}:{angle}", connection, collision_detection_channel)
                    obstacle_point_counter_right = 0
                    obstacle_point_counter_right = 0
                    break
                
            
            # Reset crash and obstacle counter every third second
            current_time = time.time()
            if (current_time - start_time_obstacle) > 3:
                crash_point_counter = 0
                obstacle_point_counter_left = 0
                obstacle_point_counter_right = 0
                start_time_obstacle = time.time()

    counter += 1
                



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        lidar.stop_motor()
        lidar.stop()
        lidar.disconnect()
    except:
        if lidar != None:
            lidar.stop_motor()
            lidar.stop()
            lidar.disconnect()