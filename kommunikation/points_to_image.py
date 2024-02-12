import csv
import numpy as np
from PIL import Image
import os

import csv
import numpy as np
from scipy.ndimage import gaussian_filter

# A function that performs intensity level adjustment based on changing the contrast of different intensity ranges
def adjust_levels(normalized_matrix, low_input, gamma, high_input):
    
    # Apply the level adjustments
    adjusted_matrix = np.where(normalized_matrix <= low_input,
                               normalized_matrix * (low_input / gamma),
                               np.where(normalized_matrix >= high_input,
                                        1 - (1 - normalized_matrix) * (1 - high_input / gamma),
                                        (normalized_matrix - low_input) / (high_input - low_input) * gamma))
    
    # Scale the adjusted matrix back to its original range
    adjusted_matrix
    
    return adjusted_matrix

# Create the occupancy grid map
# Each cell in the matrix corresponds to a specific area of the map and its value represents the number of points that fall within that area.
def generate_image_from_csv(
    csv_file,
    output_image,
    grid_size_mm,
    min_x_mm,
    max_x_mm,
    min_y_mm,
    max_y_mm,
    max_value_per_cell,
    outline=False,
    save_image=False,
    ):

    num_x_cells = int((max_x_mm - min_x_mm) / grid_size_mm)
    num_y_cells = int((max_y_mm - min_y_mm) / grid_size_mm)
    
    matrix = np.zeros((num_y_cells, num_x_cells), dtype=np.int32)
    
    with open(csv_file, 'r', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader)  # Skip header row

        for row in csv_reader:
            x_mm = float(row[0])
            y_mm = float(row[1])

            # Check if the point is within the specified range
            if min_x_mm <= x_mm <= max_x_mm and min_y_mm <= y_mm <= max_y_mm:
                cell_x = int((x_mm - min_x_mm) / grid_size_mm)
                cell_y = int((y_mm - min_y_mm) / grid_size_mm)
                
                # Increment the value in the cell, but do not exceed the maximum value
                matrix[cell_y, cell_x] = min(matrix[cell_y, cell_x] + 1, max_value_per_cell)

    #matrix = gaussian_filter(matrix, sigma=1)

    normalized_matrix = (matrix / np.max(matrix))

    low_input = 0.08
    gamma = 1
    high_input = 0.3
    normalized_matrix = adjust_levels(normalized_matrix, low_input, gamma, high_input)

    normalized_matrix = gaussian_filter(normalized_matrix, sigma=1)

    threshold = 0.01
    normalized_matrix = np.where(normalized_matrix < threshold, 0, normalized_matrix)

    image_matrix = (normalized_matrix * 255).astype(np.uint8)
    
    if save_image:
            
        # Save the normalized matrix as an image
        img = Image.fromarray(image_matrix)

        pecent = 0.02

        if outline:
            outline_width = int(img.width * pecent)
            outline_height = int(img.height * pecent)

            # Create a new white image with increased dimensions to accommodate the outline
            outlined_image = Image.new('L', (img.width + 2 * outline_width, img.height + 2 * outline_height), 255)

            # Paste the original image onto the white image, positioning it at the center
            outlined_image.paste(img, (outline_width, outline_height))

            # Save the image with the outline
            outlined_image.save(output_image)
        else:
            img.save(output_image)
    
    return normalized_matrix


if __name__ == "__main__":
    pass