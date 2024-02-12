import csv
import numpy as np
from PIL import Image
import os

def generate_image_from_csv(
    csv_file,
    output_image,
    grid_size_mm,
    min_x_mm,
    max_x_mm,
    min_y_mm,
    max_y_mm,
    outline=False
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
                matrix[cell_y, cell_x] += 1

    max_val = np.max(matrix)
    normalized_matrix = (matrix / max_val) * 255
    normalized_matrix = normalized_matrix.astype(np.uint8)
    
    # Save the normalized matrix as an image
    img = Image.fromarray(normalized_matrix)

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

# Example usage:
DATA_DIR = 'data'
DATA_FILE = '111.csv'
csv_file = os.path.join(DATA_DIR, DATA_FILE)
output_image = os.path.join(DATA_DIR, DATA_FILE+'_image.png')
grid_size_mm = 100
min_x_mm = -6000
max_x_mm = 9000
min_y_mm = -9000
max_y_mm = 5000
outline = True

generate_image_from_csv(
    csv_file,
    output_image,
    grid_size_mm,
    min_x_mm,
    max_x_mm,
    min_y_mm,
    max_y_mm,
    outline
    )
