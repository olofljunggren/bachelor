import pygame as pg
import numpy as np
import pylab
import sys
import csv
import os
import time

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.backends.backend_agg as agg
import random
from button import Button

matplotlib.use("Agg")

# Colors for buttons
BUTTON_STANDARD_COLOR = (15, 107, 54)
BUTTON_PRESSED_COLOR = (0, 57, 4)

STANDARD_FONT = "Trebuchet MS"

class PlotTab:
    def __init__(self, screen, screen_width, screen_height, fps) -> None:
        global SCREEN, SCREEN_WIDTH, SCREEN_HEIGHT, FRAMES_PER_SECOND, FONT_SIZE_MEDIUM
        SCREEN = screen
        SCREEN_WIDTH = screen_width
        SCREEN_HEIGHT = screen_height
        FRAMES_PER_SECOND = fps
        FONT_SIZE_MEDIUM = int(0.018 * screen_width)

        self.latest_time_since_rec_str = ""
        # Button setup
        self.buttons = []
        self.buttons.append(Button(SCREEN, 0, 0, SCREEN_WIDTH/2, 0.0463*SCREEN_HEIGHT, BUTTON_STANDARD_COLOR, "Styrning", FONT_SIZE_MEDIUM, False))
        self.buttons.append(Button(SCREEN, SCREEN_WIDTH/2, 0, SCREEN_WIDTH/2, 0.0463*SCREEN_HEIGHT, BUTTON_PRESSED_COLOR, "Plottar", FONT_SIZE_MEDIUM, False))
        self.buttons[1].is_active = True

        self.manual_speed_data = {
            "speed": [],
            "time": []
        }

        self.auto_speed_data = {
            "speed": [],
            "time": []
        }

        self.manual_orientation_data = {
            "orientation": [],
            "time": []
        }

        self.auto_orientation_data = {
            "orientation": [],
            "time": []
        }

        self.auto_angle_to_goal_data = {
            "start": 0,
            "angle": [],
            "time": []
        }

    def save_data(self, to_save = []):

        path = "data/plot_data"

        info = {
            "speed": {
                "data": self.manual_speed_data,
                "postfix": "_man_speed.csv",
                "type": "speed"
            },
            "orientation": {
                "data": self.manual_orientation_data,
                "postfix": "_man_orient.csv",
                "type": "orientation"
            },
            "auto_angle": {
                "data": self.auto_angle_to_goal_data,
                "postfix": "_auto_angle.csv",
                "type": "angle"
            }
        }

        for name in to_save:
            print(self.latest_time_since_rec_str)
            time_str = time.strftime("%Y_%m_%d_%H_%M_%S", self.latest_time_since_rec_str)
            with open(os.path.join(path, time_str + info[name]["postfix"]), 'a', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                # Write header
                csv_writer.writerow(["time", info[name]["type"]])
                # Write data
                for t, s in zip(info[name]["data"]["time"], info[name]["data"][info[name]["type"]]):
                    csv_writer.writerow([t, s])

    # Setup plot data
    def setup_plots(self):
        all_plot_data = []
        
        # Distance vs time.
        fig_dt = pylab.figure(figsize=[1/175*SCREEN_WIDTH, 1/180*SCREEN_HEIGHT], dpi=72)
        pylab.xlabel("Tid [s]", fontsize=18)
        pylab.ylabel("Hastighet [mm/s]", fontsize=18)
        pylab.xticks(fontsize=15)
        pylab.yticks(fontsize=15)
        axis_dt = fig_dt.gca() 
        axis_dt.plot(self.manual_speed_data["time"], self.manual_speed_data["speed"], "black")
        plt.gcf().subplots_adjust(bottom=0.18)

        canvas_dt = agg.FigureCanvasAgg(fig_dt)
        canvas_dt.draw()
        renderer_dt = canvas_dt.get_renderer()
        raw_data_dt = renderer_dt.tostring_rgb()
        size_dt = canvas_dt.get_width_height()

        # Orientation vs time.
        fig_ht = pylab.figure(figsize=[1/175*SCREEN_WIDTH, 1/180*SCREEN_HEIGHT], dpi=72)
        pylab.xlabel("Tid [s]", fontsize=18)
        pylab.ylabel("Vinkel [grader]", fontsize=18)
        pylab.xticks(fontsize=15)
        pylab.yticks(fontsize=15)
        axis_ht = fig_ht.gca() 
        axis_ht.plot(self.manual_orientation_data["time"], self.manual_orientation_data["orientation"], "black")
        plt.gcf().subplots_adjust(bottom=0.18)

        canvas_ht = agg.FigureCanvasAgg(fig_ht)
        canvas_ht.draw()
        renderer_ht = canvas_ht.get_renderer()
        raw_data_ht = renderer_ht.tostring_rgb()
        size_ht = canvas_ht.get_width_height()

        # Angle to goal vs time.
        fig_at = pylab.figure(figsize=[1/175*SCREEN_WIDTH, 1/180*SCREEN_HEIGHT], dpi=72)
        pylab.xlabel("Tid [s]", fontsize=18)
        pylab.ylabel("Vinkel [grader]", fontsize=18)
        pylab.xticks(fontsize=15)
        pylab.yticks(fontsize=15)
        axis_at = fig_at.gca() 
        axis_at.plot(self.auto_angle_to_goal_data["time"], self.auto_angle_to_goal_data["angle"], "black")
        plt.gcf().subplots_adjust(bottom=0.18)

        #print(self.auto_angle_to_goal_data)

        canvas_at = agg.FigureCanvasAgg(fig_at)
        canvas_at.draw()
        renderer_at = canvas_at.get_renderer()
        raw_data_at = renderer_at.tostring_rgb()
        size_at = canvas_at.get_width_height()

        all_plot_data.append((raw_data_dt, size_dt))
        all_plot_data.append((raw_data_ht, size_ht))
        all_plot_data.append((raw_data_at, size_at))

        pylab.close("all")
        return all_plot_data


    # Check for window closed.
    def handle_event(self, event):
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()

    
    # Rendering and updating. 
    def update_and_draw(self):
        # Fill background color.
        SCREEN.fill((75, 105, 91)) 
        self.render_buttons()

        all_plot_data = self.setup_plots()

        # Convert string data to PyGame image.
        for idx, plot_data in enumerate(all_plot_data):
            surface = pg.image.fromstring(plot_data[0], plot_data[1], "RGB")
            if idx == 0:
                SCREEN.blit(surface, (0.04688*SCREEN_WIDTH, 0.09259*SCREEN_HEIGHT))
            elif idx == 1:
                SCREEN.blit(surface, (0.5417*SCREEN_WIDTH, 0.09259*SCREEN_HEIGHT))
            elif idx == 2:
                SCREEN.blit(surface, (0.29429*SCREEN_WIDTH, 0.5556*SCREEN_HEIGHT))

        # Draw screen
        pg.display.update()

    # Render the buttons.
    def render_buttons(self):
        for button in self.buttons:
            button.draw_button()
