import os
import numpy as np
import math

from trans_data import combine_data
from points_to_image import generate_image_from_csv

"""
This script serves as a way to both combine the data and create the occupancy grid map.
This predefines a lot of parameters that has been found to not be needed to be updated at all
or very infrequently.
"""

def main():
    #id = "2023_04_21_15_42_54"
    #id = "2023_04_21_16_06_30"
    #id = "2023_04_24_07_50_14"
    #id = "2023_04_25_07_01_51"
    #id = "2023_04_25_07_43_43"
    id = "2023_04_25_07_55_57"
    #create_gridmap(0.2, math.pi*0.015, 0, 0, save_image = True)
    create_gridmap(0.03, -math.pi*0.013, 0, 0, id, save_image = False)

def create_gridmap(time_offset, offset_angle, cent_offset_distance, cent_offset_angle, id, save_image = False):
    lidar_csv = f'data/input/{id}_lidar.csv'
    pose_csv = f'data/input/{id}_pos.csv'
    rm_start = 0
    rm_end = 100
    output_csv = f'data/transformed_output/{id}_transformed_lidar_{rm_start}%->{rm_end}%.csv'

    combine_data(
    lidar_csv,
    pose_csv, 
    output_csv, 
    rm_start, 
    rm_end,
    offset_angle,
    cent_offset_distance, 
    cent_offset_angle,
    time_offset
    )

    csv_file = output_csv
    output_image = f'data/output_image/{id}_image_{rm_start}%->{rm_end}%.png'
    grid_size_mm = 10
    min_x_mm = -5000
    max_x_mm = 5000
    min_y_mm = -5000
    max_y_mm = 5000
    max_value_per_cell = 50
    outline = False

    matrix = generate_image_from_csv(
    csv_file,
    output_image,
    grid_size_mm,
    min_x_mm,
    max_x_mm,
    min_y_mm,
    max_y_mm,
    max_value_per_cell,
    outline,
    save_image
    )

    if not os.path.exists("data/matrix_output"):
        os.makedirs("data/matrix_output")
    matrix.dump(f"data/matrix_output/{id}_matrix.dat")

if __name__ == "__main__":
    main()