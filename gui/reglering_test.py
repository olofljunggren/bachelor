import numpy as np
import math

def test():
    manual_car_positions = [(0, 0), (400, -400), (200, 100), (-20, 400),\
                (0, -5500), (500, -5000), (2000, -3000), (4000, -1000), (5500, 0), (4000, 1000), \
                (2000, 3000), (100, 5400), (-400, 5500), (-2000, 4000), (-4000, 1000), (-5000, - 250)]

    position = manual_car_positions[0]
    x_car = position[0]
    y_car = position[1]
    look_ahead_distance = 300
    distance = 0
    orientation = -30
    last_error_steer = 2
    integrated_error_steer = 0

    min_steer = 275
    max_steer = 475

    KP_steer = 150
    KI_steer = 0
    KD_steer = 0
    TIME_PER_LOOP = 1/50

    for index, position in enumerate(manual_car_positions):
        x_point = position[0]
        y_point = position[1]

        if index == 0:
            distance += np.sqrt( pow(x_point-x_car, 2) + pow(y_point-y_car, 2) )
        else:
            previous_x_point = manual_car_positions[index-1][0]
            previous_y_point = manual_car_positions[index-1][1]
            manual_car_positions[index-1][1]
            distance += np.sqrt( pow(x_point-previous_x_point, 2) + pow(y_point-previous_y_point, 2) )

        if not distance >= look_ahead_distance:
            continue
        
        if x_point-x_car == 0:
                requested_orientation = 90 if y_point-y_car > 0 else -90
        else:
            requested_orientation = np.arctan((y_point-y_car)/(x_point-x_car))*180/3.1415926 
        if x_point-x_car < 0:
            requested_orientation = requested_orientation + 180 if y_point - y_car > 0 else requested_orientation - 180

        error_angle = orientation - requested_orientation
        if error_angle > 180:
            error_angle -= 360
        elif error_angle < -180:
            error_angle += 360

        integrated_error_steer += error_angle
        derivative_error = (error_angle - last_error_steer)/TIME_PER_LOOP

        steer_angle_displacement = error_angle*math.pi/180*KP_steer + KI_steer*integrated_error_steer + KD_steer*derivative_error
        steer_angle_midpoint = (min_steer + max_steer)/2
        steer_angle = steer_angle_midpoint + steer_angle_displacement
        
        last_error_steer = error_angle

        print("Bil:", (x_car, y_car), "Siktpunkt:", (x_point, y_point))
        print("requested_orientation", requested_orientation)
        print("Error:", error_angle)
        print("integrated_error_steer:", integrated_error_steer)
        print("derivative_error:", derivative_error)
        print("Steer angle displacement:", steer_angle_displacement)
        print("Final calculated steer angle:", steer_angle)
        break

if __name__ == "__main__":
    test()