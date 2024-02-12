import numpy as np
import scipy.sparse
import json
from numpyencoder import NumpyEncoder
#import matplotlib.pyplot as plt

def create_circle_mask(radius, width=1):
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = (x**2 + y**2 >= (radius - width)**2) & (x**2 + y**2 <= radius**2)
    return mask.astype(float)

def circular_hough_transform(matrix, radius_ranges, step=1):
    rows, cols = matrix.shape
    radii = [r for r_range in radius_ranges for r in range(r_range[0], r_range[1]+1, step)]
    num_radii = len(radii)
    accumulator = np.zeros((rows, cols, num_radii))

    # Convert the input matrix to a sparse representation
    sparse_matrix = scipy.sparse.coo_matrix(matrix)

    radius_index_map = {}
    for idx, radius in enumerate(radii):
        radius_index_map[radius] = idx
        circle_mask = create_circle_mask(radius)

        # Perform the convolution only on the non-zero elements of the sparse matrix
        for y, x, value in zip(sparse_matrix.row, sparse_matrix.col, sparse_matrix.data):
            y_min = max(y - radius, 0)
            y_max = min(y + radius + 1, rows)
            x_min = max(x - radius, 0)
            x_max = min(x + radius + 1, cols)

            mask = circle_mask[y_min-y+radius:y_max-y+radius, x_min-x+radius:x_max-x+radius]

            accumulator[y_min:y_max, x_min:x_max, idx] += value * mask
    
    # Normalize by the area of each circle
    for idx, radius in enumerate(radii):
        area = np.pi * radius ** 2
        accumulator[..., idx] /= (area ** (1/6))

    # Normalize the entire accumulator
    max_val = np.max(accumulator)
    if max_val > 0:
        accumulator *= 10 / max_val

    return accumulator, radius_index_map

def find_circles(accumulator, radius_index_map, threshold):
    detected_circles = np.where(accumulator > threshold)
    circles = []
    for y, x, r_idx in zip(*detected_circles):
        value = accumulator[y,x,r_idx]
        r = next(radius for radius, idx in radius_index_map.items() if idx == r_idx)
        circles.append(((y, x), r, value))

    # Perform non-maximum suppression
    circles = sorted(circles, key=lambda x: x[2], reverse=True)
    i = 0
    while i < len(circles):
        highest_value_circle = circles[i]
        j = i + 1
        while j < len(circles):
            circle = circles[j]
            dist = np.linalg.norm(np.array(highest_value_circle[0]) - np.array(circle[0]))
            #if dist < highest_value_circle[1] + 10:
            if dist < 50:
                circles.pop(j)
            else:
                j += 1
        i += 1

    return circles

def circles_json(circles, id):
    # X and Y was in the wrong place. 
    # Multiply by 10 to get mm (our conventional distance measurment).
    # Store as JSON (or dict)
    cone_data = [{"position": [int((circle[0][1]-500)*10), int((circle[0][0]-500)*10)], "radius": int(radius_correction(circle[1])*10)} for circle in circles]
    return cone_data
    """
    with open(f'data/cones/{id}_cones.json', 'w') as f:
        json.dump(cone_data, f, cls=NumpyEncoder)
    print(cone_data)
    """

def radius_correction(radius):
    if 5 <= radius <= 8:
        return 5
    if 10 <= radius <= 11:
        return 10
    if 13 <= radius <= 16:
        return 15

# Given the latest saved occupancy gridmap, perform circular hough transformation
# and identify all cones.
def get_cones(id):
    matrix = np.load(f"data/matrix_output/{id}_matrix.dat", allow_pickle=True)
    radius_ranges = [(10, 11)]
    accumulator, radius_index_map = circular_hough_transform(matrix, radius_ranges)
    circles = find_circles(accumulator, radius_index_map, threshold=3.5) #3.5
    
    return circles_json(circles, id)

if __name__ == "__main__":
    #id = "2023_04_24_07_50_14"
    #id = "2023_04_25_07_01_51"
    #id = "2023_04_25_07_43_43"
    id = "2023_04_25_07_55_57"
    get_cones(id)