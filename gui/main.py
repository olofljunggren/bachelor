import pygame as pg
from utils import *
from definitions import *
import json
from screeninfo import get_monitors
import math
import time

from plot_tab import PlotTab
from standard_tab import StandardTab


pg.init()

def set_resolution():
    mon_stats = {}
    for monitor in get_monitors():
        monitor = str(monitor)[8:-1]
        new_mon_stats_list = monitor.split(',')
        new_mon_stats_dict = {}
        for stat in new_mon_stats_list:
            stat_components = stat.split('=')
            new_mon_stats_dict[stat_components[0].strip()] = stat_components[1].strip()
        if new_mon_stats_dict["is_primary"] == "True":
            mon_stats = new_mon_stats_dict
    if not mon_stats:
        mon_stats = new_mon_stats_dict

    return [int(1.00*float(mon_stats["width"])), int(0.92*float(mon_stats["height"]))]

SCREEN_SIZE = set_resolution()

FULL_SCREEN = True # Set to true for fullscreen mode

if FULL_SCREEN:
    SCREEN_WIDTH = SCREEN_SIZE[0]
    SCREEN_HEIGHT = SCREEN_SIZE[1]
else:
    SCREEN_WIDTH = 1500
    SCREEN_HEIGHT = 700

start_time = time.time()
error_list = []
time_list = []

TABS = []
TAB = 0
SCREEN = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
FRAMES_PER_SECOND = 20


