import numpy as np
import matplotlib.pyplot as plt
from utils import *
import json

BEZIER_DIVIDER = 250
GHOST_PORT_RADIUS = 30

class Port():
    def __init__(self, p1, p2) -> None:
        self.p1 = p1
        self.p2 = p2
        self.mid_point_x = 1/2*(self.p1[0]+self.p2[0]) 
        self.mid_point_y = 1/2*(self.p1[1]+self.p2[1])
    
    def get_line_coefficients(self):

        k = -(self.p1[0]-self.p2[0])/(self.p1[1]-self.p2[1])
        m = self.mid_point_y - k*self.mid_point_x

        return k, m

def generate_bezier_curve_segment(port1, port2):
    (k1, m1) = port1.get_line_coefficients()
    (k2, m2) = port2.get_line_coefficients()
    if k1 != k2:
        intersection_x = (m2-m1)/(k1-k2)
        intersection_y = k1*(m2-m1)/(k1-k2) + m1
    else:
        raise Exception(f"Bezier: Could not find intesection point between ports ({port1[0]}, {port1[1]}) and ({port2[0]}, {port2[1]})")

    port_distance = np.sqrt((port1.mid_point_x - port2.mid_point_x)**2 + (port1.mid_point_y - port2.mid_point_y)**2)

    bezier_point_count = int(port_distance / BEZIER_DIVIDER)

    bezier_segment_points = []
    for t in np.linspace(0, 1, bezier_point_count):
        bez_x = (1-t)**2*port1.mid_point_x + 2*(1-t)*t*intersection_x + t**2*port2.mid_point_x
        bez_y = (1-t)**2*port1.mid_point_y + 2*(1-t)*t*intersection_y + t**2*port2.mid_point_y

        bezier_segment_points.append((bez_x, bez_y))

    x_data_plot = [coordinate[0] for coordinate in bezier_segment_points]
    #x_data_plot.append(intersection_x)
    y_data_plot = [coordinate[1] for coordinate in bezier_segment_points]
    #y_data_plot.append(intersection_y)
    plt.scatter(x_data_plot, y_data_plot)
    plt.autoscale(enable=True, axis='both', tight=None)

    return bezier_segment_points

def generate_sub_goals(list_of_cones):
    list_of_ports = []
    list_of_roundles = []
    for cone_list in list_of_cones:
        # Cone pair
        if len(cone_list) == 2:
            port = Port(cone_list[0]["position"], cone_list[1]["position"])
            # print(f"Mid point: {port.mid_point_x}, {port.mid_point_y}")
            list_of_ports.append(port)
        # Single cone
        if len(cone_list) == 1:
            list_of_roundles.append(cone_list[0]["position"])

    return list_of_ports, list_of_roundles

def sort_sub_goals(list_of_ports, list_of_roundles, checkpoints):
    sorted_list = []
    list_of_sub_goals = list_of_ports + list_of_roundles
    for checkpoint in checkpoints:
        shortest_dist = 999999999
        shortest_idx = 0
        for idx, sub_goal in enumerate(list_of_sub_goals):
            if type(sub_goal) is Port:
                midpoint = (sub_goal.mid_point_x, sub_goal.mid_point_y)
            else:
                midpoint = sub_goal[0], sub_goal[1]
            dist_to_checkpoint = (midpoint[0]-checkpoint[0])**2 + (midpoint[1]-checkpoint[1])**2
            if dist_to_checkpoint < shortest_dist:
                shortest_dist = dist_to_checkpoint
                shortest_idx = idx
        
        sorted_list.append(list_of_sub_goals[shortest_idx])
    return sorted_list

def generate_ghost_port(sub_goal, checkpoint):
    if sub_goal[0] - checkpoint[0] != 0:
        k = (sub_goal[1] - checkpoint[1]) / (sub_goal[0] - checkpoint[0])
        step = GHOST_PORT_RADIUS / np.sqrt(1+k**2)
        ghost_port1 = (checkpoint[0] + step, checkpoint[1] + step * k) 
        ghost_port2 = (checkpoint[0] - step, checkpoint[1] - step * k)

        print("step", step, "k", k, "checlpoint", checkpoint)
    return Port(ghost_port1, ghost_port2)

def generate_ports(list_of_sub_goals, checkpoints):
    list_of_ports = []

    for idx, sub_goal in enumerate(list_of_sub_goals):
        if type(sub_goal) is Port:
            list_of_ports.append(sub_goal)
        else:
            ghost_port = generate_ghost_port(sub_goal, checkpoints[idx])
            list_of_ports.append(ghost_port)
    return list_of_ports

def generate_full_bezier_curve(list_of_cones, checkpoints):

    list_of_ports, list_of_roundles = generate_sub_goals(list_of_cones)
    list_of_sub_goals = sort_sub_goals(list_of_ports, list_of_roundles, checkpoints)
    list_of_ports = generate_ports(list_of_sub_goals, checkpoints)

    bezier_points = []
    for idx, _ in enumerate(range(len(list_of_ports)-1)):
        bezier_points += (generate_bezier_curve_segment(list_of_ports[idx], list_of_ports[idx+1]))
        if idx == len(list_of_ports)-2:
            bezier_points += (generate_bezier_curve_segment(list_of_ports[idx+1], list_of_ports[0]))
    
    return bezier_points

def main():

    connection = connect_to_server("localhost")
    channel = connection.channel()
    channel.queue_declare(queue="internal_checkpoints")
    
    message = None
    while not message:
        message = get_latest_message("internal_checkpoints", connection, channel)
        if (not message is None) and message != "":
            checkpoints = json.loads(message)
            
    with open("data/cones/cone_data.json", "r") as f:
                cones = json.loads(f.read())        
    bezier_points = generate_full_bezier_curve(cones, checkpoints)

    with open("data/bezier/bezier_points.json", "w+") as f:
        f.write(json.dumps(bezier_points))

if __name__ == "__main__":
    main()