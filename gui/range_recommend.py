import csv
import os

def recommend_ranges(csv_file):
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    with open(csv_file, 'r', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader)  # Skip header row

        for row in csv_reader:
            x = float(row[0])
            y = float(row[1])

            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

    return min_x, max_x, min_y, max_y

DATA_DIR = 'data'
DATA_FILE = '111.csv'
csv_file = os.path.join(DATA_DIR, DATA_FILE)
min_x, max_x, min_y, max_y = recommend_ranges(csv_file)

print(f"Ideal X range: {min_x} mm to {max_x} mm")
print(f"Ideal Y range: {min_y} mm to {max_y} mm")
