import pandas as pd
import numpy as np
import math
import time

def read_csv_data(lidar_csv, pose_csv):
    lidar_data = pd.read_csv(lidar_csv, names=['distance', 'angle', 'time'], dtype={'time': float})
    pose_data = pd.read_csv(pose_csv, names=['x', 'y', 'angle', 'time'], dtype={'x': float, 'y': float, 'angle': float, 'time': float})

    # Change to Radians and invert lidar angle
    lidar_data["angle"] = -np.radians(lidar_data["angle"])
    pose_data["angle"] = np.radians(pose_data["angle"])

    # Round time values to a specific number of decimal places
    decimals = 3
    lidar_data['time'] = lidar_data['time'].round(decimals)
    pose_data['time'] = pose_data['time'].round(decimals)

    # Convert time values to DateTime
    lidar_data['time'] = pd.to_datetime(lidar_data['time'], unit='s')
    pose_data['time'] = pd.to_datetime(pose_data['time'], unit='s')

    return lidar_data, pose_data

def interpolate_pose_data(lidar_df, pose_df, time_offset):

    pose_df['time'] = pose_df['time'] + pd.to_timedelta(time_offset, unit='s')

    # Sort the DataFrames by time
    lidar_df.sort_values('time', inplace=True)
    pose_df.sort_values('time', inplace=True)

    # Perform merge_asof
    merged_df = pd.merge_asof(lidar_df, pose_df, on='time', direction='nearest', suffixes=('', '_pose'))

    # Set the index to 'time' and interpolate missing values
    merged_df.set_index('time', inplace=True)
    merged_df.interpolate(method='time', inplace=True)
    merged_df.fillna(method='bfill', inplace=True)  # Fill remaining NaN values
    #merged_df.dropna(subset=['x', 'y', 'angle_pose'], inplace=True)

    # Keep only the 'x', 'y', and 'angle' columns
    pose_df_interpolated = merged_df[['x', 'y', 'angle_pose']]
    pose_df_interpolated.rename(columns={'angle_pose': 'angle'}, inplace=True)

    return pose_df_interpolated

def polar_to_cartesian(lidar_data):
    x = lidar_data['distance'] * np.cos(lidar_data['angle'])
    y = lidar_data['distance'] * np.sin(lidar_data['angle'])
    return pd.DataFrame({'x': x, 'y': y})

def transform_lidar_to_global_frame(lidar_points, interpolated_poses, offset_angle, cent_offset_distance, cent_offset_angle):

    num_points = len(lidar_points)
    transformed_points = np.empty((num_points, 2))

    reflection_matrix = np.array([[1, 0], [0, 1]])

    slight_rotation = np.array([[np.cos(0.014968941753670473), -np.sin(0.014968941753670473)],
                        [np.sin(0.014968941753670473), np.cos(0.014968941753670473)]])
    
    # Calculate the LIDAR-to-rigid-body transformation matrix with the offset_angle
    R_offset = np.array([[np.cos(offset_angle), -np.sin(offset_angle)],
                         [np.sin(offset_angle), np.cos(offset_angle)]])
    
    cent_offset_vector = np.array([cent_offset_distance * np.cos(cent_offset_angle), cent_offset_distance * np.sin(cent_offset_angle)])

    for i, (lidar_point, pose) in enumerate(zip(lidar_points.itertuples(), interpolated_poses.itertuples())):

        # Calculate the rigid body's global transformation matrix
        R_global = np.array([[np.cos(pose.angle), -np.sin(pose.angle)],
                             [np.sin(pose.angle), np.cos(pose.angle)]])
        
        # Apply the LIDAR-to-rigid-body offset to the local LIDAR Cartesian coordinates
        lidar_point_local_rigid_body = R_offset @ np.array([lidar_point.x, lidar_point.y]) + cent_offset_vector
        
        # Transform the points from the rigid body's local coordinate system to the global coordinate system
        transformed_point = R_global @ lidar_point_local_rigid_body + np.array([pose.x, pose.y])

        # Apply the reflection matrix for vertical flip
        transformed_point = slight_rotation @ (reflection_matrix @ transformed_point)
        
        transformed_points[i] = transformed_point
        
    return pd.DataFrame(transformed_points, columns=['x', 'y'])



def save_transformed_lidar_points(transformed_points, output_csv):
    transformed_points.to_csv(output_csv, index=False, header=['x', 'y'])


def combine_data(lidar_csv, pose_csv, output_csv, rm_start, rm_end, offset_angle, cent_offset_distance, cent_offset_angle, time_offset):
    lidar_points, pose_data = read_csv_data(lidar_csv, pose_csv)

    total_points = len(lidar_points)
    start_index = int(total_points * (rm_start / 100))
    end_index = int(total_points * (rm_end / 100))
    lidar_points = lidar_points[start_index:end_index]

    total_points = len(pose_data)
    start_index = int(total_points * (rm_start / 100))
    end_index = int(total_points * (rm_end / 100))
    pose_data = pose_data[start_index:end_index]

    interpolated_poses = interpolate_pose_data(lidar_points, pose_data, time_offset)
    lidar_points = polar_to_cartesian(lidar_points)

    start_time = time.time()

    transformed_points = transform_lidar_to_global_frame(lidar_points, interpolated_poses, offset_angle, cent_offset_distance, cent_offset_angle)

    elapsed_time = start_time - time.time()

    print(f"It took{elapsed_time} seconds")

    save_transformed_lidar_points(transformed_points, output_csv)

if __name__ == "__main__":
    pass
