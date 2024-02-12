import numpy as np
from utils import *
from map_cones import identify_cones
import subprocess
import json 
import time
import math as ma
import copy
import sys
from bezier import *

REFRESHRATE = 500
TIME_PER_LOOP = 1 / REFRESHRATE


class RaceCar:
    def __init__(self) -> None:
        # Speed variables
        self.requested_speed = 0
        self.odometer_speed = 0
        self.autonomous_speed = 0
        self.autonomous_base_speed = 500
        self.autonomous_extra_speed = 500

        # Constant parameters car
        self.max_speed = 4000
        self.min_speed = 0
        self.min_servo_speed = 390
        self.max_servo_speed = 500

        # Steer variables
        self.min_steer = 275
        self.max_steer = 475
        self.steer_angle = 375

        # Position data
        self.position = (0, 0)
        self.orientation = 90 #Grader

        # Autonomous related parameters
        self.autonomous = False
        self.requested_number_of_laps = 1
        self.autonomous_laps_left = 0
        
        # Checkpoint info
        self.distance_to_goal = 0
        self.angle_to_goal = 0
        self.checkpoint_indices = []
        self.upcoming_checkpoint_indices = []
        self.number_of_removed_indices = 0

        # Driving point lists
        self.manual_car_positions = []
        self.planned_path_positions = []

        # Bezier optimization
        self.bezier_points = []
        self.bezier_mode = False
        self.send_bezier_counter = 0

        # Other
        self.cone_positions = []
        self.is_recording_path = False

        # Crash parameters
        self.hasCrashed = False
        self.noCrashMessageCount = 0

        # Connection init
        self.connection = connect_to_server("localhost")
        self.channel_manager = {}

        # PID speed
        self.error_last3_speed = []
        self.error_last3_odometer = []
        self.KP_speed = 10.0
        self.KI_speed = 0.0
        self.KD_speed = 0.0
        self.last_error_speed = 0
        self.integrated_error_speed = 0
        self.last_sent_spi_speed = 0

        # PID steer
        self.KP_steer = 15
        self.KI_steer = 0.0
        self.KD_steer = 1
        self.last_error_steer = 0
        self.integrated_error_steer = 0
        self.look_ahead_distance = 700

        # Terminate old instances
        kill_scripts_containing("position_receiver")
        kill_scripts_containing("lidar_receiver")

        purge_queue("lidar_capture")
        purge_queue("pos_capture")
        purge_queue("internal_odometer_signal")

        # Open position and lidar scripts
        self.pos_sub = subprocess.Popen(["python3", "/home/admin/Dokument/communication-module/position_receiver.py"], start_new_session=False)
        self.lidar_sub = subprocess.Popen(["python3", "/home/admin/Dokument/communication-module/lidar_receiver.py"], start_new_session=False)

    def run(self):
        counter = 0
        while True:
            if self.autonomous and not self.hasCrashed: 
                self.handle_autonomous_steering()
                self.remove_driven_route()
            
            # Important main loop updates
            self.update_position_data()
            self.update_speed()
            self.check_for_collision()
            self.avoid_obstacle()
            self.send_speed_to_spi()

            # Less frequent main loop updates
            if counter > 10:
                self.update_pid()
                self.update_mode()
                self.update_distance_and_angle_to_goal()
                self.send_remaining_data_to_gui()
                counter = 0
            counter += 1
            
    # Create new channel if no channel exist, else return existing one
    def get_channel(self, channel_name):
        if channel_name in self.channel_manager:
            return self.channel_manager[channel_name]
        else:
            self.channel_manager[channel_name] = create_channel(self.connection, channel_name)
            return self.channel_manager[channel_name]

    # Updates pid if received new message
    def update_pid(self):
        message = get_latest_message("pid_queue", self.connection, self.get_channel("pid_queue"))
        if (not message is None) and (":" in message):
            
            self.KP_speed = float(message.split(':')[0])
            self.KI_speed = float(message.split(':')[1])
            self.KD_speed = float(message.split(':')[2])
            self.KP_steer = float(message.split(':')[3])
            self.KI_steer = float(message.split(':')[4])
            self.KD_steer = float(message.split(':')[5])
            
            print(f'New PID: KP={self.KP_speed}, KI={self.KI_speed}, KD={self.KD_speed}, KPsteer={self.KP_steer}, KIsteer={self.KI_steer}, KDsteer={self.KD_steer}')

    # Updates mode if received new message
    def update_mode(self):
        message = get_latest_message("mode_queue", self.connection, self.get_channel("mode_queue"))
        if not message is None or message != "":
            if message == "autonomous":
                # Initializes autonomous paramters
                self.autonomous = True
                self.autonomous_laps_left = self.requested_number_of_laps
                self.autonomous_speed = 0
                self.number_of_removed_indices = 0
                
                # Sending status updates
                message = { "action": "autonomous"}
                send_message("lidar_capture", json.dumps(message), self.connection, self.get_channel("lidar_capture"))
                send_message("com_message", "Bytt till autonomt läge", self.connection, self.get_channel("com_message"))

                # Parameter for saving new or driving last saved course
                save_new_course = True
                absolute_path = "/home/admin/Dokument/communication-module/"
                
                # Saves recorded route, else read last recorded one
                if save_new_course:
                    with open(absolute_path + "data/manual_car_positions.json", "w+") as f:
                        f.write(json.dumps(self.manual_car_positions))
                else:
                    with open(absolute_path + "data/manual_car_positions.json", "r") as f:
                        self.manual_car_positions = json.loads(f.read())

                # Use new cones and save backup or use previous cones
                if save_new_course:
                    with open(absolute_path + "data/cones/cone_data.json", "r") as f:
                        self.cone_positions = json.loads(f.read())
                    with open(absolute_path + "data/cone_data_backup.json", "w+") as f:
                        f.write(json.dumps(self.cone_positions))
                else:
                    with open(absolute_path + "data/cone_data_backup.json", "r") as f:
                        self.cone_positions = json.loads(f.read())
                        send_message("cone_position", json.dumps(self.cone_positions))

                # Updates order of checkpoints or use previous indices
                if save_new_course:
                    self.update_checkpoint_indices(self.cone_positions, "manual")
                    with open(absolute_path + "data/checkpoint_indices.json", "w+") as f:
                        f.write(json.dumps(self.checkpoint_indices))
                else:
                    with open(absolute_path + "data/checkpoint_indices.json", "r") as f:
                        self.checkpoint_indices = json.loads(f.read())
                
                # Creates a list with checkpoint positions
                if (not self.manual_car_positions is None) and (self.manual_car_positions != []):
                    checkpoints = [self.manual_car_positions[x] for x in self.checkpoint_indices]
                else:
                    checkpoints = []

                # Sends checkpoints to bezier script and save bezier route
                if self.bezier_mode:
                    print("bezier")
                    send_message("internal_checkpoints", json.dumps(checkpoints), self.connection, self.get_channel("internal_checkpoints"))
                    time.sleep(5)
                    with open(absolute_path + "data/bezier/bezier_points.json", "r") as f:
                        self.bezier_points = json.loads(f.read())

                    send_message("bezier_route", json.dumps(self.bezier_points), self.connection, self.get_channel("bezier_route"))
                    self.planned_path_positions = copy.deepcopy(self.bezier_points)
                    self.update_checkpoint_indices(self.cone_positions, "bezier")

                    if (not self.bezier_points is None) and (self.bezier_points != []):
                        checkpoints = [self.bezier_points[x] for x in self.checkpoint_indices]
                    else:
                        checkpoints = []
                else:
                    # Saves a copy of manual route to path list
                    self.planned_path_positions = copy.deepcopy(self.manual_car_positions)

                # Sends checkpoints to gui
                send_message("checkpoints", json.dumps(checkpoints), self.connection, self.get_channel("checkpoints"))
                # Saves a copy of checkpoint indices to temp list
                self.upcoming_checkpoint_indices = copy.deepcopy(self.checkpoint_indices)

            elif message == "manual":
                # Initializes manual paramters
                self.autonomous = False
                self.manual_car_positions = []
                self.planned_path_positions = []
                self.checkpoint_indices = []
                self.upcoming_checkpoint_indices = []
                self.autonomous_speed = 0
                self.autonomous_laps_left = 0
                self.hasCrashed = False
                self.send_bezier_counter = 0

                # Sending status updates
                message = { "action": "manual"}
                send_message("lidar_capture", json.dumps(message), self.connection, self.get_channel("lidar_capture"))
                send_message("com_message", "Bytt till manuellt läge", self.connection, self.get_channel("com_message"))

        # Updates bezier mode
        message = get_latest_message("bezier_queue", self.connection, self.get_channel("bezier_queue"))
        if not message is None or message != "":
            if message == "activateBezier":
                self.bezier_mode = True
            if message == "deactivateBezier":
                self.bezier_mode = False

    # Crash message handling
    def check_for_collision(self):
        message = get_latest_message("collision_detection", self.connection, self.get_channel("collision_detection"))
        if not message is None or message != "":
            if message == "crash":
                self.hasCrashed = True
                self.autonomous_speed = 0
                self.autonomous_laps_left = 0
            elif self.hasCrashed:
                self.noCrashMessageCount += 1
                if self.noCrashMessageCount >= 50:
                    print("reset")

                    # Reseting control parameters
                    self.last_sent_spi_speed = 0
                    self.error_last3_speed = [0, 0, 0]
                    self.error_last3_odometer = [0, 0, 0]
                    self.last_error_speed = 0
                    self.integrated_error_speed = 0
                    self.requested_speed  = 0
                    
                    # Reseting crash parameters
                    self.hasCrashed = False
                    self.noCrashMessageCount = 0

    # Function to avoid obstacle in autonomous mode
    def avoid_obstacle(self):
        message = get_latest_message("obstacle_detection", self.connection, self.get_channel("obstacle_detection"))
        if self.autonomous and (not message is None):
            obstacle_info = message.split(":")
            zone = obstacle_info[0]
            distance = float(obstacle_info[1])
            angle = float(obstacle_info[2])

            obstacle_x = self.position[0] + distance*ma.cos(self.orientation-angle*ma.pi/180) # Angles calculated clockwise for LIDAR
            obstacle_y = self.position[1] + distance*ma.sin(self.orientation-angle*ma.pi/180)

            obstacle_is_checkpoint = False

            # Checks if the obstacle is a cone from the course
            for cone_list in self.cone_positions:
                distance_second_cone = 0
                distance_first_cone = 0
                if len(cone_list) == 2:
                    distance_second_cone = pow((cone_list[0]["position"][0]-obstacle_x),2) + pow((cone_list[1]["position"][1]-obstacle_y),2)
                if len(cone_list) == 1:
                    distance_first_cone = pow((cone_list[0]["position"][0]-obstacle_x),2) + pow((cone_list[0]["position"][1]-obstacle_y),2)

                if (distance_first_cone < 500000) or (distance_second_cone < 500000):
                    obstacle_is_checkpoint = True
                
            if obstacle_is_checkpoint:
                return

            # Remove upcoming point to recalculate route
            self.remove_points_thorugh_obstacle

            # Found a obstacle in front of the car on the left
            if zone == "left":
                send_message("com_message", "Bilen hittade ett hinder till vänster!", connection, com_message_channel)
                delta = -30 # degrees
                small_radius = 350
                large_radius = 500
                start_angle = self.orientation

                # Insert new points to the path list in half a ellipse to the right
                for index in range(4,0,-1):
                    if index == 1 or index == 4:
                        point_x = obstacle_x + large_radius*ma.cos((start_angle + index*delta)*ma.pi/180)
                        point_y = obstacle_y + large_radius*ma.sin((start_angle + index*delta)*ma.pi/180)
                    else:
                        point_x = obstacle_x + small_radius*ma.cos((start_angle + index*delta)*ma.pi/180)
                        point_y = obstacle_y + small_radius*ma.sin((start_angle + index*delta)*ma.pi/180)

                    point = (point_x, point_y)
                    self.planned_path_position.insert(0, point)

            # Found a obstacle in front of the car on the left
            elif zone == "right":
                send_message("com_message", "Bilen hittade ett hinder till höger!", connection, com_message_channel)
                delta = 30 # degrees
                small_radius = 350
                large_radius = 500
                start_angle = 0
                start_angle = self.orientation
                
                # Insert new points to the path list in a half ellipse to the left
                for index in range(4,0,-1):
                    if index == 1 or index == 4:
                        point_x = obstacle_x + large_radius*ma.cos((start_angle + index*delta)*ma.pi/180)
                        point_y = obstacle_y + large_radius*ma.sin((start_angle + index*delta)*ma.pi/180)
                    else:
                        point_x = obstacle_x + small_radius*ma.cos((start_angle + index*delta)*ma.pi/180)
                        point_y = obstacle_y + small_radius*ma.sin((start_angle + index*delta)*ma.pi/180)

                    point = (point_x, point_y)
                    self.planned_path_position.insert(0, point)

    # Removes points in the upcoming 1 meter driving
    def remove_points_thorugh_obstacle(self):
        distance_threshold = 1000000 # (1000mm)^2 
        number_of_points_to_remove = 0

        # Adds distance from car to first point
        if self.planned_path_position:
            number_of_points_to_remove += 1
            distance += pow(self.planned_path_position[0][0]-self.position[0], 2) + pow(self.planned_path_position[0][1]-self.position[1], 2)

        # Adds distance from point n to point n+1 until distance > threshold
        for point in self.planned_path_position:
            distance += pow(point[0]-self.position[0], 2) + pow(point[1]-self.position[1], 2)
            number_of_points_to_remove += 1
            if distance > distance_threshold:
                break

        # Removes the calculated number of points        
        for i in range(number_of_points_to_remove):
            del self.planned_path_position[0]

    # Sends steer angle and checkpoint data to gui
    def send_remaining_data_to_gui(self):
        message =  f'{self.steer_angle}:{self.distance_to_goal}:{self.angle_to_goal}'
        send_message("checkpoint_data", message, self.connection, self.get_channel("checkpoint_data"))

        # Sends calculated bezier route to when calculations definitley ready
        if self.send_bezier_counter < 20:
            self.send_bezier_counter += 1
            if self.send_bezier_counter == 20:
                send_message("bezier_route", json.dumps(self.bezier_points), self.connection, self.get_channel("bezier_route"))
    
    # Update speed related parameters
    def update_speed(self):
        message = get_latest_message("internal_odometer_signal", self.connection, self.get_channel("internal_odometer_signal"))
        
        if (not message is None):
            data = json.loads(message)
            self.odometer_speed = (int(data[2], 16)<<8) + int(data[1], 16)

            self.error_last3_odometer.append(int(self.odometer_speed))
            self.error_last3_odometer = self.error_last3_odometer[-3:]

            # If speed hasnt been updated last 3, suppose it is 0
            if len(set(self.error_last3_odometer)) == 1:
                self.odometer_speed = 0

            # Sends odometer_speed and required speed to gui
            self.autonomous_speed = int(self.autonomous_speed)
            message =  f'{self.odometer_speed}:{self.autonomous_speed}'
            send_message("speed_data", message, self.connection, self.get_channel("speed_data"))

        # Update requested user speed
        message = get_latest_message("requested_speed", self.connection, self.get_channel("requested_speed"))
        if (not message is None) and (message != ""):
            if not self.hasCrashed:
                self.requested_speed = int(message)
                self.integrated_error_speed = 0
    
    # Update position related parameters
    def update_position_data(self):
        # Check if recording
        action = get_latest_message("path_capture", self.connection, self.get_channel("path_capture"))
        if (not action is None):
            if action == "start_recording":
                self.is_recording_path = True
            elif action == "stop_recording":
                self.is_recording_path = False

        # Update position from positioning system
        positions = get_latest_message("internal_position", self.connection, self.get_channel("internal_position"))
        if (not positions is None):
            position_data = json.loads(positions)
            try:
                self.orientation = int(position_data["ANGLE"])
                self.position = ((int(position_data["X"]), int(position_data["Y"])))

                # Logic for start position
                if len(self.manual_car_positions) == 0:
                    self.manual_car_positions.append( (int(self.position[0]), int(self.position[1])) )
                if len(self.manual_car_positions) == 2:
                    self.manual_car_positions[0] = self.manual_car_positions[1]

                xdiff = self.manual_car_positions[-1][0] - int(self.position[0])
                ydiff = self.manual_car_positions[-1][1] - int(self.position[1])
                dist = xdiff*xdiff + ydiff*ydiff

                # Send position to gui if moved 10 cm since last point 
                if dist > 10000:
                # Send position data to gui
                    message =  f'{self.position[0]}:{self.position[1]}:{self.orientation}'
                    send_message("position_data", message, self.connection, self.get_channel("position_data"))

                    # Add point to plan path if recording in manual mode
                    if (not self.autonomous) and (self.is_recording_path) :
                        self.manual_car_positions.append((self.position[0], self.position[1]))
            except Exception as e:
                print(e) 

    # Removes passed by points 
    def remove_driven_route(self):
        distance_threshold = 600
        current_removed_indices = 0

        # Checks max 5 points, and removs if is in removal range, also removs checkpoints if in range
        for index in range( min(5,len(self.planned_path_positions) ) ):
            x_diff = self.position[0] - self.planned_path_positions[index-current_removed_indices][0]
            y_diff = self.position[1] - self.planned_path_positions[index-current_removed_indices][1]
            distance_to_point = np.sqrt(pow(x_diff, 2) + pow(y_diff, 2))

            if distance_to_point < distance_threshold:
                if len(self.upcoming_checkpoint_indices) > 0 and \
                    self.number_of_removed_indices == self.upcoming_checkpoint_indices[0]:
                    del self.upcoming_checkpoint_indices[0]
                del self.planned_path_positions[0]
                
                current_removed_indices += 1
                self.number_of_removed_indices += 1

        # If path list is empty, countdown lap
        if len(self.planned_path_positions) == 0:
            self.autonomous_laps_left -= 1
            if self.autonomous_laps_left >=1:
                print("Varv kvar:", self.autonomous_laps_left)
                if self.bezier_mode:
                    self.planned_path_positions = copy.deepcopy(self.bezier_points)
                else:
                    self.planned_path_positions = copy.deepcopy(self.manual_car_positions)

                self.number_of_removed_indices = 0
                self.upcoming_checkpoint_indices = copy.deepcopy(self.checkpoint_indices)
            else:
                self.autonomous_speed = 0
                self.autonomous_laps_left = 0
        
    # Update
    def send_speed_to_spi(self):
        global TIME_PER_LOOP
        speed_error = 0

        # Get speed error
        if self.autonomous:
            speed_error = self.autonomous_speed - self.odometer_speed
        else:
            speed_error = self.requested_speed - self.odometer_speed
        
        # Updating integration and derivative error
        self.integrated_error_speed += speed_error
        derivative_error = (speed_error - self.last_error_speed) / TIME_PER_LOOP

        # Updating signal with PID
        speed_signal = self.KP_speed * speed_error + self.KI_speed * self.integrated_error_speed + self.KD_speed * derivative_error
        speed_signal_spi = speed_signal/10000 + self.last_sent_spi_speed   #TODO speed controller? speed_signal_spi = speed_signal/1000 + self.min_servo_speed
           
        # Save last three sent errors
        self.error_last3_speed.append(int(speed_signal_spi))
        self.error_last3_speed = self.error_last3_speed[-3:]

        # Adjust speed to possible servo signals
        if speed_signal_spi > self.max_servo_speed:
            speed_signal_spi = self.max_servo_speed
        elif 0 < speed_signal_spi < self.min_servo_speed:
            speed_signal_spi = self.min_servo_speed
        elif speed_signal_spi < 0:
            speed_signal_spi = 0

        # If speed in current mode is 0, set message as break signal
        if (self.autonomous) and (self.autonomous_speed == 0):
            message = f'[0xf0]'
            speed_signal_spi = 0
        elif (not self.autonomous) and (self.requested_speed == 0):
            message = f'[0xf0]'
            speed_signal_spi = 0
        else:
            # Convert signal to two hexadecimal bytes
            signal = hex(int(speed_signal_spi))
            first_byte, second_byte = convert_int_to_two_bytes(signal)
            message = f'[0x02, {first_byte}, {second_byte}]'

        # Send SPI if error not is 0 and signal has changed
        if (int(speed_error) != 0) and (len(set(self.error_last3_speed)) != 1):
            if (speed_signal_spi == 0) or self.hasCrashed:
                message = f'[0xf0]'
                speed_signal_spi = 0
            send_message("send_spi", message, self.connection, self.get_channel("send_spi"))

        self.last_error_speed = speed_error
        self.last_sent_spi_speed = speed_signal_spi
    

    def handle_autonomous_steering(self):
        global TIME_PER_LOOP
        x_point = 0
        y_point = 0
        x_car = self.position[0]
        y_car = self.position[1]
        distance = 0

        # Calculation of look ahead point
        for index, position in enumerate(self.planned_path_positions):
            x_point = position[0]
            y_point = position[1]

            if index == 0:
                distance += np.sqrt( pow(x_point-x_car, 2) + pow(y_point-y_car, 2) )
            else:
                previous_x_point = self.planned_path_positions[index-1][0]
                previous_y_point = self.planned_path_positions[index-1][1]
                distance += np.sqrt( pow(x_point-previous_x_point, 2) + pow(y_point-previous_y_point, 2) )

            if distance >= self.look_ahead_distance:
                break
    
        ### Follow the carrot ###
        # Calculation of requested orientation in the global system
        if x_point-x_car == 0:
            requested_orientation = 90 if y_point-y_car >= 0 else -90
        else:
            requested_orientation = np.arctan((y_point-y_car)/(x_point-x_car))*180/3.1415926
        if x_point-x_car < 0:
            requested_orientation += 180
        if requested_orientation > 180:
            requested_orientation -= 360

        # Calculation of error angle in the global system
        error_angle = self.orientation - requested_orientation
        if error_angle > 180:
            error_angle -= 360
        elif error_angle < -180:
            error_angle += 360

        # Speed control in autonomous mode
        self.autonomous_speed = self.autonomous_base_speed + self.autonomous_extra_speed/(0.05*pow(abs(error_angle),1.5)+1)

        # PID steer controller 
        self.integrated_error_steer += error_angle
        derivative_error = (error_angle - self.last_error_steer)/TIME_PER_LOOP
        
        steer_angle_displacement = (error_angle*self.KP_steer + self.KI_steer*self.integrated_error_steer + self.KD_steer*derivative_error) / 10
        straight_forward = (self.min_steer+self.max_steer)/2
        self.steer_angle = straight_forward + steer_angle_displacement

        # Adjust steer signal to possible servo signal
        if self.steer_angle > self.max_steer:
            self.steer_angle = self.max_steer
        if self.steer_angle < self.min_steer:
            self.steer_angle = self.min_steer
        
        self.last_error_steer = error_angle

        # Sends steer servo signal
        first_byte, second_byte = convert_int_to_two_bytes(hex(int(self.steer_angle)))
        message = f'[0x12, {first_byte}, {second_byte}]'
        send_message("send_spi", message, self.connection, self.get_channel("send_spi"))

    # Calculates index in path list for each checkpoint
    def update_checkpoint_indices(self, cone_positions, mode):
        shortest_dist_index = 0
        self.checkpoint_indices = []
        if mode == "manual":
            planned_path_list = self.manual_car_positions
        elif mode == "bezier":
            planned_path_list = self.bezier_points


        for cone_list in cone_positions:
            shortest_dist_to_mid_point = 100000000
            # Assume cone_list contains a pair of cones
            if len(cone_list) == 2:
                cone_pair_mid_point = (1/2*(cone_list[0]["position"][0]+cone_list[1]["position"][0]), \
                                    1/2*(cone_list[0]["position"][1]+cone_list[1]["position"][1]) )
                
                # Save index of point with shortest distance to midpoint
                for index, car_pos in enumerate(planned_path_list):
                    dist_to_mid_point = pow(car_pos[0]-cone_pair_mid_point[0], 2) + pow(car_pos[1]-cone_pair_mid_point[1], 2)
                    if dist_to_mid_point < shortest_dist_to_mid_point:
                        shortest_dist_to_mid_point = dist_to_mid_point
                        shortest_dist_index = index
                
                self.checkpoint_indices.append(shortest_dist_index)

            # Assume cone_list contains a single cone
            elif len(cone_list) == 1:
                shortest_dist_to_cone = 100000000
                cone_position = cone_list[0]["position"]
                for index, car_pos in enumerate(planned_path_list):
                    dist_to_cone = pow(car_pos[0]-cone_position[0], 2) + pow(car_pos[1]-cone_position[1], 2)
                    if dist_to_cone < shortest_dist_to_cone:
                        shortest_dist_to_cone = dist_to_cone
                        shortest_dist_index = index

                self.checkpoint_indices.append(shortest_dist_index)

        # Sorts the checkpoints to correct driving order
        self.checkpoint_indices.sort()

    # Calculates checkpoint data
    def update_distance_and_angle_to_goal(self):
        x_checkpoint = self.position[0]
        y_checkpoint = self.position[1]

        # If list is empty, consider first checkpoint on next lap
        if len(self.upcoming_checkpoint_indices) == 0:
            if len(self.checkpoint_indices) != 0:
                self.upcoming_checkpoint_indices.append(self.checkpoint_indices[0])
            else:
                return

        # Calculates the x and y position for checkpoint
        if (self.bezier_mode) and (self.bezier_points):
            next_checkpoint = self.bezier_points[self.upcoming_checkpoint_indices[0]]
            x_checkpoint = next_checkpoint[0]
            y_checkpoint = next_checkpoint[1]
        elif (not self.bezier_mode) and (self.manual_car_positions):
            next_checkpoint = self.manual_car_positions[self.upcoming_checkpoint_indices[0]]
            x_checkpoint = next_checkpoint[0]
            y_checkpoint = next_checkpoint[1]

        x_car = self.position[0]
        y_car = self.position[1]

        # Update angle to next checkpoint
        requested_orientation = 0
        if x_checkpoint == x_car:
            requested_orientation = 90 if y_checkpoint-y_car > 0 else -90
        else: 
            requested_orientation = np.arctan((y_checkpoint-y_car)/(x_checkpoint-x_car))*180/ma.pi
        
        if x_checkpoint-x_car < 0:
            requested_orientation += 180
        
        if requested_orientation > 180:
            requested_orientation -= 360

        self.angle_to_goal = self.orientation - requested_orientation 
        if self.angle_to_goal > 180:
            self.angle_to_goal -= 360
        elif self.angle_to_goal < -180:
            self.angle_to_goal += 360

        # Update distance to next checkpoint
        x_diff = x_checkpoint - x_car
        y_diff = y_checkpoint - y_car
        distance = np.sqrt(x_diff*x_diff + y_diff*y_diff)
        self.distance_to_goal = distance



if __name__ == "__main__":
    try:
        raser = RaceCar()
        raser.run()
    except KeyboardInterrupt:
        raser.pos_sub.kill()
        sys.exit(1)