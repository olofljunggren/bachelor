import pygame as pg
import sys
from definitions import *
from button import Button
from input_field import InputField
from popup_field import PopupField
from text_field import TextField

import json
from utils import *

# Colors for buttons.
BUTTON_STANDARD_COLOR = (15, 107, 54)
BUTTON_PRESSED_COLOR = (0, 57, 4)
BUTTON_DISABLED_COLOR = (44, 44, 44)

# Font constants.
STANDARD_FONT = "Trebuchet MS"

# Control parameters for speed.
KP_speed = 10.0
KI_speed = 0.0
KD_speed = 0.0

# Control parameters for steering.
KP_steer = 15.0
KI_steer = 0.0
KD_steer = 0.5

# Misc.
IN_MUXEN = False

class StandardTab:
    def __init__(self, screen, screen_width, screen_height, fps) -> None:
        # Screen setup.
        global SCREEN, SCREEN_WIDTH, SCREEN_HEIGHT, FRAMES_PER_SECOND, FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE
        SCREEN = screen
        SCREEN_WIDTH = screen_width
        SCREEN_HEIGHT = screen_height
        FRAMES_PER_SECOND = fps
        FONT_SIZE_SMALL = int(0.008 * screen_width)
        FONT_SIZE_MEDIUM = int(0.018 * screen_width)
        FONT_SIZE_LARGE = int(0.05 * screen_width)

        # Reference to other instances.
        self.plot_tab = None

        # Flag setup.
        self.hasEstablishedInit = False

        # Limits for speed and steering control.
        self.max_speed = 4000  
        self.min_speed = 0
        self.min_steer = 275
        self.max_steer = 475

        # Recording parameters.
        self.time_since_rec = 0
        self.reset_manual_plot_data = False
        self.reset_auto_plot_data = False
        self.isRecording = False
        self.record_message = {
            "id": "",
            "action": ""
        }
        
        # Driving mode variables.
        self.autonomous_driving_ready = False
        self.autonomous_countdown = 3*FRAMES_PER_SECOND

        # Variables sent by the GUI and received by the car.
        self.speed = 0                      # Millimeters per second
        self.steer_angle_servo = 375        # Servo signal to motor, 375 is straight forward. 
        self.autonomous = False

        # Variables sent by the car and recieved by the GUI.
        self.position = (0, 0)              # Millimeters
        self.distance_to_goal = 0           # Millimeters
        self.orientation = 90               # Degrees
        self.angle_to_goal = 0              # Degrees
        self.odometer_speed = 0             # Millimeters per second
        self.autonomous_speed = 0           # Millimeters per second

        # Steering logic variables.
        self.acceleration_right = 1
        self.acceleration_left = 1
        self.acceleration_speed = 1
        self.retardation_speed = 1

        # Command input variables.
        self.previous_command_list = [">>> "]
        self.previous_command_index = 0
        self.copied_text = ">>> "

        # Map related setup.
        self.car_image = pg.image.load("./pictures/real_car_small.png").convert_alpha()
        self.cone_image = pg.image.load("./pictures/kon.png").convert_alpha()
        self.planned_path_draw_data = []
        self.car_drawline_data = []
        self.arena_width = 6000
        self.arena_height = 6000
        self.map_width = 0.4*SCREEN_WIDTH
        self.map_height = 0.45*SCREEN_HEIGHT
        SCREEN.fill((75, 105, 91)) # Background color

        self.list_of_cones = []

        # Section outlines setup.
        self.border_line_boundary_width = 2
        self.draw_section_outlines()

        # Button and fields setup.
        self.buttons = self.init_buttons()
        self.input_field = InputField(SCREEN, 0, 0.9074*SCREEN_HEIGHT, SCREEN_WIDTH, 0.0926*SCREEN_HEIGHT, (50, 70, 60), FONT_SIZE_SMALL, FRAMES_PER_SECOND)
        self.text_fields = self.init_text_fields()
        
        # Popup fields setups.
        self.popup_fields = {}
        self.popup_fields["successful_command"] = PopupField(SCREEN, SCREEN_WIDTH/4, 0.9074*SCREEN_HEIGHT, SCREEN_WIDTH/4, 0.0926*SCREEN_HEIGHT, (50, 70, 60), FONT_SIZE_SMALL, self.border_line_boundary_width, "Senast lyckade kommandon:")
        self.popup_fields["aktivitet"] = PopupField(SCREEN, SCREEN_WIDTH/2, 0.9074*SCREEN_HEIGHT, SCREEN_WIDTH/4, 0.0926*SCREEN_HEIGHT, (50, 70, 60), FONT_SIZE_SMALL, self.border_line_boundary_width, "Senaste aktiviteter:")
        self.popup_fields["error"] = PopupField(SCREEN, 3*SCREEN_WIDTH/4, 0.9074*SCREEN_HEIGHT, SCREEN_WIDTH/4, 0.0926*SCREEN_HEIGHT, (50, 70, 60), FONT_SIZE_SMALL, self.border_line_boundary_width, "Senaste felmeddelanden:")
        
        # Movement arrows setup.
        self.movement_button_list = []
        self.movement_button_list.append(pg.transform.scale(pg.image.load("./pictures/left_arrow.png"), (0.0625*SCREEN_WIDTH, 0.0741*SCREEN_HEIGHT)))
        self.movement_button_list.append(pg.transform.scale(pg.image.load("./pictures/up_arrow.png"), (0.0417*SCREEN_WIDTH, 0.111*SCREEN_HEIGHT)))
        self.movement_button_list.append(pg.transform.scale(pg.image.load("./pictures/right_arrow.png"), (0.0625*SCREEN_WIDTH, 0.0741*SCREEN_HEIGHT)))
        self.movement_button_list.append(pg.transform.scale(pg.image.load("./pictures/circle.png"), (0.03646*SCREEN_WIDTH, 0.06481*SCREEN_HEIGHT)))
        
        # Checkpoint setup.
        self.checkpoints = []

        # Connection setup.
        self.connection = {
            "ip": "192.168.0.25",
            "connection": False,
            "failed": False,
            "channels": {}
        }
        if IN_MUXEN:
            self.connection["ip"] = "192.168.5.5"
  
        # Script status setup.
        self.init_script_status_icons()
        self.status_bool_list =  {}
        for script in script_list:
            self.status_bool_list[script] = False 

        # Initialize correct button states.
        self.handle_button_logic()

    # Initialize text fields.
    def init_text_fields(self):
        text_fields = {}

        # PID parameters for speed and steer.
        text_fields["KP_speed"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.61*SCREEN_HEIGHT, f"KP speed: {KP_speed}", FONT_SIZE_SMALL)
        text_fields["KI_speed"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.65*SCREEN_HEIGHT, f"KI speed: {KI_speed}", FONT_SIZE_SMALL)
        text_fields["KD_speed"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.69*SCREEN_HEIGHT, f"KD speed: {KD_speed}", FONT_SIZE_SMALL)
        text_fields["KP_steer"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.77*SCREEN_HEIGHT, f"KP steer: {KP_steer}", FONT_SIZE_SMALL)
        text_fields["KI_steer"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.81*SCREEN_HEIGHT, f"KI steer: {KI_steer}", FONT_SIZE_SMALL)
        text_fields["KD_steer"] = TextField(SCREEN, 0.66*SCREEN_WIDTH, 0.85*SCREEN_HEIGHT, f"KD steer: {KD_steer}", FONT_SIZE_SMALL)

        # Position and movement related text fields.
        text_fields["mode"] = TextField(SCREEN, 0.01563*SCREEN_WIDTH, 0.6481*SCREEN_HEIGHT, "Läge: Manuell", FONT_SIZE_SMALL)
        text_fields["requested_vel"] = TextField(SCREEN, 0.01563*SCREEN_WIDTH, 0.7407*SCREEN_HEIGHT, "Förfrågad hastighet:", FONT_SIZE_SMALL)
        text_fields["odometer_vel"] = TextField(SCREEN, 0.01563*SCREEN_WIDTH, 0.6944*SCREEN_HEIGHT, "Odometerhastighet:", FONT_SIZE_SMALL)
        text_fields["position"] = TextField(SCREEN, 0.01563*SCREEN_WIDTH, 0.7870*SCREEN_HEIGHT, "Position:", FONT_SIZE_SMALL)
        text_fields["orientation"] = TextField(SCREEN, 0.01563*SCREEN_WIDTH, 0.8333*SCREEN_HEIGHT, "Orientering:", FONT_SIZE_SMALL)
        text_fields["steer_angle"] = TextField(SCREEN, 0.2031*SCREEN_WIDTH, 0.6944*SCREEN_HEIGHT, "Styrriktning:", FONT_SIZE_SMALL)
        text_fields["distance_checkpoint"] = TextField(SCREEN, 0.2031*SCREEN_WIDTH, 0.7407*SCREEN_HEIGHT, "Avstånd till delmål:", FONT_SIZE_SMALL)
        text_fields["angle_checkpoint"] = TextField(SCREEN, 0.2031*SCREEN_WIDTH, 0.7870*SCREEN_HEIGHT, "Riktning till delmål:", FONT_SIZE_SMALL)
        text_fields["status_connection"] = TextField(SCREEN, 0.2031*SCREEN_WIDTH, 0.8333*SCREEN_HEIGHT, "Status uppkoppling:", FONT_SIZE_SMALL)

        # Miscellaneous text fields.
        text_fields["ange_kommando"] = TextField(SCREEN, 0.003125*SCREEN_WIDTH, 0.9259*SCREEN_HEIGHT, "Ange kommando:", FONT_SIZE_SMALL)
        text_fields["status_skript"] = TextField(SCREEN, 0.8542*SCREEN_WIDTH, 0.6389*SCREEN_HEIGHT, "Status skript", FONT_SIZE_SMALL)
        text_fields["autonomous_countdown"] = TextField(SCREEN, 0.4*SCREEN_WIDTH, 0.4*SCREEN_HEIGHT, "", FONT_SIZE_LARGE)
        
        return text_fields

    # Initialize buttons.
    def init_buttons(self):
        buttons = {}

        button_height = 45*SCREEN_HEIGHT/1080
        buttons["standard_tab"] = Button(SCREEN, 0, 0, SCREEN_WIDTH/2, 0.0463*SCREEN_HEIGHT, BUTTON_PRESSED_COLOR, "Styrning", FONT_SIZE_MEDIUM, True)
        buttons["plot_tab"] = Button(SCREEN, SCREEN_WIDTH/2, 0, SCREEN_WIDTH/2, 0.0463*SCREEN_HEIGHT, BUTTON_STANDARD_COLOR, "Plottar", FONT_SIZE_MEDIUM, False)
        buttons["manual_mode"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.60*SCREEN_HEIGHT, 0.055*SCREEN_WIDTH, button_height, BUTTON_PRESSED_COLOR, "Manuell", FONT_SIZE_SMALL, True)
        buttons["auto_mode"] = Button(SCREEN, 0.529*SCREEN_WIDTH, 0.60*SCREEN_HEIGHT, 0.055*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Autonom", FONT_SIZE_SMALL, False)
        buttons["connect_raspberry"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.85*SCREEN_HEIGHT, 0.1146*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Koppla", FONT_SIZE_SMALL, False)
        buttons["bezier_mode"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.75*SCREEN_HEIGHT, 0.1146*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Bezierläge", FONT_SIZE_SMALL, False)
        buttons["map_cones"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.70*SCREEN_HEIGHT, 0.1146*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Kartläggning", FONT_SIZE_SMALL, False)
        buttons["record"] = Button(SCREEN, 0.529*SCREEN_WIDTH, 0.65*SCREEN_HEIGHT, 0.055*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Spela in", FONT_SIZE_SMALL, False)
        buttons["new_route"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.65*SCREEN_HEIGHT, 0.055*SCREEN_WIDTH, button_height, BUTTON_PRESSED_COLOR, "Kör ny rutt", FONT_SIZE_SMALL, True)
        buttons["start_autonomous"] = Button(SCREEN, 0.47*SCREEN_WIDTH, 0.80*SCREEN_HEIGHT, 0.1146*SCREEN_WIDTH, button_height, BUTTON_STANDARD_COLOR, "Starta autonom körning", FONT_SIZE_SMALL, False)
        buttons["start_autonomous"].is_disabled = True

        buttons["speed_1"] = Button(SCREEN, 0.75*SCREEN_WIDTH, 0.45*SCREEN_HEIGHT, 0.0417*SCREEN_WIDTH, button_height*1.5, BUTTON_STANDARD_COLOR, "1 m/s", FONT_SIZE_SMALL, False)
        buttons["speed_2"] = Button(SCREEN, 0.80*SCREEN_WIDTH, 0.45*SCREEN_HEIGHT, 0.0417*SCREEN_WIDTH, button_height*1.5, BUTTON_STANDARD_COLOR, "2 m/s", FONT_SIZE_SMALL, False)
        buttons["speed_3"] = Button(SCREEN, 0.85*SCREEN_WIDTH, 0.45*SCREEN_HEIGHT, 0.0417*SCREEN_WIDTH, button_height*1.5, BUTTON_STANDARD_COLOR, "3 m/s", FONT_SIZE_SMALL, False)

        # Script related buttons.
        start_position = 0.675
        spacing = 0.048
        for script in script_list:
            button_key = f'script_{script}'
            buttons[button_key] = Button(SCREEN, 0.805*SCREEN_WIDTH, start_position*SCREEN_HEIGHT, 80*SCREEN_WIDTH/1920, button_height, BUTTON_STANDARD_COLOR, "Starta", FONT_SIZE_SMALL, False)
            start_position += spacing

        return buttons

    # Initialize script related text fields and status icons. 
    def init_script_status_icons(self):
        start_position = 740
        for script in script_list:
            self.text_fields[script] = TextField(SCREEN, 0.8542*SCREEN_WIDTH, start_position*0.0009259*SCREEN_HEIGHT, script, FONT_SIZE_SMALL)
            start_position += 50

        # Mark status setup
        self.mark_dict = {}
        self.mark_size = (FONT_SIZE_SMALL, FONT_SIZE_SMALL)

        self.red_mark = pg.image.load("./pictures/red_mark.png").convert_alpha()
        self.green_mark = pg.image.load("./pictures/green_mark.png").convert_alpha()

        for script in script_list:
            self.mark_dict[script] = pg.transform.scale(self.red_mark, self.mark_size)

    # Send control parameters when connection has been established.
    def onEstablishedConnection(self):
        if not check_connection(self.connection) or self.hasEstablishedInit:
            return
        # Purge queues
        queues_to_purge = ["checkpoint_data", "speed_data", "com_message", "position_data"]
        for queue_name in queues_to_purge:
            purge_queue(self.connection, queue_name)

        # Set init PID param
        message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
        send_message(self.connection, "pid_queue", message)

        message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
        send_message(self.connection, "pid_queue", message)

        message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
        send_message(self.connection, "pid_queue", message)

        self.hasEstablishedInit = True
    
    # Handle user input related events.
    def handle_event(self, event):
        if (not self.connection["failed"]) and (not check_connection(self.connection)):
            self.connection["connection"], self.connection["failed"] = \
                connect_to_server(self.connection["ip"])
            if self.connection["failed"]:
                self.popup_fields["aktivitet"].add_to_text_list("Kunde inte ansluta till Pika servern")
            
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()
            
        self.handle_mouse_input(event)
        self.handle_keyboard_input(event)
        
    # Check for collisions between the mouse and all the buttons.
    def handle_mouse_input(self, event):
        if not event.type == pg.MOUSEBUTTONDOWN or not event.button == 1:
            return
        
        # Mouse position in the PyGame window.
        mouse_x = pg.mouse.get_pos()[0]
        mouse_y = pg.mouse.get_pos()[1]

        # Collision check, mouse vs buttons.
        for key in (self.buttons).keys():
            button = self.buttons[key]
            if mouse_x > button.x and mouse_x < button.x+button.width\
                and mouse_y > button.y and mouse_y < button.y+button.height:
                self.handle_button_pressed(key)

        # Collision check, mouse vs popup field
        for popup_field in self.popup_fields.values():
            if mouse_x > popup_field.x and mouse_x < popup_field.x+popup_field.width\
                and mouse_y > popup_field.y and mouse_y < popup_field.y+popup_field.height:
                popup_field.is_active = True
            else:
                popup_field.is_active = False

        # Collision check, mouse vs input field.
        if mouse_x > self.input_field.x and mouse_x < self.input_field.x+self.input_field.width/4\
                and mouse_y > self.input_field.y and mouse_y < self.input_field.y+self.input_field.height:
                self.input_field.field_is_active = True
                self.input_field.blinker_is_active = True
                self.input_field.blinker_index = len(self.input_field.current_text)
        else:
            self.input_field.field_is_active = False
        
        # Collision check, mouse vs movement buttons.
        if self.autonomous:
            return
        for index, move_button_img in enumerate(self.movement_button_list):
            if index == 0 and move_button_img.get_rect(topleft=(SCREEN_WIDTH*0.735, SCREEN_HEIGHT*0.3 )).collidepoint(mouse_x, mouse_y):
                self.previous_command_list.insert(1, f">>> move left {self.speed}")
                self.handle_commands("move left")
            elif index == 1 and move_button_img.get_rect(topleft=(SCREEN_WIDTH*0.802, SCREEN_HEIGHT*0.19)).collidepoint(mouse_x, mouse_y):
                self.previous_command_list.insert(1, f">>> move forward {self.speed}")
                self.handle_commands("move forward")
            elif index == 2 and move_button_img.get_rect(topleft=(SCREEN_WIDTH*0.845,  SCREEN_HEIGHT*0.3)).collidepoint(mouse_x, mouse_y):
                self.previous_command_list.insert(1, f">>> move right {self.speed}")
                self.handle_commands("move right")
            elif index == 3 and move_button_img.get_rect(topleft=(SCREEN_WIDTH*0.805,  SCREEN_HEIGHT*0.31)).collidepoint(mouse_x, mouse_y):
                self.previous_command_list.insert(1, ">>> move stop")
                self.handle_commands("move stop")

    # Handle keyboard input.
    def handle_keyboard_input(self, event):
        if not event.type == pg.KEYDOWN or not self.input_field.field_is_active:
            return
        # Backspace
        if event.key == pg.K_BACKSPACE and self.input_field.blinker_index > 4:
            self.input_field.current_text = self.input_field.current_text[:self.input_field.blinker_index-1]\
            + self.input_field.current_text[self.input_field.blinker_index:]
            self.input_field.blinker_index -= 1
        # Return
        elif event.key == pg.K_RETURN:
            if not self.input_field.current_text == ">>> ":
                self.previous_command_list.insert(1, self.input_field.current_text)
            self.handle_commands(self.input_field.current_text[4:])
            self.input_field.current_text = ">>> "
            self.previous_command_index = 0
            self.input_field.blinker_index = 4
        # Escape
        elif event.key == pg.K_ESCAPE:
            self.input_field.field_is_active = False
        # Up arrow key
        elif event.key == pg.K_UP:
            if self.previous_command_index < len(self.previous_command_list)-1:
                self.previous_command_index += 1
            self.input_field.current_text = self.previous_command_list[self.previous_command_index]
            self.input_field.blinker_index = len(self.input_field.current_text)
        # Down arrow key
        elif event.key == pg.K_DOWN:
            if self.previous_command_index > 0:
                self.previous_command_index -= 1
            self.input_field.current_text = self.previous_command_list[self.previous_command_index]
        # Left arrow key
        elif event.key == pg.K_LEFT and self.input_field.blinker_index > 4:
            self.input_field.blinker_index -= 1
        # Right arrow key
        elif event.key == pg.K_RIGHT and self.input_field.blinker_index < len(self.input_field.current_text):
            self.input_field.blinker_index += 1
        # Update blinker when appropriate.
        elif pg.Surface.get_width(self.input_field.text_surface) < self.input_field.width*1/4\
             and not (event.key == pg.KMOD_CTRL) and not (event.mod & pg.KMOD_CTRL) and not (event.key == pg.K_BACKSPACE):
            self.input_field.current_text = self.input_field.current_text[:self.input_field.blinker_index]\
            + event.unicode + self.input_field.current_text[self.input_field.blinker_index:]
            if event.unicode:
                self.input_field.blinker_index += 1

        self.handle_keyboard_special_input(event)

    # Handle special keyboard input for CTRL commands.
    def handle_keyboard_special_input(self, event):
        if not (event.mod & pg.KMOD_CTRL):
            return
        
        # Jump one word to the left (CTRL + LEFT ARROW).
        index_sum = 0
        if event.key == pg.K_LEFT:
            message_parts = self.input_field.current_text.split(" ")
            for message_part in message_parts:
                index_sum += len(message_part) + 1
                if index_sum > self.input_field.blinker_index:
                    index_sum -= len(message_part) + 2
                    break
            if index_sum < 4:
                self.input_field.blinker_index = 4
            else:
                self.input_field.blinker_index = index_sum
        
        # Jump one word to the right (CTRL + RIGHT ARROW).
        elif event.key == pg.K_RIGHT:
            message_parts = self.input_field.current_text.split(" ")
            for message_part in message_parts:
                index_sum += len(message_part) + 1
                if index_sum > self.input_field.blinker_index:
                    index_sum -= 1
                    break
            self.input_field.blinker_index = index_sum

        # Remove currently selected word (CTRL + BACKSPACE).
        elif event.key == pg.K_BACKSPACE:
            message_parts = self.input_field.current_text.split(" ")
            for message_part in message_parts:
                index_sum += len(message_part) + 1
                if index_sum > self.input_field.blinker_index:
                    index_sum -= len(message_part) + 2
                    break
            if index_sum < 4:
                index_sum = 4

            new_message = self.input_field.current_text[:index_sum] + self.input_field.current_text[self.input_field.blinker_index:]
            self.input_field.current_text = new_message
            self.input_field.blinker_index = index_sum

        # Copy from input field.
        elif event.key == pg.K_c:
            self.copied_text = self.input_field.current_text

        # Paste copied text into input field.
        elif event.key == pg.K_v:
            self.input_field.current_text = self.copied_text
            self.input_field.blinker_index = len(self.input_field.current_text)
    
    # Keyboard input check for car steering.
    def handle_user_steering(self):
        if self.input_field.field_is_active:
            return
        
        # Increase speed with W or UP ARROW.
        keys = pg.key.get_pressed()
        if keys[pg.K_UP] or keys[pg.K_w]:
            self.speed += int(10*self.acceleration_speed)
            self.acceleration_speed *= 1.3
            self.handle_button_logic()
            if self.speed > self.max_speed:
                    self.speed = self.max_speed
        else:
            self.acceleration_speed = 1

        # Decrease speed with S or DOWN ARROW.
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            self.speed -= int(10*self.retardation_speed)
            self.retardation_speed *= 1.3
            self.handle_button_logic()
            if self.speed < self.min_speed:
                self.speed = self.min_speed
        else:
            self.retardation_speed = 1

        # Steer to the left with A or LEFT ARROW.
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.steer_angle_servo -= 20*self.acceleration_left
            self.acceleration_left *= 1.1
            if self.steer_angle_servo < self.min_steer:
                self.steer_angle_servo = self.min_steer
            
            hex_angle = hex(int(self.steer_angle_servo))
            first_byte, second_byte = self.convert_int_to_two_bytes(hex_angle)

            message = f'[0x12, {first_byte}, {second_byte}]'
            send_message(self.connection, "send_spi", message)
        else:
            self.acceleration_left = 1

        # Steer straight forward with E.          
        if keys[pg.K_e]:
            self.steer_angle_servo = (self.min_steer+self.max_steer)/2+15
            hex_angle = hex(int(self.steer_angle_servo))
            first_byte, second_byte = self.convert_int_to_two_bytes(hex_angle)

            message = f'[0x12, {first_byte}, {second_byte}]'
            send_message(self.connection, "send_spi", message)

        # Steer to the right with D or RIGHT ARROW.
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.steer_angle_servo += 20*self.acceleration_right
            self.acceleration_right *= 1.1
            if self.steer_angle_servo > self.max_steer:
                self.steer_angle_servo = self.max_steer
            
            hex_angle = hex(int(self.steer_angle_servo))

            first_byte, second_byte = self.convert_int_to_two_bytes(hex_angle)

            message = f'[0x12, {first_byte}, {second_byte}]'
            send_message(self.connection, "send_spi", message)
        else:
            self.acceleration_right = 1

        # Stop the car immediately with SPACE.
        if keys[pg.K_SPACE]:
            self.speed = 0
            self.handle_button_logic()
            message = f'[0xf0]'
            send_message(self.connection, "send_spi", message)
        
        self.quickchange_pid(keys)          

    # Update the speed and steer control parameters using U, I, O and J, K, L.
    def quickchange_pid(self, keys):
        global KP_speed, KI_speed, KD_speed, KP_steer, KI_steer, KD_steer 

        increase_KP_speed = keys[pg.K_u]
        increase_KI_speed = keys[pg.K_i]
        increase_KD_speed = keys[pg.K_o]

        decrease_KP_speed = keys[pg.K_j]
        decrease_KI_speed = keys[pg.K_k]
        decrease_KD_speed = keys[pg.K_l]

        increase_KP_steer = keys[pg.K_r]
        increase_KI_steer = keys[pg.K_t]
        increase_KD_steer = keys[pg.K_y]

        decrease_KP_steer = keys[pg.K_f]
        decrease_KI_steer = keys[pg.K_g]
        decrease_KD_steer = keys[pg.K_h]
        
        # Press U to increase KP_speed.
        if increase_KP_speed:
            KP_speed += 1
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press J to decrease KP_speed.
        elif decrease_KP_speed:
            KP_speed -= 1
            if KP_speed < 0:
                KP_speed = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)

        # Press I to increase KI_speed.
        if increase_KI_speed:
            KI_speed += 0.02
            KI_speed = round(KI_speed, 2)
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press K to decrease KI_speed.
        elif decrease_KI_speed:
            KI_speed -= 0.02
            KI_speed = round(KI_speed, 2)
            if KI_speed < 0:
                KI_speed = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        
        # Press O to increase KD_speed.
        if increase_KD_speed:
            KD_speed += 0.02
            KD_speed = round(KD_speed, 2)
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press L to decrease KD_speed.
        elif decrease_KD_speed:
            KD_speed -= 0.02
            KD_speed = round(KD_speed, 2)
            if KD_speed < 0:
                KD_speed = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        
         # Press R to increase KP_steer.
        if increase_KP_steer:
            KP_steer += 0.1
            KP_steer = round(KP_steer, 2)
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press F to decrease KP_steer.
        elif decrease_KP_steer:
            KP_steer -= 0.1
            KP_steer = round(KP_steer, 2)
            if KP_steer < 0:
                KP_steer = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)

        # Press T to increase KI_steer.
        if increase_KI_steer:
            KI_steer += 0.02
            KI_steer = round(KI_steer, 2)
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press G to decrease KI_steer.
        elif decrease_KI_steer:
            KI_steer -= 0.02
            KI_steer = round(KI_steer, 2)
            if KI_steer < 0:
                KI_steer = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        
        # Press Y to increase KD_steer.
        if increase_KD_steer:
            KD_steer += 0.02
            KD_steer = round(KD_steer, 2)
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)
        # Press H to decrease KD_steer.
        elif decrease_KD_steer:
            KD_steer -= 0.02
            KD_steer = round(KD_steer, 2)
            if KD_steer < 0:
                KD_steer = 0.0
            message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
            send_message(self.connection, "pid_queue", message)

        # Update text fields with new control parameter values.
        self.text_fields["KP_speed"].text = f"KP speed: {KP_speed}"
        self.text_fields["KI_speed"].text = f"KI speed: {KI_speed}"
        self.text_fields["KD_speed"].text = f"KD speed: {KD_speed}"

        self.text_fields["KP_steer"].text = f"KP steer: {KP_steer}"
        self.text_fields["KI_steer"].text = f"KI steer: {KI_steer}"
        self.text_fields["KD_steer"].text = f"KD steer: {KD_steer}" 

    # Convert data into format suitable for transfer.
    def convert_int_to_two_bytes(self, data):
        first_byte = "0x00"
        second_byte = "0x00"
        
        if int(data,16) > 32767:
            return

        value = data.split('x')[1]

        if len(value) >= 1:
            first_byte = "0x0" + value[-1]
        if len(value) >= 2:
            first_byte = "0x" + value[-2] + value[-1]
        if len(value) >= 3:
            second_byte = "0x0" + value[-3] 
        if len(value) >= 4:
            second_byte = "0x" + value[-4] + value[-3]
        if data[0] == '-':
            second_byte = second_byte[2] + second_byte[3]
            second_byte = hex(int(second_byte,16)+128)

        return first_byte, second_byte

    # Automatic car control logic. 
    def handle_autonomous_driving(self):

        # Starting conditions for the autonomous mode.
        if not self.autonomous_driving_ready:
            return
                    

        if self.autonomous_countdown >= -30:
            self.autonomous_countdown -= 1
            
        # Car ready for autonomous driving check.
        if self.autonomous_countdown == 0:
            send_message(self.connection, "mode_queue", "autonomous")
        
        # Load checkpoints after a given time.
        if self.autonomous_countdown == -30:
            message = get_latest_message(self.connection, "checkpoints")
            if message is not None:
                self.checkpoints = json.loads(message)
                print("Checkpoints incoming: ", self.checkpoints)
            return

    # Handle interface buttons being pressed.
    def handle_button_pressed(self, key):
        
        # Manual car mode button logic.
        if key == "manual_mode" and not self.buttons["manual_mode"].is_active:
            self.buttons["manual_mode"].is_active = True
            self.buttons["auto_mode"].is_active = False
            self.text_fields["mode"].text = "Läge: Manuell"
            self.autonomous_driving_ready = False
            self.autonomous = False
            self.popup_fields["successful_command"].add_to_text_list("mode manuell")
            self.autonomous_countdown = 0
            self.buttons["speed_1"].is_active = False
            self.buttons["speed_2"].is_active = False
            self.buttons["speed_3"].is_active = False
            self.speed = 0
            self.handle_button_logic()
            self.planned_path_draw_data = []
            self.car_drawline_data = []
            self.checkpoints = []
            self.list_of_cones = []
            send_message(self.connection, "mode_queue", "manual")
            
            print("Switched to manual mode")

        # Automatic car mode button logic.
        elif key == "auto_mode" and not self.buttons["auto_mode"].is_active:
            self.buttons["auto_mode"].is_active = True
            self.buttons["manual_mode"].is_active = False
            self.text_fields["mode"].text = "Läge: Autonom"
            self.autonomous = True
            self.reset_auto_plot_data = True
            self.autonomous_countdown = FRAMES_PER_SECOND*3
            self.planned_path_draw_data = self.car_drawline_data
            self.car_drawline_data = []
            self.popup_fields["successful_command"].add_to_text_list("mode autonom")

            self.handle_button_logic()
            print("Switched to autonomous mode")

        # Calculate route button logic.
        elif key == "bezier_mode" and not self.buttons["bezier_mode"].is_disabled:
            self.buttons["bezier_mode"].is_active = not self.buttons["bezier_mode"].is_active
            if self.buttons["bezier_mode"].is_active:
                send_message(self.connection, "mode_queue", "activateBezier")
                self.popup_fields["aktivitet"].add_to_text_list("Aktiverar Bézierläge")
            else:
                send_message(self.connection, "mode_queue", "deactivateBezier")
                self.popup_fields["aktivitet"].add_to_text_list("Deaktiverar Bézierläge")

        # Connect to Raspberry Pi button logic.
        elif key == "connect_raspberry":
            self.connection["connection"], self.connection["failed"] = connect_to_server(self.connection["ip"])
            if not self.connection["connection"]:
                self.popup_fields["aktivitet"].add_to_text_list("Kunde inte ansluta till servern")
        
        # Mapping button logic.
        elif key == "map_cones" and not self.buttons["map_cones"].is_disabled:
            send_message(self.connection, "script_handle", "mapCones")

        # Record button logic.
        elif key == "record" and not self.buttons["record"].is_disabled:

            self.buttons["record"].is_active = not self.buttons["record"].is_active

            if self.buttons["record"].is_active:
                self.buttons["record"].text = "Sluta spela in"

                self.isRecording = True
                self.time_since_rec = time.time()
                self.reset_manual_plot_data = True

                self.record_message["id"] = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(self.time_since_rec))
                self.record_message["action"] = "start"

                send_message(self.connection, "lidar_capture", json.dumps(self.record_message))
                send_message(self.connection, "pos_capture", json.dumps(self.record_message))
                send_message(self.connection, "path_capture", "start_recording")
                
            else:
                self.buttons["record"].text = "Spela in"

                self.isRecording = False
                self.record_message["action"] = "stop"

                send_message(self.connection, "lidar_capture", json.dumps(self.record_message))
                send_message(self.connection, "pos_capture", json.dumps(self.record_message))
                send_message(self.connection, "path_capture", "stop_recording")

        # Map saving button logic.
        elif key == "new_route" and not self.buttons["new_route"].is_disabled:
            self.buttons["new_route"].is_active = not self.buttons["new_route"].is_active
            if self.buttons["new_route"].is_active:
                send_message(self.connection, "mode_queue", "newRoute")
            else:
                send_message(self.connection, "mode_queue", "previousRoute")

        # Start position defining button logic.
        elif key == "start_autonomous" and not self.buttons["start_autonomous"].is_disabled:
            self.popup_fields["aktivitet"].add_to_text_list("Startar autonom körning")
            self.autonomous_driving_ready = True
            self.autonomous_countdown = FRAMES_PER_SECOND*3
            self.text_fields["autonomous_countdown"].text = "Start om 3"


        # Start control script button logic.
        elif key == "script_Control":
            print(self.status_bool_list)
            if not self.status_bool_list["Control"]:
                port = 22  # Default SSH port, change if needed.
                username = "admin"
                password = "kingkong"
                remote_file_path = "/home/admin/Dokument/communication-module/control.py"

                directory = "/home/admin/Dokument/communication-module"
                file_name = "control.py"

                ssh_client = ssh_connect(self.connection["ip"], port, username, password)

                if ssh_client:
                    open_remote_python_file(ssh_client, directory, file_name)
                    ssh_client.close()
            else:
                send_message(self.connection, "script_handle", "exit")

        # Start spi_com script button logic.
        elif key == "script_spi_com" and not self.buttons["script_spi_com"].is_disabled:
            if self.status_bool_list["spi_com"]:
                send_message(self.connection, "script_handle", "spi_com:off")
            else:
                send_message(self.connection, "script_handle", "spi_com:on")

        # Start main script button logic.
        elif key == "script_main" and not self.buttons["script_main"].is_disabled:
            if self.status_bool_list["main"]:
                send_message(self.connection, "script_handle", "main:off")
            else:
                send_message(self.connection, "script_handle", "main:on")

        # Driving speed buttons logic.
        if self.buttons["speed_1"].is_disabled:
            return
        for i in range(1, 4):
            if key == "speed_1" or key == "speed_2" or key == "speed_3":
                self.buttons[f"speed_{i}"].is_active = False
            if key == f"speed_{i}" and not self.autonomous and not self.buttons[f"speed_{i}"].is_active:
                self.buttons[f"speed_{i}"].is_active = True
                self.speed = 1000*i
                self.handle_button_logic()

    # Handle all GUI input commands.
    def handle_commands(self, command):
        command_was_valid = self.handle_assign_command(command) or\
                            self.handle_move_command(command) or\
                            self.handle_send_command(command) or\
                            self.handle_clear_command(command) or\
                            self.handle_mode_command(command) or\
                            self.handle_save_command(command)
        if not command_was_valid:
            # Command was unsuccesful
            print(f"Unknown command: \"{self.input_field.current_text[4:]}\"")
            self.popup_fields["error"].add_to_text_list(f"Error: \"{self.input_field.current_text[4:]}\"")
        elif not command[:5] == "clear":
            self.popup_fields["successful_command"].add_to_text_list(command)

        return command_was_valid
    
    # Handle save command logic.
    def handle_save_command(self, command):
        command_was_valid = False
        if command.split(" ")[0].lower() == "save":
            tokens = command.split(" ")
            if len(tokens) == 2:
                if command.split(" ")[1].lower() == "speed":
                    self.plot_tab.save_data(["speed"])
                if command.split(" ")[1].lower() == "orientation":
                    self.plot_tab.save_data(["orientation"])
                if command.split(" ")[1].lower() == "angle":
                    self.plot_tab.save_data(["auto_angle"])
                if command.split(" ")[1].lower() == "all":
                    self.plot_tab.save_data(["speed", "orientation", "auto_angle"])
                command_was_valid = True
        return command_was_valid
    
    # Handle send command logic.
    def handle_send_command(self, command):
        command_was_valid = False
        if command.split(" ")[0].lower() == "send":
            tokens = command.split(" ")
            if len(tokens) == 4:
                send_message(self.connection, tokens[3], tokens[1])
                command_was_valid = True
        return command_was_valid

    # Handle assign command logic.
    def handle_assign_command(self, command):
        global KP_speed, KI_speed, KD_speed, KP_steer, KI_steer, KD_steer
        command_parts = command.split(" ")
        command_was_valid = False
        if not len(command_parts) == 3 or not command.split(" ")[0].lower() == "assign":
            return False

        # Assign value to KP_speed logic.
        if command.split(" ")[1].lower() == "speed_kp" or command.split(" ")[1].lower() == "kp_speed" \
            or command.split(" ")[1].lower() == "kp0":
            try:
                KP_speed = float(command.split(" ")[2])
                print(f"K_P was successfully assigned {KP_speed}")
                self.text_fields["KP_speed"].text = f"KP speed: {KP_speed}"
                command_was_valid = True

                message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)

            except:
                print("Invalid argument")
        
        # Assign value to KI_speed logic.
        elif command.split(" ")[1].lower() == "speed_ki" or command.split(" ")[1].lower() == "ki_speed" \
            or command.split(" ")[1].lower() == "ki0":
            try:
                KI_speed = float(command.split(" ")[2])
                print(f"K_I was successfully assigned {KI_speed}")
                self.text_fields["KI_speed"].text = f"KI speed: {KI_speed}"
                command_was_valid = True

                message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)
            except:
                print("Invalid argument")

        # Assign value to KD_speed logic.
        elif command.split(" ")[1].lower() == "speed_kd" or command.split(" ")[1].lower() == "kd_speed" \
            or command.split(" ")[1].lower() == "kd0":
            try:
                KD_speed = float(command.split(" ")[2])
                print(f"K_D was successfully assigned {KD_speed}")
                self.text_fields["KD_speed"].text = f"KD speed: {KD_speed}"
                command_was_valid = True

                message = f'{KP_speed}:{KI_speed}:{KD_speed}:{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)
            except:
                print("Invalid argument")

        # Assign value to KP_steer logic.
        elif command.split(" ")[1].lower() == "steer_kp" or command.split(" ")[1].lower() == "kp_steer" \
            or command.split(" ")[1].lower() == "kp1":
            try:
                KP_steer = float(command.split(" ")[2])
                print(f"K_P was successfully assigned {KP_steer}")
                self.text_fields["KP_steer"].text = f"KP steer: {KP_steer}"
                command_was_valid = True

                message = f'{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)

            except:
                print("Invalid argument")
        
        # Assign value to KI_steer logic.
        elif command.split(" ")[1].lower() == "steer_ki" or command.split(" ")[1].lower() == "ki_steer" \
            or command.split(" ")[1].lower() == "ki1":
            try:
                KI_steer = float(command.split(" ")[2])
                print(f"K_I was successfully assigned {KI_steer}")
                self.text_fields["KI_steer"].text = f"KI steer: {KI_steer}"
                command_was_valid = True

                message = f'{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)
            except:
                print("Invalid argument")

        # Assign value to KD_steer logic.
        elif command.split(" ")[1].lower() == "steer_kd" or command.split(" ")[1].lower() == "kd_steer" \
            or command.split(" ")[1].lower() == "kd1":
            try:
                KD_steer = float(command.split(" ")[2])
                print(f"K_D was successfully assigned {KD_steer}")
                self.text_fields["KD_steer"].text = f"KD steer: {KD_steer}"
                command_was_valid = True

                message = f'{KP_steer}:{KI_steer}:{KD_steer}'
                send_message(self.connection, "pid_queue", message)
            except:
                print("Invalid argument")
        else:
            print("Unknown command")
        return command_was_valid

    # Handles the move command logic.
    def handle_move_command(self, command):
        command_parts = command.split(" ")
        command_was_valid = False
        if not len(command_parts) == 2 or not command_parts[0].lower() == "move":
            return False

        # Steer left.
        if command_parts[1].lower() == "left":
            self.steer_angle_servo -= 1
            if self.steer_angle_servo < self.min_steer:
                self.steer_angle_servo = self.min_steer

            message = f'[0x11, {hex(self.steer_angle_servo)}]'
            send_message(self.connection, "send_spi", message)
            command_was_valid = True

        # Steer right.
        if command_parts[1].lower() == "right":
            self.steer_angle_servo += 1
            if self.steer_angle_servo > self.max_steer:
                self.steer_angle_servo = self.max_steer

            message = f'[0x11, {hex(self.steer_angle_servo)}]'
            send_message(self.connection, "send_spi", message)
            command_was_valid = True

        # Accelerate forward.
        if command_parts[1].lower() == "forward":
            self.speed += 50
            self.handle_button_logic()

            if self.speed > self.max_speed:
                self.speed = self.max_speed
            command_was_valid = True


        # Stop fully.
        if command_parts[1].lower() == "stop":
            self.speed = 0
            self.handle_button_logic()

            command_was_valid = True

        return command_was_valid

    # Handle clear command.
    def handle_clear_command(self, command):
        if command.lower().strip() == "clear":
            self.previous_command_list = [">>> "]
            self.input_field.current_text = ">>> "
            self.popup_fields["error"].list_of_texts = self.popup_fields["error"].list_of_texts[:1]
            self.popup_fields["error"].add_to_text_list("")
            self.popup_fields["error"].num_rows_to_display_mimized = 1
            self.popup_fields["aktivitet"].list_of_texts = self.popup_fields["aktivitet"].list_of_texts[:1]
            self.popup_fields["aktivitet"].add_to_text_list("")
            self.popup_fields["aktivitet"].num_rows_to_display_mimized = 1
            self.popup_fields["successful_command"].list_of_texts = self.popup_fields["successful_command"].list_of_texts[:1]
            self.popup_fields["successful_command"].add_to_text_list("")
            self.popup_fields["successful_command"].num_rows_to_display_mimized = 1
            return True

    # Handle command to switch between manual and automatic driving mode.
    def handle_mode_command(self, command):
        if not len(command.split(" ")) == 2 or not command.split(" ")[0].lower() == "mode":
            return
        second_part = command.split(" ")[1].lower()

        if second_part == "normal" or second_part == "vanlig" or \
                second_part == "manuell" or second_part == "manual" or\
                second_part == "0":
            self.handle_button_pressed("manual_mode")
            return True
        
        elif second_part == "auto" or second_part == "autonomous" or \
            second_part == "autonom" or second_part == "1":
            self.handle_button_pressed("auto_mode")
            return True

    # Update button colors according to their states.
    def handle_button_logic(self):
        # Speed logic button color

        if self.autonomous:
            self.buttons["speed_1"].is_disabled             = True
            self.buttons["speed_2"].is_disabled             = True
            self.buttons["speed_3"].is_disabled             = True
            self.buttons["new_route"].is_disabled           = True
            self.buttons["record"].is_disabled              = True
            self.buttons["map_cones"].is_disabled           = True
            self.buttons["bezier_mode"].is_disabled         = True
            self.buttons["start_autonomous"].is_disabled    = False

        else:
            self.buttons["speed_1"].is_disabled             = False
            self.buttons["speed_2"].is_disabled             = False
            self.buttons["speed_3"].is_disabled             = False
            self.buttons["new_route"].is_disabled           = False
            self.buttons["record"].is_disabled              = False
            self.buttons["map_cones"].is_disabled           = False
            self.buttons["bezier_mode"].is_disabled         = False
            self.buttons["start_autonomous"].is_disabled    = True


        for i in range(1, 4):
            key = f"speed_{i}"
            if self.speed == i*1000:
                self.buttons[key].is_active = True
            else:
                self.buttons[key].is_active = False


    # Update and draw all elements in the standard tab.       
    def update_and_draw(self):
        # Script status button color
        for index, script in enumerate(self.status_bool_list.keys()):
            key = f'script_{script}'
            if self.status_bool_list[script]:
                self.buttons[key].is_active = True
                self.buttons[key].text = "Stoppa"
            else:
                self.buttons[key].text = "Starta"
                self.buttons[key].is_active = False

        # Draw background rectangles
        pg.draw.rect(SCREEN, (75, 105, 91), (0, 0.58*SCREEN_HEIGHT, 5/8*SCREEN_WIDTH, 0.2778*SCREEN_HEIGHT), 0)
        pg.draw.rect(SCREEN, (75, 105, 91), (5/8*SCREEN_WIDTH, 0.04630*SCREEN_HEIGHT, 3/8*SCREEN_WIDTH, 0.8611*SCREEN_HEIGHT), 0)

        # Draw command window
        self.draw_map()
        self.input_field.update_blinker()
        self.input_field.draw_input_field_and_blinker()

        # Draw buttons
        for button in self.buttons.values():
            button.draw_button()
        
        # Draw lines between sections
        self.draw_section_outlines()

        # Draw text fields
        for text_field in self.text_fields.values():
            text_field.draw_text_field()

        # Draw movement buttons
        for index, button in enumerate(self.movement_button_list):
            if index == 0:
                SCREEN.blit(button, (SCREEN_WIDTH*0.735, SCREEN_HEIGHT*0.3 ))
            elif index == 1:
                SCREEN.blit(button, (SCREEN_WIDTH*0.802, SCREEN_HEIGHT*0.19))
            elif index == 2:
                SCREEN.blit(button, (SCREEN_WIDTH*0.845,  SCREEN_HEIGHT*0.3))
            elif index == 3:
                SCREEN.blit(button, (SCREEN_WIDTH*0.805,  SCREEN_HEIGHT*0.31))

        # Script status icons.
        for index, script in enumerate(self.mark_dict.keys()):
            if self.status_bool_list[script]:
                self.mark_dict[script] = pg.transform.scale(self.green_mark, self.mark_size)
            else:
                self.mark_dict[script] = pg.transform.scale(self.red_mark, self.mark_size)
            SCREEN.blit(self.mark_dict[script], (0.96*SCREEN_WIDTH, (0.6852+0.0463*index)*SCREEN_HEIGHT))
        
        if self.status_bool_list["Control"]:
            self.buttons["script_spi_com"].is_disabled  = False
            self.buttons["script_main"].is_disabled     = False
        else:
            self.buttons["script_spi_com"].is_disabled  = True
            self.buttons["script_main"].is_disabled     = True

        # Draw popup fields
        for popup_field in self.popup_fields.values():
            popup_field.draw_popup_field()

        # Update screen
        pg.display.update()

    # Draw section outlines to separate different areas.
    def draw_section_outlines(self):
        boundary_color = (30, 30, 30)
        pg.draw.line(SCREEN, boundary_color, (SCREEN_WIDTH*5/8, 0.0463*SCREEN_HEIGHT), (SCREEN_WIDTH*5/8, 0.9074*SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (0, 0.9074*SCREEN_HEIGHT), (SCREEN_WIDTH, 0.9074*SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (0, 0.58*SCREEN_HEIGHT), (SCREEN_WIDTH,  0.58*SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (0.4323*SCREEN_WIDTH, 0.58*SCREEN_HEIGHT), (0.4323*SCREEN_WIDTH, 0.9074*SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (0.7813*SCREEN_WIDTH, 0.58*SCREEN_HEIGHT), (0.7813*SCREEN_WIDTH, 0.9074*SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (SCREEN_WIDTH/4, 0.9074*SCREEN_HEIGHT), (SCREEN_WIDTH/4, SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (2*SCREEN_WIDTH/4, 0.9074*SCREEN_HEIGHT), (2*SCREEN_WIDTH/4, SCREEN_HEIGHT), self.border_line_boundary_width)
        pg.draw.line(SCREEN, boundary_color, (3*SCREEN_WIDTH/4, 0.9074*SCREEN_HEIGHT), (3*SCREEN_WIDTH/4, SCREEN_HEIGHT), self.border_line_boundary_width)

    # Draw the car, traveled path and identified cones on the screen.
    def draw_map(self):
        # Redraw background color.
        pg.draw.rect(SCREEN, (75, 105, 91), (0, 0.0463*SCREEN_HEIGHT, SCREEN_WIDTH, 0.862*SCREEN_HEIGHT))
        
        # Update cone positions
            
        # Draw cone positions
        for cone_list in self.list_of_cones:
            cone_pos_first = cone_list[0]["position"]
            cone_radius_first = cone_list[0]["radius"]
            cone_pos_second = None 
            cone_radius_second = None
            if len(cone_list) >= 2:
                cone_pos_second = cone_list[1]["position"]
                cone_radius_second = cone_list[1]["radius"]

            if (cone_pos_second is not None) and (cone_radius_second is not None):
                transformed_second_cone_pos = self.transform_coordinates(cone_pos_second) 
                transformed_first_cone_pos = self.transform_coordinates(cone_pos_first) 
                pg.draw.line(SCREEN, (0, 0, 0), transformed_first_cone_pos, transformed_second_cone_pos, 2)
                
                self.draw_cones(cone_pos_second, cone_radius_second)
            
            self.draw_cones(cone_pos_first, cone_radius_first)


        #if self.buttons["bezier_mode"].is_active:
        message = get_latest_message(self.connection, "bezier_route")
        if message is not None:
            self.planned_path_draw_data = json.loads(message)

        # Draw the traveled path.        
        if self.autonomous:
            self.draw_lines(self.planned_path_draw_data, (200, 50, 50))

        self.draw_lines(self.car_drawline_data, (0, 0, 0))
        
        # Draw the car
        car_image = pg.transform.scale(self.car_image, (30, 647/480*30))
        rotated_car_image = pg.transform.rotate(car_image, (self.orientation-90))
        map_position = self.transform_coordinates(self.position)
        new_rect = rotated_car_image.get_rect(center = car_image.get_rect(topleft = (map_position[0]-14, map_position[1]-18)).center)
        SCREEN.blit(rotated_car_image, new_rect)

        self.draw_checkpoints()

    # Draw the checkpoints on the map.
    def draw_checkpoints(self):
        for checkpoint in self.checkpoints:
            transformed_checkpoint_coords = self.transform_coordinates(checkpoint)
            pg.draw.circle(SCREEN, (200, 200, 50), transformed_checkpoint_coords, 7, 2)
        
    # Draw the cones on the map.
    def draw_cones(self, cone_pos, cone_radius):
        map_position = self.transform_coordinates(cone_pos)
        cone_surface = pg.transform.scale(self.cone_image, \
            (cone_radius/self.arena_width*self.map_width, cone_radius/self.arena_width*self.map_width))
        cone_width = pg.Surface.get_width(cone_surface)
        SCREEN.blit(cone_surface, (map_position[0]-cone_width/2, map_position[1]-cone_width/2))

    # Draw the lines on the map.
    def draw_lines(self, path_list, color):
        draw_list = []
        for pos in path_list:
            draw_list.append(self.transform_coordinates(pos))
        for idx, planned_pos in enumerate(draw_list):
            if idx < len(draw_list) - 1:
                pg.draw.line(SCREEN, color, planned_pos, draw_list[idx+1], 2)
        
    # Transform global coordinates to map coordinates in the GUI.
    def transform_coordinates(self, measured_position):
        # Constants for transforming coordinates

        map_translation_width = 0.2995*SCREEN_WIDTH
        map_translation_height = 0.3148*SCREEN_HEIGHT

        measured_x = measured_position[0]
        measured_y = -measured_position[1]

        # Transforming coordinates
        map_x = measured_x / self.arena_width / 2 * self.map_width + map_translation_width
        map_y = measured_y / self.arena_height / 2 * self.map_height + map_translation_height
        return (map_x, map_y)