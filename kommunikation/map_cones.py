from os import listdir
from os.path import isfile, join
from gridmap import create_gridmap
from circular_hough import get_cones
from utils import *
import numpy as np
import math
import json
import time

# Identify cone pairs and isolated cones based on distance
def identify_cones(cones):
    cone_data = []
    skip_index = []
    ispair = False

    for i, cone in enumerate(cones):
        for j, other_cone in enumerate(cones):
            dist = np.linalg.norm(np.array(cone["position"]) - np.array(other_cone["position"]))
            if (dist < 100) and (i != j):
                del cones[j]
                break

    for i in range(len(cones)):
        ispair = False
        for j in range(len(cones)):
            if (j == i) or (i in skip_index) or (j in skip_index):
                continue
            else:
                cone1 = cones[i]
                cone2 = cones[j]
                dist = np.linalg.norm(np.array(cone1["position"]) - np.array(cone2["position"]))
                if dist <= 1300:
                    cone_data.append([cone1, cone2])
                    skip_index.append(i)
                    skip_index.append(j)
                    ispair = True
        if not ispair and (not i in skip_index):
            skip_index.append(i)
            cone_data.append([cone1])

    return cone_data

# Send a all cone info (position, radius, if pair) over a channel as JSON
def main():
    mypath = "data/input"
    desination_path = "data/cones"

    onlyfiles = [f.replace("_lidar.csv","").replace("_pos.csv","") for f in listdir(mypath) if isfile(join(mypath, f))]
    onlyfiles = sorted(list(set(onlyfiles)))

    id = onlyfiles[-1]

    connection = connect_to_server('localhost')
    #channel = connection.channel()
    com_message_channel = create_channel(connection, "com_message")

    start_time = time.time()
    
    send_message("com_message", "Genererar karta", connection, com_message_channel)
    create_gridmap(0.03, -math.pi*0.013, 0, 0, id, save_image = False)

    send_message("com_message", "Identifierar koner", connection, com_message_channel)
    cones = get_cones(id)

    send_message("com_message", "Hittar konpar", connection, com_message_channel)
    cones = identify_cones(cones)

    current_time = time.time()
    elapsed_time = round(current_time - start_time, 1)
    send_message("com_message", f'Kartläggningen tog {elapsed_time} sekunder.', connection, com_message_channel)

    cone_file_name = f"{id}_cones.json"

    if cone_file_name in listdir(desination_path):
        with open(join(desination_path, cone_file_name), "w") as f:
            f.write(json.dumps(cones))
        with open(join(desination_path, "cone_data.json"), "w") as f:
            f.write(json.dumps(cones))
    else:
        with open(join(desination_path, cone_file_name), "w+") as f:
            f.write(json.dumps(cones))
        with open(join(desination_path, "cone_data.json"), "w+") as f:
            f.write(json.dumps(cones))
    send_message("com_message", f'Ny kondata sparad.', connection, com_message_channel)
    send_message("cone_position", json.dumps(cones))

if __name__ == "__main__":
    main()