class UserInterface:
    def __init__(self) -> None:
        self.standard_tab = StandardTab(SCREEN, SCREEN_WIDTH, SCREEN_HEIGHT, FRAMES_PER_SECOND)
        self.plot_tab = PlotTab(SCREEN, SCREEN_WIDTH, SCREEN_HEIGHT, FRAMES_PER_SECOND)
        self.standard_tab.plot_tab = self.plot_tab

        TABS.append(self.standard_tab)
        TABS.append(self.plot_tab)
        
        # General setup.
        pg.display.set_caption("Tävlingsbil")
        self.clock = pg.time.Clock()
        self.counter = 0
        self.last_sent_speed = 0
        self.steer_angle_to_display = 0

        self.update_freq_per_tab_freq_counter = 0


        #sub = subprocess.Popen(["python3", "./pos_test.py"], start_new_session=False)


    # Run the user interface
    def run(self):
        WARNING_THRESHOLD = 3 * FRAMES_PER_SECOND  # 3 seconds worth of frames.
        no_message_counter = 0

        SEND_THRESHOLD = 1.5 * FRAMES_PER_SECOND  # 1.5 seconds worth of frames.
        last_send_counter = 0

        while True:
            self.standard_tab.onEstablishedConnection()
            self.clock.tick(FRAMES_PER_SECOND)
            
            # Handles events for the currently active tab.
            for event in pg.event.get():
                TABS[TAB].handle_event(event)                
                self.handle_tab_switch(event)
            
            try:
                # Attempt to connect.
                if (check_connection(self.standard_tab.connection)):
                    last_send_counter += 1
                    if last_send_counter >= SEND_THRESHOLD:
                        send_message(self.standard_tab.connection, 'script_handle', "getRunningStatus")
                        last_send_counter = 0

                    message = get_latest_message(self.standard_tab.connection, 'running_scripts')
                    if message is None:
                        no_message_counter += 1
                    else:
                        no_message_counter = 0
                        for script in self.standard_tab.status_bool_list.keys():
                            self.standard_tab.status_bool_list[script] = False

                        message = json.loads(message)

                        for script in message:
                            self.standard_tab.status_bool_list[script] = True

                    if no_message_counter >= WARNING_THRESHOLD:
                        for script in self.standard_tab.status_bool_list.keys():
                            self.standard_tab.status_bool_list[script] = False
                        no_message_counter = 0
                    
                    # Get message from com_message
                    com_message = get_next_message(self.standard_tab.connection, 'com_message')
                    if com_message is not None:
                        self.standard_tab.popup_fields["aktivitet"].add_to_text_list(com_message)

                    cones = get_latest_message(self.standard_tab.connection, 'cone_position')
                    if cones is not None:
                        #print(cones)
                        self.standard_tab.list_of_cones = json.loads(cones)

                elif (self.standard_tab.connection["failed"]):
                    pass
                else:
                    self.standard_tab.connection["connection"], self.standard_tab.connection["failed"] = \
                    connect_to_server(self.standard_tab.connection["ip"])
            except Exception:
                pass

            # These functions should only be called when manual mode is active.
            if not self.standard_tab.autonomous: 
                self.standard_tab.handle_user_steering()
                self.send_speed_to_communication_module()
            else:
                self.standard_tab.handle_autonomous_driving()
            
            # General updates
            self.update_parameters()

            #if self.update_freq_per_tab_freq_counter > 50:
            #    TABS[TAB].update_and_draw()
            #    self.update_freq_per_tab_freq_counter = 0
            #self.update_freq_per_tab_freq_counter += 1
            TABS[TAB].update_and_draw()

            self.update_position_data()
            self.update_speed_data()
            if self.standard_tab.reset_manual_plot_data:
                self.reset_manual_plot_data()
            if self.standard_tab.reset_auto_plot_data:
                self.reset_auto_plot_data()

    # Check for mouse presses on either of the two tab buttons.
    def handle_tab_switch(self, event):
        global TAB
        if event.type == pg.MOUSEBUTTONDOWN:
            mouse_x = pg.mouse.get_pos()[0]
            mouse_y = pg.mouse.get_pos()[1]
            standard_tab_button = self.standard_tab.buttons["standard_tab"]
            plot_tab_button = self.standard_tab.buttons["plot_tab"]

            if mouse_x > standard_tab_button.x and mouse_x < standard_tab_button.x+standard_tab_button.width\
                        and mouse_y > standard_tab_button.y and mouse_y < standard_tab_button.y+standard_tab_button.height:
                TAB = 0
            elif mouse_x > plot_tab_button.x and mouse_x < plot_tab_button.x+plot_tab_button.width\
                        and mouse_y > plot_tab_button.y and mouse_y < plot_tab_button.y+plot_tab_button.height:
                TAB = 1

        keys = pg.key.get_pressed()        
        if keys[pg.K_TAB] and keys[pg.K_LCTRL]:
            TAB = int(not TAB)

    # Update all variable text fields.
    def update_parameters(self):

        if check_connection(self.standard_tab.connection):

            message = get_latest_message(self.standard_tab.connection, "checkpoint_data")
            
            if (not message is None) and (":" in message):
                if self.standard_tab.autonomous:
                    self.steer_angle_to_display = round(float(message.split(':')[0]),2)
                    self.steer_angle_to_display = ((self.steer_angle_to_display-self.standard_tab.min_steer)/(self.standard_tab.max_steer-self.standard_tab.min_steer))*90-45 
                else:
                    self.steer_angle_to_display = ((self.standard_tab.steer_angle_servo-self.standard_tab.min_steer)/(self.standard_tab.max_steer-self.standard_tab.min_steer))*90-45 
                self.standard_tab.distance_to_goal = int(float(message.split(':')[1]))
                self.standard_tab.angle_to_goal = round(float(message.split(':')[2]),2)
                
                if self.standard_tab.autonomous:
                    elapsed = (time.time()) - self.plot_tab.auto_angle_to_goal_data["start"]
                    self.plot_tab.auto_angle_to_goal_data["time"].append(elapsed)
                    self.plot_tab.auto_angle_to_goal_data["angle"].append(self.standard_tab.angle_to_goal)
                    #print(self.plot_tab.auto_angle_to_goal_data)
                    #print(self.plot_tab.auto_angle_to_goal_data)


        if not self.standard_tab.autonomous:
            speed_to_display = round(self.standard_tab.speed/1000, 2)
            self.standard_tab.text_fields["requested_vel"].text = f"Förfrågad hastighet: {speed_to_display} m/s"
        else: 
            speed_to_display = round(self.standard_tab.autonomous_speed/1000, 2)
            self.standard_tab.text_fields["requested_vel"].text = f"Förfrågad hastighet: {speed_to_display} m/s"
        odometer_speed_to_display = round(self.standard_tab.odometer_speed/1000, 2)
        self.standard_tab.text_fields["odometer_vel"].text = f"Odometerhastighet: {odometer_speed_to_display} m/s"
        self.standard_tab.text_fields["position"].text = f"Position: {(self.standard_tab.position[0],self.standard_tab.position[1])}"
        self.standard_tab.text_fields["orientation"].text = f"Orientering: {self.standard_tab.orientation}°"
        self.standard_tab.text_fields["steer_angle"].text = f"Styrriktning: {round(self.steer_angle_to_display,2)}°"
        self.standard_tab.text_fields["distance_checkpoint"].text = f"Avstånd till delmål: {round(self.standard_tab.distance_to_goal/1000, 2)} m"
        self.standard_tab.text_fields["angle_checkpoint"].text = f"Riktning till delmål: {self.standard_tab.angle_to_goal}°"

        if self.standard_tab.autonomous_countdown <= FRAMES_PER_SECOND*2:
            self.standard_tab.text_fields["autonomous_countdown"].text = "Start om 2"
        if self.standard_tab.autonomous_countdown <= FRAMES_PER_SECOND*1:
            self.standard_tab.text_fields["autonomous_countdown"].text = "Start om 1"
        if self.standard_tab.autonomous_countdown <= 0:
            self.standard_tab.text_fields["autonomous_countdown"].text = ""
        if check_connection(self.standard_tab.connection): 
            connection_text = "Ok!"
        else:
            connection_text = "Ingen"
        self.standard_tab.text_fields["status_connection"].text = f"Status uppkoppling: {connection_text}"

    # Send the requested speed to the Raspberry Pi.
    def send_speed_to_communication_module(self):
        if self.last_sent_speed != self.standard_tab.speed:
            message = f'{self.standard_tab.speed}'
            send_message(self.standard_tab.connection, "requested_speed", message)
            self.last_sent_speed = self.standard_tab.speed

    # Display the most recent car position and car orientation in the GUI.  
    def update_position_data(self):
        if check_connection(self.standard_tab.connection):
            message = get_latest_message(self.standard_tab.connection, "position_data")
            #print(message)
            if (not message is None) and (":" in message):
                x = int(message.split(':')[0])
                y = int(message.split(':')[1])
                angle = int(message.split(':')[2])

                elapsed = time.time() - self.standard_tab.time_since_rec
                if self.standard_tab.isRecording and not self.standard_tab.autonomous_driving_ready:
                    self.plot_tab.manual_orientation_data["time"].append(elapsed)
                    self.plot_tab.manual_orientation_data["orientation"].append(angle)

                self.standard_tab.position = (x, y)
                if self.standard_tab.isRecording or self.standard_tab.autonomous:
                    self.standard_tab.car_drawline_data.append((x, y))
                if len(self.standard_tab.car_drawline_data)==2:
                    self.standard_tab.car_drawline_data[0] = self.standard_tab.car_drawline_data[1]
                self.standard_tab.orientation = angle


    def reset_manual_plot_data(self):
        self.plot_tab.manual_speed_data["time"] = []
        self.plot_tab.manual_speed_data["speed"] = []
        self.plot_tab.manual_orientation_data["time"] = []
        self.plot_tab.manual_orientation_data["orientation"] = []
        self.plot_tab.latest_time_since_rec_str = time.localtime(self.standard_tab.time_since_rec)
        self.standard_tab.reset_manual_plot_data = False

    def reset_auto_plot_data(self):
        #self.plot_tab.auto_speed_data["time"] = []
        #self.plot_tab.auto_speed_data["speed"] = []
        #self.plot_tab.auto_orientation_data["time"] = []
        #self.plot_tab.auto_orientation_data["orientation"] = []

        self.plot_tab.auto_angle_to_goal_data["start"] = time.time()
        self.plot_tab.auto_angle_to_goal_data["time"] = []
        self.plot_tab.auto_angle_to_goal_data["angle"] = []

        #self.plot_tab.latest_time_since_rec_str = time.localtime(self.standard_tab.time_since_rec)
        self.standard_tab.reset_auto_plot_data = False

    # Display the most recently requested and obtained car speed in the GUI.  
    def update_speed_data(self):
        if check_connection(self.standard_tab.connection):
            message = get_latest_message(self.standard_tab.connection, "speed_data")
            if (not message is None) and (":" in message):
                self.standard_tab.odometer_speed = int(message.split(':')[0])

                elapsed = time.time() - self.standard_tab.time_since_rec
                if self.standard_tab.isRecording and not self.standard_tab.autonomous_driving_ready:
                    self.plot_tab.manual_speed_data["time"].append(elapsed)
                    self.plot_tab.manual_speed_data["speed"].append(self.standard_tab.odometer_speed)

                self.standard_tab.autonomous_speed = int(message.split(':')[1])
   
        

if __name__ == "__main__":
    user_interface = UserInterface()
    user_interface.run()